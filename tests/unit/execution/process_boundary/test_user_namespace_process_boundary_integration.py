from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from lyrion.execution.backends.linux.enforcement.primitives import (
    native_user_namespace_identity as identity_module,
)

CLONE_NEWUSER = 0x10000000


def _read_mapping(pid: int, name: str) -> list[list[str]]:
    path = Path(f"/proc/{pid}/{name}")

    lines = [
        line.split()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]

    return lines


def _verify_mapping(
    pid: int,
    host_uid: int,
    host_gid: int,
) -> None:
    uid_lines = _read_mapping(pid, "uid_map")
    gid_lines = _read_mapping(pid, "gid_map")

    if len(uid_lines) != 1:
        raise AssertionError(
            f"unexpected uid_map for pid {pid}: {uid_lines!r}"
        )

    if len(gid_lines) != 1:
        raise AssertionError(
            f"unexpected gid_map for pid {pid}: {gid_lines!r}"
        )

    assert uid_lines[0] == [
        "0",
        str(host_uid),
        "1",
    ]

    assert gid_lines[0] == [
        "0",
        str(host_gid),
        "1",
    ]


def _child_source() -> str:
    return textwrap.dedent(
        """
        import ctypes
        import os
        import sys
        from pathlib import Path

        CLONE_NEWUSER = 0x10000000
        PR_SET_NO_NEW_PRIVS = 38
        PR_GET_NO_NEW_PRIVS = 39

        libc = ctypes.CDLL(None, use_errno=True)

        libc.unshare.argtypes = [ctypes.c_int]
        libc.unshare.restype = ctypes.c_int

        libc.prctl.argtypes = [
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        libc.prctl.restype = ctypes.c_int

        ready_fd = int(sys.argv[1])
        mapping_fd = int(sys.argv[2])
        result_fd = int(sys.argv[3])

        def send(message: str) -> None:
            os.write(
                result_fd,
                (message + "\\n").encode("ascii"),
            )

        def fail(message: str) -> None:
            try:
                send("FAIL:" + message)
            finally:
                os._exit(77)

        def read_mapping(name: str) -> list[list[str]]:
            path = Path(f"/proc/self/{name}")

            return [
                line.split()
                for line in path.read_text(
                    encoding="ascii"
                ).splitlines()
                if line.strip()
            ]

        try:
            if libc.unshare(CLONE_NEWUSER) != 0:
                error_number = ctypes.get_errno()

                fail(
                    "user namespace creation failed:"
                    + os.strerror(error_number)
                )

            child_namespace = os.readlink(
                "/proc/self/ns/user"
            )

            if not child_namespace.startswith("user:["):
                fail(
                    "invalid user namespace identity:"
                    + child_namespace
                )

            send("CHILD_PID:" + str(os.getpid()))
            send("PARENT_PID:" + str(os.getppid()))
            send("USER_NAMESPACE:" + child_namespace)

            os.write(
                ready_fd,
                b"READY",
            )

            mapping_signal = os.read(
                mapping_fd,
                32,
            )

            if mapping_signal != b"MAPPED":
                fail(
                    "mapping synchronization failed:"
                    + repr(mapping_signal)
                )

            uid_lines = read_mapping("uid_map")
            gid_lines = read_mapping("gid_map")

            if len(uid_lines) != 1:
                fail(
                    "unexpected child uid_map:"
                    + repr(uid_lines)
                )

            if len(gid_lines) != 1:
                fail(
                    "unexpected child gid_map:"
                    + repr(gid_lines)
                )

            send(
                "UID_MAP:"
                + " ".join(uid_lines[0])
            )

            send(
                "GID_MAP:"
                + " ".join(gid_lines[0])
            )

            if os.getuid() != 0:
                fail(
                    "child UID is not namespace-local root:"
                    + str(os.getuid())
                )

            if os.getgid() != 0:
                fail(
                    "child GID is not namespace-local root:"
                    + str(os.getgid())
                )

            send("UID:0")
            send("GID:0")

            prctl_result = libc.prctl(
                PR_SET_NO_NEW_PRIVS,
                1,
                0,
                0,
                0,
            )

            if prctl_result != 0:
                error_number = ctypes.get_errno()

                fail(
                    "PR_SET_NO_NEW_PRIVS failed:"
                    + os.strerror(error_number)
                )

            getter_result = libc.prctl(
                PR_GET_NO_NEW_PRIVS,
                0,
                0,
                0,
                0,
            )

            if getter_result != 1:
                fail(
                    "PR_GET_NO_NEW_PRIVS returned:"
                    + str(getter_result)
                )

            no_new_privs = None

            for line in Path(
                "/proc/self/status"
            ).read_text(
                encoding="ascii"
            ).splitlines():
                if line.startswith("NoNewPrivs:"):
                    no_new_privs = int(
                        line.split(":", 1)[1].strip()
                    )
                    break

            if no_new_privs != 1:
                fail(
                    "independent NoNewPrivs observation returned:"
                    + str(no_new_privs)
                )

            send("PRCTL_NO_NEW_PRIVS:1")
            send("PROC_NO_NEW_PRIVS:1")
            send("QUALIFIED")

            os.close(result_fd)
            os._exit(0)

        except BaseException as exc:
            try:
                send(
                    "FAIL:"
                    + type(exc).__name__
                    + ":"
                    + str(exc)
                )
            finally:
                os._exit(77)
        """
    )


def _spawn_child(
    ready_write: int,
    mapping_read: int,
    result_write: int,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            _child_source(),
            str(ready_write),
            str(mapping_read),
            str(result_write),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        close_fds=True,
        pass_fds=(
            ready_write,
            mapping_read,
            result_write,
        ),
        cwd=os.getcwd(),
        env=dict(os.environ),
        start_new_session=True,
    )


def _read_all(fd: int) -> str:
    chunks: list[bytes] = []

    while True:
        chunk = os.read(
            fd,
            65536,
        )

        if not chunk:
            break

        chunks.append(chunk)

    return b"".join(chunks).decode(
        "utf-8",
        errors="replace",
    )


def _read_parent_no_new_privs() -> int:
    for line in Path(
        "/proc/self/status"
    ).read_text(
        encoding="ascii"
    ).splitlines():
        if line.startswith("NoNewPrivs:"):
            return int(
                line.split(":", 1)[1].strip()
            )

    raise AssertionError(
        "parent /proc/self/status does not contain "
        "NoNewPrivs"
    )


def test_process_boundary_establishes_disposable_user_namespace() -> None:
    parent_namespace = (
        identity_module.read_user_namespace_identity()
    )

    ready_read, ready_write = os.pipe()
    mapping_read, mapping_write = os.pipe()
    result_read, result_write = os.pipe()

    child: subprocess.Popen[bytes] | None = None

    parent_pid = os.getpid()
    host_uid = os.getuid()
    host_gid = os.getgid()

    try:
        child = _spawn_child(
            ready_write,
            mapping_read,
            result_write,
        )

        os.close(ready_write)
        ready_write = -1

        os.close(mapping_read)
        mapping_read = -1

        os.close(result_write)
        result_write = -1

        ready = os.read(
            ready_read,
            5,
        )

        if ready != b"READY":
            stdout, stderr = child.communicate(
                timeout=5
            )

            raise AssertionError(
                "child failed before mapping boundary: "
                + stdout.decode(errors="replace")
                + stderr.decode(errors="replace")
            )

        Path(
            f"/proc/{child.pid}/uid_map"
        ).write_text(
            f"0 {host_uid} 1\n",
            encoding="ascii",
        )

        Path(
            f"/proc/{child.pid}/setgroups"
        ).write_text(
            "deny",
            encoding="ascii",
        )

        Path(
            f"/proc/{child.pid}/gid_map"
        ).write_text(
            f"0 {host_gid} 1\n",
            encoding="ascii",
        )

        _verify_mapping(
            child.pid,
            host_uid,
            host_gid,
        )

        os.write(
            mapping_write,
            b"MAPPED",
        )

        os.close(mapping_write)
        mapping_write = -1

        stdout, stderr = child.communicate(
            timeout=5
        )

        result = _read_all(
            result_read
        )

        combined = (
            result
            + stdout.decode(errors="replace")
            + stderr.decode(errors="replace")
        )

        assert child.returncode == 0, combined
        assert "QUALIFIED" in combined

        child_pid_line = next(
            line
            for line in combined.splitlines()
            if line.startswith("CHILD_PID:")
        )

        observed_parent_pid_line = next(
            line
            for line in combined.splitlines()
            if line.startswith("PARENT_PID:")
        )

        child_pid = int(
            child_pid_line.split(":", 1)[1]
        )

        observed_parent_pid = int(
            observed_parent_pid_line.split(":", 1)[1]
        )

        assert child_pid > 0
        assert child_pid != parent_pid
        assert observed_parent_pid == parent_pid

        namespace_line = next(
            line
            for line in combined.splitlines()
            if line.startswith("USER_NAMESPACE:")
        )

        child_namespace = (
            identity_module.UserNamespaceIdentity(
                inode=int(
                    namespace_line.split(
                        "[",
                        1,
                    )[1].rstrip("]")
                )
            )
        )

        identity_module.verify_namespace_isolation(
            parent_namespace,
            child_namespace,
        )

        uid_map_line = next(
            line
            for line in combined.splitlines()
            if line.startswith("UID_MAP:")
        )

        gid_map_line = next(
            line
            for line in combined.splitlines()
            if line.startswith("GID_MAP:")
        )

        assert uid_map_line.split(
            ":",
            1,
        )[1].split() == [
            "0",
            str(host_uid),
            "1",
        ]

        assert gid_map_line.split(
            ":",
            1,
        )[1].split() == [
            "0",
            str(host_gid),
            "1",
        ]

        assert "UID:0" in combined
        assert "GID:0" in combined
        assert "PRCTL_NO_NEW_PRIVS:1" in combined
        assert "PROC_NO_NEW_PRIVS:1" in combined

    finally:
        for fd in (
            ready_read,
            ready_write,
            mapping_read,
            mapping_write,
            result_read,
            result_write,
        ):
            if fd >= 0:
                os.close(fd)

        if child is not None and child.poll() is None:
            child.kill()
            child.wait(timeout=2)

        assert _read_parent_no_new_privs() == 0


def test_parent_process_security_state_is_not_mutated() -> None:
    assert _read_parent_no_new_privs() == 0

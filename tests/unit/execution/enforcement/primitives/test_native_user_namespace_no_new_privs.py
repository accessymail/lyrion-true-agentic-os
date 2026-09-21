from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import textwrap
from pathlib import Path

CLONE_NEWUSER = 0x10000000

PR_SET_NO_NEW_PRIVS = 38
PR_GET_NO_NEW_PRIVS = 39

LIBC = ctypes.CDLL(None, use_errno=True)
LIBC.unshare.argtypes = [ctypes.c_int]
LIBC.unshare.restype = ctypes.c_int

LIBC.prctl.argtypes = [
    ctypes.c_int,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
    ctypes.c_ulong,
]
LIBC.prctl.restype = ctypes.c_int


def _errno_message() -> str:
    error_number = ctypes.get_errno()
    return os.strerror(error_number)


def _unshare_user_namespace() -> None:
    if LIBC.unshare(CLONE_NEWUSER) != 0:
        raise OSError(
            ctypes.get_errno(),
            f"unshare(CLONE_NEWUSER) failed: {_errno_message()}",
        )


def _set_no_new_privs() -> None:
    if LIBC.prctl(
        PR_SET_NO_NEW_PRIVS,
        1,
        0,
        0,
        0,
    ) != 0:
        raise OSError(
            ctypes.get_errno(),
            f"PR_SET_NO_NEW_PRIVS failed: {_errno_message()}",
        )


def _get_no_new_privs() -> int:
    result = LIBC.prctl(
        PR_GET_NO_NEW_PRIVS,
        0,
        0,
        0,
        0,
    )

    if result < 0:
        raise OSError(
            ctypes.get_errno(),
            f"PR_GET_NO_NEW_PRIVS failed: {_errno_message()}",
        )

    return int(result)


def _read_no_new_privs_from_proc(pid: int) -> int:
    status_path = Path(f"/proc/{pid}/status")
    for line in status_path.read_text().splitlines():
        if line.startswith("NoNewPrivs:"):
            value = line.split(":", 1)[1].strip()
            return int(value)

    raise AssertionError(
        f"NoNewPrivs field not found in {status_path}"
    )


def _write_proc_mapping(
    pid: int,
    filename: str,
    content: str,
) -> None:
    Path(f"/proc/{pid}/{filename}").write_text(content)


def _deny_setgroups(pid: int) -> None:
    Path(f"/proc/{pid}/setgroups").write_text("deny")


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
        result_fd = int(sys.argv[2])

        def send(message):
            os.write(result_fd, (message + "\\n").encode())

        try:
            if libc.unshare(CLONE_NEWUSER) != 0:
                error_number = ctypes.get_errno()
                raise OSError(
                    error_number,
                    os.strerror(error_number),
                )

            send("USER_NAMESPACE_CREATED")

            os.write(ready_fd, b"READY")

            mapping_ready_fd = int(sys.argv[3])
            if os.read(mapping_ready_fd, 1) != b"M":
                raise RuntimeError(
                    "Parent did not signal completion of UID/GID mapping"
                )

            if libc.prctl(
                PR_SET_NO_NEW_PRIVS,
                1,
                0,
                0,
                0,
            ) != 0:
                error_number = ctypes.get_errno()
                raise OSError(
                    error_number,
                    os.strerror(error_number),
                )

            send(f"UID:{os.getuid()}")
            send(f"GID:{os.getgid()}")

            getter_value = libc.prctl(
                PR_GET_NO_NEW_PRIVS,
                0,
                0,
                0,
                0,
            )

            if getter_value < 0:
                error_number = ctypes.get_errno()
                raise OSError(
                    error_number,
                    os.strerror(error_number),
                )

            send(f"PRCTL_NO_NEW_PRIVS:{getter_value}")

            proc_value = None
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith("NoNewPrivs:"):
                    proc_value = int(
                        line.split(":", 1)[1].strip()
                    )
                    break

            if proc_value is None:
                raise RuntimeError(
                    "NoNewPrivs field missing from /proc/self/status"
                )

            send(f"PROC_NO_NEW_PRIVS:{proc_value}")

            if getter_value != 1:
                raise AssertionError(
                    f"prctl getter returned {getter_value}, expected 1"
                )

            if proc_value != 1:
                raise AssertionError(
                    f"/proc reports NoNewPrivs={proc_value}, expected 1"
                )

            send("QUALIFIED")
            os._exit(0)

        except BaseException as exc:
            send(
                "FAIL:"
                + type(exc).__name__
                + ":"
                + str(exc)
            )
            os._exit(77)
        """
    )


def test_parent_no_new_privs_state_is_unchanged() -> None:
    before = _read_no_new_privs_from_proc(os.getpid())

    assert before == 0, (
        "Qualification requires the VMware Ubuntu parent to start with "
        "NoNewPrivs: 0"
    )

    after = _read_no_new_privs_from_proc(os.getpid())

    assert after == before


def test_disposable_user_namespace_can_apply_no_new_privs() -> None:
    ready_read, ready_write = os.pipe()
    result_read, result_write = os.pipe()
    mapping_read, mapping_write = os.pipe()

    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _child_source(),
            str(ready_write),
            str(result_write),
            str(mapping_read),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        pass_fds=(ready_write, result_write, mapping_read),
        start_new_session=True,
    )

    os.close(ready_write)
    os.close(result_write)
    os.close(mapping_read)

    try:
        ready = os.read(ready_read, 5)

        if ready != b"READY":
            stdout, stderr = child.communicate(timeout=5)

            combined = (
                stdout.decode(errors="replace")
                + stderr.decode(errors="replace")
            )

            if "Operation not permitted" in combined:
                raise AssertionError(
                    "Disposable user namespace unavailable: "
                    + combined
                )

            raise AssertionError(
                "Child did not reach mapping boundary: "
                + combined
            )

        host_uid = os.getuid()
        host_gid = os.getgid()

        _write_proc_mapping(
            child.pid,
            "uid_map",
            f"0 {host_uid} 1\n",
        )

        _deny_setgroups(child.pid)

        _write_proc_mapping(
            child.pid,
            "gid_map",
            f"0 {host_gid} 1\n",
        )

        os.write(mapping_write, b"M")
        os.close(mapping_write)

        stdout, stderr = child.communicate(timeout=5)

        result_chunks: list[bytes] = []
        while True:
            chunk = os.read(result_read, 65536)
            if not chunk:
                break
            result_chunks.append(chunk)

        result = b"".join(result_chunks).decode()

        combined = result + stdout.decode(errors="replace") + stderr.decode(
            errors="replace"
        )

        assert "USER_NAMESPACE_CREATED" in combined
        assert "UID:0" in combined
        assert "GID:0" in combined
        assert "PRCTL_NO_NEW_PRIVS:1" in combined
        assert "PROC_NO_NEW_PRIVS:1" in combined
        assert "QUALIFIED" in combined

        assert child.returncode == 0, combined

    finally:
        os.close(ready_read)
        os.close(result_read)

        try:
            os.close(mapping_write)
        except OSError:
            pass

        if child.poll() is None:
            child.kill()

            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def test_parent_remains_no_new_privs_unchanged_after_child() -> None:
    assert _read_no_new_privs_from_proc(os.getpid()) == 0

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from lyrion.execution.backends.linux.enforcement.primitives import (
    native_user_namespace_identity as identity_module,
)


def test_parent_user_namespace_identity_is_valid() -> None:
    identity = identity_module.read_user_namespace_identity()

    assert identity.inode > 0


def test_namespace_isolation_rejects_same_identity() -> None:
    identity = identity_module.UserNamespaceIdentity(inode=1234)

    with pytest.raises(
        identity_module.UserNamespaceIdentityError,
        match="share the same user namespace",
    ):
        identity_module.verify_namespace_isolation(
            identity,
            identity,
        )


def test_single_identity_mapping_verification() -> None:
    identity_module.verify_single_identity_mapping(
        "0 1000 1",
        namespace_id=1234,
        host_id=1000,
    )

    with pytest.raises(
        identity_module.UserNamespaceIdentityError,
        match="unexpected namespace mapping",
    ):
        identity_module.verify_single_identity_mapping(
            "0 2000 1",
            namespace_id=1234,
            host_id=1000,
        )


def test_disposable_child_has_distinct_user_namespace() -> None:
    parent = identity_module.read_user_namespace_identity()

    script = r'''
import ctypes
import os

CLONE_NEWUSER = 0x10000000

libc = ctypes.CDLL(None, use_errno=True)
libc.unshare.argtypes = [ctypes.c_int]
libc.unshare.restype = ctypes.c_int

ready_read, ready_write = os.pipe()
mapped_read, mapped_write = os.pipe()

pid = os.fork()

if pid == 0:
    os.close(ready_read)
    os.close(mapped_write)

    if libc.unshare(CLONE_NEWUSER) != 0:
        os._exit(10)

    child_ns = os.readlink("/proc/self/ns/user")

    if not child_ns.startswith("user:["):
        os._exit(11)

    os.write(ready_write, b"READY")

    if os.read(mapped_read, 32) != b"MAPPED":
        os._exit(12)

    uid_map = open(
        "/proc/self/uid_map",
        encoding="ascii",
    ).read().strip()

    gid_map = open(
        "/proc/self/gid_map",
        encoding="ascii",
    ).read().strip()

    print("USER_NS:", child_ns, flush=True)
    print("UID_MAP:", uid_map, flush=True)
    print("GID_MAP:", gid_map, flush=True)
    print("UID:", os.getuid(), flush=True)
    print("GID:", os.getgid(), flush=True)

    if os.getuid() != 0:
        os._exit(13)

    if os.getgid() != 0:
        os._exit(14)

    os._exit(0)

os.close(ready_write)
os.close(mapped_read)

ready = os.read(ready_read, 32)

if ready != b"READY":
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    raise SystemExit(20)

host_uid = os.getuid()
host_gid = os.getgid()


def write_map(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC)
    try:
        data = value.encode("ascii")
        if os.write(fd, data) != len(data):
            raise RuntimeError("short mapping write")
    finally:
        os.close(fd)


write_map(
    f"/proc/{pid}/uid_map",
    f"0 {host_uid} 1\n",
)

write_map(
    f"/proc/{pid}/setgroups",
    "deny\n",
)

write_map(
    f"/proc/{pid}/gid_map",
    f"0 {host_gid} 1\n",
)

os.write(mapped_write, b"MAPPED")

_, status = os.waitpid(pid, 0)

if not os.WIFEXITED(status):
    raise SystemExit(30)

exit_code = os.WEXITSTATUS(status)

if exit_code != 0:
    raise SystemExit(exit_code)
'''

    result = subprocess.run(
        [sys.executable, "-c", script],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, (
        "cross-namespace identity qualification failed:\n"
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}\n"
        f"returncode={result.returncode}"
    )

    child_ns_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("USER_NS:")
    )

    child_ns = child_ns_line.split(":", 1)[1].strip()

    assert child_ns.startswith("user:[")
    assert child_ns.endswith("]")

    child_inode = int(
        child_ns[len("user:[") : -1],
        10,
    )

    child = identity_module.UserNamespaceIdentity(
        inode=child_inode,
    )

    identity_module.verify_namespace_isolation(
        parent,
        child,
    )

    host_uid = os.getuid()
    host_gid = os.getgid()

    uid_map_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("UID_MAP:")
    )
    gid_map_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("GID_MAP:")
    )

    uid_mapping = uid_map_line.split(":", 1)[1].split()
    gid_mapping = gid_map_line.split(":", 1)[1].split()

    assert uid_mapping == ["0", str(host_uid), "1"]
    assert gid_mapping == ["0", str(host_gid), "1"]
    assert "UID: 0" in result.stdout
    assert "GID: 0" in result.stdout


def test_mapping_reader_reads_exact_proc_content(tmp_path: Path) -> None:
    mapping = tmp_path / "uid_map"
    mapping.write_text(
        "0 1000 1\n",
        encoding="ascii",
    )

    assert identity_module.read_mapping(mapping) == "0 1000 1"

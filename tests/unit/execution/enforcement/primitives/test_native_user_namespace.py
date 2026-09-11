"""Disposable native user-namespace mapping qualification."""

from __future__ import annotations

import subprocess
import sys

from lyrion.execution.backends.linux.enforcement.primitives.native_user_namespace import (
    CLONE_NEWUSER,
)


def test_disposable_user_namespace_creation_and_mapping() -> None:
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

    result = libc.unshare(CLONE_NEWUSER)

    if result != 0:
        errno = ctypes.get_errno()
        os.write(
            ready_write,
            f"ERROR:{errno}".encode(),
        )
        os._exit(10)

    os.write(ready_write, b"READY")

    acknowledgement = os.read(mapped_read, 32)

    if acknowledgement != b"MAPPED":
        os._exit(11)

    uid_map = open("/proc/self/uid_map", encoding="ascii").read().strip()
    gid_map = open("/proc/self/gid_map", encoding="ascii").read().strip()

    print("UID_MAP:", uid_map, flush=True)
    print("GID_MAP:", gid_map, flush=True)
    print("UID:", os.getuid(), flush=True)
    print("GID:", os.getgid(), flush=True)

    if os.getuid() != 0:
        os._exit(12)

    if os.getgid() != 0:
        os._exit(13)

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

    if result.returncode != 0:
        raise AssertionError(
            "user namespace mapping qualification failed:\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}\n"
            f"returncode={result.returncode}"
        )

    assert "UID_MAP: 0 " in result.stdout
    assert "GID_MAP: 0 " in result.stdout
    assert "UID: 0" in result.stdout
    assert "GID: 0" in result.stdout


def test_user_namespace_constant() -> None:
    assert CLONE_NEWUSER == 0x10000000

from __future__ import annotations

import subprocess
import sys

from lyrion.execution.backends.linux.enforcement.primitives import (
    native_user_namespace_capabilities as capability_module,
)


def test_parent_capabilities_remain_unchanged_after_disposable_namespace() -> None:
    before = capability_module.read_current_capability_state()

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

    os.write(ready_write, b"READY")

    if os.read(mapped_read, 32) != b"MAPPED":
        os._exit(11)

    status = open(
        "/proc/self/status",
        encoding="ascii",
    ).read()

    fields = {}

    for line in status.splitlines():
        if line.startswith(
            ("CapInh:", "CapPrm:", "CapEff:", "CapBnd:", "CapAmb:")
        ):
            key, value = line.split(":", 1)
            fields[key] = value.strip()

    effective = int(fields["CapEff"], 16)
    permitted = int(fields["CapPrm"], 16)

    # CAP_SYS_ADMIN = 21.
    if not (effective & (1 << 21)):
        os._exit(12)

    if not (permitted & (1 << 21)):
        os._exit(13)

    if os.getuid() != 0:
        os._exit(14)

    if os.getgid() != 0:
        os._exit(15)

    os._exit(0)

os.close(ready_write)
os.close(mapped_read)

if os.read(ready_read, 32) != b"READY":
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
        "disposable namespace capability verification failed:\n"
        f"stdout={result.stdout}\n"
        f"stderr={result.stderr}\n"
        f"returncode={result.returncode}"
    )

    after = capability_module.read_current_capability_state()

    assert after == before

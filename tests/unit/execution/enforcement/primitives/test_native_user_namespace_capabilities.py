from __future__ import annotations

import subprocess
import sys

import pytest

from lyrion.execution.backends.linux.enforcement.primitives import (
    native_user_namespace_capabilities as capability_module,
)


def test_capability_hex_parser() -> None:
    assert capability_module._parse_hex_capability_set("0") == frozenset()
    assert capability_module._parse_hex_capability_set("1") == frozenset({0})
    assert capability_module._parse_hex_capability_set("3") == frozenset({0, 1})
    assert capability_module._parse_hex_capability_set(
        "200000"
    ) == frozenset({21})


def test_current_parent_capability_state_is_observable() -> None:
    state = capability_module.read_current_capability_state()

    assert isinstance(state.inheritable, frozenset)
    assert isinstance(state.permitted, frozenset)
    assert isinstance(state.effective, frozenset)
    assert isinstance(state.bounding, frozenset)
    assert isinstance(state.ambient, frozenset)


def test_capability_verifier_rejects_missing_cap_sys_admin() -> None:
    state = capability_module.UserNamespaceCapabilityState(
        inheritable=frozenset(),
        permitted=frozenset(),
        effective=frozenset(),
        bounding=frozenset(),
        ambient=frozenset(),
    )

    with pytest.raises(
        capability_module.UserNamespaceCapabilityError,
        match="CAP_SYS_ADMIN",
    ):
        capability_module.verify_namespace_local_capability_state(state)


def test_disposable_user_namespace_gets_namespace_local_capabilities() -> None:
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

    print("CAP_INH:", fields["CapInh"], flush=True)
    print("CAP_PRM:", fields["CapPrm"], flush=True)
    print("CAP_EFF:", fields["CapEff"], flush=True)
    print("CAP_BND:", fields["CapBnd"], flush=True)
    print("CAP_AMB:", fields["CapAmb"], flush=True)
    print("UID:", os.getuid(), flush=True)
    print("GID:", os.getgid(), flush=True)

    effective = int(fields["CapEff"], 16)

    # CAP_SYS_ADMIN = 21.
    if not (effective & (1 << 21)):
        os._exit(12)

    if os.getuid() != 0:
        os._exit(13)

    if os.getgid() != 0:
        os._exit(14)

    os._exit(0)

os.close(ready_write)
os.close(mapped_read)

ready = os.read(ready_read, 32)

if not ready.startswith(b"READY"):
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
            "namespace-local capability qualification failed:\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}\n"
            f"returncode={result.returncode}"
        )

    assert "UID: 0" in result.stdout
    assert "GID: 0" in result.stdout

    effective_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("CAP_EFF:")
    )

    effective = int(effective_line.split(":", 1)[1].strip(), 16)

    assert effective & (1 << 21)

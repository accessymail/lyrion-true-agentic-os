"""Native Linux user-namespace qualification primitives."""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from typing import Final

CLONE_NEWUSER: Final[int] = 0x10000000


class NativeUserNamespaceError(RuntimeError):
    """Raised when user-namespace qualification fails."""


@dataclass(frozen=True, slots=True)
class UserNamespaceMapping:
    """Single-range UID/GID mapping."""

    host_uid: int
    namespace_uid: int
    uid_count: int
    host_gid: int
    namespace_gid: int
    gid_count: int

    def __post_init__(self) -> None:
        values = (
            self.host_uid,
            self.namespace_uid,
            self.uid_count,
            self.host_gid,
            self.namespace_gid,
            self.gid_count,
        )

        if any(value < 0 for value in values):
            raise ValueError("mapping values must not be negative")

        if self.uid_count <= 0 or self.gid_count <= 0:
            raise ValueError("mapping counts must be greater than zero")


def _unshare_user_namespace() -> None:
    libc = ctypes.CDLL(None, use_errno=True)

    unshare = libc.unshare
    unshare.argtypes = [ctypes.c_int]
    unshare.restype = ctypes.c_int

    if unshare(CLONE_NEWUSER) != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            f"unshare(CLONE_NEWUSER) failed: "
            f"{os.strerror(error_number)}",
        )


def _write_proc_file(path: str, value: str) -> None:
    if not path:
        raise ValueError("proc path must not be empty")

    fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC)

    try:
        data = value.encode("ascii")
        written = os.write(fd, data)

        if written != len(data):
            raise NativeUserNamespaceError(
                f"short write to {path}"
            )
    finally:
        os.close(fd)


def write_uid_mapping(
    pid: int,
    mapping: UserNamespaceMapping,
) -> None:
    if pid <= 0:
        raise ValueError("pid must be greater than zero")

    _write_proc_file(
        f"/proc/{pid}/uid_map",
        f"{mapping.namespace_uid} "
        f"{mapping.host_uid} "
        f"{mapping.uid_count}\n",
    )


def deny_setgroups(pid: int) -> None:
    if pid <= 0:
        raise ValueError("pid must be greater than zero")

    _write_proc_file(
        f"/proc/{pid}/setgroups",
        "deny\n",
    )


def write_gid_mapping(
    pid: int,
    mapping: UserNamespaceMapping,
) -> None:
    if pid <= 0:
        raise ValueError("pid must be greater than zero")

    _write_proc_file(
        f"/proc/{pid}/gid_map",
        f"{mapping.namespace_gid} "
        f"{mapping.host_gid} "
        f"{mapping.gid_count}\n",
    )


def read_mapping_file(pid: int, filename: str) -> str:
    if pid <= 0:
        raise ValueError("pid must be greater than zero")

    if filename not in {"uid_map", "gid_map", "setgroups"}:
        raise ValueError("unsupported mapping file")

    with open(
        f"/proc/{pid}/{filename}",
        encoding="ascii",
    ) as handle:
        return handle.read()


def establish_mapping(
    pid: int,
    mapping: UserNamespaceMapping,
) -> None:
    """Install UID/GID mapping in the required order."""
    write_uid_mapping(pid, mapping)
    deny_setgroups(pid)
    write_gid_mapping(pid, mapping)


def verify_mapping(
    pid: int,
    mapping: UserNamespaceMapping,
) -> bool:
    expected_uid = (
        f"{mapping.namespace_uid} "
        f"{mapping.host_uid} "
        f"{mapping.uid_count}"
    )

    expected_gid = (
        f"{mapping.namespace_gid} "
        f"{mapping.host_gid} "
        f"{mapping.gid_count}"
    )

    return (
        read_mapping_file(pid, "uid_map").strip() == expected_uid
        and read_mapping_file(pid, "gid_map").strip() == expected_gid
    )


__all__ = [
    "CLONE_NEWUSER",
    "NativeUserNamespaceError",
    "UserNamespaceMapping",
    "deny_setgroups",
    "establish_mapping",
    "read_mapping_file",
    "verify_mapping",
    "write_gid_mapping",
    "write_uid_mapping",
]

"""Read-only user-namespace identity qualification helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class UserNamespaceIdentityError(RuntimeError):
    """Raised when user-namespace identity validation fails."""


@dataclass(frozen=True, slots=True)
class UserNamespaceIdentity:
    """Kernel namespace identity observed from /proc."""

    inode: int


def read_user_namespace_identity(
    proc_namespace_path: Path = Path("/proc/self/ns/user"),
) -> UserNamespaceIdentity:
    """Read the kernel user-namespace inode without mutation."""
    try:
        target = os.readlink(proc_namespace_path)
    except OSError as exc:
        raise UserNamespaceIdentityError(
            f"unable to read user namespace identity: {exc}"
        ) from exc

    prefix = "user:["
    suffix = "]"

    if not target.startswith(prefix) or not target.endswith(suffix):
        raise UserNamespaceIdentityError(
            f"unexpected user namespace identity: {target!r}"
        )

    value = target[len(prefix) : -len(suffix)]

    try:
        inode = int(value, 10)
    except ValueError as exc:
        raise UserNamespaceIdentityError(
            f"invalid user namespace inode: {value!r}"
        ) from exc

    if inode <= 0:
        raise UserNamespaceIdentityError(
            f"invalid user namespace inode: {inode}"
        )

    return UserNamespaceIdentity(inode=inode)


def verify_namespace_isolation(
    parent: UserNamespaceIdentity,
    child: UserNamespaceIdentity,
) -> None:
    """Require parent and child to belong to different user namespaces."""
    if parent.inode == child.inode:
        raise UserNamespaceIdentityError(
            "parent and child share the same user namespace"
        )


def read_mapping(path: Path) -> str:
    """Read a namespace UID/GID mapping without modifying it."""
    try:
        value = path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise UserNamespaceIdentityError(
            f"unable to read namespace mapping {path}: {exc}"
        ) from exc

    if not value:
        raise UserNamespaceIdentityError(
            f"namespace mapping is empty: {path}"
        )

    return value


def verify_single_identity_mapping(
    mapping: str,
    *,
    namespace_id: int,
    host_id: int,
) -> None:
    """Verify the exact one-entry namespace-to-host mapping."""
    expected = f"0 {host_id} 1"

    if mapping != expected:
        raise UserNamespaceIdentityError(
            f"unexpected namespace mapping for {namespace_id}: "
            f"{mapping!r}; expected {expected!r}"
        )

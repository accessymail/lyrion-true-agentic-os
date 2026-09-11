"""Native Linux namespace primitives for disposable child processes.

Security invariants:
- Namespace mutation MUST occur only inside a disposable child process.
- This module MUST NOT mutate the LYRION controller process.
- Native operations use Linux unshare(2).
- Namespace verification observes /proc/self/ns independently.
- PID namespaces are treated specially because CLONE_NEWPID affects
  subsequently created children rather than converting the caller into PID 1.
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from typing import Final


class NativeNamespaceError(RuntimeError):
    """Raised when a native namespace operation cannot be performed."""


# Linux namespace flags from Linux UAPI <sched.h>.
CLONE_NEWNS: Final[int] = 0x00020000
CLONE_NEWPID: Final[int] = 0x20000000
CLONE_NEWNET: Final[int] = 0x40000000


@dataclass(frozen=True, slots=True)
class NativeNamespaceState:
    """Observed namespace identities for the current process."""

    process_namespace: str
    mount_namespace: str
    network_namespace: str


class _LibC:
    """Minimal libc boundary for Linux namespace operations."""

    def __init__(self) -> None:
        try:
            libc = ctypes.CDLL(None, use_errno=True)
        except OSError as exc:
            raise NativeNamespaceError(
                "unable to load libc"
            ) from exc

        unshare = libc.unshare
        unshare.argtypes = [ctypes.c_int]
        unshare.restype = ctypes.c_int

        self._unshare = unshare

    def unshare(self, flags: int) -> None:
        if flags <= 0:
            raise ValueError("namespace flags must be greater than zero")

        if self._unshare(flags) != 0:
            error_number = ctypes.get_errno()
            message = os.strerror(error_number)
            raise OSError(error_number, f"unshare failed: {message}")


def _namespace_identity(name: str) -> str:
    """Return the kernel namespace identity from /proc."""
    if not name:
        raise ValueError("namespace name must not be empty")

    try:
        identity = os.readlink(f"/proc/self/ns/{name}")
    except OSError as exc:
        raise NativeNamespaceError(
            f"unable to observe {name} namespace"
        ) from exc

    if not identity:
        raise NativeNamespaceError(
            f"empty {name} namespace identity"
        )

    return identity


def observe_current_namespaces() -> NativeNamespaceState:
    """Independently observe current process namespace identities."""
    return NativeNamespaceState(
        process_namespace=_namespace_identity("pid"),
        mount_namespace=_namespace_identity("mnt"),
        network_namespace=_namespace_identity("net"),
    )


class NativeChildNamespaceOperations:
    """Native namespace operations for a disposable Linux child.

    The caller MUST ensure this object executes in the child execution
    context rather than the LYRION controller.
    """

    @staticmethod
    def _require_child_context() -> None:
        pid = os.getpid()

        if pid <= 0:
            raise NativeNamespaceError("invalid process identity")

        try:
            pgid = os.getpgid(pid)
        except OSError as exc:
            raise NativeNamespaceError(
                "unable to obtain process-group identity"
            ) from exc

        if pgid <= 0:
            raise NativeNamespaceError(
                "invalid process-group identity"
            )

    def __init__(self) -> None:
        self._libc = _LibC()

    def isolate_mount(self) -> None:
        """Create a mount namespace for the current child."""
        self._require_child_context()
        self._libc.unshare(CLONE_NEWNS)

    def isolate_network(self) -> None:
        """Create a network namespace for the current child."""
        self._require_child_context()
        self._libc.unshare(CLONE_NEWNET)

    def isolate_process_for_future_child(self) -> None:
        """Prepare a PID namespace for a subsequently created child.

        Linux does not move the caller into the new PID namespace when
        unshare(CLONE_NEWPID) succeeds. A subsequently created child is
        placed into that namespace.
        """
        self._require_child_context()
        self._libc.unshare(CLONE_NEWPID)

    def observe(self) -> NativeNamespaceState:
        """Observe namespace state independently."""
        self._require_child_context()
        return observe_current_namespaces()


def namespace_identity_changed(
    before: NativeNamespaceState,
    after: NativeNamespaceState,
    *,
    process: bool,
    mount: bool,
    network: bool,
) -> bool:
    """Return True only when every requested identity changed."""
    if process and before.process_namespace == after.process_namespace:
        return False

    if mount and before.mount_namespace == after.mount_namespace:
        return False

    if network and before.network_namespace == after.network_namespace:
        return False

    return True


__all__ = [
    "CLONE_NEWNS",
    "CLONE_NEWNET",
    "CLONE_NEWPID",
    "NativeChildNamespaceOperations",
    "NativeNamespaceError",
    "NativeNamespaceState",
    "namespace_identity_changed",
    "observe_current_namespaces",
]

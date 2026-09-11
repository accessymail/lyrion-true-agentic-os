"""Read-only qualification helpers for user-namespace-local capabilities.

This module intentionally performs observation only.

It does not:
- mutate the current process capability state,
- change the capability bounding set,
- modify host security policy,
- grant capabilities to the parent process,
- invoke privileged helpers.

Capability observations are obtained independently from /proc/self/status
inside the disposable qualification child.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class UserNamespaceCapabilityError(RuntimeError):
    """Raised when capability-state qualification cannot be completed."""


@dataclass(frozen=True, slots=True)
class UserNamespaceCapabilityState:
    """Capability state observed from /proc/self/status."""

    inheritable: frozenset[int]
    permitted: frozenset[int]
    effective: frozenset[int]
    bounding: frozenset[int]
    ambient: frozenset[int]

    @property
    def has_cap_sys_admin(self) -> bool:
        """Return whether CAP_SYS_ADMIN (capability 21) is effective."""
        return 21 in self.effective


def _parse_hex_capability_set(value: str) -> frozenset[int]:
    """Decode Linux /proc capability hexadecimal representation."""
    normalized = value.strip()

    if not normalized:
        raise UserNamespaceCapabilityError(
            "empty capability value"
        )

    try:
        integer_value = int(normalized, 16)
    except ValueError as exc:
        raise UserNamespaceCapabilityError(
            f"invalid capability value: {normalized!r}"
        ) from exc

    capabilities = {
        bit
        for bit in range(integer_value.bit_length())
        if integer_value & (1 << bit)
    }

    return frozenset(capabilities)


def _read_status_value(
    status_path: Path,
    field_name: str,
) -> frozenset[int]:
    """Read and decode one capability field from proc status."""
    try:
        lines = status_path.read_text(encoding="ascii").splitlines()
    except OSError as exc:
        raise UserNamespaceCapabilityError(
            f"unable to read {status_path}: {exc}"
        ) from exc

    prefix = f"{field_name}:"

    for line in lines:
        if line.startswith(prefix):
            _, value = line.split(":", 1)
            return _parse_hex_capability_set(value)

    raise UserNamespaceCapabilityError(
        f"missing capability field {field_name!r} "
        f"in {status_path}"
    )


def read_current_capability_state(
    status_path: Path = Path("/proc/self/status"),
) -> UserNamespaceCapabilityState:
    """Read the current process capability state without mutation."""
    return UserNamespaceCapabilityState(
        inheritable=_read_status_value(status_path, "CapInh"),
        permitted=_read_status_value(status_path, "CapPrm"),
        effective=_read_status_value(status_path, "CapEff"),
        bounding=_read_status_value(status_path, "CapBnd"),
        ambient=_read_status_value(status_path, "CapAmb"),
    )


def verify_namespace_local_capability_state(
    state: UserNamespaceCapabilityState,
) -> None:
    """Validate the minimum C3.3 namespace-local capability invariant.

    A process that successfully creates a user namespace is expected to
    receive capabilities in that new namespace. CAP_SYS_ADMIN is used as
    the qualification sentinel because it is not effective for the
    unprivileged parent on the qualification host.

    This function only evaluates already-observed state.
    """
    if not state.has_cap_sys_admin:
        raise UserNamespaceCapabilityError(
            "CAP_SYS_ADMIN is not effective in the new user namespace"
        )

    if not state.effective.issubset(state.permitted):
        raise UserNamespaceCapabilityError(
            "effective capability set is not a subset of permitted set"
        )

    if not state.permitted.issubset(state.bounding):
        raise UserNamespaceCapabilityError(
            "permitted capability set exceeds capability bounding set"
        )

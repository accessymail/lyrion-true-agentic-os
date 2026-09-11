"""Diagnostic qualification for native Linux capability bounding-set operations.

This test is READ-ONLY with respect to the capability state.

It does not:
- acquire privileges
- invoke sudo
- call capset()
- call PR_CAPBSET_DROP
- modify host security state

It only records the current process capability state and verifies the
kernel-facing capability ABI information used by the native adapter.
"""

from __future__ import annotations

import os
import platform
import sys


def _read_proc_status() -> dict[str, str]:
    """Read capability fields directly from /proc/self/status."""
    fields = {
        "CapInh",
        "CapPrm",
        "CapEff",
        "CapBnd",
        "CapAmb",
        "NoNewPrivs",
    }

    result: dict[str, str] = {}

    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            key, separator, value = line.partition(":")
            if separator and key in fields:
                result[key] = value.strip()

    return result


def _decode_capability_mask(value: str) -> list[int]:
    """Decode a Linux hexadecimal capability mask into capability IDs."""
    mask = int(value, 16)

    capabilities: list[int] = []
    capability = 0

    while mask:
        if mask & 1:
            capabilities.append(capability)
        mask >>= 1
        capability += 1

    return capabilities


def test_native_capability_diagnostic() -> None:
    """Capture the exact native capability state of this process."""
    status = _read_proc_status()

    required = {
        "CapInh",
        "CapPrm",
        "CapEff",
        "CapBnd",
        "CapAmb",
        "NoNewPrivs",
    }

    assert set(status) == required, (
        "Incomplete /proc/self/status capability information: "
        f"{status}"
    )

    print("\n=== LYRION Native Capability Diagnostic ===")
    print(f"PID:              {os.getpid()}")
    print(f"UID:              {os.getuid()}")
    print(f"EUID:             {os.geteuid()}")
    print(f"Python:           {sys.version.split()[0]}")
    print(f"Kernel:           {platform.release()}")
    print(f"Architecture:     {platform.machine()}")

    print("\n/proc/self/status:")
    for field in (
        "CapInh",
        "CapPrm",
        "CapEff",
        "CapBnd",
        "CapAmb",
        "NoNewPrivs",
    ):
        print(f"{field}: {status[field]}")

    print("\nDecoded capability sets:")

    for field in (
        "CapInh",
        "CapPrm",
        "CapEff",
        "CapBnd",
        "CapAmb",
    ):
        decoded = _decode_capability_mask(status[field])
        print(f"{field}: {decoded}")

    bounding = _decode_capability_mask(status["CapBnd"])
    effective = _decode_capability_mask(status["CapEff"])
    permitted = _decode_capability_mask(status["CapPrm"])

    print("\nNative reduction prerequisites:")
    print(f"Bounding capabilities present: {bool(bounding)}")
    print(f"Effective capabilities present: {bool(effective)}")
    print(f"Permitted capabilities present: {bool(permitted)}")
    print(f"CAP_SETPCAP (8) effective:     {8 in effective}")
    print(f"CAP_SETPCAP (8) permitted:     {8 in permitted}")

    print("\nExpected interpretation:")

    if bounding and 8 not in effective:
        print(
            "EPERM is expected for PR_CAPBSET_DROP because the "
            "current process does not have CAP_SETPCAP effective."
        )
    elif bounding and 8 in effective:
        print(
            "CAP_SETPCAP is effective; this environment may be suitable "
            "for an explicitly authorized positive transition qualification."
        )
    else:
        print(
            "No bounding capabilities are available; positive bounding-set "
            "reduction cannot be demonstrated in this process."
        )

    print("=== End Diagnostic ===")

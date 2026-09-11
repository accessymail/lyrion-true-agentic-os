#!/usr/bin/env python3
"""Check the local LYRION G47 certification gate state.

This is a read-only fail-closed gate check.
It does not claim certification and does not modify project files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "docs/g47/sources"


def main() -> int:
    source_files = sorted(
        path
        for path in SOURCE_DIR.glob("*.json")
        if path.is_file() and not path.is_symlink()
    )

    g46_candidates = [
        path
        for path in source_files
        if "g46" in path.name.lower()
    ]

    g47_candidates = [
        path
        for path in source_files
        if "g47" in path.name.lower()
    ]

    print("LYRION G47 certification gate status")
    print("====================================")
    print()

    if len(g46_candidates) != 1:
        print(
            "G46.5 authoritative source: NOT READY",
            file=sys.stderr,
        )
        print(
            f"Expected exactly 1 local G46.5 source; found "
            f"{len(g46_candidates)}.",
            file=sys.stderr,
        )
        return 2

    if len(g47_candidates) != 1:
        print(
            "G47 authoritative source: NOT READY",
            file=sys.stderr,
        )
        print(
            f"Expected exactly 1 local G47 source; found "
            f"{len(g47_candidates)}.",
            file=sys.stderr,
        )
        return 2

    for label, path in (
        ("G46.5", g46_candidates[0]),
        ("G47", g47_candidates[0]),
    ):
        try:
            with path.open("r", encoding="utf-8") as handle:
                json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"{label} source validation: FAIL: {exc}",
                file=sys.stderr,
            )
            return 1

    print("G46.5 authoritative source: PRESENT")
    print(f"  {g46_candidates[0]}")
    print("G47 authoritative source: PRESENT")
    print(f"  {g47_candidates[0]}")
    print()
    print("Local source gate: READY")
    print()
    print(
        "NOTE: This does NOT constitute G47 certification. "
        "External, operational, and independent evidence must still "
        "satisfy the authoritative G47 acceptance criteria."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

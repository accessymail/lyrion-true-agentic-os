#!/usr/bin/env python3
"""Discover local authoritative LYRION G46.5/G47 source artifacts.

Read-only utility.
It searches explicitly supplied roots and common project locations.
It never creates, modifies, copies, or transforms source artifacts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

G46_PATTERNS = (
    "*G46*",
    "*g46*",
)

G47_PATTERNS = (
    "*G47*",
    "*g47*",
)


def find_candidates(root: Path, patterns: tuple[str, ...]) -> set[Path]:
    results: set[Path] = set()

    if not root.exists() or not root.is_dir():
        return results

    for pattern in patterns:
        try:
            results.update(
                path
                for path in root.rglob(pattern)
                if path.is_file()
            )
        except PermissionError:
            continue

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover local LYRION G46.5/G47 source artifacts."
    )
    parser.add_argument(
        "roots",
        nargs="*",
        type=Path,
        help="Directories to search.",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]

    roots = args.roots or (
        project_root,
        project_root.parent,
        Path("/mnt/c"),
    )

    g46: set[Path] = set()
    g47: set[Path] = set()

    for root in roots:
        g46.update(find_candidates(root, G46_PATTERNS))
        g47.update(find_candidates(root, G47_PATTERNS))

    project = project_root.resolve()

    g46 = {
        path.resolve()
        for path in g46
        if path.resolve() != project
    }
    g47 = {
        path.resolve()
        for path in g47
        if path.resolve() != project
    }

    print("LYRION authoritative-source discovery")
    print("======================================")
    print()
    print("G46 candidates:")

    for path in sorted(g46):
        print(f"  {path}")

    if not g46:
        print("  NONE")

    print()
    print("G47 candidates:")

    for path in sorted(g47):
        print(f"  {path}")

    if not g47:
        print("  NONE")

    print()

    if not g46 or not g47:
        print("Discovery status: INCOMPLETE")
        print("No source files were created or modified.")
        return 2

    print("Discovery status: CANDIDATES FOUND")
    print("No source files were created or modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

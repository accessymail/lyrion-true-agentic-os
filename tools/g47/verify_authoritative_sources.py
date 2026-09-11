#!/usr/bin/env python3
"""Verify authoritative G46.5/G47 source artifacts.

This utility performs read-only provenance and structural checks.
It does not modify source documents and does not claim certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"Source file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_requirement_list(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise ValueError("G46.5 source root must be a JSON object.")

    candidates = (
        "requirements",
        "requirement_registry",
        "requirement_catalog",
    )

    for key in candidates:
        value = document.get(key)

        if isinstance(value, list) and all(
            isinstance(item, dict) for item in value
        ):
            return value

    raise ValueError(
        "Could not locate a supported G46.5 requirement list. "
        "No source transformation was attempted."
    )


def find_g47_list(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise ValueError("G47 source root must be a JSON object.")

    candidates = (
        "items",
        "obligations",
        "requirements",
    )

    for key in candidates:
        value = document.get(key)

        if isinstance(value, list) and all(
            isinstance(item, dict) for item in value
        ):
            return value

    raise ValueError(
        "Could not locate a supported G47 obligation list. "
        "No source transformation was attempted."
    )


def validate_ids(
    items: list[dict[str, Any]],
    label: str,
) -> set[str]:
    ids: set[str] = set()

    for index, item in enumerate(items):
        requirement_id = item.get("requirement_id")

        if not isinstance(requirement_id, str) or not requirement_id:
            raise ValueError(
                f"{label}[{index}] has no valid requirement_id."
            )

        if requirement_id in ids:
            raise ValueError(
                f"{label} contains duplicate requirement_id: "
                f"{requirement_id}"
            )

        ids.add(requirement_id)

    return ids


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify authoritative LYRION G46.5/G47 sources."
    )
    parser.add_argument("--g46-5", required=True, type=Path)
    parser.add_argument("--g47", required=True, type=Path)

    args = parser.parse_args()

    try:
        g46_document = load_json(args.g46_5)
        g47_document = load_json(args.g47)

        g46_requirements = find_requirement_list(g46_document)
        g47_items = find_g47_list(g47_document)

        g46_ids = validate_ids(
            g46_requirements,
            "G46.5 requirements",
        )
        g47_ids = validate_ids(
            g47_items,
            "G47 obligations",
        )

        if len(g46_requirements) != 62:
            raise ValueError(
                f"G46.5 expected 62 requirements; "
                f"found {len(g46_requirements)}."
            )

        if len(g47_items) != 42:
            raise ValueError(
                f"G47 expected 42 obligations; "
                f"found {len(g47_items)}."
            )

        orphan_ids = g47_ids - g46_ids

        if orphan_ids:
            raise ValueError(
                "G47 contains IDs absent from G46.5: "
                + ", ".join(sorted(orphan_ids))
            )

        print("Authoritative source verification: PASS")
        print(f"G46.5 requirements: {len(g46_requirements)}")
        print(f"G47 obligations: {len(g47_items)}")
        print(f"G47 IDs present in G46.5: {len(g47_ids)}")
        print()
        print("SHA-256")
        print(f"G46.5: {sha256_file(args.g46_5)}")
        print(f"G47:   {sha256_file(args.g47)}")

        return 0

    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"Authoritative source verification: FAIL: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

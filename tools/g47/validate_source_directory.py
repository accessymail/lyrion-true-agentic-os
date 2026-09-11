#!/usr/bin/env python3
"""Validate the LYRION G47 authoritative-source directory.

This module performs read-only structural validation of
``docs/g47/sources``. It deliberately does not create, modify, infer,
or certify authoritative G46.5/G47 requirements.

Exit codes:
    0: READY or NOT_READY (directory is structurally safe)
    1: INVALID source directory
    2: invalid invocation/configuration
"""

from __future__ import annotations

import argparse
import json
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_SOURCE_DIRECTORY = Path("docs/g47/sources")

G46_5_TOKENS = ("g46.5", "g46_5", "g465")
G47_TOKENS = ("g47",)

ALLOWED_SUFFIX = ".json"


@dataclass(frozen=True)
class SourceRecord:
    """Description of one candidate authoritative source."""

    path: Path
    category: str
    sha256: str | None = None


class SourceDirectoryError(RuntimeError):
    """Raised when the source directory violates a safety invariant."""


def _is_symlink(path: Path) -> bool:
    """Return whether *path* is a symbolic link without following it."""
    try:
        return path.is_symlink()
    except OSError as exc:
        raise SourceDirectoryError(
            f"unable to inspect symlink state: {path}: {exc}"
        ) from exc


def _classify_name(path: Path) -> str | None:
    """Classify a JSON filename as G46.5 or G47 when unambiguous."""
    normalized = path.stem.lower().replace("-", "_")

    matches_g46_5 = any(token in normalized for token in G46_5_TOKENS)
    matches_g47 = any(token in normalized for token in G47_TOKENS)

    if matches_g46_5 and matches_g47:
        raise SourceDirectoryError(
            f"ambiguous authoritative-source filename: {path.name}"
        )

    if matches_g46_5:
        return "G46.5"

    if matches_g47:
        return "G47"

    return None


def _validate_regular_file(path: Path) -> None:
    """Reject symlinks, special files, and non-regular files."""
    if _is_symlink(path):
        raise SourceDirectoryError(f"symlink is not permitted: {path}")

    try:
        mode = path.stat(follow_symlinks=False).st_mode
    except OSError as exc:
        raise SourceDirectoryError(
            f"unable to stat source: {path}: {exc}"
        ) from exc

    if not stat.S_ISREG(mode):
        raise SourceDirectoryError(f"non-regular file is not permitted: {path}")


def _load_json(path: Path) -> Any:
    """Parse JSON using strict UTF-8 decoding."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SourceDirectoryError(
            f"unable to read source: {path}: {exc}"
        ) from exc

    if not raw:
        raise SourceDirectoryError(f"empty JSON source: {path}")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceDirectoryError(
            f"source is not valid UTF-8: {path}"
        ) from exc

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceDirectoryError(
            f"invalid JSON in {path}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc


def _validate_json_root(path: Path, value: Any) -> None:
    """Ensure the source has a JSON object/array root.

    Schema validation belongs to the authoritative-source verifier and is
    intentionally not duplicated here.
    """
    if not isinstance(value, (dict, list)):
        raise SourceDirectoryError(
            f"JSON root must be an object or array: {path}"
        )


def inspect_source_directory(directory: Path) -> tuple[list[SourceRecord], list[str]]:
    """Inspect the directory without modifying it."""
    if not directory.exists():
        return [], ["directory absent"]

    if _is_symlink(directory):
        raise SourceDirectoryError(
            f"source directory must not be a symlink: {directory}"
        )

    if not directory.is_dir():
        raise SourceDirectoryError(
            f"source path is not a directory: {directory}"
        )

    try:
        entries = sorted(
            directory.iterdir(),
            key=lambda item: item.name,
        )
    except OSError as exc:
        raise SourceDirectoryError(
            f"unable to enumerate source directory: {directory}: {exc}"
        ) from exc

    records: list[SourceRecord] = []
    warnings: list[str] = []

    for entry in entries:
        if _is_symlink(entry):
            raise SourceDirectoryError(
                f"symlink is not permitted in source directory: {entry.name}"
            )

        if entry.is_dir():
            raise SourceDirectoryError(
                f"nested directory is not permitted: {entry.name}"
            )

        _validate_regular_file(entry)

        if entry.suffix.lower() != ALLOWED_SUFFIX:
            warnings.append(f"ignored non-JSON file: {entry.name}")
            continue

        category = _classify_name(entry)

        if category is None:
            warnings.append(
                f"JSON source has no recognized G46.5/G47 filename marker: "
                f"{entry.name}"
            )
            continue

        value = _load_json(entry)
        _validate_json_root(entry, value)

        records.append(SourceRecord(path=entry, category=category))

    return records, warnings


def validate_complete_source_set(records: list[SourceRecord]) -> None:
    """Require exactly one source for each authoritative category."""
    by_category: dict[str, list[SourceRecord]] = {
        "G46.5": [],
        "G47": [],
    }

    for record in records:
        by_category[record.category].append(record)

    for category in ("G46.5", "G47"):
        matches = by_category[category]

        if len(matches) > 1:
            names = ", ".join(item.path.name for item in matches)
            raise SourceDirectoryError(
                f"duplicate {category} authoritative sources: {names}"
            )


def build_result(directory: Path) -> int:
    """Inspect and print deterministic validation status."""
    records, warnings = inspect_source_directory(directory)

    g46_5 = [item for item in records if item.category == "G46.5"]
    g47 = [item for item in records if item.category == "G47"]

    validate_complete_source_set(records)

    print("LYRION G47 authoritative-source directory validation")
    print("=" * 55)
    print(f"Directory: {directory}")
    print(f"JSON sources recognized: {len(records)}")
    print(f"G46.5 sources: {len(g46_5)}")
    print(f"G47 sources: {len(g47)}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"- {warning}")

    print("\nSources:")
    if not records:
        print("- none")

    for record in records:
        print(f"- {record.category}: {record.path}")

    if not records:
        print("\nRESULT: NOT_READY")
        print("Reason: no authoritative JSON sources are present.")
        return 0

    if not g46_5:
        print("\nRESULT: NOT_READY")
        print("Reason: G46.5 authoritative source is missing.")
        return 0

    if not g47:
        print("\nRESULT: NOT_READY")
        print("Reason: G47 authoritative source is missing.")
        return 0

    print("\nRESULT: READY")
    print("Structural source-directory validation passed.")
    print("NOTE: READY does not mean G47 certification.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate the LYRION G47 authoritative-source directory."
    )
    parser.add_argument(
        "--source-directory",
        type=Path,
        default=DEFAULT_SOURCE_DIRECTORY,
        help=f"source directory (default: {DEFAULT_SOURCE_DIRECTORY})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Program entry point."""
    args = parse_args(argv)

    try:
        directory = args.source_directory.resolve(strict=False)
        return build_result(directory)
    except SourceDirectoryError as exc:
        print(f"RESULT: INVALID\nReason: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"RESULT: INVALID\nReason: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

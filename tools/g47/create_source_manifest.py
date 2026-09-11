#!/usr/bin/env python3
"""Create a deterministic SHA-256 manifest for G46.5/G47 source artifacts.

This utility is read-only with respect to source files.
It does not claim certification and does not modify source artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_json_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} is not a regular file: {path}")

    if path.is_symlink():
        raise ValueError(f"{label} must not be a symbolic link: {path}")

    if path.suffix.lower() != ".json":
        raise ValueError(f"{label} must have a .json extension: {path}")

    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a provenance manifest for G46.5/G47 sources."
    )
    parser.add_argument("--g46-5", required=True, type=Path)
    parser.add_argument("--g47", required=True, type=Path)
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    validate_json_file(args.g46_5, "G46.5 source")
    validate_json_file(args.g47, "G47 source")

    records = [
        {
            "artifact": "G46.5",
            "filename": args.g46_5.name,
            "sha256": sha256_file(args.g46_5),
        },
        {
            "artifact": "G47",
            "filename": args.g47.name,
            "sha256": sha256_file(args.g47),
        },
    ]

    records.sort(key=lambda item: item["artifact"])

    manifest = {
        "schema": "lyrion.g47.source-manifest.v1",
        "certification_claim": False,
        "artifacts": records,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(
            f"Refusing to overwrite existing manifest: {args.output}"
        )

    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(
            manifest,
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")

    print("G46.5/G47 source manifest: PASS")

    for record in records:
        print(f"{record['artifact']}: {record['sha256']}")

    print(f"Manifest: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

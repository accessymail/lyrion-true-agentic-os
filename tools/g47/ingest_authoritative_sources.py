#!/usr/bin/env python3
"""Ingest authoritative LYRION G46.5/G47 source artifacts.

The source files must be supplied explicitly by path.

Security/provenance properties:
- Does not download from the network.
- Does not modify the supplied source files.
- Refuses to overwrite an existing destination.
- Requires regular files.
- Records SHA-256 hashes.
- Preserves the source filename.
- Does not claim G47 certification.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_source(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} source not found: {path}")

    if not path.is_file():
        raise ValueError(f"{label} source is not a regular file: {path}")

    if path.is_symlink():
        raise ValueError(f"{label} source must not be a symbolic link: {path}")

    if path.suffix.lower() != ".json":
        raise ValueError(f"{label} source must be a JSON file: {path}")


def ingest(
    source: Path,
    destination_dir: Path,
    label: str,
) -> tuple[Path, str]:
    validate_source(source, label)

    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / source.name

    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing {label} artifact: "
            f"{destination}"
        )

    source_hash = sha256_file(source)

    shutil.copy2(source, destination)

    destination_hash = sha256_file(destination)

    if source_hash != destination_hash:
        destination.unlink(missing_ok=True)
        raise ValueError(
            f"{label} SHA-256 mismatch after ingestion."
        )

    return destination, source_hash


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest authoritative LYRION G46.5/G47 JSON artifacts."
    )
    parser.add_argument("--g46-5", required=True, type=Path)
    parser.add_argument("--g47", required=True, type=Path)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("docs/g47/sources"),
    )

    args = parser.parse_args()

    created: list[Path] = []

    try:
        g46_destination, g46_hash = ingest(
            args.g46_5,
            args.destination,
            "G46.5",
        )
        created.append(g46_destination)

        g47_destination, g47_hash = ingest(
            args.g47,
            args.destination,
            "G47",
        )
        created.append(g47_destination)

        print("Authoritative source ingestion: PASS")
        print()
        print(f"G46.5: {g46_destination}")
        print(f"SHA-256: {g46_hash}")
        print()
        print(f"G47: {g47_destination}")
        print(f"SHA-256: {g47_hash}")
        print()
        print("Source files were copied without modification.")
        print("G47 certification status was not changed.")

        return 0

    except (OSError, ValueError) as exc:
        for created_path in reversed(created):
            try:
                created_path.unlink(missing_ok=True)
            except OSError:
                # Preserve the original failure while reporting rollback
                # failure explicitly below.
                print(
                    "Authoritative source ingestion: ROLLBACK FAILED: "
                    f"{created_path}",
                    file=sys.stderr,
                )

        print(
            f"Authoritative source ingestion: FAIL: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""G47 real-environment preflight and evidence-workspace preparation.

This module prepares an auditable evidence workspace for G47 execution.

Security properties:
- Read-only collection from the host wherever practical.
- No secret collection.
- No privilege escalation.
- No production-state mutation.
- Deterministic SHA-256 inventory of collected artifacts.
- Explicitly does NOT claim G47 certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

TOOL_VERSION: Final[str] = "1.0.0"
SCHEMA_VERSION: Final[str] = "g47-environment-preflight/v1"

DEFAULT_ROOT: Final[str] = ".lyrion-g47-evidence"

# Never collect these classes of files automatically.
FORBIDDEN_NAMES: Final[frozenset[str]] = frozenset(
    {
        ".env",
        ".git",
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
        "id_dsa",
    }
)


@dataclass(frozen=True)
class Artifact:
    """Description of a collected evidence artifact."""

    relative_path: str
    sha256: str
    size_bytes: int


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a regular file."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def run_read_only(
    command: list[str],
    *,
    timeout: float = 10.0,
) -> str:
    """Execute a bounded read-only diagnostic command.

    Commands are supplied as an argument vector rather than a shell string.
    """
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    output = result.stdout.strip()

    if result.returncode != 0:
        stderr = result.stderr.strip()
        return (
            f"returncode={result.returncode}\n"
            f"stdout={output}\n"
            f"stderr={stderr}"
        )

    return output


def safe_name(value: str) -> bool:
    """Return whether a path component is safe for evidence collection."""
    return (
        value not in FORBIDDEN_NAMES
        and value not in {".", ".."}
        and not value.startswith(".env")
    )


def collect_environment_metadata() -> dict[str, object]:
    """Collect non-secret environment and host metadata."""
    metadata: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "collection_epoch_utc": time.time(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
        },
        "hostname": socket.gethostname(),
        "evidence_scope": {
            "host_environment": True,
            "collector_process": True,
            "execution_subject": False,
            "execution_subject_note": (
                "This preflight collector does not execute or inspect a "
                "LYRION execution subject. Execution-subject security "
                "controls must be evidenced by the corresponding "
                "execution-boundary tests."
            ),
        },
        "collector_process": {
            "uid": os.getuid(),
            "euid": os.geteuid(),
            "kernel_release": platform.release(),
        },
        "commands": {
            "uname": run_read_only(["uname", "-a"]),
            "id": run_read_only(["id"]),
            "systemd_detect_virt": run_read_only(
                ["systemd-detect-virt"],
                timeout=5.0,
            ),
        },
        "security": {
            "scope": "collector_process",
            "no_new_privs": run_read_only(
                [
                    "sh",
                    "-c",
                    "grep '^NoNewPrivs:' /proc/self/status || true",
                ]
            ),
            "seccomp": run_read_only(
                [
                    "sh",
                    "-c",
                    "grep '^Seccomp:' /proc/self/status || true",
                ]
            ),
            "capabilities": run_read_only(
                [
                    "sh",
                    "-c",
                    "grep '^Cap' /proc/self/status || true",
                ]
            ),
        },
        "certification": {
            "production_certified": False,
            "statement": (
                "This artifact is environment preflight evidence only. "
                "It is not a G47 or production certification."
            ),
        },
    }

    return metadata


def write_json(path: Path, payload: object) -> None:
    """Write canonical UTF-8 JSON without overwriting an existing file."""
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")

    temporary = path.with_name(f".{path.name}.tmp")

    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def build_inventory(root: Path) -> list[Artifact]:
    """Build a SHA-256 inventory of evidence artifacts."""
    artifacts: list[Artifact] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(root)

        if any(not safe_name(part) for part in relative.parts):
            continue

        if path.is_symlink():
            continue

        if path.name == "SHA256SUMS":
            continue

        artifacts.append(
            Artifact(
                relative_path=relative.as_posix(),
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )

    return artifacts


def write_inventory(root: Path) -> Path:
    """Create the immutable SHA-256 inventory."""
    inventory_path = root / "SHA256SUMS"

    if inventory_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing inventory: {inventory_path}"
        )

    lines = [
        f"{artifact.sha256}  {artifact.relative_path}"
        for artifact in build_inventory(root)
    ]

    temporary = root / ".SHA256SUMS.tmp"

    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        temporary.replace(inventory_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    return inventory_path


def prepare_workspace(root: Path) -> None:
    """Create a new evidence workspace and collect preflight metadata."""
    root = root.resolve()

    if root == Path("/"):
        raise ValueError("Refusing to use filesystem root as evidence workspace.")

    root.mkdir(parents=True, exist_ok=True)

    metadata_path = root / "environment-preflight.json"

    metadata = collect_environment_metadata()
    write_json(metadata_path, metadata)

    inventory = write_inventory(root)

    print("G47 environment preflight: PASS")
    print(f"Evidence workspace: {root}")
    print(f"Metadata: {metadata_path}")
    print(f"SHA-256 inventory: {inventory}")
    print("Production certification: NOT CLAIMED")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Prepare a G47 real-environment evidence workspace."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(DEFAULT_ROOT),
        help=f"Evidence workspace (default: {DEFAULT_ROOT})",
    )
    return parser.parse_args()


def main() -> int:
    """Run the environment preflight."""
    args = parse_args()

    try:
        prepare_workspace(args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"G47 environment preflight: FAIL: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

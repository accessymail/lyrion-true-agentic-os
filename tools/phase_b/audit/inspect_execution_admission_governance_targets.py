#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

TARGETS = [
    Path("docs/phase-b/governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"),
    Path("docs/phase-b/execution-admission/LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"),
    Path("docs/phase-b/governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_MASTER_PLAN_v1.md"),
    Path("docs/phase-b/requirements/LYRION_CORE_PRD_TRACEABILITY_ACCEPTANCE_MATRIX_v1.md"),
    Path("docs/Manifest.md"),
    Path("Manifest.md"),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()


def inspect_file(path: Path) -> None:
    absolute = REPO_ROOT / path

    print("\n" + "=" * 80)
    print(path)
    print("=" * 80)

    if not absolute.is_file():
        print("STATUS: MISSING")
        return

    print("STATUS: PRESENT")
    print("SHA256:", sha256(absolute))

    text = absolute.read_text(
        encoding="utf-8",
        errors="replace",
    )

    lines = text.splitlines()

    patterns = [
        r"execution admission",
        r"execution_admission",
        r"acceptance",
        r"validated",
        r"validation",
        r"phase.?b",
        r"manifest",
        r"authorized",
        r"production",
        r"certification",
        r"G46\.5",
        r"G47",
        r"R097",
    ]

    matches = []

    for number, line in enumerate(lines, start=1):
        lowered = line.lower()

        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.append((number, line))

    print("MATCHED_LINES:", len(matches))

    for number, line in matches[:120]:
        print(f"{number:05d}: {line}")

    if len(matches) > 120:
        print(f"... {len(matches) - 120} additional matches omitted")


def main() -> int:
    print("=" * 80)
    print("LYRION TRUE AGENTIC OS")
    print("EXECUTION ADMISSION GOVERNANCE TARGET INSPECTION")
    print("MODE: READ-ONLY")
    print("=" * 80)

    root = Path(git("rev-parse", "--show-toplevel")).resolve()
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    print("\nREPOSITORY:", root)
    print("HEAD:", head)
    print("ORIGIN/MAIN:", origin)

    if head != origin:
        print("FAIL: HEAD != origin/main")
        return 1

    print("PASS: HEAD == origin/main")

    print("\nWORKTREE:")
    status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    print(status if status else "CLEAN")

    for target in TARGETS:
        inspect_file(target)

    print("\n" + "=" * 80)
    print("TARGET INSPECTION COMPLETE")
    print("=" * 80)

    print("NO FILES MODIFIED")
    print("NO MANIFESTS MODIFIED")
    print("NO DOCUMENTS MODIFIED")
    print("NO GIT MUTATION")
    print("NO COMMIT")
    print("NO PUSH")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

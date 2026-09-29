#!/usr/bin/env python3

"""
LYRION True Agentic OS
Execution Admission Governance Target Discovery

Purpose:
    Discover the exact canonical documentation and manifest targets that
    must be synchronized after formal acceptance of the Execution Admission
    slice.

MODE:
    READ-ONLY / DISCOVERY-ONLY

This tool MUST NOT:
    - modify source
    - modify tests
    - modify documentation
    - modify manifests
    - create acceptance records
    - modify Git
    - commit
    - push
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification

Fail-closed:
    If canonical targets are ambiguous or missing, no synchronization target
    is approved.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

TARGET_TERMS = (
    "manifest",
    "master",
    "checklist",
    "acceptance",
    "validation",
    "platform",
    "phase_b",
    "phase-b",
    "execution",
    "admission",
)

EXCLUDE_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "NOT_USABLE_DOCUMENTS",
}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )

    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def eligible(path: Path) -> bool:
    if not path.is_file():
        return False

    if any(part in EXCLUDE_PARTS for part in path.parts):
        return False

    return path.suffix.lower() in {
        ".md",
        ".markdown",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
    }


def score(path: Path) -> int:
    name = path.name.lower()
    path_text = str(path.relative_to(REPO_ROOT)).lower()

    value = 0

    for term in TARGET_TERMS:
        if term in name:
            value += 5

        if term in path_text:
            value += 1

    return value


def main() -> int:
    failures = 0

    print("=" * 80)
    print("LYRION TRUE AGENTIC OS")
    print("EXECUTION ADMISSION GOVERNANCE TARGET DISCOVERY")
    print("MODE: READ-ONLY / DISCOVERY-ONLY")
    print("=" * 80)

    # ---------------------------------------------------------------
    # 1. Repository identity
    # ---------------------------------------------------------------

    print("\n[1] REPOSITORY IDENTITY")

    root = Path(git("rev-parse", "--show-toplevel")).resolve()
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    print(f"Repository : {root}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")

    if root != REPO_ROOT.resolve():
        print("[FAIL] Repository root mismatch")
        failures += 1

    if head != origin:
        print("[FAIL] HEAD != origin/main")
        failures += 1
    else:
        print("[PASS] HEAD == origin/main")

    # ---------------------------------------------------------------
    # 2. Worktree safety
    # ---------------------------------------------------------------

    print("\n[2] WORKTREE SAFETY")

    status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    if status:
        print("[INFO] Existing worktree entries:")
        print(status)
    else:
        print("[PASS] Worktree clean")

    forbidden = []

    for line in status.splitlines():
        if (
            line.startswith(" M src/")
            or line.startswith("M  src/")
            or line.startswith(" M tests/")
            or line.startswith("M  tests/")
        ):
            forbidden.append(line)

    if forbidden:
        print("[FAIL] Runtime/test modifications detected")
        for item in forbidden:
            print(f"       {item}")
        failures += 1
    else:
        print("[PASS] No src/tests modifications detected")

    # ---------------------------------------------------------------
    # 3. Canonical documentation discovery
    # ---------------------------------------------------------------

    print("\n[3] CANDIDATE DOCUMENTATION TARGETS")

    candidates = []

    for path in REPO_ROOT.rglob("*"):
        if not eligible(path):
            continue

        if score(path) <= 0:
            continue

        candidates.append(path)

    candidates.sort(
        key=lambda p: (-score(p), str(p).lower())
    )

    for path in candidates[:100]:
        print(
            f"[CANDIDATE] score={score(path):02d} "
            f"path={path.relative_to(REPO_ROOT)}"
        )

    if not candidates:
        print("[FAIL] No documentation candidates found")
        failures += 1

    # ---------------------------------------------------------------
    # 4. Strong manifest candidates
    # ---------------------------------------------------------------

    print("\n[4] MANIFEST CANDIDATES")

    manifest_candidates = []

    for path in candidates:
        name = path.name.lower()

        if "manifest" in name:
            manifest_candidates.append(path)

    for path in manifest_candidates:
        print(
            f"[MANIFEST] {path.relative_to(REPO_ROOT)} "
            f"SHA256={sha256(path)}"
        )

    if not manifest_candidates:
        print("[WARN] No repository manifest candidate discovered")

    # ---------------------------------------------------------------
    # 5. Master governance candidates
    # ---------------------------------------------------------------

    print("\n[5] MASTER / GOVERNANCE CANDIDATES")

    governance_candidates = []

    for path in candidates:
        name = path.name.lower()

        if (
            "master" in name
            or "checklist" in name
            or "acceptance" in name
            or "production" in name
        ):
            governance_candidates.append(path)

    for path in governance_candidates:
        print(
            f"[GOVERNANCE] {path.relative_to(REPO_ROOT)} "
            f"SHA256={sha256(path)}"
        )

    # ---------------------------------------------------------------
    # 6. Execution Admission references
    # ---------------------------------------------------------------

    print("\n[6] EXECUTION ADMISSION REFERENCES")

    execution_candidates = []

    for path in REPO_ROOT.rglob("*"):
        if not eligible(path):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        lowered = text.lower()

        if (
            "execution admission" in lowered
            or "execution_admission" in lowered
        ):
            execution_candidates.append(path)

    execution_candidates.sort(
        key=lambda p: str(p).lower()
    )

    for path in execution_candidates:
        print(
            f"[REFERENCE] {path.relative_to(REPO_ROOT)} "
            f"SHA256={sha256(path)}"
        )

    if not execution_candidates:
        print("[WARN] No Execution Admission documentation references found")

    # ---------------------------------------------------------------
    # 7. Repository-owned canonical docs only
    # ---------------------------------------------------------------

    print("\n[7] CANONICAL TARGET SAFETY FILTER")

    canonical_candidates = [
        path
        for path in candidates
        if "docs" in path.relative_to(REPO_ROOT).parts
    ]

    for path in canonical_candidates[:100]:
        print(
            f"[DOCS-CANDIDATE] "
            f"{path.relative_to(REPO_ROOT)}"
        )

    if not canonical_candidates:
        print("[FAIL] No repository-owned docs candidates found")
        failures += 1

    # ---------------------------------------------------------------
    # 8. Acceptance evidence fingerprint
    # ---------------------------------------------------------------

    print("\n[8] ACCEPTANCE EVIDENCE FINGERPRINT")

    evidence_dir = Path(
        "/tmp/lyrion-execution-admission-validation-20260929T103404Z"
    )

    acceptance_review_sha = "UNKNOWN"

    acceptance_script = (
        REPO_ROOT
        / "tools"
        / "phase_b"
        / "audit"
        / "final_acceptance_review_execution_admission.py"
    )

    if acceptance_script.is_file():
        acceptance_review_sha = sha256(acceptance_script)

    print(
        "Acceptance review harness SHA256: "
        f"{acceptance_review_sha}"
    )

    print(
        "Evidence directory: "
        f"{evidence_dir}"
    )

    # ---------------------------------------------------------------
    # 9. Protected boundaries
    # ---------------------------------------------------------------

    print("\n[9] PROTECTED BOUNDARIES")

    print("[PASS] G46.5 reconstruction: NOT PERFORMED")
    print("[PASS] G47 reconstruction: NOT PERFORMED")
    print("[PASS] R097 modification: NOT PERFORMED")
    print("[PASS] Production certification: NOT CLAIMED")
    print("[PASS] Runtime implementation promotion: NOT PERFORMED")

    # ---------------------------------------------------------------
    # 10. Final discovery decision
    # ---------------------------------------------------------------

    print("\n" + "=" * 80)
    print("GOVERNANCE TARGET DISCOVERY RESULT")
    print("=" * 80)

    print(f"FAILURES: {failures}")

    if failures:
        print("\nDecision: GOVERNANCE_TARGET_DISCOVERY_BLOCKED")
        print("Fail-closed.")
        print("No documentation or manifest synchronization target is approved.")
        return 1

    print(
        "\nDecision: GOVERNANCE_TARGETS_DISCOVERED_FOR_REVIEW"
    )

    print(
        "Candidate targets were discovered read-only."
    )

    print(
        "No candidate has been modified or approved automatically."
    )

    print(
        "The next step is to review the exact canonical target list "
        "before synchronization."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

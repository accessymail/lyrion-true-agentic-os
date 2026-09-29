#!/usr/bin/env python3

"""
LYRION True Agentic OS
Final Acceptance Review
Phase-B Repository Baseline Audit Tooling

READ-ONLY / FAIL-CLOSED

Validates only the audit tooling itself.

This script does NOT:
    - modify src/
    - modify tests/
    - modify documentation
    - modify manifests
    - reconstruct G46.5/G47
    - modify R097
    - commit
    - push
    - claim production certification
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

AUDIT_FILE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "audit"
    / "phase_b_repository_baseline_audit.py"
)

VALIDATOR_FILE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "audit"
    / "validate_phase_b_repository_baseline_audit.py"
)

THIS_FILE = Path(__file__).resolve()

ALLOWED_WORKTREE_FILES = {
    AUDIT_FILE.relative_to(REPO_ROOT).as_posix(),
    VALIDATOR_FILE.relative_to(REPO_ROOT).as_posix(),
    THIS_FILE.relative_to(REPO_ROOT).as_posix(),
}


def run(
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def main() -> int:
    passed = 0
    failed = 0

    print("LYRION TRUE AGENTIC OS")
    print("FINAL ACCEPTANCE REVIEW")
    print("PHASE-B REPOSITORY BASELINE AUDIT TOOLING")
    print("READ-ONLY / FAIL-CLOSED")
    print()

    # ------------------------------------------------------------------
    # 1. Required files
    # ------------------------------------------------------------------

    print("=" * 78)
    print("1. REQUIRED AUDIT FILES")
    print("=" * 78)

    for path in (AUDIT_FILE, VALIDATOR_FILE):
        if path.is_file():
            print(f"[PASS] {rel(path)}")
            passed += 1
        else:
            print(f"[FAIL] Missing: {rel(path)}")
            failed += 1

    if failed:
        print()
        print("Decision : FINAL_ACCEPTANCE_BLOCKED")
        return 1

    # ------------------------------------------------------------------
    # 2. Git repository identity
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("2. REPOSITORY IDENTITY")
    print("=" * 78)

    root = run(
        "git",
        "rev-parse",
        "--show-toplevel",
    ).stdout.strip()

    branch = run(
        "git",
        "branch",
        "--show-current",
    ).stdout.strip()

    head = run(
        "git",
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    print(f"Repository : {root}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")

    if Path(root).resolve() == REPO_ROOT.resolve():
        print("[PASS] Repository root")
        passed += 1
    else:
        print("[FAIL] Repository root mismatch")
        failed += 1

    if branch == "main":
        print("[PASS] Branch is main")
        passed += 1
    else:
        print("[FAIL] Branch is not main")
        failed += 1

    # ------------------------------------------------------------------
    # 3. Worktree scope
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("3. WORKTREE SCOPE")
    print("=" * 78)

    status = run(
        "git",
        "status",
        "--short",
        "--untracked-files=all",
    ).stdout.splitlines()

    changed_paths: set[str] = set()

    for line in status:
        if not line.strip():
            continue

        # Git porcelain format:
        # XY path
        value = line[3:].strip()

        # Handle rename notation conservatively.
        if " -> " in value:
            value = value.split(" -> ", 1)[1]

        changed_paths.add(value)

    print(f"Changed paths: {len(changed_paths)}")

    for value in sorted(changed_paths):
        print(f"  {value}")

    unexpected = changed_paths - ALLOWED_WORKTREE_FILES

    if unexpected:
        print("[FAIL] Unexpected worktree files:")
        for value in sorted(unexpected):
            print(f"       {value}")
        failed += 1
    else:
        print("[PASS] Worktree scope is limited to audit tooling")
        passed += 1

    # ------------------------------------------------------------------
    # 4. Audit file hashes
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("4. AUDIT TOOL INTEGRITY")
    print("=" * 78)

    audit_hash = sha256(AUDIT_FILE)
    validator_hash = sha256(VALIDATOR_FILE)

    print(f"{rel(AUDIT_FILE)}")
    print(f"  SHA256: {audit_hash}")

    print(f"{rel(VALIDATOR_FILE)}")
    print(f"  SHA256: {validator_hash}")

    if len(audit_hash) == 64 and len(validator_hash) == 64:
        print("[PASS] SHA-256 integrity values generated")
        passed += 1
    else:
        print("[FAIL] SHA-256 generation failure")
        failed += 1

    # ------------------------------------------------------------------
    # 5. Compile both files
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("5. PYTHON COMPILE VALIDATION")
    print("=" * 78)

    for path in (AUDIT_FILE, VALIDATOR_FILE):
        result = run(
            sys.executable,
            "-m",
            "py_compile",
            str(path),
            check=False,
        )

        if result.returncode == 0:
            print(f"[PASS] {rel(path)}")
            passed += 1
        else:
            print(f"[FAIL] {rel(path)}")
            print(result.stdout)
            print(result.stderr)
            failed += 1

    # ------------------------------------------------------------------
    # 6. Execute Audit v4
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("6. FINAL AUDIT v4 EXECUTION")
    print("=" * 78)

    audit_result = run(
        sys.executable,
        str(AUDIT_FILE),
        check=False,
    )

    print(audit_result.stdout)

    if audit_result.stderr:
        print("STDERR:")
        print(audit_result.stderr)

    required_audit_markers = (
        "PHASE-B REPOSITORY EVIDENCE CLASSIFICATION & TRACEABILITY AUDIT v4",
        "Decision : BASELINE_AUDIT_REQUIRES_REVIEW",
        "FAIL     : 0",
        "Phase-B implementation       : NOT EXECUTED",
        "Production certification     : NOT CLAIMED",
        "G46.5/G47 reconstruction     : NOT PERFORMED",
        "R097 governance change       : NONE",
    )

    audit_ok = (
        all(
            marker in audit_result.stdout
            for marker in required_audit_markers
        )
        and audit_result.returncode in (0, 1)
    )

    if audit_ok:
        print("[PASS] Audit v4 final execution contract")
        passed += 1
    else:
        print("[FAIL] Audit v4 final execution contract")
        failed += 1

    # ------------------------------------------------------------------
    # 7. Execute independent validator
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("7. FINAL INDEPENDENT VALIDATION")
    print("=" * 78)

    validator_result = run(
        sys.executable,
        str(VALIDATOR_FILE),
        check=False,
    )

    print(validator_result.stdout)

    if validator_result.stderr:
        print("STDERR:")
        print(validator_result.stderr)

    required_validator_markers = (
        "PASS :",
        "FAIL : 0",
        "Decision : AUDIT_V4_VALIDATED",
        "Phase-B implementation : NOT EXECUTED",
        "Runtime mutation       : NONE",
        "Documentation mutation : NONE",
        "Manifest mutation      : NONE",
        "Git mutation            : NONE",
        "G46.5/G47 reconstruction: NOT PERFORMED",
        "R097 governance change : NONE",
        "Production certification: NOT CLAIMED",
    )

    validator_ok = (
        validator_result.returncode == 0
        and all(
            marker in validator_result.stdout
            for marker in required_validator_markers
        )
    )

    if validator_ok:
        print("[PASS] Independent validator final execution")
        passed += 1
    else:
        print("[FAIL] Independent validator final execution")
        failed += 1

    # ------------------------------------------------------------------
    # 8. Safety boundary
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("8. FINAL SAFETY BOUNDARY")
    print("=" * 78)

    safety_requirements = {
        "No source implementation": "src/" not in "\n".join(changed_paths),
        "No documentation mutation": not any(
            value.startswith("docs/")
            for value in changed_paths
        ),
        "No manifest mutation": not any(
            "manifest" in value.lower()
            for value in changed_paths
        ),
        "No G47 reconstruction": "G46.5/G47" in audit_result.stdout,
        "No R097 change": "R097 governance change       : NONE"
        in audit_result.stdout,
        "No certification claim": "Production certification     : NOT CLAIMED"
        in audit_result.stdout,
    }

    for name, condition in safety_requirements.items():
        if condition:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            failed += 1

    # ------------------------------------------------------------------
    # 9. Final decision
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("9. FINAL ACCEPTANCE DECISION")
    print("=" * 78)

    print(f"PASS : {passed}")
    print(f"FAIL : {failed}")

    if failed:
        print()
        print("Decision : FINAL_ACCEPTANCE_BLOCKED")
        print()
        print("FAIL-CLOSED:")
        print("  Do NOT commit.")
        print("  Do NOT push.")
        print("  Do NOT begin Phase-B implementation.")
        return 1

    print()
    print("Decision : AUDIT_TOOLING_READY_FOR_COMMIT")
    print()
    print("This result authorizes ONLY the next governance step:")
    print("  Review → Commit → Push → Remote Verification")
    print()
    print("It does NOT authorize:")
    print("  Phase-B implementation")
    print("  Production operation")
    print("  Production certification")
    print("  G46.5/G47 reconstruction")
    print("  R097 modification")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

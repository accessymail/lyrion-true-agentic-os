#!/usr/bin/env python3

"""
LYRION True Agentic OS
Controlled Validation Evidence Review

Slice:
    Execution Admission Boundary

Purpose:
    Independently review the actual controlled-validation evidence produced
    by the bounded Execution Admission validation run.

This tool is READ-ONLY.

It does NOT:
    - execute project tests
    - execute runtime code
    - modify src/
    - modify tests/
    - modify docs/
    - modify manifests
    - modify Git
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification

Evidence requirements:
    1. Actual controlled-validation directory exists.
    2. Complete validation log exists.
    3. Validation summary exists.
    4. Repository baseline is attributable.
    5. HEAD == origin/main.
    6. Expected toolchain is recorded.
    7. All six bounded tests are represented.
    8. Expected pass counts are present.
    9. Runtime hashes before/after are present and identical.
    10. Protected boundaries remain explicitly closed.
    11. No Git commit/push occurred during validation.
    12. Evidence is internally consistent.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

EVIDENCE_DIR = Path(
    "/tmp/lyrion-execution-admission-validation-20260929T103404Z"
)

EXPECTED_HEAD = "7b1f7fd676d32194748d8ba4f603a42edb3cf4cc"

RUNTIME_FILES = (
    "src/lyrion/capabilities/gateway.py",
    "src/lyrion/execution/contracts.py",
    "src/lyrion/execution/validator.py",
    "src/lyrion/execution/executor.py",
)

EXPECTED_HASHES = {
    "src/lyrion/execution/validator.py":
        "1a39ac52d29d2ab27bcfac9788a0aae1b0ddcc85d5ba7105790793a866ad69a8",
    "src/lyrion/execution/executor.py":
        "8c1687dda5defc35d439264ad824de92a8aa20726e144f809b330b90c26efd05",
    "src/lyrion/capabilities/gateway.py":
        "a7ce8f4a00e54f137d559c8c13e9026e50d1b3eafbd8bc3d1029c90d35f19fa9",
    "src/lyrion/execution/contracts.py":
        "ca8af0c9e94789b7e561fc43a32e037c7c1d8aade1eaa73985f3118c7c40def2",
}

EXPECTED_TESTS = (
    "tests/unit/test_capability_gateway.py",
    "tests/unit/test_execution_contracts.py",
    "tests/unit/test_execution_validator.py",
    "tests/unit/test_execution_result_state_integration.py",
    "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
    "tests/unit/execution/test_secure_executor_enforcement_integration.py",
)

EXPECTED_RESULTS = (
    "53 passed in 0.91s",
    "6 passed in 0.39s",
    "27 passed in 0.21s",
)


def run_git(*args: str) -> str:
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def require_text(
    text: str,
    needle: str,
    description: str,
) -> bool:
    if needle in text:
        print(f"[PASS] {description}")
        return True

    print(f"[FAIL] {description}")
    print(f"       Missing: {needle}")
    return False


def parse_hash_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split(None, 1)

        if len(parts) != 2:
            continue

        digest, filename = parts

        if re.fullmatch(r"[0-9a-f]{64}", digest):
            result[filename] = digest

    return result


def main() -> int:
    passed = 0
    failed = 0
    warnings = 0

    def check(condition: bool, description: str) -> None:
        nonlocal passed, failed

        if condition:
            print(f"[PASS] {description}")
            passed += 1
        else:
            print(f"[FAIL] {description}")
            failed += 1

    print("=" * 80)
    print("LYRION TRUE AGENTIC OS")
    print("CONTROLLED VALIDATION EVIDENCE REVIEW")
    print("SLICE: EXECUTION ADMISSION BOUNDARY")
    print("MODE: READ-ONLY")
    print("=" * 80)

    print(f"\nEvidence directory:")
    print(f"  {EVIDENCE_DIR}")

    # ------------------------------------------------------------------
    # 1. Evidence files
    # ------------------------------------------------------------------

    print("\n[1] EVIDENCE ARTIFACTS")

    log_path = EVIDENCE_DIR / "controlled-validation.log"
    summary_path = EVIDENCE_DIR / "validation-summary.txt"
    before_hash_path = EVIDENCE_DIR / "runtime-sha256-before.txt"
    after_hash_path = EVIDENCE_DIR / "runtime-sha256-after.txt"
    baseline_git_path = EVIDENCE_DIR / "baseline-git-state.txt"
    post_git_path = EVIDENCE_DIR / "post-validation-git-state.txt"
    python_path = EVIDENCE_DIR / "python-version.txt"
    pytest_path = EVIDENCE_DIR / "pytest-version.txt"

    evidence_files = (
        log_path,
        summary_path,
        before_hash_path,
        after_hash_path,
        baseline_git_path,
        post_git_path,
        python_path,
        pytest_path,
    )

    for path in evidence_files:
        check(path.is_file(), f"Evidence file exists: {path.name}")

    if failed:
        print("\nDecision: EVIDENCE_REVIEW_BLOCKED")
        return 1

    log = log_path.read_text(encoding="utf-8")
    summary = summary_path.read_text(encoding="utf-8")
    baseline_git = baseline_git_path.read_text(encoding="utf-8")
    post_git = post_git_path.read_text(encoding="utf-8")
    python_version = python_path.read_text(encoding="utf-8").strip()
    pytest_version = pytest_path.read_text(encoding="utf-8").strip()

    # ------------------------------------------------------------------
    # 2. Repository provenance
    # ------------------------------------------------------------------

    print("\n[2] REPOSITORY PROVENANCE")

    check(
        EXPECTED_HEAD in baseline_git,
        "Baseline evidence contains expected HEAD",
    )

    check(
        EXPECTED_HEAD in baseline_git,
        "Baseline evidence contains expected repository revision",
    )

    check(
        EXPECTED_HEAD in post_git,
        "Post-validation evidence contains expected HEAD",
    )

    check(
        EXPECTED_HEAD == run_git("rev-parse", "HEAD"),
        "Current repository HEAD matches validated HEAD",
    )

    check(
        EXPECTED_HEAD == run_git("rev-parse", "origin/main"),
        "Current origin/main matches validated HEAD",
    )

    # ------------------------------------------------------------------
    # 3. Toolchain
    # ------------------------------------------------------------------

    print("\n[3] TOOLCHAIN PROVENANCE")

    check(
        python_version == "Python 3.14.4",
        "Python version is 3.14.4",
    )

    check(
        pytest_version == "pytest 8.4.2",
        "pytest version is 8.4.2",
    )

    # ------------------------------------------------------------------
    # 4. Test scope
    # ------------------------------------------------------------------

    print("\n[4] CONTROLLED TEST SCOPE")

    for test in EXPECTED_TESTS:
        check(
            test in log,
            f"Bounded test appears in execution evidence: {test}",
        )

    # ------------------------------------------------------------------
    # 5. Test outcomes
    # ------------------------------------------------------------------

    print("\n[5] EXECUTED TEST OUTCOMES")

    for result in EXPECTED_RESULTS:
        check(
            result in log,
            f"Expected successful result present: {result}",
        )

    check(
        "53 passed" in log
        and "6 passed" in log
        and "27 passed" in log,
        "All three bounded test groups passed",
    )

    check(
        "failed" not in log.lower(),
        "No failure result is recorded in the execution log",
    )

    # ------------------------------------------------------------------
    # 6. Compilation
    # ------------------------------------------------------------------

    print("\n[6] COMPILATION EVIDENCE")

    for runtime in RUNTIME_FILES:
        check(
            f"[PASS] AST compilation: {runtime}" in log,
            f"Compilation passed: {runtime}",
        )

    # ------------------------------------------------------------------
    # 7. Runtime integrity
    # ------------------------------------------------------------------

    print("\n[7] RUNTIME INTEGRITY")

    before = parse_hash_file(before_hash_path)
    after = parse_hash_file(after_hash_path)

    for runtime, expected_hash in EXPECTED_HASHES.items():
        check(
            before.get(runtime) == expected_hash,
            f"Pre-validation SHA-256 matches baseline: {runtime}",
        )

        check(
            after.get(runtime) == expected_hash,
            f"Post-validation SHA-256 matches baseline: {runtime}",
        )

        check(
            before.get(runtime) == after.get(runtime),
            f"Pre/post SHA-256 identical: {runtime}",
        )

    # ------------------------------------------------------------------
    # 8. Protected boundaries
    # ------------------------------------------------------------------

    print("\n[8] PROTECTED BOUNDARIES")

    check(
        "Production Certification:" in summary
        and "NOT CLAIMED" in summary,
        "Production certification remains unclaimed",
    )

    check(
        "G46.5 Reconstruction:" in summary
        and "NOT PERFORMED" in summary,
        "G46.5 reconstruction was not performed",
    )

    check(
        "G47 Reconstruction:" in summary
        and "NOT PERFORMED" in summary,
        "G47 reconstruction was not performed",
    )

    check(
        "R097 Modification:" in summary
        and "NOT PERFORMED" in summary,
        "R097 was not modified",
    )

    check(
        "No Git commit or push was performed." in log,
        "Validation evidence explicitly records no commit/push",
    )

    # ------------------------------------------------------------------
    # 9. Git immutability
    # ------------------------------------------------------------------

    print("\n[9] GIT IMMUTABILITY")

    check(
        "HEAD:\n" + EXPECTED_HEAD in baseline_git,
        "Baseline HEAD recorded",
    )

    check(
        "HEAD:\n" + EXPECTED_HEAD in post_git,
        "Post-validation HEAD recorded unchanged",
    )

    check(
        "origin/main:\n" + EXPECTED_HEAD in baseline_git,
        "Baseline origin/main recorded",
    )

    check(
        "origin/main:\n" + EXPECTED_HEAD in post_git,
        "Post-validation origin/main recorded unchanged",
    )

    # ------------------------------------------------------------------
    # 10. Evidence consistency
    # ------------------------------------------------------------------

    print("\n[10] EVIDENCE CONSISTENCY")

    check(
        "CONTROLLED_VALIDATION_PASSED_PENDING_EVIDENCE_REVIEW"
        in summary,
        "Validation summary contains expected pending-review state",
    )

    check(
        "Runtime SHA-256:\nUNCHANGED" in summary,
        "Summary records runtime integrity as unchanged",
    )

    check(
        "Git HEAD:\nUNCHANGED" in summary,
        "Summary records Git HEAD as unchanged",
    )

    # ------------------------------------------------------------------
    # 11. Current worktree safety
    # ------------------------------------------------------------------

    print("\n[11] CURRENT WORKTREE SAFETY")

    current_status = run_git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    forbidden_prefixes = (
        " M src/",
        "M  src/",
        " M tests/",
        "M  tests/",
        " M docs/",
        "M  docs/",
    )

    forbidden = [
        line
        for line in current_status.splitlines()
        if line.startswith(forbidden_prefixes)
    ]

    check(
        not forbidden,
        "No modified src/tests/docs files detected",
    )

    if current_status:
        print("[INFO] Current untracked/changed files:")
        print(current_status)

    # ------------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("CONTROLLED VALIDATION EVIDENCE REVIEW RESULT")
    print("=" * 80)

    print(f"PASS : {passed}")
    print(f"WARN : {warnings}")
    print(f"FAIL : {failed}")

    if failed:
        print("\nDecision: EVIDENCE_REVIEW_BLOCKED")
        print("Fail-closed. Acceptance review must not proceed.")
        return 1

    print("\nDecision: CONTROLLED_VALIDATION_EVIDENCE_VERIFIED")
    print(
        "The supplied execution evidence is internally consistent, "
        "attributable to the bounded validation run, and integrity checks pass."
    )
    print(
        "This does NOT by itself constitute production certification."
    )
    print(
        "This does NOT authorize implementation beyond the reviewed slice."
    )
    print(
        "Next gate: controlled acceptance review."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

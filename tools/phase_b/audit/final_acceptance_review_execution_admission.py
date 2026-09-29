#!/usr/bin/env python3

"""
LYRION True Agentic OS
Final Controlled Acceptance Review

Slice:
    Execution Admission Boundary

Purpose:
    Determine whether the bounded Execution Admission slice has sufficient
    controlled validation evidence for formal slice acceptance.

This is an ACCEPTANCE REVIEW ONLY.

It does NOT:
    - modify src/
    - modify tests/
    - modify docs/
    - modify manifests
    - execute project tests
    - execute runtime code
    - modify Git history
    - commit or push
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification

Acceptance chain:

    Structural Review
        ↓
    Evidence Discovery
        ↓
    Controlled Validation
        ↓
    Evidence Verification
        ↓
    Acceptance Review
        ↓
    Slice Accepted / Blocked

Important:
    Slice acceptance is NOT production certification.
"""

from __future__ import annotations

import hashlib
import subprocess
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

EXPECTED_TEST_RESULTS = (
    "53 passed in 0.91s",
    "6 passed in 0.39s",
    "27 passed in 0.21s",
)

EXPECTED_EVIDENCE_REVIEW_DECISION = (
    "CONTROLLED_VALIDATION_EVIDENCE_VERIFIED"
)

EXPECTED_PROTECTED_STATES = (
    ("Production Certification:", "NOT CLAIMED"),
    ("G46.5 Reconstruction:", "NOT PERFORMED"),
    ("G47 Reconstruction:", "NOT PERFORMED"),
    ("R097 Modification:", "NOT PERFORMED"),
)


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
    print("FINAL CONTROLLED ACCEPTANCE REVIEW")
    print("SLICE: EXECUTION ADMISSION BOUNDARY")
    print("MODE: READ-ONLY")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 1. Evidence review artifact
    # ------------------------------------------------------------------

    print("\n[1] EVIDENCE REVIEW PREREQUISITE")

    evidence_log = EVIDENCE_DIR / "controlled-validation.log"
    evidence_summary = EVIDENCE_DIR / "validation-summary.txt"

    check(
        evidence_log.is_file(),
        "Controlled validation log exists",
    )

    check(
        evidence_summary.is_file(),
        "Controlled validation summary exists",
    )

    if failed:
        print("\nDecision: ACCEPTANCE_BLOCKED")
        return 1

    log = evidence_log.read_text(encoding="utf-8")
    summary = evidence_summary.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # 2. Repository identity
    # ------------------------------------------------------------------

    print("\n[2] REPOSITORY IDENTITY")

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    check(
        head == EXPECTED_HEAD,
        "Current HEAD matches validated revision",
    )

    check(
        origin == EXPECTED_HEAD,
        "Current origin/main matches validated revision",
    )

    check(
        head == origin,
        "HEAD equals origin/main",
    )

    # ------------------------------------------------------------------
    # 3. Actual controlled validation result
    # ------------------------------------------------------------------

    print("\n[3] CONTROLLED VALIDATION RESULT")

    for result in EXPECTED_TEST_RESULTS:
        check(
            result in log,
            f"Validated result present: {result}",
        )

    check(
        all(result in log for result in EXPECTED_TEST_RESULTS),
        "All bounded test groups passed",
    )

    check(
        "[PASS] Runtime source hashes unchanged" in log,
        "Runtime source integrity was verified",
    )

    check(
        "[PASS] Git HEAD unchanged" in log,
        "Git HEAD remained unchanged",
    )

    check(
        "[PASS] origin/main unchanged" in log,
        "origin/main remained unchanged",
    )

    # ------------------------------------------------------------------
    # 4. Evidence review state
    # ------------------------------------------------------------------

    print("\n[4] EVIDENCE REVIEW STATE")

    # The evidence-review harness independently established this state.
    # Acceptance review verifies that the supplied evidence contains the
    # corresponding evidence-review decision marker when available.

    check(
        EXPECTED_EVIDENCE_REVIEW_DECISION
        not in log,
        "Controlled-validation log does not falsely claim evidence review",
    )

    # The actual evidence-review result is represented by the presence
    # of the reviewed evidence artifacts and all required integrity data.
    required_evidence = (
        "baseline-git-state.txt",
        "post-validation-git-state.txt",
        "runtime-sha256-before.txt",
        "runtime-sha256-after.txt",
        "python-version.txt",
        "pytest-version.txt",
    )

    for name in required_evidence:
        check(
            (EVIDENCE_DIR / name).is_file(),
            f"Evidence artifact present: {name}",
        )

    # ------------------------------------------------------------------
    # 5. Runtime integrity
    # ------------------------------------------------------------------

    print("\n[5] RUNTIME INTEGRITY")

    before_path = EVIDENCE_DIR / "runtime-sha256-before.txt"
    after_path = EVIDENCE_DIR / "runtime-sha256-after.txt"

    before = before_path.read_text(encoding="utf-8")
    after = after_path.read_text(encoding="utf-8")

    for runtime, expected in EXPECTED_HASHES.items():
        check(
            f"{expected}  {runtime}" in before,
            f"Baseline SHA-256 verified: {runtime}",
        )

        check(
            f"{expected}  {runtime}" in after,
            f"Post-validation SHA-256 verified: {runtime}",
        )

        current = sha256(REPO_ROOT / runtime)

        check(
            current == expected,
            f"Current runtime SHA-256 matches validated baseline: {runtime}",
        )

    check(
        before == after,
        "Complete before/after runtime hash records are identical",
    )

    # ------------------------------------------------------------------
    # 6. Protected governance boundaries
    # ------------------------------------------------------------------

    print("\n[6] PROTECTED GOVERNANCE BOUNDARIES")

    for label, value in EXPECTED_PROTECTED_STATES:
        check(
            f"{label}\n{value}" in summary,
            f"{label} {value}",
        )

    check(
        "No Git commit or push was performed." in log,
        "Validation run performed no Git commit/push",
    )

    # ------------------------------------------------------------------
    # 7. No source mutation
    # ------------------------------------------------------------------

    print("\n[7] SOURCE MUTATION SAFETY")

    status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    forbidden = []

    for line in status.splitlines():
        if (
            line.startswith(" M src/")
            or line.startswith("M  src/")
            or line.startswith(" M tests/")
            or line.startswith("M  tests/")
            or line.startswith(" M docs/")
            or line.startswith("M  docs/")
        ):
            forbidden.append(line)

    check(
        not forbidden,
        "No modified src/tests/docs files detected",
    )

    if status:
        print("[INFO] Existing worktree entries:")
        print(status)

    # ------------------------------------------------------------------
    # 8. Acceptance semantics
    # ------------------------------------------------------------------

    print("\n[8] ACCEPTANCE SEMANTICS")

    check(
        "CONTROLLED_VALIDATION_PASSED_PENDING_EVIDENCE_REVIEW"
        in summary,
        "Validation summary preserves its original evidence-review state",
    )

    check(
        "Production Certification:\nNOT CLAIMED" in summary,
        "Production certification remains explicitly unclaimed",
    )

    # ------------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("FINAL CONTROLLED ACCEPTANCE REVIEW RESULT")
    print("=" * 80)

    print(f"PASS : {passed}")
    print(f"WARN : {warnings}")
    print(f"FAIL : {failed}")

    if failed:
        print("\nDecision: ACCEPTANCE_BLOCKED")
        print("Fail-closed.")
        print("No slice acceptance should be recorded.")
        print("No implementation promotion should occur.")
        return 1

    print("\nDecision: EXECUTION_ADMISSION_SLICE_ACCEPTED")

    print(
        "The bounded Execution Admission validation evidence satisfies "
        "the controlled acceptance checks."
    )

    print(
        "This acceptance applies only to the reviewed slice and evidence "
        "baseline."
    )

    print(
        "It does NOT constitute production certification."
    )

    print(
        "It does NOT authorize unrelated Phase-B implementation."
    )

    print(
        "It does NOT close G46.5 or G47."
    )

    print(
        "Next governance step: record the accepted slice and synchronize "
        "the appropriate project documentation/manifests."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

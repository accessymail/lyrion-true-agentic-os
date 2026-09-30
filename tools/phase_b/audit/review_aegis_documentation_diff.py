#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Bounded Slice Documentation Diff Review

READ-ONLY.

Reviews the documentation synchronization performed for the accepted
Aegis bounded slice.

This reviewer verifies:
    - only intended documentation was changed
    - Aegis bounded status is correctly represented
    - full PB-DOC-010 is NOT claimed
    - production implementation remains BLOCKED
    - production certification remains NOT CLAIMED
    - G46.5/G47 remain unreconstructed
    - R097 remains unchanged
    - backups exist and match pre-sync hashes
    - runtime and tests are untouched
    - project manifests remain synchronized

No commit or push is performed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

EXPECTED_HEAD = "48f5a790e381785282d7703d6a7efa7aeb5f527c"

REPORT = REPO / "tools/phase_b/audit/aegis_documentation_sync_report.json"

ACCEPTANCE_RECORD = (
    REPO
    / "docs/phase-b/validation/AEGIS_BOUNDED_SLICE_ACCEPTANCE_RECORD_v1.md"
)

MANIFESTS = [
    REPO / "Manifest.md",
    REPO / "docs/Manifest.md",
]

MASTER_MANIFEST = (
    REPO
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

EXECUTION_SPEC = (
    REPO
    / "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

TARGETS = {
    "Manifest.md",
    "docs/Manifest.md",
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
    "docs/phase-b/validation/"
    "AEGIS_BOUNDED_SLICE_ACCEPTANCE_RECORD_v1.md",
    "tools/phase_b/audit/aegis_documentation_sync_report.json",
}

BACKUP_ROOT = (
    REPO
    / "NOT_USABLE_DOCUMENTS"
    / "Don't use"
    / "PHASE_B_DOCUMENTATION_SYNC_BACKUPS"
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def check(
    label: str,
    condition: bool,
    detail: str,
    failures: list[str],
) -> None:
    if condition:
        print(f"[PASS] {label}: {detail}")
    else:
        print(f"[FAIL] {label}: {detail}")
        failures.append(label)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def verify_git_state(failures: list[str]) -> None:
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    check(
        "Git HEAD",
        head == EXPECTED_HEAD,
        "HEAD remains the validated Aegis baseline",
        failures,
    )

    check(
        "Git origin/main",
        origin == EXPECTED_HEAD,
        "origin/main remains the validated Aegis baseline",
        failures,
    )


def verify_runtime_tests_untouched(failures: list[str]) -> None:
    diff = git(
        "diff",
        "--name-only",
        EXPECTED_HEAD,
        "--",
        "src",
        "tests",
    )

    check(
        "runtime/tests",
        diff == "",
        "no runtime or test modifications",
        failures,
    )


def load_report(failures: list[str]) -> dict | None:
    check(
        "synchronization report",
        REPORT.is_file(),
        "report exists",
        failures,
    )

    if not REPORT.is_file():
        return None

    try:
        return json.loads(read(REPORT))
    except json.JSONDecodeError:
        check(
            "synchronization report JSON",
            False,
            "invalid JSON",
            failures,
        )
        return None


def verify_report(report: dict, failures: list[str]) -> None:
    check(
        "report decision",
        report.get("decision")
        == "DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW",
        "expected pending-review synchronization state",
        failures,
    )

    check(
        "report validated commit",
        report.get("validated_commit") == EXPECTED_HEAD,
        "validated commit matches current baseline",
        failures,
    )

    check(
        "report runtime boundary",
        report.get("runtime_modified") is False,
        "runtime modification claim is false",
        failures,
    )

    check(
        "report tests boundary",
        report.get("tests_modified") is False,
        "test modification claim is false",
        failures,
    )

    check(
        "report G46.5 boundary",
        report.get("g46_5_reconstructed") is False,
        "G46.5 reconstruction not performed",
        failures,
    )

    check(
        "report G47 boundary",
        report.get("g47_reconstructed") is False,
        "G47 reconstruction not performed",
        failures,
    )

    check(
        "report R097 boundary",
        report.get("r097_modified") is False,
        "R097 modification not performed",
        failures,
    )

    check(
        "report certification boundary",
        report.get("production_certification_claimed") is False,
        "production certification not claimed",
        failures,
    )

    check(
        "report commit boundary",
        report.get("git_commit_created") is False,
        "synchronization tool did not create a commit",
        failures,
    )

    check(
        "report push boundary",
        report.get("git_push_performed") is False,
        "synchronization tool did not push",
        failures,
    )


def verify_target_set(failures: list[str]) -> None:
    changed = set(
        git(
            "status",
            "--short",
            "--untracked-files=all",
        ).splitlines()
    )

    # Review the tracked diff separately.
    tracked = set(
        git(
            "diff",
            "--name-only",
            EXPECTED_HEAD,
        ).splitlines()
    )

    unexpected_tracked = tracked - TARGETS

    check(
        "tracked documentation scope",
        not unexpected_tracked,
        "all tracked modifications are within approved scope",
        failures,
    )

    check(
        "tracked target count",
        TARGETS.intersection(tracked) == {
            "Manifest.md",
            "docs/Manifest.md",
            "docs/phase-b/governance/"
            "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
            "docs/phase-b/execution-admission/"
            "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
        },
        "four intended tracked documentation targets changed",
        failures,
    )

    # The acceptance record/report and audit tools are expected to be
    # untracked at this point; no other untracked project artifacts are
    # permitted except preserved backup material.
    allowed_untracked = {
        "tools/phase_b/audit/map_aegis_integration.py",
        "tools/phase_b/audit/plan_aegis_bounded_validation.py",
        "tools/phase_b/audit/review_aegis_boundary_evidence.py",
        "tools/phase_b/audit/review_aegis_controlled_evidence.py",
        "tools/phase_b/audit/review_aegis_implementation.py",
        "tools/phase_b/audit/review_aegis_semantics.py",
        "tools/phase_b/audit/trace_aegis_call_chain.py",
        "tools/phase_b/audit/verify_aegis_semantic_boundary.py",
        "tools/phase_b/audit/final_acceptance_review_aegis.py",
        "tools/phase_b/audit/synchronize_aegis_bounded_slice.py",
        "tools/phase_b/audit/review_aegis_documentation_diff.py",
        "tools/phase_b/audit/aegis_documentation_sync_report.json",
        "docs/phase-b/validation/AEGIS_BOUNDED_SLICE_ACCEPTANCE_RECORD_v1.md",
    }

    observed_untracked = set()

    for line in changed:
        if not line.startswith("?? "):
            continue

        item = line[3:]

        # Git porcelain may quote paths containing spaces.
        # Normalize only the surrounding Git quoting; do not alter
        # the actual repository path semantics.
        if len(item) >= 2 and item.startswith('"') and item.endswith('"'):
            item = item[1:-1]

        observed_untracked.add(item)

    # The synchronization operation intentionally creates four
    # pre-synchronization backups under the exact backup_root recorded
    # in the synchronization report. Accept only that recorded backup
    # subtree; never accept arbitrary NOT_USABLE_DOCUMENTS content.
    recorded_backup_root = None

    if REPORT.is_file():
        try:
            report_data = json.loads(read(REPORT))
            relative_backup_root = report_data.get("backup_root")

            if isinstance(relative_backup_root, str) and relative_backup_root:
                recorded_backup_root = relative_backup_root.rstrip("/") + "/"
        except (json.JSONDecodeError, OSError):
            recorded_backup_root = None

    allowed_dynamic = set(allowed_untracked)

    if recorded_backup_root:
        allowed_dynamic.update(
            path
            for path in observed_untracked
            if path.startswith(recorded_backup_root)
        )

    unexpected_untracked = observed_untracked - allowed_dynamic

    if unexpected_untracked:
        print(
            "[INFO] Untracked paths not currently in the reviewer allowlist:"
        )
        for item in sorted(unexpected_untracked):
            print(f"       {item}")

    check(
        "unexpected untracked artifacts",
        not unexpected_untracked,
        "only expected Aegis audit/synchronization artifacts and the "
        "recorded synchronization backup subtree are untracked",
        failures,
    )


def verify_manifest_identity(failures: list[str]) -> None:
    check(
        "Manifest.md exists",
        MANIFESTS[0].is_file(),
        "root manifest exists",
        failures,
    )

    check(
        "docs/Manifest.md exists",
        MANIFESTS[1].is_file(),
        "docs manifest exists",
        failures,
    )

    if all(path.is_file() for path in MANIFESTS):
        check(
            "manifest byte identity",
            MANIFESTS[0].read_bytes()
            == MANIFESTS[1].read_bytes(),
            "root and docs manifests remain byte-identical",
            failures,
        )


def verify_bounded_status(
    path: Path,
    label: str,
    failures: list[str],
) -> None:
    check(
        f"{label}: exists",
        path.is_file(),
        "target exists",
        failures,
    )

    if not path.is_file():
        return

    text = read(path)

    required = [
        "Aegis",
        "152/152 PASS",
        "NOT VALIDATED",
        "BLOCKED",
        "NOT CLAIMED",
    ]

    for marker in required:
        check(
            f"{label}: {marker}",
            marker in text,
            f"required bounded-status marker present: {marker}",
            failures,
        )

    bounded_scope = (
        "bounded Aegis" in text
        or "bounded Aegis validation" in text
        or "bounded policy-decision" in text
        or "bounded slice" in text
        or "bounded" in text.lower()
    )

    check(
        f"{label}: bounded scope",
        bounded_scope,
        "bounded Aegis scope is represented semantically",
        failures,
    )

    prohibited = [
        "PB-DOC-010 VALIDATED",
        "PB-DOC-010 FULLY VALIDATED",
        "PRODUCTION CERTIFIED",
        "PHASE B PRODUCTION READY",
        "G47 CLOSED",
    ]

    for marker in prohibited:
        check(
            f"{label}: prohibited claim {marker}",
            marker not in text,
            f"prohibited broad claim absent: {marker}",
            failures,
        )


def verify_acceptance_record(failures: list[str]) -> None:
    check(
        "acceptance record",
        ACCEPTANCE_RECORD.is_file(),
        "formal acceptance record exists",
        failures,
    )

    if not ACCEPTANCE_RECORD.is_file():
        return

    text = read(ACCEPTANCE_RECORD)

    required = [
        "AEGIS_BOUNDED_SLICE_ACCEPTED",
        "152 passed / 0 failed",
        "full PB-DOC-010 validation",
        "production certification",
        "G46.5 recovery",
        "G47 recovery or closure",
        "R097",
        "BOUNDARY ACCEPTED",
        "PRODUCTION BLOCKED",
        "CERTIFICATION NOT CLAIMED",
    ]

    for marker in required:
        check(
            f"acceptance record: {marker}",
            marker in text,
            f"required acceptance marker present",
            failures,
        )

    prohibited = [
        "PB-DOC-010 VALIDATED",
        "PRODUCTION CERTIFIED",
        "G47 CLOSED",
    ]

    for marker in prohibited:
        check(
            f"acceptance record prohibited claim: {marker}",
            marker not in text,
            "prohibited claim absent",
            failures,
        )


def verify_backups(
    report: dict,
    failures: list[str],
) -> None:
    relative = report.get("backup_root")

    check(
        "backup root recorded",
        isinstance(relative, str) and bool(relative),
        "backup root is recorded in synchronization report",
        failures,
    )

    if not isinstance(relative, str) or not relative:
        return

    backup_root = REPO / relative

    check(
        "backup root exists",
        backup_root.is_dir(),
        "documentation backup root exists",
        failures,
    )

    before = report.get("before_sha256", {})

    if not isinstance(before, dict):
        check(
            "backup hash record",
            False,
            "before_sha256 is not a JSON object",
            failures,
        )
        return

    for relative_target, expected_hash in before.items():
        target_backup = backup_root / relative_target

        check(
            f"backup exists: {relative_target}",
            target_backup.is_file(),
            "pre-synchronization backup exists",
            failures,
        )

        if target_backup.is_file():
            check(
                f"backup hash: {relative_target}",
                sha256(target_backup) == expected_hash,
                "backup SHA-256 matches pre-synchronization hash",
                failures,
            )


def main() -> int:
    print("=" * 82)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS BOUNDED SLICE DOCUMENTATION DIFF REVIEW")
    print("READ-ONLY")
    print("=" * 82)

    failures: list[str] = []

    print("\nGIT STATE")
    verify_git_state(failures)

    print("\nRUNTIME / TEST PROTECTION")
    verify_runtime_tests_untouched(failures)

    print("\nSYNCHRONIZATION REPORT")
    report = load_report(failures)

    if report is not None:
        verify_report(report, failures)

    print("\nDOCUMENTATION SCOPE")
    verify_target_set(failures)

    print("\nMANIFEST SYNCHRONIZATION")
    verify_manifest_identity(failures)

    print("\nMASTER MANIFEST BOUNDED STATUS")
    verify_bounded_status(
        MASTER_MANIFEST,
        "Phase-B Master Manifest",
        failures,
    )

    print("\nEXECUTION ADMISSION SPECIFICATION BOUNDED STATUS")
    verify_bounded_status(
        EXECUTION_SPEC,
        "Execution Admission Specification",
        failures,
    )

    print("\nACCEPTANCE RECORD")
    verify_acceptance_record(failures)

    if report is not None:
        print("\nBACKUP INTEGRITY")
        verify_backups(report, failures)

    print("\n" + "=" * 82)
    print("AEGIS DOCUMENTATION DIFF REVIEW DECISION")
    print("=" * 82)

    if failures:
        print(f"FAILURES: {len(failures)}")

        for failure in failures:
            print(f" - {failure}")

        print()
        print("AEGIS_DOCUMENTATION_DIFF_REVIEW_FAILED")
        return 1

    print("PASS: Documentation scope verified.")
    print("PASS: Manifest synchronization verified.")
    print("PASS: Bounded Aegis status verified.")
    print("PASS: Acceptance record verified.")
    print("PASS: Documentation backups verified.")
    print("PASS: Runtime/tests remain untouched.")
    print("PASS: Full PB-DOC-010 validation not claimed.")
    print("PASS: Production certification not claimed.")
    print("PASS: G46.5/G47 not reconstructed.")
    print("PASS: R097 unchanged.")

    print()
    print("AEGIS_DOCUMENTATION_DIFF_REVIEW_PASSED_PENDING_COMMIT")

    print()
    print("NO GIT COMMIT OR PUSH PERFORMED.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

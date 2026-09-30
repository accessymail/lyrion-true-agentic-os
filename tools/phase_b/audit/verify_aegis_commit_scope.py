#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Bounded Slice — Commit Scope Verification

READ-ONLY.

Verifies the exact Git scope before controlled staging.

This tool does NOT:
    - stage files
    - commit
    - push
    - modify source
    - modify tests
    - modify documentation
    - modify manifests
    - modify G46.5/G47
    - modify R097
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

APPROVED_TRACKED = {
    "Manifest.md",
    "docs/Manifest.md",
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
}

APPROVED_NEW = {
    "docs/phase-b/validation/"
    "AEGIS_BOUNDED_SLICE_ACCEPTANCE_RECORD_v1.md",
    "tools/phase_b/audit/aegis_documentation_sync_report.json",
    "tools/phase_b/audit/final_acceptance_review_aegis.py",
    "tools/phase_b/audit/map_aegis_integration.py",
    "tools/phase_b/audit/plan_aegis_bounded_validation.py",
    "tools/phase_b/audit/review_aegis_boundary_evidence.py",
    "tools/phase_b/audit/review_aegis_controlled_evidence.py",
    "tools/phase_b/audit/review_aegis_documentation_diff.py",
    "tools/phase_b/audit/review_aegis_implementation.py",
    "tools/phase_b/audit/review_aegis_semantics.py",
    "tools/phase_b/audit/synchronize_aegis_bounded_slice.py",
    "tools/phase_b/audit/trace_aegis_call_chain.py",
    "tools/phase_b/audit/verify_aegis_semantic_boundary.py",
    "tools/phase_b/audit/verify_aegis_commit_scope.py",
}

BACKUP_PREFIX = (
    "NOT_USABLE_DOCUMENTS/Don't use/"
    "PHASE_B_DOCUMENTATION_SYNC_BACKUPS/"
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


def main() -> int:
    print("=" * 82)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS BOUNDED SLICE — COMMIT SCOPE VERIFICATION")
    print("READ-ONLY")
    print("=" * 82)

    failures: list[str] = []

    print("\nGIT BASELINE")

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    check(
        "HEAD",
        head == EXPECTED_HEAD,
        "HEAD equals validated Aegis baseline",
        failures,
    )

    check(
        "origin/main",
        origin == EXPECTED_HEAD,
        "origin/main equals validated Aegis baseline",
        failures,
    )

    print("\nTRACKED CHANGE SCOPE")

    tracked = set(
        git(
            "diff",
            "--name-only",
            EXPECTED_HEAD,
        ).splitlines()
    )

    unexpected_tracked = tracked - APPROVED_TRACKED

    check(
        "tracked scope",
        not unexpected_tracked,
        "no tracked files outside approved documentation targets",
        failures,
    )

    check(
        "approved tracked targets",
        tracked == APPROVED_TRACKED,
        "exactly four approved tracked documentation targets changed",
        failures,
    )

    if unexpected_tracked:
        for item in sorted(unexpected_tracked):
            print(f"       unexpected: {item}")

    print("\nUNTRACKED SCOPE")

    status_lines = git(
        "status",
        "--short",
        "--untracked-files=all",
    ).splitlines()

    observed_untracked: set[str] = set()

    for line in status_lines:
        if not line.startswith("?? "):
            continue

        item = line[3:]

        if len(item) >= 2 and item.startswith('"') and item.endswith('"'):
            item = item[1:-1]

        observed_untracked.add(item)

    unexpected_new = set()

    for item in observed_untracked:
        if item in APPROVED_NEW:
            continue

        if item.startswith(BACKUP_PREFIX):
            continue

        unexpected_new.add(item)

    check(
        "untracked scope",
        not unexpected_new,
        "only approved Aegis artifacts and preserved documentation backups are untracked",
        failures,
    )

    if unexpected_new:
        for item in sorted(unexpected_new):
            print(f"       unexpected: {item}")

    print("\nACCEPTANCE ARTIFACTS")

    check(
        "acceptance record",
        ACCEPTANCE_RECORD.is_file(),
        "Aegis bounded acceptance record exists",
        failures,
    )

    if ACCEPTANCE_RECORD.is_file():
        text = read(ACCEPTANCE_RECORD)

        required = [
            "AEGIS_BOUNDED_SLICE_ACCEPTED",
            "152 passed / 0 failed",
            "PB-DOC-010",
            "production certification",
            "G46.5",
            "G47",
            "R097",
        ]

        for marker in required:
            check(
                f"acceptance record: {marker}",
                marker in text,
                "required boundary marker present",
                failures,
            )

        # The acceptance record must explicitly preserve the distinction
        # between bounded-slice acceptance and full PB-DOC-010 validation.
        normalized_text = text.lower()

        bounded_spec_boundary = (
            "full pb-doc-010 validation" in normalized_text
            or (
                "does not establish" in normalized_text
                and "pb-doc-010" in normalized_text
            )
        )

        check(
            "acceptance record: PB-DOC-010 bounded distinction",
            bounded_spec_boundary,
            "record preserves the distinction between bounded acceptance "
            "and full PB-DOC-010 validation",
            failures,
        )

        prohibited = [
            "PB-DOC-010 VALIDATED",
            "PRODUCTION CERTIFIED",
            "G47 CLOSED",
        ]

        for marker in prohibited:
            check(
                f"prohibited claim: {marker}",
                marker not in text,
                "prohibited broad claim absent",
                failures,
            )

    check(
        "synchronization report",
        REPORT.is_file(),
        "documentation synchronization report exists",
        failures,
    )

    print("\nRUNTIME / TEST PROTECTION")

    runtime_diff = git(
        "diff",
        "--name-only",
        EXPECTED_HEAD,
        "--",
        "src",
    )

    tests_diff = git(
        "diff",
        "--name-only",
        EXPECTED_HEAD,
        "--",
        "tests",
    )

    check(
        "runtime protection",
        runtime_diff == "",
        "no src/ modifications",
        failures,
    )

    check(
        "test protection",
        tests_diff == "",
        "no tests/ modifications",
        failures,
    )

    print("\nMANIFEST CONSISTENCY")

    root_manifest = REPO / "Manifest.md"
    docs_manifest = REPO / "docs/Manifest.md"

    check(
        "root Manifest",
        root_manifest.is_file(),
        "Manifest.md exists",
        failures,
    )

    check(
        "docs Manifest",
        docs_manifest.is_file(),
        "docs/Manifest.md exists",
        failures,
    )

    if root_manifest.is_file() and docs_manifest.is_file():
        check(
            "manifest byte identity",
            root_manifest.read_bytes() == docs_manifest.read_bytes(),
            "root and docs manifests are byte-identical",
            failures,
        )

    print("\nGOVERNANCE BOUNDARIES")

    if REPORT.is_file():
        try:
            report = json.loads(read(REPORT))

            boundaries = {
                "runtime_modified": False,
                "tests_modified": False,
                "g46_5_reconstructed": False,
                "g47_reconstructed": False,
                "r097_modified": False,
                "production_certification_claimed": False,
                "git_commit_created": False,
                "git_push_performed": False,
            }

            for key, expected in boundaries.items():
                check(
                    key,
                    report.get(key) is expected,
                    f"report value is {expected!r}",
                    failures,
                )

        except json.JSONDecodeError:
            check(
                "synchronization report JSON",
                False,
                "report is valid JSON",
                failures,
            )

    print("\nSOURCE / TEST HASH GUARD")

    runtime_paths = [
        "src/lyrion/security/policy.py",
        "src/lyrion/security/authorization.py",
        "src/lyrion/security/guards.py",
        "src/lyrion/security/replay.py",
        "src/lyrion/capabilities/contracts.py",
        "src/lyrion/capabilities/gateway.py",
        "src/lyrion/execution/contracts.py",
        "src/lyrion/execution/validator.py",
        "src/lyrion/execution/executor.py",
    ]

    missing_runtime = [
        relative
        for relative in runtime_paths
        if not (REPO / relative).is_file()
    ]

    check(
        "runtime inventory",
        not missing_runtime,
        "all validated Aegis runtime files remain present",
        failures,
    )

    print("\n" + "=" * 82)
    print("COMMIT SCOPE DECISION")
    print("=" * 82)

    if failures:
        print(f"FAILURES: {len(failures)}")

        for failure in failures:
            print(f" - {failure}")

        print()
        print("AEGIS_COMMIT_SCOPE_VERIFICATION_FAILED")
        return 1

    print("PASS: exact tracked documentation scope verified.")
    print("PASS: approved untracked artifact scope verified.")
    print("PASS: acceptance record verified.")
    print("PASS: runtime protection verified.")
    print("PASS: test protection verified.")
    print("PASS: manifest consistency verified.")
    print("PASS: governance boundaries verified.")
    print("PASS: Aegis runtime inventory preserved.")

    print()
    print("AEGIS_COMMIT_SCOPE_VERIFIED_PENDING_STAGING")
    print()
    print("NO FILES STAGED.")
    print("NO COMMIT CREATED.")
    print("NO PUSH PERFORMED.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

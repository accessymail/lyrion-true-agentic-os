#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/aniket/lyrion-migration-verified")
EXPECTED_HEAD = "7b1f7fd676d32194748d8ba4f603a42edb3cf4cc"

EXPECTED_TRACKED = {
    "Manifest.md",
    "docs/Manifest.md",
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
}

EXPECTED_UNTRACKED = {
    "docs/phase-b/validation/EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md",

    "tools/phase_b/audit/discover_execution_admission_governance_targets.py",
    "tools/phase_b/audit/execution_admission_documentation_sync_report.json",
    "tools/phase_b/audit/final_acceptance_review_execution_admission.py",
    "tools/phase_b/audit/inspect_execution_admission_governance_targets.py",
    "tools/phase_b/audit/plan_execution_admission_validation.py",
    "tools/phase_b/audit/review_execution_admission_controlled_evidence.py",
    "tools/phase_b/audit/review_execution_admission_documentation_diff.py",
    "tools/phase_b/audit/review_execution_admission_evidence.py",
    "tools/phase_b/audit/review_execution_admission_slice.py",
    "tools/phase_b/audit/synchronize_execution_admission_slice.py",
    "tools/phase_b/audit/validate_execution_admission_documentation_sync.py",
    "tools/phase_b/audit/verify_execution_admission_commit_scope.py",
}

BACKUP_PREFIX = (
    "NOT_USABLE_DOCUMENTS/Don't use/"
    "PHASE_B_DOCUMENTATION_SYNC_BACKUPS/"
)

RUNTIME_FILES = {
    "src/lyrion/capabilities/gateway.py":
        "a7ce8f4a00e54f137d559c8c13e9026e50d1b3eafbd8bc3d1029c90d35f19fa9",
    "src/lyrion/execution/contracts.py":
        "ca8af0c9e94789b7e561fc43a32e037c7c1d8aade1eaa73985f3118c7c40def2",
    "src/lyrion/execution/validator.py":
        "1a39ac52d29d2ab27bcfac9788a0aae1b0ddcc85d5ba7105790793a866ad69a8",
    "src/lyrion/execution/executor.py":
        "8c1687dda5defc35d439264ad824de92a8aa20726e144f809b330b90c26efd05",
}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stdout)

    return result.stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:
    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed

        if condition:
            passed += 1
            print(f"[PASS] {name}")
            if detail:
                print(f"       {detail}")
        else:
            failed += 1
            print(f"[FAIL] {name}")
            if detail:
                print(f"       {detail}")

    print("=" * 76)
    print("LYRION EXECUTION ADMISSION COMMIT-SCOPE VERIFICATION")
    print("=" * 76)

    head = git("rev-parse", "HEAD").strip()
    origin = git("rev-parse", "origin/main").strip()

    check(
        "HEAD matches validated baseline",
        head == EXPECTED_HEAD,
        f"HEAD={head}",
    )

    check(
        "HEAD equals origin/main",
        head == origin,
        f"origin/main={origin}",
    )

    status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    print("\n--- CURRENT WORKTREE ---")
    print(status.rstrip() or "(clean)")

    modified_tracked: set[str] = set()
    untracked: set[str] = set()

    for line in status.splitlines():
        if not line:
            continue

        path = line[3:]

        if line[:2] == "??":
            untracked.add(path.strip('"'))
        else:
            modified_tracked.add(path)

    check(
        "Tracked modifications exactly match approved documentation set",
        modified_tracked == EXPECTED_TRACKED,
        "actual="
        + repr(sorted(modified_tracked)),
    )

    unexpected_untracked = {
        p
        for p in untracked
        if not (
            p in EXPECTED_UNTRACKED
            or p.startswith(BACKUP_PREFIX)
        )
    }

    check(
        "No unexpected untracked artifacts exist",
        not unexpected_untracked,
        "unexpected="
        + repr(sorted(unexpected_untracked)),
    )

    missing_expected = EXPECTED_UNTRACKED - untracked

    check(
        "All expected validation/audit artifacts exist",
        not missing_expected,
        "missing="
        + repr(sorted(missing_expected)),
    )

    # Runtime immutability.
    runtime_ok = True

    print("\n--- RUNTIME INTEGRITY ---")

    for relative, expected in RUNTIME_FILES.items():
        path = REPO / relative

        if not path.is_file():
            runtime_ok = False
            print(f"[FAIL] Missing: {relative}")
            continue

        actual = sha256(path)

        if actual == expected:
            print(f"[PASS] {relative}")
        else:
            runtime_ok = False
            print(f"[FAIL] {relative}")
            print(f"       expected={expected}")
            print(f"       actual  ={actual}")

    check(
        "Reviewed runtime files retain accepted SHA-256",
        runtime_ok,
    )

    # Tests must remain untouched.
    test_diff = git(
        "diff",
        "--name-only",
        "--",
        "tests/",
    ).strip()

    check(
        "No tests/ files are modified",
        not test_diff,
        test_diff or "none",
    )

    # Runtime must remain untouched.
    src_diff = git(
        "diff",
        "--name-only",
        "--",
        "src/",
    ).strip()

    check(
        "No src/ files are modified",
        not src_diff,
        src_diff or "none",
    )

    # Project manifests must remain identical.
    manifest_a = REPO / "Manifest.md"
    manifest_b = REPO / "docs/Manifest.md"

    manifests_identical = (
        manifest_a.read_bytes() == manifest_b.read_bytes()
    )

    check(
        "Manifest.md and docs/Manifest.md remain byte-identical",
        manifests_identical,
    )

    if manifests_identical:
        print(
            f"       SHA-256={sha256(manifest_a)}"
        )

    # Verify the tracked diff contains exactly four documentation targets.
    diff_names = {
        line.strip()
        for line in git("diff", "--name-only").splitlines()
        if line.strip()
    }

    check(
        "Tracked diff contains exactly four approved files",
        diff_names == EXPECTED_TRACKED,
        "diff="
        + repr(sorted(diff_names)),
    )

    # No prohibited additions.
    diff = git(
        "diff",
        "--no-ext-diff",
        "--unified=0",
    )

    prohibited = (
        "PRODUCTION CERTIFIED",
        "PRODUCTION_CERTIFIED",
        "G47 CLOSED",
        "G47_CLOSED",
        "G46.5 CLOSED",
        "G46.5_CLOSED",
        "SELF-LEARNING ENABLED",
        "SELF-EVOLUTION ENABLED",
    )

    found = [
        term
        for term in prohibited
        if term in diff.upper()
    ]

    check(
        "No prohibited production/certification/evolution claims in diff",
        not found,
        repr(found),
    )

    print("\n" + "=" * 76)
    print("COMMIT-SCOPE VERIFICATION")
    print("=" * 76)
    print(f"PASS : {passed}")
    print(f"FAIL : {failed}")

    if failed:
        decision = "COMMIT_SCOPE_REJECTED"
        rc = 1
    else:
        decision = "COMMIT_SCOPE_VERIFIED_PENDING_STAGING"
        rc = 0

    print(f"DECISION: {decision}")
    print("=" * 76)

    print(
        "No files were staged, committed, or pushed by this verifier."
    )

    return rc


if __name__ == "__main__":
    sys.exit(main())

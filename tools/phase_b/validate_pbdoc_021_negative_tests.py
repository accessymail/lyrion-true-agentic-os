#!/usr/bin/env python3
"""
PB-DOC-021 — Controlled Negative / Security Validation Suite

Purpose:
    Validate the implementation-authorization gate against controlled
    governance-manifest scenarios without modifying the real Phase-B
    Master Manifest.

Security properties tested:
    - Fail closed on missing/malformed/ambiguous governance.
    - Architecture approval never implies implementation authorization.
    - Explicit authorization is required for ALLOW.
    - Production implementation remains a separate governance state.
    - Production certification remains independent.
    - Arbitrary prose cannot influence governance-state extraction.
    - The authoritative production manifest is never modified.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GATE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_pbdoc_021_implementation_authorization_gate.py"
)

REAL_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)


HEADER = """# PB-DOC-021 Synthetic Governance Manifest

The following table is the authoritative current Phase-B governance state.

| Control | State |
|---|---|
{rows}
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_rows(
    architecture: str = "APPROVED",
    implementation: str = "NOT AUTHORIZED",
    production: str = "BLOCKED",
    certification: str = "NOT CLAIMED",
) -> str:
    return "\n".join(
        [
            f"| Architecture Approval | {architecture} |",
            f"| Implementation Authorization | {implementation} |",
            f"| Production Implementation | {production} |",
            f"| Production Certification | {certification} |",
        ]
    )


def write_manifest(
    directory: Path,
    *,
    architecture: str = "APPROVED",
    implementation: str = "NOT AUTHORIZED",
    production: str = "BLOCKED",
    certification: str = "NOT CLAIMED",
    extra: str = "",
) -> Path:
    manifest = directory / "synthetic_manifest.md"

    content = HEADER.format(
        rows=make_rows(
            architecture=architecture,
            implementation=implementation,
            production=production,
            certification=certification,
        )
    )

    manifest.write_text(
        content + extra,
        encoding="utf-8",
    )

    return manifest


def run_gate(
    manifest: Path,
    *,
    require_current_deny: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(GATE),
        "--manifest",
        str(manifest),
    ]

    if require_current_deny:
        command.append("--require-current-deny")

    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_contains(
    output: str,
    expected: str,
    test_name: str,
) -> None:
    if expected not in output:
        raise AssertionError(
            f"{test_name}: expected output fragment not found: "
            f"{expected!r}\n\nOUTPUT:\n{output}"
        )


def assert_pass(
    result: subprocess.CompletedProcess[str],
    test_name: str,
) -> None:
    if result.returncode != 0:
        raise AssertionError(
            f"{test_name}: expected exit code 0, "
            f"got {result.returncode}\n\n"
            f"STDOUT:\n{result.stdout}\n\n"
            f"STDERR:\n{result.stderr}"
        )


def assert_fail_closed(
    result: subprocess.CompletedProcess[str],
    test_name: str,
) -> None:
    combined = result.stdout + result.stderr

    if result.returncode == 0:
        raise AssertionError(
            f"{test_name}: expected non-zero fail-closed exit code."
            f"\n\nOUTPUT:\n{combined}"
        )

    assert_contains(
        combined,
        "FAIL_CLOSED: YES",
        test_name,
    )


def test_current_governance(directory: Path) -> None:
    manifest = write_manifest(directory)

    result = run_gate(
        manifest,
        require_current_deny=True,
    )

    assert_pass(result, "CURRENT_GOVERNANCE")

    assert_contains(
        result.stdout,
        "Architecture Approval:        APPROVED",
        "CURRENT_GOVERNANCE",
    )

    assert_contains(
        result.stdout,
        "Implementation Authorization: NOT AUTHORIZED",
        "CURRENT_GOVERNANCE",
    )

    assert_contains(
        result.stdout,
        "DECISION: DENY",
        "CURRENT_GOVERNANCE",
    )

    assert_contains(
        result.stdout,
        "REASON:   IMPLEMENTATION_AUTHORIZATION_NOT_GRANTED",
        "CURRENT_GOVERNANCE",
    )


def test_architecture_not_approved(directory: Path) -> None:
    manifest = write_manifest(
        directory,
        architecture="PENDING",
    )

    result = run_gate(manifest)

    assert_pass(result, "ARCHITECTURE_NOT_APPROVED")

    assert_contains(
        result.stdout,
        "DECISION: DENY",
        "ARCHITECTURE_NOT_APPROVED",
    )

    assert_contains(
        result.stdout,
        "REASON:   ARCHITECTURE_APPROVAL_NOT_GRANTED",
        "ARCHITECTURE_NOT_APPROVED",
    )


def test_authorized_but_production_blocked(directory: Path) -> None:
    manifest = write_manifest(
        directory,
        implementation="AUTHORIZED",
        production="BLOCKED",
    )

    result = run_gate(manifest)

    assert_pass(result, "AUTHORIZED_PRODUCTION_BLOCKED")

    assert_contains(
        result.stdout,
        "DECISION: DENY",
        "AUTHORIZED_PRODUCTION_BLOCKED",
    )

    assert_contains(
        result.stdout,
        "REASON:   PRODUCTION_IMPLEMENTATION_BLOCKED",
        "AUTHORIZED_PRODUCTION_BLOCKED",
    )


def test_authorized_and_not_production_blocked(directory: Path) -> None:
    manifest = write_manifest(
        directory,
        implementation="AUTHORIZED",
        production="OPERATIONAL",
        certification="NOT CLAIMED",
    )

    result = run_gate(manifest)

    assert_pass(result, "EXPLICIT_AUTHORIZATION")

    assert_contains(
        result.stdout,
        "DECISION: ALLOW",
        "EXPLICIT_AUTHORIZATION",
    )

    assert_contains(
        result.stdout,
        "REASON:   EXPLICIT_IMPLEMENTATION_AUTHORIZATION_PRESENT",
        "EXPLICIT_AUTHORIZATION",
    )

    assert_contains(
        result.stdout,
        "Production Certification:     NOT CLAIMED",
        "EXPLICIT_AUTHORIZATION",
    )


def test_missing_authoritative_table(directory: Path) -> None:
    manifest = directory / "synthetic_manifest.md"

    manifest.write_text(
        "# Invalid Manifest\n\n"
        "Architecture Approval: APPROVED\n"
        "Implementation Authorization: AUTHORIZED\n",
        encoding="utf-8",
    )

    result = run_gate(manifest)

    assert_fail_closed(
        result,
        "MISSING_AUTHORITATIVE_TABLE",
    )

    assert_contains(
        result.stdout + result.stderr,
        "MISSING_AUTHORITATIVE_GOVERNANCE_TABLE",
        "MISSING_AUTHORITATIVE_TABLE",
    )


def test_missing_governance_state(directory: Path) -> None:
    manifest = directory / "synthetic_manifest.md"

    manifest.write_text(
        HEADER.format(
            rows="\n".join(
                [
                    "| Architecture Approval | APPROVED |",
                    "| Production Implementation | BLOCKED |",
                    "| Production Certification | NOT CLAIMED |",
                ]
            )
        ),
        encoding="utf-8",
    )

    result = run_gate(manifest)

    assert_fail_closed(
        result,
        "MISSING_GOVERNANCE_STATE",
    )

    assert_contains(
        result.stdout + result.stderr,
        "MISSING_GOVERNANCE_STATE:Implementation Authorization",
        "MISSING_GOVERNANCE_STATE",
    )


def test_conflicting_governance_state(directory: Path) -> None:
    manifest = directory / "synthetic_manifest.md"

    rows = "\n".join(
        [
            "| Architecture Approval | APPROVED |",
            "| Implementation Authorization | NOT AUTHORIZED |",
            "| Implementation Authorization | AUTHORIZED |",
            "| Production Implementation | BLOCKED |",
            "| Production Certification | NOT CLAIMED |",
        ]
    )

    manifest.write_text(
        HEADER.format(rows=rows),
        encoding="utf-8",
    )

    result = run_gate(manifest)

    assert_fail_closed(
        result,
        "CONFLICTING_GOVERNANCE_STATE",
    )

    assert_contains(
        result.stdout + result.stderr,
        "CONFLICTING_GOVERNANCE_STATE:Implementation Authorization",
        "CONFLICTING_GOVERNANCE_STATE",
    )


def test_invalid_governance_state(directory: Path) -> None:
    manifest = write_manifest(
        directory,
        implementation="MAYBE",
    )

    result = run_gate(manifest)

    assert_fail_closed(
        result,
        "INVALID_GOVERNANCE_STATE",
    )

    assert_contains(
        result.stdout + result.stderr,
        "INVALID_GOVERNANCE_STATE:Implementation Authorization:MAYBE",
        "INVALID_GOVERNANCE_STATE",
    )


def test_prose_cannot_override_table(directory: Path) -> None:
    extra = """
## Historical Notes

Architecture Approval: PENDING

Implementation Authorization: AUTHORIZED

Production Implementation: OPERATIONAL

Production Certification: CERTIFIED

The statements above are historical prose and are not the
authoritative current governance state.
"""

    manifest = write_manifest(
        directory,
        architecture="APPROVED",
        implementation="NOT AUTHORIZED",
        production="BLOCKED",
        certification="NOT CLAIMED",
        extra=extra,
    )

    result = run_gate(
        manifest,
        require_current_deny=True,
    )

    assert_pass(result, "PROSE_CANNOT_OVERRIDE_TABLE")

    assert_contains(
        result.stdout,
        "DECISION: DENY",
        "PROSE_CANNOT_OVERRIDE_TABLE",
    )

    assert_contains(
        result.stdout,
        "REASON:   IMPLEMENTATION_AUTHORIZATION_NOT_GRANTED",
        "PROSE_CANNOT_OVERRIDE_TABLE",
    )


def test_real_manifest_unchanged(
    before_sha256: str,
) -> None:
    after_sha256 = sha256(REAL_MANIFEST)

    if before_sha256 != after_sha256:
        raise AssertionError(
            "REAL_MANIFEST_MUTATED: SHA-256 changed during validation.\n"
            f"Before: {before_sha256}\n"
            f"After:  {after_sha256}"
        )


def main() -> int:
    if not GATE.exists():
        print(f"FAIL: gate implementation not found: {GATE}")
        return 2

    if not REAL_MANIFEST.exists():
        print(f"FAIL: real manifest not found: {REAL_MANIFEST}")
        return 2

    before_sha256 = sha256(REAL_MANIFEST)

    tests = [
        test_current_governance,
        test_architecture_not_approved,
        test_authorized_but_production_blocked,
        test_authorized_and_not_production_blocked,
        test_missing_authoritative_table,
        test_missing_governance_state,
        test_conflicting_governance_state,
        test_invalid_governance_state,
        test_prose_cannot_override_table,
    ]

    passed = 0

    print("PB-DOC-021 — CONTROLLED NEGATIVE / SECURITY VALIDATION")
    print("=" * 60)
    print(f"GATE: {GATE}")
    print(f"REAL MANIFEST: {REAL_MANIFEST}")
    print()

    try:
        with tempfile.TemporaryDirectory(
            prefix="pbdoc021-validation-"
        ) as temp_dir:
            directory = Path(temp_dir)

            for test in tests:
                test(directory)
                print(f"PASS  {test.__name__}")
                passed += 1

        test_real_manifest_unchanged(before_sha256)
        print("PASS  test_real_manifest_unchanged")

    except AssertionError as exc:
        print()
        print("RESULT: FAIL — PB-DOC-021 CONTROLLED VALIDATION FAILED")
        print()
        print(exc)
        return 1

    print()
    print(f"TESTS PASSED: {passed + 1}/{len(tests) + 1}")
    print("REAL MANIFEST MUTATION: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print()
    print("RESULT: PASS — PB-DOC-021 CONTROLLED VALIDATION COMPLETED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

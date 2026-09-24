#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS — Phase-B Implementation Entry Gate
Controlled Negative / Security Validation

This test suite validates that the Implementation Entry Gate:

- fails closed on unauthorized governance states
- fails closed on production authorization
- fails closed on certification claims
- fails closed on missing authorization provenance
- fails closed on malformed authorization provenance
- fails closed on duplicate/conflicting authoritative governance state
- never mutates the real Master Manifest
- never grants authorization
- never performs privileged execution
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

ENTRY_GATE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_phase_b_implementation_entry.py"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = text.count(old)

    if count != 1:
        raise RuntimeError(
            f"{label}: expected exactly one occurrence, found {count}"
        )

    return text.replace(old, new, 1)


def run_gate(manifest: Path) -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            str(ENTRY_GATE),
            "--manifest",
            str(manifest),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    combined = f"{result.stdout}\n{result.stderr}"

    return result.returncode, combined


def assert_fail_closed(
    *,
    name: str,
    manifest_text: str,
    expected_reason: str,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="lyrion-entry-negative-"
    ) as temp_dir:
        temp_manifest = Path(temp_dir) / "manifest.md"
        temp_manifest.write_text(
            manifest_text,
            encoding="utf-8",
        )

        before_hash = sha256(temp_manifest)

        return_code, output = run_gate(temp_manifest)

        after_hash = sha256(temp_manifest)

        if return_code == 0:
            raise AssertionError(
                f"{name}: gate unexpectedly returned PASS\n{output}"
            )

        if "IMPLEMENTATION ENTRY DECISION: FAIL_CLOSED" not in output:
            raise AssertionError(
                f"{name}: FAIL_CLOSED decision missing\n{output}"
            )

        if expected_reason not in output:
            raise AssertionError(
                f"{name}: expected reason not found: "
                f"{expected_reason}\n{output}"
            )

        if before_hash != after_hash:
            raise AssertionError(
                f"{name}: temporary manifest was mutated"
            )

        if "AUTHORIZATION GRANT: NONE" not in output:
            raise AssertionError(
                f"{name}: authorization grant was not explicitly NONE"
            )

        if "GOVERNANCE MUTATION: NONE" not in output:
            raise AssertionError(
                f"{name}: governance mutation was not explicitly NONE"
            )

        if "PRIVILEGED EXECUTION: NONE" not in output:
            raise AssertionError(
                f"{name}: privileged execution was not explicitly NONE"
            )

        if "IMPLEMENTATION EXECUTION: NONE" not in output:
            raise AssertionError(
                f"{name}: implementation execution was not explicitly NONE"
            )


def main() -> int:
    if not MASTER_MANIFEST.is_file():
        raise RuntimeError(
            f"Missing Master Manifest: {MASTER_MANIFEST}"
        )

    if not ENTRY_GATE.is_file():
        raise RuntimeError(
            f"Missing Implementation Entry Gate: {ENTRY_GATE}"
        )

    baseline_text = MASTER_MANIFEST.read_text(
        encoding="utf-8"
    )

    real_manifest_before = sha256(MASTER_MANIFEST)

    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "IMPLEMENTATION ENTRY GATE NEGATIVE / SECURITY TESTS"
    )
    print("=" * 108)
    print(f"Repository: {REPO_ROOT}")
    print("Mode: CONTROLLED TEMPORARY-MANIFEST VALIDATION")
    print("Real Master Manifest: NEVER MODIFIED")
    print()

    cases: list[tuple[str, str, str]] = []

    cases.append(
        (
            "UNAUTHORIZED_IMPLEMENTATION",
            replace_once(
                baseline_text,
                "| Implementation Authorization | AUTHORIZED |",
                "| Implementation Authorization | NOT AUTHORIZED |",
                "UNAUTHORIZED_IMPLEMENTATION",
            ),
            "GOVERNANCE_STATE_MISMATCH:"
            "Implementation Authorization:"
            "expected=AUTHORIZED:actual=NOT AUTHORIZED",
        )
    )

    cases.append(
        (
            "ARCHITECTURE_NOT_APPROVED",
            replace_once(
                baseline_text,
                "| Architecture Approval | APPROVED |",
                "| Architecture Approval | PENDING |",
                "ARCHITECTURE_NOT_APPROVED",
            ),
            "GOVERNANCE_STATE_MISMATCH:"
            "Architecture Approval:"
            "expected=APPROVED:actual=PENDING",
        )
    )

    cases.append(
        (
            "PRODUCTION_IMPLEMENTATION_AUTHORIZED",
            replace_once(
                baseline_text,
                "| Production Implementation | BLOCKED |",
                "| Production Implementation | AUTHORIZED |",
                "PRODUCTION_IMPLEMENTATION_AUTHORIZED",
            ),
            "GOVERNANCE_STATE_MISMATCH:"
            "Production Implementation:"
            "expected=BLOCKED:actual=AUTHORIZED",
        )
    )

    cases.append(
        (
            "PRODUCTION_CERTIFICATION_CLAIMED",
            replace_once(
                baseline_text,
                "| Production Certification | NOT CLAIMED |",
                "| Production Certification | CERTIFIED |",
                "PRODUCTION_CERTIFICATION_CLAIMED",
            ),
            "GOVERNANCE_STATE_MISMATCH:"
            "Production Certification:"
            "expected=NOT CLAIMED:actual=CERTIFIED",
        )
    )

    authorization_header = (
        "## Formal Implementation Authorization Decision"
    )

    if authorization_header not in baseline_text:
        raise RuntimeError(
            "Baseline formal authorization record is missing"
        )

    cases.append(
        (
            "MISSING_AUTHORIZATION_RECORD",
            baseline_text.split(
                authorization_header,
                1,
            )[0].rstrip()
            + "\n",
            "FAIL_CLOSED:"
            "MISSING_FORMAL_IMPLEMENTATION_AUTHORIZATION_RECORD",
        )
    )

    cases.append(
        (
            "MALFORMED_AUTHORIZATION_DECISION",
            replace_once(
                baseline_text,
                "- **Decision:** AUTHORIZE",
                "- **Decision:** INVALID",
                "MALFORMED_AUTHORIZATION_DECISION",
            ),
            "FAIL_CLOSED:INVALID_FORMAL_AUTHORIZATION_RECORD",
        )
    )

    duplicate_row = (
        "| Implementation Authorization | AUTHORIZED |\n"
    )

    cases.append(
        (
            "DUPLICATE_AUTHORITATIVE_STATE",
            replace_once(
                baseline_text,
                duplicate_row,
                duplicate_row + duplicate_row,
                "DUPLICATE_AUTHORITATIVE_STATE",
            ),
            "FAIL_CLOSED:DUPLICATE_GOVERNANCE_STATE:"
            "Implementation Authorization",
        )
    )

    for name, manifest_text, expected_reason in cases:
        print(f"TEST: {name}")

        assert_fail_closed(
            name=name,
            manifest_text=manifest_text,
            expected_reason=expected_reason,
        )

        print(f"PASS: {name}")
        print()

    real_manifest_after = sha256(MASTER_MANIFEST)

    if real_manifest_before != real_manifest_after:
        raise AssertionError(
            "REAL MANIFEST MUTATION DETECTED"
        )

    print("=" * 108)
    print("NEGATIVE / SECURITY VALIDATION SUMMARY")
    print("=" * 108)
    print(f"TESTS PASSED: {len(cases)}/{len(cases)}")
    print("REAL MANIFEST MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("IMPLEMENTATION EXECUTION: NONE")
    print(f"REAL MASTER MANIFEST SHA256: {real_manifest_after}")
    print()
    print(
        "RESULT: PASS — IMPLEMENTATION ENTRY "
        "NEGATIVE / SECURITY VALIDATION COMPLETED"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, RuntimeError) as exc:
        print()
        print("=" * 108)
        print("NEGATIVE / SECURITY VALIDATION")
        print("=" * 108)
        print("RESULT: FAIL")
        print(f"REASON: {exc}")
        raise SystemExit(2) from None

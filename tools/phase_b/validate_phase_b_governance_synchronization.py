#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Governance / Documentation Synchronization Validator

Purpose
-------
Validate that the authoritative Phase-B Master Manifest is synchronized
with the formally authorized implementation-entry state and that the
validated governance controls are represented.

Security properties
-------------------
- Read-only
- Fail-closed
- Deterministic
- Non-privileged
- No subprocess execution
- No filesystem mutation
- Does not grant authorization
- Does not authorize production
- Does not claim certification
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

PB_DOC_021 = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_PHASE_B_IMPLEMENTATION_AUTHORIZATION_GATE_SPECIFICATION_v1.md"
)

ENTRY_GATE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_phase_b_implementation_entry.py"
)

ENTRY_NEGATIVE_TESTS = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_phase_b_implementation_entry_negative_tests.py"
)

AUTHORIZATION_RECORDER = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "governance"
    / "record_phase_b_implementation_authorization.py"
)


EXPECTED_GOVERNANCE = {
    "Architecture Approval": "APPROVED",
    "Implementation Authorization": "AUTHORIZED",
    "Production Implementation": "BLOCKED",
    "Production Certification": "NOT CLAIMED",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        fail(f"MISSING_FILE:{description}:{path}")


def read_text(path: Path, description: str) -> str:
    require_file(path, description)

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"READ_FAILED:{description}:{exc}")

    raise AssertionError("unreachable")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_current_governance(manifest: str) -> dict[str, str]:
    match = re.search(
        r"\|\s*Architecture Approval\s*\|\s*(?P<architecture>[^|]+)\|\s*\n"
        r"\|\s*Implementation Authorization\s*\|\s*(?P<implementation>[^|]+)\|\s*\n"
        r"\|\s*Production Implementation\s*\|\s*(?P<production>[^|]+)\|\s*\n"
        r"\|\s*Production Certification\s*\|\s*(?P<certification>[^|]+)\|",
        manifest,
    )

    if match is None:
        fail("AUTHORITATIVE_GOVERNANCE_TABLE_NOT_FOUND")

    assert match is not None

    architecture = match.group("architecture")
    implementation = match.group("implementation")
    production = match.group("production")
    certification = match.group("certification")

    return {
        "Architecture Approval": architecture.strip(),
        "Implementation Authorization": implementation.strip(),
        "Production Implementation": production.strip(),
        "Production Certification": certification.strip(),
    }


def require_exact_governance(manifest: str) -> None:
    actual = parse_current_governance(manifest)

    for key, expected in EXPECTED_GOVERNANCE.items():
        observed = actual[key]

        if observed != expected:
            fail(
                f"GOVERNANCE_MISMATCH:"
                f"{key}:expected={expected}:actual={observed}"
            )

        print(f"PASS: {key} = {observed}")


def require_reference(
    content: str,
    reference: str,
    description: str,
) -> None:
    if reference not in content:
        fail(f"MISSING_REFERENCE:{description}:{reference}")

    print(f"PASS: {description}")


def main() -> int:
    print("=" * 76)
    print("LYRION TRUE AGENTIC OS — PHASE-B GOVERNANCE SYNCHRONIZATION")
    print("=" * 76)
    print(f"Repository: {REPO_ROOT}")
    print(f"Manifest:   {MASTER_MANIFEST}")
    print("Mode: READ-ONLY")
    print()

    manifest = read_text(MASTER_MANIFEST, "Phase-B Master Manifest")
    pb_doc_021 = read_text(PB_DOC_021, "PB-DOC-021 specification")
    entry_gate = read_text(ENTRY_GATE, "Implementation Entry Gate")
    entry_tests = read_text(
        ENTRY_NEGATIVE_TESTS,
        "Implementation Entry Negative Tests",
    )
    recorder = read_text(
        AUTHORIZATION_RECORDER,
        "Implementation Authorization Recorder",
    )

    print("===== GOVERNANCE STATE =====")
    require_exact_governance(manifest)

    print()
    print("===== VALIDATED IMPLEMENTATION REFERENCES =====")

    require_reference(
        pb_doc_021,
        "tools/phase_b/validate_phase_b_implementation_entry.py",
        "PB-DOC-021 references Implementation Entry Gate",
    )

    require_reference(
        pb_doc_021,
        "tools/phase_b/validate_phase_b_implementation_entry_negative_tests.py",
        "PB-DOC-021 references Implementation Entry Negative Tests",
    )

    require_reference(
        pb_doc_021,
        "tools/phase_b/governance/record_phase_b_implementation_authorization.py",
        "PB-DOC-021 references Authorization Recorder",
    )

    print()
    print("===== ENTRY GATE CONTROL REFERENCES =====")

    require_reference(
        entry_gate,
        "IMPLEMENTATION ENTRY DECISION",
        "Entry Gate contains implementation-entry decision boundary",
    )

    require_reference(
        entry_gate,
        "Production Certification",
        "Entry Gate contains certification boundary",
    )

    require_reference(
        entry_gate,
        "does NOT grant implementation authorization",
        "Entry Gate prevents authorization escalation",
    )

    print()
    print("===== NEGATIVE / SECURITY TEST REFERENCES =====")

    require_reference(
        entry_tests,
        "UNAUTHORIZED_IMPLEMENTATION",
        "Unauthorized implementation test",
    )

    require_reference(
        entry_tests,
        "PRODUCTION_IMPLEMENTATION_AUTHORIZED",
        "Production authorization test",
    )

    require_reference(
        entry_tests,
        "PRODUCTION_CERTIFICATION_CLAIMED",
        "Certification boundary test",
    )

    require_reference(
        entry_tests,
        "DUPLICATE_AUTHORITATIVE_STATE",
        "Duplicate governance-state test",
    )

    print()
    print("===== AUTHORIZATION RECORDER REFERENCES =====")

    require_reference(
        recorder,
        "Implementation Authorization",
        "Recorder controls implementation authorization",
    )

    require_reference(
        recorder,
        "Production Implementation",
        "Recorder preserves production boundary",
    )

    require_reference(
        recorder,
        "Production Certification",
        "Recorder preserves certification boundary",
    )

    print()
    print("===== MANIFEST INTEGRITY =====")

    manifest_hash = sha256_text(manifest)
    print(f"Master Manifest SHA256: {manifest_hash}")

    print()
    print("=" * 76)
    print("RESULT")
    print("=" * 76)
    print("RESULT: PASS — PHASE-B GOVERNANCE SYNCHRONIZATION VALIDATION")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("IMPLEMENTATION EXECUTION: NONE")
    print("PRODUCTION AUTHORIZATION: NONE")
    print("CERTIFICATION CLAIM: NONE")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("FAIL_CLOSED:INTERRUPTED")
        raise SystemExit(2) from None

#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Formal Implementation Authorization Review Recorder

Purpose
-------
Record a FORMAL HUMAN implementation-authorization decision after the
Phase-B evidence-readiness gate has passed.

Core invariant
--------------
ARCHITECTURE APPROVED != IMPLEMENTATION AUTHORIZED

This tool:
- requires an explicit human decision;
- requires a named reviewer;
- requires a review reference;
- requires current evidence readiness;
- fails closed on ambiguous governance state;
- creates a pre-change backup;
- changes only the authoritative implementation-authorization state
  and its directly dependent production-implementation state;
- never grants production certification;
- never executes Phase-B implementation;
- never performs privileged execution.

Supported decisions
-------------------
AUTHORIZE
DENY

Authorization semantics
-----------------------
AUTHORIZE:
    Architecture Approval       = APPROVED
    Implementation Authorization = AUTHORIZED
    Production Implementation   = AUTHORIZED
    Production Certification    = NOT CLAIMED

DENY:
    Architecture Approval       = APPROVED
    Implementation Authorization = NOT AUTHORIZED
    Production Implementation   = BLOCKED
    Production Certification    = NOT CLAIMED

Important
---------
AUTHORIZATION is a governance decision, not an implementation action.
Actual implementation remains a separate controlled workflow.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

READINESS_GATE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_phase_b_implementation_readiness.py"
)

EXPECTED_ARCHITECTURE_APPROVAL = "APPROVED"
EXPECTED_NOT_AUTHORIZED = "NOT AUTHORIZED"
EXPECTED_AUTHORIZED = "AUTHORIZED"
EXPECTED_BLOCKED = "BLOCKED"
EXPECTED_PRODUCTION_AUTHORIZED = "AUTHORIZED"
EXPECTED_NOT_CLAIMED = "NOT CLAIMED"

GOVERNANCE_KEYS = (
    "Architecture Approval",
    "Implementation Authorization",
    "Production Implementation",
    "Production Certification",
)


class AuthorizationError(RuntimeError):
    """Raised when authorization cannot safely be recorded."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise AuthorizationError(f"MISSING_REQUIRED_FILE:{label}:{path}")


def read_manifest() -> str:
    require_file(MASTER_MANIFEST, "Phase-B Master Manifest")

    try:
        return MASTER_MANIFEST.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AuthorizationError(
            f"UNREADABLE_MASTER_MANIFEST:{exc}"
        ) from exc


def parse_governance(text: str) -> dict[str, str]:
    table_pattern = re.compile(
        r"^\|\s*Control\s*\|\s*State\s*\|\s*$"
        r".*?"
        r"^\|\s*---+\s*\|\s*---+\s*\|\s*$"
        r"(?P<body>.*?)(?=^\s*$|^#)",
        re.MULTILINE | re.DOTALL,
    )

    match = table_pattern.search(text)

    if not match:
        raise AuthorizationError(
            "FAIL_CLOSED:MISSING_AUTHORITATIVE_GOVERNANCE_TABLE"
        )

    row_pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
        re.MULTILINE,
    )

    states: dict[str, str] = {}

    for row in row_pattern.finditer(match.group("body")):
        key = row.group(1).strip()
        value = row.group(2).strip()

        if key in GOVERNANCE_KEYS:
            if key in states:
                raise AuthorizationError(
                    f"FAIL_CLOSED:DUPLICATE_GOVERNANCE_STATE:{key}"
                )

            states[key] = value

    missing = [key for key in GOVERNANCE_KEYS if key not in states]

    if missing:
        raise AuthorizationError(
            "FAIL_CLOSED:MISSING_GOVERNANCE_STATE:"
            + ",".join(missing)
        )

    return states


def require_current_pre_authorization_state(
    states: dict[str, str],
) -> None:
    expected = {
        "Architecture Approval": EXPECTED_ARCHITECTURE_APPROVAL,
        "Implementation Authorization": EXPECTED_NOT_AUTHORIZED,
        "Production Implementation": EXPECTED_BLOCKED,
        "Production Certification": EXPECTED_NOT_CLAIMED,
    }

    for key, expected_value in expected.items():
        actual = states[key]

        if actual != expected_value:
            raise AuthorizationError(
                "FAIL_CLOSED:INVALID_PRE_AUTHORIZATION_STATE:"
                f"{key}:expected={expected_value}:actual={actual}"
            )


def run_readiness_gate() -> None:
    require_file(READINESS_GATE, "Implementation Readiness Gate")

    result = subprocess.run(
        [sys.executable, str(READINESS_GATE)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    if result.returncode != 0:
        raise AuthorizationError(
            "FAIL_CLOSED:IMPLEMENTATION_READINESS_GATE_FAILED:"
            f"exit={result.returncode}"
        )

    required = (
        "READINESS DECISION: READY_FOR_FORMAL_IMPLEMENTATION_AUTHORIZATION_REVIEW",
        "AUTHORIZATION GRANT: NONE",
        "GOVERNANCE MUTATION: NONE",
        "PRIVILEGED EXECUTION: NONE",
        "RESULT: PASS — IMPLEMENTATION READINESS EVIDENCE VALIDATION COMPLETED",
    )

    combined = f"{result.stdout}\n{result.stderr}"

    for evidence in required:
        if evidence not in combined:
            raise AuthorizationError(
                "FAIL_CLOSED:MISSING_READINESS_EVIDENCE:"
                + evidence
            )


def validate_identity(text: str) -> None:
    required = (
        r"\*\*Document ID:\*\*\s*TAOS-PHASE-B-MANIFEST-001",
        r"\*\*Version:\*\*\s*1\.0\.0",
        r"\*\*Project:\*\*\s*LYRION True Agentic OS",
        r"\*\*Phase:\*\*\s*Phase B",
    )

    for pattern in required:
        if not re.search(pattern, text):
            raise AuthorizationError(
                f"FAIL_CLOSED:MANIFEST_IDENTITY_MISMATCH:{pattern}"
            )


def validate_reviewer(reviewer: str) -> str:
    normalized = reviewer.strip()

    if not normalized:
        raise AuthorizationError("FAIL_CLOSED:REVIEWER_REQUIRED")

    if len(normalized) > 200:
        raise AuthorizationError("FAIL_CLOSED:REVIEWER_TOO_LONG")

    if "\n" in normalized or "\r" in normalized:
        raise AuthorizationError("FAIL_CLOSED:INVALID_REVIEWER_FORMAT")

    return normalized


def validate_review_reference(reference: str) -> str:
    normalized = reference.strip()

    if not normalized:
        raise AuthorizationError("FAIL_CLOSED:REVIEW_REFERENCE_REQUIRED")

    if len(normalized) > 200:
        raise AuthorizationError("FAIL_CLOSED:REVIEW_REFERENCE_TOO_LONG")

    if "\n" in normalized or "\r" in normalized:
        raise AuthorizationError("FAIL_CLOSED:INVALID_REVIEW_REFERENCE_FORMAT")

    return normalized


def replace_governance_state(
    text: str,
    key: str,
    old_value: str,
    new_value: str,
) -> str:
    pattern = re.compile(
        rf"(^\|\s*{re.escape(key)}\s*\|\s*)"
        rf"{re.escape(old_value)}"
        rf"(\s*\|\s*$)",
        re.MULTILINE,
    )

    updated, count = pattern.subn(
        rf"\g<1>{new_value}\g<2>",
        text,
        count=1,
    )

    if count != 1:
        raise AuthorizationError(
            "FAIL_CLOSED:GOVERNANCE_STATE_REPLACEMENT_FAILED:"
            f"{key}:{old_value}->{new_value}"
        )

    return updated


def create_backup() -> Path:
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    backup = MASTER_MANIFEST.with_name(
        MASTER_MANIFEST.name
        + f".pre-implementation-authorization-{timestamp}"
    )

    try:
        shutil.copy2(MASTER_MANIFEST, backup)
    except OSError as exc:
        raise AuthorizationError(
            f"FAIL_CLOSED:BACKUP_CREATION_FAILED:{exc}"
        ) from exc

    return backup


def record_decision(
    *,
    decision: str,
    reviewer: str,
    review_reference: str,
) -> int:
    original_text = read_manifest()
    original_hash = sha256(MASTER_MANIFEST)

    validate_identity(original_text)

    current_states = parse_governance(original_text)
    require_current_pre_authorization_state(current_states)

    print()
    print("===== PRE-AUTHORIZATION STATE =====")

    for key in GOVERNANCE_KEYS:
        print(f"{key}: {current_states[key]}")

    print()
    print("===== HUMAN AUTHORIZATION REVIEW =====")
    print(f"Decision: {decision}")
    print(f"Reviewer: {reviewer}")
    print(f"Review Reference: {review_reference}")

    backup = create_backup()

    updated_text = original_text

    if decision == "AUTHORIZE":
        updated_text = replace_governance_state(
            updated_text,
            "Implementation Authorization",
            EXPECTED_NOT_AUTHORIZED,
            EXPECTED_AUTHORIZED,
        )

        updated_text = replace_governance_state(
            updated_text,
            "Production Implementation",
            EXPECTED_BLOCKED,
            EXPECTED_PRODUCTION_AUTHORIZED,
        )

    elif decision == "DENY":
        # Explicitly preserve the safe pre-authorization state.
        updated_text = replace_governance_state(
            updated_text,
            "Implementation Authorization",
            EXPECTED_NOT_AUTHORIZED,
            EXPECTED_NOT_AUTHORIZED,
        )

        updated_text = replace_governance_state(
            updated_text,
            "Production Implementation",
            EXPECTED_BLOCKED,
            EXPECTED_BLOCKED,
        )

    else:
        raise AuthorizationError(
            f"FAIL_CLOSED:UNSUPPORTED_DECISION:{decision}"
        )

    # Certification is never granted by this tool.
    if EXPECTED_NOT_CLAIMED not in updated_text:
        raise AuthorizationError(
            "FAIL_CLOSED:CERTIFICATION_BOUNDARY_MISSING"
        )

    decision_timestamp = datetime.now(timezone.utc).isoformat()

    audit_record = (
        "\n\n"
        "## Formal Implementation Authorization Decision\n\n"
        f"- **Decision:** {decision}\n"
        f"- **Reviewer:** {reviewer}\n"
        f"- **Review Reference:** {review_reference}\n"
        f"- **Decision Timestamp UTC:** {decision_timestamp}\n"
        f"- **Evidence Baseline:** READY_FOR_FORMAL_IMPLEMENTATION_AUTHORIZATION_REVIEW\n"
        "- **Architecture Approval:** APPROVED\n"
        f"- **Implementation Authorization:** "
        f"{EXPECTED_AUTHORIZED if decision == 'AUTHORIZE' else EXPECTED_NOT_AUTHORIZED}\n"
        f"- **Production Implementation:** "
        f"{EXPECTED_PRODUCTION_AUTHORIZED if decision == 'AUTHORIZE' else EXPECTED_BLOCKED}\n"
        "- **Production Certification:** NOT CLAIMED\n"
        "- **Implementation Executed:** NO\n"
        "- **Privileged Execution:** NONE\n"
        "- **Authorization Grant Mechanism:** Explicit human governance decision\n"
        f"- **Pre-Decision Master Manifest SHA256:** {original_hash}\n"
        "- **Governance Rule:** Authorization does not execute implementation.\n"
    )

    updated_text += audit_record

    try:
        MASTER_MANIFEST.write_text(
            updated_text,
            encoding="utf-8",
        )
    except OSError as exc:
        raise AuthorizationError(
            f"FAIL_CLOSED:MASTER_MANIFEST_WRITE_FAILED:{exc}"
        ) from exc

    after_hash = sha256(MASTER_MANIFEST)

    if after_hash == original_hash:
        raise AuthorizationError(
            "FAIL_CLOSED:EXPECTED_GOVERNANCE_CHANGE_NOT_DETECTED"
        )

    final_text = read_manifest()
    final_states = parse_governance(final_text)

    expected_final = {
        "Architecture Approval": EXPECTED_ARCHITECTURE_APPROVAL,
        "Implementation Authorization": (
            EXPECTED_AUTHORIZED
            if decision == "AUTHORIZE"
            else EXPECTED_NOT_AUTHORIZED
        ),
        "Production Implementation": (
            EXPECTED_PRODUCTION_AUTHORIZED
            if decision == "AUTHORIZE"
            else EXPECTED_BLOCKED
        ),
        "Production Certification": EXPECTED_NOT_CLAIMED,
    }

    for key, expected in expected_final.items():
        actual = final_states[key]

        if actual != expected:
            raise AuthorizationError(
                "FAIL_CLOSED:POST_DECISION_STATE_MISMATCH:"
                f"{key}:expected={expected}:actual={actual}"
            )

    print()
    print("=" * 108)
    print("FORMAL PHASE-B IMPLEMENTATION AUTHORIZATION DECISION")
    print("=" * 108)

    for key in GOVERNANCE_KEYS:
        print(f"{key}: {final_states[key]}")

    print()
    print(f"Decision: {decision}")
    print(f"Reviewer: {reviewer}")
    print(f"Review Reference: {review_reference}")
    print(f"Decision Timestamp UTC: {decision_timestamp}")
    print(f"Backup: {backup}")
    print(f"Pre-Decision SHA256: {original_hash}")
    print(f"Post-Decision SHA256: {after_hash}")
    print("Implementation Executed: NO")
    print("Privileged Execution: NONE")
    print("Production Certification: NOT CLAIMED")

    if decision == "AUTHORIZE":
        print()
        print(
            "RESULT: PASS — FORMAL IMPLEMENTATION AUTHORIZATION RECORDED"
        )
        print(
            "NEXT BOUNDARY: IMPLEMENTATION MAY PROCEED "
            "ONLY THROUGH THE APPROVED PHASE-B IMPLEMENTATION WORKFLOW."
        )
    else:
        print()
        print(
            "RESULT: PASS — FORMAL IMPLEMENTATION AUTHORIZATION DENIED"
        )
        print(
            "PHASE-B IMPLEMENTATION REMAINS BLOCKED."
        )

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Record a formal human Phase-B implementation "
            "authorization decision."
        )
    )

    parser.add_argument(
        "--decision",
        required=True,
        choices=("AUTHORIZE", "DENY"),
        help="Explicit human implementation-authorization decision.",
    )

    parser.add_argument(
        "--reviewer",
        required=True,
        help="Name of the human reviewer making the decision.",
    )

    parser.add_argument(
        "--review-reference",
        required=True,
        help="Unique governance/review reference identifier.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        reviewer = validate_reviewer(args.reviewer)
        review_reference = validate_review_reference(args.review_reference)

        return record_decision(
            decision=args.decision,
            reviewer=reviewer,
            review_reference=review_reference,
        )

    except AuthorizationError as exc:
        print()
        print("=" * 108)
        print("FORMAL PHASE-B IMPLEMENTATION AUTHORIZATION DECISION")
        print("=" * 108)
        print("DECISION: FAIL_CLOSED")
        print(f"REASON: {exc}")
        print("IMPLEMENTATION EXECUTED: NO")
        print("PRIVILEGED EXECUTION: NONE")
        print("RESULT: FAIL")
        return 2


if __name__ == "__main__":
    sys.exit(main())

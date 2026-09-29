#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
PB-DOC-001..007 Validation & Closure Evidence Audit

Purpose
-------
Perform a read-only validation of PB-DOC-001..007 against the currently
established Phase-B documentation/governance evidence model.

This tool:
  - reads canonical Phase-B documents;
  - validates identity and required governance state;
  - checks for technical-validation evidence;
  - checks required architecture/security/governance evidence markers;
  - inspects the current Gap Register state;
  - produces a deterministic validation report;
  - NEVER modifies architecture documents, manifests, or governance state;
  - NEVER changes OPEN/CLOSED states;
  - NEVER grants architecture approval;
  - NEVER authorizes implementation.

Exit codes
----------
0 = all validation checks passed; closure evidence is sufficient
1 = validation completed; one or more closure requirements remain unresolved
2 = runtime/input/configuration failure
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "docs" / "phase-b"

GAP_REGISTER = (
    DOC_ROOT
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md"
)


CANONICAL_DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001": (
        DOC_ROOT
        / "requirements"
        / "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md"
    ),
    "PB-DOC-002": (
        DOC_ROOT
        / "agentic-runtime"
        / "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md"
    ),
    "PB-DOC-003": (
        DOC_ROOT
        / "identity-authority"
        / "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md"
    ),
    "PB-DOC-004": (
        DOC_ROOT
        / "capability"
        / "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md"
    ),
    "PB-DOC-005": (
        DOC_ROOT
        / "agent-harness"
        / "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md"
    ),
    "PB-DOC-006": (
        DOC_ROOT
        / "host-harness"
        / "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md"
    ),
    "PB-DOC-007": (
        DOC_ROOT
        / "universal-computer"
        / "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md"
    ),
}


EXPECTED_GOVERNANCE = {
    "Architecture Approval": "PENDING",
    "Implementation Authorization": "NOT AUTHORIZED",
    "Production Implementation": "BLOCKED",
    "Production Certification": "NOT CLAIMED",
}


@dataclass(frozen=True)
class Finding:
    document_id: str
    level: str
    message: str


findings: list[Finding] = []


def add(document_id: str, level: str, message: str) -> None:
    findings.append(Finding(document_id, level, message))


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc


def field_values(text: str, field: str) -> list[tuple[int, str]]:
    pattern = re.compile(
        rf"^\s*\*\*{re.escape(field)}:\*\*\s*(.+?)\s*$",
        re.MULTILINE,
    )

    result: list[tuple[int, str]] = []

    for match in pattern.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        result.append((line, match.group(1).strip()))

    return result


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def validate_identity(document_id: str, text: str) -> None:
    values = field_values(text, "Document ID")

    if not values:
        add(document_id, "FAIL", "Document ID is missing")
    else:
        add(document_id, "PASS", f"Document ID present: {values[0][1]}")

    for field in ("Version", "Date", "Status"):
        values = field_values(text, field)

        if values:
            add(document_id, "PASS", f"{field} present: {values[0][1]}")
        else:
            add(document_id, "FAIL", f"{field} is missing")


def validate_governance(document_id: str, text: str) -> None:
    for field, expected in EXPECTED_GOVERNANCE.items():
        values = field_values(text, field)

        if not values:
            add(document_id, "WARN", f"{field} field is missing")
            continue

        normalized = {value.upper().strip() for _, value in values}

        if expected in normalized:
            add(
                document_id,
                "PASS",
                f"{field} contains required value: {expected}",
            )
        else:
            add(
                document_id,
                "FAIL",
                f"{field} does not contain required value: {expected}; "
                f"observed={sorted(normalized)}",
            )


def validate_technical_validation(document_id: str, text: str) -> None:
    values = field_values(text, "Technical Validation")

    if values:
        normalized = " | ".join(value for _, value in values)

        if "PASS" in normalized.upper():
            add(
                document_id,
                "PASS",
                f"Technical Validation explicitly records PASS: {normalized}",
            )
        else:
            add(
                document_id,
                "WARN",
                f"Technical Validation exists but no explicit PASS: "
                f"{normalized}",
            )
        return

    # PB-DOC-001 historically uses a different established schema.
    # Do not fabricate a Technical Validation field for it.
    if document_id == "PB-DOC-001":
        add(
            document_id,
            "WARN",
            "Technical Validation field absent; PB-DOC-001 requires "
            "schema-specific review rather than automatic failure",
        )
    else:
        add(
            document_id,
            "FAIL",
            "Technical Validation field/evidence is missing",
        )


def validate_required_evidence(document_id: str, text: str) -> None:
    common_terms = (
        "security",
        "authorization",
        "authority",
        "least privilege",
        "provenance",
        "verification",
        "fail-closed",
        "revalidation",
    )

    present = [
        term
        for term in common_terms
        if term.lower() in text.lower()
    ]

    if len(present) >= 5:
        add(
            document_id,
            "PASS",
            "Core architecture/security evidence markers present: "
            + ", ".join(present),
        )
    else:
        add(
            document_id,
            "WARN",
            "Core architecture/security evidence coverage requires review; "
            f"markers={present}",
        )


def validate_gap_register(document_ids: tuple[str, ...]) -> None:
    if not GAP_REGISTER.is_file():
        add(
            "GAP-REGISTER",
            "FAIL",
            f"Gap Register missing: {GAP_REGISTER}",
        )
        return

    text = read(GAP_REGISTER)
    lines = text.splitlines()

    for document_id in document_ids:
        matches: list[tuple[int, str]] = []

        for index, line in enumerate(lines, start=1):
            if f"| {document_id} |" in line:
                matches.append((index, line.strip()))

        if not matches:
            add(
                document_id,
                "FAIL",
                "No current Gap Register row found",
            )
            continue

        states: list[str] = []

        for _, line in matches:
            parts = [part.strip() for part in line.strip("|").split("|")]

            if len(parts) >= 4:
                states.append(parts[3])

        states = sorted(set(states))

        if states == ["OPEN"]:
            add(
                document_id,
                "INFO",
                "Gap Register currently remains OPEN",
            )
        elif len(states) == 1:
            add(
                document_id,
                "WARN",
                f"Gap Register current state is {states[0]}",
            )
        else:
            add(
                document_id,
                "FAIL",
                f"Conflicting Gap Register states detected: {states}",
            )


def print_report() -> int:
    print("=" * 88)
    print("LYRION TRUE AGENTIC OS — PB-DOC-001..007 VALIDATION AUDIT")
    print("=" * 88)
    print(f"Repository root : {REPO_ROOT}")
    print(f"Documentation   : {DOC_ROOT}")
    print(f"Gap Register    : {GAP_REGISTER}")
    print()

    print("-" * 88)
    print("1. CANONICAL DOCUMENT AVAILABILITY")
    print("-" * 88)

    missing = []

    for document_id, path in CANONICAL_DOCUMENTS.items():
        if path.is_file():
            print(f"PASS: {document_id}: {path}")
        else:
            print(f"FAIL: {document_id}: {path}")
            missing.append(document_id)

    if missing:
        print()
        print(
            "ERROR: Missing canonical documents: "
            + ", ".join(missing)
        )
        return 2

    print()
    print("-" * 88)
    print("2. DOCUMENT VALIDATION")
    print("-" * 88)

    for document_id, path in CANONICAL_DOCUMENTS.items():
        text = read(path)

        print()
        print(f"[{document_id}]")
        print(f"Path: {path}")

        validate_identity(document_id, text)
        validate_governance(document_id, text)
        validate_technical_validation(document_id, text)
        validate_required_evidence(document_id, text)

        for finding in findings:
            if finding.document_id != document_id:
                continue

            print(f"  {finding.level}: {finding.message}")

    print()
    print("-" * 88)
    print("3. GAP REGISTER RECONCILIATION")
    print("-" * 88)

    validate_gap_register(tuple(CANONICAL_DOCUMENTS.keys()))

    for finding in findings:
        if finding.document_id not in CANONICAL_DOCUMENTS:
            print(
                f"{finding.level}: "
                f"{finding.document_id}: "
                f"{finding.message}"
            )

    print()
    print("-" * 88)
    print("4. GOVERNANCE SAFETY INVARIANTS")
    print("-" * 88)

    print("Architecture Approval        : MUST REMAIN PENDING")
    print("Implementation Authorization : MUST REMAIN NOT AUTHORIZED")
    print("Production Implementation   : MUST REMAIN BLOCKED")
    print("Production Certification    : MUST REMAIN NOT CLAIMED")

    print()
    print("-" * 88)
    print("5. VALIDATION DECISION")
    print("-" * 88)

    failures = [
        finding
        for finding in findings
        if finding.level == "FAIL"
    ]

    warnings = [
        finding
        for finding in findings
        if finding.level == "WARN"
    ]

    if failures:
        print("RESULT: BLOCKED — REQUIRED VALIDATION EVIDENCE IS MISSING.")
        print(f"Blocking findings: {len(failures)}")
        return 1

    if warnings:
        print(
            "RESULT: INCOMPLETE — NO HARD FAILURE, BUT "
            "CLOSURE EVIDENCE REQUIRES REVIEW."
        )
        print(f"Warnings requiring review: {len(warnings)}")
        return 1

    print(
        "RESULT: PASS — PB-DOC-001..007 CLOSURE EVIDENCE "
        "IS STRUCTURALLY SUFFICIENT."
    )
    print(
        "NOTE: This does NOT close Gap Register entries, "
        "approve architecture, or authorize implementation."
    )
    return 0


def main() -> int:
    try:
        return print_report()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

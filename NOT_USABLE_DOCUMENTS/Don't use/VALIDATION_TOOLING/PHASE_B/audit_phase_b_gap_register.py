#!/usr/bin/env python3
"""
LYRION True Agentic OS
Phase-B Documentation Gap Register Audit

Purpose
-------
Read-only evidence audit for PB-DOC-001 through PB-DOC-007.

This tool:
- DOES NOT modify any project file.
- DOES NOT modify the Gap Register.
- DOES NOT modify the Master Manifest.
- DOES NOT change governance state.
- DOES NOT grant Architecture Approval.
- DOES NOT authorize implementation.
- DOES NOT declare production certification.

It enumerates:
1. Canonical PB-DOC-001..007 documents.
2. Their governance/status fields.
3. Every Gap Register occurrence for PB-DOC-001..007.
4. Line numbers and surrounding context.
5. Potential state conflicts.
6. Evidence relevant to determining whether closure is justified.

Exit codes:
    0 = audit completed; no parser/runtime failure.
    1 = audit completed but evidence conflicts/ambiguities were detected.
    2 = audit could not be completed.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path.cwd()

GAP_REGISTER = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md"
)

CANONICAL_DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001": REPO_ROOT
    / "docs"
    / "phase-b"
    / "requirements"
    / "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-002": REPO_ROOT
    / "docs"
    / "phase-b"
    / "agentic-runtime"
    / "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003": REPO_ROOT
    / "docs"
    / "phase-b"
    / "identity-authority"
    / "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004": REPO_ROOT
    / "docs"
    / "phase-b"
    / "capability"
    / "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-005": REPO_ROOT
    / "docs"
    / "phase-b"
    / "agent-harness"
    / "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006": REPO_ROOT
    / "docs"
    / "phase-b"
    / "host-harness"
    / "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-007": REPO_ROOT
    / "docs"
    / "phase-b"
    / "universal-computer"
    / "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",
}


TARGET_DOCS = tuple(CANONICAL_DOCUMENTS.keys())

GOVERNANCE_FIELDS = (
    "Status",
    "Technical Validation",
    "Architecture Approval",
    "Implementation Authorization",
    "Production Implementation",
    "Production Certification",
)

STATE_WORDS = (
    "OPEN",
    "CLOSED",
    "PENDING",
    "PASS",
    "FAILED",
    "BLOCKED",
    "NOT AUTHORIZED",
    "NOT CLAIMED",
)


@dataclass(frozen=True)
class Occurrence:
    document_id: str
    line_number: int
    line: str
    context_start: int
    context_end: int


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def lines(text: str) -> list[str]:
    return text.splitlines()


def print_header(title: str) -> None:
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def print_subheader(title: str) -> None:
    print()
    print("-" * 88)
    print(title)
    print("-" * 88)


def extract_field_values(text: str, field: str) -> list[tuple[int, str]]:
    """
    Extract markdown-style governance fields.

    Supports:
        **Status:** VALUE
        Status: VALUE
        | Status | VALUE |
    """
    results: list[tuple[int, str]] = []

    pattern = re.compile(
        rf"""
        (?:
            ^\s*\*\*{re.escape(field)}:\*\*\s*(.+?)\s*$
            |
            ^\s*{re.escape(field)}:\s*(.+?)\s*$
            |
            ^\s*\|\s*{re.escape(field)}\s*\|\s*(.+?)\s*\|\s*$
        )
        """,
        re.IGNORECASE | re.MULTILINE | re.VERBOSE,
    )

    for match in pattern.finditer(text):
        value = next(
            (group for group in match.groups() if group is not None),
            "",
        ).strip()

        line_number = text[: match.start()].count("\n") + 1
        results.append((line_number, value))

    return results


def extract_document_identity(text: str) -> dict[str, list[tuple[int, str]]]:
    fields = ("Document ID", "Version", "Date", "Status")
    return {
        field: extract_field_values(text, field)
        for field in fields
    }


def find_occurrences(
    text: str,
    document_id: str,
    context_radius: int = 2,
) -> list[Occurrence]:
    source_lines = lines(text)
    pattern = re.compile(rf"\b{re.escape(document_id)}\b")

    occurrences: list[Occurrence] = []

    for index, line in enumerate(source_lines):
        if pattern.search(line):
            occurrences.append(
                Occurrence(
                    document_id=document_id,
                    line_number=index + 1,
                    line=line,
                    context_start=max(1, index + 1 - context_radius),
                    context_end=min(
                        len(source_lines),
                        index + 1 + context_radius,
                    ),
                )
            )

    return occurrences


def classify_gap_state(line: str) -> str | None:
    """
    Classify explicit Gap Register table states.

    Expected examples:
        | PB-DOC-001 | ... | CRITICAL | OPEN |
        | PB-DOC-013 | ... | HIGH | CLOSED — BASELINE VALIDATED; ... |
    """
    if "|" not in line:
        return None

    parts = [part.strip() for part in line.strip().strip("|").split("|")]

    if len(parts) < 4:
        return None

    state = parts[-1]

    if state.upper().startswith("OPEN"):
        return "OPEN"

    if state.upper().startswith("CLOSED"):
        return "CLOSED"

    return None


def find_gap_register_table_occurrences(
    text: str,
    document_id: str,
) -> list[tuple[int, str, str | None]]:
    results: list[tuple[int, str, str | None]] = []

    for line_number, line in enumerate(lines(text), start=1):
        if document_id not in line:
            continue

        results.append(
            (
                line_number,
                line,
                classify_gap_state(line),
            )
        )

    return results


def surrounding_context(
    source_lines: list[str],
    line_number: int,
    radius: int = 2,
) -> list[tuple[int, str]]:
    index = line_number - 1
    start = max(0, index - radius)
    end = min(len(source_lines), index + radius + 1)

    return [
        (line_index + 1, source_lines[line_index])
        for line_index in range(start, end)
    ]


def evaluate_document(
    document_id: str,
    path: Path,
    text: str,
) -> tuple[bool, list[str]]:
    findings: list[str] = []
    sufficient = True

    identity = extract_document_identity(text)

    if not identity["Document ID"]:
        findings.append("MISSING Document ID")
        sufficient = False

    if not identity["Version"]:
        findings.append("MISSING Version")
        sufficient = False

    if not identity["Date"]:
        findings.append("MISSING Date")
        sufficient = False

    if not identity["Status"]:
        findings.append("MISSING Status")
        sufficient = False

    for field in GOVERNANCE_FIELDS[1:]:
        values = extract_field_values(text, field)

        if not values:
            findings.append(f"MISSING {field}")

    # Important:
    # We intentionally DO NOT interpret mere existence of fields as closure.
    # PB-DOC-001..007 require evidence review, not automatic closure.
    status_values = [
        value for _, value in identity["Status"]
    ]

    if status_values:
        unique_statuses = {
            re.sub(r"\s+", " ", value).strip()
            for value in status_values
        }

        if len(unique_statuses) > 1:
            findings.append(
                "MULTIPLE Status values detected: "
                + " | ".join(sorted(unique_statuses))
            )
            sufficient = False

    technical_values = extract_field_values(
        text,
        "Technical Validation",
    )

    if technical_values:
        normalized = [
            value.upper()
            for _, value in technical_values
        ]

        if not any("PASS" in value for value in normalized):
            findings.append(
                "No explicit Technical Validation PASS found"
            )
            sufficient = False
    else:
        sufficient = False

    architecture_values = extract_field_values(
        text,
        "Architecture Approval",
    )

    if architecture_values:
        if any(
            "APPROVED" in value.upper()
            for _, value in architecture_values
        ):
            findings.append(
                "Architecture Approval appears APPROVED; "
                "requires formal governance reconciliation"
            )
            sufficient = False

    implementation_values = extract_field_values(
        text,
        "Implementation Authorization",
    )

    if implementation_values:
        if not all(
            "NOT AUTHORIZED" in value.upper()
            for _, value in implementation_values
        ):
            findings.append(
                "Implementation Authorization is not consistently "
                "NOT AUTHORIZED"
            )
            sufficient = False

    production_values = extract_field_values(
        text,
        "Production Implementation",
    )

    if production_values:
        if not all(
            "BLOCKED" in value.upper()
            for _, value in production_values
        ):
            findings.append(
                "Production Implementation is not consistently BLOCKED"
            )
            sufficient = False

    certification_values = extract_field_values(
        text,
        "Production Certification",
    )

    if certification_values:
        if not all(
            "NOT CLAIMED" in value.upper()
            for _, value in certification_values
        ):
            findings.append(
                "Production Certification is not consistently NOT CLAIMED"
            )
            sufficient = False

    return sufficient, findings


def main() -> int:
    print_header(
        "LYRION TRUE AGENTIC OS — PB-DOC-001..007 "
        "GAP REGISTER EVIDENCE AUDIT"
    )

    print(f"Repository root : {REPO_ROOT}")
    print(f"Gap Register    : {GAP_REGISTER}")

    if not GAP_REGISTER.is_file():
        print()
        print("ERROR: Gap Register not found.")
        return 2

    try:
        gap_text = read_text(GAP_REGISTER)
    except OSError as exc:
        print(f"ERROR: Cannot read Gap Register: {exc}")
        return 2

    print_subheader("1. CANONICAL DOCUMENT AVAILABILITY")

    missing_documents: list[str] = []

    for document_id, path in CANONICAL_DOCUMENTS.items():
        exists = path.is_file()

        print(
            f"{'PASS' if exists else 'FAIL'}: "
            f"{document_id}: {path}"
        )

        if not exists:
            missing_documents.append(document_id)

    if missing_documents:
        print()
        print(
            "ERROR: Missing canonical documents: "
            + ", ".join(missing_documents)
        )
        return 2

    print_subheader("2. CANONICAL DOCUMENT GOVERNANCE EVIDENCE")

    document_results: dict[str, tuple[bool, list[str]]] = {}

    for document_id, path in CANONICAL_DOCUMENTS.items():
        print()
        print(f"[{document_id}] {path}")

        try:
            text = read_text(path)
        except OSError as exc:
            print(f"  ERROR: {exc}")
            return 2

        sufficient, findings = evaluate_document(
            document_id,
            path,
            text,
        )

        document_results[document_id] = (
            sufficient,
            findings,
        )

        identity = extract_document_identity(text)

        for field in (
            "Document ID",
            "Version",
            "Date",
            "Status",
        ):
            values = identity[field]

            if values:
                for line_number, value in values:
                    print(
                        f"  PASS: {field} "
                        f"(line {line_number}) = {value}"
                    )
            else:
                print(f"  FAIL: {field} missing")

        for field in GOVERNANCE_FIELDS[1:]:
            values = extract_field_values(text, field)

            if values:
                for line_number, value in values:
                    print(
                        f"  INFO: {field} "
                        f"(line {line_number}) = {value}"
                    )
            else:
                print(f"  WARN: {field} missing")

        if sufficient:
            print(
                "  RESULT: DOCUMENT EVIDENCE STRUCTURALLY "
                "SUFFICIENT FOR FURTHER CLOSURE REVIEW"
            )
        else:
            print(
                "  RESULT: DOCUMENT EVIDENCE REQUIRES "
                "FURTHER RECONCILIATION"
            )

        for finding in findings:
            print(f"  FINDING: {finding}")

    print_subheader(
        "3. EVERY GAP REGISTER OCCURRENCE — PB-DOC-001..007"
    )

    gap_results: dict[
        str,
        list[tuple[int, str, str | None]],
    ] = {}

    for document_id in TARGET_DOCS:
        occurrences = find_gap_register_table_occurrences(
            gap_text,
            document_id,
        )

        gap_results[document_id] = occurrences

        print()
        print(f"[{document_id}] occurrences: {len(occurrences)}")

        if not occurrences:
            print("  FINDING: No occurrence found")
            continue

        for line_number, line, state in occurrences:
            print(
                f"  line {line_number:>4}: "
                f"state={state or 'UNCLASSIFIED'}"
            )
            print(f"    {line}")

            context = surrounding_context(
                lines(gap_text),
                line_number,
                radius=2,
            )

            print("    context:")
            for ctx_line_number, ctx_line in context:
                print(
                    f"      {ctx_line_number:>4}: {ctx_line}"
                )

    print_subheader(
        "4. GAP REGISTER STATE CONSISTENCY ANALYSIS"
    )

    conflicts = 0

    for document_id in TARGET_DOCS:
        occurrences = gap_results[document_id]

        states = [
            state
            for _, _, state in occurrences
            if state is not None
        ]

        unique_states = set(states)

        print(
            f"{document_id}: "
            f"states={sorted(unique_states) if unique_states else 'NONE'}"
        )

        if len(unique_states) > 1:
            conflicts += 1
            print(
                "  BLOCKING FINDING: Multiple explicit Gap Register "
                "states detected."
            )

        if not states:
            conflicts += 1
            print(
                "  BLOCKING FINDING: No classified Gap Register state."
            )

    print_subheader(
        "5. CANONICAL DOCUMENT ↔ GAP REGISTER RECONCILIATION"
    )

    for document_id in TARGET_DOCS:
        sufficient, findings = document_results[document_id]

        states = {
            state
            for _, _, state in gap_results[document_id]
            if state is not None
        }

        print()
        print(document_id)
        print(
            f"  Document evidence structurally sufficient: "
            f"{'YES' if sufficient else 'NO'}"
        )
        print(
            f"  Gap Register states: "
            f"{sorted(states) if states else 'NONE'}"
        )

        # Deliberately conservative:
        # A document is NOT declared CLOSED merely because its
        # technical validation passes. Formal closure requires
        # consistent source evidence and governance reconciliation.
        if "OPEN" in states and "CLOSED" in states:
            conflicts += 1
            print(
                "  RESULT: CONFLICT — OPEN and CLOSED states coexist."
            )
        elif "OPEN" in states:
            print(
                "  RESULT: CURRENT GAP REGISTER EVIDENCE REMAINS OPEN."
            )
        elif "CLOSED" in states:
            print(
                "  RESULT: GAP REGISTER RECORDS CLOSED; "
                "independent closure evidence still requires review."
            )
        else:
            print(
                "  RESULT: UNRESOLVED GAP REGISTER STATE."
            )

        for finding in findings:
            print(f"  DOCUMENT FINDING: {finding}")

    print_subheader("6. GOVERNANCE SAFETY CHECK")

    print("Architecture Approval       : MUST REMAIN PENDING")
    print("Implementation Authorization : MUST REMAIN NOT AUTHORIZED")
    print("Production Implementation   : MUST REMAIN BLOCKED")
    print("Production Certification    : MUST REMAIN NOT CLAIMED")

    print_subheader("7. AUDIT DECISION")

    print(
        "This script is READ-ONLY and does not modify any architecture "
        "or governance document."
    )

    if conflicts:
        print()
        print(
            f"RESULT: AUDIT COMPLETED WITH {conflicts} "
            "RECONCILIATION CONFLICT(S)."
        )
        print(
            "NEXT ACTION: Inspect the reported evidence before changing "
            "the Gap Register."
        )
        return 1

    print()
    print(
        "RESULT: AUDIT COMPLETED — NO STRUCTURAL GAP-REGISTER "
        "STATE CONFLICT DETECTED."
    )
    print(
        "NOTE: This does NOT authorize closure, architecture approval, "
        "implementation, or production."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

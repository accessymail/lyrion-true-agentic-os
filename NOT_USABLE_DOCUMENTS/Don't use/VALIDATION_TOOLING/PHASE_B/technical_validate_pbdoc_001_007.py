#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
PB-DOC-001..007 Technical Validation Evidence Engine

READ-ONLY.

This tool evaluates the existing PB-DOC-001..007 documents against
document-specific structural, architectural, security, governance,
traceability, and acceptance evidence.

It does NOT:
  - modify documents;
  - modify the Gap Register;
  - change OPEN/CLOSED states;
  - insert Technical Validation fields;
  - grant Architecture Approval;
  - authorize implementation;
  - claim production certification.

Exit codes:
  0 = technical validation evidence sufficient
  1 = validation completed but evidence is incomplete
  2 = runtime/input failure
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

DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001": DOC_ROOT
    / "requirements"
    / "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-002": DOC_ROOT
    / "agentic-runtime"
    / "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003": DOC_ROOT
    / "identity-authority"
    / "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004": DOC_ROOT
    / "capability"
    / "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-005": DOC_ROOT
    / "agent-harness"
    / "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006": DOC_ROOT
    / "host-harness"
    / "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-007": DOC_ROOT
    / "universal-computer"
    / "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",
}


@dataclass(frozen=True)
class Check:
    document: str
    category: str
    name: str
    passed: bool
    detail: str


CHECKS: list[Check] = []


def record(
    document: str,
    category: str,
    name: str,
    passed: bool,
    detail: str,
) -> None:
    CHECKS.append(
        Check(
            document=document,
            category=category,
            name=name,
            passed=passed,
            detail=detail,
        )
    )


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {path}: {exc}") from exc


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def contains(text: str, *terms: str) -> bool:
    lowered = normalize(text)
    return all(term.lower() in lowered for term in terms)


def any_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = normalize(text)
    return any(term.lower() in lowered for term in terms)


def sections(text: str) -> list[str]:
    result: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()

        if re.match(r"^#{1,6}\s+", stripped):
            result.append(re.sub(r"^#{1,6}\s+", "", stripped))

    return result


def field(text: str, name: str) -> list[str]:
    pattern = re.compile(
        rf"^\s*\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$",
        re.MULTILINE,
    )

    return [
        match.group(1).strip()
        for match in pattern.finditer(text)
    ]


def check_identity(document: str, text: str) -> None:
    for name in ("Document ID", "Version", "Date", "Status"):
        values = field(text, name)

        record(
            document,
            "IDENTITY",
            f"{name} present",
            bool(values),
            values[0] if values else "missing",
        )


def check_governance(document: str, text: str) -> None:
    expected = {
        "Architecture Approval": "PENDING",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    for name, expected_value in expected.items():
        values = field(text, name)
        normalized = {value.upper().strip() for value in values}

        record(
            document,
            "GOVERNANCE",
            f"{name} remains {expected_value}",
            expected_value in normalized,
            f"observed={values or ['missing']}",
        )


def check_security(document: str, text: str) -> None:
    security_requirements = (
        (
            "authorization boundary",
            ("authorization", "authority"),
        ),
        (
            "least privilege",
            ("least privilege",),
        ),
        (
            "provenance/audit",
            ("provenance",),
        ),
        (
            "verification",
            ("verification",),
        ),
        (
            "fail-closed safety",
            ("fail-closed", "fail closed"),
        ),
        (
            "revalidation",
            ("revalidation", "re-validate", "revalidate"),
        ),
    )

    for name, terms in security_requirements:
        present = any_term(text, terms)

        record(
            document,
            "SECURITY",
            name,
            present,
            "required security concept detected"
            if present
            else "required security concept not detected",
        )


def check_architecture(document: str, text: str) -> None:
    architecture_terms = (
        "architecture",
        "boundary",
        "interface",
        "contract",
        "lifecycle",
        "execution",
        "component",
    )

    count = sum(
        1
        for term in architecture_terms
        if term.lower() in normalize(text)
    )

    record(
        document,
        "ARCHITECTURE",
        "architecture vocabulary coverage",
        count >= 5,
        f"{count}/{len(architecture_terms)} architecture concepts detected",
    )


def check_traceability(document: str, text: str) -> None:
    trace_refs = tuple(
        f"TR-{index:03d}"
        for index in range(1, 10)
    )

    present = [
        ref
        for ref in trace_refs
        if ref in text
    ]

    record(
        document,
        "TRACEABILITY",
        "traceability references",
        len(present) >= 3,
        f"{len(present)}/9 detected: {present}",
    )


def check_acceptance(document: str, text: str) -> None:
    acceptance_terms = (
        "acceptance",
        "validation",
        "verification",
        "criteria",
        "invariant",
    )

    present = [
        term
        for term in acceptance_terms
        if term.lower() in normalize(text)
    ]

    record(
        document,
        "VALIDATION",
        "acceptance/validation evidence",
        len(present) >= 3,
        f"{len(present)}/{len(acceptance_terms)} detected: {present}",
    )


def document_specific_checks(document: str, text: str) -> None:
    """
    Document-specific evidence checks.

    These are intentionally evidence-oriented. They do not manufacture
    a validation result from a status field.
    """

    rules: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
        "PB-DOC-001": (
            (
                "requirements baseline",
                ("requirements", "baseline"),
            ),
            (
                "functional requirements",
                ("functional", "requirement"),
            ),
            (
                "non-functional requirements",
                ("non-functional", "requirement"),
            ),
            (
                "security requirements",
                ("security", "requirement"),
            ),
            (
                "traceability",
                ("traceability",),
            ),
        ),

        "PB-DOC-002": (
            (
                "agentic runtime",
                ("agentic runtime",),
            ),
            (
                "task execution",
                ("task", "execution"),
            ),
            (
                "agent lifecycle",
                ("agent", "lifecycle"),
            ),
            (
                "delegated authority",
                ("delegated authority",),
            ),
            (
                "execution boundary",
                ("execution boundary",),
            ),
        ),

        "PB-DOC-003": (
            (
                "agent identity",
                ("agent identity",),
            ),
            (
                "authority model",
                ("authority", "model"),
            ),
            (
                "delegated authority",
                ("delegated authority",),
            ),
            (
                "authority attenuation",
                ("authority attenuation",),
            ),
            (
                "revocation/revalidation",
                ("revocation", "revalidation"),
            ),
        ),

        "PB-DOC-004": (
            (
                "capability model",
                ("capability", "model"),
            ),
            (
                "capability authorization",
                ("capability", "authorization"),
            ),
            (
                "least privilege",
                ("least privilege",),
            ),
            (
                "capability boundary",
                ("capability", "boundary"),
            ),
            (
                "execution admission separation",
                ("execution admission",),
            ),
        ),

        "PB-DOC-005": (
            (
                "agent harness",
                ("agent harness",),
            ),
            (
                "agent registration",
                ("agent registration",),
            ),
            (
                "agent lifecycle",
                ("agent lifecycle",),
            ),
            (
                "task binding",
                ("task binding",),
            ),
            (
                "tool invocation boundary",
                ("tool invocation",),
            ),
        ),

        "PB-DOC-006": (
            (
                "host harness",
                ("host harness",),
            ),
            (
                "host boundary",
                ("host", "boundary"),
            ),
            (
                "host integration",
                ("host integration",),
            ),
            (
                "least privilege host access",
                ("least privilege", "host"),
            ),
            (
                "host execution",
                ("host", "execution"),
            ),
        ),

        "PB-DOC-007": (
            (
                "universal computer",
                ("universal computer",),
            ),
            (
                "computer abstraction",
                ("computer", "abstraction"),
            ),
            (
                "application interaction",
                ("application", "interaction"),
            ),
            (
                "host independence",
                ("host", "independent"),
            ),
            (
                "capability boundary",
                ("capability", "boundary"),
            ),
        ),
    }

    for name, terms in rules[document]:
        present = contains(text, *terms)

        record(
            document,
            "DOCUMENT-SPECIFIC",
            name,
            present,
            "required evidence detected"
            if present
            else "required evidence not detected",
        )


def inspect_document(document: str, path: Path) -> None:
    text = read(path)

    check_identity(document, text)
    check_governance(document, text)
    check_security(document, text)
    check_architecture(document, text)
    check_traceability(document, text)
    check_acceptance(document, text)
    document_specific_checks(document, text)

    heading_count = len(sections(text))

    record(
        document,
        "STRUCTURE",
        "document contains structured sections",
        heading_count >= 5,
        f"{heading_count} headings detected",
    )


def inspect_gap_register() -> None:
    if not GAP_REGISTER.is_file():
        record(
            "GAP-REGISTER",
            "RECONCILIATION",
            "Gap Register exists",
            False,
            str(GAP_REGISTER),
        )
        return

    text = read(GAP_REGISTER)

    for document in DOCUMENTS:
        rows = [
            line.strip()
            for line in text.splitlines()
            if f"| {document} |" in line
        ]

        states = []

        for row in rows:
            parts = [
                part.strip()
                for part in row.strip("|").split("|")
            ]

            if len(parts) >= 4:
                states.append(parts[3])

        unique_states = sorted(set(states))

        record(
            document,
            "RECONCILIATION",
            "current Gap Register state is observable",
            bool(unique_states),
            f"states={unique_states}",
        )


def print_report() -> int:
    print("=" * 96)
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-001..007 TECHNICAL VALIDATION EVIDENCE AUDIT")
    print("=" * 96)
    print(f"Repository : {REPO_ROOT}")
    print(f"Documents  : {DOC_ROOT}")
    print()

    missing = [
        document
        for document, path in DOCUMENTS.items()
        if not path.is_file()
    ]

    if missing:
        print("BLOCKED: Missing canonical documents:")
        for document in missing:
            print(f"  - {document}")
        return 2

    for document, path in DOCUMENTS.items():
        print()
        print("-" * 96)
        print(document)
        print(path)
        print("-" * 96)

        before = len(CHECKS)

        inspect_document(document, path)

        for check in CHECKS[before:]:
            status = "PASS" if check.passed else "FAIL"
            print(
                f"{status}: "
                f"[{check.category}] "
                f"{check.name} — {check.detail}"
            )

    print()
    print("-" * 96)
    print("GAP REGISTER RECONCILIATION")
    print("-" * 96)

    before = len(CHECKS)
    inspect_gap_register()

    for check in CHECKS[before:]:
        status = "PASS" if check.passed else "FAIL"
        print(
            f"{status}: "
            f"[{check.category}] "
            f"{check.document}: "
            f"{check.name} — {check.detail}"
        )

    failures = [
        check
        for check in CHECKS
        if not check.passed
        and check.category
        not in {"RECONCILIATION"}
    ]

    print()
    print("-" * 96)
    print("GOVERNANCE SAFETY")
    print("-" * 96)
    print("Architecture Approval        : PENDING")
    print("Implementation Authorization : NOT AUTHORIZED")
    print("Production Implementation   : BLOCKED")
    print("Production Certification    : NOT CLAIMED")

    print()
    print("-" * 96)
    print("DECISION")
    print("-" * 96)

    if failures:
        print(
            "RESULT: INCOMPLETE — technical validation evidence "
            "requires additional review."
        )
        print(f"Technical evidence failures: {len(failures)}")
        print()
        print(
            "NO DOCUMENT, GAP REGISTER, MANIFEST, OR GOVERNANCE "
            "STATE WAS MODIFIED."
        )
        return 1

    print(
        "RESULT: PASS — technical validation evidence is "
        "structurally sufficient for review."
    )
    print()
    print(
        "IMPORTANT: PASS does not close the Gap Register, "
        "approve architecture, authorize implementation, "
        "or claim production certification."
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

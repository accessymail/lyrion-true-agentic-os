#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
PB-DOC-001..007 Evidence Reconciliation Analyzer

READ-ONLY.

Purpose:
    Reconcile the findings produced by technical_validate_pbdoc_001_007.py
    against the actual PB-DOC-001..007 document content.

This tool does NOT:
    - modify documentation;
    - modify the Gap Register;
    - modify manifests;
    - change governance state;
    - add missing fields;
    - declare architecture approval;
    - authorize implementation;
    - claim production certification.

Classification:
    PRESENT
    ABSENT
    ALTERNATE_EVIDENCE
    REQUIRES_REVIEW

The purpose is to distinguish genuine documentation gaps from validator
false negatives before any document is edited.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "docs" / "phase-b"

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

GAP_REGISTER = (
    DOC_ROOT
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md"
)


@dataclass(frozen=True)
class Finding:
    document: str
    category: str
    finding: str
    classification: str
    evidence: str


FINDINGS: list[Finding] = []


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def add(
    document: str,
    category: str,
    finding: str,
    classification: str,
    evidence: str,
) -> None:
    FINDINGS.append(
        Finding(
            document=document,
            category=category,
            finding=finding,
            classification=classification,
            evidence=evidence,
        )
    )


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {path}: {exc}") from exc


def has_any(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = normalize(text)
    return [
        term
        for term in terms
        if term.lower() in lowered
    ]


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []

    for line in text.splitlines():
        line = line.strip()

        if re.match(r"^#{1,6}\s+", line):
            headings.append(
                re.sub(r"^#{1,6}\s+", "", line)
            )

    return headings


def extract_context(
    text: str,
    terms: tuple[str, ...],
    radius: int = 2,
) -> list[str]:
    lines = text.splitlines()
    matches: list[str] = []

    lowered_terms = tuple(
        term.lower()
        for term in terms
    )

    for index, line in enumerate(lines):
        lowered = line.lower()

        if any(term in lowered for term in lowered_terms):
            start = max(0, index - radius)
            end = min(len(lines), index + radius + 1)

            block = "\n".join(
                f"{number + 1:04d}: {lines[number]}"
                for number in range(start, end)
            )

            matches.append(block)

    return matches[:5]


def reconcile_pbdoc_001(text: str) -> None:
    document = "PB-DOC-001"

    governance_terms = (
        "architecture approval",
        "implementation authorization",
        "production implementation",
        "production certification",
    )

    governance_hits = has_any(text, governance_terms)

    if len(governance_hits) == 4:
        add(
            document,
            "GOVERNANCE",
            "four Phase-B governance fields",
            "PRESENT",
            ", ".join(governance_hits),
        )
    elif governance_hits:
        add(
            document,
            "GOVERNANCE",
            "four Phase-B governance fields",
            "REQUIRES_REVIEW",
            f"only {len(governance_hits)}/4 labels detected: "
            f"{governance_hits}",
        )
    else:
        add(
            document,
            "GOVERNANCE",
            "four Phase-B governance fields",
            "ABSENT",
            "none of the four labels detected",
        )

    least_privilege = has_any(
        text,
        (
            "least privilege",
            "least-privilege",
            "minimum privilege",
            "minimal privilege",
            "privilege minimization",
        ),
    )

    add(
        document,
        "SECURITY",
        "least-privilege evidence",
        "PRESENT" if least_privilege else "ABSENT",
        ", ".join(least_privilege)
        if least_privilege
        else "no explicit least-privilege terminology detected",
    )

    traceability = has_any(
        text,
        tuple(f"TR-{i:03d}" for i in range(1, 10)),
    )

    if traceability:
        add(
            document,
            "TRACEABILITY",
            "TR-001..TR-009 references",
            "PRESENT",
            ", ".join(traceability),
        )
    else:
        alternate = has_any(
            text,
            (
                "traceability matrix",
                "requirements traceability",
                "traceability",
                "requirement mapping",
                "requirement-to-architecture",
                "cross-reference",
                "cross reference",
            ),
        )

        add(
            document,
            "TRACEABILITY",
            "TR-001..TR-009 references",
            "ALTERNATE_EVIDENCE" if alternate else "ABSENT",
            ", ".join(alternate)
            if alternate
            else "no traceability mechanism detected",
        )

    nfr = has_any(
        text,
        (
            "non-functional requirement",
            "non functional requirement",
            "nonfunctional requirement",
            "quality attribute",
            "performance requirement",
            "availability requirement",
            "reliability requirement",
            "scalability requirement",
        ),
    )

    add(
        document,
        "REQUIREMENTS",
        "non-functional requirements",
        "PRESENT" if nfr else "ABSENT",
        ", ".join(nfr)
        if nfr
        else "no explicit NFR terminology detected",
    )


def reconcile_pbdoc_002_to_007(
    document: str,
    text: str,
) -> None:
    least_privilege_terms = (
        "least privilege",
        "least-privilege",
        "minimum privilege",
        "minimal privilege",
        "privilege attenuation",
        "authority attenuation",
    )

    traceability_terms = tuple(
        f"TR-{i:03d}"
        for i in range(1, 10)
    )

    least_privilege = has_any(
        text,
        least_privilege_terms,
    )

    if least_privilege:
        add(
            document,
            "SECURITY",
            "least-privilege evidence",
            "PRESENT",
            ", ".join(least_privilege),
        )
    else:
        alternate = has_any(
            text,
            (
                "bounded authority",
                "restricted authority",
                "scoped authority",
                "authority boundary",
                "capability attenuation",
                "authority attenuation",
            ),
        )

        add(
            document,
            "SECURITY",
            "least-privilege evidence",
            "ALTERNATE_EVIDENCE" if alternate else "ABSENT",
            ", ".join(alternate)
            if alternate
            else "no explicit or equivalent terminology detected",
        )

    traceability = has_any(
        text,
        traceability_terms,
    )

    if traceability:
        add(
            document,
            "TRACEABILITY",
            "TR-001..TR-009 references",
            "PRESENT",
            ", ".join(traceability),
        )
    else:
        alternate = has_any(
            text,
            (
                "traceability matrix",
                "requirements traceability",
                "traceability",
                "requirement mapping",
                "cross-reference",
                "cross reference",
                "dependency mapping",
                "interface mapping",
            ),
        )

        add(
            document,
            "TRACEABILITY",
            "TR-001..TR-009 references",
            "ALTERNATE_EVIDENCE" if alternate else "ABSENT",
            ", ".join(alternate)
            if alternate
            else "no traceability mechanism detected",
        )


def inspect_gap_register() -> None:
    if not GAP_REGISTER.is_file():
        add(
            "GAP-REGISTER",
            "RECONCILIATION",
            "Gap Register exists",
            "ABSENT",
            str(GAP_REGISTER),
        )
        return

    text = read(GAP_REGISTER)

    for document in DOCUMENTS:
        matches = [
            line.strip()
            for line in text.splitlines()
            if f"| {document} |" in line
        ]

        if not matches:
            add(
                document,
                "RECONCILIATION",
                "Gap Register entry",
                "ABSENT",
                "no canonical row detected",
            )
            continue

        states: list[str] = []

        for row in matches:
            parts = [
                item.strip()
                for item in row.strip("|").split("|")
            ]

            if len(parts) >= 4:
                states.append(parts[3])

        unique = sorted(set(states))

        if unique == ["OPEN"]:
            classification = "PRESENT"
        elif len(unique) > 1:
            classification = "REQUIRES_REVIEW"
        else:
            classification = "REQUIRES_REVIEW"

        add(
            document,
            "RECONCILIATION",
            "Gap Register state",
            classification,
            f"states={unique}",
        )


def inspect_document(document: str, path: Path) -> None:
    text = read(path)

    if document == "PB-DOC-001":
        reconcile_pbdoc_001(text)
    else:
        reconcile_pbdoc_002_to_007(document, text)

    headings = extract_headings(text)

    add(
        document,
        "STRUCTURE",
        "structured document",
        "PRESENT" if len(headings) >= 5 else "REQUIRES_REVIEW",
        f"{len(headings)} headings detected",
    )

    # Produce useful context for manual review.
    contexts = extract_context(
        text,
        (
            "traceability",
            "least privilege",
            "non-functional",
            "non functional",
            "authority attenuation",
        ),
    )

    if contexts:
        print()
        print(f"[{document}] Relevant existing evidence context:")
        for context in contexts:
            print(context)
            print()


def print_summary() -> int:
    print("=" * 100)
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-001..007 EVIDENCE RECONCILIATION")
    print("=" * 100)
    print(f"Repository: {REPO_ROOT}")
    print()

    if not all(path.is_file() for path in DOCUMENTS.values()):
        missing = [
            document
            for document, path in DOCUMENTS.items()
            if not path.is_file()
        ]

        print("RUNTIME FAILURE: missing canonical documents:")
        for document in missing:
            print(f"  - {document}")

        return 2

    for document, path in DOCUMENTS.items():
        print("-" * 100)
        print(document)
        print(path)
        print("-" * 100)

        inspect_document(document, path)

    print()
    print("-" * 100)
    print("GAP REGISTER")
    print("-" * 100)

    inspect_gap_register()

    print()
    print("-" * 100)
    print("RECONCILIATION RESULT")
    print("-" * 100)

    order = {
        "ABSENT": 0,
        "REQUIRES_REVIEW": 1,
        "ALTERNATE_EVIDENCE": 2,
        "PRESENT": 3,
    }

    for finding in FINDINGS:
        if finding.category == "STRUCTURE":
            continue

        print(
            f"{finding.classification:18} "
            f"{finding.document:12} "
            f"[{finding.category}] "
            f"{finding.finding}"
        )
        print(f"  Evidence: {finding.evidence}")

    print()
    print("-" * 100)
    print("CLASSIFICATION SUMMARY")
    print("-" * 100)

    counts = {
        "PRESENT": 0,
        "ALTERNATE_EVIDENCE": 0,
        "REQUIRES_REVIEW": 0,
        "ABSENT": 0,
    }

    for finding in FINDINGS:
        counts[finding.classification] += 1

    for name, count in counts.items():
        print(f"{name:20}: {count}")

    print()
    print("-" * 100)
    print("GOVERNANCE SAFETY")
    print("-" * 100)
    print("Architecture Approval        : PENDING")
    print("Implementation Authorization : NOT AUTHORIZED")
    print("Production Implementation   : BLOCKED")
    print("Production Certification    : NOT CLAIMED")

    print()
    print("-" * 100)
    print("IMPORTANT")
    print("-" * 100)
    print("This analyzer is READ-ONLY.")
    print("No document was modified.")
    print("No Gap Register state was modified.")
    print("No manifest was modified.")
    print("No implementation authority was granted.")
    print("No production certification was claimed.")

    # Exit 0 only when there are no unresolved findings.
    unresolved = [
        finding
        for finding in FINDINGS
        if finding.classification in {
            "ABSENT",
            "REQUIRES_REVIEW",
        }
        and finding.category != "RECONCILIATION"
    ]

    print()
    if unresolved:
        print(
            f"RESULT: REQUIRES REVIEW — "
            f"{len(unresolved)} evidence findings remain unresolved."
        )
        return 1

    print(
        "RESULT: RECONCILED — no unresolved evidence findings detected."
    )
    return 0


def main() -> int:
    try:
        return print_summary()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

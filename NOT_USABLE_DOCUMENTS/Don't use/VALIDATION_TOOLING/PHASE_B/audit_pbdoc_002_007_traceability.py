#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
PB-DOC-002..007 Traceability Audit

READ-ONLY.

Purpose:
    Determine whether PB-DOC-002..007 contain sufficient traceability
    evidence for the Phase-B architecture, even when they do not use
    literal TR-001..TR-009 identifiers.

This is an evidence audit, NOT a governance operation.

It does NOT:
    - modify any document;
    - modify the Gap Register;
    - modify manifests;
    - add traceability references;
    - close gaps;
    - approve architecture;
    - authorize implementation;
    - claim certification.

Classification:
    EXPLICIT
    EQUIVALENT
    PARTIAL
    MISSING
    REVIEW_REQUIRED
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "docs" / "phase-b"

DOCUMENTS: dict[str, Path] = {
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
class Finding:
    document: str
    category: str
    classification: str
    detail: str


FINDINGS: list[Finding] = []


def add(
    document: str,
    category: str,
    classification: str,
    detail: str,
) -> None:
    FINDINGS.append(
        Finding(
            document=document,
            category=category,
            classification=classification,
            detail=detail,
        )
    )


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {path}: {exc}") from exc


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def matching_lines(
    text: str,
    patterns: tuple[str, ...],
) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []

    compiled = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in patterns
    ]

    for number, line in enumerate(text.splitlines(), start=1):
        if any(pattern.search(line) for pattern in compiled):
            results.append((number, line.rstrip()))

    return results


def context(
    text: str,
    patterns: tuple[str, ...],
    radius: int = 2,
    limit: int = 8,
) -> list[str]:
    lines = text.splitlines()
    output: list[str] = []

    compiled = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in patterns
    ]

    for index, line in enumerate(lines):
        if not any(pattern.search(line) for pattern in compiled):
            continue

        start = max(0, index - radius)
        end = min(len(lines), index + radius + 1)

        block = "\n".join(
            f"{n + 1:04d}: {lines[n]}"
            for n in range(start, end)
        )

        output.append(block)

        if len(output) >= limit:
            break

    return output


def explicit_tr_refs(text: str) -> list[str]:
    found: list[str] = []

    for number in range(1, 10):
        reference = f"TR-{number:03d}"

        if re.search(
            rf"(?<![A-Z0-9]){re.escape(reference)}(?![A-Z0-9])",
            text,
            re.IGNORECASE,
        ):
            found.append(reference)

    return found


def requirement_identifiers(text: str) -> list[str]:
    """
    Detect likely internal requirement identifiers.

    This intentionally uses several common project-specific patterns
    without assuming that any one pattern is authoritative.
    """

    patterns = (
        r"\b[A-Z]{2,8}-[A-Z]{1,8}-\d{2,4}\b",
        r"\b[A-Z]{2,8}-\d{2,4}\b",
        r"\bREQ-[A-Z0-9_-]+\b",
        r"\bCORE-[A-Z0-9_-]+\b",
    )

    found: set[str] = set()

    for pattern in patterns:
        for match in re.findall(pattern, text):
            found.add(match)

    return sorted(found)


def inspect_explicit_traceability(
    document: str,
    text: str,
) -> None:
    refs = explicit_tr_refs(text)

    if len(refs) == 9:
        classification = "EXPLICIT"
    elif refs:
        classification = "PARTIAL"
    else:
        classification = "MISSING"

    add(
        document,
        "TR-001..TR-009",
        classification,
        f"Explicit references detected: "
        f"{refs if refs else 'none'}",
    )


def inspect_traceability_sections(
    document: str,
    text: str,
) -> None:
    patterns = (
        r"\btraceability\b",
        r"\btraceability matrix\b",
        r"\brequirement mapping\b",
        r"\brequirements mapping\b",
        r"\bcross[- ]reference\b",
        r"\bdependency mapping\b",
        r"\binterface mapping\b",
        r"\barchitecture mapping\b",
        r"\bverification mapping\b",
    )

    matches = matching_lines(text, patterns)

    if matches:
        add(
            document,
            "TRACEABILITY-SECTIONS",
            "EQUIVALENT",
            f"{len(matches)} traceability-related lines detected",
        )
    else:
        add(
            document,
            "TRACEABILITY-SECTIONS",
            "MISSING",
            "No traceability/mapping section terminology detected",
        )


def inspect_requirement_ids(
    document: str,
    text: str,
) -> None:
    identifiers = requirement_identifiers(text)

    # Remove common document/version identifiers that do not represent
    # requirement traceability by themselves.
    identifiers = [
        item
        for item in identifiers
        if not item.startswith("TAOS-")
    ]

    if len(identifiers) >= 3:
        add(
            document,
            "REQUIREMENT-IDENTIFIERS",
            "EQUIVALENT",
            f"{len(identifiers)} internal requirement-like identifiers "
            f"detected: {identifiers[:30]}",
        )
    elif identifiers:
        add(
            document,
            "REQUIREMENT-IDENTIFIERS",
            "PARTIAL",
            f"{len(identifiers)} requirement-like identifiers detected: "
            f"{identifiers}",
        )
    else:
        add(
            document,
            "REQUIREMENT-IDENTIFIERS",
            "MISSING",
            "No internal requirement identifiers detected",
        )


def inspect_dependency_mapping(
    document: str,
    text: str,
) -> None:
    patterns = (
        r"\bdepends on\b",
        r"\bdependency\b",
        r"\bdependencies\b",
        r"\bconsumes\b",
        r"\bprovides\b",
        r"\bupstream\b",
        r"\bdownstream\b",
        r"\binterface\b",
        r"\bcontract\b",
        r"\bintegration\b",
        r"\binteroperab",
        r"\brelation(ship)?\b",
    )

    matches = matching_lines(text, patterns)

    if len(matches) >= 5:
        classification = "EQUIVALENT"
    elif matches:
        classification = "PARTIAL"
    else:
        classification = "MISSING"

    add(
        document,
        "DEPENDENCY-MAPPING",
        classification,
        f"{len(matches)} dependency/interface relationship lines",
    )


def inspect_cross_document_links(
    document: str,
    text: str,
) -> None:
    canonical_terms = (
        "PB-DOC-001",
        "PB-DOC-002",
        "PB-DOC-003",
        "PB-DOC-004",
        "PB-DOC-005",
        "PB-DOC-006",
        "PB-DOC-007",
        "PB-DOC-008",
        "PB-DOC-009",
        "PB-DOC-010",
        "PB-DOC-011",
        "PB-DOC-012",
        "PB-DOC-013",
        "PB-DOC-014",
        "PB-DOC-015",
        "PB-DOC-016",
        "PB-DOC-017",
        "PB-DOC-018",
        "PB-DOC-019",
        "PB-DOC-020",
    )

    found = [
        term
        for term in canonical_terms
        if re.search(
            rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])",
            text,
            re.IGNORECASE,
        )
    ]

    if len(found) >= 2:
        classification = "EQUIVALENT"
    elif found:
        classification = "PARTIAL"
    else:
        classification = "MISSING"

    add(
        document,
        "CROSS-DOCUMENT",
        classification,
        f"Canonical PB-DOC references: {found}",
    )


def inspect_architecture_relationships(
    document: str,
    text: str,
) -> None:
    """
    Detect architecture relationship language.

    This is important because a document can have strong traceability
    without literal TR-* identifiers.
    """

    relationship_groups = {
        "identity/authority": (
            "identity",
            "authority",
        ),
        "capability/authorization": (
            "capability",
            "authorization",
        ),
        "execution/admission": (
            "execution",
            "admission",
        ),
        "verification/provenance": (
            "verification",
            "provenance",
        ),
        "agent/host": (
            "agent",
            "host",
        ),
        "host/application": (
            "host",
            "application",
        ),
    }

    satisfied: list[str] = []

    lowered = normalized(text)

    for name, terms in relationship_groups.items():
        if all(term in lowered for term in terms):
            satisfied.append(name)

    if len(satisfied) >= 3:
        classification = "EQUIVALENT"
    elif satisfied:
        classification = "PARTIAL"
    else:
        classification = "MISSING"

    add(
        document,
        "ARCHITECTURE-RELATIONSHIPS",
        classification,
        f"Detected relationship groups: {satisfied}",
    )


def inspect_document(document: str, path: Path) -> None:
    text = read(path)

    print()
    print("=" * 100)
    print(document)
    print(path)
    print("=" * 100)

    inspect_explicit_traceability(document, text)
    inspect_traceability_sections(document, text)
    inspect_requirement_ids(document, text)
    inspect_dependency_mapping(document, text)
    inspect_cross_document_links(document, text)
    inspect_architecture_relationships(document, text)

    evidence_context = context(
        text,
        (
            r"\btraceability\b",
            r"\brequirement mapping\b",
            r"\bdependency\b",
            r"\binterface\b",
            r"\bcross[- ]reference\b",
            r"\bverification\b",
        ),
    )

    if evidence_context:
        print()
        print("Existing traceability-related context:")
        for block in evidence_context:
            print(block)
            print()


def print_results() -> int:
    print("=" * 100)
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-002..007 TRACEABILITY AUDIT")
    print("=" * 100)
    print(f"Repository: {REPO_ROOT}")
    print()

    missing = [
        document
        for document, path in DOCUMENTS.items()
        if not path.is_file()
    ]

    if missing:
        print("RUNTIME FAILURE — missing canonical documents:")
        for document in missing:
            print(f"  - {document}")
        return 2

    for document, path in DOCUMENTS.items():
        inspect_document(document, path)

    print()
    print("=" * 100)
    print("TRACEABILITY FINDINGS")
    print("=" * 100)

    for finding in FINDINGS:
        print(
            f"{finding.classification:16} "
            f"{finding.document:12} "
            f"[{finding.category}] "
            f"{finding.detail}"
        )

    print()
    print("=" * 100)
    print("PER-DOCUMENT ASSESSMENT")
    print("=" * 100)

    for document in DOCUMENTS:
        findings = [
            finding
            for finding in FINDINGS
            if finding.document == document
        ]

        explicit = [
            finding
            for finding in findings
            if finding.category == "TR-001..TR-009"
        ]

        equivalent = [
            finding
            for finding in findings
            if finding.classification == "EQUIVALENT"
        ]

        missing_findings = [
            finding
            for finding in findings
            if finding.classification == "MISSING"
        ]

        if any(
            finding.classification == "EXPLICIT"
            for finding in explicit
        ):
            assessment = "EXPLICIT_TRACEABILITY"
        elif equivalent and not missing_findings:
            assessment = "EQUIVALENT_TRACEABILITY"
        elif equivalent:
            assessment = "MIXED_EVIDENCE_REQUIRES_REVIEW"
        else:
            assessment = "INSUFFICIENT_TRACEABILITY_EVIDENCE"

        print(
            f"{document}: {assessment}"
        )

    print()
    print("=" * 100)
    print("GOVERNANCE SAFETY")
    print("=" * 100)
    print("Architecture Approval        : PENDING")
    print("Implementation Authorization : NOT AUTHORIZED")
    print("Production Implementation   : BLOCKED")
    print("Production Certification    : NOT CLAIMED")

    print()
    print("=" * 100)
    print("READ-ONLY GUARANTEE")
    print("=" * 100)
    print("No Phase-B document was modified.")
    print("No Gap Register state was modified.")
    print("No manifest was modified.")
    print("No governance state was modified.")
    print("No implementation authority was granted.")

    unresolved = [
        finding
        for finding in FINDINGS
        if finding.classification
        in {"MISSING", "REVIEW_REQUIRED", "PARTIAL"}
    ]

    print()
    if unresolved:
        print(
            f"RESULT: TRACEABILITY REVIEW REQUIRED — "
            f"{len(unresolved)} findings require interpretation."
        )
        return 1

    print(
        "RESULT: TRACEABILITY EVIDENCE SUFFICIENT FOR REVIEW."
    )
    return 0


def main() -> int:
    try:
        return print_results()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

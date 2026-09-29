#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B PB-DOC-001 / PB-DOC-013 Document Identity Forensic Audit

READ-ONLY EVIDENCE TOOL

Purpose
-------
Investigate the two unresolved document-identity findings reported by
the Phase-B cross-document reconciliation audit:

    PB-DOC-001
    PB-DOC-013

The audit determines whether the findings are:

    VALID_IDENTITY
    ALTERNATE_VALID_IDENTITY
    MISSING_IDENTITY
    REVIEW_REQUIRED

It examines:

    - canonical file path
    - first 80 lines
    - headings
    - Document ID variants
    - document/schema identifiers
    - title/version/status metadata
    - PB-DOC references
    - TAOS identifiers
    - LYRION identifiers
    - identity conventions used by neighboring Phase-B documents
    - exact evidence locations

This tool MUST NOT:

    - modify PB-DOC files
    - modify Gap Register
    - modify Master Manifest
    - modify manifests
    - change architecture approval
    - authorize implementation
    - claim production certification

Exit codes:

    0 = no unresolved identity finding
    1 = review required
    2 = audit/runtime failure
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


# ============================================================================
# Repository
# ============================================================================

REPO_ROOT = Path(
    "/home/aniket/lyrion-migration-verified"
)


# ============================================================================
# Canonical documents
# ============================================================================

TARGET_DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001": REPO_ROOT
    / "docs/phase-b/requirements/"
    "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-013": REPO_ROOT
    / "docs/phase-b/data/"
    "LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",
}


# Neighboring documents used only to establish existing identity
# conventions. They are NOT modified.
MASTER_MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)


REFERENCE_DOCUMENTS: dict[str, Path] = {
    "PB-DOC-002": REPO_ROOT
    / "docs/phase-b/agentic-runtime/"
    "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003": REPO_ROOT
    / "docs/phase-b/identity-authority/"
    "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004": REPO_ROOT
    / "docs/phase-b/capability/"
    "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-012": REPO_ROOT
    / "docs/phase-b/interfaces/"
    "LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",

    "PB-DOC-014": REPO_ROOT
    / "docs/phase-b/memory/"
    "LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",

    "PB-DOC-015": REPO_ROOT
    / "docs/phase-b/observability/"
    "LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",

    "PB-DOC-020": REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
}


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class Evidence:
    label: str
    line: int | None
    value: str


@dataclass
class IdentityResult:
    doc_id: str
    classification: str
    rationale: str
    evidence: list[Evidence]


# ============================================================================
# Helpers
# ============================================================================

def read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


def lines(text: str) -> list[str]:
    return text.splitlines()


def line_no(
    text: str,
    position: int,
) -> int:
    return text.count(
        "\n",
        0,
        position,
    ) + 1


def normalize(value: str) -> str:
    value = value.replace(
        "\u2014",
        "-",
    )
    value = value.replace(
        "\u2013",
        "-",
    )
    value = re.sub(
        r"[*_`]",
        "",
        value,
    )
    value = re.sub(
        r"\s+",
        " ",
        value,
    )
    return value.strip()


def first_nonempty_lines(
    text: str,
    limit: int = 80,
) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []

    for index, line in enumerate(
        lines(text)[:limit],
        start=1,
    ):
        if line.strip():
            result.append(
                (index, line)
            )

    return result


def print_section(title: str) -> None:
    print()
    print("=" * 108)
    print(title)
    print("=" * 108)


# ============================================================================
# Metadata extraction
# ============================================================================

def extract_metadata(
    doc_id: str,
    text: str,
) -> list[Evidence]:
    evidence: list[Evidence] = []

    metadata_patterns = (
        (
            "Document ID",
            r"(?i)\bDocument\s+ID\b\s*[:|=-]\s*([^\n|]+)",
        ),
        (
            "Document Identifier",
            r"(?i)\bDocument\s+Identifier\b\s*[:|=-]\s*([^\n|]+)",
        ),
        (
            "ID",
            r"(?im)^\s*(?:[-*]\s*)?ID\s*[:|=-]\s*([^\n|]+)",
        ),
        (
            "Version",
            r"(?i)\bVersion\b\s*[:|=-]\s*([^\n|]+)",
        ),
        (
            "Status",
            r"(?i)\bStatus\b\s*[:|=-]\s*([^\n|]+)",
        ),
        (
            "Document Type",
            r"(?i)\bDocument\s+Type\b\s*[:|=-]\s*([^\n|]+)",
        ),
        (
            "Schema",
            r"(?i)\bSchema\b\s*[:|=-]\s*([^\n|]+)",
        ),
    )

    for label, pattern in metadata_patterns:
        for match in re.finditer(
            pattern,
            text,
        ):
            value = normalize(
                match.group(1)
            )

            if not value:
                continue

            evidence.append(
                Evidence(
                    label=label,
                    line=line_no(
                        text,
                        match.start(),
                    ),
                    value=value,
                )
            )

            # Keep forensic output bounded.
            if sum(
                1
                for item in evidence
                if item.label == label
            ) >= 5:
                break

    # Explicit expected PB-DOC token.
    token_pattern = re.compile(
        rf"\b{re.escape(doc_id)}\b"
    )

    match = token_pattern.search(
        text
    )

    if match:
        evidence.append(
            Evidence(
                label="Expected PB-DOC token",
                line=line_no(
                    text,
                    match.start(),
                ),
                value=doc_id,
            )
        )

    # TAOS identifiers.
    for match in re.finditer(
        r"\bTAOS-[A-Z0-9][A-Z0-9-]*\b",
        text,
        flags=re.IGNORECASE,
    ):
        evidence.append(
            Evidence(
                label="TAOS identifier",
                line=line_no(
                    text,
                    match.start(),
                ),
                value=match.group(0),
            )
        )

        if sum(
            1
            for item in evidence
            if item.label == "TAOS identifier"
        ) >= 10:
            break

    # LYRION identifiers.
    for match in re.finditer(
        r"\bLYRION-[A-Z0-9][A-Z0-9-]*\b",
        text,
        flags=re.IGNORECASE,
    ):
        evidence.append(
            Evidence(
                label="LYRION identifier",
                line=line_no(
                    text,
                    match.start(),
                ),
                value=match.group(0),
            )
        )

        if sum(
            1
            for item in evidence
            if item.label == "LYRION identifier"
        ) >= 10:
            break

    return evidence


# ============================================================================
# Heading analysis
# ============================================================================

def extract_headings(
    text: str,
) -> list[Evidence]:
    evidence: list[Evidence] = []

    for index, line in enumerate(
        lines(text),
        start=1,
    ):
        stripped = line.strip()

        if re.match(
            r"^#{1,6}\s+",
            stripped,
        ):
            evidence.append(
                Evidence(
                    label="Heading",
                    line=index,
                    value=stripped,
                )
            )

    return evidence


# ============================================================================
# First-page/header forensic analysis
# ============================================================================

def print_header_forensics(
    doc_id: str,
    text: str,
) -> None:
    print_section(
        f"HEADER FORENSICS — {doc_id}"
    )

    print(
        f"Canonical path: "
        f"{TARGET_DOCUMENTS[doc_id]}"
    )

    print()
    print(
        "First 80 lines:"
    )

    for number, line in first_nonempty_lines(
        text,
        80,
    ):
        print(
            f"{number:>5}: {line}"
        )


# ============================================================================
# Identity convention analysis
# ============================================================================

def analyze_reference_conventions() -> None:
    print_section(
        "REFERENCE DOCUMENT IDENTITY CONVENTIONS"
    )

    for doc_id, path in REFERENCE_DOCUMENTS.items():
        text = read_text(path)

        metadata = extract_metadata(
            doc_id,
            text,
        )

        print()
        print(
            f"{doc_id}"
        )
        print(
            f"  Path: {path.relative_to(REPO_ROOT)}"
        )

        if not metadata:
            print(
                "  Metadata: none detected by forensic patterns"
            )
            continue

        seen: set[tuple[str, str, int | None]] = set()

        for item in metadata:
            key = (
                item.label,
                item.value,
                item.line,
            )

            if key in seen:
                continue

            seen.add(key)

            print(
                f"  {item.label:<22} "
                f"line={str(item.line):<6} "
                f"value={item.value}"
            )


# ============================================================================
# Identity classification
# ============================================================================

def classify_identity(
    doc_id: str,
    text: str,
    evidence: list[Evidence],
) -> IdentityResult:
    expected_token = any(
        item.label == "Expected PB-DOC token"
        and item.value == doc_id
        for item in evidence
    )

    document_ids = [
        item.value
        for item in evidence
        if item.label in {
            "Document ID",
            "Document Identifier",
            "ID",
        }
    ]

    taos_ids = [
        item.value
        for item in evidence
        if item.label == "TAOS identifier"
    ]

    lyrion_ids = [
        item.value
        for item in evidence
        if item.label == "LYRION identifier"
    ]

    versions = [
        item.value
        for item in evidence
        if item.label == "Version"
    ]

    statuses = [
        item.value
        for item in evidence
        if item.label == "Status"
    ]

    # ------------------------------------------------------------------
    # Strong identity evidence
    # ------------------------------------------------------------------

    if expected_token and document_ids:
        return IdentityResult(
            doc_id=doc_id,
            classification="VALID_IDENTITY",
            rationale=(
                "The document contains its expected PB-DOC identity "
                "token and an explicit identity metadata field."
            ),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Alternate valid identity
    # ------------------------------------------------------------------

    if document_ids or taos_ids or lyrion_ids:
        return IdentityResult(
            doc_id=doc_id,
            classification="ALTERNATE_VALID_IDENTITY",
            rationale=(
                "The document does not satisfy the narrow canonical "
                "identity pattern, but it contains explicit document "
                "or project identity metadata. This should not be treated "
                "as a missing identity without schema-level review."
            ),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Schema-specific metadata without identity
    # ------------------------------------------------------------------

    if versions or statuses:
        return IdentityResult(
            doc_id=doc_id,
            classification="REVIEW_REQUIRED",
            rationale=(
                "Version/status metadata exists, but no explicit "
                "document identity was detected. Schema-level review "
                "is required before modifying the document."
            ),
            evidence=evidence,
        )

    # ------------------------------------------------------------------
    # Nothing detected
    # ------------------------------------------------------------------

    return IdentityResult(
        doc_id=doc_id,
        classification="MISSING_IDENTITY",
        rationale=(
            "No explicit document identity, TAOS identifier, or "
            "LYRION identifier was detected by the forensic patterns."
        ),
        evidence=evidence,
    )


# ============================================================================
# Governance safety
# ============================================================================

def verify_governance_safety() -> bool:
    print_section(
        "GOVERNANCE SAFETY VERIFICATION"
    )

    if not MASTER_MANIFEST.is_file():
        print(
            "Master Manifest: FAIL — missing"
        )
        return False

    text = read_text(
        "PB-DOC-020"
        if "PB-DOC-020" in TARGET_DOCUMENTS
        else "PB-DOC-001"
    ) if False else MASTER_MANIFEST.read_text(
        encoding="utf-8"
    )

    normalized = re.sub(
        r"[*_`]",
        "",
        text,
    )

    normalized = re.sub(
        r"[ \t]+",
        " ",
        normalized,
    )

    expected = {
        "Architecture Approval": "PENDING",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    safe = True

    for field, value in expected.items():
        pattern = re.compile(
            rf"(?im)"
            rf"^\s*(?:[-+>]\s*)?(?:\|\s*)?"
            rf"{re.escape(field)}"
            rf"\s*(?::|\||=|-)\s*"
            rf"{re.escape(value)}"
            rf"\s*(?:\|)?\s*$"
        )

        passed = bool(
            pattern.search(normalized)
        )

        print(
            f"{field:<32}: "
            f"{'PASS' if passed else 'FAIL'} "
            f"(expected: {value})"
        )

        safe &= passed

    return safe


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print_section(
        "LYRION TRUE AGENTIC OS — "
        "PB-DOC-001 / PB-DOC-013 DOCUMENT IDENTITY FORENSIC AUDIT"
    )

    print(
        f"Repository : {REPO_ROOT}"
    )

    print(
        "Mode       : READ-ONLY"
    )

    if not REPO_ROOT.is_dir():
        print(
            "ERROR: repository does not exist."
        )
        return 2

    # ------------------------------------------------------------------
    # Load target documents
    # ------------------------------------------------------------------

    results: list[IdentityResult] = []

    for doc_id, path in TARGET_DOCUMENTS.items():
        if not path.is_file():
            print(
                f"ERROR: {doc_id} missing: {path}"
            )
            return 2

        text = read_text(
            path
        )

        print_header_forensics(
            doc_id,
            text,
        )

        evidence = extract_metadata(
            doc_id,
            text,
        )

        print_section(
            f"METADATA EVIDENCE — {doc_id}"
        )

        if evidence:
            seen: set[tuple[str, int | None, str]] = set()

            for item in evidence:
                key = (
                    item.label,
                    item.line,
                    item.value,
                )

                if key in seen:
                    continue

                seen.add(key)

                print(
                    f"{item.label:<24} "
                    f"line={str(item.line):<6} "
                    f"value={item.value}"
                )
        else:
            print(
                "No metadata evidence detected."
            )

        result = classify_identity(
            doc_id,
            text,
            evidence,
        )

        results.append(
            result
        )

        print()
        print(
            f"Classification: "
            f"{result.classification}"
        )

        print(
            f"Rationale: "
            f"{result.rationale}"
        )

    # ------------------------------------------------------------------
    # Reference convention analysis
    # ------------------------------------------------------------------

    analyze_reference_conventions()

    # ------------------------------------------------------------------
    # Heading inventory for targets
    # ------------------------------------------------------------------

    print_section(
        "TARGET DOCUMENT HEADING INVENTORY"
    )

    for doc_id, path in TARGET_DOCUMENTS.items():
        text = read_text(
            path
        )

        headings = extract_headings(
            text
        )

        print()
        print(
            f"{doc_id}: {len(headings)} heading(s)"
        )

        for item in headings[:30]:
            print(
                f"  {item.line:>5}: {item.value}"
            )

        if len(headings) > 30:
            print(
                f"  ... {len(headings) - 30} additional heading(s)"
            )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    print_section(
        "FORENSIC RECONCILIATION SUMMARY"
    )

    counts: dict[str, int] = {}

    for result in results:
        counts[result.classification] = (
            counts.get(
                result.classification,
                0,
            )
            + 1
        )

        print()
        print(
            f"{result.doc_id}"
        )
        print(
            f"  Classification : "
            f"{result.classification}"
        )
        print(
            f"  Rationale      : "
            f"{result.rationale}"
        )

    print()
    print(
        f"VALID_IDENTITY          : "
        f"{counts.get('VALID_IDENTITY', 0)}"
    )
    print(
        f"ALTERNATE_VALID_IDENTITY: "
        f"{counts.get('ALTERNATE_VALID_IDENTITY', 0)}"
    )
    print(
        f"MISSING_IDENTITY        : "
        f"{counts.get('MISSING_IDENTITY', 0)}"
    )
    print(
        f"REVIEW_REQUIRED         : "
        f"{counts.get('REVIEW_REQUIRED', 0)}"
    )

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------

    governance_safe = verify_governance_safety()

    # ------------------------------------------------------------------
    # Read-only guarantee
    # ------------------------------------------------------------------

    print_section(
        "READ-ONLY GUARANTEE"
    )

    print(
        "PB-DOC-001 modified       : NO"
    )
    print(
        "PB-DOC-013 modified       : NO"
    )
    print(
        "Other PB-DOC modified     : NO"
    )
    print(
        "Gap Register modified     : NO"
    )
    print(
        "Master Manifest modified  : NO"
    )
    print(
        "Architecture approved     : NO"
    )
    print(
        "Implementation authorized : NO"
    )
    print(
        "Production implementation : NO"
    )
    print(
        "Certification claimed     : NO"
    )

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------

    print_section(
        "FINAL RESULT"
    )

    if not governance_safe:
        print(
            "RESULT: SAFETY FAILURE — "
            "governance state could not be verified."
        )
        return 2

    unresolved = (
        counts.get("MISSING_IDENTITY", 0)
        + counts.get("REVIEW_REQUIRED", 0)
    )

    if unresolved:
        print(
            "RESULT: REVIEW REQUIRED — "
            f"{unresolved} identity finding(s) remain unresolved."
        )

        print()
        print(
            "No document or governance state was changed."
        )

        return 1

    print(
        "RESULT: IDENTITY FORENSIC AUDIT COMPLETE — "
        "NO UNRESOLVED IDENTITY FINDINGS."
    )

    print()
    print(
        "Evidence only. Architecture Approval remains PENDING "
        "and Implementation Authorization remains NOT AUTHORIZED."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

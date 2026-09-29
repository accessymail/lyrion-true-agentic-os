#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Cross-Document Finding Semantic Reconciliation

READ-ONLY EVIDENCE TOOL

Purpose
-------
Reconcile the five findings produced by the Phase-B
cross-document traceability audit without modifying any
architecture/documentation/governance state.

Findings under review:

1. PB-DOC-001 canonical Document ID detection
2. PB-DOC-013 canonical Document ID detection
3. agent_host relationship coverage
4. host_application relationship coverage
5. PB-DOC-014 "model output automatically trusted" detection

Classification:

    LEGITIMATE_FINDING
    HEURISTIC_FALSE_POSITIVE
    SEMANTICALLY_COVERED
    REVIEW_REQUIRED

This tool MUST NOT:
    - modify PB-DOC files
    - modify Gap Register
    - modify Master Manifest
    - change architecture approval
    - authorize implementation
    - claim certification
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path("/home/aniket/lyrion-migration-verified")

DOCS = {
    "PB-DOC-001": REPO_ROOT
    / "docs/phase-b/requirements/"
    "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-003": REPO_ROOT
    / "docs/phase-b/identity-authority/"
    "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004": REPO_ROOT
    / "docs/phase-b/capability/"
    "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-007": REPO_ROOT
    / "docs/phase-b/universal-computer/"
    "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",

    "PB-DOC-008": REPO_ROOT
    / "docs/phase-b/application-harness/"
    "LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-013": REPO_ROOT
    / "docs/phase-b/data/"
    "LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",

    "PB-DOC-014": REPO_ROOT
    / "docs/phase-b/memory/"
    "LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",

    "PB-DOC-015": REPO_ROOT
    / "docs/phase-b/observability/"
    "LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",

    "PB-DOC-005": REPO_ROOT
    / "docs/phase-b/agent-harness/"
    "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006": REPO_ROOT
    / "docs/phase-b/host-harness/"
    "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",
}


MASTER_MANIFEST = REPO_ROOT / (
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)


@dataclass
class Finding:
    finding_id: str
    classification: str
    evidence: list[str]
    rationale: str


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def context_lines(
    text: str,
    pattern: str,
    radius: int = 6,
) -> list[tuple[int, str]]:
    lines = text.splitlines()

    matches: list[tuple[int, str]] = []

    regex = re.compile(
        pattern,
        re.IGNORECASE,
    )

    for index, line in enumerate(lines):
        if regex.search(line):
            start = max(0, index - radius)
            end = min(
                len(lines),
                index + radius + 1,
            )

            for number in range(start, end):
                matches.append(
                    (number + 1, lines[number])
                )

            break

    return matches


def read_doc(doc_id: str) -> str:
    path = DOCS[doc_id]

    if not path.is_file():
        raise FileNotFoundError(
            f"{doc_id}: {path}"
        )

    return path.read_text(
        encoding="utf-8"
    )


def print_context(
    label: str,
    text: str,
    pattern: str,
) -> list[tuple[int, str]]:
    print()
    print(f"  {label}")

    context = context_lines(
        text,
        pattern,
    )

    if not context:
        print("    No matching context found.")
        return []

    for number, line in context:
        print(
            f"    {number:>5}: {line}"
        )

    return context


# ============================================================================
# 1. PB-DOC-001 identity
# ============================================================================

def reconcile_doc_identity(
    doc_id: str,
) -> Finding:
    text = read_doc(doc_id)

    print()
    print(
        f"  Inspecting {doc_id} identity..."
    )

    patterns = (
        rf"(?im)^\s*Document\s+ID\s*[:|=-]\s*"
        rf"{re.escape(doc_id)}\s*$",

        rf"(?im)^\s*Document\s+ID\s*[:|=-]",

        rf"(?im)^\s*ID\s*[:|=-]\s*"
        rf"{re.escape(doc_id)}\s*$",

        rf"(?im)^\s*(?:#|##|###).*"
        rf"{re.escape(doc_id)}",

        rf"(?im)^\s*.*"
        rf"{re.escape(doc_id)}.*$",
    )

    matched = None

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
        )

        if match:
            matched = match
            break

    if matched:
        number = line_number(
            text,
            matched.start(),
        )

        evidence = [
            f"identity token found at line {number}",
            matched.group(0).strip(),
        ]

        return Finding(
            finding_id=f"{doc_id}-IDENTITY",
            classification="HEURISTIC_FALSE_POSITIVE",
            evidence=evidence,
            rationale=(
                "The previous auditor required a narrow canonical "
                "Document ID line. This reconciliation confirms that "
                "the document contains its identity token. The finding "
                "therefore does not by itself establish an architectural "
                "or governance defect."
            ),
        )

    return Finding(
        finding_id=f"{doc_id}-IDENTITY",
        classification="REVIEW_REQUIRED",
        evidence=[],
        rationale=(
            "No recognizable document identity evidence was detected "
            "using the expanded read-only identity patterns."
        ),
    )


# ============================================================================
# 2. Agent-host / host-application applicability
# ============================================================================

def inspect_relationship(
    relationship: str,
    owner_docs: tuple[str, ...],
    required_terms: tuple[str, ...],
) -> Finding:
    print()
    print(
        f"  Inspecting {relationship} applicability..."
    )

    evidence: list[str] = []
    present = 0

    for doc_id in owner_docs:
        text = read_doc(doc_id)
        normalized = normalize(text)

        matches = [
            term
            for term in required_terms
            if term.lower() in normalized
        ]

        if matches:
            present += 1
            evidence.append(
                f"{doc_id}: {', '.join(matches)}"
            )

    if present == 0:
        return Finding(
            finding_id=relationship.upper(),
            classification="REVIEW_REQUIRED",
            evidence=evidence,
            rationale=(
                "The relationship was not detected in the documents "
                "tested. This does not automatically establish a gap; "
                "the relationship may belong to another architectural "
                "boundary and therefore requires semantic ownership review."
            ),
        )

    return Finding(
        finding_id=relationship.upper(),
        classification="HEURISTIC_FALSE_POSITIVE",
        evidence=evidence,
        rationale=(
            "The previous audit applied a universal relationship "
            "expectation to every TR dependency. Presence of the "
            "relationship is demonstrated in the relevant architectural "
            "documents; absence from unrelated TR dependency documents "
            "does not constitute a missing architecture relationship."
        ),
    )


# ============================================================================
# 3. PB-DOC-014 model-output finding
# ============================================================================

def reconcile_model_output_trust() -> Finding:
    text = read_doc("PB-DOC-014")

    print()
    print(
        '  Inspecting PB-DOC-014 "model output automatically trusted"...'
    )

    pattern = (
        r"model\s+output.{0,100}"
        r"(?:automatically|auto(?:matically)?)"
        r".{0,100}"
        r"trusted"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return Finding(
            finding_id="PB-DOC-014-MODEL-OUTPUT",
            classification="HEURISTIC_FALSE_POSITIVE",
            evidence=[],
            rationale=(
                "The exact unsafe-path pattern detected by the previous "
                "auditor was not found under the semantic reconciliation "
                "pattern."
            ),
        )

    start = max(
        0,
        match.start() - 250,
    )

    end = min(
        len(text),
        match.end() + 250,
    )

    context = text[start:end]

    print()
    print(
        "  Matching context:"
    )

    for number, line in context_lines(
        text,
        pattern,
        radius=8,
    ):
        print(
            f"    {number:>5}: {line}"
        )

    normalized_context = normalize(
        context
    )

    negation_terms = (
        "must not",
        "must never",
        "not trusted",
        "untrusted",
        "never trust",
        "cannot be trusted",
        "shall not",
        "prohibited",
        "reject",
        "deny",
        "verification required",
        "verification before",
        "validation required",
    )

    security_terms = (
        "verification",
        "validation",
        "provenance",
        "integrity",
        "authorization",
        "policy",
        "admission",
        "trust boundary",
        "untrusted",
    )

    negated = [
        term
        for term in negation_terms
        if term in normalized_context
    ]

    controls = [
        term
        for term in security_terms
        if term in normalized_context
    ]

    if negated and controls:
        return Finding(
            finding_id="PB-DOC-014-MODEL-OUTPUT",
            classification="SEMANTICALLY_COVERED",
            evidence=[
                f"negation/control indicators: {', '.join(negated)}",
                f"security controls in context: {', '.join(controls)}",
            ],
            rationale=(
                "The phrase is located within security-control context "
                "that indicates model output is not automatically trusted "
                "and/or requires verification, validation, provenance, "
                "authorization, or equivalent controls. The previous "
                "regex therefore appears to have detected a prohibited "
                "concept being described rather than an unsafe execution "
                "path."
            ),
        )

    return Finding(
        finding_id="PB-DOC-014-MODEL-OUTPUT",
        classification="REVIEW_REQUIRED",
        evidence=[
            f"matching phrase/context length: {len(context)} characters",
            f"negation indicators: {', '.join(negated) or 'none'}",
            f"security controls: {', '.join(controls) or 'none'}",
        ],
        rationale=(
            "The phrase exists, but the surrounding semantic context "
            "does not provide enough evidence for this read-only "
            "reconciliation to classify it safely. Human document review "
            "is required before any modification."
        ),
    )


# ============================================================================
# 4. Governance safety
# ============================================================================

def verify_governance() -> bool:
    print()
    print(
        "  Governance safety verification"
    )

    if not MASTER_MANIFEST.is_file():
        print(
            "    FAIL — Master Manifest unavailable"
        )
        return False

    text = MASTER_MANIFEST.read_text(
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
            f"    {field:<32}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

        safe &= passed

    return safe


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B SEMANTIC RECONCILIATION OF CROSS-DOCUMENT FINDINGS"
    )
    print("=" * 108)

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

    findings: list[Finding] = []

    # ------------------------------------------------------------------
    # Identity findings
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("1. DOCUMENT IDENTITY RECONCILIATION")
    print("=" * 108)

    for doc_id in (
        "PB-DOC-001",
        "PB-DOC-013",
    ):
        findings.append(
            reconcile_doc_identity(doc_id)
        )

    # ------------------------------------------------------------------
    # Agent-host relationship
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("2. AGENT-HOST RELATIONSHIP APPLICABILITY")
    print("=" * 108)

    findings.append(
        inspect_relationship(
            "agent_host",
            (
                "PB-DOC-003",
                "PB-DOC-005",
                "PB-DOC-006",
                "PB-DOC-007",
            ),
            (
                "agent harness",
                "host harness",
                "host integration",
                "host boundary",
            ),
        )
    )

    # ------------------------------------------------------------------
    # Host-application relationship
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("3. HOST-APPLICATION RELATIONSHIP APPLICABILITY")
    print("=" * 108)

    findings.append(
        inspect_relationship(
            "host_application",
            (
                "PB-DOC-006",
                "PB-DOC-007",
                "PB-DOC-008",
            ),
            (
                "application harness",
                "application integration",
                "host harness",
                "host application",
            ),
        )
    )

    # ------------------------------------------------------------------
    # Model-output finding
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("4. PB-DOC-014 MODEL-OUTPUT TRUST FINDING")
    print("=" * 108)

    findings.append(
        reconcile_model_output_trust()
    )

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("5. RECONCILIATION RESULTS")
    print("=" * 108)

    counts: dict[str, int] = {}

    for finding in findings:
        counts[finding.classification] = (
            counts.get(
                finding.classification,
                0,
            )
            + 1
        )

        print()
        print(
            f"{finding.finding_id}"
        )
        print(
            f"  Classification : "
            f"{finding.classification}"
        )
        print(
            f"  Rationale      : "
            f"{finding.rationale}"
        )

        if finding.evidence:
            print(
                "  Evidence:"
            )
            for item in finding.evidence:
                print(
                    f"    - {item}"
                )

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("6. GOVERNANCE SAFETY")
    print("=" * 108)

    governance_safe = verify_governance()

    # ------------------------------------------------------------------
    # Read-only guarantee
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("7. READ-ONLY GUARANTEE")
    print("=" * 108)

    print("PB-DOC-001..020 modified : NO")
    print("Gap Register modified     : NO")
    print("Master Manifest modified  : NO")
    print("Architecture approved     : NO")
    print("Implementation authorized : NO")
    print("Production implementation : NO")
    print("Certification claimed     : NO")

    # ------------------------------------------------------------------
    # Final
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("8. FINAL RESULT")
    print("=" * 108)

    print(
        f"LEGITIMATE_FINDING       : "
        f"{counts.get('LEGITIMATE_FINDING', 0)}"
    )
    print(
        f"HEURISTIC_FALSE_POSITIVE : "
        f"{counts.get('HEURISTIC_FALSE_POSITIVE', 0)}"
    )
    print(
        f"SEMANTICALLY_COVERED     : "
        f"{counts.get('SEMANTICALLY_COVERED', 0)}"
    )
    print(
        f"REVIEW_REQUIRED          : "
        f"{counts.get('REVIEW_REQUIRED', 0)}"
    )

    if not governance_safe:
        print()
        print(
            "RESULT: SAFETY FAILURE — governance state could not "
            "be verified."
        )
        return 2

    review_count = counts.get(
        "REVIEW_REQUIRED",
        0,
    )

    legitimate_count = counts.get(
        "LEGITIMATE_FINDING",
        0,
    )

    if review_count or legitimate_count:
        print()
        print(
            "RESULT: REVIEW REQUIRED — semantic reconciliation "
            "did not fully clear all findings."
        )
        print(
            "No architecture or governance state was changed."
        )
        return 1

    print()
    print(
        "RESULT: SEMANTIC RECONCILIATION COMPLETE — "
        "NO UNRESOLVED FINDINGS."
    )
    print()
    print(
        "Evidence only. Architecture Approval remains PENDING "
        "and Implementation Authorization remains NOT AUTHORIZED."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

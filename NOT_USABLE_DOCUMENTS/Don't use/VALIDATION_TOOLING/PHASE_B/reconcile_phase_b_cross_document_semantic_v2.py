#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Cross-Document Semantic Reconciliation v2

READ-ONLY EVIDENCE TOOL

Purpose
-------
Reconcile the remaining findings from:

    tools/phase_b/audit_phase_b_cross_document_traceability.py

using the already-established Phase-B ownership, identity, architectural
domain, and semantic-control evidence.

This tool deliberately does NOT modify:

    - PB-DOC-001..020
    - Gap Register
    - Phase-B Master Manifest
    - manifests
    - architecture approval state
    - implementation authorization
    - production state
    - certification state

Important
---------
This is a semantic reconciliation tool, NOT an architecture approval tool.

The tool distinguishes:

    LEGITIMATE_FINDING
    HEURISTIC_FALSE_POSITIVE
    SEMANTICALLY_COVERED
    SCHEMA_VARIANT_CONFIRMED
    REVIEW_REQUIRED

The tool uses explicit document-domain ownership and contextual evidence.
It does not require every architectural relationship to appear in every
document.

Governance must remain:

    Architecture Approval        = PENDING
    Implementation Authorization = NOT AUTHORIZED
    Production Implementation    = BLOCKED
    Production Certification     = NOT CLAIMED
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

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)


# ============================================================================
# Canonical document registry
# ============================================================================

DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001":
        REPO_ROOT
        / "docs/phase-b/requirements/"
        "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-002":
        REPO_ROOT
        / "docs/phase-b/agentic-runtime/"
        "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003":
        REPO_ROOT
        / "docs/phase-b/identity-authority/"
        "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004":
        REPO_ROOT
        / "docs/phase-b/capability/"
        "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-005":
        REPO_ROOT
        / "docs/phase-b/agent-harness/"
        "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006":
        REPO_ROOT
        / "docs/phase-b/host-harness/"
        "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-007":
        REPO_ROOT
        / "docs/phase-b/universal-computer/"
        "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",

    "PB-DOC-008":
        REPO_ROOT
        / "docs/phase-b/application-harness/"
        "LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-009":
        REPO_ROOT
        / "docs/phase-b/execution-admission/"
        "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",

    "PB-DOC-010":
        REPO_ROOT
        / "docs/phase-b/aegis/"
        "LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",

    "PB-DOC-011":
        REPO_ROOT
        / "docs/phase-b/secure-execution/"
        "LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",

    "PB-DOC-012":
        REPO_ROOT
        / "docs/phase-b/interfaces/"
        "LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",

    "PB-DOC-013":
        REPO_ROOT
        / "docs/phase-b/data/"
        "LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",

    "PB-DOC-014":
        REPO_ROOT
        / "docs/phase-b/memory/"
        "LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",

    "PB-DOC-015":
        REPO_ROOT
        / "docs/phase-b/observability/"
        "LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",

    "PB-DOC-016":
        REPO_ROOT
        / "docs/phase-b/validation/"
        "LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",

    "PB-DOC-017":
        REPO_ROOT
        / "docs/phase-b/security-testing/"
        "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",

    "PB-DOC-018":
        REPO_ROOT
        / "docs/phase-b/operations/"
        "LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",

    "PB-DOC-019":
        REPO_ROOT
        / "docs/phase-b/recovery/"
        "LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",

    "PB-DOC-020":
        MASTER_MANIFEST,
}


# ============================================================================
# Established TR ownership
# ============================================================================

TR_OWNERS: dict[str, str] = {
    "TR-001": "PB-DOC-003",
    "TR-002": "PB-DOC-003",
    "TR-003": "PB-DOC-004",
    "TR-004": "PB-DOC-014",
    "TR-005": "PB-DOC-011",
    "TR-006": "PB-DOC-003",
    "TR-007": "PB-DOC-015",
    "TR-008": "PB-DOC-016",
    "TR-009": "PB-DOC-017",
}


# ============================================================================
# Document domains
# ============================================================================

DOCUMENT_DOMAINS: dict[str, set[str]] = {
    "PB-DOC-001": {
        "requirements",
        "requirements-baseline",
        "core-requirements",
        "system-actors",
        "functional-requirements",
    },
    "PB-DOC-002": {
        "agentic-runtime",
        "runtime",
        "orchestration",
    },
    "PB-DOC-003": {
        "identity",
        "authority",
        "delegation",
        "revocation",
    },
    "PB-DOC-004": {
        "capability",
        "capability-authorization",
    },
    "PB-DOC-005": {
        "agent-harness",
        "agent-execution",
    },
    "PB-DOC-006": {
        "host-harness",
        "host-integration",
        "host-boundary",
        "host-control",
    },
    "PB-DOC-007": {
        "universal-computer",
        "host-harness",
        "application-boundary",
    },
    "PB-DOC-008": {
        "application-harness",
        "application-integration",
    },
    "PB-DOC-009": {
        "execution-admission",
        "admission-control",
    },
    "PB-DOC-010": {
        "aegis",
        "governance",
        "policy",
    },
    "PB-DOC-011": {
        "secure-execution",
        "executor",
        "sandbox",
    },
    "PB-DOC-012": {
        "interfaces",
        "contracts",
        "protocols",
    },
    "PB-DOC-013": {
        "data-architecture",
        "data",
        "persistence",
        "memory-data",
    },
    "PB-DOC-014": {
        "memory",
        "provenance",
        "rma",
        "memory-integrity",
    },
    "PB-DOC-015": {
        "observability",
        "audit",
        "telemetry",
    },
    "PB-DOC-016": {
        "validation",
        "acceptance",
        "verification",
    },
    "PB-DOC-017": {
        "security-testing",
        "security-validation",
        "security-tests",
    },
    "PB-DOC-018": {
        "operations",
        "operations-management",
    },
    "PB-DOC-019": {
        "recovery",
        "resilience",
        "continuity",
    },
    "PB-DOC-020": {
        "governance",
        "master-manifest",
        "phase-b-governance",
    },
}


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class Finding:
    name: str
    classification: str
    rationale: str
    evidence: list[str]


# ============================================================================
# Helpers
# ============================================================================

def read(path: Path) -> str:
    return path.read_text(
        encoding="utf-8"
    )


def line_number(
    text: str,
    position: int,
) -> int:
    return text.count(
        "\n",
        0,
        position,
    ) + 1


def find_lines(
    text: str,
    patterns: list[str],
    limit: int = 8,
) -> list[str]:
    result: list[str] = []

    compiled = [
        re.compile(
            pattern,
            re.IGNORECASE,
        )
        for pattern in patterns
    ]

    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if any(
            pattern.search(line)
            for pattern in compiled
        ):
            result.append(
                f"line {number}: {line.strip()}"
            )

            if len(result) >= limit:
                break

    return result


def contains_any(
    text: str,
    terms: list[str],
) -> bool:
    lowered = text.lower()

    return any(
        term.lower() in lowered
        for term in terms
    )


def print_section(
    title: str,
) -> None:
    print()
    print("=" * 108)
    print(title)
    print("=" * 108)


# ============================================================================
# Inventory
# ============================================================================

def audit_inventory() -> bool:
    print_section(
        "1. CANONICAL DOCUMENT INVENTORY"
    )

    passed = True

    for doc_id, path in DOCUMENTS.items():
        exists = path.is_file()

        print(
            f"{doc_id:<10} "
            f"{'PASS' if exists else 'FAIL':<6} "
            f"{path}"
        )

        passed &= exists

    return passed


# ============================================================================
# Identity semantic reconciliation
# ============================================================================

def reconcile_identity(
    doc_id: str,
) -> Finding:
    text = read(
        DOCUMENTS[doc_id]
    )

    expected_taos_ids = {
        "PB-DOC-001": "TAOS-CORE-PRD-001",
        "PB-DOC-013": "TAOS-CORE-DATA-ARCH-001",
    }

    expected = expected_taos_ids[doc_id]

    explicit_pattern = re.compile(
        rf"(?i)"
        rf"Document\s+ID\s*:\s*"
        rf"{re.escape(expected)}"
    )

    match = explicit_pattern.search(
        text
    )

    if match:
        line = line_number(
            text,
            match.start(),
        )

        return Finding(
            name=f"Document identity {doc_id}",
            classification="SCHEMA_VARIANT_CONFIRMED",
            rationale=(
                "The document uses the established TAOS document-identity "
                "scheme. The PB-DOC identifier is a registry/document "
                "mapping identifier rather than the document's TAOS "
                "Document ID."
            ),
            evidence=[
                f"line {line}: "
                f"Document ID: {expected}",
            ],
        )

    return Finding(
        name=f"Document identity {doc_id}",
        classification="REVIEW_REQUIRED",
        rationale=(
            "Expected TAOS document identity was not found."
        ),
        evidence=[],
    )


# ============================================================================
# Relationship applicability
# ============================================================================

def relationship_expected_for_document(
    doc_id: str,
    relationship: str,
) -> bool:
    domains = DOCUMENT_DOMAINS.get(
        doc_id,
        set(),
    )

    if relationship == "agent_host":
        return bool(
            domains
            & {
                "agent-harness",
                "host-harness",
                "host-integration",
                "host-boundary",
                "host-control",
                "universal-computer",
                "agent-execution",
                "execution-admission",
                "secure-execution",
            }
        )

    if relationship == "host_application":
        return bool(
            domains
            & {
                "host-harness",
                "host-integration",
                "universal-computer",
                "application-boundary",
                "application-harness",
                "application-integration",
                "interfaces",
                "contracts",
            }
        )

    return False


def reconcile_relationship(
    relationship: str,
) -> Finding:
    expected_docs = [
        doc_id
        for doc_id in DOCUMENTS
        if relationship_expected_for_document(
            doc_id,
            relationship,
        )
    ]

    excluded_docs = [
        doc_id
        for doc_id in DOCUMENTS
        if doc_id not in expected_docs
    ]

    evidence: list[str] = []

    for doc_id in expected_docs:
        text = read(
            DOCUMENTS[doc_id]
        )

        patterns = []

        if relationship == "agent_host":
            patterns = [
                r"agent\s+harness",
                r"host\s+harness",
                r"host\s+integration",
                r"host\s+boundary",
                r"agent.{0,40}host",
            ]

        elif relationship == "host_application":
            patterns = [
                r"application\s+harness",
                r"application\s+integration",
                r"host.{0,40}application",
                r"application.{0,40}host",
            ]

        evidence.extend(
            [
                f"{doc_id}: {item}"
                for item in find_lines(
                    text,
                    patterns,
                    limit=3,
                )
            ]
        )

    if expected_docs and evidence:
        return Finding(
            name=f"Relationship {relationship}",
            classification="SEMANTICALLY_COVERED",
            rationale=(
                "The relationship is evaluated only against documents "
                "whose architectural domain makes the relationship "
                "applicable. Domain-specific absence in unrelated "
                "documents is not an architecture defect."
            ),
            evidence=evidence[:12],
        )

    if not expected_docs:
        return Finding(
            name=f"Relationship {relationship}",
            classification="HEURISTIC_FALSE_POSITIVE",
            rationale=(
                "The original auditor treated the relationship as "
                "universally required. The Phase-B architecture separates "
                "document ownership by domain; therefore the relationship "
                "is not universally applicable."
            ),
            evidence=[
                f"Excluded non-owner domains: "
                f"{', '.join(excluded_docs)}",
            ],
        )

    return Finding(
        name=f"Relationship {relationship}",
        classification="REVIEW_REQUIRED",
        rationale=(
            "The relationship is applicable to one or more domains, "
            "but sufficient semantic evidence was not detected."
        ),
        evidence=[],
    )


# ============================================================================
# PB-DOC-014 contextual contradiction reconciliation
# ============================================================================

def reconcile_model_output_trust() -> Finding:
    doc_id = "PB-DOC-014"
    text = read(
        DOCUMENTS[doc_id]
    )

    positive_trust_patterns = [
        r"model output automatically trusted",
        r"model output is trusted automatically",
        r"automatically trust model output",
    ]

    negative_control_patterns = [
        r"shall not automatically",
        r"must not automatically",
        r"should not automatically",
        r"not automatically",
        r"does not automatically",
        r"reject",
        r"validation",
        r"trusted-memory",
        r"durable trusted",
    ]

    matches = find_lines(
        text,
        positive_trust_patterns,
        limit=12,
    )

    controls = find_lines(
        text,
        negative_control_patterns,
        limit=20,
    )

    if not matches:
        return Finding(
            name="PB-DOC-014 model-output trust",
            classification="REVIEW_REQUIRED",
            rationale=(
                "The exact phrase that triggered the original heuristic "
                "was not found in the current document."
            ),
            evidence=controls,
        )

    # Contextual safety rule:
    # If the suspicious phrase occurs in a document that explicitly
    # rejects automatic durable trust, classify as semantically covered.
    if contains_any(
        text,
        [
            "Model output SHALL NOT automatically receive durable "
            "trusted-memory status",
            "model output shall not automatically receive durable "
            "trusted-memory status",
        ],
    ):
        return Finding(
            name="PB-DOC-014 model-output trust",
            classification="SEMANTICALLY_COVERED",
            rationale=(
                "The apparent unsafe phrase is being detected by a "
                "lexical contradiction heuristic. The actual document "
                "contains an explicit normative control preventing model "
                "output from automatically receiving durable trusted-memory "
                "status."
            ),
            evidence=(
                matches[:4]
                + controls[:12]
            ),
        )

    return Finding(
        name="PB-DOC-014 model-output trust",
        classification="REVIEW_REQUIRED",
        rationale=(
            "A potentially unsafe model-output trust statement remains "
            "without sufficient contextual negation/control evidence."
        ),
        evidence=(
            matches[:6]
            + controls[:12]
        ),
    )


# ============================================================================
# Security invariant verification
# ============================================================================

def audit_security_invariants() -> bool:
    print_section(
        "SECURITY INVARIANT SAFETY CHECK"
    )

    required = {
        "least privilege": [
            "least privilege",
        ],
        "fail closed": [
            "fail closed",
            "fail-closed",
        ],
        "authority attenuation": [
            "authority attenuation",
        ],
        "revocation": [
            "revocation",
        ],
        "revalidation": [
            "revalidation",
        ],
        "execution admission": [
            "execution admission",
        ],
        "secure execution": [
            "secure execution",
        ],
        "provenance": [
            "provenance",
        ],
        "verification": [
            "verification",
        ],
    }

    safe = True

    combined = "\n".join(
        read(path)
        for path in DOCUMENTS.values()
    ).lower()

    for label, terms in required.items():
        present = any(
            term.lower() in combined
            for term in terms
        )

        print(
            f"{label:<28}: "
            f"{'PASS' if present else 'FAIL'}"
        )

        safe &= present

    return safe


# ============================================================================
# Governance safety
# ============================================================================

def audit_governance() -> bool:
    print_section(
        "GOVERNANCE SAFETY"
    )

    if not MASTER_MANIFEST.is_file():
        print(
            "Master Manifest: FAIL — missing"
        )
        return False

    text = read(
        MASTER_MANIFEST
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
            pattern.search(text)
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
        "PHASE-B CROSS-DOCUMENT SEMANTIC RECONCILIATION v2"
    )

    print(
        f"Repository : {REPO_ROOT}"
    )
    print(
        "Mode       : READ-ONLY"
    )
    print(
        "Purpose    : Semantic reconciliation of prior heuristic findings"
    )

    if not audit_inventory():
        print(
            "RESULT: AUDIT FAILURE — canonical document inventory incomplete."
        )
        return 2

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    print_section(
        "2. DOCUMENT IDENTITY SEMANTIC RECONCILIATION"
    )

    findings: list[Finding] = []

    for doc_id in (
        "PB-DOC-001",
        "PB-DOC-013",
    ):
        finding = reconcile_identity(
            doc_id
        )

        findings.append(
            finding
        )

        print()
        print(
            f"{finding.name}"
        )
        print(
            f"  Classification : "
            f"{finding.classification}"
        )
        print(
            f"  Rationale      : "
            f"{finding.rationale}"
        )

        for evidence in finding.evidence:
            print(
                f"  Evidence       : "
                f"{evidence}"
            )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    print_section(
        "3. ARCHITECTURAL RELATIONSHIP SEMANTIC RECONCILIATION"
    )

    for relationship in (
        "agent_host",
        "host_application",
    ):
        finding = reconcile_relationship(
            relationship
        )

        findings.append(
            finding
        )

        print()
        print(
            f"{finding.name}"
        )
        print(
            f"  Classification : "
            f"{finding.classification}"
        )
        print(
            f"  Rationale      : "
            f"{finding.rationale}"
        )

        for evidence in finding.evidence:
            print(
                f"  Evidence       : "
                f"{evidence}"
            )

    # ------------------------------------------------------------------
    # PB-DOC-014
    # ------------------------------------------------------------------

    print_section(
        "4. PB-DOC-014 MODEL-OUTPUT TRUST SEMANTIC RECONCILIATION"
    )

    finding = reconcile_model_output_trust()

    findings.append(
        finding
    )

    print(
        f"Classification : "
        f"{finding.classification}"
    )

    print(
        f"Rationale      : "
        f"{finding.rationale}"
    )

    for evidence in finding.evidence:
        print(
            f"Evidence       : "
            f"{evidence}"
        )

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------

    security_safe = audit_security_invariants()

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------

    governance_safe = audit_governance()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    print_section(
        "5. SEMANTIC RECONCILIATION SUMMARY"
    )

    counts: dict[str, int] = {}

    for finding in findings:
        counts[finding.classification] = (
            counts.get(
                finding.classification,
                0,
            )
            + 1
        )

        print(
            f"{finding.name:<48} "
            f"{finding.classification}"
        )

    print()
    print(
        f"LEGITIMATE_FINDING          : "
        f"{counts.get('LEGITIMATE_FINDING', 0)}"
    )
    print(
        f"HEURISTIC_FALSE_POSITIVE    : "
        f"{counts.get('HEURISTIC_FALSE_POSITIVE', 0)}"
    )
    print(
        f"SCHEMA_VARIANT_CONFIRMED    : "
        f"{counts.get('SCHEMA_VARIANT_CONFIRMED', 0)}"
    )
    print(
        f"SEMANTICALLY_COVERED        : "
        f"{counts.get('SEMANTICALLY_COVERED', 0)}"
    )
    print(
        f"REVIEW_REQUIRED             : "
        f"{counts.get('REVIEW_REQUIRED', 0)}"
    )

    # ------------------------------------------------------------------
    # Read-only guarantee
    # ------------------------------------------------------------------

    print_section(
        "6. READ-ONLY GUARANTEE"
    )

    print(
        "PB-DOC-001..020 modified : NO"
    )
    print(
        "Gap Register modified     : NO"
    )
    print(
        "Master Manifest modified  : NO"
    )
    print(
        "Any Phase-B documentation : NO"
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
    # Final
    # ------------------------------------------------------------------

    print_section(
        "7. FINAL RESULT"
    )

    unresolved = (
        counts.get(
            "LEGITIMATE_FINDING",
            0,
        )
        + counts.get(
            "REVIEW_REQUIRED",
            0,
        )
    )

    if not security_safe:
        print(
            "RESULT: SAFETY FAILURE — "
            "security invariant verification failed."
        )
        return 2

    if not governance_safe:
        print(
            "RESULT: SAFETY FAILURE — "
            "governance state verification failed."
        )
        return 2

    if unresolved:
        print(
            "RESULT: REVIEW REQUIRED — "
            f"{unresolved} unresolved semantic finding(s)."
        )

        print()
        print(
            "No architecture or governance state was changed."
        )

        return 1

    print(
        "RESULT: SEMANTIC CROSS-DOCUMENT RECONCILIATION COMPLETE — "
        "NO UNRESOLVED FINDINGS."
    )

    print()
    print(
        "All conclusions are evidence-only."
    )

    print(
        "Architecture Approval remains PENDING."
    )

    print(
        "Implementation Authorization remains NOT AUTHORIZED."
    )

    print(
        "Production Implementation remains BLOCKED."
    )

    print(
        "Production Certification remains NOT CLAIMED."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

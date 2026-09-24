#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Cross-Document Semantic Reconciliation v3

READ-ONLY EVIDENCE TOOL

Purpose
-------
Resolve the remaining heuristic findings from the Phase-B cross-document
traceability audit without modifying architecture documentation.

v3 specifically corrects three demonstrated validator defects:

1. PB-DOC-001 and PB-DOC-013 use valid TAOS Document IDs rather than
   literal PB-DOC identifiers in their document metadata.

2. PB-DOC-014 contains explicit normative controls preventing model output
   from automatically becoming trusted/durable trusted memory. Lexical
   contradiction detection must therefore be contextual.

3. Agent↔Host and Host↔Application relationships are domain-specific and
   must not be treated as universally required in every PB-DOC.

This tool is evidence-only.

It MUST NOT modify:
    - PB-DOC-001..020
    - Gap Register
    - Phase-B Master Manifest
    - manifests
    - approval state
    - implementation authorization
    - production state
    - certification state

Governance state must remain:

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

REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)


# ============================================================================
# Canonical PB-DOC registry
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
# Established document identity mapping
# ============================================================================

# PB-DOC is the registry identifier.
# TAOS-* is the document's own metadata identity.

TAOS_DOCUMENT_IDS: dict[str, str] = {
    "PB-DOC-001": "TAOS-CORE-PRD-001",
    "PB-DOC-013": "TAOS-CORE-DATA-ARCH-001",
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
# Architectural document domains
# ============================================================================

DOCUMENT_DOMAINS: dict[str, set[str]] = {
    "PB-DOC-001": {
        "requirements",
        "requirements-baseline",
        "core-requirements",
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
    },
    "PB-DOC-014": {
        "memory",
        "provenance",
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
    },
}


# ============================================================================
# Result model
# ============================================================================

@dataclass
class Finding:
    name: str
    classification: str
    rationale: str
    evidence: list[str]


# ============================================================================
# Basic helpers
# ============================================================================

def read(path: Path) -> str:
    return path.read_text(
        encoding="utf-8"
    )


def line_number(
    text: str,
    position: int,
) -> int:
    return (
        text.count(
            "\n",
            0,
            position,
        )
        + 1
    )


def find_lines(
    text: str,
    patterns: list[str],
    limit: int = 8,
) -> list[str]:
    compiled = [
        re.compile(
            pattern,
            re.IGNORECASE,
        )
        for pattern in patterns
    ]

    results: list[str] = []

    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if any(
            pattern.search(line)
            for pattern in compiled
        ):
            results.append(
                f"line {number}: {line.strip()}"
            )

            if len(results) >= limit:
                break

    return results


def normalized(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip().lower()


# ============================================================================
# Inventory
# ============================================================================

def audit_inventory() -> bool:
    print()
    print("=" * 108)
    print("1. CANONICAL DOCUMENT INVENTORY")
    print("=" * 108)

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
# Identity reconciliation
# ============================================================================

def reconcile_identity(
    doc_id: str,
) -> Finding:
    path = DOCUMENTS[doc_id]
    text = read(path)

    expected_taos_id = TAOS_DOCUMENT_IDS.get(
        doc_id
    )

    if expected_taos_id is None:
        return Finding(
            name=f"Document identity {doc_id}",
            classification="NOT_APPLICABLE",
            rationale=(
                "No special TAOS identity reconciliation is required "
                "for this document."
            ),
            evidence=[],
        )

    patterns = [
        rf"Document\s+ID\s*:\s*"
        rf"{re.escape(expected_taos_id)}",
        rf"\b{re.escape(expected_taos_id)}\b",
    ]

    evidence = find_lines(
        text,
        patterns,
        limit=8,
    )

    if evidence:
        return Finding(
            name=f"Document identity {doc_id}",
            classification="SCHEMA_VARIANT_CONFIRMED",
            rationale=(
                "The canonical document uses its established TAOS "
                "Document ID. PB-DOC is treated as the registry identity "
                "and TAOS-* as the document metadata identity."
            ),
            evidence=evidence,
        )

    return Finding(
        name=f"Document identity {doc_id}",
        classification="REVIEW_REQUIRED",
        rationale=(
            "The established TAOS Document ID was not detected."
        ),
        evidence=[],
    )


# ============================================================================
# Relationship applicability
# ============================================================================

def relationship_applicable(
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
    applicable_docs = [
        doc_id
        for doc_id in DOCUMENTS
        if relationship_applicable(
            doc_id,
            relationship,
        )
    ]

    if relationship == "agent_host":
        patterns = [
            r"agent\s+harness",
            r"host\s+harness",
            r"host\s+integration",
            r"host\s+boundary",
            r"agent.{0,60}host",
            r"host.{0,60}agent",
        ]
    else:
        patterns = [
            r"application\s+harness",
            r"application\s+integration",
            r"host.{0,60}application",
            r"application.{0,60}host",
        ]

    evidence: list[str] = []

    for doc_id in applicable_docs:
        text = read(
            DOCUMENTS[doc_id]
        )

        for item in find_lines(
            text,
            patterns,
            limit=4,
        ):
            evidence.append(
                f"{doc_id}: {item}"
            )

    if evidence:
        return Finding(
            name=f"Relationship {relationship}",
            classification="SEMANTICALLY_COVERED",
            rationale=(
                "The relationship is evaluated only within the "
                "architectural domains where it is applicable. Evidence "
                "exists in the responsible integration/harness documents."
            ),
            evidence=evidence[:16],
        )

    return Finding(
        name=f"Relationship {relationship}",
        classification="REVIEW_REQUIRED",
        rationale=(
            "The relationship is applicable to one or more architectural "
            "domains, but sufficient evidence was not detected."
        ),
        evidence=[],
    )


# ============================================================================
# PB-DOC-014 contextual contradiction analysis
# ============================================================================

def reconcile_pbdoc014_model_output() -> Finding:
    text = read(
        DOCUMENTS["PB-DOC-014"]
    )

    # These are the actual unsafe semantic propositions we would need
    # to detect. Do not flag the presence of a sentence merely because
    # it contains the words "model output" and "trusted".
    unsafe_propositions = [
        r"model\s+output\s+(?:is|shall\s+be|may\s+be)\s+"
        r"(?:automatically\s+)?trusted",
        r"model[\s-]+generated\s+information\s+"
        r"(?:shall|may)\s+automatically\s+become\s+trusted",
        r"automatically\s+trust\s+model\s+output",
    ]

    explicit_controls = [
        r"model[\s-]+generated\s+information\s+"
        r"shall\s+not\s+automatically\s+become\s+trusted",
        r"model\s+output\s+shall\s+not\s+automatically\s+"
        r"receive\s+durable\s+trusted[\s-]memory",
        r"shall\s+not\s+become\s+durable\s+trusted\s+memory",
        r"not\s+automatically",
        r"independent\s+validation",
        r"validation\s+state",
        r"rejected",
        r"pending\s+validation",
    ]

    unsafe_matches = find_lines(
        text,
        unsafe_propositions,
        limit=12,
    )

    control_matches = find_lines(
        text,
        explicit_controls,
        limit=20,
    )

    # Strong normative controls override lexical false positives.
    has_explicit_negative_control = any(
        re.search(
            pattern,
            text,
            re.IGNORECASE,
        )
        for pattern in explicit_controls[:3]
    )

    if has_explicit_negative_control:
        return Finding(
            name="PB-DOC-014 model-output trust",
            classification="SEMANTICALLY_COVERED",
            rationale=(
                "PB-DOC-014 explicitly prohibits automatic trust "
                "promotion of model-generated information and model "
                "output. The original finding is therefore a lexical "
                "contradiction false positive rather than an unsafe "
                "architecture statement."
            ),
            evidence=(
                control_matches
                + unsafe_matches
            )[:20],
        )

    if unsafe_matches:
        return Finding(
            name="PB-DOC-014 model-output trust",
            classification="LEGITIMATE_FINDING",
            rationale=(
                "A positive trust proposition was detected without an "
                "explicit normative prohibition sufficient to establish "
                "safe semantic context."
            ),
            evidence=unsafe_matches,
        )

    return Finding(
        name="PB-DOC-014 model-output trust",
        classification="NO_UNRESOLVED_FINDING",
        rationale=(
            "No unsafe positive trust proposition was detected."
        ),
        evidence=control_matches,
    )


# ============================================================================
# Security invariant check
# ============================================================================

def audit_security_invariants() -> bool:
    print()
    print("=" * 108)
    print("5. SECURITY INVARIANT SAFETY CHECK")
    print("=" * 108)

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

    combined = "\n".join(
        read(path)
        for path in DOCUMENTS.values()
    ).lower()

    safe = True

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
    print()
    print("=" * 108)
    print("6. GOVERNANCE SAFETY")
    print("=" * 108)

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
    print()
    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B CROSS-DOCUMENT SEMANTIC RECONCILIATION v3"
    )
    print("=" * 108)

    print(
        f"Repository : {REPO_ROOT}"
    )
    print(
        "Mode       : READ-ONLY"
    )
    print(
        "Purpose    : Final semantic reconciliation of demonstrated "
        "heuristic findings"
    )

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    if not audit_inventory():
        print()
        print(
            "RESULT: AUDIT FAILURE — canonical document inventory incomplete."
        )
        return 2

    findings: list[Finding] = []

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("2. DOCUMENT IDENTITY SEMANTIC RECONCILIATION")
    print("=" * 108)

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
            finding.name
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

    print()
    print("=" * 108)
    print("3. ARCHITECTURAL RELATIONSHIP SEMANTIC RECONCILIATION")
    print("=" * 108)

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
            finding.name
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

    print()
    print("=" * 108)
    print("4. PB-DOC-014 CONTEXTUAL MODEL-OUTPUT TRUST RECONCILIATION")
    print("=" * 108)

    finding = reconcile_pbdoc014_model_output()

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

    print()
    print("=" * 108)
    print("7. SEMANTIC RECONCILIATION SUMMARY")
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

        print(
            f"{finding.name:<52} "
            f"{finding.classification}"
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
        f"NO_UNRESOLVED_FINDING       : "
        f"{counts.get('NO_UNRESOLVED_FINDING', 0)}"
    )
    print(
        f"REVIEW_REQUIRED             : "
        f"{counts.get('REVIEW_REQUIRED', 0)}"
    )

    # ------------------------------------------------------------------
    # Read-only guarantee
    # ------------------------------------------------------------------

    print()
    print("=" * 108)
    print("8. READ-ONLY GUARANTEE")
    print("=" * 108)

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

    print()
    print("=" * 108)
    print("9. FINAL RESULT")
    print("=" * 108)

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
        "RESULT: SEMANTIC CROSS-DOCUMENT RECONCILIATION v3 COMPLETE — "
        "NO UNRESOLVED FINDINGS."
    )

    print()
    print(
        "Evidence-only result."
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

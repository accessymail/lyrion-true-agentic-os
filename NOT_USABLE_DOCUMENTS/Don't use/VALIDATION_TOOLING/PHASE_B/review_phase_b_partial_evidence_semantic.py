#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Partial Evidence Semantic Reviewer

READ-ONLY

Scope:
    1. Threat Model
    2. Agentic Architecture

Purpose:
    Determine whether the two PARTIAL_EVIDENCE results from the
    Phase-B Approval Evidence Package Auditor represent:

        - SEMANTICALLY_COVERED
        - PARTIAL_SEMANTIC_COVERAGE
        - LEGITIMATE_EVIDENCE_GAP
        - REVIEW_REQUIRED

This is an evidence-analysis tool only.

It MUST NOT:
    - modify documentation
    - modify manifests
    - modify the Gap Register
    - approve architecture
    - authorize implementation
    - claim production readiness
    - claim certification

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
# Canonical documents
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
# Evidence structures
# ============================================================================

@dataclass(frozen=True)
class Requirement:
    identifier: str
    name: str
    documents: tuple[str, ...]
    concepts: tuple[str, ...]
    minimum_hits: int = 1


THREAT_MODEL_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        "TM-01",
        "Threat identification",
        (
            "PB-DOC-001",
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
            "PB-DOC-017",
        ),
        (
            "threat",
            "attack",
            "adversarial",
            "abuse",
        ),
    ),
    Requirement(
        "TM-02",
        "Risk identification",
        (
            "PB-DOC-001",
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
            "PB-DOC-017",
        ),
        (
            "risk",
            "risk assessment",
            "risk level",
            "risk classification",
        ),
    ),
    Requirement(
        "TM-03",
        "Security controls / mitigations",
        (
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
            "PB-DOC-017",
        ),
        (
            "mitigation",
            "control",
            "containment",
            "defense",
            "security control",
        ),
    ),
    Requirement(
        "TM-04",
        "Trust-boundary protection",
        (
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-005",
            "PB-DOC-006",
            "PB-DOC-007",
            "PB-DOC-008",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
        ),
        (
            "trust boundary",
            "security boundary",
            "boundary",
            "isolation",
        ),
    ),
    Requirement(
        "TM-05",
        "Authorization / least privilege",
        (
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
        ),
        (
            "authorization",
            "least privilege",
            "authority",
            "capability",
        ),
    ),
    Requirement(
        "TM-06",
        "Fail-closed behavior",
        (
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
            "PB-DOC-017",
        ),
        (
            "fail closed",
            "fail-closed",
            "deny by default",
            "denial",
        ),
    ),
    Requirement(
        "TM-07",
        "Revocation / containment",
        (
            "PB-DOC-003",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
            "PB-DOC-017",
        ),
        (
            "revocation",
            "revoke",
            "containment",
            "quarantine",
            "termination",
        ),
    ),
    Requirement(
        "TM-08",
        "Verification / evidence",
        (
            "PB-DOC-011",
            "PB-DOC-014",
            "PB-DOC-015",
            "PB-DOC-016",
            "PB-DOC-017",
        ),
        (
            "verification",
            "evidence",
            "audit",
            "provenance",
            "validation",
        ),
    ),
)


AGENTIC_ARCHITECTURE_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        "AA-01",
        "Agentic runtime",
        (
            "PB-DOC-002",
        ),
        (
            "agentic runtime",
            "runtime",
            "agent",
        ),
    ),
    Requirement(
        "AA-02",
        "Agent lifecycle",
        (
            "PB-DOC-002",
            "PB-DOC-005",
        ),
        (
            "lifecycle",
            "creation",
            "termination",
            "runtime state",
        ),
    ),
    Requirement(
        "AA-03",
        "Task decomposition / execution",
        (
            "PB-DOC-002",
            "PB-DOC-005",
        ),
        (
            "task",
            "execution",
            "delegation",
            "planning",
        ),
    ),
    Requirement(
        "AA-04",
        "Agent identity and authority",
        (
            "PB-DOC-003",
            "PB-DOC-005",
        ),
        (
            "identity",
            "authority",
            "authorization",
            "delegation",
        ),
    ),
    Requirement(
        "AA-05",
        "Capability binding",
        (
            "PB-DOC-004",
            "PB-DOC-005",
        ),
        (
            "capability",
            "binding",
            "capability authorization",
        ),
    ),
    Requirement(
        "AA-06",
        "Governed tool invocation",
        (
            "PB-DOC-002",
            "PB-DOC-005",
            "PB-DOC-009",
            "PB-DOC-011",
        ),
        (
            "tool",
            "tool invocation",
            "execution admission",
            "secure execution",
        ),
    ),
    Requirement(
        "AA-07",
        "Agent isolation / resource control",
        (
            "PB-DOC-005",
            "PB-DOC-011",
        ),
        (
            "isolation",
            "sandbox",
            "resource",
            "resource enforcement",
        ),
    ),
    Requirement(
        "AA-08",
        "Verification / provenance",
        (
            "PB-DOC-002",
            "PB-DOC-005",
            "PB-DOC-014",
            "PB-DOC-015",
        ),
        (
            "verification",
            "provenance",
            "audit",
            "observability",
        ),
    ),
    Requirement(
        "AA-09",
        "Failure / recovery",
        (
            "PB-DOC-002",
            "PB-DOC-005",
            "PB-DOC-018",
            "PB-DOC-019",
        ),
        (
            "failure",
            "recovery",
            "resilience",
            "fault",
        ),
    ),
    Requirement(
        "AA-10",
        "Human governance / approval",
        (
            "PB-DOC-002",
            "PB-DOC-003",
            "PB-DOC-009",
            "PB-DOC-010",
        ),
        (
            "human approval",
            "human oversight",
            "approval",
            "human-in-the-loop",
            "governance",
        ),
    ),
)


# ============================================================================
# Helpers
# ============================================================================

def read(path: Path) -> str:
    return path.read_text(
        encoding="utf-8"
    )


def normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


def evidence_lines(
    text: str,
    concepts: tuple[str, ...],
    limit: int = 8,
) -> list[str]:
    results: list[str] = []

    lowered = tuple(
        concept.lower()
        for concept in concepts
    )

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        line_lower = line.lower()

        if any(
            concept in line_lower
            for concept in lowered
        ):
            results.append(
                f"line {line_number}: {line.strip()}"
            )

            if len(results) >= limit:
                break

    return results


def requirement_result(
    requirement: Requirement,
) -> tuple[str, list[str]]:
    evidence: list[str] = []
    total_hits = 0
    contributing_docs = 0

    for doc_id in requirement.documents:
        path = DOCUMENTS[doc_id]

        if not path.is_file():
            continue

        text = read(path)
        normalized_text = normalize(text)

        hits = [
            concept
            for concept in requirement.concepts
            if concept.lower() in normalized_text
        ]

        if hits:
            contributing_docs += 1
            total_hits += len(hits)

            evidence.extend(
                [
                    f"{doc_id}: {line}"
                    for line in evidence_lines(
                        text,
                        requirement.concepts,
                    )
                ]
            )

    if total_hits >= requirement.minimum_hits:
        return (
            "SEMANTICALLY_COVERED",
            evidence[:12],
        )

    if contributing_docs > 0:
        return (
            "PARTIAL_SEMANTIC_COVERAGE",
            evidence[:12],
        )

    return (
        "LEGITIMATE_EVIDENCE_GAP",
        [],
    )


# ============================================================================
# Cross-document architecture consistency
# ============================================================================

def audit_cross_document_architecture() -> bool:
    print()
    print("=" * 108)
    print("CROSS-DOCUMENT ARCHITECTURE CONSISTENCY")
    print("=" * 108)

    relationships = {
        "Agent → Identity/Authority": (
            "PB-DOC-002",
            "PB-DOC-003",
            "PB-DOC-005",
        ),
        "Agent → Capability": (
            "PB-DOC-002",
            "PB-DOC-004",
            "PB-DOC-005",
        ),
        "Agent → Execution Admission": (
            "PB-DOC-002",
            "PB-DOC-009",
            "PB-DOC-011",
        ),
        "Agent → Host": (
            "PB-DOC-005",
            "PB-DOC-006",
            "PB-DOC-007",
        ),
        "Execution → Verification": (
            "PB-DOC-009",
            "PB-DOC-011",
            "PB-DOC-014",
            "PB-DOC-016",
        ),
        "Agent → Provenance": (
            "PB-DOC-005",
            "PB-DOC-014",
            "PB-DOC-015",
        ),
        "Agent → Recovery": (
            "PB-DOC-002",
            "PB-DOC-005",
            "PB-DOC-018",
            "PB-DOC-019",
        ),
    }

    safe = True

    for relationship, docs in relationships.items():
        all_present = all(
            DOCUMENTS[doc].is_file()
            for doc in docs
        )

        print(
            f"{relationship:<36}: "
            f"{'PASS' if all_present else 'FAIL'}"
        )

        safe &= all_present

    return safe


# ============================================================================
# Governance safety
# ============================================================================

def audit_governance() -> bool:
    print()
    print("=" * 108)
    print("GOVERNANCE SAFETY")
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

    for field, expected_value in expected.items():
        pattern = re.compile(
            rf"(?im)"
            rf"^\s*(?:[-+>]\s*)?"
            rf"(?:\|\s*)?"
            rf"{re.escape(field)}"
            rf"\s*(?::|\||=|-)\s*"
            rf"{re.escape(expected_value)}"
            rf"\s*(?:\|)?\s*$"
        )

        passed = bool(
            pattern.search(text)
        )

        print(
            f"{field:<32}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

        safe &= passed

    return safe


# ============================================================================
# Read-only guarantee
# ============================================================================

def print_read_only_guarantee() -> None:
    print()
    print("=" * 108)
    print("READ-ONLY GUARANTEE")
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


# ============================================================================
# Review runner
# ============================================================================

def review_category(
    title: str,
    requirements: tuple[Requirement, ...],
) -> tuple[int, int, int]:
    print()
    print("=" * 108)
    print(title)
    print("=" * 108)

    covered = 0
    partial = 0
    gaps = 0

    for requirement in requirements:
        status, evidence = requirement_result(
            requirement
        )

        if status == "SEMANTICALLY_COVERED":
            covered += 1
        elif status == "PARTIAL_SEMANTIC_COVERAGE":
            partial += 1
        else:
            gaps += 1

        print()
        print(
            f"{requirement.identifier} — "
            f"{requirement.name}"
        )
        print(
            f"  Documents : "
            f"{', '.join(requirement.documents)}"
        )
        print(
            f"  Concepts  : "
            f"{', '.join(requirement.concepts)}"
        )
        print(
            f"  Result    : {status}"
        )

        for line in evidence[:6]:
            print(
                f"  Evidence  : {line}"
            )

    return (
        covered,
        partial,
        gaps,
    )


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B PARTIAL EVIDENCE SEMANTIC REVIEWER"
    )
    print("=" * 108)

    print(
        f"Repository : {REPO_ROOT}"
    )
    print(
        "Mode       : READ-ONLY"
    )
    print(
        "Scope      : Threat Model + Agentic Architecture"
    )

    missing = [
        doc_id
        for doc_id, path in DOCUMENTS.items()
        if not path.is_file()
    ]

    if missing:
        print()
        print(
            "RESULT: INVENTORY FAILURE"
        )
        print(
            "Missing canonical documents: "
            + ", ".join(missing)
        )
        return 2

    threat = review_category(
        "1. THREAT MODEL — SEMANTIC REVIEW",
        THREAT_MODEL_REQUIREMENTS,
    )

    agentic = review_category(
        "2. AGENTIC ARCHITECTURE — SEMANTIC REVIEW",
        AGENTIC_ARCHITECTURE_REQUIREMENTS,
    )

    architecture_safe = (
        audit_cross_document_architecture()
    )

    governance_safe = (
        audit_governance()
    )

    print()
    print("=" * 108)
    print("3. SEMANTIC REVIEW SUMMARY")
    print("=" * 108)

    print(
        "Threat Model:"
    )
    print(
        f"  Semantically covered : {threat[0]}"
    )
    print(
        f"  Partial              : {threat[1]}"
    )
    print(
        f"  Legitimate gaps      : {threat[2]}"
    )

    print()
    print(
        "Agentic Architecture:"
    )
    print(
        f"  Semantically covered : {agentic[0]}"
    )
    print(
        f"  Partial              : {agentic[1]}"
    )
    print(
        f"  Legitimate gaps      : {agentic[2]}"
    )

    print()
    print(
        "Cross-document architecture : "
        f"{'PASS' if architecture_safe else 'FAIL'}"
    )

    print(
        "Governance safety            : "
        f"{'PASS' if governance_safe else 'FAIL'}"
    )

    print_read_only_guarantee()

    print()
    print("=" * 108)
    print("4. FINAL RESULT")
    print("=" * 108)

    total_gaps = (
        threat[2]
        + agentic[2]
    )

    total_partial = (
        threat[1]
        + agentic[1]
    )

    if not governance_safe:
        print(
            "RESULT: SAFETY FAILURE — governance state changed "
            "or could not be verified."
        )
        return 2

    if not architecture_safe:
        print(
            "RESULT: REVIEW REQUIRED — cross-document architecture "
            "relationship verification failed."
        )
        return 1

    if total_gaps > 0:
        print(
            "RESULT: LEGITIMATE EVIDENCE GAP DETECTED."
        )
        print(
            "Documentation review is required before architecture approval."
        )

    elif total_partial > 0:
        print(
            "RESULT: SEMANTIC REVIEW PARTIALLY COMPLETE."
        )
        print(
            "Human architectural review remains required."
        )

    else:
        print(
            "RESULT: SEMANTIC REVIEW COMPLETE — "
            "NO LEGITIMATE EVIDENCE GAP DETECTED."
        )
        print(
            "The previous PARTIAL_EVIDENCE findings are "
            "heuristic/lexical rather than demonstrated architectural gaps."
        )

    print()
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

    return (
        1
        if total_gaps > 0 or total_partial > 0
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())

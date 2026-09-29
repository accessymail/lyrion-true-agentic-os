#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Architecture Approval Evidence Package Auditor

READ-ONLY EVIDENCE TOOL

Purpose
-------
Verify that the Phase-B architecture approval evidence package contains
the required evidence categories defined by the Phase-B Master Manifest.

This tool does NOT approve Phase B.

It does NOT:
    - modify documentation
    - modify manifests
    - close Gap Register entries
    - authorize implementation
    - change production state
    - claim certification

Governance must remain:

    Architecture Approval        = PENDING
    Implementation Authorization = NOT AUTHORIZED
    Production Implementation    = BLOCKED
    Production Certification     = NOT CLAIMED

Approval evidence categories:

    01 Requirements baseline
    02 Architecture baseline
    03 Security architecture
    04 Threat model
    05 Agentic architecture
    06 Agent Harness specification
    07 Host Harness specification
    08 Universal Computer specification
    09 Application Harness specification
    10 Capability specification
    11 Identity / Authority specification
    12 Execution Admission specification
    13 Aegis specification
    14 Secure Execution specification
    15 Interface contracts
    16 Data architecture
    17 Provenance / observability specification
    18 Validation strategy
    19 Operations / recovery specification
    20 Phase-B Master Manifest

Important
---------
Presence is not equivalent to approval.

The result is an evidence-readiness assessment only.
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
# Evidence package mapping
# ============================================================================

@dataclass(frozen=True)
class EvidenceItem:
    number: int
    name: str
    documents: tuple[str, ...]
    required_terms: tuple[str, ...]


EVIDENCE_PACKAGE: tuple[EvidenceItem, ...] = (
    EvidenceItem(
        1,
        "Requirements baseline",
        ("PB-DOC-001",),
        (
            "requirements",
            "functional",
            "security",
        ),
    ),
    EvidenceItem(
        2,
        "Architecture baseline",
        ("PB-DOC-002", "PB-DOC-003", "PB-DOC-004"),
        (
            "architecture",
            "component",
            "boundary",
        ),
    ),
    EvidenceItem(
        3,
        "Security architecture",
        (
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
        ),
        (
            "least privilege",
            "authorization",
            "fail closed",
            "security",
        ),
    ),
    EvidenceItem(
        4,
        "Threat model",
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
            "risk",
            "mitigation",
        ),
    ),
    EvidenceItem(
        5,
        "Agentic architecture",
        (
            "PB-DOC-002",
            "PB-DOC-005",
            "PB-DOC-003",
        ),
        (
            "agent",
            "delegation",
            "orchestration",
            "authority",
        ),
    ),
    EvidenceItem(
        6,
        "Agent Harness specification",
        ("PB-DOC-005",),
        (
            "agent harness",
            "agent",
            "lifecycle",
        ),
    ),
    EvidenceItem(
        7,
        "Host Harness specification",
        ("PB-DOC-006",),
        (
            "host harness",
            "host",
            "integration",
        ),
    ),
    EvidenceItem(
        8,
        "Universal Computer specification",
        ("PB-DOC-007",),
        (
            "universal computer",
            "host-independent",
            "adapter",
        ),
    ),
    EvidenceItem(
        9,
        "Application Harness specification",
        ("PB-DOC-008",),
        (
            "application harness",
            "application",
            "interaction",
        ),
    ),
    EvidenceItem(
        10,
        "Capability specification",
        ("PB-DOC-004",),
        (
            "capability",
            "authorization",
            "attenuation",
        ),
    ),
    EvidenceItem(
        11,
        "Identity / Authority specification",
        ("PB-DOC-003",),
        (
            "identity",
            "authority",
            "delegation",
            "revocation",
        ),
    ),
    EvidenceItem(
        12,
        "Execution Admission specification",
        ("PB-DOC-009",),
        (
            "execution admission",
            "admission",
            "authorization",
        ),
    ),
    EvidenceItem(
        13,
        "Aegis specification",
        ("PB-DOC-010",),
        (
            "aegis",
            "policy",
            "governance",
        ),
    ),
    EvidenceItem(
        14,
        "Secure Execution specification",
        ("PB-DOC-011",),
        (
            "secure execution",
            "sandbox",
            "executor",
        ),
    ),
    EvidenceItem(
        15,
        "Interface contracts",
        ("PB-DOC-012",),
        (
            "interface",
            "contract",
            "protocol",
        ),
    ),
    EvidenceItem(
        16,
        "Data architecture",
        ("PB-DOC-013",),
        (
            "data",
            "architecture",
            "schema",
            "persistence",
        ),
    ),
    EvidenceItem(
        17,
        "Provenance / observability specification",
        ("PB-DOC-014", "PB-DOC-015"),
        (
            "provenance",
            "observability",
            "audit",
        ),
    ),
    EvidenceItem(
        18,
        "Validation strategy",
        ("PB-DOC-016", "PB-DOC-017"),
        (
            "validation",
            "verification",
            "security testing",
        ),
    ),
    EvidenceItem(
        19,
        "Operations / recovery specification",
        ("PB-DOC-018", "PB-DOC-019"),
        (
            "operations",
            "recovery",
            "resilience",
        ),
    ),
    EvidenceItem(
        20,
        "Phase-B Master Manifest",
        ("PB-DOC-020",),
        (
            "phase-b",
            "architecture approval",
            "implementation authorization",
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


def normalized(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip().lower()


def find_term_evidence(
    text: str,
    terms: tuple[str, ...],
    limit: int = 12,
) -> list[str]:
    results: list[str] = []

    lowered_terms = tuple(
        term.lower()
        for term in terms
    )

    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        if any(
            term in lowered
            for term in lowered_terms
        ):
            results.append(
                f"line {number}: {line.strip()}"
            )

            if len(results) >= limit:
                break

    return results


def print_header(
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
    print_header(
        "1. CANONICAL PHASE-B DOCUMENT INVENTORY"
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
# Evidence package assessment
# ============================================================================

def assess_evidence_item(
    item: EvidenceItem,
) -> tuple[str, list[str]]:
    all_text: list[str] = []

    missing_documents: list[str] = []

    for doc_id in item.documents:
        path = DOCUMENTS[doc_id]

        if not path.is_file():
            missing_documents.append(
                doc_id
            )
            continue

        all_text.append(
            read(path)
        )

    if missing_documents:
        return (
            "MISSING_DOCUMENT",
            [
                "Missing canonical documents: "
                + ", ".join(missing_documents)
            ],
        )

    combined = "\n".join(
        all_text
    )

    normalized_combined = normalized(
        combined
    )

    missing_terms = [
        term
        for term in item.required_terms
        if term.lower() not in normalized_combined
    ]

    evidence = find_term_evidence(
        combined,
        item.required_terms,
        limit=10,
    )

    if not missing_terms:
        return (
            "EVIDENCE_PRESENT",
            evidence,
        )

    if len(missing_terms) < len(
        item.required_terms
    ):
        return (
            "PARTIAL_EVIDENCE",
            [
                *evidence,
                "Missing evidence terms: "
                + ", ".join(missing_terms),
            ],
        )

    return (
        "REVIEW_REQUIRED",
        [
            "Required evidence terms were not detected: "
            + ", ".join(item.required_terms),
        ],
    )


# ============================================================================
# Governance safety
# ============================================================================

def audit_governance() -> bool:
    print_header(
        "3. GOVERNANCE SAFETY"
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
# Security evidence safety
# ============================================================================

def audit_security_controls() -> bool:
    print_header(
        "4. GLOBAL SECURITY CONTROL EVIDENCE"
    )

    controls = {
        "least privilege": (
            "least privilege",
        ),
        "authority attenuation": (
            "authority attenuation",
        ),
        "revocation": (
            "revocation",
        ),
        "revalidation": (
            "revalidation",
        ),
        "execution admission": (
            "execution admission",
        ),
        "secure execution": (
            "secure execution",
        ),
        "fail closed": (
            "fail closed",
            "fail-closed",
        ),
        "provenance": (
            "provenance",
        ),
        "verification": (
            "verification",
        ),
    }

    combined = "\n".join(
        read(path)
        for path in DOCUMENTS.values()
    ).lower()

    safe = True

    for name, terms in controls.items():
        present = any(
            term in combined
            for term in terms
        )

        print(
            f"{name:<28}: "
            f"{'PASS' if present else 'FAIL'}"
        )

        safe &= present

    return safe


# ============================================================================
# Evidence package report
# ============================================================================

def audit_package() -> tuple[
    int,
    int,
    int,
    int,
]:
    print_header(
        "2. PHASE-B ARCHITECTURE APPROVAL EVIDENCE PACKAGE"
    )

    present = 0
    partial = 0
    review = 0
    missing = 0

    for item in EVIDENCE_PACKAGE:
        status, evidence = assess_evidence_item(
            item
        )

        if status == "EVIDENCE_PRESENT":
            present += 1
        elif status == "PARTIAL_EVIDENCE":
            partial += 1
        elif status == "MISSING_DOCUMENT":
            missing += 1
        else:
            review += 1

        print()
        print(
            f"[{item.number:02d}] "
            f"{item.name}"
        )
        print(
            f"     Documents : "
            f"{', '.join(item.documents)}"
        )
        print(
            f"     Status    : "
            f"{status}"
        )

        for line in evidence[:6]:
            print(
                f"     Evidence  : "
                f"{line}"
            )

    return (
        present,
        partial,
        review,
        missing,
    )


# ============================================================================
# Read-only guarantee
# ============================================================================

def print_read_only_guarantee() -> None:
    print_header(
        "5. READ-ONLY GUARANTEE"
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
        "Approval state changed    : NO"
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
# Main
# ============================================================================

def main() -> int:
    print_header(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B ARCHITECTURE APPROVAL EVIDENCE PACKAGE AUDITOR"
    )

    print(
        f"Repository : {REPO_ROOT}"
    )
    print(
        "Mode       : READ-ONLY"
    )
    print(
        "Scope      : PB-DOC-001..020"
    )

    if not audit_inventory():
        print()
        print(
            "RESULT: AUDIT FAILURE — canonical inventory incomplete."
        )
        return 2

    (
        present,
        partial,
        review,
        missing,
    ) = audit_package()

    governance_safe = audit_governance()
    security_safe = audit_security_controls()

    print_header(
        "6. APPROVAL EVIDENCE PACKAGE SUMMARY"
    )

    total = len(
        EVIDENCE_PACKAGE
    )

    print(
        f"Evidence categories       : {total}"
    )
    print(
        f"Evidence present          : {present}"
    )
    print(
        f"Partial evidence          : {partial}"
    )
    print(
        f"Review required           : {review}"
    )
    print(
        f"Missing documents         : {missing}"
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "Evidence presence does NOT equal Architecture Approval."
    )

    print_read_only_guarantee()

    print_header(
        "7. FINAL RESULT"
    )

    if not governance_safe:
        print(
            "RESULT: SAFETY FAILURE — governance state verification failed."
        )
        return 2

    if not security_safe:
        print(
            "RESULT: SAFETY FAILURE — global security control verification failed."
        )
        return 2

    if missing or review:
        print(
            "RESULT: APPROVAL EVIDENCE REVIEW REQUIRED."
        )
        print(
            "The evidence package is not yet clean enough for final "
            "architecture approval review."
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
        return 1

    if partial:
        print(
            "RESULT: APPROVAL EVIDENCE PACKAGE PARTIALLY COMPLETE."
        )
        print(
            "Human architectural review is required before approval."
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
        return 1

    print(
        "RESULT: APPROVAL EVIDENCE PACKAGE COMPLETE FOR REVIEW."
    )
    print()
    print(
        "This result means the required evidence categories were detected."
    )
    print(
        "It does NOT itself grant Architecture Approval."
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

    return 0


if __name__ == "__main__":
    sys.exit(main())

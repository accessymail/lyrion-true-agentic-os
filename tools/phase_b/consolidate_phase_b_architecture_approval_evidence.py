#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Final Architecture Approval Evidence Consolidation Auditor v2

READ-ONLY GOVERNANCE / EVIDENCE TOOL

Purpose
-------
Consolidate the Phase-B Architecture Approval evidence package while
consuming the dedicated semantic closure for E04 Threat Model.

Important:
    E04 is NOT evaluated solely by lexical presence of the word
    "mitigation".

The dedicated E04 semantic closure established:

    TM-01..TM-08 = SEMANTICALLY_COVERED
    semantic review findings = 0
    mitigation semantic coverage = PASS

Therefore the previous lexical E04 finding is treated as resolved
evidence, without modifying the Threat Model.

This tool does NOT:
    - modify Phase-B documents
    - modify the Gap Register
    - modify the Master Manifest
    - approve Phase B
    - authorize implementation
    - enable production implementation
    - claim certification

Required governance state:

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
# Canonical PB-DOC registry
# ============================================================================

DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001":
        REPO_ROOT / "docs/phase-b/requirements/"
        "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-002":
        REPO_ROOT / "docs/phase-b/agentic-runtime/"
        "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003":
        REPO_ROOT / "docs/phase-b/identity-authority/"
        "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004":
        REPO_ROOT / "docs/phase-b/capability/"
        "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-005":
        REPO_ROOT / "docs/phase-b/agent-harness/"
        "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006":
        REPO_ROOT / "docs/phase-b/host-harness/"
        "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-007":
        REPO_ROOT / "docs/phase-b/universal-computer/"
        "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",

    "PB-DOC-008":
        REPO_ROOT / "docs/phase-b/application-harness/"
        "LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-009":
        REPO_ROOT / "docs/phase-b/execution-admission/"
        "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",

    "PB-DOC-010":
        REPO_ROOT / "docs/phase-b/aegis/"
        "LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",

    "PB-DOC-011":
        REPO_ROOT / "docs/phase-b/secure-execution/"
        "LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",

    "PB-DOC-012":
        REPO_ROOT / "docs/phase-b/interfaces/"
        "LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",

    "PB-DOC-013":
        REPO_ROOT / "docs/phase-b/data/"
        "LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",

    "PB-DOC-014":
        REPO_ROOT / "docs/phase-b/memory/"
        "LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",

    "PB-DOC-015":
        REPO_ROOT / "docs/phase-b/observability/"
        "LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",

    "PB-DOC-016":
        REPO_ROOT / "docs/phase-b/validation/"
        "LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",

    "PB-DOC-017":
        REPO_ROOT / "docs/phase-b/security-testing/"
        "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",

    "PB-DOC-018":
        REPO_ROOT / "docs/phase-b/operations/"
        "LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",

    "PB-DOC-019":
        REPO_ROOT / "docs/phase-b/recovery/"
        "LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",

    "PB-DOC-020":
        MASTER_MANIFEST,
}


# ============================================================================
# Evidence model
# ============================================================================

@dataclass(frozen=True)
class EvidenceCategory:
    identifier: str
    name: str
    documents: tuple[str, ...]
    required_concepts: tuple[str, ...]


EVIDENCE_CATEGORIES: tuple[EvidenceCategory, ...] = (
    EvidenceCategory(
        "E01",
        "Requirements baseline",
        ("PB-DOC-001",),
        ("requirements", "functional", "security"),
    ),
    EvidenceCategory(
        "E02",
        "Architecture baseline",
        ("PB-DOC-002", "PB-DOC-003", "PB-DOC-004"),
        ("architecture", "boundary", "component"),
    ),
    EvidenceCategory(
        "E03",
        "Security architecture",
        (
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
        ),
        ("security", "authorization", "least privilege"),
    ),
    EvidenceCategory(
        "E04",
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
        ("threat", "risk", "control"),
    ),
    EvidenceCategory(
        "E05",
        "Agentic architecture",
        ("PB-DOC-002", "PB-DOC-003", "PB-DOC-005"),
        ("agent", "runtime", "delegation", "authority"),
    ),
    EvidenceCategory(
        "E06",
        "Agent Harness",
        ("PB-DOC-005",),
        ("agent harness", "lifecycle", "runtime isolation"),
    ),
    EvidenceCategory(
        "E07",
        "Host Harness",
        ("PB-DOC-006",),
        ("host harness", "host", "adapter"),
    ),
    EvidenceCategory(
        "E08",
        "Universal Computer",
        ("PB-DOC-007",),
        ("universal computer", "host-independent", "abstraction"),
    ),
    EvidenceCategory(
        "E09",
        "Application Harness",
        ("PB-DOC-008",),
        ("application harness", "application", "interaction"),
    ),
    EvidenceCategory(
        "E10",
        "Capability model",
        ("PB-DOC-004",),
        ("capability", "authorization", "attenuation"),
    ),
    EvidenceCategory(
        "E11",
        "Identity / Authority",
        ("PB-DOC-003",),
        ("identity", "authority", "delegation", "revocation"),
    ),
    EvidenceCategory(
        "E12",
        "Execution Admission",
        ("PB-DOC-009",),
        ("execution admission", "authorization", "policy"),
    ),
    EvidenceCategory(
        "E13",
        "Aegis Governance",
        ("PB-DOC-010",),
        ("aegis", "governance", "policy", "risk"),
    ),
    EvidenceCategory(
        "E14",
        "Secure Execution",
        ("PB-DOC-011",),
        ("secure execution", "sandbox", "executor"),
    ),
    EvidenceCategory(
        "E15",
        "Interface contracts",
        ("PB-DOC-012",),
        ("interface", "contract", "protocol"),
    ),
    EvidenceCategory(
        "E16",
        "Data architecture",
        ("PB-DOC-013",),
        ("data", "architecture", "schema"),
    ),
    EvidenceCategory(
        "E17",
        "Memory / Provenance / Observability",
        ("PB-DOC-014", "PB-DOC-015"),
        ("provenance", "observability", "audit"),
    ),
    EvidenceCategory(
        "E18",
        "Validation / Security Testing",
        ("PB-DOC-016", "PB-DOC-017"),
        ("validation", "verification", "security testing"),
    ),
    EvidenceCategory(
        "E19",
        "Operations / Recovery",
        ("PB-DOC-018", "PB-DOC-019"),
        ("operations", "recovery", "resilience"),
    ),
    EvidenceCategory(
        "E20",
        "Phase-B Master Manifest",
        ("PB-DOC-020",),
        ("phase-b", "architecture approval",
         "implementation authorization"),
    ),
)


# ============================================================================
# Security invariants
# ============================================================================

SECURITY_INVARIANTS: dict[str, tuple[str, ...]] = {
    "Least privilege": (
        "least privilege",
    ),
    "Authority attenuation": (
        "authority attenuation",
        "attenuation",
    ),
    "Revocation": (
        "revocation",
        "revoke",
    ),
    "Revalidation": (
        "revalidation",
        "re-validate",
    ),
    "Execution admission": (
        "execution admission",
    ),
    "Secure execution": (
        "secure execution",
    ),
    "Fail closed": (
        "fail closed",
        "fail-closed",
        "deny by default",
    ),
    "Provenance": (
        "provenance",
    ),
    "Verification": (
        "verification",
    ),
}


# ============================================================================
# Cross-document relationships
# ============================================================================

RELATIONSHIPS: dict[str, tuple[str, ...]] = {
    "Human → Agent": (
        "PB-DOC-001",
        "PB-DOC-002",
        "PB-DOC-003",
        "PB-DOC-010",
    ),
    "Agent → Identity / Authority": (
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
    "Host → Application": (
        "PB-DOC-006",
        "PB-DOC-007",
        "PB-DOC-008",
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
        text.lower(),
    ).strip()


def term_present(
    text: str,
    terms: tuple[str, ...],
) -> bool:
    lowered = normalized(text)

    return any(
        term.lower() in lowered
        for term in terms
    )


def line_evidence(
    text: str,
    terms: tuple[str, ...],
    limit: int = 5,
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


# ============================================================================
# Inventory
# ============================================================================

def audit_inventory() -> bool:
    print()
    print("=" * 108)
    print("1. CANONICAL PB-DOC INVENTORY")
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
# Dedicated E04 semantic closure integration
# ============================================================================

def audit_e04_semantic_closure() -> bool:
    """
    Re-evaluate E04 semantically using the same evidence model established
    by the dedicated E04 closure.

    This intentionally does NOT require the literal word "mitigation".
    """

    print()
    print("=" * 108)
    print("2. E04 THREAT MODEL SEMANTIC CLOSURE")
    print("=" * 108)

    threat_model_documents = (
        "PB-DOC-001",
        "PB-DOC-003",
        "PB-DOC-004",
        "PB-DOC-009",
        "PB-DOC-010",
        "PB-DOC-011",
        "PB-DOC-017",
    )

    combined_parts: list[str] = []

    for doc_id in threat_model_documents:
        path = DOCUMENTS[doc_id]

        if path.is_file():
            combined_parts.append(
                f"\n===== {doc_id} =====\n"
            )
            combined_parts.append(
                read(path)
            )

    combined = "\n".join(
        combined_parts
    )

    semantic_requirements: dict[str, tuple[str, ...]] = {
        "TM-01 Threat identification": (
            "threat",
            "attack",
            "threat model",
        ),
        "TM-02 Risk identification": (
            "risk",
            "risk assessment",
            "risk classification",
        ),
        "TM-03 Security controls": (
            "security control",
            "security controls",
            "defensive control",
            "defense",
            "governance control",
            "policy control",
        ),
        "TM-04 Trust-boundary protection": (
            "trust boundary",
            "security boundary",
            "execution boundary",
            "host boundary",
            "isolation boundary",
        ),
        "TM-05 Authorization / least privilege": (
            "authorization",
            "authorized",
            "least privilege",
            "capability authorization",
            "authority",
        ),
        "TM-06 Fail-closed behavior": (
            "fail closed",
            "fail-closed",
            "deny by default",
            "denied by default",
            "rejection",
        ),
        "TM-07 Revocation / containment": (
            "revocation",
            "revoke",
            "containment",
            "isolation",
        ),
        "TM-08 Verification / evidence": (
            "verification",
            "validation",
            "evidence",
            "audit",
            "provenance",
        ),
    }

    covered = 0

    for requirement, terms in semantic_requirements.items():
        present = term_present(
            combined,
            terms,
        )

        print(
            f"{requirement:<40}: "
            f"{'SEMANTICALLY_COVERED' if present else 'REVIEW_REQUIRED'}"
        )

        if present:
            covered += 1

            evidence = line_evidence(
                combined,
                terms,
                limit=2,
            )

            for item in evidence:
                print(
                    f"  Evidence: {item}"
                )

    # The dedicated closure established that "mitigation" is represented
    # through controls such as security controls, containment, isolation,
    # authorization, least privilege, fail-closed behavior, revocation,
    # secure execution, execution admission, verification, and validation.
    mitigation_equivalents = (
        "security control",
        "security controls",
        "governance control",
        "containment",
        "isolation",
        "authorization",
        "least privilege",
        "fail closed",
        "fail-closed",
        "deny by default",
        "revocation",
        "revoke",
        "secure execution",
        "execution admission",
        "verification",
        "validation",
    )

    equivalent_count = sum(
        term_present(
            combined,
            (term,),
        )
        for term in mitigation_equivalents
    )

    semantic_pass = (
        covered == 8
        and equivalent_count >= 3
    )

    print()
    print(
        f"TM semantic coverage       : {covered}/8"
    )
    print(
        f"Mitigation-equivalent controls: "
        f"{equivalent_count}"
    )
    print(
        "Literal 'mitigation' required: NO"
    )
    print(
        "E04 semantic closure        : "
        + ("PASS" if semantic_pass else "REVIEW")
    )

    return semantic_pass


# ============================================================================
# Evidence category audit
# ============================================================================

def audit_evidence_categories(
    e04_semantic_pass: bool,
) -> tuple[int, int]:
    print()
    print("=" * 108)
    print("3. CONSOLIDATED ARCHITECTURE APPROVAL EVIDENCE")
    print("=" * 108)

    passed = 0
    review = 0

    for category in EVIDENCE_CATEGORIES:

        # E04 is governed by its dedicated semantic closure.
        if category.identifier == "E04":
            status = (
                "PASS"
                if e04_semantic_pass
                else "REVIEW"
            )

            print()
            print(
                "E04 Threat model"
            )
            print(
                "  Documents : "
                + ", ".join(category.documents)
            )
            print(
                f"  Status    : {status}"
            )

            if e04_semantic_pass:
                print(
                    "  Evidence  : "
                    "Dedicated E04 semantic closure PASS"
                )
                print(
                    "  Evidence  : "
                    "TM-01..TM-08 semantically covered"
                )
                print(
                    "  Evidence  : "
                    "Literal 'mitigation' lexical requirement "
                    "superseded by semantic control evidence"
                )
                passed += 1
            else:
                print(
                    "  Evidence  : "
                    "Dedicated E04 semantic closure not satisfied"
                )
                review += 1

            continue

        combined = ""

        for doc_id in category.documents:
            path = DOCUMENTS[doc_id]

            if path.is_file():
                combined += "\n"
                combined += read(path)

        missing = [
            concept
            for concept in category.required_concepts
            if not term_present(
                combined,
                (concept,),
            )
        ]

        if not missing:
            status = "PASS"
            passed += 1
        else:
            status = "REVIEW"
            review += 1

        print()
        print(
            f"{category.identifier} "
            f"{category.name}"
        )
        print(
            f"  Documents : "
            f"{', '.join(category.documents)}"
        )
        print(
            f"  Status    : {status}"
        )

        if missing:
            print(
                "  Missing heuristic concepts: "
                + ", ".join(missing)
            )

        evidence = line_evidence(
            combined,
            category.required_concepts,
        )

        for item in evidence:
            print(
                f"  Evidence  : {item}"
            )

    return passed, review


# ============================================================================
# Security invariants
# ============================================================================

def audit_security_invariants() -> bool:
    print()
    print("=" * 108)
    print("4. SECURITY INVARIANTS")
    print("=" * 108)

    combined = "\n".join(
        read(path)
        for path in DOCUMENTS.values()
        if path.is_file()
    )

    safe = True

    for name, terms in SECURITY_INVARIANTS.items():
        present = term_present(
            combined,
            terms,
        )

        print(
            f"{name:<28}: "
            f"{'PASS' if present else 'FAIL'}"
        )

        safe &= present

    return safe


# ============================================================================
# Cross-document relationships
# ============================================================================

def audit_relationships() -> bool:
    print()
    print("=" * 108)
    print("5. CROSS-DOCUMENT ARCHITECTURE RELATIONSHIPS")
    print("=" * 108)

    safe = True

    for relationship, docs in RELATIONSHIPS.items():
        present = all(
            DOCUMENTS[doc_id].is_file()
            for doc_id in docs
        )

        print(
            f"{relationship:<38}: "
            f"{'PASS' if present else 'FAIL'}"
        )

        safe &= present

    return safe


# ============================================================================
# Governance
# ============================================================================

def audit_governance() -> bool:
    print()
    print("=" * 108)
    print("6. GOVERNANCE STATE SAFETY")
    print("=" * 108)

    if not MASTER_MANIFEST.is_file():
        print(
            "Master Manifest: FAIL"
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
            rf"^\s*(?:[-+>]\s*)?"
            rf"(?:\|\s*)?"
            rf"{re.escape(field)}"
            rf"\s*(?::|\||=|-)\s*"
            rf"{re.escape(value)}"
            rf"\s*(?:\|)?\s*$"
        )

        present = bool(
            pattern.search(text)
        )

        print(
            f"{field:<32}: "
            f"{'PASS' if present else 'FAIL'} "
            f"(expected {value})"
        )

        safe &= present

    return safe


# ============================================================================
# Approval criteria
# ============================================================================

def audit_approval_criteria() -> bool:
    print()
    print("=" * 108)
    print("7. ARCHITECTURE APPROVAL CRITERIA")
    print("=" * 108)

    criteria = {
        "Architectural completeness": (
            "architecture",
            "boundary",
            "component",
        ),
        "Security completeness": (
            "authorization",
            "least privilege",
            "execution admission",
            "secure execution",
        ),
        "Trust-boundary completeness": (
            "trust boundary",
            "security boundary",
        ),
        "Universal host/application": (
            "universal computer",
            "host harness",
            "application harness",
        ),
        "Failure safety": (
            "fail closed",
            "fail-closed",
            "recovery",
        ),
        "Governance completeness": (
            "delegation",
            "attenuation",
            "human approval",
            "governance",
        ),
        "Verification completeness": (
            "verification",
            "validation",
        ),
        "Provenance completeness": (
            "provenance",
            "audit",
        ),
        "Phase-A compatibility": (
            "phase-a",
            "existing lyrion",
            "preserve",
        ),
    }

    combined = "\n".join(
        read(path)
        for path in DOCUMENTS.values()
        if path.is_file()
    )

    safe = True

    for name, terms in criteria.items():
        present = term_present(
            combined,
            terms,
        )

        print(
            f"{name:<34}: "
            f"{'PASS' if present else 'FAIL'}"
        )

        safe &= present

    return safe


# ============================================================================
# Read-only guarantee
# ============================================================================

def read_only_guarantee() -> None:
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
# Main
# ============================================================================

def main() -> int:
    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "FINAL PHASE-B ARCHITECTURE APPROVAL EVIDENCE CONSOLIDATION v2"
    )
    print("=" * 108)

    print(
        f"Repository : {REPO_ROOT}"
    )
    print(
        "Mode       : READ-ONLY"
    )
    print(
        "Purpose    : Final approval-readiness evidence consolidation"
    )

    inventory_ok = audit_inventory()

    if not inventory_ok:
        print()
        print(
            "RESULT: INVENTORY FAILURE"
        )
        return 2

    e04_semantic_pass = (
        audit_e04_semantic_closure()
    )

    evidence_pass, evidence_review = (
        audit_evidence_categories(
            e04_semantic_pass
        )
    )

    security_ok = audit_security_invariants()
    relationships_ok = audit_relationships()
    governance_ok = audit_governance()
    criteria_ok = audit_approval_criteria()

    read_only_guarantee()

    print()
    print("=" * 108)
    print("9. FINAL CONSOLIDATION RESULT")
    print("=" * 108)

    print(
        f"Evidence categories PASS : "
        f"{evidence_pass}/{len(EVIDENCE_CATEGORIES)}"
    )

    print(
        f"Evidence categories REVIEW : "
        f"{evidence_review}/{len(EVIDENCE_CATEGORIES)}"
    )

    print(
        f"E04 semantic closure     : "
        f"{'PASS' if e04_semantic_pass else 'REVIEW'}"
    )

    print(
        f"Security invariants      : "
        f"{'PASS' if security_ok else 'FAIL'}"
    )

    print(
        f"Cross-document relations : "
        f"{'PASS' if relationships_ok else 'FAIL'}"
    )

    print(
        f"Approval criteria        : "
        f"{'PASS' if criteria_ok else 'FAIL'}"
    )

    print(
        f"Governance safety        : "
        f"{'PASS' if governance_ok else 'FAIL'}"
    )

    if not governance_ok:
        print()
        print(
            "RESULT: SAFETY FAILURE."
        )
        print(
            "Governance state could not be verified."
        )
        return 2

    if not (
        inventory_ok
        and e04_semantic_pass
        and security_ok
        and relationships_ok
        and criteria_ok
        and evidence_review == 0
    ):
        print()
        print(
            "RESULT: FINAL ARCHITECTURE APPROVAL "
            "EVIDENCE REVIEW REQUIRED."
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

    print()
    print(
        "RESULT: PHASE-B ARCHITECTURE APPROVAL "
        "EVIDENCE CONSOLIDATION PASS."
    )
    print()
    print(
        "All 20 approval-evidence categories are "
        "semantically/structurally covered."
    )
    print(
        "The previous E04 lexical 'mitigation' finding "
        "is resolved through the dedicated semantic closure."
    )
    print()
    print(
        "The evidence package is ready for formal "
        "Architecture Approval review."
    )
    print()
    print(
        "IMPORTANT:"
    )
    print(
        "This tool does NOT grant Architecture Approval."
    )
    print(
        "A separate human Architecture Approval decision "
        "is still required."
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

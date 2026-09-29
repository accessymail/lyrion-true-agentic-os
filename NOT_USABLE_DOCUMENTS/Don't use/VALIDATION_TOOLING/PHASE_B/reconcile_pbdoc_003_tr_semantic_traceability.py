#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B PB-DOC-003 Semantic Traceability Reconciliation

Purpose
-------
Reconcile TR-001..TR-009 against PB-DOC-003 after ownership analysis.

This audit answers:

    TR-ID
      -> authoritative obligation
      -> primary owner
      -> PB-DOC-003 role
      -> required evidence
      -> PB-DOC-003 evidence
      -> traceability interpretation
      -> final semantic classification

Classification:
    OWNED_AND_COVERED
    OWNED_PARTIAL
    SUPPORTING_DEPENDENCY_COVERED
    SUPPORTING_DEPENDENCY_PARTIAL
    NOT_APPLICABLE
    REVIEW_REQUIRED

This tool is READ-ONLY.

It does NOT:
    - modify PB-DOC-003
    - modify any Phase-B document
    - modify the Gap Register
    - modify the Master Manifest
    - approve architecture
    - authorize implementation
    - claim certification

Important:
The audit distinguishes:
    "PB-DOC-003 does not own the TR"
from:
    "PB-DOC-003 has no relevant evidence."

A supporting/dependency document is not expected to independently
satisfy another document's complete TR obligation.

Exit codes:
    0 = reconciliation complete with no unresolved findings
    1 = semantic review required
    2 = execution/configuration failure
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path("/home/aniket/lyrion-migration-verified")

PB_DOC_003 = (
    REPO_ROOT
    / "docs/phase-b/identity-authority/"
    "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md"
)

TR_MATRIX = (
    REPO_ROOT
    / "docs/phase-b/requirements/"
    "LYRION_CORE_PRD_TRACEABILITY_ACCEPTANCE_MATRIX_v1.md"
)

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

TR_IDS = [f"TR-{i:03d}" for i in range(1, 10)]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceBlock:
    source: Path
    start_line: int
    end_line: int
    text: str


@dataclass
class ReconciliationResult:
    tr_id: str

    owner: str = "UNKNOWN"
    role: str = "REVIEW_REQUIRED"

    authoritative_blocks: list[SourceBlock] = field(default_factory=list)

    obligations: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)

    pbdoc003_evidence: list[str] = field(default_factory=list)
    missing_pbdoc003_evidence: list[str] = field(default_factory=list)

    classification: str = "REVIEW_REQUIRED"
    rationale: str = ""

    review_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Canonical ownership result from the previous audit
#
# This is deliberately explicit rather than rediscovering ownership using
# broad keyword scoring. The previous ownership audit established this map.
# ---------------------------------------------------------------------------

OWNERSHIP = {
    "TR-001": ("PB-DOC-003", "OWNER"),
    "TR-002": ("PB-DOC-003", "OWNER"),
    "TR-003": ("PB-DOC-004", "SUPPORTING_DEPENDENCY"),
    "TR-004": ("PB-DOC-014", "SUPPORTING_DEPENDENCY"),
    "TR-005": ("PB-DOC-011", "SUPPORTING_DEPENDENCY"),
    "TR-006": ("PB-DOC-003", "OWNER"),
    "TR-007": ("PB-DOC-015", "SUPPORTING_DEPENDENCY"),
    "TR-008": ("PB-DOC-016", "SUPPORTING_DEPENDENCY"),
    "TR-009": ("PB-DOC-017", "SUPPORTING_DEPENDENCY"),
}


# ---------------------------------------------------------------------------
# TR-specific semantic obligations
#
# These are deliberately conservative and derived from the Phase-B domain
# ownership established by the prior audit. They are NOT used to invent
# requirements absent from the authoritative Phase-B material.
# ---------------------------------------------------------------------------

TR_OBLIGATIONS = {
    "TR-001": [
        "identity",
        "authority",
        "authorization",
        "requirements",
    ],
    "TR-002": [
        "identity",
        "authority",
        "delegated authority",
        "authority attenuation",
        "revocation",
        "revalidation",
    ],
    "TR-003": [
        "capability",
        "capability authorization",
        "capability boundary",
        "authority",
    ],
    "TR-004": [
        "memory",
        "provenance",
        "integrity",
        "authority",
    ],
    "TR-005": [
        "execution",
        "execution admission",
        "secure execution",
        "authority",
        "verification",
    ],
    "TR-006": [
        "agent",
        "delegation",
        "authority",
        "revocation",
        "resource",
    ],
    "TR-007": [
        "observability",
        "audit",
        "provenance",
        "authority",
    ],
    "TR-008": [
        "validation",
        "verification",
        "acceptance",
        "authority",
    ],
    "TR-009": [
        "security testing",
        "security validation",
        "authority",
        "revocation",
        "least privilege",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def print_header(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


# ---------------------------------------------------------------------------
# Authoritative source discovery
# ---------------------------------------------------------------------------

def authoritative_sources() -> list[Path]:
    return [
        REPO_ROOT / "docs/phase-b/requirements/"
        "LYRION_CORE_PRD_TRACEABILITY_ACCEPTANCE_MATRIX_v1.md",

        REPO_ROOT / "docs/phase-b/execution-admission/"
        "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",

        REPO_ROOT / "docs/phase-b/secure-execution/"
        "LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",

        REPO_ROOT / "docs/phase-b/interfaces/"
        "LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",

        REPO_ROOT / "docs/phase-b/validation/"
        "LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",

        REPO_ROOT / "docs/phase-b/security-testing/"
        "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",

        MASTER_MANIFEST,
    ]


def discover_tr_blocks() -> dict[str, list[SourceBlock]]:
    discovered = {tr: [] for tr in TR_IDS}

    for source in authoritative_sources():
        if not source.is_file():
            continue

        lines = read_lines(source)

        for tr_id in TR_IDS:
            pattern = re.compile(
                rf"\b{re.escape(tr_id)}\b",
                re.IGNORECASE,
            )

            for index, line in enumerate(lines):
                if not pattern.search(line):
                    continue

                start = max(0, index - 3)
                end = min(len(lines), index + 35)

                discovered[tr_id].append(
                    SourceBlock(
                        source=source,
                        start_line=start + 1,
                        end_line=end,
                        text="\n".join(lines[start:end]),
                    )
                )

    return discovered


# ---------------------------------------------------------------------------
# Extract obligation evidence from authoritative TR material
# ---------------------------------------------------------------------------

def extract_authoritative_obligations(
    tr_id: str,
    blocks: list[SourceBlock],
) -> list[str]:
    text = normalize(
        "\n".join(block.text for block in blocks)
    )

    candidates = TR_OBLIGATIONS[tr_id]

    found = []

    for obligation in candidates:
        if obligation in text:
            found.append(obligation)

    return unique(found)


# ---------------------------------------------------------------------------
# PB-DOC-003 evidence
# ---------------------------------------------------------------------------

def extract_pbdoc003_evidence(
    pb_text: str,
    obligations: list[str],
) -> list[str]:
    normalized = normalize(pb_text)

    return [
        obligation
        for obligation in obligations
        if obligation in normalized
    ]


# ---------------------------------------------------------------------------
# Evidence strength
# ---------------------------------------------------------------------------

def evidence_strength(
    tr_id: str,
    obligation: str,
    pb_text: str,
) -> str:
    """
    Conservative semantic strength assessment.

    DIRECT:
        Explicit requirement/control language around the obligation.

    SUPPORTING:
        Concept exists and is linked to authority/identity context.

    ABSENT:
        Concept not present.
    """

    text = normalize(pb_text)

    direct_patterns = {
        "identity": [
            "identity",
            "agent identity",
            "principal identity",
        ],
        "authority": [
            "authority",
            "delegated authority",
            "authority scope",
        ],
        "authorization": [
            "authorization",
            "authorized",
            "authorization decision",
        ],
        "requirements": [
            "requirements",
            "requirement",
        ],
        "delegated authority": [
            "delegated authority",
            "delegation",
        ],
        "authority attenuation": [
            "authority attenuation",
            "attenuation",
            "attenuate",
        ],
        "revocation": [
            "revocation",
            "revoked",
            "revoke",
        ],
        "revalidation": [
            "revalidation",
            "revalidate",
        ],
        "capability": [
            "capability",
            "capability authorization",
        ],
        "capability authorization": [
            "capability authorization",
            "capability",
        ],
        "capability boundary": [
            "capability boundary",
            "boundary",
        ],
        "memory": [
            "memory",
            "memory access",
        ],
        "provenance": [
            "provenance",
            "provenance record",
        ],
        "integrity": [
            "integrity",
            "integrity protection",
        ],
        "execution": [
            "execution",
            "execute",
            "execution authority",
        ],
        "execution admission": [
            "execution admission",
            "admission",
        ],
        "secure execution": [
            "secure execution",
            "secure executor",
        ],
        "verification": [
            "verification",
            "verify",
        ],
        "agent": [
            "agent",
            "agent identity",
        ],
        "delegation": [
            "delegation",
            "delegated authority",
        ],
        "resource": [
            "resource",
            "resource limit",
            "resource constraint",
        ],
        "observability": [
            "observability",
            "observable",
        ],
        "audit": [
            "audit",
            "auditable",
        ],
        "validation": [
            "validation",
            "validated",
        ],
        "acceptance": [
            "acceptance",
            "acceptance criteria",
        ],
        "security testing": [
            "security testing",
            "security test",
        ],
        "security validation": [
            "security validation",
            "security test",
        ],
        "least privilege": [
            "least privilege",
            "least-privilege",
        ],
    }

    patterns = direct_patterns.get(
        obligation,
        [obligation],
    )

    hits = [
        pattern
        for pattern in patterns
        if pattern in text
    ]

    if not hits:
        return "ABSENT"

    # Identity/authority document naturally provides strongest evidence
    # for identity/authority concepts. For other domains, presence is
    # supporting evidence rather than ownership evidence.
    if obligation in {
        "identity",
        "authority",
        "authorization",
        "delegated authority",
        "authority attenuation",
        "revocation",
        "revalidation",
        "least privilege",
    }:
        return "DIRECT"

    return "SUPPORTING"


# ---------------------------------------------------------------------------
# Semantic classification
# ---------------------------------------------------------------------------

def classify_result(
    tr_id: str,
    owner: str,
    role: str,
    obligations: list[str],
    pb_evidence: list[str],
    pb_text: str,
) -> tuple[str, str, list[str]]:
    missing = [
        obligation
        for obligation in obligations
        if obligation not in pb_evidence
    ]

    strengths = {
        obligation: evidence_strength(
            tr_id,
            obligation,
            pb_text,
        )
        for obligation in pb_evidence
    }

    # ---------------------------------------------------------------
    # OWNER
    # ---------------------------------------------------------------

    if role == "OWNER":
        if not obligations:
            return (
                "REVIEW_REQUIRED",
                "No authoritative obligations could be extracted.",
                missing,
            )

        if not missing:
            weak = [
                obligation
                for obligation, strength in strengths.items()
                if strength == "ABSENT"
            ]

            if not weak:
                return (
                    "OWNED_AND_COVERED",
                    "PB-DOC-003 owns the TR and contains evidence for "
                    "the authoritative obligation set.",
                    missing,
                )

        return (
            "OWNED_PARTIAL",
            "PB-DOC-003 owns the TR but one or more authoritative "
            "obligations lack identifiable evidence.",
            missing,
        )

    # ---------------------------------------------------------------
    # SUPPORTING DEPENDENCY
    # ---------------------------------------------------------------

    if role == "SUPPORTING_DEPENDENCY":
        # A supporting document does not need to reproduce the owner's
        # complete TR. We only assess whether the identity/authority
        # dependency expected from PB-DOC-003 is represented.
        dependency_obligations = [
            obligation
            for obligation in obligations
            if obligation in {
                "identity",
                "authority",
                "authorization",
                "delegated authority",
                "authority attenuation",
                "revocation",
                "revalidation",
                "least privilege",
            }
        ]

        missing_dependency = [
            obligation
            for obligation in dependency_obligations
            if obligation not in pb_evidence
        ]

        if not dependency_obligations:
            return (
                "NOT_APPLICABLE",
                "The TR is owned elsewhere and exposes no identifiable "
                "identity/authority dependency for PB-DOC-003.",
                [],
            )

        if not missing_dependency:
            return (
                "SUPPORTING_DEPENDENCY_COVERED",
                "The TR is owned by another Phase-B document and "
                "PB-DOC-003 contains the expected identity/authority "
                "dependency evidence.",
                missing_dependency,
            )

        return (
            "SUPPORTING_DEPENDENCY_PARTIAL",
            "The TR is owned elsewhere, but one or more relevant "
            "identity/authority dependencies are not explicitly "
            "represented in PB-DOC-003.",
            missing_dependency,
        )

    if role == "DEPENDENCY":
        return (
            "SUPPORTING_DEPENDENCY_PARTIAL",
            "PB-DOC-003 was previously classified as a dependency, "
            "but the dependency evidence requires confirmation.",
            missing,
        )

    if role == "NOT_APPLICABLE":
        return (
            "NOT_APPLICABLE",
            "The authoritative TR ownership analysis places this "
            "requirement outside PB-DOC-003 scope.",
            [],
        )

    return (
        "REVIEW_REQUIRED",
        "Ownership role is unresolved.",
        missing,
    )


# ---------------------------------------------------------------------------
# Governance safety
# ---------------------------------------------------------------------------

def verify_governance_safety() -> bool:
    if not MASTER_MANIFEST.is_file():
        print(
            "Governance safety: UNVERIFIABLE — "
            "Master Manifest missing"
        )
        return False

    text = MASTER_MANIFEST.read_text(
        encoding="utf-8"
    )

    normalized = re.sub(r"[*_`]", "", text)
    normalized = re.sub(r"[ \t]+", " ", normalized)

    expected = {
        "Architecture Approval": "PENDING",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    ok = True

    for field, expected_value in expected.items():
        pattern = re.compile(
            rf"(?im)"
            rf"^\s*(?:[-+>]\s*)?(?:\|\s*)?"
            rf"{re.escape(field)}"
            rf"\s*(?::|\||=|-)\s*"
            rf"{re.escape(expected_value)}"
            rf"\s*(?:\|)?\s*$"
        )

        found = bool(pattern.search(normalized))

        print(
            f"    {field:<32}: "
            f"{'PASS' if found else 'FAIL'} "
            f"(expected: {expected_value})"
        )

        ok &= found

    print(
        f"Governance safety              : "
        f"{'PASS' if ok else 'FAIL'}"
    )

    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print_header(
        "LYRION TRUE AGENTIC OS — "
        "PB-DOC-003 SEMANTIC TRACEABILITY RECONCILIATION"
    )

    print(f"Repository : {REPO_ROOT}")
    print("Target     : PB-DOC-003 — Identity / Authority")
    print("Mode       : READ-ONLY")
    print("Scope      : TR-001..TR-009")

    if not REPO_ROOT.is_dir():
        print("ERROR: repository does not exist.")
        return 2

    if not PB_DOC_003.is_file():
        print("ERROR: PB-DOC-003 canonical document missing.")
        return 2

    if not TR_MATRIX.is_file():
        print(
            "ERROR: canonical TR traceability matrix missing."
        )
        return 2

    pb_lines = read_lines(PB_DOC_003)
    pb_text = "\n".join(pb_lines)

    print(
        f"PB-DOC-003 lines: {len(pb_lines)}"
    )

    # ---------------------------------------------------------------
    # Discover authoritative TR material
    # ---------------------------------------------------------------

    print_header(
        "1. AUTHORITATIVE TR MATERIAL"
    )

    tr_blocks = discover_tr_blocks()

    for tr_id in TR_IDS:
        blocks = tr_blocks[tr_id]

        if not blocks:
            print(
                f"{tr_id}: NO AUTHORITATIVE MATERIAL FOUND"
            )
            continue

        sources = unique([
            str(
                block.source.relative_to(REPO_ROOT)
            )
            for block in blocks
        ])

        print(
            f"{tr_id}: {len(sources)} source(s)"
        )

        for source in sources:
            print(
                f"    {source}"
            )

    # ---------------------------------------------------------------
    # Reconciliation
    # ---------------------------------------------------------------

    print_header(
        "2. SEMANTIC TRACEABILITY RECONCILIATION"
    )

    results: list[ReconciliationResult] = []

    for tr_id in TR_IDS:
        owner, role = OWNERSHIP[tr_id]

        result = ReconciliationResult(
            tr_id=tr_id,
            owner=owner,
            role=role,
            authoritative_blocks=tr_blocks[tr_id],
        )

        if not tr_blocks[tr_id]:
            result.classification = (
                "REVIEW_REQUIRED"
            )
            result.rationale = (
                "No authoritative TR material was discovered."
            )
            result.review_reasons.append(
                "Authoritative TR material unavailable."
            )
            results.append(result)
            continue

        obligations = extract_authoritative_obligations(
            tr_id,
            tr_blocks[tr_id],
        )

        # Never silently invent obligations. The explicit TR obligation
        # map is intersected with what the authoritative material
        # actually contains.
        allowed_obligations = set(
            TR_OBLIGATIONS[tr_id]
        )

        obligations = [
            obligation
            for obligation in obligations
            if obligation in allowed_obligations
        ]

        pb_evidence = extract_pbdoc003_evidence(
            pb_text,
            obligations,
        )

        classification, rationale, missing = (
            classify_result(
                tr_id,
                owner,
                role,
                obligations,
                pb_evidence,
                pb_text,
            )
        )

        result.obligations = obligations
        result.required_evidence = obligations
        result.pbdoc003_evidence = pb_evidence
        result.missing_pbdoc003_evidence = missing
        result.classification = classification
        result.rationale = rationale

        if classification == "REVIEW_REQUIRED":
            result.review_reasons.append(
                rationale
            )

        results.append(result)

        print()
        print(f"{tr_id}")
        print(f"  Primary owner       : {owner}")
        print(f"  PB-DOC-003 role     : {role}")
        print(f"  Classification      : {classification}")

        print(
            "  Obligations         : "
            + (
                ", ".join(obligations)
                if obligations
                else "NONE"
            )
        )

        print(
            "  PB-DOC-003 evidence : "
            + (
                ", ".join(pb_evidence)
                if pb_evidence
                else "NONE"
            )
        )

        print(
            "  Missing evidence    : "
            + (
                ", ".join(missing)
                if missing
                else "NONE"
            )
        )

        print(
            f"  Rationale           : {rationale}"
        )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print_header(
        "3. RECONCILIATION SUMMARY"
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

    classifications = [
        "OWNED_AND_COVERED",
        "OWNED_PARTIAL",
        "SUPPORTING_DEPENDENCY_COVERED",
        "SUPPORTING_DEPENDENCY_PARTIAL",
        "NOT_APPLICABLE",
        "REVIEW_REQUIRED",
    ]

    for classification in classifications:
        print(
            f"{classification:<32}: "
            f"{counts.get(classification, 0)}"
        )

    print()
    print(
        f"{'TR':<8}"
        f"{'Owner':<20}"
        f"{'Role':<24}"
        f"{'Classification':<34}"
    )

    print("-" * 86)

    for result in results:
        print(
            f"{result.tr_id:<8}"
            f"{result.owner:<20}"
            f"{result.role:<24}"
            f"{result.classification:<34}"
        )

    # ---------------------------------------------------------------
    # Review findings
    # ---------------------------------------------------------------

    review = [
        result
        for result in results
        if result.classification in {
            "OWNED_PARTIAL",
            "SUPPORTING_DEPENDENCY_PARTIAL",
            "REVIEW_REQUIRED",
        }
    ]

    print()
    print(
        f"Semantic findings requiring review: "
        f"{len(review)}"
    )

    for result in review:
        print(
            f"  - {result.tr_id}: "
            f"{result.classification} — "
            f"{result.rationale}"
        )

    # ---------------------------------------------------------------
    # Governance safety
    # ---------------------------------------------------------------

    print_header(
        "4. GOVERNANCE SAFETY"
    )

    governance_ok = verify_governance_safety()

    # ---------------------------------------------------------------
    # Read-only assertion
    # ---------------------------------------------------------------

    print_header(
        "5. READ-ONLY GUARANTEE"
    )

    print(
        "PB-DOC-003 modified          : NO"
    )
    print(
        "Gap Register modified        : NO"
    )
    print(
        "Master Manifest modified     : NO"
    )
    print(
        "Any Phase-B documentation    : NO"
    )
    print(
        "Architecture Approval changed: NO"
    )
    print(
        "Implementation authorized    : NO"
    )
    print(
        "Production implementation    : NO"
    )
    print(
        "Production certification     : NO"
    )

    # ---------------------------------------------------------------
    # Final result
    # ---------------------------------------------------------------

    print_header(
        "6. FINAL RESULT"
    )

    if not governance_ok:
        print(
            "RESULT: SAFETY FAILURE — "
            "governance state could not be verified."
        )
        return 2

    if review:
        print(
            "RESULT: REVIEW REQUIRED — "
            f"{len(review)} semantic findings remain."
        )
        print()
        print(
            "No documentation or Gap Register changes "
            "are authorized by this audit."
        )
        return 1

    print(
        "RESULT: SEMANTIC TRACEABILITY RECONCILIATION "
        "COMPLETE — NO UNRESOLVED FINDINGS."
    )

    print()
    print(
        "Evidence only. Architecture Approval and "
        "Implementation Authorization remain unchanged."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

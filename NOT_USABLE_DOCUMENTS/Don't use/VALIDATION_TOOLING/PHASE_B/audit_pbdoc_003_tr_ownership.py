#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B TR Ownership / Dependency Audit
Target: PB-DOC-003 — Identity & Authority

Purpose
-------
Determine whether PB-DOC-003:
  - owns a TR requirement,
  - provides supporting evidence for it,
  - is a dependency of the TR,
  - is not applicable,
  - or requires architectural review.

This is a READ-ONLY architecture analysis tool.

It does NOT:
  - modify any documentation
  - modify the Gap Register
  - modify manifests
  - close findings
  - approve architecture
  - authorize implementation
  - claim production certification

Important
---------
The tool deliberately does NOT infer ownership from keyword frequency alone.
Ownership is evaluated from:
  1. authoritative TR definitions,
  2. canonical document domains,
  3. explicit ownership/domain language,
  4. PB-DOC-003 scope,
  5. semantic dependency evidence.

Exit codes:
  0 = no unresolved ownership findings
  1 = review required
  2 = runtime/configuration failure
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


@dataclass(frozen=True)
class TRDefinition:
    tr_id: str
    source: Path
    start_line: int
    end_line: int
    text: str


@dataclass
class OwnershipResult:
    tr_id: str
    definitions: list[TRDefinition] = field(default_factory=list)

    primary_owner: str = "UNKNOWN"
    pbdoc003_role: str = "REVIEW_REQUIRED"

    ownership_evidence: list[str] = field(default_factory=list)
    dependency_evidence: list[str] = field(default_factory=list)
    pbdoc003_evidence: list[str] = field(default_factory=list)

    rationale: str = ""
    review_reasons: list[str] = field(default_factory=list)


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def print_header(title: str) -> None:
    print()
    print("=" * 92)
    print(title)
    print("=" * 92)


# ---------------------------------------------------------------------------
# Canonical Phase-B document ownership domains
# ---------------------------------------------------------------------------

DOCUMENT_DOMAINS: dict[str, list[str]] = {
    "PB-DOC-001": [
        "requirements",
        "prd",
        "functional requirements",
        "non-functional requirements",
        "requirements baseline",
    ],
    "PB-DOC-002": [
        "agentic runtime",
        "runtime",
        "agent lifecycle",
        "task orchestration",
        "agent scheduling",
    ],
    "PB-DOC-003": [
        "identity",
        "authority",
        "delegated authority",
        "authority attenuation",
        "revocation",
        "revalidation",
        "authentication",
        "attribution",
    ],
    "PB-DOC-004": [
        "capability",
        "capability model",
        "capability authorization",
        "capability boundary",
    ],
    "PB-DOC-005": [
        "agent harness",
        "agent registration",
        "agent lifecycle",
        "agent tool invocation",
    ],
    "PB-DOC-006": [
        "host harness",
        "host integration",
        "host boundary",
        "host operation",
        "host mediation",
    ],
    "PB-DOC-007": [
        "universal computer",
        "computer abstraction",
        "host independence",
        "application interaction",
    ],
    "PB-DOC-008": [
        "application harness",
        "application integration",
        "application interaction",
    ],
    "PB-DOC-009": [
        "execution admission",
        "admission control",
        "execution authorization",
        "execution decision",
    ],
    "PB-DOC-010": [
        "aegis",
        "governance",
        "policy enforcement",
        "agent governance",
    ],
    "PB-DOC-011": [
        "secure execution",
        "sandbox",
        "secure executor",
        "execution isolation",
    ],
    "PB-DOC-012": [
        "interface",
        "contract",
        "interface contract",
        "protocol",
        "message contract",
    ],
    "PB-DOC-013": [
        "data architecture",
        "data model",
        "data integrity",
        "data lifecycle",
    ],
    "PB-DOC-014": [
        "memory",
        "provenance",
        "memory provenance",
        "memory integrity",
    ],
    "PB-DOC-015": [
        "observability",
        "telemetry",
        "audit",
        "monitoring",
    ],
    "PB-DOC-016": [
        "validation",
        "verification",
        "acceptance",
        "validation strategy",
    ],
    "PB-DOC-017": [
        "security testing",
        "security test",
        "threat testing",
        "security validation",
    ],
    "PB-DOC-018": [
        "operations",
        "operations management",
        "operational controls",
    ],
    "PB-DOC-019": [
        "recovery",
        "resilience",
        "fault recovery",
        "continuity",
    ],
    "PB-DOC-020": [
        "master manifest",
        "phase-b governance",
        "architecture approval",
        "implementation authorization",
    ],
}


# ---------------------------------------------------------------------------
# TR-specific primary ownership domains
# ---------------------------------------------------------------------------

TR_PRIMARY_OWNER_HINTS: dict[str, list[str]] = {
    "TR-001": [
        "requirements traceability",
        "requirements",
        "identity",
        "authority",
        "authorization",
    ],
    "TR-002": [
        "agent identity",
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
        "execution admission",
    ],
    "TR-004": [
        "memory",
        "data integrity",
        "memory integrity",
        "provenance",
    ],
    "TR-005": [
        "secure execution",
        "execution",
        "execution admission",
        "sandbox",
        "verification",
    ],
    "TR-006": [
        "agent swarm",
        "swarm governance",
        "agent-to-agent",
        "delegation",
        "resource",
        "cancellation",
    ],
    "TR-007": [
        "observability",
        "telemetry",
        "audit",
        "monitoring",
    ],
    "TR-008": [
        "validation",
        "verification",
        "acceptance",
    ],
    "TR-009": [
        "security testing",
        "security validation",
        "threat testing",
    ],
}


# ---------------------------------------------------------------------------
# TR definition discovery
# ---------------------------------------------------------------------------

def discover_tr_definitions() -> dict[str, list[TRDefinition]]:
    result = {tr: [] for tr in TR_IDS}

    candidate_sources = [
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

    for source in candidate_sources:
        if not source.is_file():
            continue

        lines = read_lines(source)

        for tr_id in TR_IDS:
            pattern = re.compile(
                rf"\b{re.escape(tr_id)}\b",
                re.IGNORECASE,
            )

            for idx, line in enumerate(lines):
                if not pattern.search(line):
                    continue

                start = max(0, idx - 2)
                end = min(len(lines), idx + 30)

                result[tr_id].append(
                    TRDefinition(
                        tr_id=tr_id,
                        source=source,
                        start_line=start + 1,
                        end_line=end,
                        text="\n".join(lines[start:end]),
                    )
                )

    return result


# ---------------------------------------------------------------------------
# Determine authoritative TR concept set
# ---------------------------------------------------------------------------

def extract_tr_concepts(
    definitions: list[TRDefinition],
) -> list[str]:
    text = normalize(
        "\n".join(definition.text for definition in definitions)
    )

    candidates = [
        "requirements traceability",
        "requirements",
        "identity",
        "authority",
        "authorization",
        "delegated authority",
        "authority attenuation",
        "revocation",
        "revalidation",
        "capability",
        "capability authorization",
        "capability boundary",
        "execution admission",
        "secure execution",
        "execution",
        "sandbox",
        "memory",
        "data integrity",
        "memory integrity",
        "provenance",
        "agent swarm",
        "swarm governance",
        "agent-to-agent",
        "resource",
        "cancellation",
        "observability",
        "telemetry",
        "audit",
        "validation",
        "verification",
        "acceptance",
        "security testing",
        "security validation",
        "threat testing",
        "least privilege",
        "fail closed",
    ]

    return [
        concept
        for concept in candidates
        if concept in text
    ]


# ---------------------------------------------------------------------------
# PB-DOC-003 evidence
# ---------------------------------------------------------------------------

def find_pbdoc003_evidence(
    pb_lines: list[str],
    concepts: list[str],
) -> list[str]:
    text = normalize("\n".join(pb_lines))

    return [
        concept
        for concept in concepts
        if concept in text
    ]


# ---------------------------------------------------------------------------
# Primary owner determination
# ---------------------------------------------------------------------------

def determine_primary_owner(
    tr_id: str,
    definitions: list[TRDefinition],
) -> tuple[str, list[str]]:
    tr_text = normalize(
        "\n".join(definition.text for definition in definitions)
    )

    scores: dict[str, int] = {}

    for doc_id, domains in DOCUMENT_DOMAINS.items():
        score = 0

        for domain in domains:
            if domain in tr_text:
                score += 1

        if score:
            scores[doc_id] = score

    # Explicit TR-specific ownership hints are stronger than generic
    # vocabulary.
    hints = TR_PRIMARY_OWNER_HINTS[tr_id]

    for doc_id, domains in DOCUMENT_DOMAINS.items():
        score = scores.get(doc_id, 0)

        for hint in hints:
            if hint in domains:
                score += 3

        if score:
            scores[doc_id] = score

    if not scores:
        return "UNKNOWN", []

    highest = max(scores.values())
    owners = sorted(
        doc_id
        for doc_id, score in scores.items()
        if score == highest
    )

    if len(owners) != 1:
        return (
            "MULTIPLE_CANDIDATES",
            [
                f"{doc_id}={scores[doc_id]}"
                for doc_id in owners
            ],
        )

    owner = owners[0]

    evidence = [
        f"{owner} domain score={scores[owner]}"
    ]

    return owner, evidence


# ---------------------------------------------------------------------------
# Role classification
# ---------------------------------------------------------------------------

def classify_pbdoc003_role(
    tr_id: str,
    primary_owner: str,
    tr_concepts: list[str],
    pb_evidence: list[str],
    definitions: list[TRDefinition],
) -> tuple[str, str, list[str]]:
    pb_identity_authority = {
        "identity",
        "authority",
        "authorization",
        "delegated authority",
        "authority attenuation",
        "revocation",
        "revalidation",
        "least privilege",
    }

    tr_text = normalize(
        "\n".join(definition.text for definition in definitions)
    )

    identity_hits = [
        concept
        for concept in pb_identity_authority
        if concept in tr_text and concept in pb_evidence
    ]

    # PB-DOC-003 owns the identity/authority TR domain.
    if primary_owner == "PB-DOC-003":
        if len(identity_hits) >= 3:
            return (
                "OWNER",
                "TR definition and PB-DOC-003 scope align around identity/"
                "authority responsibilities.",
                identity_hits,
            )

        return (
            "REVIEW_REQUIRED",
            "PB-DOC-003 appears to be the primary domain owner, but "
            "substantive ownership evidence is insufficient.",
            identity_hits,
        )

    # If another document owns the TR but PB-DOC-003 supplies identity/
    # authority prerequisites, it is a supporting/dependency document.
    if primary_owner not in {"UNKNOWN", "MULTIPLE_CANDIDATES"}:
        if len(identity_hits) >= 3:
            return (
                "SUPPORTING_DEPENDENCY",
                f"{primary_owner} appears to own the TR, while PB-DOC-003 "
                "provides identity/authority controls required by that domain.",
                identity_hits,
            )

        if len(identity_hits) >= 1:
            return (
                "DEPENDENCY",
                f"{primary_owner} appears to own the TR, while PB-DOC-003 "
                "contains limited identity/authority dependency evidence.",
                identity_hits,
            )

        return (
            "NOT_APPLICABLE",
            f"{primary_owner} appears to own the TR and PB-DOC-003 does "
            "not provide substantive identity/authority dependency evidence.",
            [],
        )

    if primary_owner == "MULTIPLE_CANDIDATES":
        return (
            "REVIEW_REQUIRED",
            "Multiple candidate owning domains were detected; ownership "
            "cannot be safely assigned automatically.",
            identity_hits,
        )

    return (
        "REVIEW_REQUIRED",
        "No reliable primary owner could be established from the "
        "authoritative TR definitions.",
        identity_hits,
    )


# ---------------------------------------------------------------------------
# Governance safety
# ---------------------------------------------------------------------------

def verify_governance_safety() -> bool:
    if not MASTER_MANIFEST.is_file():
        print("Governance safety: UNVERIFIABLE — Master Manifest missing")
        return False

    text = MASTER_MANIFEST.read_text(encoding="utf-8")

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
        "PB-DOC-003 TR OWNERSHIP / DEPENDENCY AUDIT"
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
        print("ERROR: canonical TR traceability matrix missing.")
        return 2

    pb_lines = read_lines(PB_DOC_003)

    print(f"PB-DOC-003 lines: {len(pb_lines)}")

    # ---------------------------------------------------------------
    # Discover authoritative definitions
    # ---------------------------------------------------------------

    print_header("1. AUTHORITATIVE TR SOURCES")

    definitions = discover_tr_definitions()

    for tr_id in TR_IDS:
        defs = definitions[tr_id]

        if not defs:
            print(f"{tr_id}: NO AUTHORITATIVE OCCURRENCE FOUND")
            continue

        sources = unique([
            str(definition.source.relative_to(REPO_ROOT))
            for definition in defs
        ])

        print(f"{tr_id}: {len(sources)} source(s)")
        for source in sources:
            print(f"    {source}")

    # ---------------------------------------------------------------
    # Evaluate ownership
    # ---------------------------------------------------------------

    print_header("2. TR OWNERSHIP / DEPENDENCY ANALYSIS")

    results: list[OwnershipResult] = []

    for tr_id in TR_IDS:
        defs = definitions[tr_id]

        result = OwnershipResult(
            tr_id=tr_id,
            definitions=defs,
        )

        if not defs:
            result.primary_owner = "UNKNOWN"
            result.pbdoc003_role = "REVIEW_REQUIRED"
            result.rationale = (
                "No authoritative TR definition was discovered."
            )
            result.review_reasons.append(
                "Authoritative TR definition missing."
            )
            results.append(result)
            continue

        concepts = extract_tr_concepts(defs)

        primary_owner, owner_evidence = determine_primary_owner(
            tr_id,
            defs,
        )

        pb_evidence = find_pbdoc003_evidence(
            pb_lines,
            concepts,
        )

        role, rationale, role_evidence = classify_pbdoc003_role(
            tr_id,
            primary_owner,
            concepts,
            pb_evidence,
            defs,
        )

        result.primary_owner = primary_owner
        result.pbdoc003_role = role
        result.ownership_evidence = owner_evidence
        result.dependency_evidence = role_evidence
        result.pbdoc003_evidence = pb_evidence
        result.rationale = rationale

        if role == "REVIEW_REQUIRED":
            result.review_reasons.append(rationale)

        results.append(result)

        print()
        print(f"{tr_id}")
        print(f"  Primary owner       : {primary_owner}")
        print(f"  PB-DOC-003 role     : {role}")
        print(
            "  TR concepts         : "
            + (
                ", ".join(concepts)
                if concepts
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
            "  Ownership evidence  : "
            + (
                ", ".join(owner_evidence)
                if owner_evidence
                else "NONE"
            )
        )
        print(
            "  Dependency evidence : "
            + (
                ", ".join(role_evidence)
                if role_evidence
                else "NONE"
            )
        )
        print(f"  Rationale           : {rationale}")

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print_header("3. OWNERSHIP SUMMARY")

    counts: dict[str, int] = {}

    for result in results:
        counts[result.pbdoc003_role] = (
            counts.get(result.pbdoc003_role, 0) + 1
        )

    for role in (
        "OWNER",
        "SUPPORTING_DEPENDENCY",
        "DEPENDENCY",
        "NOT_APPLICABLE",
        "REVIEW_REQUIRED",
    ):
        print(
            f"{role:<24}: {counts.get(role, 0)}"
        )

    print()
    print(
        f"{'TR':<8}"
        f"{'Primary Owner':<20}"
        f"{'PB-DOC-003 Role':<24}"
    )
    print("-" * 52)

    for result in results:
        print(
            f"{result.tr_id:<8}"
            f"{result.primary_owner:<20}"
            f"{result.pbdoc003_role:<24}"
        )

    # ---------------------------------------------------------------
    # Review findings
    # ---------------------------------------------------------------

    review = [
        result
        for result in results
        if result.pbdoc003_role == "REVIEW_REQUIRED"
    ]

    print()
    print(f"Ownership findings requiring review: {len(review)}")

    for result in review:
        print(
            f"  - {result.tr_id}: "
            f"{result.rationale}"
        )

    # ---------------------------------------------------------------
    # Governance
    # ---------------------------------------------------------------

    print_header("4. GOVERNANCE SAFETY")

    governance_ok = verify_governance_safety()

    # ---------------------------------------------------------------
    # Read-only assertion
    # ---------------------------------------------------------------

    print_header("5. READ-ONLY GUARANTEE")

    print("PB-DOC-003 modified          : NO")
    print("Gap Register modified        : NO")
    print("Master Manifest modified     : NO")
    print("Any Phase-B documentation    : NO")
    print("Architecture Approval changed: NO")
    print("Implementation authorized    : NO")
    print("Production implementation    : NO")
    print("Production certification     : NO")

    # ---------------------------------------------------------------
    # Final result
    # ---------------------------------------------------------------

    print_header("6. FINAL RESULT")

    if not governance_ok:
        print(
            "RESULT: SAFETY FAILURE — "
            "governance state could not be verified."
        )
        return 2

    if review:
        print(
            "RESULT: REVIEW REQUIRED — "
            f"{len(review)} ownership findings remain unresolved."
        )
        print()
        print(
            "No documentation or Gap Register changes are authorized "
            "by this audit."
        )
        return 1

    print(
        "RESULT: OWNERSHIP AUDIT COMPLETE — "
        "NO UNRESOLVED OWNERSHIP FINDINGS."
    )
    print()
    print(
        "This is evidence only. Architecture Approval and "
        "Implementation Authorization remain unchanged."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

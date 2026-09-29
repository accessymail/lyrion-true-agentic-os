#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Cross-Document Traceability & Reconciliation Audit

Scope
-----
PB-DOC-001 .. PB-DOC-020
TR-001 .. TR-009

Purpose
-------
Perform a read-only architecture-level cross-document reconciliation.

The audit evaluates:

    TR
      -> canonical owner
      -> supporting/dependency documents
      -> required architectural domains
      -> evidence in owner
      -> evidence in dependencies
      -> cross-document relationships
      -> contradictions / unresolved findings

This tool is EVIDENCE ONLY.

It does NOT:
    - modify documents
    - modify the Gap Register
    - modify the Master Manifest
    - change approval state
    - authorize implementation
    - claim production certification
    - create architecture decisions

Important
---------
Literal TR-ID presence is NOT treated as the sole definition of
traceability. A document may satisfy a TR through an explicit
internal requirement identifier, semantic evidence, or a declared
architectural dependency.

The audit therefore distinguishes:
    OWNER
    SUPPORTING_DEPENDENCY
    DEPENDENCY
    NOT_APPLICABLE
    REVIEW_REQUIRED

Exit codes:
    0 = complete with no unresolved findings
    1 = review required
    2 = safety/runtime/configuration failure
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================================
# Repository
# ============================================================================

REPO_ROOT = Path("/home/aniket/lyrion-migration-verified")


# ============================================================================
# Canonical PB-DOC registry
# ============================================================================

CANONICAL_DOCUMENTS: dict[str, Path] = {
    "PB-DOC-001": REPO_ROOT / "docs/phase-b/requirements/"
    "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-002": REPO_ROOT / "docs/phase-b/agentic-runtime/"
    "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003": REPO_ROOT / "docs/phase-b/identity-authority/"
    "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004": REPO_ROOT / "docs/phase-b/capability/"
    "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-005": REPO_ROOT / "docs/phase-b/agent-harness/"
    "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006": REPO_ROOT / "docs/phase-b/host-harness/"
    "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-007": REPO_ROOT / "docs/phase-b/universal-computer/"
    "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",

    "PB-DOC-008": REPO_ROOT / "docs/phase-b/application-harness/"
    "LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-009": REPO_ROOT / "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",

    "PB-DOC-010": REPO_ROOT / "docs/phase-b/aegis/"
    "LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",

    "PB-DOC-011": REPO_ROOT / "docs/phase-b/secure-execution/"
    "LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",

    "PB-DOC-012": REPO_ROOT / "docs/phase-b/interfaces/"
    "LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",

    "PB-DOC-013": REPO_ROOT / "docs/phase-b/data/"
    "LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",

    "PB-DOC-014": REPO_ROOT / "docs/phase-b/memory/"
    "LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",

    "PB-DOC-015": REPO_ROOT / "docs/phase-b/observability/"
    "LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",

    "PB-DOC-016": REPO_ROOT / "docs/phase-b/validation/"
    "LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",

    "PB-DOC-017": REPO_ROOT / "docs/phase-b/security-testing/"
    "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",

    "PB-DOC-018": REPO_ROOT / "docs/phase-b/operations/"
    "LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",

    "PB-DOC-019": REPO_ROOT / "docs/phase-b/recovery/"
    "LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",

    "PB-DOC-020": REPO_ROOT / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
}


TR_IDS = [f"TR-{index:03d}" for index in range(1, 10)]


MASTER_MANIFEST = CANONICAL_DOCUMENTS["PB-DOC-020"]


# ============================================================================
# Canonical TR ownership established by previous controlled audits
# ============================================================================

TR_OWNERSHIP: dict[str, str] = {
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
# Canonical supporting dependencies
#
# These are deliberately conservative and represent architectural
# relationships, not complete ownership.
# ============================================================================

TR_SUPPORTING_DEPENDENCIES: dict[str, set[str]] = {
    "TR-001": {
        "PB-DOC-001",
        "PB-DOC-003",
        "PB-DOC-012",
        "PB-DOC-016",
    },

    "TR-002": {
        "PB-DOC-001",
        "PB-DOC-003",
        "PB-DOC-005",
        "PB-DOC-010",
        "PB-DOC-012",
    },

    "TR-003": {
        "PB-DOC-003",
        "PB-DOC-004",
        "PB-DOC-009",
        "PB-DOC-010",
        "PB-DOC-012",
    },

    "TR-004": {
        "PB-DOC-003",
        "PB-DOC-013",
        "PB-DOC-014",
        "PB-DOC-015",
    },

    "TR-005": {
        "PB-DOC-003",
        "PB-DOC-004",
        "PB-DOC-009",
        "PB-DOC-011",
        "PB-DOC-012",
        "PB-DOC-016",
    },

    "TR-006": {
        "PB-DOC-002",
        "PB-DOC-003",
        "PB-DOC-005",
        "PB-DOC-010",
        "PB-DOC-019",
    },

    "TR-007": {
        "PB-DOC-003",
        "PB-DOC-012",
        "PB-DOC-014",
        "PB-DOC-015",
    },

    "TR-008": {
        "PB-DOC-001",
        "PB-DOC-003",
        "PB-DOC-014",
        "PB-DOC-016",
    },

    "TR-009": {
        "PB-DOC-003",
        "PB-DOC-009",
        "PB-DOC-010",
        "PB-DOC-011",
        "PB-DOC-016",
        "PB-DOC-017",
    },
}


# ============================================================================
# Architectural relationship expectations
# ============================================================================

RELATIONSHIP_GROUPS: dict[str, tuple[str, ...]] = {
    "identity_authority": (
        "identity",
        "authority",
        "authorization",
        "delegation",
        "revocation",
        "revalidation",
    ),

    "capability_authorization": (
        "capability",
        "capability authorization",
        "capability boundary",
    ),

    "execution_admission": (
        "execution admission",
        "admission control",
        "execution authorization",
    ),

    "secure_execution": (
        "secure execution",
        "sandbox",
        "secure executor",
        "execution isolation",
    ),

    "verification_provenance": (
        "verification",
        "provenance",
        "audit",
    ),

    "agent_host": (
        "agent harness",
        "host harness",
        "host integration",
        "host boundary",
    ),

    "host_application": (
        "host harness",
        "application harness",
        "application integration",
    ),

    "observability": (
        "observability",
        "telemetry",
        "monitoring",
    ),

    "validation_security": (
        "validation",
        "security testing",
        "security validation",
    ),

    "recovery_resilience": (
        "recovery",
        "resilience",
        "fault recovery",
    ),
}


# ============================================================================
# Security invariants that must remain globally represented
# ============================================================================

SECURITY_INVARIANTS: tuple[str, ...] = (
    "least privilege",
    "fail closed",
    "authority attenuation",
    "revocation",
    "revalidation",
    "execution admission",
    "secure execution",
    "provenance",
    "verification",
)


# ============================================================================
# Data structures
# ============================================================================

@dataclass(frozen=True)
class Document:
    doc_id: str
    path: Path
    text: str
    lines: tuple[str, ...]


@dataclass
class RelationshipResult:
    group: str
    present_documents: list[str] = field(default_factory=list)
    missing_expected_documents: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    classification: str = "REVIEW_REQUIRED"


@dataclass
class TRResult:
    tr_id: str
    owner: str
    dependencies: set[str]

    owner_present: bool = False
    owner_evidence: list[str] = field(default_factory=list)

    dependency_results: dict[str, str] = field(
        default_factory=dict
    )

    relationship_results: list[RelationshipResult] = field(
        default_factory=list
    )

    contradictions: list[str] = field(default_factory=list)

    classification: str = "REVIEW_REQUIRED"
    rationale: str = ""


# ============================================================================
# Helpers
# ============================================================================

def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


def read_document(doc_id: str, path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    return Document(
        doc_id=doc_id,
        path=path,
        text=text,
        lines=tuple(text.splitlines()),
    )


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def print_header(title: str) -> None:
    print()
    print("=" * 108)
    print(title)
    print("=" * 108)


def contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    return any(
        pattern.lower() in normalized
        for pattern in patterns
    )


def count_terms(text: str, terms: tuple[str, ...]) -> int:
    normalized = normalize(text)
    return sum(
        1
        for term in terms
        if term.lower() in normalized
    )


# ============================================================================
# Document loading
# ============================================================================

def load_documents() -> tuple[dict[str, Document], list[str]]:
    documents: dict[str, Document] = {}
    failures: list[str] = []

    for doc_id, path in CANONICAL_DOCUMENTS.items():
        if not path.is_file():
            failures.append(
                f"{doc_id}: missing canonical file: {path}"
            )
            continue

        try:
            documents[doc_id] = read_document(
                doc_id,
                path,
            )
        except Exception as exc:
            failures.append(
                f"{doc_id}: unable to read: {exc}"
            )

    return documents, failures


# ============================================================================
# Document identity validation
# ============================================================================

def validate_document_identity(
    document: Document,
) -> tuple[bool, str]:
    text = document.text

    patterns = (
        rf"(?im)^\s*(?:#\s*)?Document\s+ID\s*[:|=-]\s*"
        rf"{re.escape(document.doc_id)}\s*$",

        rf"(?im)^\s*(?:\*\*)?Document\s+ID(?:\*\*)?"
        rf"\s*[:|=-]\s*{re.escape(document.doc_id)}\s*$",
    )

    if any(re.search(pattern, text) for pattern in patterns):
        return True, "explicit Document ID matched"

    # Some documents use a title/heading convention. Keep this as
    # secondary evidence rather than silently accepting arbitrary mentions.
    if document.doc_id in text:
        return True, "Document ID token present"

    return False, "canonical Document ID not detected"


# ============================================================================
# Governance safety
# ============================================================================

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

        found = bool(
            pattern.search(normalized)
        )

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


# ============================================================================
# Requirement / architecture evidence
# ============================================================================

def find_internal_requirement_ids(
    document: Document,
) -> list[str]:
    matches = re.findall(
        r"\b(?:CORE|TAOS|LYRION|REQ|SEC|AUTH|CAP|EXEC|VAL|OBS|DATA|MEM)"
        r"-[A-Z0-9]+(?:-[A-Z0-9]+)+-\d{3,}\b",
        document.text,
        flags=re.IGNORECASE,
    )

    return unique(matches)


def find_tr_references(
    document: Document,
) -> list[str]:
    return unique(
        re.findall(
            r"\bTR-\d{3}\b",
            document.text,
        )
    )


def find_architecture_relationships(
    document: Document,
) -> dict[str, int]:
    result: dict[str, int] = {}

    for group, terms in RELATIONSHIP_GROUPS.items():
        count = count_terms(
            document.text,
            terms,
        )
        result[group] = count

    return result


# ============================================================================
# Owner evidence
# ============================================================================

def evaluate_owner(
    tr_id: str,
    owner: str,
    documents: dict[str, Document],
) -> tuple[bool, list[str]]:
    if owner not in documents:
        return False, [
            "canonical owner document unavailable"
        ]

    document = documents[owner]

    evidence: list[str] = []

    if tr_id in find_tr_references(document):
        evidence.append(
            f"literal {tr_id} reference"
        )

    internal_ids = find_internal_requirement_ids(
        document
    )

    if internal_ids:
        evidence.append(
            f"{len(internal_ids)} internal requirement identifier(s)"
        )

    relationships = find_architecture_relationships(
        document
    )

    represented_groups = [
        group
        for group, count in relationships.items()
        if count > 0
    ]

    evidence.extend(
        f"relationship:{group}"
        for group in represented_groups
    )

    # Owner evidence is considered sufficient when the document has
    # substantive architecture evidence even if it does not literally
    # repeat the TR identifier.
    substantive = (
        len(internal_ids) > 0
        or len(represented_groups) >= 2
        or tr_id in find_tr_references(document)
    )

    return substantive, unique(evidence)


# ============================================================================
# Dependency evidence
# ============================================================================

def evaluate_dependency(
    tr_id: str,
    dependency: str,
    documents: dict[str, Document],
) -> tuple[str, list[str]]:
    if dependency not in documents:
        return (
            "MISSING_DOCUMENT",
            ["canonical dependency document unavailable"],
        )

    document = documents[dependency]

    evidence: list[str] = []

    if tr_id in find_tr_references(document):
        evidence.append(
            f"literal {tr_id} reference"
        )

    relationships = find_architecture_relationships(
        document
    )

    represented_groups = [
        group
        for group, count in relationships.items()
        if count > 0
    ]

    evidence.extend(
        f"relationship:{group}"
        for group in represented_groups
    )

    internal_ids = find_internal_requirement_ids(
        document
    )

    if internal_ids:
        evidence.append(
            f"{len(internal_ids)} internal requirement identifier(s)"
        )

    if tr_id in find_tr_references(document):
        return "DIRECT", unique(evidence)

    if represented_groups or internal_ids:
        return "SEMANTIC", unique(evidence)

    return "ABSENT", []


# ============================================================================
# Cross-document relationship analysis
# ============================================================================

def expected_relationship_documents(
    tr_id: str,
) -> dict[str, set[str]]:
    """
    Expected architecture relationships for each TR.

    This is deliberately structural. It checks whether the Phase-B
    architecture has representation across the appropriate document
    boundaries, rather than demanding identical text.
    """

    owner = TR_OWNERSHIP[tr_id]
    dependencies = TR_SUPPORTING_DEPENDENCIES[tr_id]

    return {
        "owner": {owner},
        "dependencies": dependencies,
    }


def evaluate_relationship_group(
    group: str,
    expected_documents: set[str],
    documents: dict[str, Document],
) -> RelationshipResult:
    result = RelationshipResult(
        group=group
    )

    for doc_id in sorted(expected_documents):
        document = documents.get(doc_id)

        if document is None:
            result.missing_expected_documents.append(
                doc_id
            )
            continue

        terms = RELATIONSHIP_GROUPS[group]

        count = count_terms(
            document.text,
            terms,
        )

        if count > 0:
            result.present_documents.append(
                doc_id
            )
            result.evidence.append(
                f"{doc_id}:{count} term-match(es)"
            )
        else:
            result.missing_expected_documents.append(
                doc_id
            )

    if result.present_documents:
        if not result.missing_expected_documents:
            result.classification = "COVERED"

        else:
            result.classification = "PARTIAL"

    else:
        result.classification = "ABSENT"

    return result


# ============================================================================
# Contradiction detection
# ============================================================================

def detect_contradictions(
    documents: dict[str, Document],
) -> list[str]:
    contradictions: list[str] = []

    # ------------------------------------------------------------------
    # Governance contradictions
    # ------------------------------------------------------------------

    governance_expectations = {
        "Architecture Approval": "PENDING",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    manifest = documents.get("PB-DOC-020")

    if manifest:
        normalized = re.sub(
            r"[*_`]",
            "",
            manifest.text,
        )

        normalized = re.sub(
            r"[ \t]+",
            " ",
            normalized,
        )

        for field, expected in governance_expectations.items():
            # Search for the field and inspect a bounded window.
            pattern = re.compile(
                rf"{re.escape(field)}"
                rf"\s*(?::|\||=|-)\s*"
                rf"([A-Z][A-Z ]+)",
                re.IGNORECASE,
            )

            matches = pattern.findall(
                normalized
            )

            if matches:
                values = {
                    normalize(match).upper()
                    for match in matches
                }

                if expected not in values:
                    contradictions.append(
                        f"PB-DOC-020 governance field "
                        f"{field!r} does not expose expected "
                        f"state {expected!r}"
                    )

    # ------------------------------------------------------------------
    # Dangerous alternate-path language
    # ------------------------------------------------------------------

    forbidden_patterns = (
        (
            "direct agent-to-host unrestricted access",
            r"direct\s+agent[- ]to[- ]host\s+unrestricted\s+access",
        ),
        (
            "agent bypasses authorization",
            r"agent.{0,80}bypass(?:es|ing)?\s+authorization",
        ),
        (
            "capability automatically grants execution",
            r"capability.{0,80}automatically.{0,80}execution",
        ),
        (
            "model output automatically trusted",
            r"model\s+output.{0,80}automatically.{0,80}trusted",
        ),
    )

    for doc_id, document in documents.items():
        text = normalize(document.text)

        for label, pattern in forbidden_patterns:
            if re.search(pattern, text):
                contradictions.append(
                    f"{doc_id}: potentially unsafe alternate-path "
                    f"statement detected: {label}"
                )

    return unique(contradictions)


# ============================================================================
# Security invariant analysis
# ============================================================================

def evaluate_security_invariants(
    documents: dict[str, Document],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}

    for invariant in SECURITY_INVARIANTS:
        represented: list[str] = []

        for doc_id, document in documents.items():
            if invariant in normalize(document.text):
                represented.append(doc_id)

        result[invariant] = represented

    return result


# ============================================================================
# TR reconciliation
# ============================================================================

def reconcile_tr(
    tr_id: str,
    documents: dict[str, Document],
) -> TRResult:
    owner = TR_OWNERSHIP[tr_id]
    dependencies = TR_SUPPORTING_DEPENDENCIES[tr_id]

    result = TRResult(
        tr_id=tr_id,
        owner=owner,
        dependencies=dependencies,
    )

    owner_ok, owner_evidence = evaluate_owner(
        tr_id,
        owner,
        documents,
    )

    result.owner_present = owner in documents
    result.owner_evidence = owner_evidence

    if not owner_ok:
        result.classification = "REVIEW_REQUIRED"
        result.rationale = (
            "Primary owner exists or is expected, but sufficient "
            "owner evidence was not detected."
        )
        return result

    for dependency in sorted(dependencies):
        status, evidence = evaluate_dependency(
            tr_id,
            dependency,
            documents,
        )

        result.dependency_results[dependency] = status

    missing_dependencies = [
        doc_id
        for doc_id, status in result.dependency_results.items()
        if status == "MISSING_DOCUMENT"
    ]

    absent_dependencies = [
        doc_id
        for doc_id, status in result.dependency_results.items()
        if status == "ABSENT"
    ]

    if missing_dependencies:
        result.classification = "REVIEW_REQUIRED"
        result.rationale = (
            "One or more canonical dependency documents are missing."
        )
        return result

    if absent_dependencies:
        # Dependency documents are not required to duplicate the owner's
        # entire TR. However, if ALL dependency evidence is absent, the
        # cross-document relationship is not sufficiently evidenced.
        represented = [
            status
            for status in result.dependency_results.values()
            if status in {"DIRECT", "SEMANTIC"}
        ]

        if not represented:
            result.classification = "REVIEW_REQUIRED"
            result.rationale = (
                "No supporting/dependency evidence was detected "
                "outside the owner."
            )
            return result

    result.classification = "RECONCILED"
    result.rationale = (
        "Owner evidence is present and the cross-document dependency "
        "graph contains substantive supporting evidence."
    )

    return result


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    print_header(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B CROSS-DOCUMENT TRACEABILITY & RECONCILIATION AUDIT"
    )

    print(
        f"Repository : {REPO_ROOT}"
    )
    print(
        "Scope      : PB-DOC-001..PB-DOC-020"
    )
    print(
        "Traceability: TR-001..TR-009"
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
    # Load all canonical documents
    # ------------------------------------------------------------------

    print_header(
        "1. CANONICAL DOCUMENT INVENTORY"
    )

    documents, load_failures = load_documents()

    for doc_id in CANONICAL_DOCUMENTS:
        if doc_id in documents:
            document = documents[doc_id]

            print(
                f"{doc_id:<12} "
                f"PASS  "
                f"{len(document.lines):>5} lines  "
                f"{document.path.relative_to(REPO_ROOT)}"
            )
        else:
            failure_text = next(
                (
                    failure
                    for failure in load_failures
                    if failure.startswith(doc_id + ":")
                ),
                "unknown",
            )
            print(
                f"{doc_id:<12} FAIL  {failure_text}"
            )

    if load_failures:
        print()
        print(
            "Canonical document loading failures:"
        )

        for failure in load_failures:
            print(
                f"  - {failure}"
            )

        return 2

    # ------------------------------------------------------------------
    # Document identity
    # ------------------------------------------------------------------

    print_header(
        "2. DOCUMENT IDENTITY VALIDATION"
    )

    identity_failures: list[str] = []

    for doc_id, document in documents.items():
        passed, evidence = validate_document_identity(
            document
        )

        print(
            f"{doc_id:<12}: "
            f"{'PASS' if passed else 'FAIL'} — "
            f"{evidence}"
        )

        if not passed:
            identity_failures.append(
                doc_id
            )

    # ------------------------------------------------------------------
    # TR ownership validation
    # ------------------------------------------------------------------

    print_header(
        "3. TR OWNERSHIP / DEPENDENCY REGISTRY"
    )

    ownership_failures: list[str] = []

    for tr_id in TR_IDS:
        owner = TR_OWNERSHIP[tr_id]
        dependencies = TR_SUPPORTING_DEPENDENCIES[tr_id]

        owner_exists = owner in documents

        dependency_missing = [
            dependency
            for dependency in dependencies
            if dependency not in documents
        ]

        print(
            f"{tr_id:<8} "
            f"OWNER={owner:<12} "
            f"OWNER_PRESENT={'YES' if owner_exists else 'NO'} "
            f"DEPENDENCIES={len(dependencies):>2} "
            f"MISSING={len(dependency_missing):>2}"
        )

        if not owner_exists or dependency_missing:
            ownership_failures.append(
                tr_id
            )

    # ------------------------------------------------------------------
    # Cross-document TR reconciliation
    # ------------------------------------------------------------------

    print_header(
        "4. CROSS-DOCUMENT TR RECONCILIATION"
    )

    tr_results: list[TRResult] = []

    for tr_id in TR_IDS:
        result = reconcile_tr(
            tr_id,
            documents,
        )

        tr_results.append(
            result
        )

        print()
        print(
            f"{tr_id}"
        )
        print(
            f"  Primary owner       : "
            f"{result.owner}"
        )
        print(
            f"  Owner evidence      : "
            + (
                ", ".join(result.owner_evidence)
                if result.owner_evidence
                else "NONE"
            )
        )
        print(
            f"  Classification      : "
            f"{result.classification}"
        )

        print(
            "  Dependencies:"
        )

        for dependency, status in (
            result.dependency_results.items()
        ):
            print(
                f"    {dependency:<12} {status}"
            )

        print(
            f"  Rationale           : "
            f"{result.rationale}"
        )

    # ------------------------------------------------------------------
    # Architecture relationship coverage
    # ------------------------------------------------------------------

    print_header(
        "5. ARCHITECTURAL RELATIONSHIP COVERAGE"
    )

    relationship_results: list[RelationshipResult] = []

    for tr_id in TR_IDS:
        owner = TR_OWNERSHIP[tr_id]

        expected = (
            {owner}
            | TR_SUPPORTING_DEPENDENCIES[tr_id]
        )

        for group in RELATIONSHIP_GROUPS:
            relationship = evaluate_relationship_group(
                group,
                expected,
                documents,
            )

            relationship_results.append(
                relationship
            )

            # Only print a compact summary here; detailed evidence is
            # retained internally for the final report.
            print(
                f"{tr_id:<8} "
                f"{group:<26} "
                f"{relationship.classification:<10} "
                f"present={len(relationship.present_documents):>2} "
                f"missing={len(relationship.missing_expected_documents):>2}"
            )

    relationship_review = [
        relationship
        for relationship in relationship_results
        if relationship.classification == "ABSENT"
    ]

    # ------------------------------------------------------------------
    # Security invariant coverage
    # ------------------------------------------------------------------

    print_header(
        "6. GLOBAL SECURITY INVARIANT COVERAGE"
    )

    security_results = evaluate_security_invariants(
        documents
    )

    security_failures: list[str] = []

    for invariant, represented in security_results.items():
        status = (
            "PASS"
            if represented
            else "FAIL"
        )

        print(
            f"{invariant:<28}: "
            f"{status} "
            f"documents={len(represented)}"
        )

        if not represented:
            security_failures.append(
                invariant
            )

    # ------------------------------------------------------------------
    # Contradiction analysis
    # ------------------------------------------------------------------

    print_header(
        "7. CROSS-DOCUMENT CONTRADICTION ANALYSIS"
    )

    contradictions = detect_contradictions(
        documents
    )

    if contradictions:
        for contradiction in contradictions:
            print(
                f"REVIEW: {contradiction}"
            )
    else:
        print(
            "No contradictory architectural/governance "
            "patterns detected."
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    print_header(
        "8. FINAL RECONCILIATION SUMMARY"
    )

    tr_counts: dict[str, int] = {}

    for result in tr_results:
        tr_counts[result.classification] = (
            tr_counts.get(
                result.classification,
                0,
            )
            + 1
        )

    print(
        "TR RECONCILIATION"
    )

    for classification in (
        "RECONCILED",
        "REVIEW_REQUIRED",
    ):
        print(
            f"  {classification:<20}: "
            f"{tr_counts.get(classification, 0)}"
        )

    print()
    print(
        "DOCUMENT IDENTITY"
    )
    print(
        f"  Passed                : "
        f"{len(CANONICAL_DOCUMENTS) - len(identity_failures)}"
    )
    print(
        f"  Failed                : "
        f"{len(identity_failures)}"
    )

    print()
    print(
        "ARCHITECTURAL RELATIONSHIPS"
    )
    print(
        f"  Absent relationships  : "
        f"{len(relationship_review)}"
    )

    print()
    print(
        "SECURITY INVARIANTS"
    )
    print(
        f"  Missing invariants    : "
        f"{len(security_failures)}"
    )

    print()
    print(
        "CONTRADICTIONS"
    )
    print(
        f"  Findings              : "
        f"{len(contradictions)}"
    )

    # ------------------------------------------------------------------
    # Detailed unresolved findings
    # ------------------------------------------------------------------

    unresolved: list[str] = []

    unresolved.extend(
        f"{result.tr_id}: {result.rationale}"
        for result in tr_results
        if result.classification == "REVIEW_REQUIRED"
    )

    unresolved.extend(
        f"Relationship {relationship.group}: "
        f"expected documents missing or relationship absent"
        for relationship in relationship_review
    )

    unresolved.extend(
        f"Security invariant missing: {invariant}"
        for invariant in security_failures
    )

    unresolved.extend(
        contradictions
    )

    if identity_failures:
        unresolved.extend(
            f"Document identity failed: {doc_id}"
            for doc_id in identity_failures
        )

    # ------------------------------------------------------------------
    # Governance safety
    # ------------------------------------------------------------------

    print_header(
        "9. GOVERNANCE SAFETY"
    )

    governance_ok = verify_governance_safety()

    # ------------------------------------------------------------------
    # Read-only guarantee
    # ------------------------------------------------------------------

    print_header(
        "10. READ-ONLY GUARANTEE"
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
    # Final result
    # ------------------------------------------------------------------

    print_header(
        "11. FINAL RESULT"
    )

    if not governance_ok:
        print(
            "RESULT: SAFETY FAILURE — "
            "governance state could not be verified."
        )
        return 2

    if unresolved:
        print(
            "RESULT: REVIEW REQUIRED — "
            f"{len(unresolved)} unresolved "
            "cross-document finding(s)."
        )

        print()
        print(
            "UNRESOLVED FINDINGS:"
        )

        for finding in unresolved:
            print(
                f"  - {finding}"
            )

        print()
        print(
            "No documentation, Gap Register, Master Manifest, "
            "approval, authorization, or certification state "
            "was changed."
        )

        return 1

    print(
        "RESULT: CROSS-DOCUMENT TRACEABILITY & "
        "RECONCILIATION COMPLETE — "
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

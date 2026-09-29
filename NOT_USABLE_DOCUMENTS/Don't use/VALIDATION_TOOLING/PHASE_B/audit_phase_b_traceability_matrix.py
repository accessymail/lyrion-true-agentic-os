#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Traceability Matrix Audit

READ-ONLY.

Purpose
-------
Build an evidence-based traceability matrix for TR-001..TR-009 using
the existing Phase-B documentation.

The auditor:
  1. Locates TR-001..TR-009 definitions/references in the repository.
  2. Extracts surrounding evidence.
  3. Maps each TR requirement against PB-DOC-001..020.
  4. Detects internal requirement identifiers.
  5. Detects explicit and implicit architectural relationships.
  6. Separates direct evidence from inferred/equivalent evidence.
  7. Reports unresolved traceability relationships.

It does NOT:
  - modify documentation;
  - modify manifests;
  - modify the Gap Register;
  - add TR references;
  - close documentation gaps;
  - approve architecture;
  - authorize implementation;
  - claim production certification.

Classification:
  DIRECT
  EQUIVALENT
  RELATED
  ABSENT
  REVIEW_REQUIRED

Exit codes:
  0 = no unresolved matrix findings
  1 = review required
  2 = runtime/configuration failure
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "docs" / "phase-b"

TR_IDS = tuple(f"TR-{index:03d}" for index in range(1, 10))

PB_DOCS: dict[str, Path] = {
    "PB-DOC-001": DOC_ROOT
    / "requirements"
    / "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",

    "PB-DOC-002": DOC_ROOT
    / "agentic-runtime"
    / "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",

    "PB-DOC-003": DOC_ROOT
    / "identity-authority"
    / "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",

    "PB-DOC-004": DOC_ROOT
    / "capability"
    / "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",

    "PB-DOC-005": DOC_ROOT
    / "agent-harness"
    / "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-006": DOC_ROOT
    / "host-harness"
    / "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-007": DOC_ROOT
    / "universal-computer"
    / "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",

    "PB-DOC-008": DOC_ROOT
    / "application-harness"
    / "LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",

    "PB-DOC-009": DOC_ROOT
    / "execution-admission"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",

    "PB-DOC-010": DOC_ROOT
    / "aegis"
    / "LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",

    "PB-DOC-011": DOC_ROOT
    / "secure-execution"
    / "LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",

    "PB-DOC-012": DOC_ROOT
    / "interfaces"
    / "LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",

    "PB-DOC-013": DOC_ROOT
    / "data"
    / "LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",

    "PB-DOC-014": DOC_ROOT
    / "memory"
    / "LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",

    "PB-DOC-015": DOC_ROOT
    / "observability"
    / "LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",

    "PB-DOC-016": DOC_ROOT
    / "validation"
    / "LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",

    "PB-DOC-017": DOC_ROOT
    / "security-testing"
    / "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",

    "PB-DOC-018": DOC_ROOT
    / "operations"
    / "LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",

    "PB-DOC-019": DOC_ROOT
    / "recovery"
    / "LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",

    "PB-DOC-020": DOC_ROOT
    / "manifest"
    / "LYRION_UNIFIED_CORE_PHASE_B_MASTER_MANIFEST_v1.md",
}


@dataclass(frozen=True)
class Evidence:
    document: str
    line: int
    text: str


@dataclass(frozen=True)
class MatrixResult:
    tr_id: str
    document: str
    classification: str
    evidence: tuple[Evidence, ...]
    reason: str


RESULTS: list[MatrixResult] = []


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {path}: {exc}") from exc


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def lines_matching(
    text: str,
    patterns: tuple[str, ...],
) -> list[Evidence]:
    compiled = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in patterns
    ]

    results: list[Evidence] = []

    for number, line in enumerate(text.splitlines(), start=1):
        if any(pattern.search(line) for pattern in compiled):
            results.append(
                Evidence(
                    document="",
                    line=number,
                    text=line.strip(),
                )
            )

    return results


def context_for_term(
    document: str,
    text: str,
    term: str,
    radius: int = 2,
    limit: int = 6,
) -> list[Evidence]:
    lines = text.splitlines()
    output: list[Evidence] = []

    pattern = re.compile(
        rf"(?<![A-Z0-9]){re.escape(term)}(?![A-Z0-9])",
        re.IGNORECASE,
    )

    for index, line in enumerate(lines):
        if not pattern.search(line):
            continue

        start = max(0, index - radius)
        end = min(len(lines), index + radius + 1)

        for number in range(start, end):
            output.append(
                Evidence(
                    document=document,
                    line=number + 1,
                    text=lines[number].strip(),
                )
            )

        if len(output) >= limit * (radius * 2 + 1):
            break

    return output


def locate_tr_definitions() -> dict[str, list[Evidence]]:
    """
    Search the entire Phase-B documentation tree for TR identifiers.

    No definition is invented. The auditor only reports what actually
    exists in the repository.
    """

    definitions: dict[str, list[Evidence]] = {
        tr_id: []
        for tr_id in TR_IDS
    }

    if not DOC_ROOT.is_dir():
        raise RuntimeError(
            f"Phase-B documentation directory not found: {DOC_ROOT}"
        )

    for path in sorted(DOC_ROOT.rglob("*.md")):
        try:
            text = read(path)
        except RuntimeError:
            continue

        relative = str(path.relative_to(REPO_ROOT))

        for tr_id in TR_IDS:
            evidence = context_for_term(
                relative,
                text,
                tr_id,
                radius=2,
                limit=4,
            )

            definitions[tr_id].extend(evidence)

    return definitions


def detect_internal_requirement_ids(text: str) -> list[str]:
    patterns = (
        r"\bCORE-[A-Z0-9_-]+-\d{1,4}\b",
        r"\b[A-Z]{2,12}-[A-Z]{1,12}-\d{1,4}\b",
        r"\bREQ-[A-Z0-9_-]+\b",
    )

    identifiers: set[str] = set()

    for pattern in patterns:
        for match in re.findall(pattern, text):
            identifiers.add(match)

    return sorted(identifiers)


def detect_relationships(text: str) -> dict[str, bool]:
    lowered = normalize(text)

    return {
        "identity_authority": (
            "identity" in lowered
            and "authority" in lowered
        ),
        "authority_capability": (
            "authority" in lowered
            and "capability" in lowered
        ),
        "capability_authorization": (
            "capability" in lowered
            and "authorization" in lowered
        ),
        "authorization_execution": (
            "authorization" in lowered
            and "execution" in lowered
        ),
        "execution_verification": (
            "execution" in lowered
            and "verification" in lowered
        ),
        "verification_provenance": (
            "verification" in lowered
            and "provenance" in lowered
        ),
        "agent_host": (
            "agent" in lowered
            and "host" in lowered
        ),
        "host_application": (
            "host" in lowered
            and "application" in lowered
        ),
        "fail_closed": (
            "fail-closed" in lowered
            or "fail closed" in lowered
        ),
        "least_privilege": (
            "least privilege" in lowered
            or "least-privilege" in lowered
        ),
    }


def classify_document(
    tr_id: str,
    document: str,
    text: str,
    tr_definition_evidence: list[Evidence],
) -> MatrixResult:
    """
    Classification is intentionally conservative.

    DIRECT:
        The document explicitly references the TR identifier.

    EQUIVALENT:
        The document contains strong architectural/requirement evidence
        relevant to the TR definition, but no literal TR identifier.

    RELATED:
        Some supporting relationship exists, but evidence is incomplete.

    ABSENT:
        No meaningful evidence detected.

    REVIEW_REQUIRED:
        The TR definition itself cannot be established from repository
        evidence, so no semantic conclusion is safe.
    """

    explicit_pattern = re.compile(
        rf"(?<![A-Z0-9]){re.escape(tr_id)}(?![A-Z0-9])",
        re.IGNORECASE,
    )

    explicit_lines: list[Evidence] = []

    for number, line in enumerate(text.splitlines(), start=1):
        if explicit_pattern.search(line):
            explicit_lines.append(
                Evidence(
                    document=document,
                    line=number,
                    text=line.strip(),
                )
            )

    if explicit_lines:
        return MatrixResult(
            tr_id=tr_id,
            document=document,
            classification="DIRECT",
            evidence=tuple(explicit_lines[:6]),
            reason="Literal TR reference exists in the document.",
        )

    # Without a repository-supported definition we cannot infer semantics.
    if not tr_definition_evidence:
        return MatrixResult(
            tr_id=tr_id,
            document=document,
            classification="REVIEW_REQUIRED",
            evidence=(),
            reason=(
                "No repository definition/reference for this TR identifier "
                "was found; semantic mapping cannot safely be inferred."
            ),
        )

    relationships = detect_relationships(text)
    relationship_score = sum(
        1
        for value in relationships.values()
        if value
    )

    identifiers = detect_internal_requirement_ids(text)

    traceability_terms = (
        "requirements traceability",
        "traceability",
        "requirement mapping",
        "dependency",
        "interface",
        "contract",
        "verification",
        "provenance",
        "acceptance criteria",
    )

    lowered = normalize(text)

    traceability_score = sum(
        1
        for term in traceability_terms
        if term in lowered
    )

    if relationship_score >= 7 and traceability_score >= 4:
        classification = "EQUIVALENT"
        reason = (
            f"Strong architecture evidence: "
            f"{relationship_score} relationship groups and "
            f"{traceability_score} traceability concepts; "
            f"{len(identifiers)} internal requirement identifiers."
        )
    elif relationship_score >= 4 or traceability_score >= 3:
        classification = "RELATED"
        reason = (
            f"Relevant architecture evidence exists "
            f"({relationship_score} relationship groups; "
            f"{traceability_score} traceability concepts), "
            "but equivalence is not established."
        )
    else:
        classification = "ABSENT"
        reason = "No sufficient evidence for this TR relationship."

    evidence: list[Evidence] = []

    evidence.extend(
        context_for_term(
            document,
            text,
            "verification",
            radius=1,
            limit=2,
        )
    )

    evidence.extend(
        context_for_term(
            document,
            text,
            "authorization",
            radius=1,
            limit=2,
        )
    )

    return MatrixResult(
        tr_id=tr_id,
        document=document,
        classification=classification,
        evidence=tuple(evidence[:8]),
        reason=reason,
    )


def build_matrix(
    definitions: dict[str, list[Evidence]],
) -> None:
    for tr_id in TR_IDS:
        print()
        print("=" * 100)
        print(f"{tr_id} — SOURCE DEFINITION EVIDENCE")
        print("=" * 100)

        definition_evidence = definitions[tr_id]

        if definition_evidence:
            # De-duplicate by file/line/text.
            seen: set[tuple[str, int, str]] = set()

            for evidence in definition_evidence:
                key = (
                    evidence.document,
                    evidence.line,
                    evidence.text,
                )

                if key in seen:
                    continue

                seen.add(key)

                print(
                    f"{evidence.document}:{evidence.line}: "
                    f"{evidence.text}"
                )
        else:
            print("NO SOURCE DEFINITION/REFERENCE FOUND")

        for document, path in PB_DOCS.items():
            if not path.is_file():
                RESULTS.append(
                    MatrixResult(
                        tr_id=tr_id,
                        document=document,
                        classification="REVIEW_REQUIRED",
                        evidence=(),
                        reason="Canonical PB-DOC file is missing.",
                    )
                )
                continue

            text = read(path)

            result = classify_document(
                tr_id,
                document,
                text,
                definition_evidence,
            )

            RESULTS.append(result)


def print_matrix() -> int:
    print()
    print("=" * 100)
    print("LYRION TRUE AGENTIC OS")
    print("PHASE-B TRACEABILITY MATRIX")
    print("=" * 100)

    for tr_id in TR_IDS:
        print()
        print(f"--- {tr_id} ---")

        rows = [
            result
            for result in RESULTS
            if result.tr_id == tr_id
        ]

        for result in rows:
            print(
                f"{result.document:12} "
                f"{result.classification:16} "
                f"{result.reason}"
            )

            for evidence in result.evidence[:3]:
                print(
                    f"    evidence {evidence.document}:"
                    f"{evidence.line}: "
                    f"{evidence.text}"
                )

    print()
    print("=" * 100)
    print("PER-TR SUMMARY")
    print("=" * 100)

    unresolved = 0

    for tr_id in TR_IDS:
        rows = [
            result
            for result in RESULTS
            if result.tr_id == tr_id
        ]

        counts: dict[str, int] = {}

        for result in rows:
            counts[result.classification] = (
                counts.get(result.classification, 0) + 1
            )

        review_count = (
            counts.get("REVIEW_REQUIRED", 0)
            + counts.get("ABSENT", 0)
        )

        if review_count:
            unresolved += 1

        print(
            f"{tr_id}: "
            f"DIRECT={counts.get('DIRECT', 0)} "
            f"EQUIVALENT={counts.get('EQUIVALENT', 0)} "
            f"RELATED={counts.get('RELATED', 0)} "
            f"ABSENT={counts.get('ABSENT', 0)} "
            f"REVIEW_REQUIRED={counts.get('REVIEW_REQUIRED', 0)}"
        )

    print()
    print("=" * 100)
    print("GOVERNANCE SAFETY")
    print("=" * 100)
    print("Architecture Approval        : PENDING")
    print("Implementation Authorization : NOT AUTHORIZED")
    print("Production Implementation   : BLOCKED")
    print("Production Certification    : NOT CLAIMED")

    print()
    print("=" * 100)
    print("READ-ONLY GUARANTEE")
    print("=" * 100)
    print("No Phase-B document was modified.")
    print("No Gap Register state was modified.")
    print("No manifest was modified.")
    print("No governance state was modified.")
    print("No implementation authority was granted.")

    print()

    if unresolved:
        print(
            f"RESULT: TRACEABILITY MATRIX REQUIRES REVIEW — "
            f"{unresolved}/9 TR requirements contain unresolved "
            "or non-equivalent evidence."
        )
        return 1

    print(
        "RESULT: TRACEABILITY MATRIX EVIDENCE SUFFICIENT FOR REVIEW."
    )
    return 0


def main() -> int:
    try:
        definitions = locate_tr_definitions()
        build_matrix(definitions)
        return print_matrix()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

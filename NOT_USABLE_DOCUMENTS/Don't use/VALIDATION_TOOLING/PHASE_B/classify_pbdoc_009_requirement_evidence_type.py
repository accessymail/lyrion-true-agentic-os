from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

NORMATIVE_PATTERN = re.compile(
    r"\b(?:SHALL|MUST|SHOULD|REQUIRED|"
    r"SHALL NOT|MUST NOT)\b",
    re.IGNORECASE,
)

HEADING_PATTERN = re.compile(
    r"^(#{1,6})\s+(.+?)\s*$"
)

TOKEN_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9_/-]{2,}"
)

CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "SECURITY_CONTROL": (
        "security",
        "authorization",
        "authority",
        "capability",
        "admission",
        "aegis",
        "sandbox",
        "fail-closed",
        "fail closed",
        "revocation",
        "revoked",
        "expiry",
        "expired",
        "integrity",
        "trust",
        "privilege",
        "privileged",
        "attack",
        "threat",
        "containment",
        "emergency",
    ),
    "TEST_VERIFICATION": (
        "test",
        "testing",
        "validation",
        "verify",
        "verification",
        "evidence",
        "negative test",
        "re-execution",
        "independent verification",
        "acceptance",
        "qualification",
    ),
    "GOVERNANCE": (
        "governance",
        "approval",
        "authorized",
        "authorization gate",
        "implementation authorization",
        "production authorization",
        "certification",
        "human",
        "hitl",
        "delegated authority",
        "policy",
        "decision",
        "reviewer",
        "change control",
        "authority boundary",
    ),
    "DOCUMENTATION_TRACEABILITY": (
        "documentation",
        "manifest",
        "traceability",
        "provenance",
        "record",
        "audit record",
        "document",
        "version",
        "baseline",
        "repository",
        "path",
        "reference",
        "hash",
        "synchronization",
    ),
    "ARCHITECTURE_BOUNDARY": (
        "architecture",
        "architectural",
        "boundary",
        "upstream",
        "downstream",
        "shall remain",
        "shall not replace",
        "shall not bypass",
        "alternate path",
        "trust boundary",
        "component",
        "interface",
        "harness",
        "lhicf",
        "universal computer",
        "host harness",
        "application harness",
    ),
    "IMPLEMENTATION_CONTROL": (
        "implement",
        "implementation",
        "execute",
        "execution",
        "request",
        "context",
        "service",
        "component",
        "function",
        "interface",
        "process",
        "operation",
        "recovery",
        "lifecycle",
        "runtime",
    ),
}


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    section: str
    line: int
    text: str


@dataclass(frozen=True)
class Classification:
    requirement: Requirement
    categories: tuple[str, ...]
    scores: tuple[tuple[str, int], ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def extract_requirements() -> list[Requirement]:
    lines = SPECIFICATION.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines()

    requirements: list[Requirement] = []
    section = "UNSPECIFIED"

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        heading = HEADING_PATTERN.match(line)

        if heading:
            section = heading.group(2).strip()

        if not NORMATIVE_PATTERN.search(line):
            continue

        text = line.strip()

        if not text:
            continue

        requirements.append(
            Requirement(
                requirement_id=(
                    f"PB-DOC-009-R{len(requirements) + 1:03d}"
                ),
                section=section,
                line=line_number,
                text=text,
            )
        )

    return requirements


def score_requirement(
    requirement: Requirement,
) -> Classification:
    text = requirement.text.lower()
    scores: dict[str, int] = {}

    for category, terms in CATEGORY_TERMS.items():
        score = 0

        for term in terms:
            if term.lower() in text:
                score += 1

        scores[category] = score

    positive = [
        (category, score)
        for category, score in scores.items()
        if score > 0
    ]

    positive.sort(
        key=lambda item: (-item[1], item[0])
    )

    if not positive:
        categories = ("UNCLASSIFIED",)
    elif len(positive) == 1:
        categories = (positive[0][0],)
    else:
        highest = positive[0][1]

        categories = tuple(
            category
            for category, score in positive
            if score >= max(1, highest - 1)
        )

        if len(categories) > 1:
            categories = tuple(
                dict.fromkeys(
                    (
                        "MIXED",
                        *categories,
                    )
                )
            )

    return Classification(
        requirement=requirement,
        categories=categories,
        scores=tuple(positive),
    )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — REQUIREMENT EVIDENCE-TYPE "
        "CLASSIFICATION"
    )
    print("READ-ONLY")
    print()

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")

    if not SPECIFICATION.is_file():
        print(
            "RESULT: FAIL — PB-DOC-009 specification "
            "not found."
        )
        return 1

    specification = SPECIFICATION.read_text(
        encoding="utf-8",
        errors="strict",
    )

    if "PB-DOC-009" not in specification:
        print(
            "RESULT: FAIL — PB-DOC-009 identity "
            "not established."
        )
        return 1

    if "Execution Admission" not in specification:
        print(
            "RESULT: FAIL — Execution Admission "
            "identity not established."
        )
        return 1

    requirements = extract_requirements()

    if not requirements:
        print(
            "RESULT: FAIL — no normative requirements "
            "discovered."
        )
        return 1

    classifications = [
        score_requirement(requirement)
        for requirement in requirements
    ]

    print(
        f"Specification SHA256: {sha256(SPECIFICATION)}"
    )
    print(
        f"Normative requirements: {len(requirements)}"
    )

    print()
    print("=" * 100)
    print("REQUIREMENT EVIDENCE-TYPE CLASSIFICATION")
    print("=" * 100)

    for classification in classifications:
        requirement = classification.requirement

        print()
        print("-" * 100)
        print(
            f"{requirement.requirement_id} | "
            f"SPEC:L{requirement.line}"
        )
        print(f"SECTION: {requirement.section}")
        print(
            f"CATEGORY: "
            f"{', '.join(classification.categories)}"
        )
        print(f"REQUIREMENT: {requirement.text}")

        if classification.scores:
            print(
                "SIGNALS: "
                + ", ".join(
                    f"{category}={score}"
                    for category, score
                    in classification.scores
                )
            )
        else:
            print("SIGNALS: NONE")

    counts: dict[str, int] = {}

    for classification in classifications:
        for category in classification.categories:
            counts[category] = (
                counts.get(category, 0) + 1
            )

    print()
    print("=" * 100)
    print("CLASSIFICATION SUMMARY")
    print("=" * 100)

    for category, count in sorted(counts.items()):
        print(f"{category}: {count}")

    print()
    print("=" * 100)
    print("CLASSIFICATION SEMANTICS")
    print("=" * 100)

    print(
        "IMPLEMENTATION_CONTROL = requires concrete "
        "implementation/runtime evidence."
    )
    print(
        "SECURITY_CONTROL = requires security/control-boundary "
        "evidence."
    )
    print(
        "TEST_VERIFICATION = requires validation/test/evidence "
        "proof."
    )
    print(
        "GOVERNANCE = requires authorization/approval/"
        "governance evidence."
    )
    print(
        "DOCUMENTATION_TRACEABILITY = requires documentary/"
        "provenance/traceability evidence."
    )
    print(
        "ARCHITECTURE_BOUNDARY = requires architectural/"
        "boundary/interface evidence."
    )
    print(
        "MIXED = multiple evidence types are materially relevant."
    )

    print()
    print("=" * 100)
    print("ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 100)

    print(
        "PRESERVE: NOT ASSIGNED"
    )
    print(
        "EXTEND: NOT ASSIGNED"
    )
    print(
        "NEW: NOT ASSIGNED"
    )
    print(
        "REFACTOR: NOT ASSIGNED"
    )
    print(
        "CONFLICT: NOT ASSIGNED"
    )

    print()
    print("=" * 100)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 100)

    print("READ-ONLY: YES")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")

    print()
    print("=" * 100)
    print("FINAL RESULT")
    print("=" * 100)

    print(
        "RESULT: PASS — PB-DOC-009 REQUIREMENT "
        "EVIDENCE-TYPE CLASSIFICATION COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

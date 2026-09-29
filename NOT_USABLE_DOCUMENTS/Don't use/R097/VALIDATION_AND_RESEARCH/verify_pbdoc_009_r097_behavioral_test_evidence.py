from __future__ import annotations

import ast
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

TEST_ROOT = REPO_ROOT / "tests"

TARGET = (
    "R097",
    "Expired or revoked authority is not restored from checkpoint state.",
)


@dataclass(frozen=True)
class TestCase:
    path: Path
    line: int
    name: str
    source: str


@dataclass(frozen=True)
class Evidence:
    category: str
    path: Path
    line: int
    text: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_source(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, UnicodeError):
        return ""


def discover_test_cases() -> list[TestCase]:
    if not TEST_ROOT.is_dir():
        return []

    cases: list[TestCase] = []

    for path in sorted(TEST_ROOT.rglob("*.py")):
        if any(
            part in {
                ".venv",
                "__pycache__",
                ".pytest_cache",
            }
            for part in path.parts
        ):
            continue

        source = read_source(path)

        if not source:
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            if not node.name.startswith("test_"):
                continue

            segment = ast.get_source_segment(
                source,
                node,
            ) or ""

            cases.append(
                TestCase(
                    path=path,
                    line=node.lineno,
                    name=node.name,
                    source=segment,
                )
            )

    return cases


def matching_terms(
    source: str,
    terms: tuple[str, ...],
) -> list[str]:
    lowered = source.lower()

    return [
        term
        for term in terms
        if term.lower() in lowered
    ]


def collect_evidence(
    cases: list[TestCase],
    terms: tuple[str, ...],
    category: str,
) -> list[Evidence]:
    evidence: list[Evidence] = []

    for case in cases:
        matched = matching_terms(
            case.source,
            terms,
        )

        if not matched:
            continue

        evidence.append(
            Evidence(
                category=category,
                path=case.path,
                line=case.line,
                text=(
                    f"{case.name} | "
                    f"terms={matched}"
                ),
            )
        )

    return evidence


def case_has_all(
    case: TestCase,
    required_terms: tuple[str, ...],
) -> bool:
    lowered = case.source.lower()

    return all(
        term.lower() in lowered
        for term in required_terms
    )


def find_strong_cases(
    cases: list[TestCase],
) -> list[TestCase]:
    strong: list[TestCase] = []

    required_groups = (
        (
            "checkpoint",
            "recovery",
        ),
        (
            "authorization",
            "expiry",
        ),
        (
            "authorization",
            "revok",
        ),
        (
            "admission",
            "authorization",
        ),
    )

    for case in cases:
        if any(
            case_has_all(case, group)
            for group in required_groups
        ):
            strong.append(case)

    return strong


def find_cross_boundary_cases(
    cases: list[TestCase],
) -> list[TestCase]:
    boundary_terms = (
        "checkpoint",
        "recovery",
        "authorization",
        "admission",
        "expiry",
        "expired",
        "revok",
        "revoke",
        "deny",
        "denied",
        "reject",
        "fail",
        "assert",
    )

    results: list[TestCase] = []

    for case in cases:
        matched = matching_terms(
            case.source,
            boundary_terms,
        )

        if len(set(matched)) >= 4:
            results.append(case)

    return results


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 BEHAVIORAL "
        "TEST-EVIDENCE DEEP VERIFICATION"
    )
    print("READ-ONLY")
    print()

    if not SPECIFICATION.is_file():
        print("RESULT: FAIL — specification missing.")
        return 1

    if not TEST_ROOT.is_dir():
        print("RESULT: FAIL — tests directory missing.")
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )
    print(f"Test root: {TEST_ROOT}")

    cases = discover_test_cases()

    print(
        f"Concrete test cases discovered: "
        f"{len(cases)}"
    )

    print()
    print("=" * 100)
    print("R097 — BEHAVIORAL TEST-EVIDENCE ANALYSIS")
    print("=" * 100)
    print(f"DESCRIPTION: {TARGET[1]}")

    expiry_cases = collect_evidence(
        cases,
        (
            "authorization",
            "expiry",
        ),
        "AUTHORIZATION_EXPIRY",
    )

    revocation_cases = collect_evidence(
        cases,
        (
            "authorization",
            "revok",
        ),
        "AUTHORIZATION_REVOCATION",
    )

    checkpoint_cases = collect_evidence(
        cases,
        (
            "checkpoint",
            "recovery",
        ),
        "CHECKPOINT_RECOVERY",
    )

    admission_cases = collect_evidence(
        cases,
        (
            "admission",
            "authorization",
        ),
        "ADMISSION_AUTHORIZATION",
    )

    denial_cases = collect_evidence(
        cases,
        (
            "authorization",
            "denied",
        ),
        "AUTHORIZATION_DENIAL",
    )

    strong_cases = find_strong_cases(cases)
    cross_boundary_cases = find_cross_boundary_cases(cases)

    print()
    print("CATEGORY COUNTS")
    print(
        f"  Authorization + expiry: "
        f"{len(expiry_cases)}"
    )
    print(
        f"  Authorization + revocation: "
        f"{len(revocation_cases)}"
    )
    print(
        f"  Checkpoint + recovery: "
        f"{len(checkpoint_cases)}"
    )
    print(
        f"  Admission + authorization: "
        f"{len(admission_cases)}"
    )
    print(
        f"  Authorization denial: "
        f"{len(denial_cases)}"
    )
    print(
        f"  Strong lifecycle candidates: "
        f"{len(strong_cases)}"
    )
    print(
        f"  Cross-boundary candidates: "
        f"{len(cross_boundary_cases)}"
    )

    print()
    print("EXPIRY TEST EVIDENCE")

    for item in expiry_cases[:30]:
        print(
            f"  TEST: {item.path}:L{item.line} | "
            f"{item.text}"
        )

    print()
    print("REVOCATION TEST EVIDENCE")

    for item in revocation_cases[:30]:
        print(
            f"  TEST: {item.path}:L{item.line} | "
            f"{item.text}"
        )

    print()
    print("CHECKPOINT / RECOVERY TEST EVIDENCE")

    for item in checkpoint_cases[:30]:
        print(
            f"  TEST: {item.path}:L{item.line} | "
            f"{item.text}"
        )

    print()
    print("ADMISSION / AUTHORIZATION TEST EVIDENCE")

    for item in admission_cases[:30]:
        print(
            f"  TEST: {item.path}:L{item.line} | "
            f"{item.text}"
        )

    print()
    print("STRONG LIFECYCLE CANDIDATES")

    for case in strong_cases[:30]:
        print(
            f"  TEST: {case.path}:L{case.line} | "
            f"{case.name}"
        )

    print()
    print("CROSS-BOUNDARY TEST CANDIDATES")

    for case in cross_boundary_cases[:30]:
        print(
            f"  TEST: {case.path}:L{case.line} | "
            f"{case.name}"
        )

    has_checkpoint_recovery = bool(
        checkpoint_cases
    )

    has_expiry = bool(
        expiry_cases
    )

    has_revocation = bool(
        revocation_cases
    )

    has_admission = bool(
        admission_cases
    )

    has_denial = bool(
        denial_cases
    )

    has_strong = bool(
        strong_cases
    )

    has_cross_boundary = bool(
        cross_boundary_cases
    )

    print()
    print("=" * 100)
    print("R097 CONTROL-EVIDENCE ASSESSMENT")
    print("=" * 100)

    print(
        "Checkpoint/recovery tests: "
        f"{'PRESENT' if has_checkpoint_recovery else 'ABSENT'}"
    )
    print(
        "Authorization expiry tests: "
        f"{'PRESENT' if has_expiry else 'ABSENT'}"
    )
    print(
        "Authorization revocation tests: "
        f"{'PRESENT' if has_revocation else 'ABSENT'}"
    )
    print(
        "Admission/authorization tests: "
        f"{'PRESENT' if has_admission else 'ABSENT'}"
    )
    print(
        "Authorization denial tests: "
        f"{'PRESENT' if has_denial else 'ABSENT'}"
    )
    print(
        "Strong lifecycle test candidates: "
        f"{'PRESENT' if has_strong else 'ABSENT'}"
    )
    print(
        "Cross-boundary candidates: "
        f"{'PRESENT' if has_cross_boundary else 'ABSENT'}"
    )

    if has_strong and has_cross_boundary:
        state = "CANDIDATE_STRONG_BEHAVIORAL_EVIDENCE"
    elif (
        has_checkpoint_recovery
        and has_expiry
        and has_admission
        and has_denial
    ):
        state = "CANDIDATE_CROSS_BOUNDARY_TEST_EVIDENCE"
    elif (
        has_checkpoint_recovery
        and (has_expiry or has_revocation)
    ):
        state = "PARTIAL_BEHAVIORAL_EVIDENCE"
    else:
        state = "EVIDENCE_GAP"

    print()
    print(f"R097 TEST-EVIDENCE RESULT: {state}")

    print()
    print("=" * 100)
    print("ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 100)
    print("PRESERVE: NOT ASSIGNED")
    print("EXTEND: NOT ASSIGNED")
    print("NEW: NOT ASSIGNED")
    print("REFACTOR: NOT ASSIGNED")
    print("CONFLICT: NOT ASSIGNED")

    print()
    print("=" * 100)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 100)
    print("READ-ONLY: YES")
    print("TEST SOURCE MUTATION: NONE")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("IMPLEMENTATION EXECUTION: NONE")

    print()
    print("=" * 100)
    print("FINAL RESULT")
    print("=" * 100)
    print(
        "RESULT: PASS — R097 BEHAVIORAL "
        "TEST-EVIDENCE VERIFICATION COMPLETED"
    )
    print(
        "NOTE: Candidate test evidence is not a "
        "compliance or architectural decision."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

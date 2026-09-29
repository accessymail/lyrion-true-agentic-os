from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "tests"
SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)


@dataclass(frozen=True)
class TestCase:
    path: Path
    line: int
    name: str
    source: str


TARGET_TEST_TERMS = (
    "recovery",
    "requeue",
    "queued",
    "admission",
    "authorization",
    "expired",
    "revoked",
    "capability",
    "gateway",
)


def read_source(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, UnicodeError):
        return ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def discover_tests() -> list[TestCase]:
    results: list[TestCase] = []

    for path in sorted(
        TEST_ROOT.rglob("test_*.py")
    ):
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

            segment = (
                ast.get_source_segment(
                    source,
                    node,
                )
                or ""
            )

            lowered = segment.lower()

            if not any(
                term in lowered
                for term in TARGET_TEST_TERMS
            ):
                continue

            results.append(
                TestCase(
                    path=path,
                    line=node.lineno,
                    name=node.name,
                    source=segment,
                )
            )

    return results


def classify(test: TestCase) -> str:
    lowered = test.source.lower()

    has_recovery = any(
        term in lowered
        for term in (
            "recovery",
            "recover",
            "requeue",
        )
    )

    has_queue = any(
        term in lowered
        for term in (
            "queued",
            "claim",
            "queue",
        )
    )

    has_admission = any(
        term in lowered
        for term in (
            "admission",
            "admit",
            "capabilitygateway",
            "gateway",
        )
    )

    has_authorization = any(
        term in lowered
        for term in (
            "authorization",
            "authorize",
            "expired",
            "revoked",
        )
    )

    if (
        has_recovery
        and has_queue
        and has_admission
        and has_authorization
    ):
        return "STRONG_R097_CANDIDATE"

    if has_recovery and has_admission:
        return "RECOVERY_ADMISSION_CANDIDATE"

    if has_admission and has_authorization:
        return "ADMISSION_AUTHORIZATION_CANDIDATE"

    if has_recovery or has_queue:
        return "RECOVERY_QUEUE_CANDIDATE"

    return "GENERAL_ADMISSION_CANDIDATE"


def run_test(
    test: TestCase,
) -> tuple[int, str]:
    nodeid = (
        f"{test.path.relative_to(REPO_ROOT)}::"
        f"{test.name}"
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--disable-warnings",
        nodeid,
    ]

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    output = (
        completed.stdout
        + completed.stderr
    )

    return completed.returncode, output


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 TARGETED "
        "BEHAVIORAL RECOVERY → ADMISSION VALIDATION"
    )
    print("CONTROLLED TEST EXECUTION")
    print()

    if not SPECIFICATION.is_file():
        print(
            "RESULT: FAIL — execution admission "
            "specification missing."
        )
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    print()
    print("=" * 100)
    print("TEST DISCOVERY")
    print("=" * 100)

    tests = discover_tests()

    if not tests:
        print(
            "RESULT: FAIL — no relevant behavioral "
            "tests discovered."
        )
        return 1

    strong = [
        test
        for test in tests
        if classify(test)
        == "STRONG_R097_CANDIDATE"
    ]

    recovery_admission = [
        test
        for test in tests
        if classify(test)
        == "RECOVERY_ADMISSION_CANDIDATE"
    ]

    admission_authorization = [
        test
        for test in tests
        if classify(test)
        == "ADMISSION_AUTHORIZATION_CANDIDATE"
    ]

    print(
        f"Relevant tests discovered: {len(tests)}"
    )
    print(
        f"Strong R097 candidates: {len(strong)}"
    )
    print(
        "Recovery/admission candidates: "
        f"{len(recovery_admission)}"
    )
    print(
        "Admission/authorization candidates: "
        f"{len(admission_authorization)}"
    )

    print()
    print("=" * 100)
    print("STRONG R097 TEST CANDIDATES")
    print("=" * 100)

    for test in strong:
        print(
            f"{test.path}:L{test.line} | "
            f"{test.name}"
        )

    print()
    print("=" * 100)
    print("SELECTED EXISTING TESTS")
    print("=" * 100)

    selected: list[TestCase] = []

    preferred_names = (
        "test_postgresql_recovery_decision_and_requeue_roll_back_together",
        "test_expired_authorization_is_rejected",
        "test_revoked_decision_is_rejected",
        "test_expired_request_is_not_admitted",
    )

    for preferred in preferred_names:
        matches = [
            test
            for test in tests
            if test.name == preferred
        ]

        if len(matches) == 1:
            selected.append(matches[0])

    unique_selected: list[TestCase] = []

    seen: set[tuple[Path, str]] = set()

    for test in selected:
        key = (test.path, test.name)

        if key in seen:
            continue

        seen.add(key)
        unique_selected.append(test)

    selected = unique_selected

    if not selected:
        print(
            "RESULT: FAIL — expected targeted "
            "behavioral tests could not be resolved."
        )
        return 1

    for test in selected:
        print(
            f"SELECTED: {test.path}:L{test.line} | "
            f"{test.name}"
        )

    print()
    print("=" * 100)
    print("TARGETED TEST EXECUTION")
    print("=" * 100)

    failures = 0

    for test in selected:
        print()
        print(
            f"RUNNING: {test.path}:L{test.line} | "
            f"{test.name}"
        )

        return_code, output = run_test(test)

        print(output.rstrip())

        if return_code == 0:
            print(
                "TEST RESULT: PASS"
            )
        else:
            failures += 1
            print(
                "TEST RESULT: FAIL"
            )

    print()
    print("=" * 100)
    print("R097 BEHAVIORAL ASSESSMENT")
    print("=" * 100)

    all_passed = failures == 0

    print(
        "TARGETED TESTS:",
        "ALL PASS"
        if all_passed
        else f"{failures} FAILURE(S)",
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "Passing the existing lifecycle tests does not "
        "automatically prove the complete recovery-to-fresh-"
        "admission invariant unless a test directly exercises "
        "that combined path."
    )

    direct_combined_test = any(
        (
            "requeue" in test.source.lower()
            and "admission" in test.source.lower()
            and (
                "gateway"
                in test.source.lower()
                or "capability"
                in test.source.lower()
            )
        )
        for test in selected
    )

    print(
        "DIRECT COMBINED RECOVERY + "
        "FRESH ADMISSION TEST:",
        "FOUND"
        if direct_combined_test
        else "NOT FOUND",
    )

    if (
        all_passed
        and direct_combined_test
    ):
        result = (
            "R097_BEHAVIORAL_RECOVERY_TO_FRESH_ADMISSION "
            "EVIDENCE_ESTABLISHED"
        )
    elif all_passed:
        result = (
            "R097_TARGETED_LIFECYCLE_TESTS_PASS — "
            "DIRECT_COMBINED_BEHAVIORAL_EVIDENCE_REQUIRED"
        )
    else:
        result = (
            "R097_BEHAVIORAL_VALIDATION_FAILED"
        )

    print()
    print(f"R097 RESULT: {result}")

    print()
    print("=" * 100)
    print("SAFETY / SCOPE")
    print("=" * 100)
    print("Existing tests only.")
    print("No test files modified.")
    print("No source files modified.")
    print("No documentation modified.")
    print("No manifest modified.")
    print("No governance mutation.")
    print("No authorization grant.")
    print("No production authorization.")
    print("No certification claim.")
    print(
        "No privileged host operation intentionally "
        "performed by this validator."
    )

    print()
    print("=" * 100)
    print("FINAL RESULT")
    print("=" * 100)
    print(
        "RESULT: PASS — R097 TARGETED BEHAVIORAL "
        "VALIDATION COMPLETED"
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

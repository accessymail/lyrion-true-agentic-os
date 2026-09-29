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

TARGETS = (
    (
        REPO_ROOT
        / "tests/integration/test_postgresql_recovery_orchestrator.py",
        "test_postgresql_recovery_decision_and_requeue_roll_back_together",
    ),
    (
        REPO_ROOT
        / "tests/unit/test_aegis_guards.py",
        "test_expired_authorization_is_rejected",
    ),
    (
        REPO_ROOT
        / "tests/unit/test_aegis_guards.py",
        "test_revoked_decision_is_rejected",
    ),
    (
        REPO_ROOT
        / "tests/unit/test_capability_gateway.py",
        "test_expired_request_is_not_admitted",
    ),
)


@dataclass(frozen=True)
class TestEvidence:
    path: Path
    line: int
    name: str
    source: str
    calls: tuple[str, ...]
    assertions: tuple[str, ...]
    lifecycle_terms: tuple[str, ...]


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


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node.func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ast.unparse(node.func)


def collect_calls(tree: ast.AST) -> tuple[str, ...]:
    calls = {
        call_name(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }

    return tuple(sorted(calls))


def collect_assertions(tree: ast.AST) -> tuple[str, ...]:
    assertions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            assertions.append(
                ast.unparse(node.test)
            )

        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr.startswith("assert")
        ):
            assertions.append(
                ast.unparse(node)
            )

    return tuple(assertions)


def collect_lifecycle_terms(
    source: str,
) -> tuple[str, ...]:
    terms = (
        "checkpoint",
        "recovery",
        "recover",
        "authorization",
        "authority",
        "admission",
        "expiry",
        "expired",
        "revok",
        "revoke",
        "denied",
        "deny",
        "reject",
        "fail",
        "rollback",
        "requeue",
        "assert",
    )

    lowered = source.lower()

    return tuple(
        term
        for term in terms
        if term in lowered
    )


def locate_test(
    path: Path,
    test_name: str,
) -> TestEvidence | None:
    source = read_source(path)

    if not source:
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        if node.name != test_name:
            continue

        segment = ast.get_source_segment(
            source,
            node,
        ) or ""

        try:
            body_tree = ast.parse(segment)
        except SyntaxError:
            return None

        return TestEvidence(
            path=path,
            line=node.lineno,
            name=node.name,
            source=segment,
            calls=collect_calls(body_tree),
            assertions=collect_assertions(body_tree),
            lifecycle_terms=collect_lifecycle_terms(segment),
        )

    return None


def direct_file_dependencies(
    test: TestEvidence,
) -> tuple[str, ...]:
    source = test.source.lower()

    dependencies: list[str] = []

    mappings = (
        (
            "checkpoint",
            "src/lyrion/execution/checkpoint.py",
        ),
        (
            "recovery",
            "src/lyrion/persistence/recovery.py",
        ),
        (
            "authorization",
            "src/lyrion/security/authorization.py",
        ),
        (
            "aegis",
            "src/lyrion/security/",
        ),
        (
            "capabilitygateway",
            "src/lyrion/capabilities/gateway.py",
        ),
        (
            "admission",
            "src/lyrion/capabilities/gateway.py",
        ),
    )

    for token, path in mappings:
        if token in source:
            dependencies.append(path)

    return tuple(sorted(set(dependencies)))


def classify(
    test: TestEvidence,
) -> str:
    terms = set(test.lifecycle_terms)
    calls = " ".join(test.calls).lower()

    has_recovery = bool(
        {"recovery", "recover", "rollback", "requeue"} & terms
    )
    has_checkpoint = "checkpoint" in terms
    has_authority = bool(
        {"authorization", "authority", "aegis"} & terms
    )
    has_expiry = bool(
        {"expiry", "expired"} & terms
    )
    has_revocation = bool(
        {"revok", "revoke"} & terms
    )
    has_admission = "admission" in terms
    has_denial = bool(
        {"denied", "deny", "reject", "fail"} & terms
    )
    has_assertion = bool(test.assertions)

    direct_authority_call = any(
        token in calls
        for token in (
            "authorize",
            "is_authorized",
            "evaluate",
            "admit",
            "gateway.admit",
        )
    )

    if (
        has_recovery
        and has_checkpoint
        and has_authority
        and (has_expiry or has_revocation)
        and has_admission
        and has_denial
        and has_assertion
    ):
        return "STRONG_RECOVERY_AUTHORITY_LIFECYCLE_CANDIDATE"

    if (
        has_authority
        and (has_expiry or has_revocation)
        and has_denial
        and has_assertion
        and (direct_authority_call or has_admission)
    ):
        return "DIRECT_AUTHORITY_LIFECYCLE_EVIDENCE"

    if (
        has_recovery
        and has_checkpoint
        and has_assertion
    ):
        return "RECOVERY_CHECKPOINT_EVIDENCE"

    return "INSUFFICIENT_FOR_R097"


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 TARGETED TEST "
        "CONTROL-FLOW VERIFICATION"
    )
    print("READ-ONLY")
    print()

    if not SPECIFICATION.is_file():
        print("RESULT: FAIL — specification missing.")
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    print()
    print("=" * 100)
    print("TARGETED TESTS")
    print("=" * 100)

    results: list[tuple[TestEvidence, str]] = []

    for path, test_name in TARGETS:
        print()
        print("-" * 100)
        print(f"TARGET: {path}")
        print(f"TEST:   {test_name}")

        if not path.is_file():
            print("STATUS: MISSING TEST FILE")
            continue

        evidence = locate_test(
            path,
            test_name,
        )

        if evidence is None:
            print("STATUS: TEST CASE NOT RESOLVED")
            continue

        classification = classify(evidence)
        results.append(
            (evidence, classification)
        )

        print(
            f"RESOLVED: {evidence.path}:L"
            f"{evidence.line}"
        )

        print()
        print("LIFECYCLE TERMS:")
        print(
            "  "
            + (
                ", ".join(evidence.lifecycle_terms)
                if evidence.lifecycle_terms
                else "NONE"
            )
        )

        print()
        print("DIRECT CALLS:")

        for call in evidence.calls:
            print(f"  CALL: {call}")

        if not evidence.calls:
            print("  CALL: NONE")

        print()
        print("ASSERTIONS:")

        for assertion in evidence.assertions:
            print(f"  ASSERT: {assertion}")

        if not evidence.assertions:
            print("  ASSERT: NONE")

        print()
        print("DIRECT IMPLEMENTATION DEPENDENCIES:")

        dependencies = direct_file_dependencies(
            evidence
        )

        for dependency in dependencies:
            print(f"  DEPENDENCY: {dependency}")

        if not dependencies:
            print("  DEPENDENCY: NONE")

        print()
        print(f"CONTROL-FLOW CLASSIFICATION: {classification}")

    print()
    print("=" * 100)
    print("R097 TARGETED CONTROL-FLOW ASSESSMENT")
    print("=" * 100)

    strong = [
        evidence
        for evidence, classification in results
        if classification
        == "STRONG_RECOVERY_AUTHORITY_LIFECYCLE_CANDIDATE"
    ]

    direct = [
        evidence
        for evidence, classification in results
        if classification
        == "DIRECT_AUTHORITY_LIFECYCLE_EVIDENCE"
    ]

    recovery = [
        evidence
        for evidence, classification in results
        if classification
        == "RECOVERY_CHECKPOINT_EVIDENCE"
    ]

    print(
        "Strong recovery-authority candidates: "
        f"{len(strong)}"
    )
    print(
        "Direct authority lifecycle tests: "
        f"{len(direct)}"
    )
    print(
        "Recovery/checkpoint tests: "
        f"{len(recovery)}"
    )
    print(
        "Resolved target tests: "
        f"{len(results)}/{len(TARGETS)}"
    )

    if strong:
        state = (
            "CANDIDATE_DIRECT_RECOVERY_AUTHORITY_CONTROL_FLOW"
        )
    elif direct and recovery:
        state = (
            "PARTIAL_RECOVERY_AUTHORITY_CONTROL_FLOW"
        )
    elif recovery:
        state = "RECOVERY_CONTROL_FLOW_ONLY"
    else:
        state = "INSUFFICIENT_CONTROL_FLOW_EVIDENCE"

    print()
    print(
        "R097 TARGETED RESULT: "
        f"{state}"
    )

    print()
    print("=" * 100)
    print("IMPORTANT EVIDENCE LIMIT")
    print("=" * 100)
    print(
        "This verifier analyzes existing test bodies, "
        "calls, and assertions."
    )
    print(
        "It does NOT execute the target tests."
    )
    print(
        "It does NOT prove runtime behavior."
    )
    print(
        "It does NOT classify architecture."
    )

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
        "RESULT: PASS — R097 TARGETED TEST "
        "CONTROL-FLOW VERIFICATION COMPLETED"
    )
    print(
        "NOTE: Control-flow evidence is not a "
        "compliance or architectural decision."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

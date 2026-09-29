from __future__ import annotations

import ast
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

RECOVERY_ORCHESTRATOR = (
    REPO_ROOT
    / "src/lyrion/persistence/recovery_orchestrator.py"
)

RECOVERY_MANAGER = (
    REPO_ROOT
    / "src/lyrion/persistence/recovery.py"
)

SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)


@dataclass(frozen=True)
class MethodInfo:
    class_name: str
    method_name: str
    line: int
    source: str
    calls: tuple[str, ...]


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


def collect_calls(
    node: ast.AST,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                call_name(item)
                for item in ast.walk(node)
                if isinstance(item, ast.Call)
            }
        )
    )


def find_method(
    path: Path,
    class_name: str,
    method_name: str,
) -> MethodInfo | None:
    source = read_source(path)

    if not source:
        return None

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        if node.name != class_name:
            continue

        for child in node.body:
            if not isinstance(
                child,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                continue

            if child.name != method_name:
                continue

            segment = (
                ast.get_source_segment(
                    source,
                    child,
                )
                or ""
            )

            return MethodInfo(
                class_name=class_name,
                method_name=method_name,
                line=child.lineno,
                source=segment,
                calls=collect_calls(child),
            )

    return None


def security_evidence(
    method: MethodInfo,
) -> list[tuple[int, list[str], str]]:
    terms = (
        "authorization",
        "authorize",
        "authority",
        "is_authorized",
        "authorizationdecision",
        "authorizationguard",
        "aegis",
        "admission",
        "admit",
        "capabilitygateway",
        "executionadmission",
        "expired",
        "expiry",
        "expires_at",
        "revoked",
        "revoke",
        "replay",
        "revalidate",
        "re-validation",
        "validate",
        "denied",
        "deny",
        "reject",
        "fail_closed",
        "fail-closed",
    )

    results: list[tuple[int, list[str], str]] = []

    for number, line in enumerate(
        method.source.splitlines(),
        start=method.line,
    ):
        lowered = line.lower()

        matches = [
            term
            for term in terms
            if term in lowered
        ]

        if matches:
            results.append(
                (
                    number,
                    matches,
                    line.strip(),
                )
            )

    return results


def print_method(
    title: str,
    method: MethodInfo,
) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(
        f"RESOLVED: {method.class_name}."
        f"{method.method_name}"
    )
    print(
        f"LOCATION: "
        f"{method.class_name}.{method.method_name}"
        f"():L{method.line}"
    )

    print()
    print("CALLS:")

    for call in method.calls:
        print(f"  {call}")

    print()
    print("SOURCE BODY:")

    for number, line in enumerate(
        method.source.splitlines(),
        start=method.line,
    ):
        print(f"L{number}: {line}")

    print()
    print("SECURITY / AUTHORITY EVIDENCE:")

    evidence = security_evidence(method)

    if not evidence:
        print(
            "  NONE — no direct authority/"
            "authorization/admission lifecycle terms."
        )
    else:
        for number, terms, line in evidence:
            print(
                f"  L{number}: terms={terms} | {line}"
            )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 RECOVERY MANAGER "
        "CONTROL-FLOW TRACE"
    )
    print("READ-ONLY")
    print()

    required = (
        SPECIFICATION,
        RECOVERY_ORCHESTRATOR,
        RECOVERY_MANAGER,
    )

    missing = [
        path
        for path in required
        if not path.is_file()
    ]

    if missing:
        print(
            "RESULT: FAIL — required evidence file missing."
        )

        for path in missing:
            print(f"  MISSING: {path}")

        return 1

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    recover_one = find_method(
        RECOVERY_ORCHESTRATOR,
        "PersistentRecoveryOrchestrator",
        "recover_one",
    )

    decide = find_method(
        RECOVERY_MANAGER,
        "RecoveryManager",
        "decide",
    )

    decision = find_method(
        RECOVERY_MANAGER,
        "RecoveryManager",
        "_decision",
    )

    if recover_one is None:
        print(
            "RESULT: FAIL — recover_one was not resolved."
        )
        return 1

    if decide is None:
        print(
            "RESULT: FAIL — RecoveryManager.decide "
            "was not resolved."
        )
        return 1

    if decision is None:
        print(
            "RESULT: FAIL — RecoveryManager._decision "
            "was not resolved."
        )
        return 1

    print_method(
        "RECOVERY ENTRYPOINT — recover_one()",
        recover_one,
    )

    print_method(
        "RECOVERY DECISION — RecoveryManager.decide()",
        decide,
    )

    print_method(
        "RECOVERY DECISION CORE — RecoveryManager._decision()",
        decision,
    )

    print()
    print("=" * 100)
    print("R097 CONTROL-FLOW QUESTIONS")
    print("=" * 100)

    recover_calls_decide = any(
        call.endswith("decide")
        or call == "self._manager.decide"
        for call in recover_one.calls
    )

    decide_calls_decision = any(
        call.endswith("_decision")
        or call == "self._decision"
        for call in decide.calls
    )

    manager_evidence = (
        security_evidence(decide)
        + security_evidence(decision)
    )

    manager_terms = {
        term
        for _, terms, _ in manager_evidence
        for term in terms
    }

    authority_terms = {
        "authorization",
        "authorize",
        "authority",
        "is_authorized",
        "authorizationdecision",
        "authorizationguard",
        "aegis",
        "capabilitygateway",
        "executionadmission",
        "admission",
        "admit",
    }

    lifecycle_terms = {
        "expired",
        "expiry",
        "expires_at",
        "revoked",
        "revoke",
        "replay",
        "revalidate",
        "re-validation",
    }

    found_authority = bool(
        manager_terms & authority_terms
    )

    found_lifecycle = bool(
        manager_terms & lifecycle_terms
    )

    print(
        "recover_one() → RecoveryManager.decide(): "
        f"{'YES' if recover_calls_decide else 'NO'}"
    )

    print(
        "RecoveryManager.decide() → _decision(): "
        f"{'YES' if decide_calls_decision else 'NO'}"
    )

    print(
        "RecoveryManager contains authority/admission "
        "references: "
        f"{'YES' if found_authority else 'NO'}"
    )

    print(
        "RecoveryManager contains authority lifecycle "
        "references: "
        f"{'YES' if found_lifecycle else 'NO'}"
    )

    if manager_terms:
        print()
        print("Detected control terms:")

        for term in sorted(manager_terms):
            print(f"  {term}")

    print()
    print("=" * 100)
    print("R097 EVIDENCE INTERPRETATION")
    print("=" * 100)

    if (
        recover_calls_decide
        and decide_calls_decision
        and found_authority
        and found_lifecycle
    ):
        result = (
            "AUTHORITY_LIFECYCLE_CONTROL_PRESENT — "
            "DEEP DOWNSTREAM TRACE REQUIRED"
        )
    elif (
        recover_calls_decide
        and decide_calls_decision
        and found_authority
    ):
        result = (
            "AUTHORITY_REFERENCE_PRESENT — "
            "LIFECYCLE REVALIDATION NOT ESTABLISHED"
        )
    elif (
        recover_calls_decide
        and decide_calls_decision
    ):
        result = (
            "RECOVERY_DECISION_CHAIN_PRESENT — "
            "NO AUTHORITY REVALIDATION ESTABLISHED"
        )
    else:
        result = (
            "RECOVERY_MANAGER_CONTROL_FLOW "
            "NOT FULLY ESTABLISHED"
        )

    print(f"R097 RESULT: {result}")

    print()
    print("=" * 100)
    print("EVIDENCE LIMITS")
    print("=" * 100)
    print(
        "This verifier performs static AST/source inspection."
    )
    print(
        "It does NOT execute recovery behavior."
    )
    print(
        "It does NOT prove runtime authorization behavior."
    )
    print(
        "It does NOT modify source, tests, documentation, "
        "manifests, or governance."
    )
    print(
        "It does NOT grant authorization."
    )
    print(
        "It does NOT classify PRESERVE/EXTEND/NEW/"
        "REFACTOR/CONFLICT."
    )

    print()
    print("=" * 100)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 100)
    print("READ-ONLY: YES")
    print("SOURCE MUTATION: NONE")
    print("TEST MUTATION: NONE")
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
        "RESULT: PASS — R097 RECOVERY MANAGER "
        "CONTROL-FLOW TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

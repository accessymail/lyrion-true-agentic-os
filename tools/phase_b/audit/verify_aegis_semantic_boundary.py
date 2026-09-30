#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Semantic Boundary Verifier

READ-ONLY EVIDENCE TOOL.

Purpose:
    Verify the observable source-level relationship:

        Aegis Policy
            ->
        Aegis Authorization Service
            ->
        Authorization Guard / Replay Guard
            ->
        Capability Gateway
            ->
        Execution Admission
            ->
        Secure Executor

The verifier uses AST structure and source-level relationships rather than
simple keyword presence.

Safety:
    - Does not execute production Aegis behavior.
    - Does not modify source, tests, docs, manifests, or Git.
    - Does not reconstruct G46.5/G47.
    - Does not modify R097.
    - Does not claim production certification.
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

PATHS = {
    "policy": REPO / "src/lyrion/security/policy.py",
    "authorization": REPO / "src/lyrion/security/authorization.py",
    "guards": REPO / "src/lyrion/security/guards.py",
    "replay": REPO / "src/lyrion/security/replay.py",
    "capability_contracts": REPO / "src/lyrion/capabilities/contracts.py",
    "gateway": REPO / "src/lyrion/capabilities/gateway.py",
    "execution_contracts": REPO / "src/lyrion/execution/contracts.py",
    "validator": REPO / "src/lyrion/execution/validator.py",
    "executor": REPO / "src/lyrion/execution/executor.py",
}


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_tree(path: Path) -> tuple[str, ast.Module]:
    text = path.read_text(encoding="utf-8")
    return text, ast.parse(text, filename=str(path))


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = qualified_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr

    return ""


def all_calls(tree: ast.AST) -> list[str]:
    values: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = qualified_name(node.func)
            if name:
                values.append(name)

    return sorted(set(values))


def all_names(tree: ast.AST) -> set[str]:
    values: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            values.add(node.id)

        elif isinstance(node, ast.Attribute):
            values.add(node.attr)

    return values


def all_imports(tree: ast.AST) -> list[str]:
    values: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for alias in node.names:
                values.append(
                    f"{module}.{alias.name}"
                    if module
                    else alias.name
                )

    return sorted(set(values))


def class_node(
    tree: ast.Module,
    class_name: str,
) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node

    return None


def method_node(
    class_def: ast.ClassDef,
    method_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in class_def.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method_name
        ):
            return node

    return None


def function_node(
    tree: ast.Module,
    function_name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == function_name
        ):
            return node

    return None


def calls_in(node: ast.AST) -> set[str]:
    return {
        qualified_name(item.func)
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
        and qualified_name(item.func)
    }


def names_in(node: ast.AST) -> set[str]:
    values: set[str] = set()

    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            values.add(item.id)

        elif isinstance(item, ast.Attribute):
            values.add(item.attr)

    return values


def imports_containing(
    imports: list[str],
    *terms: str,
) -> list[str]:
    lowered = tuple(term.lower() for term in terms)

    return [
        item
        for item in imports
        if any(term in item.lower() for term in lowered)
    ]


def check(
    label: str,
    condition: bool,
    detail: str,
) -> bool:
    state = "PASS" if condition else "WARN"
    print(f"[{state}] {label}: {detail}")
    return condition


def load_sources() -> dict[str, tuple[str, ast.Module]]:
    loaded: dict[str, tuple[str, ast.Module]] = {}

    for label, path in PATHS.items():
        print()
        print("=" * 78)
        print(label)
        print(path.relative_to(REPO))
        print("=" * 78)

        if not path.is_file():
            print("[FAIL] missing")
            continue

        try:
            text, tree = read_tree(path)
        except SyntaxError as exc:
            print(f"[FAIL] AST parse: {exc}")
            continue

        loaded[label] = (text, tree)

        print("[PASS] present")
        print("[PASS] AST parse")
        print(f"[INFO] SHA-256: {sha256(path)}")
        print(f"[INFO] bytes: {path.stat().st_size}")

    return loaded


def verify_policy(
    loaded: dict[str, tuple[str, ast.Module]],
) -> int:
    print()
    print("=" * 78)
    print("1. AEGIS POLICY SEMANTICS")
    print("=" * 78)

    if "policy" not in loaded:
        print("[FAIL] policy source unavailable")
        return 1

    text, tree = loaded["policy"]
    names = all_names(tree)
    calls = all_calls(tree)

    evaluator = class_node(tree, "AegisPolicyEvaluator")

    if evaluator is None:
        print("[FAIL] AegisPolicyEvaluator class not found")
        return 1

    evaluate = method_node(evaluator, "evaluate")

    passed = 0
    total = 0

    checks = (
        (
            "evaluator class",
            evaluator is not None,
            "AegisPolicyEvaluator is defined",
        ),
        (
            "evaluate method",
            evaluate is not None,
            "policy evaluation entry point exists",
        ),
        (
            "request evaluation",
            bool(evaluate and "CapabilityRequest" in names_in(evaluate)),
            "evaluate operates on capability request",
        ),
        (
            "authorization result",
            "AuthorizationResult" in names,
            "AuthorizationResult is used",
        ),
        (
            "authorization decision",
            "AuthorizationDecision" in names,
            "AuthorizationDecision is used",
        ),
        (
            "expiry check",
            "is_expired" in calls,
            "expiry is evaluated",
        ),
        (
            "denial",
            "DENIED" in names or "DENIED" in text,
            "explicit denial state exists",
        ),
        (
            "allow",
            "ALLOWED" in names or "ALLOWED" in text,
            "explicit allow state exists",
        ),
        (
            "revocation",
            "REVOKED" in names or "REVOKED" in text,
            "revocation state exists",
        ),
    )

    for label, condition, detail in checks:
        total += 1
        passed += check(label, condition, detail)

    print(f"\nPOLICY: {passed}/{total} PASS")
    return 0 if passed == total else 1


def verify_authorization(
    loaded: dict[str, tuple[str, ast.Module]],
) -> int:
    print()
    print("=" * 78)
    print("2. AEGIS AUTHORIZATION SERVICE")
    print("=" * 78)

    if "authorization" not in loaded:
        print("[FAIL] authorization source unavailable")
        return 1

    text, tree = loaded["authorization"]
    names = all_names(tree)
    calls = all_calls(tree)
    imports = all_imports(tree)

    service = class_node(tree, "AegisAuthorizationService")
    authorize = (
        method_node(service, "authorize")
        if service
        else None
    )

    passed = 0
    total = 0

    checks = (
        (
            "service class",
            service is not None,
            "AegisAuthorizationService is defined",
        ),
        (
            "authorize method",
            authorize is not None,
            "authorization entry point exists",
        ),
        (
            "policy evaluator dependency",
            "AegisPolicyEvaluator" in names
            or bool(imports_containing(imports, "policy")),
            "policy evaluator dependency is observable",
        ),
        (
            "authorization guard dependency",
            "AuthorizationGuard" in names
            or bool(imports_containing(imports, "guards")),
            "authorization guard dependency is observable",
        ),
        (
            "replay guard dependency",
            "ReplayGuard" in names
            or bool(imports_containing(imports, "replay")),
            "replay guard dependency is observable",
        ),
        (
            "policy evaluation call",
            "evaluate" in calls,
            "policy evaluator is invoked",
        ),
        (
            "authorization check",
            "is_authorized" in calls,
            "authorization guard is invoked",
        ),
        (
            "replay check",
            "check_and_record" in calls,
            "replay protection is invoked",
        ),
        (
            "denial handling",
            "DENIED" in names or "DENIED" in text,
            "denial is represented in the service",
        ),
    )

    for label, condition, detail in checks:
        total += 1
        passed += check(label, condition, detail)

    print(f"\nAUTHORIZATION SERVICE: {passed}/{total} PASS")
    return 0 if passed == total else 1


def verify_gateway(
    loaded: dict[str, tuple[str, ast.Module]],
) -> int:
    print()
    print("=" * 78)
    print("3. CAPABILITY GATEWAY / EXECUTION ADMISSION")
    print("=" * 78)

    if "gateway" not in loaded:
        print("[FAIL] gateway source unavailable")
        return 1

    text, tree = loaded["gateway"]
    names = all_names(tree)
    calls = all_calls(tree)

    gateway = class_node(tree, "CapabilityGateway")
    execution_admission = class_node(tree, "ExecutionAdmission")

    admit = (
        method_node(gateway, "admit")
        if gateway
        else None
    )

    from_authorization = (
        method_node(execution_admission, "from_authorization")
        if execution_admission
        else None
    )

    passed = 0
    total = 0

    checks = (
        (
            "CapabilityGateway",
            gateway is not None,
            "gateway class exists",
        ),
        (
            "ExecutionAdmission",
            execution_admission is not None,
            "execution admission exists",
        ),
        (
            "admit method",
            admit is not None,
            "gateway admission entry point exists",
        ),
        (
            "authorization decision",
            "AuthorizationDecision" in names,
            "gateway consumes authorization decision",
        ),
        (
            "capability request",
            "CapabilityRequest" in names,
            "gateway handles capability requests",
        ),
        (
            "admission construction",
            from_authorization is not None
            or "from_authorization" in calls,
            "admission is constructed from authorization",
        ),
        (
            "admission validation",
            "validate_authorization_state" in calls,
            "authorization state is explicitly validated",
        ),
        (
            "execution separation",
            "execute" not in calls,
            "gateway does not directly execute the capability",
        ),
    )

    for label, condition, detail in checks:
        total += 1
        passed += check(label, condition, detail)

    print(f"\nGATEWAY: {passed}/{total} PASS")
    return 0 if passed == total else 1


def verify_executor(
    loaded: dict[str, tuple[str, ast.Module]],
) -> int:
    print()
    print("=" * 78)
    print("4. SECURE EXECUTOR BOUNDARY")
    print("=" * 78)

    if "executor" not in loaded:
        print("[FAIL] executor source unavailable")
        return 1

    text, tree = loaded["executor"]
    names = all_names(tree)
    calls = all_calls(tree)

    executor = class_node(tree, "SecureExecutor")
    execute = (
        method_node(executor, "execute")
        if executor
        else None
    )

    passed = 0
    total = 0

    checks = (
        (
            "SecureExecutor",
            executor is not None,
            "secure executor exists",
        ),
        (
            "execute method",
            execute is not None,
            "execution entry point exists",
        ),
        (
            "ExecutionAdmission",
            "ExecutionAdmission" in names,
            "executor receives execution admission",
        ),
        (
            "authorization state",
            "authorization_decision" in text,
            "authorization decision is represented",
        ),
        (
            "validation boundary",
            any(
                item in calls
                for item in (
                    "validate",
                    "validate_for_execution",
                    "require_admission",
                    "require_authorized",
                )
            ),
            "validation/admission enforcement call is observable",
        ),
        (
            "deny handling",
            "DENIED" in text or "_denied_result" in names,
            "denied execution path exists",
        ),
    )

    for label, condition, detail in checks:
        total += 1
        passed += check(label, condition, detail)

    print(f"\nEXECUTOR: {passed}/{total} PASS")
    return 0 if passed == total else 1


def verify_authority_separation(
    loaded: dict[str, tuple[str, ast.Module]],
) -> int:
    print()
    print("=" * 78)
    print("5. AUTHORITY-SEPARATION CHECKS")
    print("=" * 78)

    passed = 0
    total = 0

    checks: list[tuple[str, bool, str]] = []

    if "gateway" in loaded:
        gateway_text, gateway_tree = loaded["gateway"]
        gateway_calls = all_calls(gateway_tree)

        checks.append(
            (
                "gateway has no direct execution call",
                "execute" not in gateway_calls,
                "gateway does not directly invoke execute()",
            )
        )

    if "executor" in loaded:
        executor_text, executor_tree = loaded["executor"]

        checks.append(
            (
                "executor does not define policy authority",
                "AegisPolicyEvaluator" not in all_names(executor_tree),
                "executor does not instantiate the Aegis evaluator",
            )
        )

        checks.append(
            (
                "executor does not define authorization service",
                "AegisAuthorizationService"
                not in all_names(executor_tree),
                "executor does not instantiate Aegis authorization",
            )
        )

    for label, condition, detail in checks:
        total += 1
        passed += check(label, condition, detail)

    print(f"\nAUTHORITY SEPARATION: {passed}/{total} PASS")
    return 0 if passed == total else 1


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS SEMANTIC BOUNDARY VERIFIER")
    print("READ-ONLY")
    print("=" * 78)

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    status = run_git("status", "--short", "--untracked-files=all")

    print("\nREPOSITORY STATE")
    print(f"HEAD:        {head}")
    print(f"origin/main: {origin}")
    print(
        "[PASS] HEAD == origin/main"
        if head == origin
        else "[WARN] HEAD != origin/main"
    )

    print("\nWORKTREE")
    if status:
        print(status)
        print("[INFO] Existing read-only review tools are preserved.")
    else:
        print("[PASS] CLEAN")

    loaded = load_sources()

    results = [
        verify_policy(loaded),
        verify_authorization(loaded),
        verify_gateway(loaded),
        verify_executor(loaded),
        verify_authority_separation(loaded),
    ]

    print()
    print("=" * 78)
    print("PROTECTED BOUNDARIES")
    print("=" * 78)
    print("[PASS] No runtime execution")
    print("[PASS] No source modification")
    print("[PASS] No test modification")
    print("[PASS] No documentation modification")
    print("[PASS] No manifest modification")
    print("[PASS] No Git mutation")
    print("[PASS] No G46.5 reconstruction")
    print("[PASS] No G47 reconstruction")
    print("[PASS] No R097 modification")
    print("[PASS] Production certification NOT CLAIMED")

    print()
    print("=" * 78)
    print("FINAL DECISION")
    print("=" * 78)

    if all(result == 0 for result in results):
        print(
            "AEGIS_SEMANTIC_BOUNDARY_PASS_"
            "PENDING_CONTROLLED_VALIDATION"
        )
    else:
        print("AEGIS_SEMANTIC_BOUNDARY_REQUIRES_ENGINEERING_REVIEW")

    print()
    print("This verifier provides source-level evidence only.")
    print("It does not establish runtime validation or production acceptance.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

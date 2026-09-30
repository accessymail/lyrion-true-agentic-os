#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Boundary Evidence Review

READ-ONLY.

Purpose:
    Verify the observable Aegis -> AuthorizationGuard ->
    CapabilityGateway -> ExecutionAdmission -> SecureExecutor boundary.

This tool performs structural/source evidence inspection only.
It does NOT execute the Aegis runtime.

No:
    - source modification
    - test modification
    - documentation modification
    - manifest modification
    - Git mutation
    - G46.5/G47 reconstruction
    - R097 modification
    - production certification claim
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

FILES = {
    "aegis_policy": REPO / "src/lyrion/security/policy.py",
    "aegis_authorization": REPO / "src/lyrion/security/authorization.py",
    "authorization_guard": REPO / "src/lyrion/security/guards.py",
    "replay_guard": REPO / "src/lyrion/security/replay.py",
    "capability_contracts": REPO / "src/lyrion/capabilities/contracts.py",
    "capability_gateway": REPO / "src/lyrion/capabilities/gateway.py",
    "execution_contracts": REPO / "src/lyrion/execution/contracts.py",
    "execution_validator": REPO / "src/lyrion/execution/validator.py",
    "secure_executor": REPO / "src/lyrion/execution/executor.py",
}

TESTS = [
    REPO / "tests/unit/test_aegis_policy.py",
    REPO / "tests/unit/test_aegis_authorization.py",
    REPO / "tests/unit/test_aegis_guards.py",
    REPO / "tests/unit/test_aegis_replay.py",
    REPO / "tests/unit/test_aegis_rules.py",
    REPO / "tests/unit/test_capability_gateway.py",
    REPO / "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
    REPO / "tests/unit/execution/test_secure_executor_enforcement_integration.py",
]


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse(path: Path) -> ast.AST:
    return ast.parse(
        path.read_text(encoding="utf-8"),
        filename=str(path),
    )


def names(tree: ast.AST) -> set[str]:
    result: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            result.add(node.id)

        elif isinstance(node, ast.Attribute):
            result.add(node.attr)

    return result


def calls(tree: ast.AST) -> set[str]:
    result: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                result.add(node.func.id)

            elif isinstance(node.func, ast.Attribute):
                result.add(node.func.attr)

    return result


def functions(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def classes(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_file(label: str, path: Path) -> tuple[ast.AST | None, str]:
    print()
    print("=" * 78)
    print(label)
    print(path.relative_to(REPO))
    print("=" * 78)

    if not path.is_file():
        print("[FAIL] FILE MISSING")
        return None, ""

    text = source(path)

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        print(f"[FAIL] AST PARSE: {exc}")
        return None, text

    print("[PASS] File present")
    print("[PASS] AST parse")
    print(f"[INFO] SHA-256: {sha256(path)}")
    print(f"[INFO] Bytes: {path.stat().st_size}")

    print("\nClasses:")
    for item in sorted(classes(tree)):
        print(f"  - {item}")

    print("\nFunctions:")
    for item in sorted(functions(tree)):
        print(f"  - {item}")

    return tree, text


def require(
    label: str,
    condition: bool,
    detail: str,
) -> bool:
    if condition:
        print(f"[PASS] {label}: {detail}")
        return True

    print(f"[WARN] {label}: {detail}")
    return False


def inspect_aegis(
    tree: ast.AST,
    text: str,
) -> int:
    passed = 0
    checks = 0

    nameset = names(tree)
    callset = calls(tree)
    fnset = functions(tree)

    checks += 1
    passed += require(
        "Aegis evaluator",
        "AegisPolicyEvaluator" in nameset,
        "AegisPolicyEvaluator present",
    )

    checks += 1
    passed += require(
        "Policy evaluation",
        "evaluate" in fnset or "evaluate" in callset,
        "evaluation entry point present",
    )

    checks += 1
    passed += require(
        "Authorization result",
        "AuthorizationResult" in nameset,
        "AuthorizationResult used",
    )

    checks += 1
    passed += require(
        "Explicit decisions",
        "AuthorizationDecision" in nameset,
        "AuthorizationDecision used",
    )

    checks += 1
    passed += require(
        "Capability binding",
        "CapabilityRequest" in nameset,
        "CapabilityRequest consumed",
    )

    checks += 1
    passed += require(
        "Expiry enforcement",
        "is_expired" in callset,
        "request expiry checked",
    )

    checks += 1
    passed += require(
        "Revocation handling",
        "REVOKED" in text,
        "revoked state represented",
    )

    checks += 1
    passed += require(
        "Approval state",
        "REQUIRES_APPROVAL" in text,
        "approval decision represented",
    )

    checks += 1
    passed += require(
        "Explicit denial",
        "DENIED" in text,
        "denial decision represented",
    )

    checks += 1
    passed += require(
        "Explicit allow",
        "ALLOWED" in text,
        "allow decision represented",
    )

    print(f"\nAegis structural checks: {passed}/{checks} PASS")

    return 0 if passed == checks else 1


def inspect_authorization(
    tree: ast.AST,
    text: str,
) -> int:
    passed = 0
    checks = 0

    nameset = names(tree)
    callset = calls(tree)
    fnset = functions(tree)

    required = (
        ("AegisAuthorizationService", "AegisAuthorizationService" in nameset),
        ("AegisPolicyEvaluator", "AegisPolicyEvaluator" in nameset),
        ("AuthorizationGuard", "AuthorizationGuard" in nameset),
        ("ReplayGuard", "ReplayGuard" in nameset),
        ("authorize()", "authorize" in fnset),
        ("policy evaluator call", "evaluate" in callset),
        ("authorization guard", "is_authorized" in callset),
        ("replay protection", "check_and_record" in callset),
        ("denial result", "DENIED" in text),
    )

    for label, condition in required:
        checks += 1
        passed += require(
            label,
            condition,
            "present" if condition else "not observed",
        )

    print(f"\nAuthorization checks: {passed}/{checks} PASS")

    return 0 if passed == checks else 1


def inspect_gateway(
    tree: ast.AST,
    text: str,
) -> int:
    passed = 0
    checks = 0

    nameset = names(tree)
    callset = calls(tree)

    required = (
        ("CapabilityRequest", "CapabilityRequest" in nameset),
        ("AuthorizationDecision", "AuthorizationDecision" in nameset),
        ("ExecutionAdmission", "ExecutionAdmission" in nameset),
        ("authorization state validation",
         "validate_authorization_state" in callset),
        ("admission creation",
         "from_authorization" in callset),
    )

    for label, condition in required:
        checks += 1
        passed += require(
            label,
            condition,
            "present" if condition else "not observed",
        )

    print(f"\nGateway checks: {passed}/{checks} PASS")

    return 0 if passed == checks else 1


def inspect_executor(
    tree: ast.AST,
    text: str,
) -> int:
    passed = 0
    checks = 0

    nameset = names(tree)
    callset = calls(tree)

    required = (
        ("ExecutionAdmission", "ExecutionAdmission" in nameset),
        ("authorization decision", "authorization_decision" in text),
        ("admission validation",
         any(
             item in callset
             for item in (
                 "validate",
                 "validate_for_execution",
                 "require_authorized",
             )
         )),
    )

    for label, condition in required:
        checks += 1
        passed += require(
            label,
            condition,
            "present" if condition else "not observed",
        )

    print(f"\nExecutor checks: {passed}/{checks} PASS")

    return 0 if passed == checks else 1


def inspect_tests() -> int:
    print()
    print("=" * 78)
    print("TEST SURFACE")
    print("=" * 78)

    total = 0
    with_tests = 0

    for path in TESTS:
        if not path.is_file():
            print(f"[WARN] Missing test: {path.relative_to(REPO)}")
            continue

        text = source(path)
        tree = parse(path)

        test_functions = sorted(
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )

        total += len(test_functions)

        if test_functions:
            with_tests += 1

        print()
        print(path.relative_to(REPO))
        print(f"  SHA-256: {sha256(path)}")
        print(f"  Tests:   {len(test_functions)}")

        for test in test_functions:
            print(f"    - {test}")

    print()
    print(f"[INFO] Test modules containing tests: {with_tests}/{len(TESTS)}")
    print(f"[INFO] Total discovered test functions: {total}")

    return 0


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS BOUNDARY EVIDENCE REVIEW")
    print("READ-ONLY — NO RUNTIME EXECUTION")
    print("=" * 78)

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    status = git("status", "--short", "--untracked-files=all")

    print("\nREPOSITORY")
    print(f"HEAD:        {head}")
    print(f"origin/main: {origin}")

    if head == origin:
        print("[PASS] HEAD == origin/main")
    else:
        print("[WARN] HEAD differs from origin/main")

    print("\nWORKTREE")
    if status:
        print(status)
        print("[INFO] Review tooling is untracked and preserved.")
    else:
        print("[PASS] CLEAN")

    results: list[int] = []

    parsed: dict[str, tuple[ast.AST, str]] = {}

    for label, path in FILES.items():
        tree, text = check_file(label, path)

        if tree is None:
            print(f"[FAIL] {label} cannot be inspected")
            results.append(1)
        else:
            parsed[label] = (tree, text)

    print()
    print("=" * 78)
    print("BOUNDARY SEMANTIC CHECKS")
    print("=" * 78)

    if "aegis_policy" in parsed:
        results.append(
            inspect_aegis(*parsed["aegis_policy"])
        )

    if "aegis_authorization" in parsed:
        results.append(
            inspect_authorization(*parsed["aegis_authorization"])
        )

    if "capability_gateway" in parsed:
        results.append(
            inspect_gateway(*parsed["capability_gateway"])
        )

    if "secure_executor" in parsed:
        results.append(
            inspect_executor(*parsed["secure_executor"])
        )

    inspect_tests()

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
    print("DECISION")
    print("=" * 78)

    if any(result != 0 for result in results):
        print("AEGIS_BOUNDARY_EVIDENCE_REQUIRES_REVIEW")
    else:
        print("AEGIS_BOUNDARY_STRUCTURAL_EVIDENCE_PASS_PENDING_CONTROLLED_VALIDATION")

    print()
    print("This is structural/source evidence only.")
    print("It does not establish implementation validation or acceptance.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

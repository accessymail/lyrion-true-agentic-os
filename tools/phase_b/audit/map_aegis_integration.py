#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Integration / Dependency Evidence Mapper

READ-ONLY reconnaissance only.

Purpose:
    Map the existing Aegis implementation to its actual repository
    dependencies and downstream execution-boundary references.

Safety:
    - No runtime execution.
    - No source/test/doc/manifest modification.
    - No Git mutation.
    - No G46.5/G47 reconstruction.
    - No R097 modification.
    - No production/certification claim.
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

TARGETS = {
    "aegis_policy": REPO / "src/lyrion/security/policy.py",
    "aegis_authorization": REPO / "src/lyrion/security/authorization.py",
    "aegis_rules": REPO / "src/lyrion/security/rules.py",
    "aegis_guards": REPO / "src/lyrion/security/guards.py",
    "aegis_replay": REPO / "src/lyrion/security/replay.py",
    "capability_gateway": REPO / "src/lyrion/capabilities/gateway.py",
    "execution_admission": REPO / "src/lyrion/execution/validator.py",
    "execution_contracts": REPO / "src/lyrion/execution/contracts.py",
    "secure_executor": REPO / "src/lyrion/execution/executor.py",
}

TEST_TARGETS = [
    REPO / "tests/unit/test_aegis_policy.py",
    REPO / "tests/unit/test_aegis_policy_integration.py",
    REPO / "tests/unit/test_aegis_authorization.py",
    REPO / "tests/unit/test_aegis_guards.py",
    REPO / "tests/unit/test_aegis_replay.py",
    REPO / "tests/unit/test_aegis_rules.py",
]

CONTRACT_TERMS = (
    "aegis",
    "authorization",
    "policy",
    "capability",
    "decision",
    "deny",
    "allow",
    "risk",
    "trust",
    "revocation",
    "replay",
    "containment",
    "quarantine",
    "provenance",
    "hitl",
    "fail-closed",
    "fail_closed",
    "authority",
    "principal",
    "target_scope",
    "policy_version",
)


def git(*args: str) -> str:
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


def dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def imports_from(tree: ast.AST) -> list[str]:
    values: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                values.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            for alias in node.names:
                values.add(
                    f"{module}.{alias.name}"
                    if module
                    else alias.name
                )

    return sorted(values)


def calls_from(tree: ast.AST) -> list[str]:
    values: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted(node.func)
            if name:
                values.add(name)

    return sorted(values)


def definitions_from(tree: ast.AST) -> tuple[list[str], list[str]]:
    classes: set[str] = set()
    functions: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.add(node.name)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)

    return sorted(classes), sorted(functions)


def source_terms(text: str) -> list[str]:
    lower = text.lower()
    return [
        term
        for term in CONTRACT_TERMS
        if term.lower() in lower
    ]


def map_file(label: str, path: Path) -> None:
    print()
    print("=" * 78)
    print(f"{label}: {path.relative_to(REPO)}")
    print("=" * 78)

    if not path.is_file():
        print("STATUS: MISSING")
        return

    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))

    classes, functions = definitions_from(tree)

    print(f"STATUS: PRESENT")
    print(f"SHA-256: {sha256(path)}")
    print(f"BYTES: {path.stat().st_size}")

    print("\nCLASSES:")
    for item in classes:
        print(f"  - {item}")

    print("\nFUNCTIONS:")
    for item in functions:
        print(f"  - {item}")

    print("\nIMPORTS:")
    for item in imports_from(tree):
        print(f"  - {item}")

    print("\nCALLS:")
    for item in calls_from(tree):
        print(f"  - {item}")

    print("\nCONTRACT TERMS PRESENT:")
    for item in source_terms(text):
        print(f"  - {item}")


def search_repository(term: str) -> None:
    print()
    print("-" * 78)
    print(f"REPOSITORY REFERENCE SEARCH: {term}")
    print("-" * 78)

    result = subprocess.run(
        [
            "git",
            "grep",
            "-n",
            "-I",
            "-E",
            term,
            "--",
            "src",
            "tests",
            "docs/phase-b",
        ],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stdout.strip():
        lines = result.stdout.splitlines()

        for line in lines[:120]:
            print(f"  {line}")

        if len(lines) > 120:
            print(f"  ... {len(lines) - 120} additional matches omitted")
    else:
        print("  NO MATCHES")


def test_summary(path: Path) -> None:
    print()
    print("=" * 78)
    print(f"TEST: {path.relative_to(REPO)}")
    print("=" * 78)

    if not path.is_file():
        print("STATUS: MISSING")
        return

    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))

    tests: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                tests.append(node.name)

    print(f"STATUS: PRESENT")
    print(f"SHA-256: {sha256(path)}")
    print(f"BYTES: {path.stat().st_size}")
    print(f"TEST_COUNT: {len(tests)}")

    for name in sorted(tests):
        print(f"  - {name}")

    if not tests:
        print("  [WARN] No test functions discovered")


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS INTEGRATION / DEPENDENCY EVIDENCE MAP")
    print("READ-ONLY")
    print("=" * 78)

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    status = git("status", "--short", "--untracked-files=all")

    print("\nREPOSITORY STATE")
    print(f"HEAD:        {head}")
    print(f"origin/main: {origin}")
    print(f"HEAD_MATCH:  {'PASS' if head == origin else 'FAIL'}")

    print("\nWORKTREE")
    if status:
        print(status)
        print("[INFO] Existing untracked review tooling is preserved.")
    else:
        print("CLEAN")

    print("\nTARGET IMPLEMENTATION MAP")

    missing = []

    for label, path in TARGETS.items():
        map_file(label, path)

        if not path.is_file():
            missing.append(label)

    print("\nTEST SURFACE MAP")

    for path in TEST_TARGETS:
        test_summary(path)

    print("\nCRITICAL CROSS-BOUNDARY SEARCHES")

    search_repository(
        r"AegisPolicyEvaluator|AegisAuthorizationService"
    )

    search_repository(
        r"authorization_guard|AuthorizationGuard|ReplayGuard"
    )

    search_repository(
        r"CapabilityGateway|capability_gateway|CapabilityRequest"
    )

    search_repository(
        r"ExecutionAdmission|execution_admission|ExecutionAdmission"
    )

    search_repository(
        r"require_authorized|is_authorized|AuthorizationDecision"
    )

    search_repository(
        r"fail.?closed|default.?deny|deny"
    )

    search_repository(
        r"containment|quarantine|revocation|provenance|HITL"
    )

    print("\nARCHITECTURAL QUESTIONS THIS MAP SUPPORTS")

    questions = (
        "1. Does Aegis produce an explicit authorization decision?",
        "2. Is authorization bound to principal, capability, scope and policy version?",
        "3. Is replay protection enforced before consequential authorization?",
        "4. Does Capability Gateway consume Aegis authorization rather than create authority?",
        "5. Does Execution Admission consume Aegis authorization without overriding denial?",
        "6. Is Secure Executor downstream of authorization/admission?",
        "7. Where are trust/risk/containment/quarantine/provenance controls implemented?",
        "8. Is HITL represented as a control rather than an agent decision?",
        "9. Is fail-closed behavior enforced at consequential boundaries?",
        "10. Is there any alternate privileged execution path?"
    )

    for question in questions:
        print(f"  {question}")

    print("\nPROTECTED BOUNDARIES")
    print("[PASS] Read-only source inspection")
    print("[PASS] No Aegis runtime execution")
    print("[PASS] No source modification")
    print("[PASS] No test modification")
    print("[PASS] No documentation modification")
    print("[PASS] No manifest modification")
    print("[PASS] No Git mutation")
    print("[PASS] No G46.5 reconstruction")
    print("[PASS] No G47 reconstruction")
    print("[PASS] No R097 modification")
    print("[PASS] Production certification NOT CLAIMED")

    if missing:
        print("\nDECISION")
        print("AEGIS_INTEGRATION_MAP_INCOMPLETE_MISSING_TARGETS")
        return 1

    print("\nDECISION")
    print("AEGIS_INTEGRATION_MAP_COMPLETE_PENDING_ENGINEERING_REVIEW")
    print()
    print("This output is evidence reconnaissance only.")
    print("It does not establish implementation validation, acceptance,")
    print("production readiness, or certification.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

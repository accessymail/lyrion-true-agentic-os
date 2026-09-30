#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Semantic Evidence Review — Read-Only

Purpose:
    Inspect the existing Aegis implementation and test surface at the
    AST/source-structure level and compare observable implementation
    signals against the approved Aegis governance contract.

Safety:
    - Read-only.
    - Does not execute Aegis runtime behavior.
    - Does not modify source, tests, documentation, manifests, or Git.
    - Does not claim implementation validation.
    - Does not claim production readiness/certification.
    - Does not reconstruct G46.5/G47.
    - Does not modify R097.

This is evidence reconnaissance, not an acceptance gate.
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

RUNTIME_FILES = (
    REPO / "src/lyrion/security/policy.py",
    REPO / "src/lyrion/security/authorization.py",
)

TEST_FILES = (
    REPO / "tests/unit/test_aegis_policy.py",
    REPO / "tests/unit/test_aegis_policy_integration.py",
    REPO / "tests/unit/test_aegis_authorization.py",
    REPO / "tests/unit/test_aegis_guards.py",
    REPO / "tests/unit/test_aegis_replay.py",
    REPO / "tests/unit/test_aegis_rules.py",
)

AEGIS_SPEC = (
    REPO
    / "docs/phase-b/aegis/"
    / "LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md"
)

SECURITY_SPEC = (
    REPO
    / "docs/phase-b/security-testing/"
    / "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md"
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
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def calls(tree: ast.AST) -> list[str]:
    result: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if name:
                result.append(name)

    return sorted(set(result))


def definitions(tree: ast.AST) -> tuple[list[str], list[str]]:
    classes: list[str] = []
    functions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)

    return sorted(set(classes)), sorted(set(functions))


def imports(tree: ast.AST) -> list[str]:
    result: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            result.extend(
                f"{module}.{alias.name}" if module else alias.name
                for alias in node.names
            )

    return sorted(set(result))


def source_signals(text: str) -> dict[str, bool]:
    lower = text.lower()

    return {
        "allow": "allow" in lower,
        "deny": "deny" in lower,
        "decision": "decision" in lower,
        "policy": "policy" in lower,
        "authorization": "authorization" in lower,
        "authority": "authority" in lower,
        "capability": "capability" in lower,
        "risk": "risk" in lower,
        "trust": "trust" in lower,
        "revocation": "revok" in lower,
        "containment": "containment" in lower,
        "quarantine": "quarantine" in lower,
        "fail_closed": "fail" in lower and "closed" in lower,
        "provenance": "provenance" in lower,
        "replay": "replay" in lower,
        "model": "model" in lower,
        "agent": "agent" in lower,
    }


def print_file_structure(path: Path) -> None:
    text = source(path)
    tree = ast.parse(text, filename=str(path))

    classes, functions = definitions(tree)

    print()
    print("=" * 72)
    print(path.relative_to(REPO))
    print("=" * 72)
    print(f"SHA-256: {sha256(path)}")
    print(f"Bytes:   {path.stat().st_size}")

    print("\nCLASSES")
    for item in classes:
        print(f"  - {item}")

    print("\nFUNCTIONS")
    for item in functions:
        print(f"  - {item}")

    print("\nIMPORTS")
    for item in imports(tree):
        print(f"  - {item}")

    print("\nCALLS")
    for item in calls(tree):
        print(f"  - {item}")

    print("\nSOURCE SIGNALS")
    for name, present in source_signals(text).items():
        print(f"  {'PASS' if present else 'WARN'}  {name}")


def print_test_structure(path: Path) -> None:
    text = source(path)
    tree = ast.parse(text, filename=str(path))

    classes, functions = definitions(tree)

    print()
    print("=" * 72)
    print(path.relative_to(REPO))
    print("=" * 72)
    print(f"SHA-256: {sha256(path)}")

    print("\nTEST FUNCTIONS")
    for item in functions:
        if item.startswith("test"):
            print(f"  - {item}")

    if classes:
        print("\nTEST CLASSES")
        for item in classes:
            print(f"  - {item}")

    print("\nASSERTION / TEST CALL SIGNALS")

    interesting = (
        "assert",
        "pytest",
        "raises",
        "mock",
        "patch",
        "monkeypatch",
        "parametrize",
    )

    found: set[str] = set()

    for call in calls(tree):
        lower = call.lower()
        if any(term in lower for term in interesting):
            found.add(call)

    for item in sorted(found):
        print(f"  - {item}")

    print("\nTEST SOURCE SIGNALS")
    for name, present in source_signals(text).items():
        print(f"  {'PASS' if present else 'WARN'}  {name}")


def document_signals(path: Path) -> None:
    text = source(path).lower()

    required = (
        "independent",
        "authority",
        "policy",
        "trust",
        "risk",
        "capability",
        "containment",
        "revocation",
        "quarantine",
        "hitl",
        "provenance",
        "fail-closed",
        "alternate execution",
        "bypass",
    )

    print()
    print("=" * 72)
    print(path.relative_to(REPO))
    print("=" * 72)

    for term in required:
        present = term in text
        print(f"[{'PASS' if present else 'WARN'}] contract term: {term}")


def main() -> int:
    print("=" * 72)
    print("LYRION AEGIS SEMANTIC EVIDENCE REVIEW")
    print("READ-ONLY — NO IMPLEMENTATION")
    print("=" * 72)

    print("\nREPOSITORY STATE")
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    status = git("status", "--short", "--untracked-files=all")

    print(f"HEAD:        {head}")
    print(f"origin/main: {origin}")
    print(f"HEAD_MATCH:  {'PASS' if head == origin else 'WARN'}")

    if status:
        print("\nWORKTREE:")
        print(status)
        print("[INFO] The review tool itself is currently untracked.")
    else:
        print("WORKTREE:    CLEAN")

    print("\nGOVERNANCE CONTRACT")
    document_signals(AEGIS_SPEC)

    print("\nSECURITY TESTING CONTRACT")
    document_signals(SECURITY_SPEC)

    print("\nRUNTIME SEMANTIC INSPECTION")
    for path in RUNTIME_FILES:
        if not path.is_file():
            print(f"[FAIL] Missing runtime file: {path}")
            return 1
        print_file_structure(path)

    print("\nTEST SEMANTIC INSPECTION")
    for path in TEST_FILES:
        if not path.is_file():
            print(f"[FAIL] Missing test file: {path}")
            return 1
        print_test_structure(path)

    print("\nPROTECTED BOUNDARIES")
    print("[PASS] No runtime execution performed")
    print("[PASS] No source modification performed")
    print("[PASS] No test modification performed")
    print("[PASS] No documentation modification performed")
    print("[PASS] No manifest modification performed")
    print("[PASS] No G46.5 reconstruction")
    print("[PASS] No G47 reconstruction")
    print("[PASS] No R097 modification")
    print("[PASS] Production certification NOT CLAIMED")

    print("\nDECISION")
    print("AEGIS_SEMANTIC_REVIEW_COMPLETE_PENDING_ENGINEERING_REVIEW")
    print()
    print("This report is reconnaissance evidence only.")
    print("It does not establish validation, acceptance, or certification.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

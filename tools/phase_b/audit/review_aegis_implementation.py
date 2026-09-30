#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Implementation Reconciliation — Read-Only Review

Purpose:
    Compare the existing Aegis implementation/test surface against the
    repository's approved Phase-B Aegis governance boundary.

Safety:
    - Read-only.
    - Does not modify source, tests, documentation, manifests, or Git state.
    - Does not execute Aegis runtime behavior.
    - Does not claim implementation validation or production certification.
    - Does not reconstruct G46.5/G47 evidence.
    - Does not modify R097.

This is a reconnaissance/reconciliation tool, not an acceptance gate.
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

DOCUMENT = (
    REPO
    / "docs/phase-b/aegis/"
    / "LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md"
)

SECURITY_TESTING_DOCUMENT = (
    REPO
    / "docs/phase-b/security-testing/"
    / "LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md"
)

MASTER_MANIFEST = (
    REPO
    / "docs/phase-b/governance/"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

REQUIRED_CONTRACT_TERMS = (
    "independent governance",
    "policy",
    "risk",
    "containment",
    "security decision",
    "fail-closed",
    "model",
    "agent",
    "authority",
    "capability",
    "provenance",
)

REQUIRED_SECURITY_TERMS = (
    "policy evaluation",
    "Aegis",
    "independent security",
    "bypass Aegis",
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_file(path: Path, label: str) -> bool:
    exists = path.is_file()
    print(
        f"[{'PASS' if exists else 'FAIL'}] "
        f"{label}: {path.relative_to(REPO) if path.exists() else path}"
    )
    return exists


def inspect_python(path: Path) -> tuple[bool, int, int]:
    source = read(path)

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        print(f"[FAIL] AST parse: {path.relative_to(REPO)}: {exc}")
        return False, 0, 0

    functions = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
    )
    classes = sum(
        isinstance(node, ast.ClassDef)
        for node in ast.walk(tree)
    )

    print(
        f"[PASS] AST parse: {path.relative_to(REPO)} "
        f"(classes={classes}, functions={functions})"
    )
    return True, classes, functions


def term_presence(path: Path, terms: tuple[str, ...], label: str) -> int:
    text = read(path).lower()
    found = 0

    for term in terms:
        if term.lower() in text:
            found += 1
            print(f"[PASS] {label}: '{term}'")
        else:
            print(f"[WARN] {label}: '{term}' not found")

    return found


def main() -> int:
    print("=" * 72)
    print("LYRION AEGIS IMPLEMENTATION RECONCILIATION")
    print("READ-ONLY — NO IMPLEMENTATION")
    print("=" * 72)

    failures = 0
    warnings = 0

    print("\n----- REPOSITORY -----")

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    status = run_git("status", "--short", "--untracked-files=all")

    print(f"HEAD:       {head}")
    print(f"origin/main:{origin}")

    if head == origin:
        print("[PASS] HEAD == origin/main")
    else:
        print("[WARN] HEAD != origin/main")
        warnings += 1

    if status:
        print("[WARN] Worktree contains changes/untracked files:")
        print(status)
        warnings += 1
    else:
        print("[PASS] Worktree clean")

    print("\n----- GOVERNANCE DOCUMENTS -----")

    for path, label in (
        (DOCUMENT, "Aegis Governance Specification"),
        (SECURITY_TESTING_DOCUMENT, "Security Testing Specification"),
        (MASTER_MANIFEST, "Phase-B Master Manifest"),
    ):
        if not check_file(path, label):
            failures += 1

    print("\n----- RUNTIME -----")

    runtime_ok = True

    for path in RUNTIME_FILES:
        if not check_file(path, "Runtime"):
            runtime_ok = False
            failures += 1
            continue

        parsed, _, _ = inspect_python(path)
        if not parsed:
            runtime_ok = False
            failures += 1

        print(
            f"[INFO] SHA-256 {path.relative_to(REPO)}: "
            f"{sha256(path)}"
        )

    print("\n----- TEST SURFACE -----")

    tests_ok = True

    for path in TEST_FILES:
        if not check_file(path, "Test"):
            tests_ok = False
            failures += 1

    print("\n----- AEGIS CONTRACT SURFACE -----")

    contract_found = term_presence(
        DOCUMENT,
        REQUIRED_CONTRACT_TERMS,
        "Aegis contract",
    )

    if contract_found == len(REQUIRED_CONTRACT_TERMS):
        print("[PASS] Required Aegis contract vocabulary present")
    else:
        warnings += 1

    print("\n----- SECURITY TESTING CONTRACT -----")

    security_found = term_presence(
        SECURITY_TESTING_DOCUMENT,
        REQUIRED_SECURITY_TERMS,
        "Security testing",
    )

    if security_found == len(REQUIRED_SECURITY_TERMS):
        print("[PASS] Required Aegis security-testing vocabulary present")
    else:
        warnings += 1

    print("\n----- IMPLEMENTATION SIGNALS -----")

    runtime_text = "\n".join(
        read(path).lower()
        for path in RUNTIME_FILES
        if path.is_file()
    )

    implementation_signals = {
        "policy": "policy" in runtime_text,
        "authorization": "authorization" in runtime_text,
        "deny": "deny" in runtime_text,
        "allow": "allow" in runtime_text,
        "risk": "risk" in runtime_text,
        "containment": "containment" in runtime_text,
        "revocation": "revok" in runtime_text,
        "quarantine": "quarantine" in runtime_text,
        "fail_closed": "fail" in runtime_text and "closed" in runtime_text,
    }

    for name, present in implementation_signals.items():
        print(f"[{'PASS' if present else 'WARN'}] runtime signal: {name}")
        if not present:
            warnings += 1

    print("\n----- TEST SIGNALS -----")

    test_text = "\n".join(
        read(path).lower()
        for path in TEST_FILES
        if path.is_file()
    )

    test_signals = {
        "deny": "deny" in test_text,
        "allow": "allow" in test_text,
        "replay": "replay" in test_text,
        "guard": "guard" in test_text,
        "policy": "policy" in test_text,
        "authorization": "authorization" in test_text,
    }

    for name, present in test_signals.items():
        print(f"[{'PASS' if present else 'WARN'}] test signal: {name}")
        if not present:
            warnings += 1

    print("\n----- PROTECTED BOUNDARIES -----")

    print("[PASS] Implementation modification: NOT PERFORMED")
    print("[PASS] Production certification: NOT CLAIMED")
    print("[PASS] G46.5 reconstruction: NOT PERFORMED")
    print("[PASS] G47 reconstruction: NOT PERFORMED")
    print("[PASS] R097 modification: NOT PERFORMED")

    print("\n----- DECISION -----")

    if failures:
        decision = "AEGIS_RECONCILIATION_BLOCKED"
    else:
        decision = "AEGIS_RECONCILIATION_REQUIRES_EVIDENCE_REVIEW"

    print(f"PASS : {0 if failures else 1}")
    print(f"WARN : {warnings}")
    print(f"FAIL : {failures}")
    print(f"Decision: {decision}")

    print("\nNo source, tests, documentation, manifests, or Git state were modified.")
    print("This report does NOT establish implementation validation.")
    print("This report does NOT establish production readiness or certification.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

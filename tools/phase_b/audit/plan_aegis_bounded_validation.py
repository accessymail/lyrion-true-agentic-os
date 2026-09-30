#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Bounded Validation Planner

READ-ONLY GOVERNANCE / VALIDATION PLANNER.

Purpose:
    Produce an exact, controlled validation plan for the existing Aegis
    bounded implementation slice.

Validation boundary:

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
    Execution Validator
        ->
    Secure Executor
        ->
    Enforcement Boundary

This planner DOES NOT:
    - modify runtime source
    - modify tests
    - modify documentation
    - modify manifests
    - execute production Aegis behavior
    - access credentials
    - perform privileged host execution
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification

It produces the exact bounded validation commands and required evidence.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

RUNTIME_FILES = [
    REPO / "src/lyrion/security/policy.py",
    REPO / "src/lyrion/security/authorization.py",
    REPO / "src/lyrion/security/guards.py",
    REPO / "src/lyrion/security/replay.py",
    REPO / "src/lyrion/capabilities/contracts.py",
    REPO / "src/lyrion/capabilities/gateway.py",
    REPO / "src/lyrion/execution/contracts.py",
    REPO / "src/lyrion/execution/validator.py",
    REPO / "src/lyrion/execution/executor.py",
]

TEST_FILES = [
    REPO / "tests/unit/test_aegis_policy.py",
    REPO / "tests/unit/test_aegis_authorization.py",
    REPO / "tests/unit/test_aegis_guards.py",
    REPO / "tests/unit/test_aegis_replay.py",
    REPO / "tests/unit/test_capability_gateway.py",
    REPO / "tests/unit/test_capability_contracts.py",
    REPO / "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
    REPO / "tests/unit/execution/test_secure_executor_enforcement_integration.py",
    REPO / "tests/unit/test_execution_result_state_integration.py",
    REPO / "tests/unit/test_secure_executor.py",
]


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


def check_file(path: Path, category: str) -> bool:
    relative = path.relative_to(REPO)

    if not path.is_file():
        print(f"[FAIL] {category}: missing: {relative}")
        return False

    print(f"[PASS] {category}: {relative}")
    print(f"       SHA-256: {sha256(path)}")
    return True


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS BOUNDED VALIDATION PLANNER")
    print("READ-ONLY")
    print("=" * 78)

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    status = run_git("status", "--short", "--untracked-files=all")

    print("\nREPOSITORY STATE")
    print(f"HEAD:        {head}")
    print(f"origin/main: {origin}")

    if head == origin:
        print("[PASS] HEAD == origin/main")
    else:
        print("[FAIL] HEAD != origin/main")

    print("\nWORKTREE STATE")

    if status:
        print(status)
        print(
            "[INFO] Existing Aegis read-only audit tools are expected "
            "to remain untracked during planning."
        )
    else:
        print("[PASS] CLEAN")

    print("\nRUNTIME IMPLEMENTATION INVENTORY")

    runtime_ok = True

    for path in RUNTIME_FILES:
        runtime_ok &= check_file(path, "RUNTIME")

    print("\nTEST INVENTORY")

    tests_ok = True

    for path in TEST_FILES:
        tests_ok &= check_file(path, "TEST")

    print("\n" + "=" * 78)
    print("CONTROLLED VALIDATION COMMANDS")
    print("=" * 78)

    commands = [
        (
            "A",
            "Static compilation of bounded Aegis runtime",
            "python -m py_compile "
            "src/lyrion/security/policy.py "
            "src/lyrion/security/authorization.py "
            "src/lyrion/security/guards.py "
            "src/lyrion/security/replay.py "
            "src/lyrion/capabilities/contracts.py "
            "src/lyrion/capabilities/gateway.py "
            "src/lyrion/execution/contracts.py "
            "src/lyrion/execution/validator.py "
            "src/lyrion/execution/executor.py",
        ),
        (
            "B",
            "Aegis policy / authorization / guard / replay validation",
            "pytest -q "
            "tests/unit/test_aegis_policy.py "
            "tests/unit/test_aegis_authorization.py "
            "tests/unit/test_aegis_guards.py "
            "tests/unit/test_aegis_replay.py",
        ),
        (
            "C",
            "Capability contracts and gateway validation",
            "pytest -q "
            "tests/unit/test_capability_contracts.py "
            "tests/unit/test_capability_gateway.py",
        ),
        (
            "D",
            "Secure Executor enforcement boundary",
            "pytest -q "
            "tests/unit/execution/test_secure_executor_enforcement_boundary.py "
            "tests/unit/execution/test_secure_executor_enforcement_integration.py "
            "tests/unit/test_secure_executor.py",
        ),
        (
            "E",
            "Execution result-state integration",
            "pytest -q "
            "tests/unit/test_execution_result_state_integration.py",
        ),
    ]

    for identifier, purpose, command in commands:
        print()
        print(f"[{identifier}] {purpose}")
        print(f"    {command}")

    print("\n" + "=" * 78)
    print("REQUIRED EVIDENCE")
    print("=" * 78)

    evidence = [
        "1. Exact command executed.",
        "2. UTC execution timestamp.",
        "3. Python version.",
        "4. pytest version.",
        "5. Git HEAD before validation.",
        "6. origin/main before validation.",
        "7. Complete command output.",
        "8. Process exit status.",
        "9. Test count and failure count.",
        "10. Runtime SHA-256 values before validation.",
        "11. Runtime SHA-256 values after validation.",
        "12. Confirmation that source files were not modified.",
        "13. Confirmation that tests were not modified.",
        "14. Confirmation that documentation/manifests were not modified.",
        "15. Confirmation that Git HEAD did not change.",
        "16. Confirmation that G46.5/G47 were not reconstructed.",
        "17. Confirmation that R097 was not modified.",
        "18. Production certification remains NOT CLAIMED.",
    ]

    for item in evidence:
        print(f"[REQUIRED] {item}")

    print("\n" + "=" * 78)
    print("SECURITY / EXECUTION RESTRICTIONS")
    print("=" * 78)

    restrictions = [
        "No credentials.",
        "No secrets.",
        "No provider deployment.",
        "No database writes.",
        "No systemd changes.",
        "No privileged host execution.",
        "No external network-dependent validation.",
        "No production infrastructure.",
        "No modification of runtime source.",
        "No modification of project tests.",
        "No modification of governance documents.",
        "No G46.5 reconstruction.",
        "No G47 reconstruction.",
        "No R097 modification.",
        "No production-certification claim.",
    ]

    for item in restrictions:
        print(f"[PASS] {item}")

    print("\n" + "=" * 78)
    print("VALIDATION SCOPE")
    print("=" * 78)

    print(
        "Bounded Aegis implementation only:"
    )

    print(
        "Aegis Policy -> Authorization Service -> Guards -> "
        "Capability Gateway -> Execution Admission -> "
        "Execution Validator -> Secure Executor"
    )

    print("\nExplicitly OUT OF SCOPE:")
    print("Full PB-DOC-010 production validation")
    print("Full Phase-B validation")
    print("G46.5")
    print("G47")
    print("R097")
    print("Production certification")
    print("Production operation")

    print("\n" + "=" * 78)
    print("PLANNER DECISION")
    print("=" * 78)

    if head != origin:
        print("VALIDATION_PLAN_BLOCKED_REPOSITORY_NOT_SYNCHRONIZED")
        return 1

    if not runtime_ok:
        print("VALIDATION_PLAN_BLOCKED_RUNTIME_INVENTORY")
        return 1

    if not tests_ok:
        print("VALIDATION_PLAN_BLOCKED_TEST_INVENTORY")
        return 1

    print("AEGIS_BOUNDED_VALIDATION_PLAN_READY")

    print()
    print(
        "This planner establishes a controlled validation plan only."
    )
    print(
        "It does not establish validation, acceptance, operation, "
        "or production certification."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

"""
LYRION True Agentic OS
Controlled Validation Planner
Slice: Execution Admission Boundary

READ-ONLY / PLANNING-ONLY

Purpose:
    Establish the exact bounded validation scope before executing tests.

This tool does NOT:
    - execute pytest
    - execute runtime code
    - modify src/
    - modify tests/
    - modify docs/
    - modify manifests
    - modify Git
    - reconstruct G46.5/G47
    - modify R097
    - claim validation or certification

Output:
    A deterministic validation plan identifying:
        - runtime boundary
        - direct tests
        - related enforcement tests
        - validation tooling
        - proposed execution order
        - evidence requirements
        - protected boundaries
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

RUNTIME_FILES = (
    "src/lyrion/capabilities/gateway.py",
    "src/lyrion/execution/contracts.py",
    "src/lyrion/execution/validator.py",
    "src/lyrion/execution/executor.py",
)

DIRECT_TESTS = (
    "tests/unit/test_capability_gateway.py",
    "tests/unit/test_execution_contracts.py",
    "tests/unit/test_execution_validator.py",
    "tests/unit/test_execution_result_state_integration.py",
    "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
    "tests/unit/execution/test_secure_executor_enforcement_integration.py",
)

VALIDATION_TOOL_NAMES = (
    "phase_b_repository_baseline_audit.py",
    "validate_phase_b_repository_baseline_audit.py",
    "final_acceptance_review_phase_b_audit.py",
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
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


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def imports(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except (OSError, SyntaxError):
        return set()

    result: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(item.name for item in node.names)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.add(node.module)

    return result


def test_targets_runtime(test: Path, runtime: Path) -> bool:
    text = test.read_text(errors="replace")

    module = str(runtime.with_suffix("")).replace("/", ".")
    stem = runtime.stem

    return (
        module in text
        or module in imports(test)
        or stem in text
    )


def main() -> int:
    failures = 0
    warnings = 0

    print("=" * 80)
    print("LYRION TRUE AGENTIC OS")
    print("CONTROLLED VALIDATION PLANNER")
    print("SLICE: EXECUTION ADMISSION BOUNDARY")
    print("MODE: READ-ONLY / PLANNING-ONLY")
    print("=" * 80)

    # ---------------------------------------------------------------
    # 1. Repository baseline
    # ---------------------------------------------------------------

    print("\n[1] REPOSITORY BASELINE")

    root = git("rev-parse", "--show-toplevel")
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    branch = git("branch", "--show-current")

    print(f"Repository : {root}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")

    if Path(root).resolve() != REPO_ROOT.resolve():
        print("[FAIL] Repository root mismatch")
        failures += 1

    if branch != "main":
        print("[FAIL] Unexpected branch")
        failures += 1

    if head != origin:
        print("[WARN] HEAD differs from origin/main")
        warnings += 1
    else:
        print("[PASS] Repository synchronized")

    # ---------------------------------------------------------------
    # 2. Worktree
    # ---------------------------------------------------------------

    print("\n[2] WORKTREE")

    status = git("status", "--short", "--untracked-files=all")

    if status:
        print("[INFO] Existing changes:")
        print(status)
        warnings += 1
    else:
        print("[PASS] Worktree clean")

    # ---------------------------------------------------------------
    # 3. Runtime boundary
    # ---------------------------------------------------------------

    print("\n[3] RUNTIME VALIDATION BOUNDARY")

    runtime_paths = []

    for item in RUNTIME_FILES:
        path = REPO_ROOT / item

        if not path.is_file():
            print(f"[FAIL] Missing: {item}")
            failures += 1
            continue

        runtime_paths.append(path)

        print(f"[PASS] {item}")
        print(f"       SHA256: {sha256(path)}")

    # ---------------------------------------------------------------
    # 4. Direct test inventory
    # ---------------------------------------------------------------

    print("\n[4] DIRECT TEST INVENTORY")

    test_paths = []

    for item in DIRECT_TESTS:
        path = REPO_ROOT / item

        if not path.is_file():
            print(f"[FAIL] Missing: {item}")
            failures += 1
            continue

        test_paths.append(path)
        print(f"[PASS] {item}")

    # ---------------------------------------------------------------
    # 5. Runtime → test mapping
    # ---------------------------------------------------------------

    print("\n[5] RUNTIME → TEST MAPPING")

    for runtime in runtime_paths:
        linked = [
            test
            for test in test_paths
            if test_targets_runtime(test, runtime)
        ]

        print(f"\nRuntime: {rel(runtime)}")

        if linked:
            for test in linked:
                print(f"  [LINK] {rel(test)}")
        else:
            print("  [WARN] No direct structural test mapping")
            warnings += 1

    # ---------------------------------------------------------------
    # 6. Validation tooling
    # ---------------------------------------------------------------

    print("\n[6] VALIDATION TOOLING")

    audit_root = REPO_ROOT / "tools" / "phase_b" / "audit"

    validation_paths = []

    for name in VALIDATION_TOOL_NAMES:
        path = audit_root / name

        if path.is_file():
            validation_paths.append(path)
            print(f"[PASS] {rel(path)}")
        else:
            print(f"[WARN] Validation tool not present: {name}")
            warnings += 1

    # ---------------------------------------------------------------
    # 7. Proposed validation order
    # ---------------------------------------------------------------

    print("\n[7] PROPOSED CONTROLLED EXECUTION ORDER")

    commands = (
        (
            "A",
            "Compile bounded Python sources/tests",
            "python3 -m compileall -q "
            "src/lyrion/capabilities/gateway.py "
            "src/lyrion/execution/contracts.py "
            "src/lyrion/execution/validator.py "
            "src/lyrion/execution/executor.py",
        ),
        (
            "B",
            "Run direct Execution Admission unit tests",
            "pytest -q "
            "tests/unit/test_capability_gateway.py "
            "tests/unit/test_execution_contracts.py "
            "tests/unit/test_execution_validator.py",
        ),
        (
            "C",
            "Run bounded execution-result integration test",
            "pytest -q "
            "tests/unit/test_execution_result_state_integration.py",
        ),
        (
            "D",
            "Run Secure Executor enforcement boundary tests",
            "pytest -q "
            "tests/unit/execution/"
            "test_secure_executor_enforcement_boundary.py "
            "tests/unit/execution/"
            "test_secure_executor_enforcement_integration.py",
        ),
    )

    for code, purpose, command in commands:
        print(f"\n[{code}] {purpose}")
        print(f"    {command}")

    print(
        "\n[IMPORTANT] These commands are PLAN OUTPUT ONLY. "
        "They are NOT executed by this tool."
    )

    # ---------------------------------------------------------------
    # 8. Evidence capture requirements
    # ---------------------------------------------------------------

    print("\n[8] REQUIRED EXECUTION EVIDENCE")

    evidence_requirements = (
        "Exact command executed",
        "Repository HEAD at execution time",
        "Clean/known worktree state",
        "Python/pytest versions",
        "Complete test output",
        "Exit status",
        "Test count and failures",
        "Timestamp",
        "SHA-256 of relevant runtime files",
        "No modification to protected boundaries",
    )

    for item in evidence_requirements:
        print(f"[REQUIRED] {item}")

    # ---------------------------------------------------------------
    # 9. Fail-closed rules
    # ---------------------------------------------------------------

    print("\n[9] FAIL-CLOSED RULES")

    rules = (
        "Any compilation failure blocks further validation.",
        "Any bounded test failure blocks acceptance.",
        "Unexpected runtime/source mutation blocks acceptance.",
        "Missing attributable evidence blocks acceptance.",
        "Ambiguous or conflicting governance state blocks execution.",
        "G46.5/G47 reconstruction is prohibited.",
        "R097 modification is prohibited.",
        "Production certification is not established by this plan.",
    )

    for rule in rules:
        print(f"[RULE] {rule}")

    # ---------------------------------------------------------------
    # 10. Final plan decision
    # ---------------------------------------------------------------

    print("\n" + "=" * 80)
    print("CONTROLLED VALIDATION PLAN RESULT")
    print("=" * 80)

    print(f"FAILURES : {failures}")
    print(f"WARNINGS : {warnings}")

    if failures:
        print("\nDecision: VALIDATION_PLAN_BLOCKED")
        print("FAIL-CLOSED.")
        return 1

    print("\nDecision: VALIDATION_PLAN_READY")
    print(
        "The bounded commands above are ready for controlled execution."
    )
    print(
        "This decision does NOT mean validation has passed."
    )
    print(
        "This decision does NOT authorize production operation."
    )
    print(
        "This decision does NOT establish certification."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

"""
LYRION True Agentic OS
Bounded Phase-B Implementation-Slice Review

Slice:
    Execution Admission Boundary

MODE:
    READ-ONLY / FAIL-CLOSED

This review establishes structural traceability only.

It does NOT:
    - modify LYRION runtime code
    - modify tests
    - modify documentation
    - modify manifests
    - commit or push Git changes
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification
    - infer successful validation from file presence
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
    "src/lyrion/execution/executor.py",
    "src/lyrion/execution/validator.py",
)

DIRECT_TEST_FILES = (
    "tests/unit/test_capability_gateway.py",
    "tests/unit/test_execution_contracts.py",
    "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
    "tests/unit/execution/test_secure_executor_enforcement_integration.py",
    "tests/unit/test_execution_result_state_integration.py",
)

SEMANTIC_TERMS = (
    "admission",
    "authority",
    "authorization",
    "capability",
    "execution",
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


def python_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(errors="replace"))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                imports.add(item.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def direct_test_link(test: Path, runtime: Path) -> bool:
    """
    Conservative structural linkage.

    A test is considered directly linked only when its source explicitly
    references the runtime module path or runtime filename stem.

    Keyword-only matches are deliberately excluded.
    """
    text = test.read_text(errors="replace")
    imports = python_imports(test)

    runtime_module = str(
        runtime.with_suffix("")
    ).replace("/", ".")

    runtime_stem = runtime.stem

    return (
        runtime_module in text
        or runtime_module in imports
        or runtime_stem in text
    )


def main() -> int:
    passed = 0
    warnings = 0
    failed = 0

    print("=" * 80)
    print("LYRION TRUE AGENTIC OS")
    print("BOUNDED PHASE-B IMPLEMENTATION-SLICE REVIEW")
    print("SLICE: EXECUTION ADMISSION BOUNDARY")
    print("MODE: READ-ONLY / FAIL-CLOSED")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 1. Repository baseline
    # ------------------------------------------------------------------

    print("\n[1] REPOSITORY BASELINE")

    repository = git("rev-parse", "--show-toplevel")
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    print(f"Repository : {repository}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")

    if Path(repository).resolve() == REPO_ROOT.resolve():
        print("[PASS] Repository root")
        passed += 1
    else:
        print("[FAIL] Repository root mismatch")
        failed += 1

    if branch == "main":
        print("[PASS] main branch")
        passed += 1
    else:
        print("[FAIL] Unexpected branch")
        failed += 1

    if head == origin:
        print("[PASS] Local HEAD == origin/main")
        passed += 1
    else:
        print("[WARN] Local HEAD differs from origin/main")
        warnings += 1

    # ------------------------------------------------------------------
    # 2. Worktree baseline
    # ------------------------------------------------------------------

    print("\n[2] WORKTREE BASELINE")

    status = git("status", "--short", "--untracked-files=all")

    if not status:
        print("[PASS] Worktree clean before review")
        passed += 1
    else:
        print("[INFO] Existing worktree changes:")
        print(status)
        warnings += 1

    # ------------------------------------------------------------------
    # 3. Governance
    # ------------------------------------------------------------------

    print("\n[3] GOVERNANCE BASELINE")

    governance = (
        REPO_ROOT
        / "docs/phase-b/governance/"
        "LYRION_PHASE_B_IMPLEMENTATION_AUTHORIZATION_GATE_SPECIFICATION_v1.md"
    )

    if governance.is_file():
        text = governance.read_text(errors="replace")
        lowered = text.lower()

        print("[PASS] PB-DOC-021 present")
        print(f"       SHA256: {sha256(governance)}")
        passed += 1

        markers = (
            "authorized",
            "production",
            "certification",
            "fail closed",
        )

        for marker in markers:
            if marker in lowered:
                print(f"[PASS] Governance marker: {marker}")
                passed += 1
            else:
                print(f"[WARN] Governance marker absent: {marker}")
                warnings += 1
    else:
        print("[FAIL] PB-DOC-021 missing")
        failed += 1

    # ------------------------------------------------------------------
    # 4. Runtime boundary
    # ------------------------------------------------------------------

    print("\n[4] BOUNDED RUNTIME FILES")

    runtime_paths: list[Path] = []

    for item in RUNTIME_FILES:
        path = REPO_ROOT / item

        if path.is_file() and path.is_relative_to(REPO_ROOT / "src"):
            runtime_paths.append(path)
            print(f"[PASS] {item}")
            passed += 1
        else:
            print(f"[FAIL] Missing/out-of-bound runtime file: {item}")
            failed += 1

    # ------------------------------------------------------------------
    # 5. Test boundary
    # ------------------------------------------------------------------

    print("\n[5] BOUNDED PROJECT TESTS")

    test_paths: list[Path] = []

    for item in DIRECT_TEST_FILES:
        path = REPO_ROOT / item

        if path.is_file() and path.is_relative_to(REPO_ROOT / "tests"):
            test_paths.append(path)
            print(f"[PASS] {item}")
            passed += 1
        else:
            print(f"[WARN] Test file not found: {item}")
            warnings += 1

    # ------------------------------------------------------------------
    # 6. Runtime ↔ test structural mapping
    # ------------------------------------------------------------------

    print("\n[6] RUNTIME ↔ TEST TRACEABILITY")

    for runtime in runtime_paths:
        linked = [
            test
            for test in test_paths
            if direct_test_link(test, runtime)
        ]

        print(f"\n{rel(runtime)}")

        if linked:
            print(f"[PASS] Direct structural links: {len(linked)}")

            for test in linked:
                print(f"       {rel(test)}")

            passed += 1
        else:
            print("[WARN] No direct structural test link established")
            warnings += 1

    # ------------------------------------------------------------------
    # 7. Runtime semantic presence
    # ------------------------------------------------------------------

    print("\n[7] RUNTIME SEMANTIC CHECK")

    for runtime in runtime_paths:
        text = runtime.read_text(errors="replace").lower()

        matches = [
            term
            for term in SEMANTIC_TERMS
            if term in text
        ]

        if matches:
            print(
                f"[PASS] {rel(runtime)} -> "
                f"{', '.join(matches)}"
            )
            passed += 1
        else:
            print(
                f"[WARN] {rel(runtime)} -> "
                "no bounded semantic markers"
            )
            warnings += 1

    # ------------------------------------------------------------------
    # 8. Documentation traceability
    # ------------------------------------------------------------------

    print("\n[8] DOCUMENTATION TRACEABILITY")

    docs_root = REPO_ROOT / "docs"
    documentation_hits: list[Path] = []

    if docs_root.is_dir():
        for path in docs_root.rglob("*.md"):
            if not path.is_file():
                continue

            if "NOT_USABLE_DOCUMENTS" in path.parts:
                continue

            try:
                text = path.read_text(errors="replace").lower()
            except OSError:
                continue

            if "execution admission" in text:
                documentation_hits.append(path)

    if documentation_hits:
        print(
            "[PASS] Execution-admission documentation references: "
            f"{len(documentation_hits)}"
        )

        for path in documentation_hits[:20]:
            print(f"       {rel(path)}")

        passed += 1
    else:
        print(
            "[WARN] No explicit execution-admission "
            "documentation reference found"
        )
        warnings += 1

    # ------------------------------------------------------------------
    # 9. Validation tooling
    # ------------------------------------------------------------------

    print("\n[9] VALIDATION TOOLING")

    tools_root = REPO_ROOT / "tools" / "phase_b"

    validation_files = (
        list(tools_root.rglob("*.py"))
        if tools_root.is_dir()
        else []
    )

    if validation_files:
        print(
            "[PASS] Phase-B validation tooling: "
            f"{len(validation_files)} files"
        )
        passed += 1
    else:
        print("[FAIL] No Phase-B validation tooling found")
        failed += 1

    # ------------------------------------------------------------------
    # 10. Executed evidence boundary
    # ------------------------------------------------------------------

    print("\n[10] EXECUTED VALIDATION EVIDENCE")

    print(
        "[NOT ESTABLISHED] Test-file presence does not establish "
        "successful test execution."
    )

    print(
        "[NOT ESTABLISHED] Validation-tool presence does not establish "
        "successful validation."
    )

    print(
        "[NOT ESTABLISHED] Historical evidence does not automatically "
        "constitute current execution evidence."
    )

    warnings += 1

    # ------------------------------------------------------------------
    # 11. Acceptance evidence
    # ------------------------------------------------------------------

    print("\n[11] ACCEPTANCE EVIDENCE")

    print(
        "[NOT ESTABLISHED] Controlled acceptance evidence for this "
        "specific slice."
    )

    warnings += 1

    # ------------------------------------------------------------------
    # 12. Protected boundaries
    # ------------------------------------------------------------------

    print("\n[12] PROTECTED BOUNDARIES")

    print("[PASS] G46.5 reconstruction: NOT PERFORMED")
    print("[PASS] G47 reconstruction: NOT PERFORMED")
    print("[PASS] R097 modification: NOT PERFORMED")
    print("[PASS] Production certification: NOT CLAIMED")

    passed += 4

    # ------------------------------------------------------------------
    # 13. Final worktree observation
    # ------------------------------------------------------------------

    print("\n[13] FINAL WORKTREE STATE")

    final_status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    if not final_status:
        print("[PASS] Worktree unchanged by review")
        passed += 1
    else:
        print("[INFO] Worktree remains:")
        print(final_status)

        # The harness itself may be untracked. That is not a runtime
        # mutation, but it prevents a clean baseline claim.
        warnings += 1

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("BOUNDED SLICE REVIEW RESULT")
    print("=" * 80)

    print(f"PASS : {passed}")
    print(f"WARN : {warnings}")
    print(f"FAIL : {failed}")

    if failed:
        print("\nDecision: SLICE_REVIEW_BLOCKED")
        print("FAIL-CLOSED: no implementation.")
        return 1

    if warnings:
        print("\nDecision: SLICE_REVIEW_REQUIRES_EVIDENCE_REVIEW")
        print(
            "Structural traceability exists, but executed validation "
            "and/or acceptance evidence remains unresolved."
        )
        print("No implementation authorization is inferred.")
        return 0

    print(
        "\nDecision: "
        "SLICE_REVIEW_READY_FOR_CONTROLLED_VALIDATION"
    )
    print(
        "Production operation and production certification remain blocked."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

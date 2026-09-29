#!/usr/bin/env python3

"""
LYRION True Agentic OS
Execution Admission Evidence Review

MODE:
    READ-ONLY / FAIL-CLOSED

Purpose:
    Review existing evidence relevant to the bounded Execution Admission
    slice without executing or modifying the implementation.

This tool does NOT:
    - modify src/
    - modify tests/
    - modify docs/
    - modify manifests
    - execute project tests
    - execute production operations
    - reconstruct G46.5/G47
    - modify R097
    - commit or push
    - claim production certification

Evidence classifications:

    PRESENT
        Artifact/file exists.

    STRUCTURALLY_RELEVANT
        Content contains explicit slice-relevant references.

    EXECUTED_EVIDENCE
        Only assigned when an artifact itself explicitly documents
        attributable execution evidence. Presence alone is insufficient.

    ACCEPTANCE_EVIDENCE
        Only assigned when an artifact explicitly documents controlled
        acceptance for this slice.

    NOT_ESTABLISHED
        The available material does not establish the required state.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

RUNTIME_TARGET = (
    REPO_ROOT / "src/lyrion/execution/validator.py"
)

TEST_ROOT = REPO_ROOT / "tests"
TOOLS_ROOT = REPO_ROOT / "tools" / "phase_b"
DOCS_ROOT = REPO_ROOT / "docs"

SLICE_TERMS = (
    "execution admission",
    "execution_admission",
    "execution admission boundary",
    "execution validator",
    "capability gateway",
    "secure executor",
)

EVIDENCE_TERMS = (
    "executed",
    "execution result",
    "test result",
    "validation result",
    "validation evidence",
    "acceptance",
    "pass",
    "passed",
    "pytest",
)

FORBIDDEN_RECONSTRUCTION_TERMS = (
    "g46.5",
    "g47",
)

R097_TERMS = (
    "r097",
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


def parse_python(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(errors="replace"))
    except (OSError, SyntaxError):
        return None


def imports_runtime_validator(path: Path) -> bool:
    tree = parse_python(path)

    if tree is None:
        return False

    target_module = "lyrion.execution.validator"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == target_module:
                    return True

        elif isinstance(node, ast.ImportFrom):
            if node.module == target_module:
                return True

    return False


def references_validator_symbol(path: Path) -> bool:
    text = path.read_text(errors="replace")

    return bool(
        re.search(
            r"\bvalidator\b|\bExecutionValidator\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def relevant_test_files() -> list[Path]:
    results: list[Path] = []

    if not TEST_ROOT.is_dir():
        return results

    for path in TEST_ROOT.rglob("*.py"):
        if not path.is_file():
            continue

        if imports_runtime_validator(path):
            results.append(path)
            continue

        if references_validator_symbol(path):
            results.append(path)

    return sorted(set(results))


def relevant_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []

    results: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if ".git" in path.parts:
            continue

        if "__pycache__" in path.parts:
            continue

        if "NOT_USABLE_DOCUMENTS" in path.parts:
            continue

        try:
            text = path.read_text(errors="replace").lower()
        except (OSError, UnicodeDecodeError):
            continue

        if any(term in text for term in SLICE_TERMS):
            results.append(path)

    return results


def classify_evidence(path: Path) -> tuple[str, str]:
    """
    Conservative evidence classification.

    This deliberately does NOT infer execution from:
        - filenames
        - file existence
        - test source
        - validation source
        - generic PASS/FAIL strings
    """

    try:
        text = path.read_text(errors="replace")
    except (OSError, UnicodeDecodeError):
        return "NOT_ESTABLISHED", "Unreadable"

    lowered = text.lower()

    explicit_execution_patterns = (
        r"\bexecuted\b",
        r"\bexecution evidence\b",
        r"\btest execution\b",
        r"\bvalidation execution\b",
        r"\bpytest\b.*\bpassed\b",
        r"\b\d+\s+passed\b",
    )

    explicit_acceptance_patterns = (
        r"\bacceptance evidence\b",
        r"\bacceptance result\b",
        r"\baccepted\b",
        r"\bcontrolled acceptance\b",
    )

    acceptance = any(
        re.search(pattern, lowered, flags=re.DOTALL)
        for pattern in explicit_acceptance_patterns
    )

    execution = any(
        re.search(pattern, lowered, flags=re.DOTALL)
        for pattern in explicit_execution_patterns
    )

    if acceptance:
        return "ACCEPTANCE_EVIDENCE", "Explicit acceptance wording found"

    if execution:
        return "EXECUTED_EVIDENCE", "Explicit execution wording found"

    if any(term in lowered for term in EVIDENCE_TERMS):
        return (
            "STRUCTURALLY_RELEVANT",
            "Relevant evidence terminology found; execution not established",
        )

    return "PRESENT", "Artifact exists"


def main() -> int:
    passed = 0
    warnings = 0
    failed = 0

    print("=" * 80)
    print("LYRION TRUE AGENTIC OS")
    print("EXECUTION ADMISSION EVIDENCE REVIEW")
    print("MODE: READ-ONLY / FAIL-CLOSED")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 1. Repository identity
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

    if head == origin:
        print("[PASS] Local HEAD == origin/main")
        passed += 1
    else:
        print("[WARN] Local HEAD differs from origin/main")
        warnings += 1

    # ------------------------------------------------------------------
    # 2. Worktree observation
    # ------------------------------------------------------------------

    print("\n[2] WORKTREE OBSERVATION")

    status = git("status", "--short", "--untracked-files=all")

    if status:
        print("[INFO] Existing changes:")
        print(status)
        warnings += 1
    else:
        print("[PASS] Worktree clean")
        passed += 1

    # ------------------------------------------------------------------
    # 3. Target runtime
    # ------------------------------------------------------------------

    print("\n[3] TARGET RUNTIME")

    if RUNTIME_TARGET.is_file():
        print(f"[PASS] {rel(RUNTIME_TARGET)}")
        print(f"       SHA256: {sha256(RUNTIME_TARGET)}")
        passed += 1
    else:
        print("[FAIL] Execution validator missing")
        failed += 1

    # ------------------------------------------------------------------
    # 4. Validator test mapping
    # ------------------------------------------------------------------

    print("\n[4] EXECUTION VALIDATOR TEST DISCOVERY")

    tests = relevant_test_files()

    if tests:
        print(f"[INFO] Candidate validator-related tests: {len(tests)}")

        direct_imports = []
        symbol_references = []

        for test in tests:
            imported = imports_runtime_validator(test)

            if imported:
                direct_imports.append(test)
                print(f"[PASS] Direct module import: {rel(test)}")
            else:
                symbol_references.append(test)
                print(f"[INFO] Symbol/reference match: {rel(test)}")

        if direct_imports:
            passed += 1
        else:
            warnings += 1

        if symbol_references:
            print(
                "[INFO] Reference matches are NOT treated as direct "
                "runtime-test evidence."
            )
    else:
        print("[WARN] No validator-related tests discovered")
        warnings += 1

    # ------------------------------------------------------------------
    # 5. Validation tooling relevance
    # ------------------------------------------------------------------

    print("\n[5] VALIDATION TOOLING RELEVANCE")

    tool_hits = relevant_files(TOOLS_ROOT)

    if tool_hits:
        print(
            "[PASS] Phase-B validation tooling containing slice references: "
            f"{len(tool_hits)}"
        )

        for path in tool_hits[:30]:
            print(f"       {rel(path)}")

        passed += 1
    else:
        print("[WARN] No slice-relevant validation tooling discovered")
        warnings += 1

    # ------------------------------------------------------------------
    # 6. Documentation relevance
    # ------------------------------------------------------------------

    print("\n[6] DOCUMENTATION RELEVANCE")

    doc_hits = relevant_files(DOCS_ROOT)

    if doc_hits:
        print(
            "[PASS] Slice-relevant documentation artifacts: "
            f"{len(doc_hits)}"
        )

        for path in doc_hits[:30]:
            print(f"       {rel(path)}")

        passed += 1
    else:
        print("[WARN] No slice-relevant documentation discovered")
        warnings += 1

    # ------------------------------------------------------------------
    # 7. Candidate evidence inventory
    # ------------------------------------------------------------------

    print("\n[7] EVIDENCE ARTIFACT INVENTORY")

    evidence_roots = (
        REPO_ROOT / "artifacts",
        REPO_ROOT / "docs" / "phase-b",
        REPO_ROOT / "tools" / "phase_b",
    )

    evidence_candidates: list[Path] = []

    for root in evidence_roots:
        evidence_candidates.extend(relevant_files(root))

    evidence_candidates = sorted(set(evidence_candidates))

    print(
        f"[INFO] Slice-relevant candidate artifacts: "
        f"{len(evidence_candidates)}"
    )

    executed_candidates = []
    acceptance_candidates = []

    for path in evidence_candidates:
        classification, reason = classify_evidence(path)

        if classification == "EXECUTED_EVIDENCE":
            executed_candidates.append(path)

        elif classification == "ACCEPTANCE_EVIDENCE":
            acceptance_candidates.append(path)

        print(
            f"[{classification}] {rel(path)}"
            f" :: {reason}"
        )

    # ------------------------------------------------------------------
    # 8. Executed evidence decision
    # ------------------------------------------------------------------

    print("\n[8] EXECUTED VALIDATION EVIDENCE DECISION")

    if executed_candidates:
        print(
            "[INFO] Candidate artifacts contain explicit execution wording."
        )
        print(
            "[CAUTION] This review does not independently validate the "
            "authenticity or provenance of those execution records."
        )

        for path in executed_candidates:
            print(f"       {rel(path)}")

        warnings += 1
    else:
        print(
            "[NOT ESTABLISHED] No explicit current executed-validation "
            "evidence identified by this bounded review."
        )
        warnings += 1

    # ------------------------------------------------------------------
    # 9. Acceptance evidence decision
    # ------------------------------------------------------------------

    print("\n[9] ACCEPTANCE EVIDENCE DECISION")

    if acceptance_candidates:
        print(
            "[INFO] Candidate acceptance artifacts discovered:"
        )

        for path in acceptance_candidates:
            print(f"       {rel(path)}")

        print(
            "[CAUTION] Candidate discovery is not independent acceptance "
            "verification."
        )

        warnings += 1
    else:
        print(
            "[NOT ESTABLISHED] No explicit current controlled acceptance "
            "evidence identified."
        )
        warnings += 1

    # ------------------------------------------------------------------
    # 10. Protected boundaries
    # ------------------------------------------------------------------

    print("\n[10] PROTECTED BOUNDARIES")

    print("[PASS] G46.5 reconstruction: NOT PERFORMED")
    print("[PASS] G47 reconstruction: NOT PERFORMED")
    print("[PASS] R097 modification: NOT PERFORMED")
    print("[PASS] Production certification: NOT CLAIMED")

    passed += 4

    # ------------------------------------------------------------------
    # 11. Source safety
    # ------------------------------------------------------------------

    print("\n[11] SOURCE SAFETY")

    print("[PASS] No project test execution performed")
    print("[PASS] No runtime execution performed")
    print("[PASS] No filesystem mutation requested")
    print("[PASS] No Git mutation requested")

    passed += 4

    # ------------------------------------------------------------------
    # 12. Final worktree
    # ------------------------------------------------------------------

    print("\n[12] FINAL WORKTREE OBSERVATION")

    final_status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    if final_status:
        print("[INFO] Worktree remains:")
        print(final_status)
        warnings += 1
    else:
        print("[PASS] Worktree clean after review")
        passed += 1

    # ------------------------------------------------------------------
    # Final decision
    # ------------------------------------------------------------------

    print("\n" + "=" * 80)
    print("EXECUTION ADMISSION EVIDENCE REVIEW RESULT")
    print("=" * 80)

    print(f"PASS : {passed}")
    print(f"WARN : {warnings}")
    print(f"FAIL : {failed}")

    if failed:
        print("\nDecision: EVIDENCE_REVIEW_BLOCKED")
        print("FAIL-CLOSED.")
        return 1

    if warnings:
        print("\nDecision: EVIDENCE_REVIEW_REQUIRES_CONTROLLED_VALIDATION")
        print(
            "Structural evidence exists, but current executed validation "
            "and/or controlled acceptance is not independently established."
        )
        print("No implementation authorization is inferred.")
        return 0

    print("\nDecision: EVIDENCE_REVIEW_COMPLETE")
    print(
        "This does NOT authorize production operation or "
        "production certification."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

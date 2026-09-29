#!/usr/bin/env python3

"""
LYRION True Agentic OS
Independent Validation Harness
for Phase-B Repository Evidence Classification Audit v4

READ-ONLY VALIDATION
NO RUNTIME MODIFICATION
NO DOCUMENTATION MODIFICATION
NO MANIFEST MODIFICATION
NO GIT MUTATION

Purpose:
    Independently validate the structural and safety properties of
    phase_b_repository_baseline_audit.py before that audit tooling
    is accepted into the repository baseline.

This validator intentionally does NOT:
    - execute Phase-B implementation
    - execute production services
    - modify source code
    - modify documentation
    - reconstruct G46.5/G47
    - alter R097
    - claim production certification
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

AUDIT_FILE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "audit"
    / "phase_b_repository_baseline_audit.py"
)


FORBIDDEN_RUNTIME_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
)

FORBIDDEN_MUTATION_TERMS = (
    "write_text",
    "write_bytes",
    "unlink(",
    "rename(",
    "replace(",
    "mkdir(",
    "rmdir(",
    "shutil.copy",
    "shutil.move",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "git commit",
    "git push",
    "git reset",
    "git checkout",
)

EXPECTED_EXCLUSIONS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "NOT_USABLE_DOCUMENTS",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def pass_check(name: str, detail: str = "") -> None:
    print(f"[PASS] {name}")
    if detail:
        print(f"       {detail}")


def fail_check(name: str, detail: str = "") -> None:
    print(f"[FAIL] {name}")
    if detail:
        print(f"       {detail}")


def main() -> int:
    passed = 0
    failed = 0

    print("LYRION TRUE AGENTIC OS")
    print("PHASE-B REPOSITORY BASELINE AUDIT v4")
    print("INDEPENDENT VALIDATION HARNESS")
    print("READ-ONLY / FAIL-CLOSED")
    print()

    # ------------------------------------------------------------------
    # 1. Audit file existence
    # ------------------------------------------------------------------

    print("=" * 78)
    print("1. AUDIT FILE")
    print("=" * 78)

    if not AUDIT_FILE.is_file():
        fail_check(
            "Audit file exists",
            str(AUDIT_FILE),
        )
        return 1

    pass_check(
        "Audit file exists",
        str(AUDIT_FILE),
    )
    passed += 1

    audit_text = AUDIT_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )

    # ------------------------------------------------------------------
    # 2. Syntax
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("2. PYTHON SYNTAX")
    print("=" * 78)

    try:
        tree = ast.parse(
            audit_text,
            filename=str(AUDIT_FILE),
        )
    except SyntaxError as exc:
        fail_check(
            "Audit Python syntax",
            str(exc),
        )
        failed += 1
        return 1

    pass_check("Audit Python syntax")
    passed += 1

    # ------------------------------------------------------------------
    # 3. Required read-only architecture markers
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("3. READ-ONLY SAFETY CONTRACT")
    print("=" * 78)

    required_markers = (
        "READ-ONLY",
        "FAIL-CLOSED",
        "NOT ASSESSED BY FILE PRESENCE",
        "PRODUCTION CERTIFICATION",
        "G46.5/G47",
        "R097",
    )

    for marker in required_markers:
        if marker in audit_text:
            pass_check(
                f"Required safety marker: {marker}",
            )
            passed += 1
        else:
            fail_check(
                f"Required safety marker: {marker}",
            )
            failed += 1

    # ------------------------------------------------------------------
    # 4. Evidence boundary contract
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("4. EVIDENCE BOUNDARY CONTRACT")
    print("=" * 78)

    for exclusion in EXPECTED_EXCLUSIONS:
        if exclusion in audit_text:
            pass_check(
                f"Excluded evidence boundary: {exclusion}",
            )
            passed += 1
        else:
            fail_check(
                f"Excluded evidence boundary: {exclusion}",
            )
            failed += 1

    # ------------------------------------------------------------------
    # 5. Test-root restriction
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("5. PROJECT TEST DISCOVERY BOUNDARY")
    print("=" * 78)

    required_test_contract = (
        "TEST_ROOTS",
        "REPO_ROOT / \"tests\"",
        "def project_test_files",
    )

    for marker in required_test_contract:
        if marker in audit_text:
            pass_check(
                f"Test boundary marker: {marker}",
            )
            passed += 1
        else:
            fail_check(
                f"Test boundary marker: {marker}",
            )
            failed += 1

    if "NOT_USABLE_DOCUMENTS" in audit_text:
        pass_check(
            "Historical/unusable documentation explicitly excluded",
        )
        passed += 1
    else:
        fail_check(
            "Historical/unusable documentation explicitly excluded",
        )
        failed += 1

    # ------------------------------------------------------------------
    # 6. Runtime source restriction
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("6. RUNTIME SOURCE BOUNDARY")
    print("=" * 78)

    if "SRC_ROOT = REPO_ROOT / \"src\"" in audit_text:
        pass_check(
            "Runtime implementation discovery restricted to src/",
        )
        passed += 1
    else:
        fail_check(
            "Runtime implementation discovery restricted to src/",
        )
        failed += 1

    validation_boundary_markers = (
        "TOOLS_ROOT = REPO_ROOT / \"tools\" / \"phase_b\"",
        "def validation_files",
        "Validation tooling",
        "tools",
        "phase_b",
    )

    if all(
        marker in audit_text
        for marker in validation_boundary_markers
    ):
        pass_check(
            "Validation tooling is represented separately from runtime",
        )
        passed += 1
    else:
        missing = [
            marker
            for marker in validation_boundary_markers
            if marker not in audit_text
        ]
        fail_check(
            "Validation tooling is represented separately from runtime",
            "missing markers: " + ", ".join(missing),
        )
        failed += 1

    # ------------------------------------------------------------------
    # 7. No filesystem mutation APIs
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("7. FILESYSTEM MUTATION REVIEW")
    print("=" * 78)

    dangerous_mutations = (
        "write_text(",
        "write_bytes(",
        "unlink(",
        "rename(",
        "replace(",
        "mkdir(",
        "rmdir(",
        "shutil.copy",
        "shutil.move",
    )

    for token in dangerous_mutations:
        if token in audit_text:
            fail_check(
                f"No filesystem mutation: {token}",
            )
            failed += 1
        else:
            pass_check(
                f"No filesystem mutation: {token}",
            )
            passed += 1

    # ------------------------------------------------------------------
    # 8. Git mutation review
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("8. GIT MUTATION REVIEW")
    print("=" * 78)

    forbidden_git_tokens = (
        "git commit",
        "git push",
        "git reset",
        "git checkout",
        "git clean",
    )

    for token in forbidden_git_tokens:
        if token in audit_text:
            fail_check(
                f"No Git mutation command: {token}",
            )
            failed += 1
        else:
            pass_check(
                f"No Git mutation command: {token}",
            )
            passed += 1

    # ------------------------------------------------------------------
    # 9. Production certification boundary
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("9. PRODUCTION CERTIFICATION BOUNDARY")
    print("=" * 78)

    certification_markers = (
        "Production Certification",
        "PRODUCTION CERTIFICATION",
        "makes no certification claim",
        "Production certification     : NOT CLAIMED",
    )

    for marker in certification_markers:
        if marker in audit_text:
            pass_check(
                f"Certification boundary preserved: {marker}",
            )
            passed += 1
        else:
            fail_check(
                f"Certification boundary preserved: {marker}",
            )
            failed += 1

    # ------------------------------------------------------------------
    # 10. G46.5 / G47 reconstruction protection
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("10. G46.5 / G47 PROVENANCE BOUNDARY")
    print("=" * 78)

    if "G46.5/G47 reconstruction     : NOT PERFORMED" in audit_text:
        pass_check(
            "G46.5/G47 reconstruction remains prohibited",
        )
        passed += 1
    else:
        fail_check(
            "G46.5/G47 reconstruction remains prohibited",
        )
        failed += 1

    # ------------------------------------------------------------------
    # 11. R097 protection
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("11. R097 GOVERNANCE BOUNDARY")
    print("=" * 78)

    if "R097 governance change       : NONE" in audit_text:
        pass_check(
            "R097 remains unchanged",
        )
        passed += 1
    else:
        fail_check(
            "R097 remains unchanged",
        )
        failed += 1

    # ------------------------------------------------------------------
    # 12. AST-level dangerous calls
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("12. AST MUTATION REVIEW")
    print("=" * 78)

    dangerous_call_names = {
        "write_text",
        "write_bytes",
        "unlink",
        "rename",
        "replace",
        "mkdir",
        "rmdir",
        "copy",
        "move",
    }

    dangerous_calls_found: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function_name = None

        if isinstance(node.func, ast.Name):
            function_name = node.func.id

        elif isinstance(node.func, ast.Attribute):
            function_name = node.func.attr

        if function_name in dangerous_call_names:
            dangerous_calls_found.append(function_name)

    if dangerous_calls_found:
        fail_check(
            "AST mutation review",
            ", ".join(sorted(set(dangerous_calls_found))),
        )
        failed += 1
    else:
        pass_check(
            "AST mutation review",
            "no filesystem mutation calls detected",
        )
        passed += 1

    # ------------------------------------------------------------------
    # 13. Current Git state — observation only
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("13. CURRENT GIT STATE")
    print("=" * 78)

    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    status = git("status", "--short")

    print(f"Branch : {branch}")
    print(f"HEAD   : {head}")
    print(
        "Status : "
        + ("CLEAN" if not status else "WORKTREE HAS CHANGES")
    )

    # This validator must not modify or reject the audit merely because
    # the audit file itself is currently uncommitted.
    pass_check(
        "Git state inspected without mutation",
    )
    passed += 1

    # ------------------------------------------------------------------
    # 14. Integrity hash
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("14. AUDIT FILE INTEGRITY")
    print("=" * 78)

    print(f"SHA256 : {sha256(AUDIT_FILE)}")

    pass_check(
        "Audit file SHA-256 generated",
    )
    passed += 1

    # ------------------------------------------------------------------
    # 15. Final decision
    # ------------------------------------------------------------------

    print()
    print("=" * 78)
    print("15. VALIDATION DECISION")
    print("=" * 78)

    print(f"PASS : {passed}")
    print(f"FAIL : {failed}")

    if failed:
        print("Decision : AUDIT_V4_VALIDATION_FAILED")
        print()
        print("FAIL-CLOSED:")
        print("  Audit v4 must NOT be accepted into the baseline.")
        print("  Phase-B implementation remains untouched.")
        print("  No Git commit/push performed.")
        return 1

    print("Decision : AUDIT_V4_VALIDATED")
    print()
    print("FAIL-CLOSED SAFETY BOUNDARY:")
    print("  Phase-B implementation : NOT EXECUTED")
    print("  Runtime mutation       : NONE")
    print("  Documentation mutation : NONE")
    print("  Manifest mutation      : NONE")
    print("  Git mutation            : NONE")
    print("  G46.5/G47 reconstruction: NOT PERFORMED")
    print("  R097 governance change : NONE")
    print("  Production certification: NOT CLAIMED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
PB-DOC-021 — Final Code Quality / Security Audit

Audit-only validation.

This script:
- validates Python syntax;
- runs Ruff;
- runs mypy;
- checks for repository-specific hard-coded paths;
- checks for privileged/runtime integration;
- checks for governance mutation primitives;
- checks that PB-DOC-021 remains isolated from runtime execution;
- verifies the real governance manifest is unchanged;
- reviews the working-tree diff for the two PB-DOC-021 implementation files.

It does not modify governance state and does not execute privileged operations.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GATE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_pbdoc_021_implementation_authorization_gate.py"
)

NEGATIVE_TESTS = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_pbdoc_021_negative_tests.py"
)

REAL_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

TARGETS = (GATE, NEGATIVE_TESTS)

FORBIDDEN_RUNTIME_IMPORTS = (
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "os.exec",
    "os.spawn",
    "socket.",
)

FORBIDDEN_PRIVILEGED_TERMS = (
    "sudo ",
    "pkexec ",
    "setuid(",
    "setgid(",
    "cap_set",
)

FORBIDDEN_GOVERNANCE_MUTATION = (
    ".write_text(",
    ".write_bytes(",
    "unlink(",
    "rename(",
    "replace(",
    "chmod(",
)

# This audit itself invokes subprocesses for validation. Therefore the
# subprocess restriction applies specifically to the PB-DOC-021 gate
# implementation, not to this audit harness.
GATE_FORBIDDEN_RUNTIME_IMPORTS = (
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "os.exec",
    "os.spawn",
    "socket.",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    command: list[str],
    *,
    cwd: Path = REPO_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def require_pass(
    name: str,
    result: subprocess.CompletedProcess[str],
) -> None:
    if result.returncode != 0:
        print(f"FAIL  {name}")
        print(result.stdout)
        print(result.stderr)
        raise SystemExit(1)

    print(f"PASS  {name}")


def read_target(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def audit_syntax() -> None:
    require_pass(
        "PY_COMPILE",
        run(
            [
                sys.executable,
                "-m",
                "py_compile",
                *(str(path) for path in TARGETS),
            ]
        ),
    )


def audit_ruff() -> None:
    require_pass(
        "RUFF",
        run(
            [
                "ruff",
                "check",
                *(str(path) for path in TARGETS),
            ]
        ),
    )


def audit_mypy() -> None:
    require_pass(
        "MYPY",
        run(
            [
                "mypy",
                "--follow-imports=skip",
                *(str(path) for path in TARGETS),
            ]
        ),
    )


def audit_no_hardcoded_repo_path() -> None:
    forbidden = str(REPO_ROOT)

    for path in TARGETS:
        text = read_target(path)

        if forbidden in text:
            print(f"FAIL  HARD_CODED_REPO_PATH: {path}")
            raise SystemExit(1)

    print("PASS  HARD_CODED_REPO_PATH")


def audit_gate_runtime_isolation() -> None:
    text = read_target(GATE)

    for term in GATE_FORBIDDEN_RUNTIME_IMPORTS:
        if term in text:
            print(
                f"FAIL  GATE_RUNTIME_ISOLATION: "
                f"forbidden term {term!r} in {GATE}"
            )
            raise SystemExit(1)

    for term in FORBIDDEN_PRIVILEGED_TERMS:
        if term in text:
            print(
                f"FAIL  GATE_PRIVILEGED_OPERATION: "
                f"forbidden term {term!r} in {GATE}"
            )
            raise SystemExit(1)

    print("PASS  GATE_RUNTIME_ISOLATION")


def audit_gate_does_not_mutate_governance() -> None:
    text = read_target(GATE)

    # The gate must read the manifest but never write, rename, replace,
    # delete, or chmod governance state.
    for term in FORBIDDEN_GOVERNANCE_MUTATION:
        if term in text:
            print(
                f"FAIL  GATE_GOVERNANCE_MUTATION: "
                f"forbidden operation {term!r} in {GATE}"
            )
            raise SystemExit(1)

    print("PASS  GATE_GOVERNANCE_MUTATION")


def audit_gate_does_not_grant_authorization() -> None:
    text = read_target(GATE)

    required_safe_patterns = (
        'decision="DENY"',
        'reason_code="IMPLEMENTATION_AUTHORIZATION_NOT_GRANTED"',
        'reason_code="EXPLICIT_IMPLEMENTATION_AUTHORIZATION_PRESENT"',
    )

    for pattern in required_safe_patterns:
        if pattern not in text:
            print(
                f"FAIL  AUTHORIZATION_SEMANTICS: "
                f"missing required pattern {pattern!r}"
            )
            raise SystemExit(1)

    # Authorization may only produce ALLOW after explicitly reading the
    # AUTHORIZED governance state.
    required_sequence = (
        'governance.implementation_authorization == "NOT AUTHORIZED"',
        'governance.implementation_authorization != "AUTHORIZED"',
        'decision="ALLOW"',
    )

    position = -1

    for pattern in required_sequence:
        current = text.find(pattern, position + 1)

        if current == -1:
            print(
                f"FAIL  AUTHORIZATION_SEMANTICS: "
                f"required ordering missing for {pattern!r}"
            )
            raise SystemExit(1)

        position = current

    print("PASS  AUTHORIZATION_SEMANTICS")


def audit_production_certification_separation() -> None:
    text = read_target(GATE)

    required = (
        "production_certification",
        "Certification is a separate",
    )

    for pattern in required:
        if pattern not in text:
            print(
                f"FAIL  CERTIFICATION_SEPARATION: "
                f"missing {pattern!r}"
            )
            raise SystemExit(1)

    print("PASS  CERTIFICATION_SEPARATION")


def audit_real_manifest_integrity(before_sha256: str) -> None:
    after_sha256 = sha256(REAL_MANIFEST)

    if before_sha256 != after_sha256:
        print("FAIL  REAL_MANIFEST_INTEGRITY")
        print(f"Before: {before_sha256}")
        print(f"After:  {after_sha256}")
        raise SystemExit(1)

    print("PASS  REAL_MANIFEST_INTEGRITY")


def audit_git_diff() -> None:
    result = run(
        [
            "git",
            "diff",
            "--check",
            "--",
            str(GATE.relative_to(REPO_ROOT)),
            str(NEGATIVE_TESTS.relative_to(REPO_ROOT)),
        ]
    )

    require_pass("GIT_DIFF_CHECK", result)


def audit_expected_files() -> None:
    for path in TARGETS:
        if not path.is_file():
            print(f"FAIL  EXPECTED_FILE: {path}")
            raise SystemExit(1)

    print("PASS  EXPECTED_FILES")


def main() -> int:
    print("PB-DOC-021 — FINAL CODE QUALITY / SECURITY AUDIT")
    print("=" * 60)
    print(f"GATE: {GATE}")
    print(f"NEGATIVE TESTS: {NEGATIVE_TESTS}")
    print(f"REAL MANIFEST: {REAL_MANIFEST}")
    print()

    before_sha256 = sha256(REAL_MANIFEST)

    audit_expected_files()
    audit_syntax()
    audit_ruff()
    audit_mypy()
    audit_no_hardcoded_repo_path()
    audit_gate_runtime_isolation()
    audit_gate_does_not_mutate_governance()
    audit_gate_does_not_grant_authorization()
    audit_production_certification_separation()
    audit_git_diff()

    audit_real_manifest_integrity(before_sha256)

    print()
    print("AUDIT RESULT: PASS")
    print("GOVERNANCE MUTATION: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("REAL MANIFEST: UNCHANGED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

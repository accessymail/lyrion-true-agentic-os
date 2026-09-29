#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Implementation Readiness Evidence Gate

Purpose
-------
Determine whether the approved Phase-B architecture/evidence corpus is
structurally and semantically ready for a FORMAL IMPLEMENTATION
AUTHORIZATION REVIEW.

This gate does NOT:
- authorize implementation;
- modify governance state;
- modify documentation;
- execute privileged operations;
- deploy software;
- alter the Master Manifest.

Core invariant
--------------
ARCHITECTURE APPROVED != IMPLEMENTATION AUTHORIZED

Current expected state
----------------------
Architecture Approval       = APPROVED
Implementation Authorization = NOT AUTHORIZED
Production Implementation   = BLOCKED
Production Certification    = NOT CLAIMED

Decision semantics
------------------
READY_FOR_AUTHORIZATION_REVIEW means the evidence baseline is sufficiently
validated for a separate human/governance authorization decision.

It does NOT mean implementation is authorized.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

DOCUMENTATION_VALIDATOR = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_phase_b_documentation.py"
)

PB021_GATE = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_pbdoc_021_implementation_authorization_gate.py"
)

PB021_NEGATIVE_TESTS = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "validate_pbdoc_021_negative_tests.py"
)

PB021_FINAL_AUDIT = (
    REPO_ROOT
    / "tools"
    / "phase_b"
    / "audit_pbdoc_021_final.py"
)


EXPECTED_GOVERNANCE = {
    "Architecture Approval": "APPROVED",
    "Implementation Authorization": "NOT AUTHORIZED",
    "Production Implementation": "BLOCKED",
    "Production Certification": "NOT CLAIMED",
}


class ReadinessError(RuntimeError):
    """Raised when readiness validation cannot safely complete."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ReadinessError(f"MISSING_REQUIRED_FILE:{label}:{path}")


def read_text(path: Path, label: str) -> str:
    require_file(path, label)

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReadinessError(
            f"UNREADABLE_REQUIRED_FILE:{label}:{exc}"
        ) from exc


def parse_authoritative_governance(text: str) -> dict[str, str]:
    """
    Parse ONLY the authoritative Markdown governance table.

    Prose elsewhere in the manifest cannot override this table.
    """
    table_pattern = re.compile(
        r"^\|\s*Control\s*\|\s*State\s*\|\s*$"
        r".*?"
        r"^\|\s*---+\s*\|\s*---+\s*\|\s*$"
        r"(?P<body>.*?)(?=^\s*$|^#)",
        re.MULTILINE | re.DOTALL,
    )

    match = table_pattern.search(text)

    if not match:
        raise ReadinessError(
            "FAIL_CLOSED:MISSING_AUTHORITATIVE_GOVERNANCE_TABLE"
        )

    states: dict[str, str] = {}

    row_pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
        re.MULTILINE,
    )

    for row in row_pattern.finditer(match.group("body")):
        key = row.group(1).strip()
        value = row.group(2).strip()

        if key in EXPECTED_GOVERNANCE:
            if key in states:
                raise ReadinessError(
                    f"FAIL_CLOSED:DUPLICATE_GOVERNANCE_STATE:{key}"
                )

            states[key] = value

    missing = [
        key
        for key in EXPECTED_GOVERNANCE
        if key not in states
    ]

    if missing:
        raise ReadinessError(
            "FAIL_CLOSED:MISSING_GOVERNANCE_STATE:"
            + ",".join(missing)
        )

    return states


def verify_governance(text: str) -> None:
    states = parse_authoritative_governance(text)

    for key, expected in EXPECTED_GOVERNANCE.items():
        actual = states[key]

        if actual != expected:
            raise ReadinessError(
                "GOVERNANCE_STATE_MISMATCH:"
                f"{key}:expected={expected}:actual={actual}"
            )

        print(f"PASS: {key} = {actual}")


def verify_manifest_identity(text: str) -> None:
    required = (
        r"\*\*Document ID:\*\*\s*TAOS-PHASE-B-MANIFEST-001",
        r"\*\*Version:\*\*\s*1\.0\.0",
        r"\*\*Project:\*\*\s*LYRION True Agentic OS",
        r"\*\*Phase:\*\*\s*Phase B",
    )

    for pattern in required:
        if not re.search(pattern, text):
            raise ReadinessError(
                f"FAIL_CLOSED:MANIFEST_IDENTITY_MISMATCH:{pattern}"
            )

    print("PASS: Master Manifest identity")


def verify_phase_b_registry_references(text: str) -> None:
    """
    Verify that the authoritative Master Manifest references PB-DOC-001
    through PB-DOC-021.

    This does not infer document paths. The existing documentation validator
    remains responsible for detailed document integrity and semantics.
    """
    missing = []

    for number in range(1, 22):
        reference = f"PB-DOC-{number:03d}"

        if reference not in text:
            missing.append(reference)

    if missing:
        raise ReadinessError(
            "FAIL_CLOSED:MISSING_PHASE_B_REGISTRY_REFERENCES:"
            + ",".join(missing)
        )

    print("PASS: PB-DOC-001 through PB-DOC-021 registry references")


def run_validator(
    label: str,
    command: list[str],
    *,
    required_output: tuple[str, ...] = (),
) -> None:
    print()
    print(f"===== {label} =====")

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    if result.returncode != 0:
        raise ReadinessError(
            f"{label}:VALIDATOR_FAILED:exit={result.returncode}"
        )

    combined = f"{result.stdout}\n{result.stderr}"

    for required in required_output:
        if required not in combined:
            raise ReadinessError(
                f"{label}:MISSING_REQUIRED_EVIDENCE:{required}"
            )

    print(f"PASS: {label}")


def verify_read_only_contract() -> None:
    """
    Verify the executable AST for prohibited filesystem mutation,
    privileged OS operations, and unsafe subprocess execution.

    AST inspection is intentional: security-control strings, comments,
    documentation, and this function's own detection rules must not create
    false positives.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(Path(__file__)))

    violations: list[str] = []

    forbidden_method_calls = {
        "write_text",
        "write_bytes",
        "unlink",
        "rename",
        "replace",
        "chmod",
        "mkdir",
        "rmdir",
    }

    forbidden_os_calls = {
        "system",
        "popen",
        "execl",
        "execle",
        "execlp",
        "execv",
        "execve",
        "execvp",
        "execvpe",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "setuid",
        "setgid",
        "seteuid",
        "setegid",
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Attribute):
            method = node.func.attr

            if method in forbidden_method_calls:
                violations.append(
                    f"filesystem mutation call: .{method}() "
                    f"at line {node.lineno}"
                )

            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
                and method in forbidden_os_calls
            ):
                violations.append(
                    f"privileged/system os call: os.{method}() "
                    f"at line {node.lineno}"
                )

        # subprocess.run is allowed because this readiness gate invokes
        # existing validation tools. Shell execution is never permitted.
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr == "run"
        ):
            for keyword in node.keywords:
                if (
                    keyword.arg == "shell"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                ):
                    violations.append(
                        f"subprocess.run(shell=True) at line {node.lineno}"
                    )

            # Reject literal privileged executables.
            command_literals: list[str] = []

            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    command_literals.append(arg.value)

            for keyword in node.keywords:
                if keyword.arg in {"args", "executable"}:
                    value = keyword.value
                    if isinstance(value, ast.Constant) and isinstance(
                        value.value, str
                    ):
                        command_literals.append(value.value)

            for literal in command_literals:
                tokens = literal.strip().split()
                if tokens and tokens[0] in {"sudo", "pkexec"}:
                    violations.append(
                        f"privileged subprocess executable "
                        f"'{tokens[0]}' at line {node.lineno}"
                    )

    if violations:
        raise ReadinessError(
            "FAIL_CLOSED:READ_ONLY_CONTRACT_VIOLATION:"
            + "; ".join(violations)
        )

    print("PASS: readiness gate read-only contract")


def verify_no_authorization_grant(text: str) -> None:

    prohibited_states = (
        "Implementation Authorization: AUTHORIZED",
        "Production Implementation: AUTHORIZED",
        "Production Certification: CERTIFIED",
    )

    for state in prohibited_states:
        if state in text:
            raise ReadinessError(
                f"FAIL_CLOSED:PROHIBITED_AUTHORIZATION_STATE:{state}"
            )

    required_boundaries = (
        "Implementation Authorization: NOT AUTHORIZED",
        "Production Implementation: BLOCKED",
        "Production Certification: NOT CLAIMED",
    )

    for boundary in required_boundaries:
        if boundary not in text:
            raise ReadinessError(
                f"FAIL_CLOSED:MISSING_AUTHORIZATION_BOUNDARY:{boundary}"
            )

    print("PASS: authorization boundary preserved")


def verify_manifest_unchanged(
    before_hash: str,
    after_hash: str,
) -> None:
    if before_hash != after_hash:
        raise ReadinessError(
            "FAIL_CLOSED:MASTER_MANIFEST_MUTATED_DURING_VALIDATION"
        )

    print("PASS: Master Manifest unchanged")


def main() -> int:
    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B IMPLEMENTATION READINESS EVIDENCE GATE"
    )
    print("=" * 108)
    print(f"Repository: {REPO_ROOT}")
    print("Mode: READ-ONLY")
    print("Authority: Evidence readiness review only")
    print()

    try:
        verify_read_only_contract()

        manifest_text = read_text(
            MASTER_MANIFEST,
            "Phase-B Master Manifest",
        )

        before_hash = sha256(MASTER_MANIFEST)

        print("===== AUTHORITATIVE GOVERNANCE =====")
        verify_manifest_identity(manifest_text)
        verify_governance(manifest_text)
        verify_phase_b_registry_references(manifest_text)
        verify_no_authorization_grant(manifest_text)

        run_validator(
            "PHASE-B DOCUMENTATION VALIDATION",
            [sys.executable, str(DOCUMENTATION_VALIDATOR)],
            required_output=(
                "RESULT: PASS",
                "Architecture Approval",
                "Implementation Authorization",
                "Production Implementation",
                "Production Certification",
            ),
        )

        run_validator(
            "PB-DOC-021 AUTHORIZATION GATE",
            [
                sys.executable,
                str(PB021_GATE),
                "--require-current-deny",
            ],
            required_output=(
                "DECISION: DENY",
                "AUTHORIZATION GRANT: NONE",
                "MUTATION: NONE",
                "PRIVILEGED EXECUTION: NONE",
            ),
        )

        run_validator(
            "PB-DOC-021 NEGATIVE TESTS",
            [sys.executable, str(PB021_NEGATIVE_TESTS)],
            required_output=(
                "TESTS PASSED: 10/10",
                "REAL MANIFEST MUTATION: NONE",
                "AUTHORIZATION GRANT: NONE",
                "PRIVILEGED EXECUTION: NONE",
            ),
        )

        run_validator(
            "PB-DOC-021 FINAL AUDIT",
            [sys.executable, str(PB021_FINAL_AUDIT)],
            required_output=(
                "AUDIT RESULT: PASS",
                "GOVERNANCE MUTATION: NONE",
                "PRIVILEGED EXECUTION: NONE",
                "AUTHORIZATION GRANT: NONE",
                "REAL MANIFEST: UNCHANGED",
            ),
        )

        after_hash = sha256(MASTER_MANIFEST)
        verify_manifest_unchanged(before_hash, after_hash)

        print()
        print("=" * 108)
        print("IMPLEMENTATION READINESS DECISION")
        print("=" * 108)

        print("Evidence Baseline          : PASS")
        print("Architecture Approval      : APPROVED")
        print("Implementation Authorization: NOT AUTHORIZED")
        print("Production Implementation  : BLOCKED")
        print("Production Certification   : NOT CLAIMED")
        print()
        print(
            "READINESS DECISION: "
            "READY_FOR_FORMAL_IMPLEMENTATION_AUTHORIZATION_REVIEW"
        )
        print()
        print("AUTHORIZATION GRANT: NONE")
        print("GOVERNANCE MUTATION: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        print(f"MASTER MANIFEST SHA256: {after_hash}")
        print()
        print(
            "IMPORTANT: This gate only establishes evidence readiness."
        )
        print(
            "It does NOT authorize Phase-B implementation."
        )
        print(
            "It does NOT change the Master Manifest."
        )
        print(
            "A separate formal implementation-authorization decision "
            "remains required."
        )
        print()
        print(
            "RESULT: PASS — IMPLEMENTATION READINESS EVIDENCE "
            "VALIDATION COMPLETED"
        )

        return 0

    except ReadinessError as exc:
        print()
        print("=" * 108)
        print("IMPLEMENTATION READINESS DECISION")
        print("=" * 108)
        print("READINESS DECISION: FAIL_CLOSED")
        print(f"REASON: {exc}")
        print("AUTHORIZATION GRANT: NONE")
        print("GOVERNANCE MUTATION: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        print("RESULT: FAIL")
        return 2


if __name__ == "__main__":
    sys.exit(main())

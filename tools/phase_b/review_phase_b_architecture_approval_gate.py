#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Formal Architecture Approval Review Gate

READ-ONLY GOVERNANCE TOOL

Purpose
-------
Perform the final machine-verifiable pre-review checks before the
human Architecture Approval decision.

This tool does NOT:
    - approve the architecture
    - modify documentation
    - modify manifests
    - authorize implementation
    - implement Phase B
    - claim production readiness
    - claim certification

Required state before human review:

    Evidence Consolidation       = PASS
    Architecture Approval        = PENDING
    Implementation Authorization = NOT AUTHORIZED
    Production Implementation    = BLOCKED
    Production Certification     = NOT CLAIMED

Final output when all checks pass:

    READY FOR FORMAL HUMAN ARCHITECTURE APPROVAL REVIEW

The human approval decision remains a separate governance action.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

CONSOLIDATION_TOOL = (
    REPO_ROOT
    / "tools/phase_b/"
    "consolidate_phase_b_architecture_approval_evidence.py"
)

DOCUMENT_ROOT = REPO_ROOT / "docs/phase-b"

REQUIRED_DOCUMENT_COUNT = 20


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def verify_repository() -> bool:
    return REPO_ROOT.is_dir()


def verify_master_manifest() -> bool:
    return MASTER_MANIFEST.is_file()


def verify_consolidation_tool() -> bool:
    return CONSOLIDATION_TOOL.is_file()


def verify_canonical_documents() -> tuple[bool, int]:
    """
    Verify that exactly the expected PB-DOC registry count is represented
    by canonical Phase-B documentation paths.

    This check intentionally does not modify or discover alternate files.
    """

    canonical_names = [
        "requirements/LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",
        "agentic-runtime/LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",
        "identity-authority/LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",
        "capability/LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",
        "agent-harness/LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",
        "host-harness/LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",
        "universal-computer/LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",
        "application-harness/LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",
        "execution-admission/LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
        "aegis/LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",
        "secure-execution/LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",
        "interfaces/LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",
        "data/LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",
        "memory/LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",
        "observability/LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",
        "validation/LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",
        "security-testing/LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",
        "operations/LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",
        "recovery/LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",
        "governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    ]

    existing = 0

    for relative in canonical_names:
        if (DOCUMENT_ROOT / relative).is_file():
            existing += 1

    return (
        existing == REQUIRED_DOCUMENT_COUNT,
        existing,
    )


def extract_governance_state() -> dict[str, str]:
    text = read(MASTER_MANIFEST)

    fields = {
        "Architecture Approval": "UNKNOWN",
        "Implementation Authorization": "UNKNOWN",
        "Production Implementation": "UNKNOWN",
        "Production Certification": "UNKNOWN",
    }

    patterns = {
        field: re.compile(
            rf"(?im)"
            rf"^\s*(?:[-+>]\s*)?"
            rf"(?:\|\s*)?"
            rf"{re.escape(field)}"
            rf"\s*(?::|\||=|-)\s*"
            rf"(.+?)"
            rf"\s*(?:\|)?\s*$"
        )
        for field in fields
    }

    for field, pattern in patterns.items():
        match = pattern.search(text)
        if match:
            fields[field] = match.group(1).strip()

    return fields


def verify_governance_state() -> bool:
    state = extract_governance_state()

    expected = {
        "Architecture Approval": "PENDING",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    safe = True

    print()
    print("=" * 108)
    print("GOVERNANCE STATE")
    print("=" * 108)

    for field, expected_value in expected.items():
        actual = state[field]

        passed = actual.upper() == expected_value

        print(
            f"{field:<34}: "
            f"{'PASS' if passed else 'FAIL'} "
            f"(actual={actual!r}, expected={expected_value!r})"
        )

        safe &= passed

    return safe


def run_consolidation_audit() -> tuple[bool, str]:
    """
    Execute the existing read-only consolidation auditor.

    Its stdout is captured and inspected.
    """

    print()
    print("=" * 108)
    print("FINAL EVIDENCE CONSOLIDATION RECHECK")
    print("=" * 108)

    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(CONSOLIDATION_TOOL),
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        print(
            f"Unable to execute consolidation auditor: {exc}"
        )
        return False, ""

    output = completed.stdout + completed.stderr

    result_pass = (
        "RESULT: PHASE-B ARCHITECTURE APPROVAL "
        "EVIDENCE CONSOLIDATION PASS."
        in output
    )

    all_twenty = (
        "Evidence categories PASS : 20/20"
        in output
        and
        "Evidence categories REVIEW : 0/20"
        in output
    )

    governance_safe = (
        "Architecture Approval           : PASS"
        in output
        and
        "Implementation Authorization    : PASS"
        in output
        and
        "Production Implementation       : PASS"
        in output
        and
        "Production Certification        : PASS"
        in output
    )

    passed = (
        completed.returncode == 0
        and result_pass
        and all_twenty
        and governance_safe
    )

    print(
        "Consolidation execution : "
        + ("PASS" if completed.returncode == 0 else "FAIL")
    )

    print(
        "20/20 evidence          : "
        + ("PASS" if all_twenty else "FAIL")
    )

    print(
        "Consolidation result    : "
        + ("PASS" if result_pass else "FAIL")
    )

    print(
        "Governance safety       : "
        + ("PASS" if governance_safe else "FAIL")
    )

    return passed, output


def verify_no_implementation_authorization() -> bool:
    """
    Defensive guard against accidentally treating evidence validation
    as implementation authorization.
    """

    text = read(MASTER_MANIFEST)

    forbidden_authorization_states = (
        "Implementation Authorization: AUTHORIZED",
        "Implementation Authorization: APPROVED",
        "Implementation Authorization: GRANTED",
    )

    safe = not any(
        marker.lower() in text.lower()
        for marker in forbidden_authorization_states
    )

    print()
    print("=" * 108)
    print("IMPLEMENTATION-AUTHORIZATION SAFETY GUARD")
    print("=" * 108)

    print(
        "Implementation authorization detected : "
        + ("UNSAFE" if not safe else "NOT AUTHORIZED")
    )

    return safe


def verify_read_only_contract() -> bool:
    """
    AST-based read-only contract verification.

    The previous implementation searched for mutation-marker strings.
    That caused a false positive because the marker list itself contained
    those strings.

    This implementation inspects actual Python call expressions instead.
    """

    import ast

    source = read(Path(__file__))

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print()
        print("=" * 108)
        print("READ-ONLY CONTRACT")
        print("=" * 108)
        print(
            f"AST parsing failed: {exc}"
        )
        return False

    forbidden_calls = {
        "write_text",
        "write_bytes",
        "unlink",
        "rmdir",
        "mkdir",
        "touch",
        "copy",
        "copy2",
        "copytree",
        "move",
        "remove",
        "rename",
        "replace",
        "symlink",
        "link",
        "chmod",
        "chown",
    }

    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function_name = None

        if isinstance(node.func, ast.Attribute):
            function_name = node.func.attr

        elif isinstance(node.func, ast.Name):
            function_name = node.func.id

        if function_name in forbidden_calls:
            violations.append(
                f"{function_name}@line{node.lineno}"
            )

    print()
    print("=" * 108)
    print("READ-ONLY CONTRACT")
    print("=" * 108)

    if violations:
        print(
            "Actual filesystem mutation calls detected: "
            + ", ".join(violations)
        )
        return False

    print(
        "Actual filesystem mutation calls : NONE"
    )

    print(
        "AST read-only contract           : PASS"
    )

    print(
        "Document modification             : NOT PERFORMED"
    )

    return True

def print_final_result(
    inventory_ok: bool,
    consolidation_ok: bool,
    governance_ok: bool,
    authorization_guard_ok: bool,
    readonly_ok: bool,
) -> int:

    print()
    print("=" * 108)
    print("FINAL PHASE-B ARCHITECTURE APPROVAL REVIEW GATE")
    print("=" * 108)

    print(
        "Canonical documentation inventory : "
        + ("PASS" if inventory_ok else "FAIL")
    )

    print(
        "Evidence consolidation            : "
        + ("PASS" if consolidation_ok else "FAIL")
    )

    print(
        "Governance state                   : "
        + ("PASS" if governance_ok else "FAIL")
    )

    print(
        "Implementation authorization guard: "
        + ("PASS" if authorization_guard_ok else "FAIL")
    )

    print(
        "Read-only contract                 : "
        + ("PASS" if readonly_ok else "FAIL")
    )

    print()

    if not all(
        (
            inventory_ok,
            consolidation_ok,
            governance_ok,
            authorization_guard_ok,
            readonly_ok,
        )
    ):
        print(
            "RESULT: ARCHITECTURE APPROVAL REVIEW GATE "
            "NOT READY."
        )
        print()
        print(
            "Architecture Approval remains PENDING."
        )
        print(
            "Implementation Authorization remains NOT AUTHORIZED."
        )
        print(
            "Production Implementation remains BLOCKED."
        )
        print(
            "Production Certification remains NOT CLAIMED."
        )

        return 1

    print(
        "RESULT: READY FOR FORMAL HUMAN "
        "ARCHITECTURE APPROVAL REVIEW."
    )

    print()
    print(
        "Evidence Consolidation : PASS"
    )

    print(
        "Evidence Categories    : 20/20 PASS"
    )

    print(
        "Architecture Approval  : PENDING"
    )

    print(
        "Implementation          : NOT AUTHORIZED"
    )

    print(
        "Production              : BLOCKED"
    )

    print(
        "Certification           : NOT CLAIMED"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This gate prepares the evidence for human review."
    )

    print(
        "It does NOT grant Architecture Approval."
    )

    print(
        "It does NOT authorize Phase-B implementation."
    )

    print(
        "It does NOT change any project documentation."
    )

    return 0


def main() -> int:
    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "FORMAL PHASE-B ARCHITECTURE APPROVAL REVIEW GATE"
    )
    print("=" * 108)

    print(
        f"Repository : {REPO_ROOT}"
    )

    print(
        "Mode       : READ-ONLY"
    )

    print(
        "Authority  : Evidence preparation only"
    )

    repository_ok = verify_repository()

    if not repository_ok:
        print(
            "RESULT: Repository not found."
        )
        return 2

    manifest_ok = verify_master_manifest()
    consolidation_tool_ok = verify_consolidation_tool()

    print()
    print("=" * 108)
    print("PRECONDITIONS")
    print("=" * 108)

    print(
        "Repository                  : "
        + ("PASS" if repository_ok else "FAIL")
    )

    print(
        "Master Manifest             : "
        + ("PASS" if manifest_ok else "FAIL")
    )

    print(
        "Consolidation auditor       : "
        + ("PASS" if consolidation_tool_ok else "FAIL")
    )

    if not (
        manifest_ok
        and consolidation_tool_ok
    ):
        print()
        print(
            "RESULT: PRECONDITION FAILURE."
        )
        return 2

    inventory_ok, count = verify_canonical_documents()

    print(
        "Canonical PB-DOC inventory  : "
        f"{'PASS' if inventory_ok else 'FAIL'} "
        f"({count}/{REQUIRED_DOCUMENT_COUNT})"
    )

    consolidation_ok, _ = run_consolidation_audit()

    governance_ok = verify_governance_state()

    authorization_guard_ok = (
        verify_no_implementation_authorization()
    )

    readonly_ok = verify_read_only_contract()

    return print_final_result(
        inventory_ok=inventory_ok,
        consolidation_ok=consolidation_ok,
        governance_ok=governance_ok,
        authorization_guard_ok=authorization_guard_ok,
        readonly_ok=readonly_ok,
    )


if __name__ == "__main__":
    sys.exit(main())

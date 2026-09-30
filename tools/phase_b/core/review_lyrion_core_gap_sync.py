#!/usr/bin/env python3
"""
LYRION True Agentic OS
Core Gap & Synchronization Assessment R2

READ-ONLY ASSESSMENT ONLY.

This tool:
    - does not modify source code
    - does not modify documentation
    - does not modify manifests
    - does not modify Git state
    - does not access databases/network services
    - does not access credentials/secrets
    - does not reconstruct G46.5/G47
    - does not claim production certification

Important:
    Static repository presence is NOT equivalent to:
        IMPLEMENTED -> VALIDATED -> ACCEPTED -> PRODUCTION

Security ownership review is scoped specifically to the Agent Harness.
Existing security-owner modules such as Aegis/authorization.py are not
treated as forbidden merely because they legitimately expose authorization
APIs.

HUI/FUI detection reports repository-layout evidence only.
Absence from conventional frontend roots does NOT prove frontend absence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

CORE_RUNTIME = REPO / "src" / "lyrion"
TEST_ROOT = REPO / "tests"
DOC_ROOT = REPO / "docs"

MANIFEST_CANDIDATES = (
    REPO / "Manifest.md",
    REPO / "docs" / "Manifest.md",
    REPO
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
)

AGENT_HARNESS_ROOT = CORE_RUNTIME / "agent_harness"

FRONTEND_ROOT_CANDIDATES = (
    REPO / "frontend",
    REPO / "ui",
    REPO / "web",
    REPO / "app",
    REPO / "src" / "ui",
    REPO / "src" / "frontend",
)

FUTURE_RESERVED_TERMS = (
    "self-learning",
    "self-evolution",
    "self-awareness",
    "self-recognition",
    "self-understanding",
    "self-wakeup",
    "self-response",
)


@dataclass(frozen=True)
class Finding:
    area: str
    requirement: str
    status: str
    evidence: tuple[str, ...]
    note: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def existing(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def grep_files(
    root: Path,
    patterns: Iterable[str],
) -> dict[str, list[str]]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    matches: dict[str, list[str]] = {}

    for path in python_files(root):
        text = read_text(path)

        if not text:
            continue

        found = [pattern.pattern for pattern in compiled if pattern.search(text)]

        if found:
            matches[relative(path)] = found

    return matches


def ast_parse_summary(root: Path) -> tuple[int, int]:
    total = 0
    failures = 0

    for path in python_files(root):
        total += 1

        try:
            ast.parse(
                read_text(path),
                filename=str(path),
            )
        except OSError, UnicodeDecodeError, SyntaxError:
            failures += 1

    return total, failures


def git_state() -> dict[str, str]:
    result: dict[str, str] = {}

    commands = {
        "branch": ["git", "branch", "--show-current"],
        "head": ["git", "rev-parse", "HEAD"],
        "origin_main": ["git", "rev-parse", "origin/main"],
    }

    for key, command in commands.items():
        try:
            completed = subprocess.run(
                command,
                cwd=REPO,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except OSError, subprocess.TimeoutExpired:
            result[key] = "UNAVAILABLE"
            continue

        result[key] = completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        result["worktree_clean"] = (
            "YES" if status.returncode == 0 and not status.stdout.strip() else "NO"
        )
    except OSError, subprocess.TimeoutExpired:
        result["worktree_clean"] = "UNAVAILABLE"

    return result


def manifest_findings() -> list[Finding]:
    manifests = existing(MANIFEST_CANDIDATES)

    if not manifests:
        return [
            Finding(
                "Governance",
                "Canonical manifest presence",
                "PENDING",
                (),
                "No expected repository manifest path was found.",
            )
        ]

    return [
        Finding(
            "Governance",
            f"Manifest: {relative(manifest)}",
            "NOT-EVIDENCED",
            (
                relative(manifest),
                sha256(manifest),
            ),
            (
                "Manifest presence and SHA-256 integrity were observed. "
                "This assessment does not promote semantic governance "
                "status."
            ),
        )
        for manifest in manifests
    ]


def core_component_findings() -> list[Finding]:
    components = {
        "Agent Harness": (CORE_RUNTIME / "agent_harness",),
        "Aegis": (
            CORE_RUNTIME / "security" / "policy.py",
            CORE_RUNTIME / "security" / "authorization.py",
        ),
        "Capability Gateway": (CORE_RUNTIME / "capabilities" / "gateway.py",),
        "Execution Contracts": (CORE_RUNTIME / "execution" / "contracts.py",),
        "Execution Admission / Executor": (
            CORE_RUNTIME / "execution" / "executor.py",
            CORE_RUNTIME / "execution" / "validator.py",
        ),
        "Tests": (TEST_ROOT,),
        "Phase-B documentation": (DOC_ROOT / "phase-b",),
    }

    findings: list[Finding] = []

    for name, paths in components.items():
        present = existing(paths)

        if not present:
            findings.append(
                Finding(
                    "Core",
                    name,
                    "PENDING",
                    (),
                    "Expected repository surface was not found.",
                )
            )
            continue

        if name in {"Tests", "Phase-B documentation"}:
            status = "NOT-EVIDENCED"
        else:
            status = "IMPLEMENTED"

        findings.append(
            Finding(
                "Core",
                name,
                status,
                tuple(relative(path) for path in present),
                (
                    "Repository surface exists. Presence alone does not "
                    "prove validation or acceptance."
                ),
            )
        )

    return findings


def security_chain_findings() -> list[Finding]:
    patterns = {
        "Aegis": (
            r"\bAegis\b",
            r"security",
        ),
        "Capability Gateway": (
            r"CapabilityGateway",
            r"capability",
        ),
        "Execution Admission": (
            r"ExecutionAdmission",
            r"execution.?admission",
        ),
        "Secure Executor": (
            r"SecureExecutor",
            r"secure.?executor",
        ),
        "Sandbox": (
            r"\bSandbox\b",
            r"sandbox",
        ),
        "LHICF": (
            r"LHICF",
            r"host.?integration",
        ),
    }

    findings: list[Finding] = []

    for name, search_patterns in patterns.items():
        matches = grep_files(
            CORE_RUNTIME,
            search_patterns,
        )

        if matches:
            findings.append(
                Finding(
                    "Security Chain",
                    name,
                    "IMPLEMENTED",
                    tuple(sorted(matches)[:10]),
                    (
                        "Static runtime evidence found. This does not "
                        "constitute runtime security certification."
                    ),
                )
            )
        else:
            findings.append(
                Finding(
                    "Security Chain",
                    name,
                    "PENDING",
                    (),
                    "No matching runtime evidence was detected.",
                )
            )

    return findings


def agentic_core_findings() -> list[Finding]:
    patterns = {
        "Task binding": (
            r"task_id",
            r"task",
            r"binding",
        ),
        "Agent identity": (
            r"agent_id",
            r"AgentIdentity",
        ),
        "Delegated authority consumption": (
            r"authority_context",
            r"delegated",
        ),
        "Capability binding": (
            r"capability_context",
            r"capability",
        ),
        "Execution admission": (
            r"execution_admission",
            r"ExecutionAdmission",
        ),
        "Lifecycle": (
            r"lifecycle",
            r"RUNNING",
            r"CANCEL",
        ),
        "Provenance": (
            r"provenance",
            r"Provenance",
        ),
    }

    findings: list[Finding] = []

    for name, search_patterns in patterns.items():
        matches = grep_files(
            CORE_RUNTIME,
            search_patterns,
        )

        findings.append(
            Finding(
                "Agentic Core",
                name,
                "IMPLEMENTED" if matches else "PENDING",
                tuple(sorted(matches)[:10]),
                (
                    "Static implementation signal only. Integration, "
                    "validation, and acceptance require independent "
                    "evidence."
                ),
            )
        )

    return findings


def hui_fui_findings() -> list[Finding]:
    present = existing(FRONTEND_ROOT_CANDIDATES)

    if not present:
        return [
            Finding(
                "HUI/FUI",
                "Frontend repository location",
                "NOT-EVIDENCED",
                (),
                (
                    "No conventional frontend root was found. This is "
                    "only a repository-layout observation and does not "
                    "prove that HUI/FUI is absent."
                ),
            )
        ]

    return [
        Finding(
            "HUI/FUI",
            "Frontend repository location",
            "NOT-EVIDENCED",
            tuple(relative(path) for path in present),
            (
                "A conventional frontend root exists. HUI/FUI "
                "implementation, integration, browser E2E, and security "
                "validation still require dedicated evidence."
            ),
        )
    ]


def validation_findings() -> list[Finding]:
    evidence_paths = (
        DOC_ROOT / "phase-b" / "agent-harness" / "validation",
        DOC_ROOT / "phase-b" / "aegis",
        DOC_ROOT / "phase-b" / "execution-admission",
        REPO / "artifacts",
    )

    present = existing(evidence_paths)

    if not present:
        return [
            Finding(
                "Validation",
                "Validation evidence surface",
                "PENDING",
                (),
                "No expected validation-evidence roots were found.",
            )
        ]

    return [
        Finding(
            "Validation",
            "Validation evidence surface",
            "NOT-EVIDENCED",
            tuple(relative(path) for path in present),
            (
                "Evidence roots exist. Individual evidence must be "
                "matched to current implementation and acceptance records."
            ),
        )
    ]


def agent_harness_security_ownership_findings() -> list[Finding]:
    """
    Security ownership review is intentionally scoped ONLY to the
    Agent Harness.

    Existing Aegis/authorization.py is a legitimate security owner and
    must not be flagged simply because it contains authorization APIs.
    """

    if not AGENT_HARNESS_ROOT.exists():
        return [
            Finding(
                "Architecture Safety",
                "Agent Harness security ownership",
                "NOT-EVIDENCED",
                (),
                (
                    "Agent Harness does not exist in the expected location; "
                    "ownership review cannot be performed."
                ),
            )
        ]

    forbidden_function_names = {
        "authorize",
        "grant_capability",
        "create_admission",
        "execute_privileged",
        "bypass_security",
        "create_authority",
        "grant_authority",
    }

    violations: list[str] = []

    for path in python_files(AGENT_HARNESS_ROOT):
        try:
            tree = ast.parse(
                read_text(path),
                filename=str(path),
            )
        except OSError, UnicodeDecodeError, SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                if node.name in forbidden_function_names:
                    violations.append(f"{relative(path)}:{node.lineno}:{node.name}")

    if violations:
        return [
            Finding(
                "Architecture Safety",
                "Agent Harness security ownership",
                "BLOCKED",
                tuple(sorted(violations)),
                (
                    "Agent Harness declares a forbidden security-owner "
                    "API. Manual architectural review is required."
                ),
            )
        ]

    return [
        Finding(
            "Architecture Safety",
            "Agent Harness security ownership",
            "NOT-EVIDENCED",
            (),
            (
                "No forbidden security-owner function was detected "
                "inside Agent Harness. Existing Aegis/authorization "
                "modules were intentionally excluded from this check."
            ),
        )
    ]


def agent_harness_dependency_findings() -> list[Finding]:
    required_symbols = {
        "ExecutionAdmission": r"\bExecutionAdmission\b",
        "SecureExecutor": r"\bSecureExecutor\b",
        "Sandbox": r"\bSandbox\b",
        "provenance": r"\bprovenance\b",
        "AgentIsolationContract": r"\bAgentIsolationContract\b",
    }

    findings: list[Finding] = []

    for name, pattern in required_symbols.items():
        matches = grep_files(
            AGENT_HARNESS_ROOT,
            (pattern,),
        )

        findings.append(
            Finding(
                "Agent Harness Boundary",
                name,
                "IMPLEMENTED" if matches else "PENDING",
                tuple(sorted(matches)),
                (
                    "Dependency/contract reference detected. This does "
                    "not independently prove runtime enforcement."
                ),
            )
        )

    return findings


def future_reserved_findings() -> list[Finding]:
    return [
        Finding(
            "Future Reserved",
            term,
            "FUTURE-RESERVED",
            (),
            "Explicitly excluded from current implementation scope.",
        )
        for term in FUTURE_RESERVED_TERMS
    ]


def count_statuses(
    findings: list[Finding],
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1

    return dict(sorted(counts.items()))


def emit_report(
    findings: list[Finding],
    ast_summary: tuple[int, int],
) -> None:
    report = {
        "assessment": ("LYRION_CORE_GAP_AND_SYNCHRONIZATION_ASSESSMENT_R2"),
        "mode": "READ_ONLY",
        "repository": str(REPO),
        "git": git_state(),
        "python_ast": {
            "files_scanned": ast_summary[0],
            "parse_failures": ast_summary[1],
        },
        "status_counts": count_statuses(findings),
        "findings": [asdict(finding) for finding in findings],
        "governance_boundary": {
            "production_certification": "NOT_CLAIMED",
            "g46_5": "NOT_RECONSTRUCTED",
            "g47": "BLOCKED_FAIL_CLOSED",
            "self_learning": "FUTURE_RESERVED",
            "self_evolution": "FUTURE_RESERVED",
            "self_awareness_family": "FUTURE_RESERVED",
        },
        "assessment_limitations": [
            ("Repository presence is not implementation validation."),
            ("Static implementation evidence is not runtime security certification."),
            ("Frontend-root absence is not proof of HUI/FUI absence."),
            ("This tool does not reconstruct G46.5 or G47."),
            ("This tool does not grant implementation authorization."),
        ],
    }

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )


def main() -> int:
    if not REPO.is_dir():
        print(
            "ERROR: repository root not found",
            file=sys.stderr,
        )
        return 2

    findings: list[Finding] = []

    findings.extend(manifest_findings())
    findings.extend(core_component_findings())
    findings.extend(security_chain_findings())
    findings.extend(agentic_core_findings())
    findings.extend(hui_fui_findings())
    findings.extend(validation_findings())
    findings.extend(agent_harness_security_ownership_findings())
    findings.extend(agent_harness_dependency_findings())
    findings.extend(future_reserved_findings())

    ast_summary = ast_parse_summary(CORE_RUNTIME)

    emit_report(
        findings,
        ast_summary,
    )

    return 0 if ast_summary[1] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

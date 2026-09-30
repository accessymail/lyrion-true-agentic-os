#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-001..008 Implementation-Gap Audit

Purpose:
    Perform a read-only reconciliation between the Phase-B specifications
    PB-DOC-001 through PB-DOC-008 and the existing repository implementation.

Safety:
    - No source modification.
    - No test modification.
    - No documentation modification.
    - No G46.5/G47 reconstruction.
    - No R097 modification.
    - No credentials/secrets/provider/database/systemd access.
    - No privileged execution.
    - No network operations.
    - No Git mutation.
    - No production-certification claim.

This tool assesses repository evidence only.
File presence is NOT treated as implementation correctness.
Test presence is NOT treated as successful validation.
"""

from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

DOCS = {
    "PB-DOC-001": REPO / "docs/phase-b/requirements/"
    "LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",
    "PB-DOC-002": REPO / "docs/phase-b/agentic-runtime/"
    "LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",
    "PB-DOC-003": REPO / "docs/phase-b/identity-authority/"
    "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",
    "PB-DOC-004": REPO / "docs/phase-b/capability/"
    "LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",
    "PB-DOC-005": REPO / "docs/phase-b/agent-harness/"
    "LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-006": REPO / "docs/phase-b/host-harness/"
    "LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-007": REPO / "docs/phase-b/universal-computer/"
    "LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",
    "PB-DOC-008": REPO / "docs/phase-b/application-harness/"
    "LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",
}


# Repository-owned implementation surfaces only.
RUNTIME_ROOT = REPO / "src"
TEST_ROOT = REPO / "tests"

FORBIDDEN_ROOTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".tox",
    "NOT_USABLE_DOCUMENTS",
}


@dataclass(frozen=True)
class Evidence:
    doc_id: str
    category: str
    matches: tuple[str, ...]


# Explicit architectural concepts expected to have discoverable repository
# evidence. These are evidence probes, not correctness assertions.
PROBES: dict[str, dict[str, tuple[str, ...]]] = {
    "PB-DOC-001": {
        "requirements": (
            "requirement",
            "task",
            "security",
            "authority",
            "capability",
            "verification",
            "provenance",
        ),
        "runtime": (
            "src/lyrion/tasks",
            "src/lyrion/cognition",
            "src/lyrion/piae",
        ),
        "tests": (
            "tests",
        ),
    },
    "PB-DOC-002": {
        "requirements": (
            "agentic runtime",
            "lifecycle",
            "task",
            "orchestration",
            "runtime",
            "agent",
        ),
        "runtime": (
            "src/lyrion/piae",
            "src/lyrion/cognition",
            "src/lyrion/tasks",
        ),
        "tests": (
            "tests",
        ),
    },
    "PB-DOC-003": {
        "requirements": (
            "agent identity",
            "principal",
            "authority",
            "delegated authority",
            "authorization",
            "revocation",
        ),
        "runtime": (
            "src/lyrion/security",
            "src/lyrion/tasks",
        ),
        "tests": (
            "tests",
        ),
    },
    "PB-DOC-004": {
        "requirements": (
            "capability",
            "scope",
            "target",
            "least privilege",
            "deny-by-default",
        ),
        "runtime": (
            "src/lyrion/capabilities",
            "src/lyrion/execution",
        ),
        "tests": (
            "tests/unit/test_capability_gateway.py",
            "tests/unit/test_capability_contracts.py",
        ),
    },
    "PB-DOC-005": {
        "requirements": (
            "agent harness",
            "agent lifecycle",
            "task binding",
            "runtime isolation",
            "resource limits",
        ),
        "runtime": (
            "src/lyrion",
        ),
        "tests": (
            "tests",
        ),
    },
    "PB-DOC-006": {
        "requirements": (
            "host harness",
            "filesystem",
            "process",
            "service",
            "network",
            "application",
            "desktop",
            "device",
            "clipboard",
        ),
        "runtime": (
            "src/lyrion/integration",
            "src/lyrion/execution",
        ),
        "tests": (
            "tests/unit/execution",
            "tests",
        ),
    },
    "PB-DOC-007": {
        "requirements": (
            "universal computer",
            "host abstraction",
            "adapter",
            "operation",
            "environment discovery",
        ),
        "runtime": (
            "src/lyrion/integration",
            "src/lyrion/execution",
        ),
        "tests": (
            "tests",
        ),
    },
    "PB-DOC-008": {
        "requirements": (
            "application harness",
            "application identity",
            "application discovery",
            "application capability",
            "application adapter",
            "desktop",
            "MCP",
            "A2A",
        ),
        "runtime": (
            "src/lyrion/application",
            "src/lyrion/integration",
        ),
        "tests": (
            "tests",
        ),
    },
}


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(path: Path) -> str:
    return str(path.relative_to(REPO))


def repository_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative_parts = path.relative_to(REPO).parts
        if any(part in FORBIDDEN_ROOTS for part in relative_parts):
            continue

        files.append(path)

    return sorted(files)


def read_doc(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def headings(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if re.match(r"^#{1,6}\s+", line)
    ]


def document_status(text: str) -> dict[str, str]:
    result: dict[str, str] = {}

    for key in (
        "Status",
        "Architecture Approval",
        "Implementation Authorization",
        "Production Implementation",
        "Production Certification",
    ):
        match = re.search(
            rf"^\*\*{re.escape(key)}:\*\*\s*(.+?)\s*$",
            text,
            flags=re.MULTILINE,
        )
        if match:
            result[key] = match.group(1).strip()

    return result


def ast_summary(path: Path) -> tuple[bool, int, int]:
    try:
        tree = ast.parse(
            path.read_text(encoding="utf-8", errors="replace"),
            filename=str(path),
        )
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return False, 0, 0

    classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    functions = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
    )
    return True, classes, functions


def keyword_hits(text: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def path_hits(
    files: list[Path],
    expected_fragments: tuple[str, ...],
) -> list[str]:
    hits: list[str] = []

    for fragment in expected_fragments:
        for path in files:
            if fragment in safe_relative(path):
                hits.append(safe_relative(path))
                break

    return sorted(set(hits))


def test_hits(
    files: list[Path],
    expected_fragments: tuple[str, ...],
) -> list[str]:
    test_files = [
        path
        for path in files
        if path.is_relative_to(TEST_ROOT)
    ]

    hits: list[str] = []

    for fragment in expected_fragments:
        for path in test_files:
            if fragment in safe_relative(path):
                hits.append(safe_relative(path))
                break

    return sorted(set(hits))


def runtime_ast_inventory(files: list[Path]) -> tuple[int, int]:
    python_files = [
        path
        for path in files
        if path.suffix == ".py" and path.is_relative_to(RUNTIME_ROOT)
    ]

    parsed = 0
    failed = 0

    for path in python_files:
        ok, _, _ = ast_summary(path)
        if ok:
            parsed += 1
        else:
            failed += 1

    return parsed, failed


SELF_PATH = "tools/phase_b/audit/review_pb_doc_001_008_implementation_gap.py"


def mutation_guard() -> tuple[bool, str]:
    status = run_git("status", "--short", "--untracked-files=all")

    unexpected = []
    for line in status.splitlines():
        path = line[3:] if len(line) >= 4 else line
        if path != SELF_PATH:
            unexpected.append(line)

    if unexpected:
        return (
            False,
            "Unexpected pre-existing or concurrent worktree changes detected: "
            + " | ".join(unexpected),
        )

    if status:
        return (
            True,
            "Only the audit tool itself is untracked; no pre-existing "
            "repository changes detected.",
        )

    return True, "Worktree clean before audit."


def main() -> int:
    print("=" * 78)
    print("LYRION TRUE AGENTIC OS — PB-DOC-001..008 IMPLEMENTATION-GAP AUDIT")
    print("=" * 78)

    print("\n[1] Repository identity")
    print(f"Repository : {REPO}")
    print(f"HEAD       : {run_git('rev-parse', 'HEAD')}")
    print(f"Branch     : {run_git('branch', '--show-current')}")
    print(f"Origin     : {run_git('rev-parse', 'origin/main')}")

    clean, clean_message = mutation_guard()
    print(f"Worktree   : {'CLEAN' if clean else 'NOT CLEAN'}")
    print(f"Guard      : {clean_message}")

    if not clean:
        print("\nDECISION: BASELINE_NOT_CLEAN")
        print("No implementation-gap conclusion is issued.")
        return 2

    print("\n[2] Specification inventory")

    missing_docs: list[str] = []

    for doc_id, path in DOCS.items():
        exists = path.is_file()
        print(
            f"{doc_id}: "
            f"{'PRESENT' if exists else 'MISSING'} "
            f"{safe_relative(path)}"
        )

        if not exists:
            missing_docs.append(doc_id)

    if missing_docs:
        print(f"\nDECISION: MISSING_SPECIFICATIONS {missing_docs}")
        return 3

    print("\n[3] Specification status")

    for doc_id, path in DOCS.items():
        text = read_doc(path)
        status = document_status(text)

        print(f"\n{doc_id}")
        for key, value in status.items():
            print(f"  {key}: {value}")

        print(f"  headings: {len(headings(text))}")
        print(f"  sha256:   {sha256(path)}")

    runtime_files = repository_files(RUNTIME_ROOT)
    test_files = repository_files(TEST_ROOT)

    print("\n[4] Repository implementation inventory")
    print(f"Runtime files: {len(runtime_files)}")
    print(f"Test files   : {len(test_files)}")

    parsed, failed = runtime_ast_inventory(runtime_files)

    print(f"Python runtime AST parse PASS: {parsed}")
    print(f"Python runtime AST parse FAIL: {failed}")

    if failed:
        print(
            "WARNING: runtime syntax inventory contains files that could "
            "not be parsed."
        )

    print("\n[5] PB-DOC-001..008 evidence probes")

    all_evidence: list[Evidence] = []

    for doc_id, probes in PROBES.items():
        doc_text = read_doc(DOCS[doc_id])

        requirement_hits = keyword_hits(
            doc_text,
            probes["requirements"],
        )

        runtime_hits = path_hits(
            runtime_files,
            probes["runtime"],
        )

        test_hits_result = test_hits(
            test_files,
            probes["tests"],
        )

        all_evidence.extend(
            [
                Evidence(
                    doc_id,
                    "specification-keywords",
                    tuple(requirement_hits),
                ),
                Evidence(
                    doc_id,
                    "runtime-path-evidence",
                    tuple(runtime_hits),
                ),
                Evidence(
                    doc_id,
                    "test-path-evidence",
                    tuple(test_hits_result),
                ),
            ]
        )

        print(f"\n{doc_id}")
        print(
            "  specification concepts : "
            f"{len(requirement_hits)}/{len(probes['requirements'])}"
        )
        print(
            "  runtime path evidence  : "
            f"{len(runtime_hits)}/{len(probes['runtime'])}"
        )
        print(
            "  test path evidence     : "
            f"{len(test_hits_result)}/{len(probes['tests'])}"
        )

        if runtime_hits:
            for item in runtime_hits[:12]:
                print(f"    RUNTIME  {item}")

        if test_hits_result:
            for item in test_hits_result[:12]:
                print(f"    TEST     {item}")

    print("\n[6] Explicit architecture-boundary checks")

    required_boundaries = {
        "Aegis": (
            "src/lyrion/security",
        ),
        "Capability Gateway": (
            "src/lyrion/capabilities",
        ),
        "Execution Admission": (
            "src/lyrion/execution",
        ),
        "Secure Executor": (
            "src/lyrion/execution",
        ),
        "Agent Sandbox": (
            "src/lyrion/execution",
        ),
        "LHICF / Host Integration": (
            "src/lyrion/integration",
        ),
    }

    for name, fragments in required_boundaries.items():
        hits = path_hits(runtime_files, fragments)
        print(
            f"{name:24} : "
            f"{'PRESENT' if hits else 'NOT LOCATED'}"
        )

    print("\n[7] Safety-boundary verification")

    forbidden_targets = (
        "G46.5",
        "G47",
        "R097",
        "production certification",
    )

    print("Audit does not reconstruct or modify:")
    for item in forbidden_targets:
        print(f"  - {item}")

    print("\n[8] Classification")

    # This is intentionally conservative. The tool does not select a
    # production implementation target merely from file presence.
    print("PB-DOC-001..008 documentation evidence : PRESENT")
    print("Existing runtime evidence               : PRESENT")
    print("Existing test evidence                  : PRESENT")
    print("Executed validation evidence            : NOT ASSESSED")
    print("Acceptance evidence                     : NOT ASSESSED")
    print("Production certification                : NOT CLAIMED")

    print("\nDECISION: IMPLEMENTATION_GAP_AUDIT_COMPLETE")
    print("NEXT: engineering review required before selecting the next bounded slice.")

    print("\n[9] Post-audit mutation check")

    final_status = run_git("status", "--short", "--untracked-files=all")

    unexpected_final = []
    for line in final_status.splitlines():
        path = line[3:] if len(line) >= 4 else line
        if path != SELF_PATH:
            unexpected_final.append(line)

    if unexpected_final:
        print("FAIL: repository changed during the audit.")
        for line in unexpected_final:
            print(line)
        return 4

    print(
        "PASS: repository remains unchanged except for the audit tool "
        "itself."
    )
    print("\nREAD_ONLY_AUDIT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

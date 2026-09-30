#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-001..008 Semantic Implementation-Gap Audit

READ-ONLY ENGINEERING AUDIT

Purpose:
    Map PB-DOC-001..008 architectural requirements to actual repository-owned
    runtime symbols and tests.

Safety:
    - No source implementation.
    - No test implementation.
    - No documentation modification.
    - No G46.5/G47 reconstruction.
    - No R097 modification.
    - No credentials/secrets/provider/database/systemd access.
    - No privileged execution.
    - No network operations.
    - No Git mutation.
    - No production-certification claim.

Important:
    Symbol discovery is evidence of implementation surface only.
    It is NOT proof of semantic correctness, validation, acceptance, or
    production readiness.
"""

from __future__ import annotations

import ast
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = REPO / "src"
TEST_ROOT = REPO / "tests"

SELF_PATH = "tools/phase_b/audit/review_pb_doc_001_008_semantic_gap.py"

# Previously created read-only PB-DOC-001..008 audit tool.
# It is intentionally preserved and permitted as part of this audit family.
ALLOWED_AUDIT_PATHS = {
    SELF_PATH,
    "tools/phase_b/audit/review_pb_doc_001_008_implementation_gap.py",
}

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
class Symbol:
    path: str
    kind: str
    name: str
    line: int


@dataclass(frozen=True)
class RequirementProbe:
    doc_id: str
    requirement: str
    runtime_terms: tuple[str, ...]
    test_terms: tuple[str, ...]


PROBES: tuple[RequirementProbe, ...] = (
    RequirementProbe(
        "PB-DOC-001",
        "Requirements / task / security / authority / capability / verification / provenance",
        (
            "Task",
            "TaskContext",
            "TaskManager",
            "Cognition",
            "PIAE",
            "Authority",
            "Capability",
            "Provenance",
            "Verification",
        ),
        (
            "task",
            "authority",
            "capability",
            "provenance",
            "verification",
        ),
    ),
    RequirementProbe(
        "PB-DOC-002",
        "Agentic runtime / lifecycle / orchestration / task / runtime",
        (
            "Agent",
            "AgentRuntime",
            "Runtime",
            "Lifecycle",
            "Orchestr",
            "Scheduler",
            "Supervisor",
            "Task",
        ),
        (
            "agent",
            "runtime",
            "lifecycle",
            "orchestration",
            "task",
        ),
    ),
    RequirementProbe(
        "PB-DOC-003",
        "Agent identity / principal / delegated authority / authorization / revocation",
        (
            "AgentIdentity",
            "Principal",
            "Authority",
            "Delegated",
            "Authorization",
            "AuthorizationGuard",
            "ReplayGuard",
            "Revocation",
            "AegisAuthorizationService",
        ),
        (
            "identity",
            "principal",
            "authority",
            "authorization",
            "revocation",
            "replay",
        ),
    ),
    RequirementProbe(
        "PB-DOC-004",
        "Capability / scope / target / least privilege / deny-by-default",
        (
            "Capability",
            "CapabilityGateway",
            "CapabilityRequest",
            "CapabilityContract",
            "CapabilityScope",
            "Target",
            "LeastPrivilege",
        ),
        (
            "capability",
            "scope",
            "target",
            "deny",
            "least",
        ),
    ),
    RequirementProbe(
        "PB-DOC-005",
        "Agent Harness / lifecycle / task binding / isolation / resource limits",
        (
            "AgentHarness",
            "AgentRuntime",
            "Agent",
            "Lifecycle",
            "TaskBinding",
            "RuntimeContext",
            "Resource",
            "Sandbox",
        ),
        (
            "agent_harness",
            "agent",
            "lifecycle",
            "task",
            "resource",
            "sandbox",
        ),
    ),
    RequirementProbe(
        "PB-DOC-006",
        "Host Harness / filesystem / process / service / network / application / desktop / device",
        (
            "HostHarness",
            "HostContext",
            "HostAdapter",
            "HostOperation",
            "Filesystem",
            "Process",
            "Service",
            "Network",
            "Application",
            "Desktop",
            "Device",
            "Clipboard",
            "LHICF",
        ),
        (
            "host",
            "filesystem",
            "process",
            "service",
            "network",
            "application",
            "desktop",
            "device",
            "clipboard",
            "lhicf",
        ),
    ),
    RequirementProbe(
        "PB-DOC-007",
        "Universal Computer / abstraction / adapter / operation / environment discovery",
        (
            "UniversalComputer",
            "Universal",
            "Operation",
            "Adapter",
            "Environment",
            "Host",
            "Discovery",
        ),
        (
            "universal",
            "computer",
            "adapter",
            "operation",
            "environment",
            "discovery",
        ),
    ),
    RequirementProbe(
        "PB-DOC-008",
        "Application Harness / identity / discovery / capability / adapter / desktop / MCP / A2A",
        (
            "ApplicationHarness",
            "Application",
            "ApplicationIdentity",
            "ApplicationContext",
            "ApplicationAdapter",
            "ApplicationCapability",
            "Desktop",
            "MCP",
            "A2A",
        ),
        (
            "application",
            "identity",
            "discovery",
            "capability",
            "adapter",
            "desktop",
            "mcp",
            "a2a",
        ),
    ),
)


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


def relative(path: Path) -> str:
    return str(path.relative_to(REPO))


def repository_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    result: list[Path] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        parts = path.relative_to(REPO).parts

        if any(part in FORBIDDEN_ROOTS for part in parts):
            continue

        result.append(path)

    return sorted(result)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def mutation_guard() -> tuple[bool, str]:
    status = run_git("status", "--short", "--untracked-files=all")

    unexpected: list[str] = []

    for line in status.splitlines():
        path = line[3:] if len(line) >= 4 else line

        if path not in ALLOWED_AUDIT_PATHS:
            unexpected.append(line)

    if unexpected:
        return False, "Unexpected worktree changes: " + " | ".join(unexpected)

    return True, "Only this audit tool is untracked."


def parse_symbols(path: Path) -> tuple[list[Symbol], bool]:
    try:
        tree = ast.parse(
            path.read_text(encoding="utf-8", errors="replace"),
            filename=str(path),
        )
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return [], False

    symbols: list[Symbol] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(
                Symbol(
                    relative(path),
                    "class",
                    node.name,
                    node.lineno,
                )
            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                Symbol(
                    relative(path),
                    "function",
                    node.name,
                    node.lineno,
                )
            )

    return symbols, True


def collect_symbols(files: list[Path]) -> tuple[list[Symbol], int]:
    symbols: list[Symbol] = []
    failures = 0

    for path in files:
        if path.suffix != ".py":
            continue

        found, ok = parse_symbols(path)

        if not ok:
            failures += 1
            continue

        symbols.extend(found)

    return symbols, failures


def symbol_matches(
    symbols: list[Symbol],
    terms: tuple[str, ...],
) -> list[Symbol]:
    lowered = tuple(term.lower() for term in terms)

    matches: list[Symbol] = []

    for symbol in symbols:
        name = symbol.name.lower()

        if any(term in name for term in lowered):
            matches.append(symbol)

    return sorted(
        matches,
        key=lambda item: (item.path, item.line, item.name),
    )


def test_matches(
    test_files: list[Path],
    terms: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []

    lowered_terms = tuple(term.lower() for term in terms)

    for path in test_files:
        name = relative(path).lower()

        if any(term in name for term in lowered_terms):
            matches.append(relative(path))
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).lower()
        except OSError:
            continue

        if any(term in text for term in lowered_terms):
            matches.append(relative(path))

    return sorted(set(matches))


def requirement_status(
    runtime_matches: list[Symbol],
    test_matches_result: list[str],
) -> str:
    if runtime_matches and test_matches_result:
        return "RUNTIME_AND_TEST_SURFACE_FOUND"

    if runtime_matches:
        return "RUNTIME_SURFACE_ONLY"

    if test_matches_result:
        return "TEST_SURFACE_ONLY"

    return "NO_DIRECT_SYMBOL_OR_TEST_EVIDENCE"


def main() -> int:
    print("=" * 82)
    print("LYRION TRUE AGENTIC OS — PB-DOC-001..008 SEMANTIC GAP AUDIT")
    print("=" * 82)

    print("\n[1] Repository safety baseline")

    print(f"Repository : {REPO}")
    print(f"HEAD       : {run_git('rev-parse', 'HEAD')}")
    print(f"Origin     : {run_git('rev-parse', 'origin/main')}")
    print(f"Branch     : {run_git('branch', '--show-current')}")

    clean, message = mutation_guard()

    print(f"Guard      : {'PASS' if clean else 'FAIL'}")
    print(f"Detail     : {message}")

    if not clean:
        print("\nDECISION: BASELINE_NOT_CLEAN")
        return 2

    print("\n[2] Repository surfaces")

    runtime_files = repository_files(RUNTIME_ROOT)
    test_files = repository_files(TEST_ROOT)

    print(f"Runtime Python/files: {len(runtime_files)}")
    print(f"Test files          : {len(test_files)}")

    print("\n[3] Runtime AST symbol extraction")

    runtime_symbols, runtime_parse_failures = collect_symbols(runtime_files)

    test_symbols, test_parse_failures = collect_symbols(test_files)

    print(f"Runtime symbols      : {len(runtime_symbols)}")
    print(f"Runtime AST failures : {runtime_parse_failures}")
    print(f"Test symbols         : {len(test_symbols)}")
    print(f"Test AST failures    : {test_parse_failures}")

    if runtime_parse_failures:
        print("WARNING: runtime AST extraction is incomplete.")

    print("\n[4] Semantic requirement mapping")

    total_runtime = 0
    total_test = 0

    for probe in PROBES:
        runtime_matches = symbol_matches(
            runtime_symbols,
            probe.runtime_terms,
        )

        tests = test_matches(
            test_files,
            probe.test_terms,
        )

        total_runtime += bool(runtime_matches)
        total_test += bool(tests)

        status = requirement_status(
            runtime_matches,
            tests,
        )

        print(f"\n{probe.doc_id}")
        print(f"Requirement : {probe.requirement}")
        print(f"Status      : {status}")

        if runtime_matches:
            print("Runtime symbols:")

            for symbol in runtime_matches[:15]:
                print(
                    f"  {symbol.kind:8} "
                    f"{symbol.name:36} "
                    f"{symbol.path}:{symbol.line}"
                )

        else:
            print("Runtime symbols: NONE")

        if tests:
            print("Test evidence:")

            for test in tests[:15]:
                print(f"  {test}")

        else:
            print("Test evidence: NONE")

    print("\n[5] Existing security/execution boundary symbols")

    boundary_terms = (
        "Aegis",
        "Authorization",
        "CapabilityGateway",
        "ExecutionAdmission",
        "SecureExecutor",
        "Sandbox",
        "LHICF",
    )

    for term in boundary_terms:
        matches = symbol_matches(
            runtime_symbols,
            (term,),
        )

        print(f"\n{term}: {len(matches)} symbol(s)")

        for symbol in matches[:10]:
            print(
                f"  {symbol.kind:8} "
                f"{symbol.name:36} "
                f"{symbol.path}:{symbol.line}"
            )

    print("\n[6] Evidence classification")

    print(f"PB-DOC runtime surfaces with direct symbol evidence: {total_runtime}/8")
    print(f"PB-DOC test surfaces with direct test evidence    : {total_test}/8")

    print()
    print("Executed validation evidence : NOT ASSESSED")
    print("Acceptance evidence          : NOT ASSESSED")
    print("Production implementation    : BLOCKED")
    print("Production certification     : NOT CLAIMED")
    print("G46.5/G47 reconstruction     : NOT PERFORMED")
    print("R097 modification            : NONE")

    print("\n[7] Post-audit safety check")

    final_status = run_git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    unexpected_final: list[str] = []

    for line in final_status.splitlines():
        path = line[3:] if len(line) >= 4 else line

        if path not in ALLOWED_AUDIT_PATHS:
            unexpected_final.append(line)

    if unexpected_final:
        print("FAIL: unexpected repository mutation detected.")

        for line in unexpected_final:
            print(line)

        return 4

    print("PASS: repository unchanged except for the PB-DOC-001..008 audit tools.")

    print("\nDECISION: SEMANTIC_GAP_AUDIT_COMPLETE")
    print(
        "NEXT: engineering review of the mapped runtime/test evidence "
        "is required before selecting a bounded implementation slice."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

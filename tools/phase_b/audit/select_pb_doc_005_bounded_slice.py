#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005 Agent Harness — Bounded Slice Selection Review

READ-ONLY ARCHITECTURAL SELECTION GATE.

Purpose
-------
Identify the smallest safe PB-DOC-005 Agent Harness bounded implementation
slice using the existing implementation contracts.

This tool does NOT implement PB-DOC-005.

It determines whether the first bounded slice can be defined around:

    Agent Identity
        ->
    Task Binding
        ->
    Delegated Authority Context
        ->
    Capability Context
        ->
    Execution Admission
        ->
    Existing Secure Execution Chain

Architectural invariant:

    HUMAN INTENT
        ->
    LYRI INTERPRETATION
        ->
    TASK
        ->
    AGENT DELEGATION
        ->
    SECURE EXECUTION
        ->
    VERIFICATION
        ->
    MEMORY / AUDIT / PROVENANCE

Security invariant:

    Aegis
        ->
    Capability Gateway
        ->
    Execution Admission
        ->
    Secure Executor
        ->
    Sandbox
        ->
    Process Boundary
        ->
    LHICF / Host

The bounded slice MUST NOT:

    - create an alternate authorization authority
    - create an alternate execution admission path
    - bypass Aegis
    - bypass Capability Gateway
    - bypass Secure Executor
    - bypass Sandbox
    - duplicate Task execution contracts unnecessarily
    - replace existing PIAE/task contracts
    - create privileged host execution
    - formalize LHICF by duplicating host enforcement
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification

Evidence class:
    STATIC ARCHITECTURAL SELECTION REVIEW

This is NOT implementation validation.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
TEST_ROOT = REPO_ROOT / "tests"

ALLOWED_SELF = (
    "select_pb_doc_005_bounded_slice.py",
    "map_pb_doc_005_008_architecture_representation.py",
    "map_pb_doc_005_008_contract_ownership.py",
    "map_pb_doc_005_008_contract_responsibilities.py",
    "review_child_launcher_execution_boundary.py",
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "review_pb_doc_005_task_binding_lhicf_boundary.py",
    "trace_pb_doc_001_008_call_chain.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
    "trace_pb_doc_001_008_execution_flow.py",
)


@dataclass(frozen=True)
class Symbol:
    module: str
    name: str
    qualified: str
    kind: str
    line: int


@dataclass(frozen=True)
class Candidate:
    name: str
    path: str
    reason: str
    role: str


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def repo_guard() -> tuple[bool, list[str]]:
    failures: list[str] = []

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    branch = git("branch", "--show-current")

    if head != origin:
        failures.append(
            f"HEAD {head} != origin/main {origin}"
        )

    if branch != "main":
        failures.append(
            f"unexpected branch: {branch}"
        )

    status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    for line in status.splitlines():
        path = line[3:].strip()

        if (
            path.startswith("tools/phase_b/audit/")
            and Path(path).name in ALLOWED_SELF
        ):
            continue

        failures.append(
            f"unexpected worktree change: {line}"
        )

    return not failures, failures


def source_files() -> list[Path]:
    return sorted(
        p
        for p in SRC_ROOT.rglob("*.py")
        if p.is_file()
        and not any(
            part in {
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "NOT_USABLE_DOCUMENTS",
            }
            for part in p.parts
        )
    )


def test_files() -> list[Path]:
    return sorted(
        p
        for p in TEST_ROOT.rglob("*.py")
        if p.is_file()
        and not any(
            part in {
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "NOT_USABLE_DOCUMENTS",
            }
            for part in p.parts
        )
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


class Visitor(ast.NodeVisitor):
    def __init__(self, module: str) -> None:
        self.module = module
        self.symbols: list[Symbol] = []
        self.calls: list[tuple[str, int]] = []
        self.imports: list[str] = []
        self.text: list[str] = []

        self.class_stack: list[str] = []

    def visit_Import(
        self,
        node: ast.Import,
    ) -> None:
        for alias in node.names:
            self.imports.append(alias.name)

        self.generic_visit(node)

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> None:
        module = node.module or ""

        for alias in node.names:
            self.imports.append(
                f"{module}.{alias.name}"
            )

        self.generic_visit(node)

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ) -> None:
        qualified = ".".join(
            [
                self.module,
                *self.class_stack,
                node.name,
            ]
        )

        self.symbols.append(
            Symbol(
                module=self.module,
                name=node.name,
                qualified=qualified,
                kind="class",
                line=node.lineno,
            )
        )

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> None:
        qualified = ".".join(
            [
                self.module,
                *self.class_stack,
                node.name,
            ]
        )

        self.symbols.append(
            Symbol(
                module=self.module,
                name=node.name,
                qualified=qualified,
                kind="function",
                line=node.lineno,
            )
        )

        self.generic_visit(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self.visit_FunctionDef(node)

    def visit_Call(
        self,
        node: ast.Call,
    ) -> None:
        self.calls.append(
            (
                ast.unparse(node.func),
                node.lineno,
            )
        )

        self.generic_visit(node)

    def visit_Constant(
        self,
        node: ast.Constant,
    ) -> None:
        if isinstance(node.value, str):
            self.text.append(
                node.value,
            )

        self.generic_visit(node)


def module_name(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT)

    parts = list(relative.parts)

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(
        ["lyrion", *parts]
    )


def parse_sources() -> tuple[
    list[Symbol],
    dict[str, Visitor],
    int,
]:
    symbols: list[Symbol] = []
    visitors: dict[str, Visitor] = {}
    failures = 0

    for path in source_files():
        module = module_name(path)

        try:
            tree = ast.parse(
                path.read_text(
                    encoding="utf-8",
                ),
                filename=str(path),
            )
        except SyntaxError:
            failures += 1
            continue

        visitor = Visitor(module)
        visitor.visit(tree)

        visitors[module] = visitor
        symbols.extend(visitor.symbols)

    return symbols, visitors, failures


def symbol_matches(
    symbols: list[Symbol],
    terms: tuple[str, ...],
) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols
        if any(
            term.lower()
            in symbol.qualified.lower()
            for term in terms
        )
    ]


def test_matches(
    tests: list[Path],
    terms: tuple[str, ...],
) -> list[str]:
    result: list[str] = []

    for path in tests:
        try:
            text = path.read_text(
                encoding="utf-8",
            ).lower()
        except Exception:
            continue

        if any(
            term.lower() in text
            for term in terms
        ):
            result.append(
                str(
                    path.relative_to(REPO_ROOT)
                )
            )

    return sorted(result)


def exact_files(
    candidates: tuple[str, ...],
) -> list[str]:
    result: list[str] = []

    for candidate in candidates:
        path = REPO_ROOT / candidate

        if path.is_file():
            result.append(candidate)

    return result


def main() -> int:
    print("=" * 100)
    print(
        "LYRION PB-DOC-005 AGENT HARNESS "
        "BOUNDED SLICE SELECTION REVIEW"
    )
    print("=" * 100)

    clean, failures = repo_guard()

    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    print(f"Repository : {REPO_ROOT}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")
    print(
        "Repo Guard : "
        + ("PASS" if clean else "FAIL")
    )

    if not clean:
        for failure in failures:
            print(f"  FAIL: {failure}")

        print("Decision: BASELINE_NOT_CLEAN")
        return 2

    sources = source_files()
    tests = test_files()

    symbols, visitors, parse_failures = (
        parse_sources()
    )

    print()
    print("-" * 100)
    print("SOURCE INVENTORY")
    print("-" * 100)
    print(
        f"Runtime Python files : {len(sources)}"
    )
    print(
        f"Runtime modules      : {len(visitors)}"
    )
    print(
        f"Runtime symbols      : {len(symbols)}"
    )
    print(
        f"Project test files   : {len(tests)}"
    )
    print(
        f"AST failures         : {parse_failures}"
    )

    if parse_failures:
        print(
            "Decision: STATIC_ANALYSIS_INCOMPLETE"
        )
        return 3

    # ------------------------------------------------------------------
    # Existing task-binding contract
    # ------------------------------------------------------------------

    task_terms = (
        "ExecutionRequest",
        "ExecutionAdmission",
        "ExecutionAdmissionEnvelope",
        "Task",
        "TaskContext",
        "PIAE",
        "Opportunity",
    )

    task_symbols = symbol_matches(
        symbols,
        task_terms,
    )

    task_tests = test_matches(
        tests,
        (
            "execution_contract",
            "execution_lifecycle",
            "execution_runner",
            "piae",
            "task",
            "secure_executor",
        ),
    )

    print()
    print("=" * 100)
    print("EXISTING TASK-BINDING CONTRACT")
    print("=" * 100)

    for symbol in task_symbols[:100]:
        print(
            f"  {symbol.kind:10s} "
            f"{symbol.qualified}"
        )

    print(
        f"Task-related runtime symbols: "
        f"{len(task_symbols)}"
    )
    print(
        f"Task-related tests: "
        f"{len(task_tests)}"
    )

    # ------------------------------------------------------------------
    # Identity / authority contracts
    # ------------------------------------------------------------------

    authority_terms = (
        "AgentIdentity",
        "Principal",
        "Authority",
        "Delegated",
        "Authorization",
        "AuthorizationGuard",
        "ReplayGuard",
        "AegisAuthorizationService",
    )

    authority_symbols = symbol_matches(
        symbols,
        authority_terms,
    )

    authority_tests = test_matches(
        tests,
        (
            "aegis_authorization",
            "aegis_guards",
            "identity",
            "authorization",
            "delegated",
            "revocation",
            "replay",
        ),
    )

    print()
    print("=" * 100)
    print("IDENTITY / AUTHORITY CONTRACT")
    print("=" * 100)

    for symbol in authority_symbols[:100]:
        print(
            f"  {symbol.kind:10s} "
            f"{symbol.qualified}"
        )

    print(
        f"Authority-related runtime symbols: "
        f"{len(authority_symbols)}"
    )
    print(
        f"Authority-related tests: "
        f"{len(authority_tests)}"
    )

    # ------------------------------------------------------------------
    # Security chain
    # ------------------------------------------------------------------

    boundary_terms = {
        "Aegis": (
            "AegisAuthorizationService",
            "AegisPolicyEvaluator",
        ),
        "CapabilityGateway": (
            "CapabilityGateway",
        ),
        "ExecutionAdmission": (
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
        ),
        "SecureExecutor": (
            "SecureExecutor",
        ),
        "Sandbox": (
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
            "SandboxConfig",
        ),
        "ProcessBoundary": (
            "ChildLauncher",
            "LaunchHandoff",
            "ChildLaunchResult",
        ),
        "HostIntegration": (
            "HostIntegration",
            "PrimitiveAdapter",
            "LinuxHostCapability",
            "EnforcementApplication",
        ),
    }

    print()
    print("=" * 100)
    print("SECURITY / EXECUTION CHAIN")
    print("=" * 100)

    boundary_inventory: dict[
        str, list[Symbol]
    ] = {}

    for boundary, terms in boundary_terms.items():
        matches = symbol_matches(
            symbols,
            terms,
        )

        boundary_inventory[boundary] = matches

        print(
            f"{boundary:22s}: "
            f"{len(matches)} symbols"
        )

    # ------------------------------------------------------------------
    # Agent Harness existing representation
    # ------------------------------------------------------------------

    agent_harness_terms = (
        "AgentHarness",
        "AgentRuntime",
        "Agent",
        "Lifecycle",
        "TaskBinding",
        "RuntimeContext",
        "ResourceLimits",
        "Sandbox",
    )

    agent_symbols = symbol_matches(
        symbols,
        agent_harness_terms,
    )

    agent_tests = test_matches(
        tests,
        (
            "agent",
            "lifecycle",
            "runtime",
            "sandbox",
            "resource",
            "task",
        ),
    )

    print()
    print("=" * 100)
    print("AGENT-HARNESS EXISTING REPRESENTATION")
    print("=" * 100)

    for symbol in agent_symbols[:100]:
        print(
            f"  {symbol.kind:10s} "
            f"{symbol.qualified}"
        )

    print(
        f"Agent-harness-related runtime symbols: "
        f"{len(agent_symbols)}"
    )
    print(
        f"Agent-harness-related tests: "
        f"{len(agent_tests)}"
    )

    explicit_agent_harness = [
        symbol
        for symbol in agent_symbols
        if symbol.name == "AgentHarness"
    ]

    explicit_task_binding = [
        symbol
        for symbol in task_symbols
        if symbol.name == "TaskBinding"
    ]

    # ------------------------------------------------------------------
    # Candidate bounded slice
    # ------------------------------------------------------------------

    candidates = [
        Candidate(
            name="PB-DOC-005 Task Binding Contract Adapter",
            path=(
                "src/lyrion/execution/contracts.py"
            ),
            reason=(
                "Existing ExecutionRequest and "
                "ExecutionAdmissionEnvelope already "
                "represent execution-bound task context."
            ),
            role=(
                "Formalize the Agent Harness task-binding "
                "contract over existing execution contracts."
            ),
        ),
        Candidate(
            name="PB-DOC-005 Agent Runtime Binding Facade",
            path=(
                "src/lyrion/piae/"
            ),
            reason=(
                "Existing PIAE runtime surfaces already "
                "associate opportunity/task/execution lifecycle."
            ),
            role=(
                "Expose governed agent/task binding without "
                "creating execution authority."
            ),
        ),
        Candidate(
            name="PB-DOC-005 Authorization Context Binding",
            path=(
                "src/lyrion/security/"
            ),
            reason=(
                "Aegis and authorization contracts already "
                "provide authority state."
            ),
            role=(
                "Consume existing authorization state only; "
                "never create new authority."
            ),
        ),
    ]

    print()
    print("=" * 100)
    print("BOUNDED-SLICE CANDIDATES")
    print("=" * 100)

    for candidate in candidates:
        print()
        print(
            f"Candidate : {candidate.name}"
        )
        print(
            f"Path      : {candidate.path}"
        )
        print(
            f"Reason    : {candidate.reason}"
        )
        print(
            f"Role      : {candidate.role}"
        )

    # ------------------------------------------------------------------
    # Forbidden architecture signals
    # ------------------------------------------------------------------

    forbidden_terms = (
        "alternate_authorization",
        "independent_authority",
        "privileged_execution",
        "bypass_aegis",
        "bypass_gateway",
        "bypass_admission",
        "bypass_executor",
        "bypass_sandbox",
        "direct_host_privilege",
        "alternate_execution_path",
    )

    forbidden_hits: list[str] = []

    for path in sources:
        try:
            text = path.read_text(
                encoding="utf-8",
            ).lower()
        except Exception:
            continue

        for term in forbidden_terms:
            if term in text:
                forbidden_hits.append(
                    f"{path.relative_to(REPO_ROOT)}:{term}"
                )

    print()
    print("=" * 100)
    print("ARCHITECTURAL SAFETY CHECK")
    print("=" * 100)

    if forbidden_hits:
        print(
            "Potential forbidden architecture "
            "signals detected:"
        )

        for hit in sorted(
            set(forbidden_hits)
        )[:100]:
            print(
                f"  - {hit}"
            )
    else:
        print(
            "No explicit forbidden architecture "
            "signals detected."
        )

    # ------------------------------------------------------------------
    # Scope determination
    # ------------------------------------------------------------------

    existing_contracts_present = bool(
        task_symbols
    )

    authority_boundary_present = bool(
        boundary_inventory["Aegis"]
        and boundary_inventory[
            "CapabilityGateway"
        ]
        and boundary_inventory[
            "ExecutionAdmission"
        ]
        and boundary_inventory[
            "SecureExecutor"
        ]
        and boundary_inventory[
            "Sandbox"
        ]
    )

    process_boundary_present = bool(
        boundary_inventory[
            "ProcessBoundary"
        ]
    )

    no_explicit_duplicate_task_binding = not bool(
        explicit_task_binding
    )

    no_explicit_agent_harness = not bool(
        explicit_agent_harness
    )

    bounded_slice_ready = all(
        (
            existing_contracts_present,
            authority_boundary_present,
            process_boundary_present,
            no_explicit_duplicate_task_binding,
            no_explicit_agent_harness,
            not forbidden_hits,
        )
    )

    print()
    print("=" * 100)
    print("BOUNDED-SLICE READINESS")
    print("=" * 100)

    checks = {
        "existing_task_contracts": (
            existing_contracts_present
        ),
        "security_chain_present": (
            authority_boundary_present
        ),
        "process_boundary_present": (
            process_boundary_present
        ),
        "no_duplicate_task_binding": (
            no_explicit_duplicate_task_binding
        ),
        "no_existing_agent_harness_duplicate": (
            no_explicit_agent_harness
        ),
        "no_forbidden_architecture_signal": (
            not forbidden_hits
        ),
    }

    for name, value in checks.items():
        print(
            f"{name:45s}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    # ------------------------------------------------------------------
    # Recommended scope
    # ------------------------------------------------------------------

    if bounded_slice_ready:
        decision = (
            "PB_DOC_005_BOUNDED_SLICE_READY_FOR_ENGINEERING_DESIGN"
        )

        selected_scope = {
            "primary_contract": (
                "Existing execution/task contracts"
            ),
            "agent_binding": (
                "Explicit binding of agent identity, "
                "task, delegated authority, capability "
                "and execution admission context"
            ),
            "authorization": (
                "Consume existing Aegis authorization state"
            ),
            "execution": (
                "Reuse existing ExecutionAdmission and "
                "SecureExecutor"
            ),
            "sandbox": (
                "Reuse existing Sandbox policy/enforcement"
            ),
            "process_boundary": (
                "Reuse existing ChildLauncher / LaunchHandoff"
            ),
            "lifecycle": (
                "Integrate with existing PIAE/runtime lifecycle"
            ),
            "prohibited": (
                "No duplicate authorization, execution "
                "admission, sandbox, host privilege or LHICF "
                "implementation"
            ),
        }
    else:
        decision = (
            "PB_DOC_005_BOUNDED_SLICE_REQUIRES_ENGINEERING_REVIEW"
        )
        selected_scope = {}

    print()
    print("=" * 100)
    print("SELECTED BOUNDED SCOPE")
    print("=" * 100)

    if selected_scope:
        for key, value in selected_scope.items():
            print(
                f"{key:18s}: {value}"
            )
    else:
        print(
            "No bounded implementation scope selected."
        )

    # ------------------------------------------------------------------
    # Evidence boundary
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EVIDENCE BOUNDARY")
    print("=" * 100)

    print(
        "Analysis type                 : "
        "STATIC BOUNDED-SLICE SELECTION REVIEW"
    )
    print(
        "Implementation                : NOT PERFORMED"
    )
    print(
        "Executed validation           : NOT ASSESSED"
    )
    print(
        "Acceptance evidence           : NOT ASSESSED"
    )
    print(
        "Production implementation     : BLOCKED"
    )
    print(
        "Production certification      : NOT CLAIMED"
    )
    print(
        "G46.5 reconstruction          : NOT PERFORMED"
    )
    print(
        "G47 reconstruction            : NOT PERFORMED"
    )
    print(
        "R097 modification             : NONE"
    )
    print(
        "Source/test/document mutation : NONE"
    )

    summary = {
        "decision": decision,
        "head": head,
        "origin_main": origin,
        "runtime_python_files": len(sources),
        "runtime_modules": len(visitors),
        "runtime_symbols": len(symbols),
        "project_test_files": len(tests),
        "parse_failures": parse_failures,
        "existing_task_contracts": {
            "runtime_symbols": len(task_symbols),
            "tests": len(task_tests),
        },
        "authority_contracts": {
            "runtime_symbols": len(
                authority_symbols
            ),
            "tests": len(
                authority_tests
            ),
        },
        "explicit_agent_harness": bool(
            explicit_agent_harness
        ),
        "explicit_task_binding": bool(
            explicit_task_binding
        ),
        "security_chain": {
            key: len(value)
            for key, value in boundary_inventory.items()
        },
        "forbidden_architecture_signals": sorted(
            set(forbidden_hits)
        ),
        "readiness_checks": checks,
        "selected_scope": selected_scope,
        "implementation": "NOT_PERFORMED",
        "production_implementation": "BLOCKED",
        "production_certification": "NOT_CLAIMED",
        "g46_5": "NOT_PERFORMED",
        "g47": "NOT_PERFORMED",
        "r097": "NONE",
    }

    print()
    print("=" * 100)
    print("MACHINE SUMMARY")
    print("=" * 100)

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print(f"Decision: {decision}")

    return 0 if bounded_slice_ready else 4


if __name__ == "__main__":
    raise SystemExit(main())

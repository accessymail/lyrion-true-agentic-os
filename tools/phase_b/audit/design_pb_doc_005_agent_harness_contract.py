#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005 Agent Harness — Engineering Contract Design Review

READ-ONLY DESIGN GATE.

Purpose
-------
Define and review the first PB-DOC-005 Agent Harness bounded contract
against the existing LYRION runtime architecture.

This tool does NOT implement the Agent Harness.

It establishes the engineering contract for:

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
    Secure Executor
        ->
    Sandbox
        ->
    Process Boundary
        ->
    Existing PIAE/runtime lifecycle
        ->
    Verification / Provenance

Architectural rules
-------------------
1. Agent Harness is NOT an authorization authority.
2. Agent Harness is NOT an execution authority.
3. Agent Harness MUST NOT create a second execution-admission path.
4. Agent Harness MUST consume existing Aegis authorization state.
5. Agent Harness MUST preserve agent/task/authority/capability separation.
6. Agent Harness MUST preserve least privilege.
7. Agent Harness MUST preserve fail-closed behavior.
8. Agent Harness MUST preserve revocation / expiry / replay semantics.
9. Agent Harness MUST reuse ExecutionAdmission.
10. Agent Harness MUST reuse SecureExecutor.
11. Agent Harness MUST reuse Sandbox enforcement.
12. Agent Harness MUST reuse ProcessBoundary / LaunchHandoff.
13. Agent Harness MUST NOT create privileged host execution.
14. Agent Harness MUST NOT become an LHICF implementation.
15. Agent Harness MUST remain auditable and attributable.
16. Model output, prompts, memory, tool output, or self-declaration
    MUST NOT establish agent identity or authority.

Evidence class
--------------
STATIC ENGINEERING CONTRACT DESIGN REVIEW

This is NOT:
    - implementation
    - executed validation
    - acceptance
    - production certification
    - G46.5 reconstruction
    - G47 reconstruction
    - R097 modification
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

SELF_NAME = (
    "design_pb_doc_005_agent_harness_contract.py"
)

ALLOWED_AUDIT_TOOLS = {
    SELF_NAME,
    "select_pb_doc_005_bounded_slice.py",
    "review_child_launcher_execution_boundary.py",
    "review_pb_doc_005_task_binding_lhicf_boundary.py",
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "trace_pb_doc_001_008_call_chain.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
    "trace_pb_doc_001_008_execution_flow.py",
    "map_pb_doc_005_008_architecture_representation.py",
    "map_pb_doc_005_008_contract_ownership.py",
    "map_pb_doc_005_008_contract_responsibilities.py",
}


@dataclass(frozen=True)
class Symbol:
    module: str
    name: str
    qualified: str
    kind: str
    line: int


@dataclass(frozen=True)
class ContractRequirement:
    identifier: str
    requirement: str
    source_boundary: str
    existing_support: tuple[str, ...]
    implementation_status: str


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
            "HEAD != origin/main"
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
            and Path(path).name in ALLOWED_AUDIT_TOOLS
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
        self.imports: list[str] = []
        self.calls: list[tuple[str, int]] = []
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
                self.module,
                node.name,
                qualified,
                "class",
                node.lineno,
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
                self.module,
                node.name,
                qualified,
                "function",
                node.lineno,
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


def module_name(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT)
    parts = list(relative.parts)

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(["lyrion", *parts])


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


def matches(
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


def matching_tests(
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


def print_symbols(
    title: str,
    symbols: list[Symbol],
    limit: int = 30,
) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)

    for symbol in symbols[:limit]:
        print(
            f"  {symbol.kind:10s} "
            f"{symbol.qualified}"
        )

    print(
        f"Total matching symbols: {len(symbols)}"
    )


def main() -> int:
    print("=" * 100)
    print(
        "LYRION PB-DOC-005 AGENT HARNESS "
        "ENGINEERING CONTRACT DESIGN REVIEW"
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
    print("SOURCE BASELINE")
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
            "Decision: DESIGN_REVIEW_INCOMPLETE"
        )
        return 3

    # ---------------------------------------------------------------
    # Existing architecture surfaces
    # ---------------------------------------------------------------

    identity = matches(
        symbols,
        (
            "AgentIdentity",
            "ApplicationPrincipalContext",
            "Principal",
            "Identity",
        ),
    )

    task = matches(
        symbols,
        (
            "ExecutionRequest",
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
            "Task",
            "TaskContext",
        ),
    )

    authority = matches(
        symbols,
        (
            "AegisAuthorizationService",
            "AuthorizationGuard",
            "ReplayGuard",
            "AuthorizationResult",
            "AuthorizationDecision",
            "Authority",
        ),
    )

    capability = matches(
        symbols,
        (
            "CapabilityRequest",
            "CapabilityGateway",
            "CapabilityOperation",
            "CapabilityContract",
        ),
    )

    execution = matches(
        symbols,
        (
            "SecureExecutor",
            "ExecutionValidator",
            "ExecutionAdmission",
        ),
    )

    sandbox = matches(
        symbols,
        (
            "SandboxConfig",
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
            "ResourceLimits",
        ),
    )

    process_boundary = matches(
        symbols,
        (
            "ChildLauncher",
            "LaunchHandoff",
            "ChildLaunchResult",
        ),
    )

    lifecycle = matches(
        symbols,
        (
            "PIAE",
            "Lifecycle",
            "RuntimeLifecycle",
            "PersistentExecutionLifecycle",
        ),
    )

    provenance = matches(
        symbols,
        (
            "Provenance",
            "Audit",
            "Verification",
            "Evidence",
        ),
    )

    print_symbols(
        "IDENTITY SURFACE",
        identity,
    )

    print_symbols(
        "TASK / EXECUTION CONTRACT SURFACE",
        task,
    )

    print_symbols(
        "AUTHORITY / AEGIS SURFACE",
        authority,
    )

    print_symbols(
        "CAPABILITY SURFACE",
        capability,
    )

    print_symbols(
        "SECURE EXECUTION SURFACE",
        execution,
    )

    print_symbols(
        "SANDBOX / RESOURCE SURFACE",
        sandbox,
    )

    print_symbols(
        "PROCESS BOUNDARY SURFACE",
        process_boundary,
    )

    print_symbols(
        "RUNTIME / LIFECYCLE SURFACE",
        lifecycle,
    )

    print_symbols(
        "VERIFICATION / PROVENANCE SURFACE",
        provenance,
    )

    # ---------------------------------------------------------------
    # Existing test surfaces
    # ---------------------------------------------------------------

    identity_tests = matching_tests(
        tests,
        (
            "identity",
            "principal",
            "agent",
        ),
    )

    authority_tests = matching_tests(
        tests,
        (
            "aegis_authorization",
            "authorization",
            "aegis_guards",
            "replay",
            "revocation",
        ),
    )

    task_tests = matching_tests(
        tests,
        (
            "execution_contract",
            "execution_lifecycle",
            "execution_runner",
            "task",
        ),
    )

    capability_tests = matching_tests(
        tests,
        (
            "capability",
            "gateway",
        ),
    )

    execution_tests = matching_tests(
        tests,
        (
            "secure_executor",
            "execution_result",
            "execution_admission",
        ),
    )

    sandbox_tests = matching_tests(
        tests,
        (
            "sandbox",
            "resource",
            "enforcement",
        ),
    )

    process_tests = matching_tests(
        tests,
        (
            "child_launcher",
            "process_boundary",
            "child_context",
            "child_entry",
        ),
    )

    lifecycle_tests = matching_tests(
        tests,
        (
            "lifecycle",
            "runtime",
            "piae",
        ),
    )

    provenance_tests = matching_tests(
        tests,
        (
            "provenance",
            "verification",
            "audit",
        ),
    )

    # ---------------------------------------------------------------
    # Engineering contract
    # ---------------------------------------------------------------

    requirements = [
        ContractRequirement(
            "AH-001",
            "Agent identity must be explicit and attributable.",
            "Agent Identity",
            (
                "Identity/principal runtime surface",
                "Agent-related tests",
            ),
            "DESIGN OVER EXISTING SURFACE",
        ),
        ContractRequirement(
            "AH-002",
            "Task binding must preserve task identity and execution context.",
            "Task Binding",
            (
                "ExecutionRequest",
                "ExecutionAdmission",
                "ExecutionAdmissionEnvelope",
            ),
            "DESIGN OVER EXISTING CONTRACTS",
        ),
        ContractRequirement(
            "AH-003",
            "Delegated authority must be consumed, never created by Agent Harness.",
            "Authority Context",
            (
                "AegisAuthorizationService",
                "AuthorizationGuard",
                "ReplayGuard",
            ),
            "CONSUME EXISTING AUTHORITY",
        ),
        ContractRequirement(
            "AH-004",
            "Capability context must remain capability-bound and least-privileged.",
            "Capability Context",
            (
                "CapabilityRequest",
                "CapabilityGateway",
            ),
            "CONSUME EXISTING CAPABILITY CONTRACTS",
        ),
        ContractRequirement(
            "AH-005",
            "Execution must require existing execution admission.",
            "Execution Admission",
            (
                "ExecutionAdmission",
                "ExecutionAdmissionEnvelope",
            ),
            "REUSE EXISTING CONTRACT",
        ),
        ContractRequirement(
            "AH-006",
            "Agent Harness must delegate execution to SecureExecutor.",
            "Secure Execution",
            (
                "SecureExecutor",
            ),
            "REUSE EXISTING EXECUTOR",
        ),
        ContractRequirement(
            "AH-007",
            "Sandbox policy must remain enforced downstream.",
            "Sandbox",
            (
                "SandboxPolicy",
                "SandboxPolicyEvaluator",
                "ResourceLimits",
            ),
            "REUSE EXISTING SANDBOX",
        ),
        ContractRequirement(
            "AH-008",
            "Process execution must remain behind the existing process boundary.",
            "Process Boundary",
            (
                "ChildLauncher",
                "LaunchHandoff",
            ),
            "REUSE EXISTING PROCESS BOUNDARY",
        ),
        ContractRequirement(
            "AH-009",
            "Agent lifecycle must integrate with existing runtime/PIAE lifecycle.",
            "Lifecycle",
            (
                "PIAE/runtime lifecycle",
                "PersistentExecutionLifecycle",
            ),
            "INTEGRATE EXISTING LIFECYCLE",
        ),
        ContractRequirement(
            "AH-010",
            "Execution outcomes must remain verifiable and attributable.",
            "Verification / Provenance",
            (
                "Verification",
                "Audit",
                "Provenance",
            ),
            "REUSE EXISTING OBSERVABILITY",
        ),
    ]

    print()
    print("=" * 100)
    print("ENGINEERING CONTRACT")
    print("=" * 100)

    for requirement in requirements:
        print()
        print(
            f"{requirement.identifier} "
            f"[{requirement.implementation_status}]"
        )
        print(
            f"  Requirement : "
            f"{requirement.requirement}"
        )
        print(
            f"  Boundary    : "
            f"{requirement.source_boundary}"
        )
        print(
            f"  Existing    : "
            f"{', '.join(requirement.existing_support)}"
        )

    # ---------------------------------------------------------------
    # Contract invariants
    # ---------------------------------------------------------------

    invariants = {
        "I-001": (
            "Agent identity != human identity != Lyri identity "
            "!= session identity != task identity"
        ),
        "I-002": (
            "Agent registration/binding != execution authorization"
        ),
        "I-003": (
            "Task binding != capability grant"
        ),
        "I-004": (
            "Capability != authority"
        ),
        "I-005": (
            "Authority != execution admission"
        ),
        "I-006": (
            "Execution admission != execution"
        ),
        "I-007": (
            "Agent Harness != Aegis"
        ),
        "I-008": (
            "Agent Harness != Capability Gateway"
        ),
        "I-009": (
            "Agent Harness != Secure Executor"
        ),
        "I-010": (
            "Agent Harness != Sandbox"
        ),
        "I-011": (
            "Agent Harness != LHICF"
        ),
        "I-012": (
            "Model output cannot establish identity or authority"
        ),
        "I-013": (
            "Invalid/stale/revoked/expired authority fails closed"
        ),
        "I-014": (
            "Execution cannot bypass existing security chain"
        ),
    }

    print()
    print("=" * 100)
    print("CONTRACT INVARIANTS")
    print("=" * 100)

    for identifier, value in invariants.items():
        print(
            f"{identifier}: {value}"
        )

    # ---------------------------------------------------------------
    # Forbidden responsibilities
    # ---------------------------------------------------------------

    forbidden = {
        "F-001": "Create or issue authority",
        "F-002": "Override Aegis decisions",
        "F-003": "Create alternate Capability Gateway",
        "F-004": "Create alternate Execution Admission",
        "F-005": "Execute directly outside SecureExecutor",
        "F-006": "Create a second Sandbox",
        "F-007": "Bypass ProcessBoundary / ChildLauncher",
        "F-008": "Perform privileged host operations",
        "F-009": "Become LHICF",
        "F-010": "Treat model output as authorization",
        "F-011": "Treat registration as execution permission",
        "F-012": "Persist authority without provenance/revocation semantics",
    }

    print()
    print("=" * 100)
    print("FORBIDDEN RESPONSIBILITIES")
    print("=" * 100)

    for identifier, value in forbidden.items():
        print(
            f"{identifier}: {value}"
        )

    # ---------------------------------------------------------------
    # Readiness
    # ---------------------------------------------------------------

    readiness = {
        "identity_surface_present": bool(identity),
        "task_contract_present": bool(task),
        "authority_surface_present": bool(authority),
        "capability_surface_present": bool(capability),
        "secure_executor_present": bool(execution),
        "sandbox_surface_present": bool(sandbox),
        "process_boundary_present": bool(process_boundary),
        "lifecycle_surface_present": bool(lifecycle),
        "provenance_surface_present": bool(provenance),
        "identity_tests_present": bool(identity_tests),
        "authority_tests_present": bool(authority_tests),
        "task_tests_present": bool(task_tests),
        "capability_tests_present": bool(capability_tests),
        "execution_tests_present": bool(execution_tests),
        "sandbox_tests_present": bool(sandbox_tests),
        "process_tests_present": bool(process_tests),
        "lifecycle_tests_present": bool(lifecycle_tests),
        "provenance_tests_present": bool(provenance_tests),
    }

    design_ready = all(
        readiness.values()
    )

    print()
    print("=" * 100)
    print("DESIGN READINESS")
    print("=" * 100)

    for name, value in readiness.items():
        print(
            f"{name:45s}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    # ---------------------------------------------------------------
    # Design boundary
    # ---------------------------------------------------------------

    if design_ready:
        decision = (
            "PB_DOC_005_ENGINEERING_CONTRACT_DESIGN_READY"
        )
    else:
        decision = (
            "PB_DOC_005_ENGINEERING_CONTRACT_DESIGN_REQUIRES_REVIEW"
        )

    print()
    print("=" * 100)
    print("DESIGN DECISION")
    print("=" * 100)
    print(f"Decision: {decision}")

    # ---------------------------------------------------------------
    # Exact proposed implementation boundary
    # ---------------------------------------------------------------

    proposed_boundary = {
        "IN_SCOPE": [
            "Agent Harness contract/type definition",
            "Explicit agent-to-task binding",
            "Binding of existing delegated-authority context",
            "Binding of existing capability context",
            "ExecutionAdmission consumption",
            "Lifecycle integration",
            "Fail-closed validation of binding state",
            "Audit/provenance integration",
            "Unit and adversarial tests for the contract",
        ],
        "OUT_OF_SCOPE": [
            "Aegis policy implementation",
            "Authorization engine redesign",
            "Capability Gateway redesign",
            "Execution Admission redesign",
            "SecureExecutor redesign",
            "Sandbox redesign",
            "ChildLauncher redesign",
            "LHICF implementation",
            "Host privilege implementation",
            "Universal Computer implementation",
            "Self-learning",
            "Self-evolution",
            "Self-awareness",
            "Production certification",
            "G46.5/G47 reconstruction",
        ],
    }

    print()
    print("=" * 100)
    print("PROPOSED IMPLEMENTATION BOUNDARY")
    print("=" * 100)

    for category, items in proposed_boundary.items():
        print()
        print(category)

        for item in items:
            print(
                f"  - {item}"
            )

    # ---------------------------------------------------------------
    # Evidence boundary
    # ---------------------------------------------------------------

    print()
    print("=" * 100)
    print("EVIDENCE BOUNDARY")
    print("=" * 100)
    print(
        "Analysis type                 : "
        "STATIC ENGINEERING CONTRACT DESIGN"
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
        "surface_counts": {
            "identity": len(identity),
            "task": len(task),
            "authority": len(authority),
            "capability": len(capability),
            "execution": len(execution),
            "sandbox": len(sandbox),
            "process_boundary": len(process_boundary),
            "lifecycle": len(lifecycle),
            "provenance": len(provenance),
        },
        "test_surface_counts": {
            "identity": len(identity_tests),
            "authority": len(authority_tests),
            "task": len(task_tests),
            "capability": len(capability_tests),
            "execution": len(execution_tests),
            "sandbox": len(sandbox_tests),
            "process_boundary": len(process_tests),
            "lifecycle": len(lifecycle_tests),
            "provenance": len(provenance_tests),
        },
        "requirements": [
            {
                "id": item.identifier,
                "requirement": item.requirement,
                "boundary": item.source_boundary,
                "existing_support": list(
                    item.existing_support
                ),
                "status": item.implementation_status,
            }
            for item in requirements
        ],
        "invariants": invariants,
        "forbidden_responsibilities": forbidden,
        "readiness": readiness,
        "proposed_boundary": proposed_boundary,
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

    return 0 if design_ready else 4


if __name__ == "__main__":
    raise SystemExit(main())

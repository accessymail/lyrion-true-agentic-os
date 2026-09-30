#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005 — Agent Harness Implementation Design Review

READ-ONLY IMPLEMENTATION DESIGN GATE.

Purpose
-------
Translate the accepted PB-DOC-005 formal contract specification into an
implementation design that identifies:

    - exact candidate module placement
    - existing contracts to extend/reuse
    - dependency direction
    - API/data-model boundaries
    - validation responsibilities
    - integration points
    - test placement
    - migration/compatibility constraints
    - prohibited architectural changes

This tool DOES NOT modify runtime source, tests, documentation, manifests,
Git history, G46.5/G47 artifacts, or R097.

Implementation must remain inside the established architecture:

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
    Host / LHICF

Agent Harness is an orchestration/binding layer only.

It MUST NOT become:
    - an authorization authority
    - a capability authority
    - an execution authority
    - a sandbox authority
    - a host privilege layer
    - an LHICF replacement

Evidence class:
    STATIC IMPLEMENTATION DESIGN REVIEW
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

SELF_NAME = "design_pb_doc_005_implementation.py"

ALLOWED_AUDIT_TOOLS = {
    SELF_NAME,
    "specify_pb_doc_005_agent_harness_contract.py",
    "design_pb_doc_005_agent_harness_contract.py",
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
class CandidateModule:
    path: str
    role: str
    existing_symbols: tuple[str, ...]
    proposed_extension: str
    risk: str


@dataclass(frozen=True)
class IntegrationPoint:
    identifier: str
    upstream: str
    downstream: str
    contract: str
    direction: str
    rule: str


@dataclass(frozen=True)
class TestPlan:
    identifier: str
    path: str
    category: str
    purpose: str


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
        failures.append("HEAD != origin/main")

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


def module_name(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT)
    parts = list(relative.parts)

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(["lyrion", *parts])


class Visitor(ast.NodeVisitor):
    def __init__(self, module: str) -> None:
        self.module = module
        self.symbols: list[Symbol] = []
        self.imports: list[str] = []
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


def symbols_for(
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


def existing_path(
    relative_path: str,
) -> bool:
    return (
        REPO_ROOT / relative_path
    ).exists()


def matching_tests(
    tests: list[Path],
    terms: tuple[str, ...],
) -> list[str]:
    result: list[str] = []

    for path in tests:
        try:
            content = path.read_text(
                encoding="utf-8",
            ).lower()
        except Exception:
            continue

        if any(
            term.lower() in content
            for term in terms
        ):
            result.append(
                str(
                    path.relative_to(REPO_ROOT)
                )
            )

    return sorted(result)


def main() -> int:
    print("=" * 100)
    print(
        "LYRION PB-DOC-005 AGENT HARNESS "
        "IMPLEMENTATION DESIGN REVIEW"
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
            "Decision: IMPLEMENTATION_DESIGN_INCOMPLETE"
        )
        return 3

    # ------------------------------------------------------------------
    # Existing implementation surfaces
    # ------------------------------------------------------------------

    surface_terms = {
        "identity": (
            "AgentIdentity",
            "ApplicationPrincipalContext",
            "ProcessIdentity",
        ),
        "task": (
            "Task",
            "TaskContext",
            "ExecutionRequest",
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
        ),
        "authority": (
            "AegisAuthorizationService",
            "AuthorizationGuard",
            "ReplayGuard",
            "AuthorizationResult",
        ),
        "capability": (
            "CapabilityRequest",
            "CapabilityGateway",
            "CapabilityOperation",
        ),
        "executor": (
            "SecureExecutor",
            "ExecutionValidator",
        ),
        "sandbox": (
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
            "SandboxConfig",
            "ResourceLimits",
        ),
        "process": (
            "ChildLauncher",
            "LaunchHandoff",
            "ChildLaunchResult",
        ),
        "lifecycle": (
            "PIAE",
            "PersistentExecutionLifecycle",
            "RuntimeLifecycle",
        ),
        "provenance": (
            "Provenance",
            "Verification",
            "Audit",
            "Evidence",
        ),
    }

    surface_counts: dict[str, int] = {}

    print()
    print("=" * 100)
    print("EXISTING IMPLEMENTATION SURFACES")
    print("=" * 100)

    for name, terms in surface_terms.items():
        found = symbols_for(
            symbols,
            terms,
        )

        surface_counts[name] = len(found)

        print(
            f"{name:20s}: "
            f"{len(found)} symbols"
        )

    # ------------------------------------------------------------------
    # Candidate module placement
    # ------------------------------------------------------------------

    candidates = [
        CandidateModule(
            path="src/lyrion/agent_harness/",
            role=(
                "Dedicated Agent Harness contract and binding layer."
            ),
            existing_symbols=(
                "No explicit AgentHarness symbol currently established",
            ),
            proposed_extension=(
                "Introduce the bounded Agent Harness contract here "
                "without duplicating authorization or execution."
            ),
            risk=(
                "Must remain a binding/orchestration layer and "
                "must not become a privileged execution path."
            ),
        ),
        CandidateModule(
            path="src/lyrion/execution/contracts.py",
            role=(
                "Existing execution/task contract definitions."
            ),
            existing_symbols=(
                "ExecutionRequest",
                "ExecutionAdmission",
                "ExecutionAdmissionEnvelope",
            ),
            proposed_extension=(
                "Reuse existing contracts as Agent Harness "
                "integration anchors; avoid moving ownership."
            ),
            risk=(
                "Changing existing execution contracts could "
                "increase blast radius."
            ),
        ),
        CandidateModule(
            path="src/lyrion/security/",
            role=(
                "Existing Aegis/authorization security boundary."
            ),
            existing_symbols=(
                "AegisAuthorizationService",
                "AuthorizationGuard",
                "ReplayGuard",
            ),
            proposed_extension=(
                "Consume authorization state only."
            ),
            risk=(
                "Any new authority logic here would violate "
                "the bounded slice."
            ),
        ),
        CandidateModule(
            path="src/lyrion/capabilities/gateway.py",
            role=(
                "Existing capability mediation boundary."
            ),
            existing_symbols=(
                "CapabilityGateway",
            ),
            proposed_extension=(
                "Consume capability admission state only."
            ),
            risk=(
                "No Agent Harness-owned capability grant."
            ),
        ),
        CandidateModule(
            path="src/lyrion/execution/executor.py",
            role=(
                "Existing secure execution boundary."
            ),
            existing_symbols=(
                "SecureExecutor",
            ),
            proposed_extension=(
                "Agent Harness delegates into existing executor."
            ),
            risk=(
                "No direct process creation or privileged execution."
            ),
        ),
    ]

    print()
    print("=" * 100)
    print("CANDIDATE MODULE PLACEMENT")
    print("=" * 100)

    for candidate in candidates:
        print()
        print(
            f"Path : {candidate.path}"
        )
        print(
            f"Role : {candidate.role}"
        )
        print(
            "Existing symbols:"
        )

        for symbol in candidate.existing_symbols:
            print(
                f"  - {symbol}"
            )

        print(
            f"Proposed extension: "
            f"{candidate.proposed_extension}"
        )
        print(
            f"Risk: {candidate.risk}"
        )

    # ------------------------------------------------------------------
    # Recommended ownership
    # ------------------------------------------------------------------

    ownership = {
        "Agent Harness contract": (
            "src/lyrion/agent_harness/"
        ),
        "Execution/task contracts": (
            "src/lyrion/execution/contracts.py"
        ),
        "Authorization": (
            "src/lyrion/security/"
        ),
        "Capability mediation": (
            "src/lyrion/capabilities/gateway.py"
        ),
        "Secure execution": (
            "src/lyrion/execution/executor.py"
        ),
        "Sandbox": (
            "existing sandbox/enforcement modules"
        ),
        "Process boundary": (
            "existing ChildLauncher / LaunchHandoff modules"
        ),
        "Lifecycle": (
            "existing PIAE/runtime lifecycle modules"
        ),
        "Verification/provenance": (
            "existing audit/provenance modules"
        ),
    }

    print()
    print("=" * 100)
    print("OWNERSHIP MODEL")
    print("=" * 100)

    for owner, path in ownership.items():
        print(
            f"{owner:30s}: {path}"
        )

    # ------------------------------------------------------------------
    # Integration points
    # ------------------------------------------------------------------

    integrations = [
        IntegrationPoint(
            "INT-001",
            "Agent Harness",
            "Aegis Authorization",
            "Delegated authority context",
            "CONSUME",
            "No authority creation",
        ),
        IntegrationPoint(
            "INT-002",
            "Agent Harness",
            "Capability Gateway",
            "Authorized capability context",
            "CONSUME",
            "No capability expansion",
        ),
        IntegrationPoint(
            "INT-003",
            "Agent Harness",
            "Execution Admission",
            "ExecutionAdmission / Envelope",
            "REQUIRE",
            "No execution without valid admission",
        ),
        IntegrationPoint(
            "INT-004",
            "Agent Harness",
            "Secure Executor",
            "Validated execution request",
            "DELEGATE",
            "No direct privileged execution",
        ),
        IntegrationPoint(
            "INT-005",
            "Secure Executor",
            "Sandbox",
            "Sandbox policy/resource enforcement",
            "REUSE",
            "Existing downstream enforcement remains authoritative",
        ),
        IntegrationPoint(
            "INT-006",
            "Secure Executor",
            "Child Launcher",
            "LaunchHandoff",
            "REUSE",
            "Process boundary remains downstream",
        ),
        IntegrationPoint(
            "INT-007",
            "Agent Harness",
            "PIAE / Runtime",
            "Lifecycle/task context",
            "INTEGRATE",
            "Lifecycle is not authorization",
        ),
        IntegrationPoint(
            "INT-008",
            "Agent Harness",
            "Audit / Provenance",
            "Attribution and execution provenance",
            "EMIT",
            "No unverifiable execution",
        ),
    ]

    print()
    print("=" * 100)
    print("INTEGRATION POINTS")
    print("=" * 100)

    for item in integrations:
        print()
        print(
            f"{item.identifier}"
        )
        print(
            f"  {item.upstream} "
            f"--[{item.contract}/{item.direction}]--> "
            f"{item.downstream}"
        )
        print(
            f"  Rule: {item.rule}"
        )

    # ------------------------------------------------------------------
    # Data model
    # ------------------------------------------------------------------

    data_model = {
        "AgentBinding": {
            "agent_id": "required immutable identifier",
            "task_id": "required task identifier",
            "authority_context": (
                "reference to existing delegated authority"
            ),
            "capability_context": (
                "reference to authorized capability context"
            ),
            "execution_admission": (
                "reference to existing valid admission"
            ),
            "lifecycle_state": (
                "existing runtime lifecycle state"
            ),
            "provenance_context": (
                "audit/provenance attribution"
            ),
        },
        "BindingValidationResult": {
            "valid": "boolean",
            "failure_reason": (
                "structured fail-closed reason when invalid"
            ),
            "validated_agent_id": (
                "attributable identity when valid"
            ),
            "validated_task_id": (
                "bound task when valid"
            ),
            "validated_admission": (
                "existing admission reference when valid"
            ),
        },
    }

    print()
    print("=" * 100)
    print("PROPOSED DATA MODEL")
    print("=" * 100)

    for name, fields in data_model.items():
        print()
        print(name)

        for field, description in fields.items():
            print(
                f"  {field:24s}: "
                f"{description}"
            )

    # ------------------------------------------------------------------
    # API boundary
    # ------------------------------------------------------------------

    api = {
        "bind": (
            "Create/validate AgentBinding from already-authorized "
            "execution context."
        ),
        "validate": (
            "Validate identity/task/authority/capability/admission/"
            "lifecycle consistency."
        ),
        "delegate": (
            "Delegate an already-valid execution context to the "
            "existing SecureExecutor."
        ),
        "provenance": (
            "Return attributable binding/execution provenance."
        ),
    }

    forbidden_api = {
        "authorize": (
            "Forbidden: Agent Harness must not authorize."
        ),
        "grant_capability": (
            "Forbidden: Agent Harness must not grant capabilities."
        ),
        "create_admission": (
            "Forbidden: Agent Harness must not independently create "
            "execution admission."
        ),
        "execute_privileged": (
            "Forbidden: Agent Harness must not directly execute "
            "privileged host operations."
        ),
        "bypass_security": (
            "Forbidden: no security-chain bypass API."
        ),
    }

    print()
    print("=" * 100)
    print("PROPOSED API BOUNDARY")
    print("=" * 100)

    for name, description in api.items():
        print(
            f"  {name:18s}: {description}"
        )

    print()
    print("FORBIDDEN API")

    for name, description in forbidden_api.items():
        print(
            f"  {name:18s}: {description}"
        )

    # ------------------------------------------------------------------
    # Test placement
    # ------------------------------------------------------------------

    test_plan = [
        TestPlan(
            "T-001",
            "tests/unit/agent_harness/",
            "Contract",
            "AgentBinding construction and immutable identity/task association.",
        ),
        TestPlan(
            "T-002",
            "tests/unit/agent_harness/",
            "Validation",
            "Fail-closed validation for missing/mismatched context.",
        ),
        TestPlan(
            "T-003",
            "tests/unit/agent_harness/",
            "Authority",
            "Expired/revoked/invalid/self-granted authority rejection.",
        ),
        TestPlan(
            "T-004",
            "tests/unit/agent_harness/",
            "Capability",
            "Capability mismatch and authority-bound capability validation.",
        ),
        TestPlan(
            "T-005",
            "tests/unit/agent_harness/",
            "Admission",
            "ExecutionAdmission requirement and validation.",
        ),
        TestPlan(
            "T-006",
            "tests/unit/agent_harness/",
            "Security",
            "Security-chain bypass rejection.",
        ),
        TestPlan(
            "T-007",
            "tests/unit/agent_harness/",
            "Process",
            "ChildLauncher/LaunchHandoff remains the process boundary.",
        ),
        TestPlan(
            "T-008",
            "tests/unit/agent_harness/",
            "Lifecycle",
            "Valid and invalid lifecycle transitions.",
        ),
        TestPlan(
            "T-009",
            "tests/unit/agent_harness/",
            "Provenance",
            "Attribution and verification preservation.",
        ),
        TestPlan(
            "T-010",
            "tests/integration/agent_harness/",
            "Integration",
            "Agent Harness -> existing ExecutionAdmission -> SecureExecutor.",
        ),
        TestPlan(
            "T-011",
            "tests/integration/agent_harness/",
            "Adversarial",
            "Prompt/model/memory/tool-output identity or authority injection.",
        ),
        TestPlan(
            "T-012",
            "tests/integration/agent_harness/",
            "Regression",
            "Existing execution/security behavior remains unchanged.",
        ),
    ]

    print()
    print("=" * 100)
    print("IMPLEMENTATION TEST PLAN")
    print("=" * 100)

    for item in test_plan:
        print(
            f"{item.identifier} | "
            f"{item.category}"
        )
        print(
            f"  Path   : {item.path}"
        )
        print(
            f"  Purpose: {item.purpose}"
        )

    # ------------------------------------------------------------------
    # Compatibility and migration rules
    # ------------------------------------------------------------------

    compatibility_rules = [
        "Existing execution contracts remain source-of-truth.",
        "Existing authorization contracts remain source-of-truth.",
        "Existing capability contracts remain source-of-truth.",
        "Existing SecureExecutor remains execution owner.",
        "Existing Sandbox remains downstream enforcement owner.",
        "Existing ChildLauncher remains process-boundary owner.",
        "No breaking change to existing execution semantics unless required by contract validation.",
        "Agent Harness integration must be additive and capability-scoped.",
        "Existing callers must not silently acquire new authority.",
        "No migration may weaken fail-closed behavior.",
    ]

    print()
    print("=" * 100)
    print("COMPATIBILITY / MIGRATION RULES")
    print("=" * 100)

    for rule in compatibility_rules:
        print(
            f"  - {rule}"
        )

    # ------------------------------------------------------------------
    # Architecture hazards
    # ------------------------------------------------------------------

    hazards = {
        "H-001": (
            "Agent Harness accidentally becomes an authorization authority."
        ),
        "H-002": (
            "Agent Harness creates a parallel ExecutionAdmission path."
        ),
        "H-003": (
            "Agent Harness directly invokes process/host execution."
        ),
        "H-004": (
            "Agent Harness duplicates Sandbox enforcement."
        ),
        "H-005": (
            "Agent Harness mutates or expands delegated authority."
        ),
        "H-006": (
            "Agent identity becomes inferred from model output."
        ),
        "H-007": (
            "Existing execution contracts are unnecessarily redesigned."
        ),
        "H-008": (
            "LHICF responsibility is duplicated instead of consumed."
        ),
    }

    print()
    print("=" * 100)
    print("ARCHITECTURE HAZARDS")
    print("=" * 100)

    for identifier, hazard in hazards.items():
        print(
            f"{identifier}: {hazard}"
        )

    # ------------------------------------------------------------------
    # Design checks
    # ------------------------------------------------------------------

    checks = {
        "security_chain_surfaces_present": all(
            surface_counts.get(name, 0) > 0
            for name in (
                "authority",
                "capability",
                "task",
                "executor",
                "sandbox",
                "process",
            )
        ),
        "lifecycle_surface_present": (
            surface_counts["lifecycle"] > 0
        ),
        "provenance_surface_present": (
            surface_counts["provenance"] > 0
        ),
        "dedicated_agent_harness_namespace_is_free": (
            not existing_path(
                "src/lyrion/agent_harness/"
            )
        ),
        "execution_contract_exists": (
            existing_path(
                "src/lyrion/execution/contracts.py"
            )
        ),
        "secure_executor_exists": (
            existing_path(
                "src/lyrion/execution/executor.py"
            )
        ),
        "capability_gateway_exists": (
            existing_path(
                "src/lyrion/capabilities/gateway.py"
            )
        ),
        "security_package_exists": (
            existing_path(
                "src/lyrion/security/"
            )
        ),
        "no_runtime_source_mutation": True,
        "no_test_source_mutation": True,
        "production_certification_not_claimed": True,
    }

    print()
    print("=" * 100)
    print("IMPLEMENTATION DESIGN CHECKS")
    print("=" * 100)

    for name, value in checks.items():
        print(
            f"{name:50s}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    design_ready = all(
        checks.values()
    )

    # ------------------------------------------------------------------
    # Explicit implementation sequence
    # ------------------------------------------------------------------

    implementation_sequence = [
        "1. Create the dedicated Agent Harness contract namespace.",
        "2. Define immutable AgentBinding contract.",
        "3. Define structured BindingValidationResult.",
        "4. Implement fail-closed binding validation only.",
        "5. Integrate existing authority state without creating authority.",
        "6. Integrate existing capability state without granting capability.",
        "7. Require existing ExecutionAdmission.",
        "8. Delegate execution to existing SecureExecutor.",
        "9. Preserve existing Sandbox and ChildLauncher boundaries.",
        "10. Integrate existing PIAE/runtime lifecycle semantics.",
        "11. Add contract/unit/adversarial/integration tests.",
        "12. Run controlled validation.",
        "13. Perform independent review before documentation synchronization.",
    ]

    print()
    print("=" * 100)
    print("PROPOSED IMPLEMENTATION SEQUENCE")
    print("=" * 100)

    for step in implementation_sequence:
        print(
            f"  {step}"
        )

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    if design_ready:
        decision = (
            "PB_DOC_005_IMPLEMENTATION_DESIGN_READY"
        )
    else:
        decision = (
            "PB_DOC_005_IMPLEMENTATION_DESIGN_REQUIRES_REVIEW"
        )

    print()
    print("=" * 100)
    print("FINAL DESIGN DECISION")
    print("=" * 100)
    print(
        f"Decision: {decision}"
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
        "STATIC IMPLEMENTATION DESIGN"
    )
    print(
        "Runtime implementation        : NOT PERFORMED"
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
        "ast_failures": parse_failures,
        "surface_counts": surface_counts,
        "candidate_modules": [
            {
                "path": candidate.path,
                "role": candidate.role,
                "existing_symbols": list(
                    candidate.existing_symbols
                ),
                "proposed_extension": candidate.proposed_extension,
                "risk": candidate.risk,
            }
            for candidate in candidates
        ],
        "ownership": ownership,
        "integration_points": [
            {
                "id": item.identifier,
                "upstream": item.upstream,
                "downstream": item.downstream,
                "contract": item.contract,
                "direction": item.direction,
                "rule": item.rule,
            }
            for item in integrations
        ],
        "data_model": data_model,
        "api": api,
        "forbidden_api": forbidden_api,
        "test_plan": [
            {
                "id": item.identifier,
                "path": item.path,
                "category": item.category,
                "purpose": item.purpose,
            }
            for item in test_plan
        ],
        "compatibility_rules": compatibility_rules,
        "hazards": hazards,
        "checks": checks,
        "implementation_sequence": implementation_sequence,
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

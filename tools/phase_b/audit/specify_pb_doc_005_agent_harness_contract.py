#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005 — Formal Agent Harness Contract Specification Review

READ-ONLY DESIGN SPECIFICATION GATE.

This tool formalizes the already-reviewed PB-DOC-005 bounded slice into
a precise implementation contract.

It does NOT:
    - modify runtime source
    - modify tests
    - modify documentation
    - modify manifests
    - modify Git
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification

Contract boundary:

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
    Existing PIAE / Runtime Lifecycle
        ->
    Verification / Provenance

Core architectural invariant:

    Agent Harness coordinates and binds execution context.
    It does not create authority and does not directly execute privileged
    operations.

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
    Host / LHICF

The formal contract is divided into:

    1. Identity contract
    2. Task-binding contract
    3. Authority contract
    4. Capability contract
    5. Execution-admission contract
    6. Lifecycle contract
    7. Failure-state contract
    8. Audit/provenance contract
    9. Security invariants
    10. Non-responsibilities
    11. Test obligations
    12. Implementation boundary
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
    "specify_pb_doc_005_agent_harness_contract.py"
)

ALLOWED_AUDIT_TOOLS = {
    SELF_NAME,
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
class ContractClause:
    identifier: str
    category: str
    statement: str
    required_state: str
    failure_behavior: str
    existing_anchor: tuple[str, ...]


@dataclass(frozen=True)
class TestObligation:
    identifier: str
    category: str
    scenario: str
    expected_result: str
    security_property: str


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
        self.class_stack: list[str] = []

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
    int,
]:
    symbols: list[Symbol] = []
    failures = 0

    for path in source_files():
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

        visitor = Visitor(
            module_name(path),
        )
        visitor.visit(tree)
        symbols.extend(visitor.symbols)

    return symbols, failures


def symbol_present(
    symbols: list[Symbol],
    terms: tuple[str, ...],
) -> bool:
    return any(
        any(
            term.lower()
            in symbol.qualified.lower()
            for term in terms
        )
        for symbol in symbols
    )


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
        "LYRION PB-DOC-005 FORMAL AGENT HARNESS "
        "CONTRACT SPECIFICATION REVIEW"
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

    symbols, parse_failures = parse_sources()

    print()
    print("-" * 100)
    print("SOURCE BASELINE")
    print("-" * 100)
    print(
        f"Runtime Python files : {len(sources)}"
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
            "Decision: CONTRACT_SPECIFICATION_INCOMPLETE"
        )
        return 3

    # ------------------------------------------------------------------
    # Existing implementation anchors
    # ------------------------------------------------------------------

    anchors = {
        "agent_identity": (
            "AgentIdentity",
            "ApplicationPrincipalContext",
            "ProcessIdentity",
        ),
        "task": (
            "Task",
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
        "execution": (
            "SecureExecutor",
            "ExecutionValidator",
        ),
        "sandbox": (
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
            "SandboxConfig",
            "ResourceLimits",
        ),
        "process_boundary": (
            "ChildLauncher",
            "LaunchHandoff",
            "ChildLaunchResult",
        ),
        "lifecycle": (
            "PIAE",
            "PersistentExecutionLifecycle",
            "RuntimeLifecycleState",
        ),
        "provenance": (
            "Provenance",
            "Verification",
            "Audit",
            "Evidence",
        ),
    }

    print()
    print("=" * 100)
    print("EXISTING CONTRACT ANCHORS")
    print("=" * 100)

    anchor_presence: dict[str, bool] = {}

    for category, terms in anchors.items():
        present = symbol_present(
            symbols,
            terms,
        )
        anchor_presence[category] = present

        print(
            f"{category:24s}: "
            f"{'PRESENT' if present else 'MISSING'}"
        )

    # ------------------------------------------------------------------
    # Formal clauses
    # ------------------------------------------------------------------

    clauses = [
        ContractClause(
            "AHC-001",
            "Identity",
            "Every Agent Harness execution context MUST carry an explicit attributable agent identity.",
            "Agent identity is present and independently attributable.",
            "FAIL CLOSED; no task binding or execution admission.",
            (
                "AgentIdentity",
                "ApplicationPrincipalContext",
            ),
        ),
        ContractClause(
            "AHC-002",
            "Identity",
            "Agent identity MUST remain distinct from human, Lyri, session, task, model, provider and tool identities.",
            "Identity domains remain explicitly separated.",
            "REJECT ambiguous identity binding.",
            (
                "AgentIdentity",
                "ProcessIdentity",
            ),
        ),
        ContractClause(
            "AHC-003",
            "Task Binding",
            "An Agent Harness binding MUST associate one attributable agent context with an explicitly identified task context.",
            "Agent and task identities are both present and consistent.",
            "FAIL CLOSED.",
            (
                "Task",
                "ExecutionRequest",
                "ExecutionAdmissionEnvelope",
            ),
        ),
        ContractClause(
            "AHC-004",
            "Authority",
            "Agent Harness MUST consume delegated authority established by the existing authorization architecture.",
            "Existing authorization state is valid, current and attributable.",
            "DENY when authority is missing, expired, revoked or invalid.",
            (
                "AegisAuthorizationService",
                "AuthorizationGuard",
                "ReplayGuard",
            ),
        ),
        ContractClause(
            "AHC-005",
            "Authority",
            "Agent Harness MUST NOT create, expand, attenuate beyond policy, or independently issue execution authority.",
            "Authority is externally established and bounded.",
            "REJECT any attempted self-grant or authority expansion.",
            (
                "AegisAuthorizationService",
                "AuthorizationResult",
            ),
        ),
        ContractClause(
            "AHC-006",
            "Capability",
            "Agent Harness MUST bind only to capabilities already represented by the authorized execution context.",
            "Capability and authority remain consistent.",
            "DENY capability mismatch.",
            (
                "CapabilityRequest",
                "CapabilityGateway",
            ),
        ),
        ContractClause(
            "AHC-007",
            "Execution Admission",
            "No Agent Harness execution MAY proceed without valid existing ExecutionAdmission.",
            "Admission is present, valid, current and attributable.",
            "FAIL CLOSED.",
            (
                "ExecutionAdmission",
                "ExecutionAdmissionEnvelope",
            ),
        ),
        ContractClause(
            "AHC-008",
            "Execution",
            "Agent Harness MUST delegate execution to SecureExecutor and MUST NOT directly execute privileged host operations.",
            "Execution enters the existing secure execution path.",
            "REJECT direct execution path.",
            (
                "SecureExecutor",
                "ExecutionValidator",
            ),
        ),
        ContractClause(
            "AHC-009",
            "Sandbox",
            "Sandbox policy and resource limits MUST remain downstream enforcement controls.",
            "Sandbox policy is attached to admitted execution.",
            "DENY execution when sandbox requirements fail.",
            (
                "SandboxPolicy",
                "SandboxPolicyEvaluator",
                "ResourceLimits",
            ),
        ),
        ContractClause(
            "AHC-010",
            "Process Boundary",
            "Process creation MUST remain behind the existing ChildLauncher / LaunchHandoff boundary.",
            "Validated LaunchHandoff reaches the process boundary.",
            "REJECT malformed or invalid handoff.",
            (
                "ChildLauncher",
                "LaunchHandoff",
            ),
        ),
        ContractClause(
            "AHC-011",
            "Lifecycle",
            "Agent lifecycle state MUST integrate with existing PIAE/runtime lifecycle semantics.",
            "Lifecycle transition is valid and attributable.",
            "REJECT invalid lifecycle transition.",
            (
                "PIAE",
                "PersistentExecutionLifecycle",
            ),
        ),
        ContractClause(
            "AHC-012",
            "Revocation / Expiry",
            "Revoked, expired, stale or otherwise invalid delegated authority MUST prevent execution.",
            "Authority remains valid at admission/execution boundary.",
            "FAIL CLOSED.",
            (
                "AuthorizationResult",
                "AuthorizationGuard",
                "ExecutionAdmission",
            ),
        ),
        ContractClause(
            "AHC-013",
            "Replay",
            "Replay-sensitive execution state MUST preserve existing replay protection.",
            "Execution context is not an unauthorized replay.",
            "DENY replay.",
            (
                "ReplayGuard",
            ),
        ),
        ContractClause(
            "AHC-014",
            "Provenance",
            "Agent binding, execution admission and resulting execution MUST remain attributable to audit/provenance records.",
            "Provenance identity remains linked throughout execution.",
            "REJECT unverifiable execution result.",
            (
                "Audit",
                "Provenance",
                "Verification",
            ),
        ),
        ContractClause(
            "AHC-015",
            "Model Boundary",
            "Model output, prompt content, memory content or tool output MUST NOT establish agent identity or authority.",
            "Identity and authority originate from trusted contracts.",
            "REJECT untrusted identity/authority claims.",
            (
                "AgentIdentity",
                "AuthorizationResult",
            ),
        ),
        ContractClause(
            "AHC-016",
            "Security Chain",
            "Agent Harness MUST preserve Aegis -> Capability Gateway -> Execution Admission -> Secure Executor -> Sandbox -> Process Boundary ordering.",
            "Security chain remains intact.",
            "FAIL CLOSED on missing or bypassed boundary.",
            (
                "AegisAuthorizationService",
                "CapabilityGateway",
                "ExecutionAdmission",
                "SecureExecutor",
                "SandboxPolicyEvaluator",
                "ChildLauncher",
            ),
        ),
    ]

    print()
    print("=" * 100)
    print("FORMAL CONTRACT CLAUSES")
    print("=" * 100)

    for clause in clauses:
        print()
        print(
            f"{clause.identifier} | "
            f"{clause.category}"
        )
        print(
            f"  Statement       : "
            f"{clause.statement}"
        )
        print(
            f"  Required state  : "
            f"{clause.required_state}"
        )
        print(
            f"  Failure behavior: "
            f"{clause.failure_behavior}"
        )
        print(
            f"  Existing anchor : "
            f"{', '.join(clause.existing_anchor)}"
        )

    # ------------------------------------------------------------------
    # Failure states
    # ------------------------------------------------------------------

    failure_states = {
        "UNBOUND_AGENT": (
            "Agent identity missing or invalid",
            "DENY / FAIL CLOSED",
        ),
        "TASK_MISMATCH": (
            "Agent/task binding inconsistent",
            "DENY / FAIL CLOSED",
        ),
        "AUTHORITY_MISSING": (
            "Delegated authority absent",
            "DENY / FAIL CLOSED",
        ),
        "AUTHORITY_EXPIRED": (
            "Authority expired",
            "DENY / FAIL CLOSED",
        ),
        "AUTHORITY_REVOKED": (
            "Authority revoked",
            "DENY / FAIL CLOSED",
        ),
        "AUTHORITY_INVALID": (
            "Authority validation failed",
            "DENY / FAIL CLOSED",
        ),
        "CAPABILITY_MISMATCH": (
            "Capability does not match authorized context",
            "DENY / FAIL CLOSED",
        ),
        "ADMISSION_MISSING": (
            "Execution admission absent",
            "DENY / FAIL CLOSED",
        ),
        "ADMISSION_INVALID": (
            "Execution admission invalid",
            "DENY / FAIL CLOSED",
        ),
        "SANDBOX_REJECTED": (
            "Sandbox policy rejects operation",
            "DENY / FAIL CLOSED",
        ),
        "PROCESS_HANDOFF_INVALID": (
            "LaunchHandoff invalid or integrity failure",
            "DENY / FAIL CLOSED",
        ),
        "LIFECYCLE_INVALID": (
            "Invalid agent/task lifecycle transition",
            "REJECT TRANSITION",
        ),
        "REPLAY_DETECTED": (
            "Replay protection detects reuse",
            "DENY / FAIL CLOSED",
        ),
        "PROVENANCE_FAILURE": (
            "Execution cannot be attributed or verified",
            "FAIL CLOSED / UNVERIFIED",
        ),
    }

    print()
    print("=" * 100)
    print("FAILURE STATES")
    print("=" * 100)

    for state, (description, behavior) in failure_states.items():
        print(
            f"{state:26s}: "
            f"{description} -> {behavior}"
        )

    # ------------------------------------------------------------------
    # Test obligations
    # ------------------------------------------------------------------

    test_obligations = [
        TestObligation(
            "AHT-001",
            "Identity",
            "Valid attributable agent binds to a valid task.",
            "ACCEPT",
            "Identity attribution",
        ),
        TestObligation(
            "AHT-002",
            "Identity",
            "Missing agent identity is rejected.",
            "DENY",
            "Fail closed",
        ),
        TestObligation(
            "AHT-003",
            "Task Binding",
            "Agent/task mismatch is rejected.",
            "DENY",
            "Identity/task separation",
        ),
        TestObligation(
            "AHT-004",
            "Authority",
            "Valid delegated authority is consumed without mutation.",
            "ACCEPT",
            "Least privilege",
        ),
        TestObligation(
            "AHT-005",
            "Authority",
            "Self-granted authority is rejected.",
            "DENY",
            "Authority separation",
        ),
        TestObligation(
            "AHT-006",
            "Authority",
            "Expired authority is rejected.",
            "DENY",
            "Expiry enforcement",
        ),
        TestObligation(
            "AHT-007",
            "Authority",
            "Revoked authority is rejected.",
            "DENY",
            "Revocation enforcement",
        ),
        TestObligation(
            "AHT-008",
            "Capability",
            "Capability mismatch is rejected.",
            "DENY",
            "Capability binding",
        ),
        TestObligation(
            "AHT-009",
            "Admission",
            "Missing execution admission is rejected.",
            "DENY",
            "Admission boundary",
        ),
        TestObligation(
            "AHT-010",
            "Admission",
            "Invalid execution admission is rejected.",
            "DENY",
            "Fail closed",
        ),
        TestObligation(
            "AHT-011",
            "Execution",
            "Valid binding delegates to SecureExecutor.",
            "EXECUTE THROUGH EXISTING PATH",
            "Execution-chain preservation",
        ),
        TestObligation(
            "AHT-012",
            "Sandbox",
            "Sandbox rejection prevents execution.",
            "DENY",
            "Sandbox enforcement",
        ),
        TestObligation(
            "AHT-013",
            "Process Boundary",
            "Invalid LaunchHandoff prevents child creation.",
            "DENY",
            "Process-boundary integrity",
        ),
        TestObligation(
            "AHT-014",
            "Replay",
            "Replay attempt is rejected.",
            "DENY",
            "Replay protection",
        ),
        TestObligation(
            "AHT-015",
            "Lifecycle",
            "Invalid lifecycle transition is rejected.",
            "REJECT TRANSITION",
            "Lifecycle integrity",
        ),
        TestObligation(
            "AHT-016",
            "Provenance",
            "Execution remains attributable and verifiable.",
            "ACCEPT WITH PROVENANCE",
            "Auditability",
        ),
        TestObligation(
            "AHT-017",
            "Model Boundary",
            "Model output cannot create identity or authority.",
            "DENY",
            "Untrusted-input separation",
        ),
        TestObligation(
            "AHT-018",
            "Security Chain",
            "Attempted security-chain bypass is rejected.",
            "DENY",
            "Defense in depth",
        ),
    ]

    print()
    print("=" * 100)
    print("TEST OBLIGATIONS")
    print("=" * 100)

    for test in test_obligations:
        print(
            f"{test.identifier} | "
            f"{test.category}"
        )
        print(
            f"  Scenario : {test.scenario}"
        )
        print(
            f"  Expected : {test.expected_result}"
        )
        print(
            f"  Property : {test.security_property}"
        )

    # ------------------------------------------------------------------
    # Existing test coverage signals
    # ------------------------------------------------------------------

    test_groups = {
        "identity": (
            "identity",
            "agent",
            "principal",
        ),
        "authority": (
            "aegis_authorization",
            "authorization",
            "aegis_guards",
            "replay",
            "revocation",
        ),
        "task": (
            "execution_contract",
            "execution_lifecycle",
            "execution_runner",
            "task",
        ),
        "capability": (
            "capability",
            "gateway",
        ),
        "execution": (
            "secure_executor",
            "execution_result",
            "execution_admission",
        ),
        "sandbox": (
            "sandbox",
            "enforcement",
            "resource",
        ),
        "process_boundary": (
            "child_launcher",
            "process_boundary",
            "child_context",
        ),
        "lifecycle": (
            "lifecycle",
            "runtime",
            "piae",
        ),
        "provenance": (
            "provenance",
            "verification",
            "audit",
        ),
    }

    test_surface_counts: dict[str, int] = {}

    print()
    print("=" * 100)
    print("TEST-SURFACE ALIGNMENT")
    print("=" * 100)

    for group, terms in test_groups.items():
        count = len(
            matching_tests(
                tests,
                terms,
            )
        )

        test_surface_counts[group] = count

        print(
            f"{group:24s}: "
            f"{count} matching test files"
        )

    # ------------------------------------------------------------------
    # Formal consistency checks
    # ------------------------------------------------------------------

    clause_ids = [
        clause.identifier
        for clause in clauses
    ]

    test_ids = [
        test.identifier
        for test in test_obligations
    ]

    consistency = {
        "all_clause_ids_unique": (
            len(clause_ids)
            == len(set(clause_ids))
        ),
        "all_test_ids_unique": (
            len(test_ids)
            == len(set(test_ids))
        ),
        "all_clause_anchors_nonempty": all(
            clause.existing_anchor
            for clause in clauses
        ),
        "all_test_scenarios_nonempty": all(
            test.scenario
            for test in test_obligations
        ),
        "all_failure_states_fail_closed_or_reject": all(
            (
                "DENY" in behavior
                or "REJECT" in behavior
                or "FAIL CLOSED" in behavior
                or "UNVERIFIED" in behavior
            )
            for _description, behavior
            in failure_states.values()
        ),
        "security_chain_anchors_present": all(
            anchor_presence.get(category, False)
            for category in (
                "authority",
                "capability",
                "task",
                "execution",
                "sandbox",
                "process_boundary",
            )
        ),
        "provenance_anchor_present": (
            anchor_presence["provenance"]
        ),
    }

    print()
    print("=" * 100)
    print("SPECIFICATION CONSISTENCY")
    print("=" * 100)

    for name, value in consistency.items():
        print(
            f"{name:48s}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    specification_ready = all(
        consistency.values()
    )

    # ------------------------------------------------------------------
    # Explicit implementation boundary
    # ------------------------------------------------------------------

    implementation_boundary = {
        "new_contract_layer": [
            "Agent identity binding contract",
            "Agent-to-task binding contract",
            "Delegated-authority context binding",
            "Capability context binding",
            "ExecutionAdmission reference/binding",
            "Lifecycle binding",
            "Fail-closed binding validator",
            "Audit/provenance binding",
        ],
        "reuse_without_redesign": [
            "AegisAuthorizationService",
            "AuthorizationGuard",
            "ReplayGuard",
            "CapabilityGateway",
            "ExecutionAdmission",
            "SecureExecutor",
            "SandboxPolicyEvaluator",
            "ChildLauncher",
            "LaunchHandoff",
            "Existing PIAE/runtime lifecycle",
        ],
        "explicitly_forbidden": [
            "Independent authorization",
            "Authority creation",
            "Capability expansion",
            "Alternate execution admission",
            "Direct privileged execution",
            "Second sandbox",
            "Process-boundary bypass",
            "LHICF replacement",
            "Host privilege layer",
        ],
    }

    print()
    print("=" * 100)
    print("IMPLEMENTATION BOUNDARY")
    print("=" * 100)

    for category, values in implementation_boundary.items():
        print()
        print(category)

        for value in values:
            print(
                f"  - {value}"
            )

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    if specification_ready:
        decision = (
            "PB_DOC_005_FORMAL_CONTRACT_SPECIFICATION_READY"
        )
    else:
        decision = (
            "PB_DOC_005_FORMAL_CONTRACT_SPECIFICATION_REQUIRES_REVIEW"
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
        "STATIC FORMAL CONTRACT SPECIFICATION"
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
        "runtime_symbols": len(symbols),
        "project_test_files": len(tests),
        "parse_failures": parse_failures,
        "anchor_presence": anchor_presence,
        "contract_clause_count": len(clauses),
        "failure_state_count": len(
            failure_states
        ),
        "test_obligation_count": len(
            test_obligations
        ),
        "test_surface_counts": test_surface_counts,
        "consistency": consistency,
        "contract_clauses": [
            {
                "id": clause.identifier,
                "category": clause.category,
                "statement": clause.statement,
                "required_state": clause.required_state,
                "failure_behavior": clause.failure_behavior,
                "existing_anchor": list(
                    clause.existing_anchor
                ),
            }
            for clause in clauses
        ],
        "failure_states": {
            key: {
                "description": value[0],
                "behavior": value[1],
            }
            for key, value in failure_states.items()
        },
        "test_obligations": [
            {
                "id": test.identifier,
                "category": test.category,
                "scenario": test.scenario,
                "expected_result": test.expected_result,
                "security_property": test.security_property,
            }
            for test in test_obligations
        ],
        "implementation_boundary": implementation_boundary,
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

    return 0 if specification_ready else 4


if __name__ == "__main__":
    raise SystemExit(main())

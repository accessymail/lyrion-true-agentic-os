#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005..008 Contract Ownership Mapper

READ-ONLY ARCHITECTURE / ENGINEERING REVIEW.

Purpose
-------
Establish ownership of existing implementation contracts and responsibilities
against the approved Phase-B conceptual boundaries:

    PB-DOC-005 Agent Harness
    PB-DOC-006 Host Harness
    PB-DOC-007 Universal Computer
    PB-DOC-008 Application Harness
    LHICF

The mapper answers:

    1. Which existing runtime contracts represent each responsibility?
    2. Which PB-DOC responsibility owns each implementation surface?
    3. Which surfaces are shared/overlapping?
    4. Which responsibilities have no confirmed implementation owner?
    5. Does the existing host/enforcement surface provide enough evidence
       to treat LHICF as a boundary over existing capabilities rather than
       a duplicate implementation?
    6. Which areas are safe candidates for a future bounded implementation
       review?

This tool DOES NOT implement anything.

Safety:
    - read-only
    - AST/static analysis only
    - no source/test/docs mutation
    - no Git mutation
    - no credentials/secrets
    - no external network
    - no privileged operations
    - no G46.5/G47 reconstruction
    - no R097 modification
    - no production certification claim

Evidence classification:
    STATIC CONTRACT OWNERSHIP REVIEW ONLY
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
TEST_ROOT = REPO_ROOT / "tests"

ALLOWED_AUDIT_UNTRACKED = {
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "trace_pb_doc_001_008_call_chain.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
    "trace_pb_doc_001_008_execution_flow.py",
    "map_pb_doc_005_008_architecture_representation.py",
    "map_pb_doc_005_008_contract_responsibilities.py",
    "map_pb_doc_005_008_contract_ownership.py",
}


@dataclass(frozen=True)
class Symbol:
    qualified: str
    short: str
    module: str
    kind: str
    file: str
    line: int
    bases: tuple[str, ...] = ()


@dataclass
class ModuleModel:
    module: str
    path: Path
    tree: ast.Module
    symbols: list[Symbol] = field(default_factory=list)


@dataclass
class Responsibility:
    concept: str
    name: str
    terms: tuple[str, ...]
    boundary_terms: tuple[str, ...]


@dataclass
class Ownership:
    responsibility: Responsibility
    symbols: list[Symbol]
    tests: list[str]
    modules: list[str]

    @property
    def runtime_count(self) -> int:
        return len(self.symbols)

    @property
    def test_count(self) -> int:
        return len(self.tests)


# ---------------------------------------------------------------------------
# Canonical responsibility ownership vocabulary
# ---------------------------------------------------------------------------

RESPONSIBILITIES: tuple[Responsibility, ...] = (
    # PB-DOC-005 ------------------------------------------------------------
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "agent_identity",
        (
            "AgentIdentity",
            "AgentContext",
            "Principal",
            "ApplicationPrincipalContext",
        ),
        ("agent", "identity", "principal"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "agent_lifecycle",
        (
            "Lifecycle",
            "RuntimeState",
            "RuntimeController",
            "TaskState",
        ),
        ("agent", "lifecycle", "runtime"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "task_binding",
        (
            "TaskBinding",
            "TaskContext",
            "TaskManager",
            "TaskExecution",
        ),
        ("agent", "task", "binding"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "authority_binding",
        (
            "Authority",
            "Authorization",
            "AuthorizationGuard",
            "AegisAuthorizationService",
        ),
        ("agent", "authority", "authorization"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "capability_binding",
        (
            "Capability",
            "CapabilityRequest",
            "CapabilityGateway",
            "CapabilityOperation",
        ),
        ("agent", "capability"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "resource_control",
        (
            "ResourceLimits",
            "RuntimeBudget",
            "Budget",
        ),
        ("agent", "resource", "budget"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "runtime_isolation",
        (
            "Sandbox",
            "SandboxConfig",
            "SandboxPolicy",
            "ProcessBoundary",
        ),
        ("agent", "sandbox", "isolation"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "audit_provenance",
        (
            "Audit",
            "Evidence",
            "Provenance",
            "ExecutionAudit",
        ),
        ("agent", "audit", "provenance"),
    ),
    Responsibility(
        "PB-DOC-005 AgentHarness",
        "recovery_revalidation",
        (
            "Recovery",
            "Checkpoint",
            "Retry",
            "Reentry",
        ),
        ("agent", "recovery", "revalidation"),
    ),

    # PB-DOC-006 ------------------------------------------------------------
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_context",
        (
            "HostContext",
            "HostIdentity",
            "HostState",
            "EnvironmentPlan",
            "BackendCapabilities",
        ),
        ("host", "context", "environment"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_discovery",
        (
            "HostCapabilityDetector",
            "HostCapabilityProvider",
            "CapabilitySnapshot",
            "LinuxHostCapabilityDetector",
            "LinuxHostCapabilityProvider",
        ),
        ("host", "discovery", "capability"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_negotiation",
        (
            "HostNegotiation",
            "CapabilityNegotiation",
            "NegotiationEngine",
        ),
        ("host", "negotiation"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_policy",
        (
            "HostPolicy",
            "HostPolicyRegistry",
            "PolicyRegistry",
        ),
        ("host", "policy"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "filesystem",
        (
            "Filesystem",
            "FilesystemIsolation",
            "Landlock",
        ),
        ("host", "filesystem"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "process",
        (
            "Process",
            "ProcessBoundary",
            "ProcessRunner",
            "Supervisor",
            "ChildContext",
        ),
        ("host", "process"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "service",
        (
            "Service",
            "ServiceManager",
            "Systemd",
        ),
        ("host", "service"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "network",
        (
            "Network",
            "NetworkPlan",
        ),
        ("host", "network"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "application_host",
        (
            "ApplicationContext",
            "ApplicationRuntime",
            "EnforcementApplication",
        ),
        ("host", "application"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_adapters",
        (
            "HostAdapter",
            "PrimitiveAdapter",
            "AdapterRegistry",
        ),
        ("host", "adapter"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_enforcement",
        (
            "Enforcement",
            "AppArmor",
            "Cgroup",
            "Seccomp",
            "Namespace",
            "NoNewPrivs",
        ),
        ("host", "enforcement", "security"),
    ),
    Responsibility(
        "PB-DOC-006 HostHarness",
        "host_verification",
        (
            "Qualification",
            "EvidenceProvenance",
            "Freshness",
            "PlanIntegrity",
            "SnapshotDiff",
        ),
        ("host", "verification", "provenance"),
    ),

    # PB-DOC-007 ------------------------------------------------------------
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "operation_abstraction",
        (
            "CapabilityOperation",
            "ExecutionRequest",
            "ExecutionResult",
        ),
        ("universal", "operation", "execution"),
    ),
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "environment_mapping",
        (
            "EnvironmentPlan",
            "BackendCapabilities",
            "ExecutionBackend",
        ),
        ("universal", "environment", "backend"),
    ),
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "adapter_mapping",
        (
            "PrimitiveAdapter",
            "PrimitiveAdapterRegistry",
            "AdapterRegistry",
        ),
        ("universal", "adapter", "mapping"),
    ),
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "capability_discovery",
        (
            "CapabilityDetector",
            "CapabilityProvider",
            "CapabilitySnapshot",
        ),
        ("universal", "capability", "discovery"),
    ),
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "execution_admission",
        (
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
            "CapabilityGateway",
        ),
        ("universal", "admission", "authorization"),
    ),
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "secure_execution",
        (
            "SecureExecutor",
            "ExecutionValidator",
            "ExecutionPolicy",
        ),
        ("universal", "secure", "execution"),
    ),
    Responsibility(
        "PB-DOC-007 UniversalComputer",
        "verification",
        (
            "Verification",
            "Evidence",
            "Provenance",
        ),
        ("universal", "verification", "provenance"),
    ),

    # PB-DOC-008 ------------------------------------------------------------
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_identity",
        (
            "ApplicationIdentity",
            "ApplicationPrincipalContext",
            "ApplicationContext",
        ),
        ("application", "identity", "context"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_state",
        (
            "ApplicationState",
            "ApplicationSessionContext",
            "ApplicationCorrelationContext",
            "RuntimeState",
        ),
        ("application", "state", "runtime"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_discovery",
        (
            "ApplicationDiscovery",
            "ApplicationRegistry",
            "ApplicationRuntime",
        ),
        ("application", "discovery"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_capability",
        (
            "ApplicationCapability",
            "CapabilityOperation",
            "CapabilityRequest",
        ),
        ("application", "capability"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_adapter",
        (
            "ApplicationAdapter",
            "EnforcementApplication",
            "EnforcementApplicationContext",
        ),
        ("application", "adapter", "mapping"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_execution",
        (
            "ExecutionAdmission",
            "SecureExecutor",
            "ExecutionResult",
        ),
        ("application", "execution"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_security",
        (
            "Authorization",
            "AegisAuthorizationService",
            "AuthorizationGuard",
            "Sandbox",
        ),
        ("application", "security", "authorization"),
    ),
    Responsibility(
        "PB-DOC-008 ApplicationHarness",
        "application_verification",
        (
            "EnforcementEvidence",
            "Verification",
            "Evidence",
            "Provenance",
        ),
        ("application", "verification", "provenance"),
    ),

    # LHICF -----------------------------------------------------------------
    Responsibility(
        "LHICF",
        "host_integration_boundary",
        (
            "LHICF",
            "HostIntegrationControlFabric",
            "HostIntegration",
        ),
        ("lhicf", "host", "integration"),
    ),
    Responsibility(
        "LHICF",
        "host_adapter_boundary",
        (
            "HostAdapter",
            "PrimitiveAdapter",
            "AdapterRegistry",
            "PrimitiveAdapterRegistry",
        ),
        ("lhicf", "adapter", "host"),
    ),
    Responsibility(
        "LHICF",
        "host_operation_boundary",
        (
            "HostOperation",
            "Filesystem",
            "Process",
            "Service",
            "Network",
            "Application",
            "Desktop",
            "Device",
            "Clipboard",
        ),
        ("lhicf", "operation", "host"),
    ),
    Responsibility(
        "LHICF",
        "execution_enforcement_boundary",
        (
            "ExecutionAdmission",
            "SecureExecutor",
            "Sandbox",
            "CapabilityGateway",
        ),
        ("lhicf", "execution", "enforcement"),
    ),
    Responsibility(
        "LHICF",
        "host_provenance_boundary",
        (
            "Evidence",
            "Provenance",
            "EnforcementEvidence",
            "Audit",
        ),
        ("lhicf", "provenance", "verification"),
    ),
)


# ---------------------------------------------------------------------------
# Git / repository guard
# ---------------------------------------------------------------------------

def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def repo_guard() -> tuple[bool, list[str]]:
    failures: list[str] = []

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    branch = run_git("branch", "--show-current")
    status = run_git("status", "--short", "--untracked-files=all")

    if head != origin:
        failures.append("HEAD != origin/main")

    if branch != "main":
        failures.append(f"unexpected branch: {branch}")

    for line in status.splitlines():
        path = line[3:].strip()

        if (
            path.startswith("tools/phase_b/audit/")
            and Path(path).name in ALLOWED_AUDIT_UNTRACKED
        ):
            continue

        failures.append(f"unexpected worktree change: {line}")

    return not failures, failures


# ---------------------------------------------------------------------------
# Source inventory
# ---------------------------------------------------------------------------

def source_files() -> list[Path]:
    return sorted(
        path
        for path in SRC_ROOT.rglob("*.py")
        if path.is_file()
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
            for part in path.parts
        )
    )


def test_files() -> list[Path]:
    if not TEST_ROOT.exists():
        return []

    return sorted(
        path
        for path in TEST_ROOT.rglob("*.py")
        if path.is_file()
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
            for part in path.parts
        )
    )


def module_name(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT)
    parts = list(relative.parts)

    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(parts)


# ---------------------------------------------------------------------------
# AST model
# ---------------------------------------------------------------------------

def dotted(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return f"{left}.{node.attr}" if left else node.attr

    return None


class Visitor(ast.NodeVisitor):
    def __init__(self, module: str, path: Path) -> None:
        self.module = module
        self.path = path
        self.tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        self.symbols: list[Symbol] = []
        self.class_stack: list[str] = []
        self.visit(self.tree)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = ".".join(
            [self.module, *self.class_stack, node.name]
        )

        bases = tuple(
            base
            for base in (
                dotted(item)
                for item in node.bases
            )
            if base
        )

        self.symbols.append(
            Symbol(
                qualified=qualified,
                short=node.name,
                module=self.module,
                kind="class",
                file=str(self.path.relative_to(REPO_ROOT)),
                line=node.lineno,
                bases=bases,
            )
        )

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def _function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        qualified = ".".join(
            [self.module, *self.class_stack, node.name]
        )

        self.symbols.append(
            Symbol(
                qualified=qualified,
                short=node.name,
                module=self.module,
                kind="function",
                file=str(self.path.relative_to(REPO_ROOT)),
                line=node.lineno,
            )
        )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._function(node)


def parse_sources(
    paths: list[Path],
) -> tuple[list[ModuleModel], list[str]]:
    models: list[ModuleModel] = []
    failures: list[str] = []

    for path in paths:
        try:
            visitor = Visitor(module_name(path), path)

            models.append(
                ModuleModel(
                    module=visitor.module,
                    path=path,
                    tree=visitor.tree,
                    symbols=visitor.symbols,
                )
            )
        except Exception as exc:
            failures.append(f"{path}: {exc}")

    return models, failures


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def symbol_matches(symbol: Symbol, term: str) -> bool:
    return term.lower() in (
        f"{symbol.qualified} {symbol.short}"
    ).lower()


def matching_symbols(
    models: list[ModuleModel],
    terms: tuple[str, ...],
) -> list[Symbol]:
    found: dict[str, Symbol] = {}

    for model in models:
        for symbol in model.symbols:
            if any(
                symbol_matches(symbol, term)
                for term in terms
            ):
                found[symbol.qualified] = symbol

    return sorted(
        found.values(),
        key=lambda symbol: (
            symbol.file,
            symbol.line,
            symbol.qualified,
        ),
    )


def file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").lower()
    except Exception:
        return ""


def matching_tests(
    tests: list[Path],
    terms: tuple[str, ...],
) -> list[str]:
    lowered = tuple(term.lower() for term in terms)
    found: list[str] = []

    for path in tests:
        text = file_text(path)

        if any(term in text for term in lowered):
            found.append(
                str(path.relative_to(REPO_ROOT))
            )

    return sorted(found)


# ---------------------------------------------------------------------------
# Ownership analysis
# ---------------------------------------------------------------------------

def build_ownership(
    models: list[ModuleModel],
    tests: list[Path],
) -> list[Ownership]:
    ownership: list[Ownership] = []

    for responsibility in RESPONSIBILITIES:
        symbols = matching_symbols(
            models,
            responsibility.terms,
        )

        tests_found = matching_tests(
            tests,
            responsibility.terms,
        )

        modules = sorted(
            {
                symbol.module
                for symbol in symbols
            }
        )

        ownership.append(
            Ownership(
                responsibility=responsibility,
                symbols=symbols,
                tests=tests_found,
                modules=modules,
            )
        )

    return ownership


def explicit_boundary(
    concept: str,
    models: list[ModuleModel],
) -> bool:
    terms = {
        "PB-DOC-005 AgentHarness": (
            "AgentHarness",
        ),
        "PB-DOC-006 HostHarness": (
            "HostHarness",
        ),
        "PB-DOC-007 UniversalComputer": (
            "UniversalComputer",
        ),
        "PB-DOC-008 ApplicationHarness": (
            "ApplicationHarness",
        ),
        "LHICF": (
            "LHICF",
            "HostIntegrationControlFabric",
        ),
    }[concept]

    return bool(
        matching_symbols(
            models,
            terms,
        )
    )


def ownership_index(
    ownership: list[Ownership],
) -> dict[str, set[str]]:
    """
    qualified symbol -> PB-DOC responsibility owners.
    """
    index: dict[str, set[str]] = defaultdict(set)

    for item in ownership:
        for symbol in item.symbols:
            index[symbol.qualified].add(
                f"{item.responsibility.concept}:"
                f"{item.responsibility.name}"
            )

    return index


def overlap_report(
    index: dict[str, set[str]],
) -> dict[str, list[str]]:
    return {
        symbol: sorted(owners)
        for symbol, owners in index.items()
        if len(owners) > 1
    }


def unique_module_ownership(
    ownership: list[Ownership],
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)

    for item in ownership:
        for module in item.modules:
            result[module].add(
                item.responsibility.concept
            )

    return result


# ---------------------------------------------------------------------------
# Boundary-specific interpretation
# ---------------------------------------------------------------------------

def lhicf_analysis(
    ownership: list[Ownership],
) -> dict:
    lhicf = [
        item
        for item in ownership
        if item.responsibility.concept == "LHICF"
    ]

    direct = next(
        (
            item
            for item in lhicf
            if item.responsibility.name
            == "host_integration_boundary"
        ),
        None,
    )

    adapters = next(
        (
            item
            for item in lhicf
            if item.responsibility.name
            == "host_adapter_boundary"
        ),
        None,
    )

    operations = next(
        (
            item
            for item in lhicf
            if item.responsibility.name
            == "host_operation_boundary"
        ),
        None,
    )

    enforcement = next(
        (
            item
            for item in lhicf
            if item.responsibility.name
            == "execution_enforcement_boundary"
        ),
        None,
    )

    provenance = next(
        (
            item
            for item in lhicf
            if item.responsibility.name
            == "host_provenance_boundary"
        ),
        None,
    )

    return {
        "explicit_lhicf_symbol": bool(
            direct and direct.symbols
        ),
        "adapter_surface": bool(
            adapters and adapters.symbols
        ),
        "operation_surface": bool(
            operations and operations.symbols
        ),
        "enforcement_surface": bool(
            enforcement and enforcement.symbols
        ),
        "provenance_surface": bool(
            provenance and provenance.symbols
        ),
        "adapter_runtime_count": (
            len(adapters.symbols)
            if adapters
            else 0
        ),
        "operation_runtime_count": (
            len(operations.symbols)
            if operations
            else 0
        ),
        "enforcement_runtime_count": (
            len(enforcement.symbols)
            if enforcement
            else 0
        ),
        "provenance_runtime_count": (
            len(provenance.symbols)
            if provenance
            else 0
        ),
    }


def responsibility_status(
    item: Ownership,
) -> str:
    if item.runtime_count and item.test_count:
        return "RUNTIME_AND_TEST"

    if item.runtime_count:
        return "RUNTIME_ONLY"

    if item.test_count:
        return "TEST_ONLY"

    return "NO_EVIDENCE"


def candidate_score(
    item: Ownership,
) -> int:
    score = 0

    if item.runtime_count:
        score += 2

    if item.test_count:
        score += 1

    if item.modules:
        score += 1

    return score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 100)
    print("LYRION PB-DOC-005..008 CONTRACT OWNERSHIP MAPPER")
    print("=" * 100)

    clean, failures = repo_guard()

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    branch = run_git("branch", "--show-current")

    print(f"Repository : {REPO_ROOT}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")
    print(f"Repo Guard : {'PASS' if clean else 'FAIL'}")

    if not clean:
        for failure in failures:
            print(f"  FAIL: {failure}")

        print("Decision: BASELINE_NOT_CLEAN")
        return 2

    paths = source_files()
    tests = test_files()

    models, parse_failures = parse_sources(paths)

    symbol_count = sum(
        len(model.symbols)
        for model in models
    )

    print()
    print("-" * 100)
    print("SOURCE INVENTORY")
    print("-" * 100)
    print(f"Runtime Python files : {len(paths)}")
    print(f"Runtime modules      : {len(models)}")
    print(f"Runtime symbols      : {symbol_count}")
    print(f"Project test files   : {len(tests)}")
    print(f"AST failures         : {len(parse_failures)}")

    if parse_failures:
        for failure in parse_failures[:20]:
            print(f"  PARSE FAIL: {failure}")

    ownership = build_ownership(
        models,
        tests,
    )

    print()
    print("=" * 100)
    print("RESPONSIBILITY OWNERSHIP")
    print("=" * 100)

    concept_summary: dict[str, dict] = {}

    concepts = sorted(
        {
            item.responsibility.concept
            for item in ownership
        }
    )

    for concept in concepts:
        items = [
            item
            for item in ownership
            if item.responsibility.concept == concept
        ]

        print()
        print("-" * 100)
        print(concept)
        print("-" * 100)

        explicit = explicit_boundary(
            concept,
            models,
        )

        for item in items:
            status = responsibility_status(item)

            print(
                f"{item.responsibility.name:34s} "
                f"status={status:18s} "
                f"runtime={item.runtime_count:3d} "
                f"tests={item.test_count:3d} "
                f"modules={len(item.modules):3d}"
            )

            if item.symbols:
                for symbol in item.symbols[:5]:
                    print(
                        f"      - {symbol.qualified} "
                        f"[{symbol.kind}] "
                        f"{symbol.file}:{symbol.line}"
                    )

        runtime_responsibilities = sum(
            bool(item.symbols)
            for item in items
        )

        tested_responsibilities = sum(
            bool(item.tests)
            for item in items
        )

        if explicit:
            architectural_state = "EXPLICIT_BOUNDARY"
        elif (
            runtime_responsibilities >= 3
            and tested_responsibilities >= 3
        ):
            architectural_state = (
                "IMPLICIT_BOUNDARY_CANDIDATE"
            )
        elif runtime_responsibilities:
            architectural_state = (
                "PARTIAL_REPRESENTATION"
            )
        else:
            architectural_state = (
                "NO_CONFIRMED_RUNTIME_REPRESENTATION"
            )

        concept_summary[concept] = {
            "explicit_boundary": explicit,
            "architectural_state": architectural_state,
            "runtime_responsibilities": runtime_responsibilities,
            "tested_responsibilities": tested_responsibilities,
            "total_runtime_symbols": sum(
                item.runtime_count
                for item in items
            ),
            "total_tests": sum(
                item.test_count
                for item in items
            ),
        }

        print()
        print(f"BOUNDARY STATE: {architectural_state}")

    # ------------------------------------------------------------------
    # Shared symbol ownership
    # ------------------------------------------------------------------

    index = ownership_index(
        ownership,
    )

    overlaps = overlap_report(
        index,
    )

    print()
    print("=" * 100)
    print("CROSS-BOUNDARY SYMBOL OVERLAP")
    print("=" * 100)

    print(
        f"Shared qualified symbols: {len(overlaps)}"
    )

    for symbol, owners in list(
        sorted(overlaps.items())
    )[:100]:
        print()
        print(symbol)
        for owner in owners:
            print(f"  owner: {owner}")

    # ------------------------------------------------------------------
    # Module ownership
    # ------------------------------------------------------------------

    modules = unique_module_ownership(
        ownership,
    )

    shared_modules = {
        module: sorted(concepts)
        for module, concepts in modules.items()
        if len(concepts) > 1
    }

    print()
    print("=" * 100)
    print("CROSS-BOUNDARY MODULE OVERLAP")
    print("=" * 100)

    print(
        f"Shared modules: {len(shared_modules)}"
    )

    for module, concepts_for_module in list(
        sorted(shared_modules.items())
    )[:100]:
        print(
            f"{module}: "
            + ", ".join(concepts_for_module)
        )

    # ------------------------------------------------------------------
    # Unowned / thin responsibilities
    # ------------------------------------------------------------------

    thin: list[str] = []
    unowned: list[str] = []

    for item in ownership:
        if not item.symbols:
            unowned.append(
                f"{item.responsibility.concept}:"
                f"{item.responsibility.name}"
            )
        elif not item.tests:
            thin.append(
                f"{item.responsibility.concept}:"
                f"{item.responsibility.name}"
            )

    print()
    print("=" * 100)
    print("OWNERSHIP GAPS")
    print("=" * 100)

    print(f"No runtime owner      : {len(unowned)}")
    for value in unowned:
        print(f"  - {value}")

    print()
    print(
        "Runtime owner without matching test surface:"
        f" {len(thin)}"
    )

    for value in thin:
        print(f"  - {value}")

    # ------------------------------------------------------------------
    # LHICF
    # ------------------------------------------------------------------

    lhicf = lhicf_analysis(
        ownership,
    )

    print()
    print("=" * 100)
    print("LHICF OWNERSHIP RECONCILIATION")
    print("=" * 100)

    for key, value in lhicf.items():
        print(f"{key:32s}: {value}")

    if lhicf["explicit_lhicf_symbol"]:
        lhicf_state = "EXPLICIT_LHICF_BOUNDARY"
    elif all(
        (
            lhicf["adapter_surface"],
            lhicf["operation_surface"],
            lhicf["enforcement_surface"],
            lhicf["provenance_surface"],
        )
    ):
        lhicf_state = (
            "IMPLICIT_HOST_INTEGRATION_BOUNDARY_CANDIDATE"
        )
    elif any(
        (
            lhicf["adapter_surface"],
            lhicf["operation_surface"],
            lhicf["enforcement_surface"],
            lhicf["provenance_surface"],
        )
    ):
        lhicf_state = (
            "PARTIAL_HOST_INTEGRATION_REPRESENTATION"
        )
    else:
        lhicf_state = (
            "NO_CONFIRMED_LHICF_REPRESENTATION"
        )

    print()
    print(f"LHICF STATE: {lhicf_state}")

    # ------------------------------------------------------------------
    # Protected architecture order
    # ------------------------------------------------------------------

    protected_terms = {
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
            "Sandbox",
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
        ),
        "HostIntegration": (
            "PrimitiveAdapter",
            "LinuxHostCapabilityDetector",
            "LinuxHostCapabilityProvider",
            "EnforcementApplication",
        ),
    }

    protected_presence = {}

    print()
    print("=" * 100)
    print("PROTECTED SECURITY / EXECUTION BOUNDARY INVENTORY")
    print("=" * 100)

    for boundary, terms in protected_terms.items():
        symbols = matching_symbols(
            models,
            terms,
        )

        protected_presence[boundary] = len(symbols)

        print(
            f"{boundary:24s}: "
            f"{len(symbols):3d} symbol(s)"
        )

        for symbol in symbols[:8]:
            print(
                f"      - {symbol.qualified}"
            )

    # ------------------------------------------------------------------
    # Bounded-slice candidates
    # ------------------------------------------------------------------

    candidate_items = sorted(
        ownership,
        key=lambda item: (
            -candidate_score(item),
            item.responsibility.concept,
            item.responsibility.name,
        ),
    )

    candidates = [
        {
            "concept": item.responsibility.concept,
            "responsibility": item.responsibility.name,
            "runtime_symbols": item.runtime_count,
            "tests": item.test_count,
            "score": candidate_score(item),
        }
        for item in candidate_items[:20]
    ]

    print()
    print("=" * 100)
    print("POTENTIAL BOUNDED-SLICE SURFACES")
    print("=" * 100)

    print(
        "These are evidence-rich responsibility surfaces only."
    )
    print(
        "They are NOT implementation authorization or selection."
    )

    for candidate in candidates:
        print(
            f"{candidate['concept']:28s} "
            f"{candidate['responsibility']:32s} "
            f"runtime={candidate['runtime_symbols']:3d} "
            f"tests={candidate['tests']:3d} "
            f"score={candidate['score']}"
        )

    # ------------------------------------------------------------------
    # Final interpretation
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ARCHITECTURAL INTERPRETATION")
    print("=" * 100)

    print(
        "1. Existing implementation surfaces are mapped to documented "
        "responsibilities without renaming or restructuring runtime code."
    )

    print(
        "2. Shared symbols/modules indicate responsibility overlap and "
        "must be resolved by contract ownership before introducing new "
        "architectural boundaries."
    )

    print(
        "3. An implicit boundary candidate is NOT equivalent to an "
        "approved explicit implementation boundary."
    )

    print(
        "4. LHICF must not duplicate existing host enforcement, adapter, "
        "qualification, provenance, or execution-control mechanisms."
    )

    print(
        "5. Any explicit LHICF boundary introduced later must remain "
        "downstream of authorization/admission/security controls and "
        "must not create an alternate privileged execution path."
    )

    print(
        "6. PB-DOC-005..008 implementation selection requires contract "
        "ownership reconciliation and bounded validation planning."
    )

    print()
    print(
        "NO IMPLEMENTATION SLICE IS AUTHORIZED BY THIS TOOL."
    )

    # ------------------------------------------------------------------
    # Evidence boundary
    # ------------------------------------------------------------------

    print()
    print("-" * 100)
    print("EVIDENCE BOUNDARY")
    print("-" * 100)

    print(
        "Analysis type                 : "
        "STATIC CONTRACT OWNERSHIP REVIEW"
    )
    print("Executed validation           : NOT ASSESSED")
    print("Acceptance evidence           : NOT ASSESSED")
    print("Production implementation     : BLOCKED")
    print("Production certification      : NOT CLAIMED")
    print("G46.5 reconstruction          : NOT PERFORMED")
    print("G47 reconstruction            : NOT PERFORMED")
    print("R097 modification             : NONE")
    print("Source/test/document mutation : NONE")

    # ------------------------------------------------------------------
    # Machine summary
    # ------------------------------------------------------------------

    summary = {
        "decision": (
            "PB_DOC_005_008_CONTRACT_OWNERSHIP_MAPPING_COMPLETE"
        ),
        "head": head,
        "origin_main": origin,
        "runtime_python_files": len(paths),
        "runtime_modules": len(models),
        "runtime_symbols": symbol_count,
        "project_test_files": len(tests),
        "parse_failures": len(parse_failures),
        "concepts": concept_summary,
        "shared_qualified_symbols": len(overlaps),
        "shared_modules": len(shared_modules),
        "unowned_responsibilities": unowned,
        "runtime_without_tests": thin,
        "lhicf": {
            **lhicf,
            "state": lhicf_state,
        },
        "protected_boundary_presence": protected_presence,
        "candidate_surfaces": candidates,
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
    print(
        "Decision: "
        "PB_DOC_005_008_CONTRACT_OWNERSHIP_MAPPING_COMPLETE"
    )

    print()
    print("=" * 100)
    print("RUNTIME HASH SAMPLE")
    print("=" * 100)

    for path in paths[:12]:
        digest = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        print(
            f"{path.relative_to(REPO_ROOT)} "
            f"{digest}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

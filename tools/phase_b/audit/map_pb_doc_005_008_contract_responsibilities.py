#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005..008 Contract Responsibility Mapper

READ-ONLY ENGINEERING REVIEW.

Purpose
-------
Determine whether existing runtime contracts and implementations already
represent the documented responsibilities of:

    PB-DOC-005 Agent Harness
    PB-DOC-006 Host Harness
    PB-DOC-007 Universal Computer
    PB-DOC-008 Application Harness
    LHICF

This is a contract/responsibility analysis, NOT an implementation task.

The mapper intentionally distinguishes:

    1. Concept/name presence
    2. Responsibility presence
    3. Contract representation
    4. Dependency/integration representation
    5. Security-boundary preservation
    6. Explicit architectural boundary
    7. Evidence sufficient for implementation selection

It MUST NOT infer that a concept is missing merely because the exact
architectural class/module name is absent.

Safety
------
This tool:
    - reads repository source/tests/docs only
    - performs AST/static analysis only
    - does not execute project runtime code
    - does not modify src/
    - does not modify tests/
    - does not modify docs/manifests
    - does not access credentials/secrets
    - does not access external networks
    - does not perform privileged operations
    - does not modify Git history
    - does not reconstruct G46.5/G47
    - does not alter R097
    - does not claim production certification

Evidence classification:
    STATIC CONTRACT RESPONSIBILITY REVIEW ONLY
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
SELF = Path(__file__).resolve()

ALLOWED_AUDIT_UNTRACKED = {
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "trace_pb_doc_001_008_call_chain.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
    "trace_pb_doc_001_008_execution_flow.py",
    "map_pb_doc_005_008_architecture_representation.py",
    "map_pb_doc_005_008_contract_responsibilities.py",
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
    imports: dict[str, str] = field(default_factory=dict)
    symbols: list[Symbol] = field(default_factory=list)


@dataclass
class ResponsibilityEvidence:
    responsibility: str
    contract_terms: tuple[str, ...]
    runtime_symbols: list[Symbol] = field(default_factory=list)
    contract_symbols: list[Symbol] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    security_signals: list[str] = field(default_factory=list)

    @property
    def score(self) -> int:
        score = 0

        if self.runtime_symbols:
            score += 1

        if self.contract_symbols:
            score += 2

        if self.tests:
            score += 1

        if self.security_signals:
            score += 1

        return score


# ---------------------------------------------------------------------------
# Responsibility contract definitions
# ---------------------------------------------------------------------------

RESPONSIBILITIES = {
    "PB-DOC-005 AgentHarness": {
        "agent_identity": (
            "AgentIdentity",
            "AgentContext",
            "Principal",
            "ApplicationPrincipalContext",
        ),
        "agent_lifecycle": (
            "Lifecycle",
            "RuntimeState",
            "RuntimeController",
            "TaskState",
        ),
        "task_binding": (
            "TaskBinding",
            "Task",
            "TaskContext",
            "TaskManager",
            "TaskExecution",
        ),
        "authority_binding": (
            "Authority",
            "Authorization",
            "Delegated",
            "AuthorizationGuard",
            "AegisAuthorizationService",
        ),
        "capability_binding": (
            "Capability",
            "CapabilityRequest",
            "CapabilityGateway",
            "CapabilityOperation",
        ),
        "resource_control": (
            "ResourceLimits",
            "RuntimeBudget",
            "Budget",
            "Resource",
        ),
        "runtime_isolation": (
            "Sandbox",
            "SandboxConfig",
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
            "ProcessBoundary",
        ),
        "audit_provenance": (
            "Audit",
            "Evidence",
            "Provenance",
            "ExecutionAudit",
        ),
        "recovery_revalidation": (
            "Recovery",
            "Checkpoint",
            "Retry",
            "Reentry",
        ),
    },
    "PB-DOC-006 HostHarness": {
        "host_context": (
            "HostContext",
            "HostIdentity",
            "HostState",
            "EnvironmentPlan",
            "BackendCapabilities",
        ),
        "host_discovery": (
            "HostCapabilityDetector",
            "HostCapabilityProvider",
            "CapabilitySnapshot",
            "LinuxHostCapabilityDetector",
            "LinuxHostCapabilityProvider",
        ),
        "host_negotiation": (
            "Negotiation",
            "HostNegotiation",
            "CapabilityNegotiation",
            "NegotiationEngine",
        ),
        "host_policy": (
            "HostPolicy",
            "HostPolicyRegistry",
            "PolicyRegistry",
        ),
        "filesystem": (
            "Filesystem",
            "FilesystemIsolation",
            "Landlock",
        ),
        "process": (
            "Process",
            "ProcessBoundary",
            "ProcessRunner",
            "Supervisor",
            "ChildContext",
        ),
        "service": (
            "Service",
            "Systemd",
            "ServiceManager",
        ),
        "network": (
            "Network",
            "NetworkPlan",
            "FilesystemIsolationAdapter",
        ),
        "application_host": (
            "Application",
            "ApplicationContext",
            "ApplicationRuntime",
            "EnforcementApplication",
        ),
        "desktop_device": (
            "Desktop",
            "Device",
            "Clipboard",
            "Notification",
        ),
        "host_adapters": (
            "HostAdapter",
            "PrimitiveAdapter",
            "Adapter",
            "AdapterRegistry",
        ),
        "host_enforcement": (
            "Enforcement",
            "AppArmor",
            "Cgroup",
            "Seccomp",
            "Namespace",
            "NoNewPrivs",
        ),
        "host_verification": (
            "Qualification",
            "EvidenceProvenance",
            "Freshness",
            "PlanIntegrity",
            "SnapshotDiff",
        ),
    },
    "PB-DOC-007 UniversalComputer": {
        "operation_abstraction": (
            "CapabilityOperation",
            "Operation",
            "ExecutionRequest",
            "ExecutionResult",
        ),
        "environment_mapping": (
            "EnvironmentPlan",
            "BackendCapabilities",
            "ExecutionBackend",
        ),
        "adapter_mapping": (
            "PrimitiveAdapter",
            "PrimitiveAdapterRegistry",
            "AdapterRegistry",
            "Adapter",
        ),
        "capability_discovery": (
            "CapabilityDetector",
            "CapabilityProvider",
            "CapabilitySnapshot",
        ),
        "execution_admission": (
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
            "CapabilityGateway",
        ),
        "secure_execution": (
            "SecureExecutor",
            "ExecutionValidator",
            "ExecutionPolicy",
        ),
        "verification": (
            "Verification",
            "Evidence",
            "Provenance",
            "Audit",
        ),
    },
    "PB-DOC-008 ApplicationHarness": {
        "application_identity": (
            "ApplicationIdentity",
            "ApplicationPrincipalContext",
            "ApplicationContext",
        ),
        "application_state": (
            "ApplicationState",
            "ApplicationSessionContext",
            "ApplicationCorrelationContext",
            "RuntimeState",
        ),
        "application_discovery": (
            "ApplicationDiscovery",
            "ApplicationRegistry",
            "ApplicationRuntime",
        ),
        "application_capability": (
            "ApplicationCapability",
            "CapabilityOperation",
            "CapabilityRequest",
        ),
        "application_adapter": (
            "ApplicationAdapter",
            "EnforcementApplication",
            "EnforcementApplicationContext",
            "PrimitiveAdapter",
        ),
        "application_execution": (
            "ExecutionAdmission",
            "SecureExecutor",
            "ExecutionResult",
        ),
        "application_security": (
            "Authorization",
            "AegisAuthorizationService",
            "AuthorizationGuard",
            "Sandbox",
        ),
        "application_verification": (
            "EnforcementEvidence",
            "Verification",
            "Evidence",
            "Provenance",
        ),
    },
    "LHICF": {
        "host_integration_boundary": (
            "LHICF",
            "HostIntegrationControlFabric",
            "HostIntegration",
        ),
        "host_adapter_boundary": (
            "HostAdapter",
            "PrimitiveAdapter",
            "AdapterRegistry",
            "PrimitiveAdapterRegistry",
        ),
        "host_operation_boundary": (
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
        "execution_enforcement_boundary": (
            "SecureExecutor",
            "Sandbox",
            "ExecutionAdmission",
            "CapabilityGateway",
        ),
        "host_provenance_boundary": (
            "Evidence",
            "Provenance",
            "EnforcementEvidence",
            "Audit",
        ),
    },
}


SECURITY_TERMS = {
    "authorization": (
        "authorize",
        "authorization",
        "require_authorized",
        "AuthorizationGuard",
        "AegisAuthorizationService",
    ),
    "capability": (
        "CapabilityGateway",
        "CapabilityRequest",
        "CapabilityOperation",
    ),
    "admission": (
        "ExecutionAdmission",
        "require_admission",
        "from_authorization",
    ),
    "sandbox": (
        "SandboxPolicy",
        "SandboxPolicyEvaluator",
        "sandbox",
    ),
    "secure_executor": (
        "SecureExecutor",
        "execute",
    ),
    "host_enforcement": (
        "PrimitiveAdapter",
        "enforcement",
        "AppArmor",
        "Landlock",
        "Cgroup",
        "Seccomp",
        "Namespace",
    ),
    "verification": (
        "evidence",
        "verified",
        "provenance",
        "audit",
    ),
}


# ---------------------------------------------------------------------------
# Git / filesystem safety
# ---------------------------------------------------------------------------

def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


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
# AST analysis
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
        self.imports: dict[str, str] = {}
        self.symbols: list[Symbol] = []
        self.class_stack: list[str] = []

        self.visit(self.tree)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports[alias.asname or alias.name.split(".")[0]] = alias.name

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""

        for alias in node.names:
            self.imports[alias.asname or alias.name] = (
                f"{module}:{alias.name}"
            )

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = ".".join(
            [self.module, *self.class_stack, node.name]
        )

        bases = tuple(
            base
            for base in (
                dotted(value)
                for value in node.bases
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
                    imports=visitor.imports,
                    symbols=visitor.symbols,
                )
            )

        except Exception as exc:
            failures.append(f"{path}: {exc}")

    return models, failures


# ---------------------------------------------------------------------------
# Symbol / text matching
# ---------------------------------------------------------------------------

def symbol_matches(symbol: Symbol, term: str) -> bool:
    return term.lower() in (
        f"{symbol.qualified} {symbol.short}"
    ).lower()


def matching_symbols(
    models: list[ModuleModel],
    terms: tuple[str, ...],
) -> list[Symbol]:
    result: dict[str, Symbol] = {}

    for model in models:
        for symbol in model.symbols:
            if any(
                symbol_matches(symbol, term)
                for term in terms
            ):
                result[symbol.qualified] = symbol

    return sorted(
        result.values(),
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
    result: list[str] = []

    lowered = tuple(term.lower() for term in terms)

    for path in tests:
        text = file_text(path)

        if any(term in text for term in lowered):
            result.append(
                str(path.relative_to(REPO_ROOT))
            )

    return sorted(result)


# ---------------------------------------------------------------------------
# Contract detection
# ---------------------------------------------------------------------------

def is_contract_symbol(symbol: Symbol) -> bool:
    name = symbol.short.lower()

    contract_markers = (
        "contract",
        "request",
        "result",
        "context",
        "state",
        "policy",
        "decision",
        "envelope",
        "plan",
        "snapshot",
        "capabilities",
        "identity",
        "authority",
        "evidence",
    )

    return any(marker in name for marker in contract_markers)


def module_contract_density(
    models: list[ModuleModel],
) -> dict[str, int]:
    density: dict[str, int] = {}

    for model in models:
        density[model.module] = sum(
            1
            for symbol in model.symbols
            if is_contract_symbol(symbol)
        )

    return density


# ---------------------------------------------------------------------------
# Security boundary analysis
# ---------------------------------------------------------------------------

def security_signals_for_symbols(
    symbols: list[Symbol],
    models_by_path: dict[str, ModuleModel],
) -> list[str]:
    signals: set[str] = set()

    for symbol in symbols:
        model = models_by_path.get(symbol.file)

        if model is None:
            continue

        source = file_text(model.path)

        for category, terms in SECURITY_TERMS.items():
            if any(
                term.lower() in source
                for term in terms
            ):
                signals.add(category)

    return sorted(signals)


def boundary_order_signals(
    models: list[ModuleModel],
) -> dict[str, list[str]]:
    """
    Determine whether implementation modules expose names associated with
    the protected order:

        Aegis
        Capability Gateway
        Execution Admission
        Secure Executor
        Sandbox
        Linux enforcement / adapter / host
    """

    order = {
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
        "HostBoundary": (
            "PrimitiveAdapter",
            "LinuxHostCapabilityDetector",
            "LinuxHostCapabilityProvider",
            "EnforcementApplication",
        ),
    }

    result: dict[str, list[str]] = {}

    for boundary, terms in order.items():
        symbols = matching_symbols(
            models,
            terms,
        )

        result[boundary] = [
            symbol.qualified
            for symbol in symbols[:20]
        ]

    return result


# ---------------------------------------------------------------------------
# Responsibility analysis
# ---------------------------------------------------------------------------

def analyze_responsibility(
    responsibility: str,
    terms: tuple[str, ...],
    models: list[ModuleModel],
    tests: list[Path],
    models_by_path: dict[str, ModuleModel],
) -> ResponsibilityEvidence:
    runtime_symbols = matching_symbols(
        models,
        terms,
    )

    contract_symbols = [
        symbol
        for symbol in runtime_symbols
        if is_contract_symbol(symbol)
    ]

    matched_tests = matching_tests(
        tests,
        terms,
    )

    modules = sorted(
        {
            symbol.module
            for symbol in runtime_symbols
        }
    )

    security_signals = security_signals_for_symbols(
        runtime_symbols,
        models_by_path,
    )

    return ResponsibilityEvidence(
        responsibility=responsibility,
        contract_terms=terms,
        runtime_symbols=runtime_symbols,
        contract_symbols=contract_symbols,
        tests=matched_tests,
        modules=modules,
        security_signals=security_signals,
    )


def classification(
    evidence: list[ResponsibilityEvidence],
) -> str:
    if not evidence:
        return "NO_RESPONSIBILITY_EVIDENCE"

    runtime = sum(
        bool(item.runtime_symbols)
        for item in evidence
    )

    contracts = sum(
        bool(item.contract_symbols)
        for item in evidence
    )

    tests = sum(
        bool(item.tests)
        for item in evidence
    )

    if runtime and contracts and tests:
        return "CONTRACT_RUNTIME_TEST_REPRESENTATION"

    if runtime and contracts:
        return "CONTRACT_RUNTIME_REPRESENTATION"

    if runtime and tests:
        return "RUNTIME_TEST_REPRESENTATION"

    if runtime:
        return "RUNTIME_SURFACE_ONLY"

    if contracts:
        return "CONTRACT_SURFACE_ONLY"

    if tests:
        return "TEST_SURFACE_ONLY"

    return "NO_RESPONSIBILITY_EVIDENCE"


def explicit_boundary_status(
    concept: str,
    models: list[ModuleModel],
) -> str:
    explicit_names = {
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
    }

    symbols = matching_symbols(
        models,
        explicit_names.get(concept, ()),
    )

    return (
        "EXPLICIT_BOUNDARY_SYMBOL_PRESENT"
        if symbols
        else "NO_EXPLICIT_BOUNDARY_SYMBOL"
    )


def architectural_classification(
    concept: str,
    evidence: list[ResponsibilityEvidence],
    explicit_status: str,
) -> str:
    represented = sum(
        bool(item.runtime_symbols)
        for item in evidence
    )

    contract_represented = sum(
        bool(item.contract_symbols)
        for item in evidence
    )

    security_represented = sum(
        bool(item.security_signals)
        for item in evidence
    )

    if explicit_status == "EXPLICIT_BOUNDARY_SYMBOL_PRESENT":
        return "EXPLICIT_IMPLEMENTATION_BOUNDARY"

    if (
        represented >= 3
        and contract_represented >= 2
        and security_represented >= 2
    ):
        return "IMPLICIT_BOUNDARY_CANDIDATE_REQUIRES_CONTRACT_RECONCILIATION"

    if represented >= 2:
        return "PARTIAL_IMPLEMENTATION_REPRESENTATION"

    if represented:
        return "LIMITED_RUNTIME_REPRESENTATION"

    return "NO_CONFIRMED_RUNTIME_REPRESENTATION"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 100)
    print("LYRION PB-DOC-005..008 CONTRACT RESPONSIBILITY MAPPER")
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

    models_by_path = {
        str(model.path.relative_to(REPO_ROOT)): model
        for model in models
    }

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

    results: dict[str, list[ResponsibilityEvidence]] = {}
    concept_summary: dict[str, dict] = {}

    print()
    print("=" * 100)
    print("CONTRACT RESPONSIBILITY ANALYSIS")
    print("=" * 100)

    for concept, responsibility_map in RESPONSIBILITIES.items():
        print()
        print("-" * 100)
        print(concept)
        print("-" * 100)

        evidence_list: list[ResponsibilityEvidence] = []

        for responsibility, terms in responsibility_map.items():
            evidence = analyze_responsibility(
                responsibility,
                terms,
                models,
                tests,
                models_by_path,
            )

            evidence_list.append(evidence)

            print(
                f"{responsibility:32s} "
                f"runtime={len(evidence.runtime_symbols):3d} "
                f"contracts={len(evidence.contract_symbols):3d} "
                f"tests={len(evidence.tests):3d} "
                f"security={len(evidence.security_signals):2d}"
            )

            for symbol in evidence.contract_symbols[:4]:
                print(
                    f"      contract: "
                    f"{symbol.qualified} "
                    f"[{symbol.kind}] "
                    f"{symbol.file}:{symbol.line}"
                )

            if evidence.security_signals:
                print(
                    "      security: "
                    + ", ".join(evidence.security_signals)
                )

        results[concept] = evidence_list

        explicit = explicit_boundary_status(
            concept,
            models,
        )

        class_result = classification(
            evidence_list,
        )

        architecture_result = architectural_classification(
            concept,
            evidence_list,
            explicit,
        )

        print()
        print(f"REPRESENTATION : {class_result}")
        print(f"BOUNDARY       : {explicit}")
        print(f"ARCHITECTURE   : {architecture_result}")

        concept_summary[concept] = {
            "representation": class_result,
            "explicit_boundary": explicit,
            "architectural_classification": architecture_result,
            "responsibilities": {
                evidence.responsibility: {
                    "runtime_symbols": len(
                        evidence.runtime_symbols
                    ),
                    "contract_symbols": len(
                        evidence.contract_symbols
                    ),
                    "tests": len(evidence.tests),
                    "security_signals": evidence.security_signals,
                    "modules": evidence.modules[:20],
                    "score": evidence.score,
                }
                for evidence in evidence_list
            },
        }

    print()
    print("=" * 100)
    print("PROTECTED SECURITY / EXECUTION ORDER")
    print("=" * 100)

    boundary_signals = boundary_order_signals(
        models,
    )

    for boundary, symbols in boundary_signals.items():
        print()
        print(f"{boundary}:")
        if symbols:
            for symbol in symbols:
                print(f"  - {symbol}")
        else:
            print("  - NO_SYMBOL_FOUND")

    print()
    print("=" * 100)
    print("LHICF-SPECIFIC RECONCILIATION")
    print("=" * 100)

    lhicf = results["LHICF"]

    direct_lhicf = [
        item
        for item in lhicf
        if item.runtime_symbols
    ]

    lhicf = results["LHICF"]

    direct_lhicf = [
        item
        for item in lhicf
        if item.runtime_symbols
    ]

    print(
        "Direct LHICF symbols:",
        sum(len(item.runtime_symbols) for item in direct_lhicf),
    )

    print(
        "Host adapter representation:",
        sum(
            len(item.runtime_symbols)
            for item in direct_lhicf
            if item.responsibility == "host_adapter_boundary"
        ),
    )

    print(
        "Host operation representation:",
        sum(
            len(item.runtime_symbols)
            for item in direct_lhicf
            if item.responsibility == "host_operation_boundary"
        ),
    )

    print(
        "Execution enforcement representation:",
        sum(
            len(item.runtime_symbols)
            for item in direct_lhicf
            if item.responsibility == "execution_enforcement_boundary"
        ),
    )

    print(
        "Host provenance representation:",
        sum(
            len(item.runtime_symbols)
            for item in direct_lhicf
            if item.responsibility == "host_provenance_boundary"
        ),
    )

    print()
    print("=" * 100)
    print("ARCHITECTURAL INTERPRETATION")
    print("=" * 100)

    print(
        "This analysis distinguishes responsibility representation from "
        "explicit architectural ownership."
    )
    print(
        "Existing adapters/enforcement/host modules are NOT automatically "
        "declared to be LHICF."
    )
    print(
        "A future LHICF implementation must not introduce an alternate "
        "authorization or privileged execution path."
    )
    print(
        "Any proposed boundary must preserve:"
    )
    print(
        "Aegis -> Capability Gateway -> Execution Admission -> "
        "Secure Executor -> Sandbox -> Host integration"
    )

    print()
    print("No implementation slice selected.")
    print("No source/test/document mutation performed.")

    print()
    print("-" * 100)
    print("EVIDENCE BOUNDARY")
    print("-" * 100)
    print("Analysis type                 : STATIC CONTRACT RESPONSIBILITY REVIEW")
    print("Executed validation           : NOT ASSESSED")
    print("Acceptance evidence           : NOT ASSESSED")
    print("Production implementation     : BLOCKED")
    print("Production certification      : NOT CLAIMED")
    print("G46.5 reconstruction          : NOT PERFORMED")
    print("G47 reconstruction            : NOT PERFORMED")
    print("R097 modification             : NONE")
    print("Source/test/document mutation : NONE")

    summary = {
        "decision": "PB_DOC_005_008_CONTRACT_RESPONSIBILITY_MAPPING_COMPLETE",
        "head": head,
        "origin_main": origin,
        "runtime_python_files": len(paths),
        "runtime_modules": len(models),
        "runtime_symbols": symbol_count,
        "project_test_files": len(tests),
        "parse_failures": len(parse_failures),
        "concepts": concept_summary,
        "protected_boundary_signals": boundary_signals,
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
    print(json.dumps(summary, indent=2, sort_keys=True))

    print()
    print(
        "Decision: "
        "PB_DOC_005_008_CONTRACT_RESPONSIBILITY_MAPPING_COMPLETE"
    )

    print()
    print("=" * 100)
    print("RUNTIME HASH SAMPLE")
    print("=" * 100)

    for path in paths[:12]:
        print(
            f"{path.relative_to(REPO_ROOT)} "
            f"{sha256(path)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

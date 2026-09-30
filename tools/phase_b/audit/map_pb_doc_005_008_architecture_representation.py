#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005..008 Architecture Representation Mapper

READ-ONLY ENGINEERING REVIEW TOOL.

Purpose:
    Map the documented Phase-B concepts:

        PB-DOC-005 Agent Harness
        PB-DOC-006 Host Harness
        PB-DOC-007 Universal Computer
        PB-DOC-008 Application Harness
        LHICF

    against the EXISTING runtime implementation.

The tool deliberately does NOT infer that a concept is missing merely because
the exact architectural name is absent. It searches for implementation
abstractions, responsibilities, interfaces, adapters, enforcement boundaries,
and host/application integration mechanisms that may represent the concept
under another name.

This tool MUST NOT:
    - modify src/
    - modify tests/
    - modify docs/
    - modify manifests
    - reconstruct G46.5/G47
    - access credentials/secrets
    - access external networks
    - perform privileged operations
    - modify Git history
    - claim production certification

Evidence classification:
    STATIC ARCHITECTURE-REPRESENTATION REVIEW ONLY
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
    "trace_pb_doc_001_008_call_chain.py",
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
    "trace_pb_doc_001_008_execution_flow.py",
    "map_pb_doc_005_008_architecture_representation.py",
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


# ---------------------------------------------------------------------------
# Concept responsibility maps
# ---------------------------------------------------------------------------

CONCEPTS = {
    "PB-DOC-005 AgentHarness": {
        "responsibilities": {
            "agent_identity": [
                "AgentIdentity",
                "Principal",
                "Agent",
                "AgentContext",
                "ApplicationPrincipalContext",
            ],
            "lifecycle": [
                "Lifecycle",
                "RuntimeState",
                "RuntimeController",
                "State",
                "TaskState",
            ],
            "task_binding": [
                "TaskBinding",
                "Task",
                "TaskContext",
                "TaskManager",
                "TaskExecution",
            ],
            "authority": [
                "Authority",
                "Authorization",
                "AuthorizationGuard",
                "Delegated",
                "AegisAuthorizationService",
            ],
            "capability": [
                "Capability",
                "CapabilityRequest",
                "CapabilityGateway",
                "CapabilityOperation",
            ],
            "resource_control": [
                "Resource",
                "ResourceLimits",
                "RuntimeBudget",
                "Budget",
            ],
            "sandbox": [
                "Sandbox",
                "SandboxConfig",
                "SandboxPolicy",
                "SandboxPolicyEvaluator",
            ],
            "recovery": [
                "Recovery",
                "Checkpoint",
                "Failure",
                "Retry",
            ],
        },
    },
    "PB-DOC-006 HostHarness": {
        "responsibilities": {
            "host_identity_context": [
                "HostContext",
                "HostIdentity",
                "HostState",
                "Environment",
                "EnvironmentPlan",
            ],
            "host_capability_discovery": [
                "HostCapability",
                "CapabilityDetector",
                "CapabilityProvider",
                "CapabilitySnapshot",
                "LinuxHostCapabilitySnapshot",
                "LinuxHostCapabilityDetector",
                "LinuxHostCapabilityProvider",
            ],
            "filesystem": [
                "Filesystem",
                "FilesystemMode",
                "Path",
                "File",
            ],
            "process": [
                "Process",
                "ProcessBoundary",
                "ProcessRunner",
                "ProcessExecution",
            ],
            "service": [
                "Service",
                "Systemd",
                "ServiceManager",
            ],
            "network": [
                "Network",
                "NetworkMode",
                "NetworkAdapter",
            ],
            "application": [
                "Application",
                "ApplicationContext",
                "ApplicationRuntime",
            ],
            "desktop": [
                "Desktop",
                "Display",
                "Window",
                "Clipboard",
                "Notification",
            ],
            "device": [
                "Device",
                "Hardware",
                "USB",
            ],
            "adapter": [
                "HostAdapter",
                "PrimitiveAdapter",
                "Adapter",
                "AdapterRegistry",
            ],
            "enforcement": [
                "LinuxEnforcement",
                "Enforcement",
                "AppArmor",
                "Cgroup",
                "Seccomp",
                "Namespace",
            ],
        },
    },
    "PB-DOC-007 UniversalComputer": {
        "responsibilities": {
            "abstraction": [
                "UniversalComputer",
                "UniversalComputerOperation",
                "Operation",
                "PrimitiveAdapter",
                "PrimitiveAdapterRegistry",
            ],
            "mapping": [
                "EnvironmentPlan",
                "OperationPlan",
                "Mapping",
                "AdapterRegistry",
            ],
            "host_independence": [
                "Environment",
                "Host",
                "Platform",
                "Backend",
            ],
            "discovery": [
                "Discovery",
                "CapabilityDetector",
                "CapabilityProvider",
                "CapabilitySnapshot",
            ],
            "execution_boundary": [
                "ExecutionAdmission",
                "SecureExecutor",
                "ExecutionResult",
                "ExecutionRequest",
            ],
            "verification": [
                "Verification",
                "Evidence",
                "Provenance",
                "Audit",
            ],
        },
    },
    "PB-DOC-008 ApplicationHarness": {
        "responsibilities": {
            "application_identity": [
                "ApplicationIdentity",
                "ApplicationContext",
                "ApplicationPrincipalContext",
            ],
            "application_discovery": [
                "Application",
                "ApplicationRuntime",
                "ApplicationDiscovery",
                "ApplicationRegistry",
            ],
            "application_capability": [
                "ApplicationCapability",
                "Capability",
                "CapabilityOperation",
                "CapabilityRequest",
            ],
            "application_adapter": [
                "ApplicationAdapter",
                "Adapter",
                "EnforcementApplication",
                "EnforcementApplicationContext",
            ],
            "ui_api": [
                "UI",
                "Desktop",
                "API",
                "MCP",
                "A2A",
            ],
            "application_state": [
                "ApplicationState",
                "RuntimeState",
                "Context",
            ],
            "security_execution": [
                "Authorization",
                "ExecutionAdmission",
                "SecureExecutor",
                "Sandbox",
                "AegisAuthorizationService",
            ],
            "verification": [
                "Verification",
                "Evidence",
                "Provenance",
                "Audit",
            ],
        },
    },
    "LHICF": {
        "responsibilities": {
            "host_integration": [
                "HostIntegration",
                "HostIntegrationControlFabric",
                "LHICF",
                "Lhicf",
            ],
            "adapter_boundary": [
                "HostAdapter",
                "PrimitiveAdapter",
                "Adapter",
                "AdapterRegistry",
            ],
            "host_operations": [
                "HostOperation",
                "Filesystem",
                "Process",
                "Service",
                "Network",
                "Application",
                "Desktop",
                "Device",
                "Clipboard",
            ],
            "security_boundary": [
                "ExecutionAdmission",
                "SecureExecutor",
                "Sandbox",
                "CapabilityGateway",
            ],
            "verification_provenance": [
                "Verification",
                "Provenance",
                "Evidence",
                "Audit",
            ],
        },
    },
}


# ---------------------------------------------------------------------------
# Git / filesystem safety
# ---------------------------------------------------------------------------

def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


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

        if path.startswith("tools/phase_b/audit/"):
            if Path(path).name in ALLOWED_AUDIT_UNTRACKED:
                continue

        failures.append(f"unexpected worktree change: {line}")

    return not failures, failures


def runtime_files() -> list[Path]:
    return sorted(
        p
        for p in SRC_ROOT.rglob("*.py")
        if p.is_file()
        and not any(
            part
            in {
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
    if not TEST_ROOT.exists():
        return []

    return sorted(
        p
        for p in TEST_ROOT.rglob("*.py")
        if p.is_file()
        and not any(
            part
            in {
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


# ---------------------------------------------------------------------------
# AST model
# ---------------------------------------------------------------------------

def module_name(path: Path) -> str:
    rel = path.relative_to(SRC_ROOT)
    parts = list(rel.parts)

    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(parts)


def dotted(node: ast.AST | None) -> str | None:
    if node is None:
        return None

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
            value
            for value in (dotted(base) for base in node.bases)
            if value
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

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)


def parse_files(
    files: list[Path],
) -> tuple[list[ModuleModel], list[str]]:
    models: list[ModuleModel] = []
    failures: list[str] = []

    for path in files:
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
# Concept matching
# ---------------------------------------------------------------------------

def text_for_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").lower()
    except Exception:
        return ""


def symbol_matches(symbol: Symbol, term: str) -> bool:
    haystack = f"{symbol.qualified} {symbol.short}".lower()
    return term.lower() in haystack


def responsibility_matches(
    models: list[ModuleModel],
    terms: list[str],
) -> list[Symbol]:
    matches: dict[str, Symbol] = {}

    for model in models:
        for symbol in model.symbols:
            for term in terms:
                if symbol_matches(symbol, term):
                    matches[symbol.qualified] = symbol
                    break

    return sorted(matches.values(), key=lambda item: item.qualified)


def test_matches(
    files: list[Path],
    terms: list[str],
) -> list[str]:
    matches: list[str] = []

    lowered_terms = [term.lower() for term in terms]

    for path in files:
        text = text_for_file(path)

        if any(term in text for term in lowered_terms):
            matches.append(str(path.relative_to(REPO_ROOT)))

    return sorted(matches)


def module_scope_matches(
    models: list[ModuleModel],
    terms: list[str],
) -> list[str]:
    results: set[str] = set()

    for model in models:
        module_text = model.module.lower()
        file_text = str(model.path).lower()

        if any(
            term.lower() in module_text or term.lower() in file_text
            for term in terms
        ):
            results.add(
                str(model.path.relative_to(REPO_ROOT))
            )

    return sorted(results)


# ---------------------------------------------------------------------------
# Representation classification
# ---------------------------------------------------------------------------

def classify_concept(
    responsibility_results: dict[str, list[Symbol]],
    test_results: dict[str, list[str]],
) -> str:
    runtime_hits = sum(
        bool(matches)
        for matches in responsibility_results.values()
    )

    test_hits = sum(
        bool(matches)
        for matches in test_results.values()
    )

    if runtime_hits and test_hits:
        return "RUNTIME_AND_TEST_REPRESENTATION_FOUND"

    if runtime_hits:
        return "RUNTIME_REPRESENTATION_FOUND"

    if test_hits:
        return "TEST_OR_CONTRACT_SURFACE_ONLY"

    return "NO_DIRECT_IMPLEMENTATION_REPRESENTATION_FOUND"


def print_symbol_sample(
    symbols: list[Symbol],
    limit: int = 8,
) -> None:
    for symbol in symbols[:limit]:
        print(
            f"      - {symbol.qualified} "
            f"[{symbol.kind}] "
            f"{symbol.file}:{symbol.line}"
        )


# ---------------------------------------------------------------------------
# Boundary-specific analysis
# ---------------------------------------------------------------------------

def boundary_proximity(
    models: list[ModuleModel],
    concept: str,
) -> dict[str, list[str]]:
    signals: dict[str, list[str]] = defaultdict(list)

    for model in models:
        text = text_for_file(model.path)

        if concept == "PB-DOC-005 AgentHarness":
            if any(
                term in text
                for term in (
                    "agent",
                    "lifecycle",
                    "task",
                    "resource",
                    "sandbox",
                    "authorization",
                )
            ):
                signals["agent-runtime"].append(
                    str(model.path.relative_to(REPO_ROOT))
                )

        elif concept == "PB-DOC-006 HostHarness":
            if any(
                term in text
                for term in (
                    "host",
                    "linux",
                    "process",
                    "filesystem",
                    "service",
                    "network",
                    "apparmor",
                    "cgroup",
                    "seccomp",
                )
            ):
                signals["host-runtime"].append(
                    str(model.path.relative_to(REPO_ROOT))
                )

        elif concept == "PB-DOC-007 UniversalComputer":
            if any(
                term in text
                for term in (
                    "adapter",
                    "environment",
                    "primitive",
                    "capability",
                    "execution",
                    "operation",
                )
            ):
                signals["universal-computer-runtime"].append(
                    str(model.path.relative_to(REPO_ROOT))
                )

        elif concept == "PB-DOC-008 ApplicationHarness":
            if any(
                term in text
                for term in (
                    "application",
                    "desktop",
                    "mcp",
                    "a2a",
                    "enforcementapplication",
                )
            ):
                signals["application-runtime"].append(
                    str(model.path.relative_to(REPO_ROOT))
                )

        elif concept == "LHICF":
            if any(
                term in text
                for term in (
                    "host integration",
                    "host_adapter",
                    "primitiveadapter",
                    "host operation",
                    "linux enforcement",
                    "enforcement",
                )
            ):
                signals["host-integration-runtime"].append(
                    str(model.path.relative_to(REPO_ROOT))
                )

    return {
        key: sorted(set(value))
        for key, value in signals.items()
    }


def architecture_interpretation(
    concept: str,
    runtime_hits: int,
    responsibilities: int,
    proximity: dict[str, list[str]],
) -> str:
    if runtime_hits and responsibilities:
        return (
            "CONCRETE_REPRESENTATION_CANDIDATE — "
            "existing runtime abstractions map to documented responsibilities; "
            "requires engineering contract review before implementation."
        )

    if proximity:
        return (
            "PARTIAL_RESPONSIBILITY_SURFACE — "
            "related implementation exists, but explicit architectural "
            "boundary representation is not established."
        )

    return (
        "NO_CONFIRMED_RUNTIME_MAPPING — "
        "requires architecture/implementation design review."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 96)
    print("LYRION PB-DOC-005..008 ARCHITECTURE REPRESENTATION MAPPER")
    print("=" * 96)

    ok, failures = repo_guard()

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    branch = run_git("branch", "--show-current")

    print(f"Repository : {REPO_ROOT}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")
    print(f"Repo Guard : {'PASS' if ok else 'FAIL'}")

    if not ok:
        for failure in failures:
            print(f"  FAIL: {failure}")
        print("Decision: BASELINE_NOT_CLEAN")
        return 2

    files = runtime_files()
    tests = test_files()

    models, parse_failures = parse_files(files)

    symbol_count = sum(len(model.symbols) for model in models)

    print()
    print("-" * 96)
    print("SOURCE INVENTORY")
    print("-" * 96)
    print(f"Runtime Python files : {len(files)}")
    print(f"Runtime modules      : {len(models)}")
    print(f"Runtime symbols      : {symbol_count}")
    print(f"Project test files   : {len(tests)}")
    print(f"AST failures         : {len(parse_failures)}")

    if parse_failures:
        for failure in parse_failures[:20]:
            print(f"  PARSE FAIL: {failure}")

    runtime_results: dict[str, dict[str, list[Symbol]]] = {}
    test_results: dict[str, dict[str, list[str]]] = {}
    proximity_results: dict[str, dict[str, list[str]]] = {}
    machine_summary: dict[str, dict] = {}

    print()
    print("=" * 96)
    print("PB-DOC ARCHITECTURE REPRESENTATION ANALYSIS")
    print("=" * 96)

    for concept, definition in CONCEPTS.items():
        print()
        print("-" * 96)
        print(concept)
        print("-" * 96)

        runtime_results[concept] = {}
        test_results[concept] = {}

        for responsibility, terms in definition["responsibilities"].items():
            symbols = responsibility_matches(models, terms)
            matching_tests = test_matches(tests, terms)

            runtime_results[concept][responsibility] = symbols
            test_results[concept][responsibility] = matching_tests

            print(
                f"{responsibility:30s} "
                f"runtime={len(symbols):3d} "
                f"tests={len(matching_tests):3d}"
            )

            if symbols:
                print_symbol_sample(symbols, limit=5)

            if matching_tests:
                for path in matching_tests[:4]:
                    print(f"      test: {path}")

        proximity = boundary_proximity(models, concept)
        proximity_results[concept] = proximity

        runtime_hit_count = sum(
            len(value)
            for value in runtime_results[concept].values()
        )

        responsibility_count = sum(
            bool(value)
            for value in runtime_results[concept].values()
        )

        classification = classify_concept(
            runtime_results[concept],
            test_results[concept],
        )

        interpretation = architecture_interpretation(
            concept,
            runtime_hit_count,
            responsibility_count,
            proximity,
        )

        machine_summary[concept] = {
            "classification": classification,
            "runtime_hit_count": runtime_hit_count,
            "responsibility_count": responsibility_count,
            "test_hit_count": sum(
                len(value)
                for value in test_results[concept].values()
            ),
            "proximity": proximity,
            "interpretation": interpretation,
        }

        print()
        print(f"CLASSIFICATION : {classification}")
        print(f"INTERPRETATION : {interpretation}")

        if proximity:
            print("PROXIMITY SIGNALS:")
            for key, paths in proximity.items():
                print(f"  {key}: {len(paths)} file(s)")
                for path in paths[:8]:
                    print(f"    - {path}")

    print()
    print("=" * 96)
    print("SECURITY / EXECUTION BOUNDARY PRESENCE")
    print("=" * 96)

    boundary_terms = {
        "Aegis": [
            "AegisAuthorizationService",
            "AegisPolicyEvaluator",
        ],
        "Authorization": [
            "AuthorizationGuard",
            "ReplayGuard",
            "AuthorizationResult",
        ],
        "CapabilityGateway": [
            "CapabilityGateway",
        ],
        "ExecutionAdmission": [
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
        ],
        "SecureExecutor": [
            "SecureExecutor",
        ],
        "Sandbox": [
            "SandboxConfig",
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
        ],
        "UniversalComputer": [
            "PrimitiveAdapter",
            "PrimitiveAdapterRegistry",
            "EnvironmentPlan",
            "LinuxEnforcementPlanner",
        ],
        "ApplicationHarness": [
            "EnforcementApplication",
            "EnforcementApplicationContext",
        ],
        "LHICF": [
            "LHICF",
            "HostIntegrationControlFabric",
            "HostIntegration",
        ],
    }

    boundary_presence: dict[str, int] = {}

    for boundary, terms in boundary_terms.items():
        symbols = responsibility_matches(models, terms)
        boundary_presence[boundary] = len(symbols)

        print(
            f"{boundary:24s}: "
            f"{'PRESENT' if symbols else 'NOT_EXPLICITLY_FOUND'} "
            f"({len(symbols)})"
        )

        print_symbol_sample(symbols, limit=6)

    print()
    print("=" * 96)
    print("ARCHITECTURAL CONCLUSION")
    print("=" * 96)

    print(
        "This tool does NOT declare an architectural component missing "
        "solely because its exact name is absent."
    )
    print(
        "Existing abstractions are classified as representation candidates "
        "only when runtime responsibilities are materially mapped."
    )
    print(
        "A responsibility surface is not equivalent to an approved "
        "architecture boundary or production implementation."
    )
    print(
        "No implementation slice is selected by this tool."
    )

    print()
    print("Required engineering interpretation:")
    print(
        "1. Determine whether PB-DOC-005 Agent Harness is represented by "
        "existing agent/runtime/task/authority abstractions."
    )
    print(
        "2. Determine whether PB-DOC-006 Host Harness is represented by "
        "existing host capability/enforcement/backend abstractions."
    )
    print(
        "3. Determine whether PB-DOC-007 Universal Computer is represented "
        "by existing adapter/environment/operation abstractions."
    )
    print(
        "4. Determine whether PB-DOC-008 Application Harness is represented "
        "by existing application/enforcement abstractions."
    )
    print(
        "5. Determine whether LHICF is an existing boundary, an implicit "
        "integration mechanism, or a future explicit boundary."
    )

    print()
    print("-" * 96)
    print("EVIDENCE BOUNDARY")
    print("-" * 96)
    print("Analysis type                 : STATIC ARCHITECTURE REPRESENTATION REVIEW")
    print("Executed validation           : NOT ASSESSED")
    print("Acceptance evidence           : NOT ASSESSED")
    print("Production implementation     : BLOCKED")
    print("Production certification      : NOT CLAIMED")
    print("G46.5 reconstruction          : NOT PERFORMED")
    print("G47 reconstruction            : NOT PERFORMED")
    print("R097 modification             : NONE")
    print("Source/test/document mutation : NONE")

    summary = {
        "decision": "PB_DOC_005_008_REPRESENTATION_MAPPING_COMPLETE",
        "head": head,
        "origin_main": origin,
        "runtime_python_files": len(files),
        "runtime_modules": len(models),
        "runtime_symbols": symbol_count,
        "project_test_files": len(tests),
        "parse_failures": len(parse_failures),
        "concepts": machine_summary,
        "boundary_presence": boundary_presence,
        "production_certification": "NOT_CLAIMED",
        "production_implementation": "BLOCKED",
        "g46_5": "NOT_PERFORMED",
        "g47": "NOT_PERFORMED",
        "r097": "NONE",
    }

    print()
    print("-" * 96)
    print("MACHINE SUMMARY")
    print("-" * 96)
    print(json.dumps(summary, indent=2, sort_keys=True))

    print()
    print("Decision: PB_DOC_005_008_REPRESENTATION_MAPPING_COMPLETE")

    print()
    print("-" * 96)
    print("RUNTIME HASH SAMPLE")
    print("-" * 96)

    for path in files[:12]:
        print(
            f"{path.relative_to(REPO_ROOT)} "
            f"{sha256(path)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

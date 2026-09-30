#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-001..008 Read-Only Execution-Flow Tracer

Purpose:
    Trace the concrete static execution/dependency flow around the existing
    Phase-B security and execution boundaries.

This is ENGINEERING REVIEW evidence only.

It does not:
    - modify src/
    - modify tests/
    - modify docs/
    - modify manifests
    - create/reconstruct G46.5 or G47 evidence
    - access credentials/secrets
    - access external networks
    - perform privileged operations
    - modify Git history
    - claim production certification
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
SELF = Path(__file__).resolve()

ALLOWED_AUDIT_UNTRACKED = {
    "trace_pb_doc_001_008_call_chain.py",
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "trace_pb_doc_001_008_execution_flow.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
}

BOUNDARY_SYMBOLS = {
    "Aegis": {
        "AegisAuthorizationService",
        "AegisPolicyEvaluator",
        "AegisPolicy",
        "AegisRuleEvaluator",
    },
    "Authorization": {
        "AuthorizationGuard",
        "ReplayGuard",
        "AuthorizationDecision",
        "AuthorizationResult",
        "ApplicationPrincipalContext",
        "validate_authorization_state",
        "validate_authorization_expiry",
    },
    "CapabilityGateway": {
        "CapabilityGateway",
        "CapabilityRequest",
        "CapabilityOperation",
    },
    "ExecutionAdmission": {
        "ExecutionAdmission",
        "ExecutionAdmissionEnvelope",
    },
    "PIAE": {
        "PIAE",
        "Planning",
        "Planner",
        "Plan",
        "Decision",
    },
    "SecureExecutor": {
        "SecureExecutor",
        "ExecutionResult",
    },
    "Sandbox": {
        "SandboxConfig",
        "SandboxPolicy",
        "SandboxPolicyEvaluator",
        "SandboxEvaluationResult",
    },
    "UniversalComputer": {
        "UniversalComputer",
        "UniversalComputerOperation",
        "PrimitiveAdapter",
        "PrimitiveAdapterRegistry",
        "EnvironmentPlan",
        "LinuxEnforcementPlanner",
    },
    "AgentHarness": {
        "AgentHarness",
        "AgentRuntime",
        "AgentIdentity",
        "AgentLifecycle",
        "TaskBinding",
    },
    "HostHarness": {
        "HostHarness",
        "HostContext",
        "HostAdapter",
        "HostOperation",
    },
    "ApplicationHarness": {
        "ApplicationHarness",
        "ApplicationIdentity",
        "ApplicationContext",
        "ApplicationAdapter",
        "ApplicationCapability",
        "EnforcementApplication",
        "EnforcementApplicationContext",
    },
    "LHICF": {
        "LHICF",
        "Lhicf",
        "HostIntegrationControlFabric",
        "HostIntegration",
    },
}

EXPECTED_FLOW = [
    "Aegis",
    "Authorization",
    "CapabilityGateway",
    "ExecutionAdmission",
    "PIAE",
    "SecureExecutor",
    "Sandbox",
    "UniversalComputer",
    "HostHarness",
    "LHICF",
]

EXPLICIT_PACKAGE_OWNERSHIP = (
    ("lyrion.security.authorization", "Aegis"),
    ("lyrion.security.policy", "Aegis"),
    ("lyrion.security.rules", "Aegis"),
    ("lyrion.security.guards", "Authorization"),
    ("lyrion.security.replay", "Authorization"),
    ("lyrion.capabilities.gateway", "CapabilityGateway"),
    ("lyrion.capabilities.contracts", "CapabilityGateway"),
    ("lyrion.execution.contracts", "ExecutionAdmission"),
    ("lyrion.execution.executor", "SecureExecutor"),
    ("lyrion.execution.sandbox", "Sandbox"),
    ("lyrion.piae", "PIAE"),
    ("lyrion.cognition", "PIAE"),
    ("lyrion.execution.backends.linux.enforcement", "UniversalComputer"),
)


@dataclass(frozen=True)
class Symbol:
    qualified: str
    short: str
    module: str
    kind: str
    file: str
    line: int


@dataclass
class ModuleModel:
    module: str
    path: Path
    tree: ast.Module
    imports: dict[str, str] = field(default_factory=dict)
    symbols: dict[str, Symbol] = field(default_factory=dict)


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
        self.symbols: dict[str, Symbol] = {}
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
        self.symbols[node.name] = Symbol(
            qualified=qualified,
            short=node.name,
            module=self.module,
            kind="class",
            file=str(self.path.relative_to(REPO_ROOT)),
            line=node.lineno,
        )

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def _function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        qualified = ".".join(
            [self.module, *self.class_stack, node.name]
        )
        self.symbols[node.name] = Symbol(
            qualified=qualified,
            short=node.name,
            module=self.module,
            kind="function",
            file=str(self.path.relative_to(REPO_ROOT)),
            line=node.lineno,
        )
        self.generic_visit(node)


def parse_all(
    files: list[Path],
) -> tuple[dict[str, ModuleModel], list[str]]:
    models: dict[str, ModuleModel] = {}
    failures: list[str] = []

    for path in files:
        try:
            visitor = Visitor(module_name(path), path)
            models[visitor.module] = ModuleModel(
                module=visitor.module,
                path=path,
                tree=visitor.tree,
                imports=visitor.imports,
                symbols=visitor.symbols,
            )
        except Exception as exc:
            failures.append(f"{path}: {exc}")

    return models, failures


def build_index(
    models: dict[str, ModuleModel],
) -> tuple[dict[str, list[Symbol]], dict[str, Symbol]]:
    short: dict[str, list[Symbol]] = defaultdict(list)
    qualified: dict[str, Symbol] = {}

    for model in models.values():
        for symbol in model.symbols.values():
            short[symbol.short].append(symbol)
            qualified[symbol.qualified] = symbol

    return short, qualified


def owner(symbol: Symbol | None) -> str | None:
    if symbol is None:
        return None

    for boundary, names in BOUNDARY_SYMBOLS.items():
        if symbol.short in names:
            return boundary

    for prefix, boundary in EXPLICIT_PACKAGE_OWNERSHIP:
        if symbol.module == prefix or symbol.module.startswith(prefix + "."):
            return boundary

    return None


def resolve(
    reference: str,
    model: ModuleModel,
    short_index: dict[str, list[Symbol]],
) -> list[Symbol]:
    short = reference.split(".")[-1]
    candidates: list[Symbol] = []

    candidates.extend(
        symbol
        for symbol in model.symbols.values()
        if symbol.short == short
    )

    if short in model.imports:
        imported = model.imports[short]
        imported_short = imported.split(":")[-1].split(".")[-1]
        candidates.extend(short_index.get(imported_short, []))

    candidates.extend(short_index.get(short, []))

    unique = {candidate.qualified: candidate for candidate in candidates}
    return list(unique.values())


def function_body(
    model: ModuleModel,
    symbol: Symbol,
) -> ast.AST | None:
    for node in ast.walk(model.tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.name == symbol.short
                and node.lineno == symbol.line
            ):
                return node

    return None


def find_boundary_symbols(
    qualified_index: dict[str, Symbol],
) -> dict[str, list[Symbol]]:
    result: dict[str, list[Symbol]] = defaultdict(list)

    for symbol in qualified_index.values():
        boundary = owner(symbol)
        if boundary:
            result[boundary].append(symbol)

    return result


def collect_edges(
    models: dict[str, ModuleModel],
    short_index: dict[str, list[Symbol]],
) -> dict[str, set[str]]:
    """
    Build a conservative boundary graph.

    A graph edge exists only when a concrete resolved Symbol owned by one
    boundary directly references a concrete Symbol owned by another boundary
    through:
      - a call
      - a constructor/factory invocation
      - a type annotation
      - an instantiated dependency
    """
    graph: dict[str, set[str]] = defaultdict(set)

    for model in models.values():
        for source in model.symbols.values():
            source_boundary = owner(source)
            if not source_boundary:
                continue

            body = function_body(model, source)
            if body is None:
                continue

            for node in ast.walk(body):
                references: list[str] = []

                if isinstance(node, ast.Call):
                    ref = dotted(node.func)
                    if ref:
                        references.append(ref)

                elif isinstance(node, ast.AnnAssign):
                    ref = dotted(node.annotation)
                    if ref:
                        references.append(ref)

                elif isinstance(node, ast.arg):
                    ref = dotted(node.annotation)
                    if ref:
                        references.append(ref)

                for reference in references:
                    for target in resolve(
                        reference,
                        model,
                        short_index,
                    ):
                        target_boundary = owner(target)

                        if (
                            target_boundary
                            and target_boundary != source_boundary
                        ):
                            graph[source_boundary].add(target_boundary)

    return graph


def trace_paths(
    graph: dict[str, set[str]],
    start: str,
    target: str,
    max_depth: int = 8,
) -> list[list[str]]:
    paths: list[list[str]] = []
    queue: deque[list[str]] = deque([[start]])

    while queue and len(paths) < 10:
        path = queue.popleft()
        current = path[-1]

        if current == target:
            paths.append(path)
            continue

        if len(path) > max_depth:
            continue

        for nxt in sorted(graph.get(current, set())):
            if nxt not in path:
                queue.append([*path, nxt])

    return paths


def main() -> int:
    print("=" * 88)
    print("LYRION PB-DOC-001..008 READ-ONLY EXECUTION-FLOW TRACE")
    print("=" * 88)

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
    models, parse_failures = parse_all(files)
    short_index, qualified_index = build_index(models)
    boundaries = find_boundary_symbols(qualified_index)

    print(f"Runtime Python files : {len(files)}")
    print(f"Parsed modules       : {len(models)}")
    print(f"AST failures         : {len(parse_failures)}")
    print(f"Runtime symbols      : {len(qualified_index)}")

    if parse_failures:
        for failure in parse_failures[:20]:
            print(f"  PARSE FAIL: {failure}")

    print()
    print("-" * 88)
    print("BOUNDARY REPRESENTATION")
    print("-" * 88)

    for boundary in BOUNDARY_SYMBOLS:
        symbols = boundaries.get(boundary, [])
        print(
            f"{boundary:22s}: "
            f"{'PRESENT' if symbols else 'NOT_EXPLICITLY_FOUND'} "
            f"({len(symbols)})"
        )
        for symbol in sorted(symbols, key=lambda x: x.qualified)[:8]:
            print(
                f"  - {symbol.qualified} "
                f"[{symbol.kind}] {symbol.file}:{symbol.line}"
            )

    graph = collect_edges(models, short_index)

    print()
    print("-" * 88)
    print("CONCRETE BOUNDARY DEPENDENCY GRAPH")
    print("-" * 88)

    for source in EXPECTED_FLOW:
        targets = sorted(graph.get(source, set()))
        if targets:
            print(f"{source} -> {', '.join(targets)}")
        else:
            print(f"{source} -> [no resolved cross-boundary edge]")

    print()
    print("-" * 88)
    print("EXPECTED EXECUTION-FLOW PATH ANALYSIS")
    print("-" * 88)

    adjacent_pairs = list(
        zip(EXPECTED_FLOW, EXPECTED_FLOW[1:])
    )

    path_results = []

    for source, target in adjacent_pairs:
        paths = trace_paths(graph, source, target)

        if paths:
            print(f"{source} -> {target}: PATH FOUND")
            for path in paths:
                print("  " + " -> ".join(path))
        else:
            print(f"{source} -> {target}: NO STATIC PATH")

        path_results.append(
            {
                "source": source,
                "target": target,
                "paths": paths,
            }
        )

    print()
    print("-" * 88)
    print("ARCHITECTURAL REPRESENTATION CHECK")
    print("-" * 88)

    for boundary in (
        "AgentHarness",
        "HostHarness",
        "UniversalComputer",
        "ApplicationHarness",
        "LHICF",
    ):
        symbols = boundaries.get(boundary, [])

        if symbols:
            print(
                f"{boundary}: REPRESENTED "
                f"({len(symbols)} concrete symbol(s))"
            )
        else:
            print(
                f"{boundary}: NO_EXPLICIT_SYMBOL "
                f"(requires abstraction/implementation review)"
            )

    print()
    print("-" * 88)
    print("STATIC EVIDENCE BOUNDARY")
    print("-" * 88)
    print("Execution-flow analysis       : STATIC ENGINEERING REVIEW")
    print("Executed validation            : NOT ASSESSED")
    print("Acceptance evidence            : NOT ASSESSED")
    print("Production implementation      : BLOCKED")
    print("Production certification       : NOT CLAIMED")
    print("G46.5 reconstruction           : NOT PERFORMED")
    print("G47 reconstruction             : NOT PERFORMED")
    print("R097 modification              : NONE")
    print("Source/test/document mutation  : NONE")

    summary = {
        "decision": "EXECUTION_FLOW_TRACE_COMPLETE",
        "head": head,
        "origin_main": origin,
        "runtime_python_files": len(files),
        "parsed_modules": len(models),
        "runtime_symbols": len(qualified_index),
        "parse_failures": len(parse_failures),
        "boundary_counts": {
            key: len(value)
            for key, value in boundaries.items()
        },
        "graph": {
            key: sorted(value)
            for key, value in graph.items()
        },
        "path_results": path_results,
        "production_certification": "NOT_CLAIMED",
        "production_implementation": "BLOCKED",
        "g46_5": "NOT_PERFORMED",
        "g47": "NOT_PERFORMED",
        "r097": "NONE",
    }

    print()
    print("-" * 88)
    print("MACHINE SUMMARY")
    print("-" * 88)
    print(json.dumps(summary, indent=2, sort_keys=True))

    print()
    print("Decision: EXECUTION_FLOW_TRACE_COMPLETE")

    print()
    print("-" * 88)
    print("RUNTIME HASH SAMPLE")
    print("-" * 88)

    for path in files[:12]:
        print(
            f"{path.relative_to(REPO_ROOT)} "
            f"{sha256(path)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

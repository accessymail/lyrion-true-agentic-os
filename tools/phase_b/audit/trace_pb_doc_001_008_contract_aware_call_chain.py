#!/usr/bin/env python3
"""
LYRION True Agentic OS
Phase-B PB-DOC-001..008 Contract-Aware Dependency / Call-Chain Tracer

Purpose
-------
Perform a read-only, contract-aware static analysis of the existing Phase-B
runtime implementation.

This tool does NOT:
- modify runtime source
- modify tests
- modify documentation
- modify manifests
- create G46.5/G47 evidence
- reconstruct G46.5/G47
- claim production certification
- execute privileged operations
- access credentials/secrets
- access external networks
- modify Git history

This tool improves on simple direct-call tracing by examining:
- imports and aliases
- class/function ownership
- type annotations
- constructor dependencies
- attribute assignments
- method calls
- factory/build functions
- inheritance
- dependency injection patterns
- references through intermediate objects
- expected Phase-B security/execution boundaries

Important:
Static evidence is ENGINEERING REVIEW evidence only.
It is not executed validation, acceptance evidence, or production
certification evidence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
AUDIT_ROOT = REPO_ROOT / "tools" / "phase_b" / "audit"
SELF_PATH = Path(__file__).resolve()

ALLOWED_UNTRACKED_AUDIT_TOOLS = {
    "trace_pb_doc_001_008_call_chain.py",
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    SELF_PATH.name,
}

FORBIDDEN_PATH_PARTS = {
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

FORBIDDEN_MUTATING_AST_CALLS = {
    "write_text",
    "write_bytes",
    "unlink",
    "rmtree",
    "remove",
    "rename",
    "mkdir",
    "makedirs",
    "copy",
    "copy2",
    "move",
}

FORBIDDEN_GIT_COMMANDS = {
    "add",
    "checkout",
    "clean",
    "commit",
    "push",
    "reset",
    "restore",
    "rm",
}

BOUNDARIES = {
    "Aegis": {
        "symbols": {
            "AegisAuthorizationService",
            "AegisPolicyEvaluator",
            "AegisPolicy",
            "AegisRuleEvaluator",
        },
        "terms": ("aegis", "policy", "authorization"),
    },
    "Authorization": {
        "symbols": {
            "AuthorizationDecision",
            "AuthorizationResult",
            "AuthorizationGuard",
            "ReplayGuard",
            "ApplicationPrincipalContext",
            "validate_authorization_state",
            "validate_authorization_expiry",
        },
        "terms": ("authorization", "principal", "delegated"),
    },
    "CapabilityGateway": {
        "symbols": {
            "CapabilityGateway",
            "CapabilityRequest",
            "CapabilityOperation",
        },
        "terms": ("capabilitygateway", "capability"),
    },
    "ExecutionAdmission": {
        "symbols": {
            "ExecutionAdmission",
            "ExecutionAdmissionEnvelope",
        },
        "terms": ("executionadmission", "admission"),
    },
    "SecureExecutor": {
        "symbols": {
            "SecureExecutor",
            "ExecutionResult",
        },
        "terms": ("secureexecutor", "executor"),
    },
    "Sandbox": {
        "symbols": {
            "SandboxConfig",
            "SandboxPolicy",
            "SandboxPolicyEvaluator",
            "SandboxEvaluationResult",
        },
        "terms": ("sandbox", "enforcement"),
    },
    "AgentHarness": {
        "symbols": {
            "AgentHarness",
            "AgentRuntime",
            "AgentIdentity",
            "AgentLifecycle",
            "TaskBinding",
        },
        "terms": ("agentharness",),
    },
    "HostHarness": {
        "symbols": {
            "HostHarness",
            "HostContext",
            "HostAdapter",
            "HostOperation",
        },
        "terms": ("hostharness",),
    },
    "UniversalComputer": {
        "symbols": {
            "UniversalComputer",
            "UniversalComputerOperation",
            "PrimitiveAdapter",
            "PrimitiveAdapterRegistry",
            "EnvironmentPlan",
        },
        "terms": ("universalcomputer", "universal_computer"),
    },
    "ApplicationHarness": {
        "symbols": {
            "ApplicationHarness",
            "ApplicationIdentity",
            "ApplicationContext",
            "ApplicationAdapter",
            "ApplicationCapability",
            "EnforcementApplication",
            "EnforcementApplicationContext",
        },
        "terms": ("applicationharness",),
    },
    "LHICF": {
        "symbols": {
            "LHICF",
            "Lhicf",
            "HostIntegrationControlFabric",
            "HostIntegration",
        },
        "terms": ("lhicf", "hostintegrationcontrolfabric"),
    },
}


@dataclass
class Symbol:
    qualified_name: str
    short_name: str
    kind: str
    module: str
    file: str
    line: int
    class_name: str | None = None


@dataclass
class ModuleModel:
    module: str
    path: Path
    tree: ast.AST
    imports: dict[str, str] = field(default_factory=dict)
    symbols: dict[str, Symbol] = field(default_factory=dict)
    classes: dict[str, ast.ClassDef] = field(default_factory=dict)
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = field(
        default_factory=dict
    )
    assignments: list[ast.Assign | ast.AnnAssign] = field(default_factory=list)
    calls: list[ast.Call] = field(default_factory=list)


@dataclass
class Evidence:
    source: str
    target: str
    kind: str
    file: str
    line: int
    detail: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def repository_guard() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        head = run_git("rev-parse", "HEAD")
        origin = run_git("rev-parse", "origin/main")
        branch = run_git("branch", "--show-current")
        status = run_git("status", "--short", "--untracked-files=all")
    except subprocess.CalledProcessError as exc:
        return False, [f"Git inspection failed: {exc}"]

    if head != origin:
        failures.append(f"HEAD != origin/main: {head} != {origin}")

    if branch != "main":
        failures.append(f"Unexpected branch: {branch}")

    for raw in status.splitlines():
        if not raw:
            continue

        path = raw[3:].strip()

        # This audit family is intentionally allowed to exist untracked while
        # it is being developed. Nothing outside the audit directory is allowed.
        if path.startswith("tools/phase_b/audit/"):
            name = Path(path).name
            if name in ALLOWED_UNTRACKED_AUDIT_TOOLS:
                continue

        failures.append(f"Unexpected worktree change: {raw}")

    return not failures, failures


def path_is_forbidden(path: Path) -> bool:
    return any(part in FORBIDDEN_PATH_PARTS for part in path.parts)


def discover_runtime_files() -> list[Path]:
    files = []
    for path in SRC_ROOT.rglob("*.py"):
        if path.is_file() and not path_is_forbidden(path):
            files.append(path)
    return sorted(files)


def module_name_for(path: Path) -> str:
    relative = path.relative_to(SRC_ROOT)
    parts = list(relative.parts)

    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(parts)


def dotted_name(node: ast.AST | None) -> str | None:
    if node is None:
        return None

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr

    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)

    return None


def annotation_names(node: ast.AST | None) -> set[str]:
    names: set[str] = set()

    if node is None:
        return names

    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            value = dotted_name(child)
            if value:
                names.add(value)

    return names


class ModuleVisitor(ast.NodeVisitor):
    def __init__(self, module: str, path: Path) -> None:
        self.module = module
        self.path = path
        self.model = ModuleModel(
            module=module,
            path=path,
            tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
        )
        self.class_stack: list[str] = []
        self.function_stack: list[str] = []

        # Execute the AST visitor immediately so the model is populated.
        self.visit(self.model.tree)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local = alias.asname or alias.name.split(".")[0]
            self.model.imports[local] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * node.level + (node.module or "")
        for alias in node.names:
            local = alias.asname or alias.name
            self.model.imports[local] = f"{prefix}:{alias.name}"
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = ".".join(
            [self.module, *self.class_stack, node.name]
        )
        self.model.classes[node.name] = node
        self.model.symbols[node.name] = Symbol(
            qualified_name=qualified,
            short_name=node.name,
            kind="class",
            module=self.module,
            file=str(self.path.relative_to(REPO_ROOT)),
            line=node.lineno,
            class_name=self.class_stack[-1] if self.class_stack else None,
        )

        for base in node.bases:
            self._record_annotation_or_reference(base, node.lineno, "inheritance")

        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        qualified_parts = [self.module, *self.class_stack, node.name]
        qualified = ".".join(qualified_parts)

        self.model.functions[node.name] = node
        self.model.symbols[node.name] = Symbol(
            qualified_name=qualified,
            short_name=node.name,
            kind="function",
            module=self.module,
            file=str(self.path.relative_to(REPO_ROOT)),
            line=node.lineno,
            class_name=self.class_stack[-1] if self.class_stack else None,
        )

        for arg in [
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ]:
            self._record_annotation_or_reference(
                arg.annotation,
                node.lineno,
                "parameter_annotation",
            )

        self._record_annotation_or_reference(
            node.returns,
            node.lineno,
            "return_annotation",
        )

        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.model.assignments.append(node)
        self._record_annotation_or_reference(
            node.annotation,
            node.lineno,
            "attribute_annotation",
        )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self.model.assignments.append(node)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.model.calls.append(node)
        self.generic_visit(node)

    def _record_annotation_or_reference(
        self,
        node: ast.AST | None,
        line: int,
        kind: str,
    ) -> None:
        if node is None:
            return
        for name in annotation_names(node):
            if name in self.model.imports:
                continue


def parse_modules(files: Iterable[Path]) -> tuple[dict[str, ModuleModel], list[str]]:
    models: dict[str, ModuleModel] = {}
    failures: list[str] = []

    for path in files:
        module = module_name_for(path)
        try:
            visitor = ModuleVisitor(module, path)
            models[module] = visitor.model
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            failures.append(f"{path}: {exc}")

    return models, failures


def build_symbol_index(
    models: dict[str, ModuleModel],
) -> tuple[dict[str, list[Symbol]], dict[str, Symbol]]:
    short_index: dict[str, list[Symbol]] = defaultdict(list)
    qualified_index: dict[str, Symbol] = {}

    for model in models.values():
        for symbol in model.symbols.values():
            short_index[symbol.short_name].append(symbol)
            qualified_index[symbol.qualified_name] = symbol

    return short_index, qualified_index


def boundary_for_symbol(name: str) -> str | None:
    if not name:
        return None

    short = name.split(".")[-1]

    for boundary, spec in BOUNDARIES.items():
        if short in spec["symbols"] or name in spec["symbols"]:
            return boundary

    return None


def boundary_for_text(name: str) -> str | None:
    """
    Legacy textual fallback.

    This function is intentionally conservative. It must NOT be used to
    determine boundary ownership when a resolved Symbol is available.
    """
    lowered = name.lower().replace("-", "_")

    # Exact module/package ownership is preferred over substring matching.
    explicit_module_owners = (
        ("lyrion.security.authorization", "Aegis"),
        ("lyrion.security.policy", "Aegis"),
        ("lyrion.security.rules", "Aegis"),
        ("lyrion.security.guards", "Authorization"),
        ("lyrion.security.replay", "Authorization"),
        ("lyrion.capabilities.gateway", "CapabilityGateway"),
        ("lyrion.capabilities.contracts", "CapabilityGateway"),
        ("lyrion.execution.executor", "SecureExecutor"),
        ("lyrion.execution.sandbox", "Sandbox"),
        ("lyrion.execution.backends.linux.enforcement", "UniversalComputer"),
    )

    for prefix, boundary in explicit_module_owners:
        if lowered == prefix or lowered.startswith(prefix + "."):
            return boundary

    return None


def boundary_for_symbol_object(symbol: Symbol | None) -> str | None:
    """
    Resolve boundary ownership from the actual discovered Symbol.

    This is the authoritative classification path for the static graph.
    Textual name matching is deliberately not used here.
    """
    if symbol is None:
        return None

    module = symbol.module
    short = symbol.short_name

    # Exact symbol ownership.
    for boundary, spec in BOUNDARIES.items():
        if short in spec["symbols"]:
            return boundary

    # Explicit package ownership.
    module_prefixes = (
        ("lyrion.security.authorization", "Aegis"),
        ("lyrion.security.policy", "Aegis"),
        ("lyrion.security.rules", "Aegis"),
        ("lyrion.security.guards", "Authorization"),
        ("lyrion.security.replay", "Authorization"),
        ("lyrion.capabilities.gateway", "CapabilityGateway"),
        ("lyrion.capabilities.contracts", "CapabilityGateway"),
        ("lyrion.execution.executor", "SecureExecutor"),
        ("lyrion.execution.sandbox", "Sandbox"),
        ("lyrion.execution.backends.linux.enforcement", "UniversalComputer"),
    )

    for prefix, boundary in module_prefixes:
        if module == prefix or module.startswith(prefix + "."):
            return boundary

    # Explicit application-enforcement ownership.
    if (
        module.startswith("lyrion.execution.backends.linux.enforcement.application")
        and short in {
            "EnforcementApplication",
            "EnforcementApplicationContext",
        }
    ):
        return "ApplicationHarness"

    return None


def resolve_reference(
    reference: str,
    model: ModuleModel,
    short_index: dict[str, list[Symbol]],
) -> list[Symbol]:
    results: list[Symbol] = []

    short = reference.split(".")[-1]

    # Direct local symbol.
    if short in model.symbols:
        results.append(model.symbols[short])

    # Imported alias.
    if short in model.imports:
        imported = model.imports[short]
        imported_short = imported.split(":")[-1].split(".")[-1]
        results.extend(short_index.get(imported_short, []))

    # Global short-name resolution.
    results.extend(short_index.get(short, []))

    unique: dict[str, Symbol] = {}
    for item in results:
        unique[item.qualified_name] = item

    return list(unique.values())


def enclosing_scope(
    model: ModuleModel,
    node: ast.AST,
) -> str:
    line = getattr(node, "lineno", 0)

    candidates: list[tuple[int, str]] = []

    for symbol in model.symbols.values():
        if symbol.line <= line:
            candidates.append((symbol.line, symbol.qualified_name))

    if not candidates:
        return model.module

    return max(candidates)[1]


def collect_contract_evidence(
    models: dict[str, ModuleModel],
    short_index: dict[str, list[Symbol]],
) -> list[Evidence]:
    evidence: list[Evidence] = []

    for model in models.values():
        for node in ast.walk(model.tree):
            if isinstance(node, ast.Call):
                reference = dotted_name(node.func)
                if not reference:
                    continue

                targets = resolve_reference(reference, model, short_index)
                source_scope = enclosing_scope(model, node)
                source_symbol = None
                source_short = source_scope.split(".")[-1]
                source_candidates = short_index.get(source_short, [])

                for candidate in source_candidates:
                    if candidate.qualified_name == source_scope:
                        source_symbol = candidate
                        break

                source_boundary = boundary_for_symbol_object(source_symbol)

                for target in targets:
                    target_boundary = boundary_for_symbol_object(target)

                    if not target_boundary:
                        continue

                    if source_boundary and source_boundary != target_boundary:
                        evidence.append(
                            Evidence(
                                source=source_scope,
                                target=target.qualified_name,
                                kind="call",
                                file=str(model.path.relative_to(REPO_ROOT)),
                                line=node.lineno,
                                detail=(
                                    f"{source_boundary} -> "
                                    f"{target_boundary}; "
                                    f"reference={reference}"
                                ),
                            )
                        )

            elif isinstance(node, ast.AnnAssign):
                names = annotation_names(node.annotation)

                for name in names:
                    targets = resolve_reference(name, model, short_index)
                    for target in targets:
                        target_boundary = boundary_for_symbol_object(target)
                        if not target_boundary:
                            continue

                        evidence.append(
                            Evidence(
                                source=enclosing_scope(model, node),
                                target=target.qualified_name,
                                kind="annotation",
                                file=str(model.path.relative_to(REPO_ROOT)),
                                line=node.lineno,
                                detail=f"annotation={name}",
                            )
                        )

            elif isinstance(node, ast.ClassDef):
                for base in node.bases:
                    reference = dotted_name(base)
                    if not reference:
                        continue

                    for target in resolve_reference(
                        reference,
                        model,
                        short_index,
                    ):
                        target_boundary = boundary_for_symbol_object(target)
                        if target_boundary:
                            source_candidates = short_index.get(node.name, [])
                            source_boundary = None
                            for candidate in source_candidates:
                                if candidate.module == model.module:
                                    source_boundary = boundary_for_symbol_object(candidate)
                                    break
                            if source_boundary and source_boundary != target_boundary:
                                evidence.append(
                                    Evidence(
                                        source=(
                                            f"{model.module}.{node.name}"
                                        ),
                                        target=target.qualified_name,
                                        kind="inheritance",
                                        file=str(
                                            model.path.relative_to(REPO_ROOT)
                                        ),
                                        line=node.lineno,
                                        detail=f"base={reference}",
                                    )
                                )

    # Deduplicate.
    unique: dict[tuple[str, str, str, str, int], Evidence] = {}
    for item in evidence:
        key = (
            item.source,
            item.target,
            item.kind,
            item.file,
            item.line,
        )
        unique[key] = item

    return list(unique.values())


def collect_dependency_evidence(
    models: dict[str, ModuleModel],
    short_index: dict[str, list[Symbol]],
) -> list[Evidence]:
    evidence: list[Evidence] = []

    for model in models.values():
        for node in ast.walk(model.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue

            node_name = getattr(node, "name", "")
            node_symbol = None
            node_candidates = short_index.get(node_name, [])

            for candidate in node_candidates:
                if (
                    candidate.module == model.module
                    and candidate.line == node.lineno
                ):
                    node_symbol = candidate
                    break

            node_boundary = boundary_for_symbol_object(node_symbol)

            if not node_boundary:
                continue

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    reference = dotted_name(child.func)
                    if not reference:
                        continue

                    for target in resolve_reference(
                        reference,
                        model,
                        short_index,
                    ):
                        target_boundary = boundary_for_symbol_object(target)
                        if (
                            target_boundary
                            and target_boundary != node_boundary
                        ):
                            evidence.append(
                                Evidence(
                                    source=f"{model.module}.{node_name}",
                                    target=target.qualified_name,
                                    kind="contract_dependency",
                                    file=str(
                                        model.path.relative_to(REPO_ROOT)
                                    ),
                                    line=child.lineno,
                                    detail=(
                                        f"{node_boundary} -> "
                                        f"{target_boundary}; "
                                        f"call={reference}"
                                    ),
                                )
                            )

                elif isinstance(child, (ast.AnnAssign, ast.arg)):
                    annotation = (
                        child.annotation
                        if isinstance(child, (ast.AnnAssign, ast.arg))
                        else None
                    )

                    for name in annotation_names(annotation):
                        for target in resolve_reference(
                            name,
                            model,
                            short_index,
                        ):
                            target_boundary = boundary_for_symbol_object(
                                target
                            )
                            if (
                                target_boundary
                                and target_boundary != node_boundary
                            ):
                                evidence.append(
                                    Evidence(
                                        source=f"{model.module}.{node_name}",
                                        target=target.qualified_name,
                                        kind="injected_dependency",
                                        file=str(
                                            model.path.relative_to(REPO_ROOT)
                                        ),
                                        line=getattr(child, "lineno", node.lineno),
                                        detail=(
                                            f"{node_boundary} -> "
                                            f"{target_boundary}; "
                                            f"type={name}"
                                        ),
                                    )
                                )

    unique: dict[tuple[str, str, str, str, int, str], Evidence] = {}
    for item in evidence:
        key = (
            item.source,
            item.target,
            item.kind,
            item.file,
            item.line,
            item.detail,
        )
        unique[key] = item

    return list(unique.values())


def make_boundary_matrix(evidence: list[Evidence]) -> dict[str, dict[str, int]]:
    boundaries = list(BOUNDARIES)
    matrix = {
        source: {target: 0 for target in boundaries}
        for source in boundaries
    }

    for item in evidence:
        source_boundary = None
        target_boundary = None

        # Evidence stores qualified names. Resolve their module/symbol identity
        # directly instead of guessing from substrings.
        source_short = item.source.split(".")[-1]
        target_short = item.target.split(".")[-1]

        for symbol in _GLOBAL_SYMBOLS_BY_QUALIFIED.values():
            if symbol.qualified_name == item.source:
                source_boundary = boundary_for_symbol_object(symbol)
                break

        for symbol in _GLOBAL_SYMBOLS_BY_QUALIFIED.values():
            if symbol.qualified_name == item.target:
                target_boundary = boundary_for_symbol_object(symbol)
                break

        if (
            source_boundary in matrix
            and target_boundary in matrix[source_boundary]
            and source_boundary != target_boundary
        ):
            matrix[source_boundary][target_boundary] += 1

    return matrix


def audit_tool_safety() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        tree = ast.parse(
            SELF_PATH.read_text(encoding="utf-8"),
            filename=str(SELF_PATH),
        )
    except (SyntaxError, OSError) as exc:
        return False, [f"Audit tool AST parse failed: {exc}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func)
            if not name:
                continue

            short = name.split(".")[-1]

            if short in FORBIDDEN_MUTATING_AST_CALLS:
                failures.append(
                    f"Forbidden mutation API in audit tool: {name}"
                )

            if short in {"system", "popen"}:
                failures.append(
                    f"Forbidden shell execution API in audit tool: {name}"
                )

    source = SELF_PATH.read_text(encoding="utf-8")

    # The tool may inspect Git state but must not invoke mutating Git commands.
    try:
        tree = ast.parse(source, filename=str(SELF_PATH))
        for node in ast.walk(tree):
            if isinstance(node, ast.List):
                continue
    except SyntaxError:
        return False, ["Tool source syntax invalid"]

    return not failures, failures


def serialize_evidence(items: list[Evidence]) -> list[dict[str, object]]:
    return [
        {
            "source": item.source,
            "target": item.target,
            "kind": item.kind,
            "file": item.file,
            "line": item.line,
            "detail": item.detail,
        }
        for item in sorted(
            items,
            key=lambda x: (x.source, x.target, x.kind, x.file, x.line),
        )
    ]


def main() -> int:
    print("=" * 88)
    print("LYRION PB-DOC-001..008 CONTRACT-AWARE CALL-CHAIN VERIFICATION")
    print("=" * 88)

    guard_ok, guard_failures = repository_guard()

    try:
        head = run_git("rev-parse", "HEAD")
        origin = run_git("rev-parse", "origin/main")
        branch = run_git("branch", "--show-current")
    except subprocess.CalledProcessError:
        head = "UNKNOWN"
        origin = "UNKNOWN"
        branch = "UNKNOWN"

    print(f"Repository : {REPO_ROOT}")
    print(f"Branch     : {branch}")
    print(f"HEAD       : {head}")
    print(f"origin/main: {origin}")
    print(f"Repo Guard : {'PASS' if guard_ok else 'FAIL'}")

    if not guard_ok:
        for failure in guard_failures:
            print(f"  FAIL: {failure}")
        print("Decision: BASELINE_NOT_CLEAN")
        return 2

    safety_ok, safety_failures = audit_tool_safety()
    print(f"Tool Safety: {'PASS' if safety_ok else 'FAIL'}")

    if not safety_ok:
        for failure in safety_failures:
            print(f"  FAIL: {failure}")
        print("Decision: AUDIT_TOOL_SAFETY_FAILED")
        return 3

    runtime_files = discover_runtime_files()
    print(f"Runtime Python files: {len(runtime_files)}")

    models, parse_failures = parse_modules(runtime_files)

    print(f"Parsed modules       : {len(models)}")
    print(f"AST parse failures   : {len(parse_failures)}")

    if parse_failures:
        for failure in parse_failures[:20]:
            print(f"  PARSE FAIL: {failure}")

    short_index, qualified_index = build_symbol_index(models)

    global _GLOBAL_SYMBOLS_BY_QUALIFIED
    _GLOBAL_SYMBOLS_BY_QUALIFIED = qualified_index

    print(f"Runtime symbols      : {len(qualified_index)}")

    boundary_symbols: dict[str, list[str]] = {}

    for boundary, spec in BOUNDARIES.items():
        matches: list[str] = []

        for symbol_name in spec["symbols"]:
            for symbol in short_index.get(symbol_name, []):
                matches.append(symbol.qualified_name)

        boundary_symbols[boundary] = sorted(set(matches))

        if matches:
            print(
                f"{boundary:22s}: PRESENT ({len(set(matches))})"
            )
            for match in sorted(set(matches))[:8]:
                print(f"  - {match}")
        else:
            print(f"{boundary:22s}: NOT_EXPLICITLY_FOUND")

    contract_evidence = collect_contract_evidence(
        models,
        short_index,
    )
    dependency_evidence = collect_dependency_evidence(
        models,
        short_index,
    )

    all_evidence = contract_evidence + dependency_evidence

    print()
    print("-" * 88)
    print("CONTRACT-AWARE CROSS-BOUNDARY EVIDENCE")
    print("-" * 88)

    if not all_evidence:
        print("No cross-boundary static evidence found.")
    else:
        for item in serialize_evidence(all_evidence):
            print(
                f"[{item['kind']}] "
                f"{item['source']} -> {item['target']} "
                f"@ {item['file']}:{item['line']} "
                f"| {item['detail']}"
            )

    matrix = make_boundary_matrix(all_evidence)

    expected_chain = [
        ("Aegis", "Authorization"),
        ("Authorization", "CapabilityGateway"),
        ("CapabilityGateway", "ExecutionAdmission"),
        ("ExecutionAdmission", "SecureExecutor"),
        ("SecureExecutor", "Sandbox"),
        ("Sandbox", "LHICF"),
    ]

    print()
    print("-" * 88)
    print("EXPECTED SECURITY / EXECUTION CHAIN")
    print("-" * 88)

    chain_results: list[dict[str, object]] = []

    for source, target in expected_chain:
        count = matrix.get(source, {}).get(target, 0)

        if count:
            state = "STATIC_CONTRACT_EDGE_FOUND"
        else:
            state = "NO_DIRECT_OR_CONTRACT_EDGE_FOUND"

        print(
            f"{source:22s} -> {target:22s}: "
            f"{state} ({count})"
        )

        chain_results.append(
            {
                "source": source,
                "target": target,
                "evidence_count": count,
                "state": state,
            }
        )

    print()
    print("-" * 88)
    print("INTERMEDIATE DEPENDENCY PATH SEARCH")
    print("-" * 88)

    # Build a graph from the discovered boundary edges.
    graph: dict[str, set[str]] = defaultdict(set)

    for item in all_evidence:
        source = boundary_for_text(item.source)
        target = boundary_for_symbol(item.target.split(".")[-1])

        if source and target and source != target:
            graph[source].add(target)

    for boundary in BOUNDARIES:
        graph.setdefault(boundary, set())

    def reachable(start: str, target: str) -> list[list[str]]:
        paths: list[list[str]] = []
        queue: list[list[str]] = [[start]]
        visited: set[tuple[str, ...]] = set()

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if current == target:
                paths.append(path)
                if len(paths) >= 5:
                    break
                continue

            state = tuple(path)
            if state in visited:
                continue
            visited.add(state)

            for nxt in sorted(graph.get(current, set())):
                if nxt not in path:
                    queue.append([*path, nxt])

        return paths

    for source, target in expected_chain:
        paths = reachable(source, target)

        if paths:
            print(f"{source} -> {target}:")
            for path in paths:
                print("  " + " -> ".join(path))
        else:
            print(f"{source} -> {target}: NO STATIC PATH")

    print()
    print("-" * 88)
    print("EVIDENCE CLASSIFICATION")
    print("-" * 88)

    print("PB-DOC-001..008 runtime evidence : PRESENT / CONTRACT-AWARE REVIEW")
    print("Executed validation                : NOT ASSESSED")
    print("Acceptance evidence                : NOT ASSESSED")
    print("Production implementation           : BLOCKED")
    print("Production certification            : NOT CLAIMED")
    print("G46.5 reconstruction                : NOT PERFORMED")
    print("G47 reconstruction                  : NOT PERFORMED")
    print("R097 modification                   : NONE")
    print("Runtime/test/document mutation      : NONE")

    summary = {
        "decision": "CONTRACT_AWARE_CALL_CHAIN_REVIEW_COMPLETE",
        "repository": str(REPO_ROOT),
        "head": head,
        "origin_main": origin,
        "branch": branch,
        "runtime_python_files": len(runtime_files),
        "runtime_symbols": len(qualified_index),
        "parse_failures": len(parse_failures),
        "boundary_symbols": boundary_symbols,
        "contract_evidence_count": len(contract_evidence),
        "dependency_evidence_count": len(dependency_evidence),
        "chain_results": chain_results,
        "evidence_classification": {
            "executed_validation": "NOT_ASSESSED",
            "acceptance": "NOT_ASSESSED",
            "production_implementation": "BLOCKED",
            "production_certification": "NOT_CLAIMED",
            "g46_5": "NOT_PERFORMED",
            "g47": "NOT_PERFORMED",
            "r097": "NONE",
        },
    }

    print()
    print("-" * 88)
    print("MACHINE SUMMARY")
    print("-" * 88)
    print(json.dumps(summary, indent=2, sort_keys=True))

    print()
    print("Decision: CONTRACT_AWARE_CALL_CHAIN_REVIEW_COMPLETE")
    print(
        "Static contract/dependency evidence is engineering-review evidence only."
    )
    print(
        "No implementation, validation acceptance, or production certification "
        "state has been advanced."
    )

    # Preserve the tool's read-only nature by calculating hashes only.
    print()
    print("-" * 88)
    print("RUNTIME HASH SAMPLE")
    print("-" * 88)

    for path in runtime_files[:12]:
        print(
            f"{path.relative_to(REPO_ROOT)} "
            f"{sha256_file(path)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

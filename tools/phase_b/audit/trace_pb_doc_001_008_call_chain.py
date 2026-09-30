#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-001..008 Call-Chain Verification

Purpose
-------
Read-only architectural verification of the existing repository implementation
surface for the PB-DOC-001..008 boundaries.

This tool:
- parses repository-owned Python source with AST;
- discovers classes/functions/methods;
- traces direct symbol references and direct call relationships;
- evaluates the expected security/execution chain;
- reports missing/ambiguous boundaries conservatively;
- never modifies runtime source, tests, documentation, manifests, evidence,
  G46.5/G47 artifacts, R097 artifacts, or Git state.

Important:
-----------
Symbol presence or static call relationships are NOT runtime validation.
This tool does not establish:
- production correctness;
- successful execution;
- acceptance;
- certification;
- recovered G46.5/G47 evidence.

It is an engineering-review aid only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


REPO = Path("/home/aniket/lyrion-migration-verified")
SRC_ROOT = REPO / "src"
TEST_ROOT = REPO / "tests"

SELF_PATH = "tools/phase_b/audit/trace_pb_doc_001_008_call_chain.py"

ALLOWED_AUDIT_PATHS = {
    SELF_PATH,
    "tools/phase_b/audit/review_pb_doc_001_008_implementation_gap.py",
    "tools/phase_b/audit/review_pb_doc_001_008_semantic_gap.py",
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

FORBIDDEN_MUTATION_TERMS = {
    "write_text",
    "write_bytes",
    "unlink",
    "rmtree",
    "remove(",
    "rename(",
    "replace(",
    "git add",
    "git commit",
    "git push",
    "git reset",
    "git checkout",
    "git clean",
}


@dataclass(frozen=True)
class Symbol:
    qualified_name: str
    kind: str
    path: str
    lineno: int
    owner: str | None = None


@dataclass(frozen=True)
class Edge:
    caller: str
    callee_text: str
    path: str
    lineno: int


@dataclass(frozen=True)
class BoundaryResult:
    name: str
    found_symbols: tuple[str, ...]
    referenced_by: tuple[str, ...]
    calls_to: tuple[str, ...]
    status: str
    notes: tuple[str, ...]


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    files: list[Path] = []
    for path in root.rglob("*.py"):
        rel = relative(path)
        parts = set(path.parts)
        if parts.intersection(FORBIDDEN_PATH_PARTS):
            continue
        if rel.startswith("NOT_USABLE_DOCUMENTS/"):
            continue
        files.append(path)

    return sorted(files)


def parse_file(path: Path) -> ast.Module | None:
    try:
        return ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
    except (OSError, UnicodeError, SyntaxError):
        return None


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr

    return None


def collect_symbols(
    path: Path,
    tree: ast.Module,
) -> list[Symbol]:
    result: list[Symbol] = []

    module = relative(path)

    def visit_body(
        body: Iterable[ast.stmt],
        owner: str | None = None,
    ) -> None:
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = (
                    "class"
                    if isinstance(node, ast.ClassDef)
                    else "function"
                )

                qualified = node.name
                if owner:
                    qualified = f"{owner}.{node.name}"

                result.append(
                    Symbol(
                        qualified_name=qualified,
                        kind=kind,
                        path=module,
                        lineno=node.lineno,
                        owner=owner,
                    )
                )

                if isinstance(node, ast.ClassDef):
                    visit_body(node.body, qualified)

    visit_body(tree.body)
    return result


def collect_edges(
    path: Path,
    tree: ast.Module,
    symbols: list[Symbol],
) -> list[Edge]:
    result: list[Edge] = []
    module = relative(path)

    owners_by_line: list[tuple[int, int, str]] = []

    for symbol in symbols:
        start = symbol.lineno
        end = start

        # The exact end line is intentionally not inferred from source ranges.
        # We instead use AST parent traversal below for reliable ownership.
        owners_by_line.append((start, end, symbol.qualified_name))

    class_function_stack: list[str] = []

    class EdgeVisitor(ast.NodeVisitor):
        def _visit_callable(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            class EdgeNestedVisitor(ast.NodeVisitor):
                def visit_Call(self, call: ast.Call) -> None:
                    target = dotted_name(call.func)
                    if target:
                        caller = (
                            ".".join(caller_stack)
                            if class_function_stack
                            else "<module>"
                        )
                        result.append(
                            Edge(
                                caller=caller,
                                callee_text=target,
                                path=module,
                                lineno=call.lineno,
                            )
                        )
                    self.generic_visit(call)

            caller_stack = list(class_function_stack_global)
            caller_stack.append(node.name)

            EdgeNestedVisitor().visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            class_function_stack_global.append(node.name)
            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    self._visit_callable(child)
                elif isinstance(child, ast.ClassDef):
                    self.visit(child)
            class_function_stack_global.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_callable(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_callable(node)

    class_function_stack_global: list[str] = []
    EdgeVisitor().visit(tree)

    return result


def normalize(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


def symbol_matches(symbol: Symbol, terms: tuple[str, ...]) -> bool:
    candidate = normalize(symbol.qualified_name)
    return any(normalize(term) in candidate for term in terms)


def edge_matches(edge: Edge, terms: tuple[str, ...]) -> bool:
    candidate = normalize(edge.callee_text)
    return any(normalize(term) in candidate for term in terms)


def collect_repository_surface() -> tuple[list[Symbol], list[Edge], int, int]:
    symbols: list[Symbol] = []
    edges: list[Edge] = []
    parse_failures = 0
    file_count = 0

    for path in python_files(SRC_ROOT):
        file_count += 1
        tree = parse_file(path)
        if tree is None:
            parse_failures += 1
            continue

        file_symbols = collect_symbols(path, tree)
        symbols.extend(file_symbols)
        edges.extend(collect_edges(path, tree, file_symbols))

    return symbols, edges, file_count, parse_failures


def mutation_guard() -> tuple[bool, list[str]]:
    status = run_git(
        "status",
        "--short",
        "--untracked-files=all",
    )

    unexpected: list[str] = []

    if not status:
        return True, unexpected

    for line in status.splitlines():
        path = line[3:].strip()
        if path not in ALLOWED_AUDIT_PATHS:
            unexpected.append(line)

    return not unexpected, unexpected


def verify_tool_source_safety() -> tuple[bool, list[str]]:
    """
    Verify the audit tool structurally rather than searching its source text.

    Forbidden operation names may legitimately appear inside the safety
    policy itself, so string matching would produce false positives.
    """
    path = REPO / SELF_PATH

    if not path.exists():
        return False, ["Call-chain tool does not exist."]

    try:
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
    except (OSError, UnicodeError, SyntaxError) as exc:
        return False, [f"Unable to parse audit tool: {exc}"]

    violations: list[str] = []

    forbidden_calls = {
        "write_text",
        "write_bytes",
        "unlink",
        "rmtree",
        "remove",
        "rename",
        "replace",
        "commit",
        "push",
        "reset",
        "checkout",
        "clean",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = dotted_name(node.func)

            if not target:
                continue

            terminal = target.rsplit(".", 1)[-1]

            if terminal in forbidden_calls:
                violations.append(
                    f"forbidden call: {target} at line {node.lineno}"
                )

    return not violations, sorted(set(violations))


# ---------------------------------------------------------------------------
# Expected architecture
# ---------------------------------------------------------------------------

BOUNDARIES: dict[str, tuple[str, ...]] = {
    "Aegis": (
        "AegisAuthorizationService",
        "AegisPolicyEvaluator",
        "AegisPolicy",
        "AegisRuleEvaluator",
    ),
    "Authorization": (
        "AuthorizationGuard",
        "ReplayGuard",
        "AuthorizationDecision",
        "AuthorizationResult",
        "validate_authorization_state",
        "validate_authorization_expiry",
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
        "SandboxPolicyEvaluator",
        "SandboxPolicy",
        "SandboxConfig",
    ),
    "AgentHarness": (
        "AgentHarness",
        "AgentRuntime",
        "AgentIdentity",
        "AgentLifecycle",
    ),
    "HostHarness": (
        "HostHarness",
        "HostAdapter",
        "HostContext",
        "HostOperation",
    ),
    "UniversalComputer": (
        "UniversalComputer",
        "UniversalComputerOperation",
        "UniversalOperation",
        "PrimitiveAdapter",
        "EnvironmentPlan",
    ),
    "ApplicationHarness": (
        "ApplicationHarness",
        "ApplicationAdapter",
        "ApplicationIdentity",
        "ApplicationContext",
        "ApplicationCapability",
    ),
    "LHICF": (
        "LHICF",
        "HostIntegration",
        "HostControl",
        "HostIntegrationControl",
        "HostIntegrationFabric",
    ),
}


CHAIN: tuple[str, ...] = (
    "Aegis",
    "Authorization",
    "CapabilityGateway",
    "ExecutionAdmission",
    "SecureExecutor",
    "Sandbox",
    "LHICF",
)


CHAIN_REQUIRED_REFERENCES: dict[str, tuple[str, ...]] = {
    "Aegis": (
        "authorization",
        "policy",
        "guard",
        "replay",
    ),
    "Authorization": (
        "CapabilityGateway",
        "ExecutionAdmission",
        "authorization",
    ),
    "CapabilityGateway": (
        "ExecutionAdmission",
        "SecureExecutor",
        "validator",
    ),
    "ExecutionAdmission": (
        "SecureExecutor",
        "validate",
    ),
    "SecureExecutor": (
        "sandbox",
        "execution",
        "audit",
    ),
    "Sandbox": (
        "sandbox",
        "execution",
    ),
    "LHICF": (
        "host",
        "adapter",
        "execution",
    ),
}


def boundary_results(
    symbols: list[Symbol],
    edges: list[Edge],
) -> list[BoundaryResult]:
    results: list[BoundaryResult] = []

    for boundary, terms in BOUNDARIES.items():
        found = [
            symbol.qualified_name
            for symbol in symbols
            if symbol_matches(symbol, terms)
        ]

        relevant_callers: set[str] = set()
        relevant_callees: set[str] = set()

        for edge in edges:
            if any(normalize(term) in normalize(edge.callee_text) for term in terms):
                relevant_callers.add(
                    f"{edge.caller} @ {edge.path}:{edge.lineno}"
                )

            if any(
                normalize(term) in normalize(edge.caller)
                for term in terms
            ):
                relevant_callees.add(edge.callee_text)

        notes: list[str] = []

        if not found:
            status = "NOT_FOUND"
            notes.append(
                "No matching source symbol was found for the configured "
                "boundary vocabulary."
            )
        else:
            status = "SYMBOL_PRESENT"
            notes.append(
                "Static symbol presence only; semantic correctness is not "
                "established."
            )

        results.append(
            BoundaryResult(
                name=boundary,
                found_symbols=tuple(found[:20]),
                referenced_by=tuple(sorted(relevant_callers)[:30]),
                calls_to=tuple(sorted(relevant_callees)[:30]),
                status=status,
                notes=tuple(notes),
            )
        )

    return results


def chain_edges(
    edges: list[Edge],
    symbols: list[Symbol],
) -> list[dict[str, object]]:
    symbol_names = [symbol.qualified_name for symbol in symbols]

    output: list[dict[str, object]] = []

    for source, target in zip(CHAIN, CHAIN[1:]):
        source_terms = BOUNDARIES[source]
        target_terms = BOUNDARIES[target]

        source_symbols = [
            name
            for name in symbol_names
            if any(normalize(t) in normalize(name) for t in source_terms)
        ]

        target_terms_normalized = tuple(normalize(t) for t in target_terms)

        references: list[dict[str, object]] = []

        for edge in edges:
            caller_norm = normalize(edge.caller)

            if not any(
                normalize(source_term) in caller_norm
                for source_term in source_terms
            ):
                continue

            if not any(
                term in normalize(edge.callee_text)
                for term in target_terms_normalized
            ):
                continue

            references.append(
                {
                    "caller": edge.caller,
                    "callee": edge.callee_text,
                    "path": edge.path,
                    "line": edge.lineno,
                }
            )

        output.append(
            {
                "source": source,
                "target": target,
                "source_symbols": source_symbols[:20],
                "direct_static_edges": references[:50],
                "status": (
                    "DIRECT_STATIC_EDGE_FOUND"
                    if references
                    else "NO_DIRECT_STATIC_EDGE_FOUND"
                ),
            }
        )

    return output


def print_boundary(result: BoundaryResult) -> None:
    print(f"\n{result.name}")
    print("-" * len(result.name))
    print(f"Status: {result.status}")

    if result.found_symbols:
        print("Symbols:")
        for item in result.found_symbols:
            print(f"  - {item}")
    else:
        print("Symbols: NONE")

    if result.referenced_by:
        print("Referenced by:")
        for item in result.referenced_by[:10]:
            print(f"  - {item}")

    if result.calls_to:
        print("Calls to:")
        for item in result.calls_to[:10]:
            print(f"  - {item}")

    for note in result.notes:
        print(f"Note: {note}")


def main() -> int:
    print("=" * 90)
    print("LYRION TRUE AGENTIC OS — PB-DOC-001..008 CALL-CHAIN VERIFICATION")
    print("=" * 90)

    if not REPO.exists():
        print(f"FAIL: repository does not exist: {REPO}")
        return 2

    print("\n[1] Repository safety baseline")
    print(f"Repository : {REPO}")

    head = run_git("rev-parse", "HEAD")
    origin = run_git("rev-parse", "origin/main")
    branch = run_git("branch", "--show-current")

    print(f"HEAD       : {head}")
    print(f"Origin     : {origin}")
    print(f"Branch     : {branch}")

    guard_ok, unexpected = mutation_guard()

    # The current audit family intentionally permits its own read-only tools.
    if guard_ok:
        print("Guard      : PASS")
        print(
            "Detail     : Only the PB-DOC-001..008 audit tools are untracked."
        )
    else:
        print("Guard      : FAIL")
        print("Unexpected worktree changes:")
        for item in unexpected:
            print(f"  {item}")
        print("DECISION: BASELINE_NOT_CLEAN")
        return 3

    source_safe, violations = verify_tool_source_safety()

    print("\n[2] Audit-tool safety")
    if source_safe:
        print("Mutation terms: PASS")
    else:
        print("Mutation terms: FAIL")
        for violation in violations:
            print(f"  - {violation}")
        print("DECISION: AUDIT_TOOL_SAFETY_FAILURE")
        return 4

    print("\n[3] Runtime AST inventory")

    symbols, edges, runtime_files, parse_failures = (
        collect_repository_surface()
    )

    print(f"Runtime Python files : {runtime_files}")
    print(f"Runtime symbols      : {len(symbols)}")
    print(f"AST failures         : {parse_failures}")
    print(f"Static call edges    : {len(edges)}")

    if parse_failures:
        print("DECISION: AST_PARSE_FAILURE")
        return 5

    print("\n[4] Boundary inventory")

    results = boundary_results(symbols, edges)

    for result in results:
        print_boundary(result)

    print("\n[5] Security / execution chain")

    chain = chain_edges(edges, symbols)

    for item in chain:
        print(
            f"{item['source']} -> {item['target']} : "
            f"{item['status']}"
        )

        for edge in item["direct_static_edges"][:8]:
            print(
                f"  {edge['caller']} -> {edge['callee']} "
                f"({edge['path']}:{edge['line']})"
            )

    print("\n[6] PB-DOC boundary interpretation")

    pb_doc_notes = {
        "PB-DOC-001": (
            "Requirements/task/intelligence contracts must remain distinct "
            "from execution authority."
        ),
        "PB-DOC-002": (
            "Agent runtime/lifecycle must not itself become an authorization "
            "authority."
        ),
        "PB-DOC-003": (
            "Identity, principal, delegated authority, authorization, "
            "revocation and replay protection must remain explicit."
        ),
        "PB-DOC-004": (
            "Capability discovery/modeling must not enlarge authority."
        ),
        "PB-DOC-005": (
            "Agent Harness must not create an alternate privileged execution "
            "path."
        ),
        "PB-DOC-006": (
            "Host Harness must remain subordinate to the security/execution "
            "chain."
        ),
        "PB-DOC-007": (
            "Universal Computer must consume authority/admission rather than "
            "create authority."
        ),
        "PB-DOC-008": (
            "Application Harness must not bypass Aegis, Capability Gateway, "
            "Execution Admission, Secure Executor, Sandbox or LHICF."
        ),
    }

    for key, note in pb_doc_notes.items():
        print(f"{key}: {note}")

    print("\n[7] Evidence boundary")

    print(
        "Static call-chain evidence : ENGINEERING REVIEW ONLY"
    )
    print(
        "Executed validation        : NOT ASSESSED"
    )
    print(
        "Acceptance evidence        : NOT ASSESSED"
    )
    print(
        "Production implementation  : BLOCKED"
    )
    print(
        "Production certification   : NOT CLAIMED"
    )
    print(
        "G46.5/G47 reconstruction   : NOT PERFORMED"
    )
    print(
        "R097 modification          : NONE"
    )

    print("\n[8] Post-audit safety check")

    final_ok, final_unexpected = mutation_guard()

    if final_ok:
        print(
            "PASS: repository unchanged except for the "
            "PB-DOC-001..008 audit tools."
        )
    else:
        print("FAIL: unexpected worktree mutation detected.")
        for item in final_unexpected:
            print(f"  {item}")
        print("DECISION: POST_AUDIT_MUTATION_DETECTED")
        return 6

    output = {
        "decision": "CALL_CHAIN_VERIFICATION_COMPLETE",
        "head": head,
        "origin": origin,
        "branch": branch,
        "runtime_files": runtime_files,
        "runtime_symbols": len(symbols),
        "ast_failures": parse_failures,
        "static_call_edges": len(edges),
        "boundaries": [asdict(item) for item in results],
        "security_execution_chain": chain,
        "executed_validation": "NOT_ASSESSED",
        "acceptance": "NOT_ASSESSED",
        "production_implementation": "BLOCKED",
        "production_certification": "NOT_CLAIMED",
        "g46_5_g47_reconstruction": "NOT_PERFORMED",
        "r097_modification": "NONE",
    }

    print("\n[9] Machine-readable summary")
    print(json.dumps(output, indent=2, sort_keys=True))

    print("\nDECISION: CALL_CHAIN_VERIFICATION_COMPLETE")
    print(
        "NEXT: engineering review of concrete call-chain edges is required "
        "before selecting a bounded implementation slice."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

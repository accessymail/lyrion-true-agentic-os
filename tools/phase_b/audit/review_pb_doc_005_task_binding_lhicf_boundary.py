#!/usr/bin/env python3
"""
LYRION True Agentic OS
PB-DOC-005 Task Binding + LHICF Boundary Contract Review

READ-ONLY ENGINEERING REVIEW.

Purpose:
    Final narrow review before selecting a PB-DOC-005..008 bounded slice.

    A. Determine whether PB-DOC-005 Task Binding already exists under
       another implementation contract/name.

    B. Determine whether the existing host/enforcement/adapter surface
       already provides the responsibilities required by LHICF.

    C. Determine whether LHICF can be formalized as a boundary contract
       over existing implementation without creating:
           - duplicate host enforcement
           - alternate authorization
           - alternate execution admission
           - privileged bypass
           - duplicate sandbox
           - independent authority

Safety:
    - read-only
    - AST/static analysis only
    - no source/test/docs modification
    - no Git mutation
    - no credentials/secrets
    - no network access
    - no privileged execution
    - no G46.5/G47 reconstruction
    - no R097 modification
    - no production certification claim

Evidence classification:
    FINAL STATIC CONTRACT-BOUNDARY REVIEW ONLY
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

ALLOWED_AUDIT_UNTRACKED = {
    "review_pb_doc_001_008_implementation_gap.py",
    "review_pb_doc_001_008_semantic_gap.py",
    "trace_pb_doc_001_008_call_chain.py",
    "trace_pb_doc_001_008_contract_aware_call_chain.py",
    "trace_pb_doc_001_008_execution_flow.py",
    "map_pb_doc_005_008_architecture_representation.py",
    "map_pb_doc_005_008_contract_responsibilities.py",
    "map_pb_doc_005_008_contract_ownership.py",
    "review_pb_doc_005_task_binding_lhicf_boundary.py",
}


@dataclass(frozen=True)
class Symbol:
    qualified: str
    short: str
    module: str
    kind: str
    file: str
    line: int


@dataclass
class Module:
    name: str
    path: Path
    tree: ast.Module
    symbols: list[Symbol]


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
        failures.append(f"unexpected branch: {branch}")

    status = git(
        "status",
        "--short",
        "--untracked-files=all",
    )

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
    if not TEST_ROOT.exists():
        return []

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
    rel = path.relative_to(SRC_ROOT)
    parts = list(rel.parts)

    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = parts[-1][:-3]

    return ".".join(parts)


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

        self.symbols.append(
            Symbol(
                qualified,
                node.name,
                self.module,
                "class",
                str(self.path.relative_to(REPO_ROOT)),
                node.lineno,
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
                qualified,
                node.name,
                self.module,
                "function",
                str(self.path.relative_to(REPO_ROOT)),
                node.lineno,
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
) -> tuple[list[Module], list[str]]:
    modules: list[Module] = []
    failures: list[str] = []

    for path in paths:
        try:
            visitor = Visitor(
                module_name(path),
                path,
            )

            modules.append(
                Module(
                    visitor.module,
                    path,
                    visitor.tree,
                    visitor.symbols,
                )
            )

        except Exception as exc:
            failures.append(
                f"{path}: {exc}"
            )

    return modules, failures


def all_symbols(
    modules: list[Module],
) -> list[Symbol]:
    result: list[Symbol] = []

    for module in modules:
        result.extend(module.symbols)

    return result


def matches(
    symbols: list[Symbol],
    terms: tuple[str, ...],
) -> list[Symbol]:
    result: dict[str, Symbol] = {}

    for symbol in symbols:
        text = (
            f"{symbol.qualified} "
            f"{symbol.short}"
        ).lower()

        if any(
            term.lower() in text
            for term in terms
        ):
            result[symbol.qualified] = symbol

    return sorted(
        result.values(),
        key=lambda s: (
            s.file,
            s.line,
            s.qualified,
        ),
    )


def test_matches(
    tests: list[Path],
    terms: tuple[str, ...],
) -> list[str]:
    result: list[str] = []

    lowered = tuple(
        term.lower()
        for term in terms
    )

    for path in tests:
        try:
            text = path.read_text(
                encoding="utf-8",
            ).lower()
        except Exception:
            continue

        if any(
            term in text
            for term in lowered
        ):
            result.append(
                str(path.relative_to(REPO_ROOT))
            )

    return sorted(result)


# ---------------------------------------------------------------------------
# A. PB-DOC-005 TASK BINDING
# ---------------------------------------------------------------------------

TASK_BINDING_TERMS = (
    "TaskBinding",
    "TaskContext",
    "TaskManager",
    "TaskExecution",
    "TaskRequest",
    "TaskResult",
    "TaskState",
    "Task",
    "ExecutionRequest",
    "ExecutionAdmission",
    "ExecutionAdmissionEnvelope",
    "PIAE",
)

TASK_BINDING_CONTRACT_TERMS = (
    "TaskBinding",
    "TaskContext",
    "TaskExecution",
    "TaskRequest",
    "TaskResult",
    "TaskState",
    "ExecutionRequest",
    "ExecutionAdmission",
)


def task_binding_analysis(
    symbols: list[Symbol],
    tests: list[Path],
) -> dict:
    runtime = matches(
        symbols,
        TASK_BINDING_TERMS,
    )

    contracts = matches(
        symbols,
        TASK_BINDING_CONTRACT_TERMS,
    )

    test_surface = test_matches(
        tests,
        TASK_BINDING_TERMS,
    )

    modules = sorted(
        {
            symbol.module
            for symbol in runtime
        }
    )

    task_specific = [
        symbol
        for symbol in runtime
        if any(
            term.lower()
            in symbol.short.lower()
            for term in (
                "taskbinding",
                "taskcontext",
                "taskexecution",
                "taskrequest",
                "taskmanager",
            )
        )
    ]

    execution_binding = [
        symbol
        for symbol in runtime
        if any(
            term.lower()
            in symbol.short.lower()
            for term in (
                "executionadmission",
                "executionrequest",
                "executionresult",
            )
        )
    ]

    if task_specific:
        state = "EXPLICIT_OR_NEAR_EXPLICIT_TASK_BINDING"
    elif execution_binding:
        state = (
            "TASK_BINDING_REPRESENTED_BY_EXECUTION_CONTRACTS"
        )
    elif runtime:
        state = "PARTIAL_TASK_BINDING_SURFACE"
    else:
        state = "NO_CONFIRMED_TASK_BINDING"

    return {
        "state": state,
        "runtime_count": len(runtime),
        "contract_count": len(contracts),
        "test_count": len(test_surface),
        "module_count": len(modules),
        "task_specific_count": len(task_specific),
        "execution_binding_count": len(execution_binding),
        "runtime_symbols": [
            symbol.qualified
            for symbol in runtime[:40]
        ],
        "contract_symbols": [
            symbol.qualified
            for symbol in contracts[:40]
        ],
        "tests": test_surface[:40],
        "modules": modules[:40],
    }


# ---------------------------------------------------------------------------
# B. LHICF responsibility surfaces
# ---------------------------------------------------------------------------

LHICF_SURFACES = {
    "identity_and_context": (
        "HostContext",
        "HostIdentity",
        "HostState",
        "ApplicationContext",
        "ApplicationRuntime",
    ),
    "capability_discovery": (
        "HostCapabilityDetector",
        "HostCapabilityProvider",
        "LinuxHostCapabilityDetector",
        "LinuxHostCapabilityProvider",
        "CapabilitySnapshot",
    ),
    "adapter_boundary": (
        "HostAdapter",
        "PrimitiveAdapter",
        "AdapterRegistry",
        "PrimitiveAdapterRegistry",
    ),
    "host_operations": (
        "Filesystem",
        "Process",
        "Service",
        "Network",
        "Application",
        "Desktop",
        "Device",
        "Clipboard",
    ),
    "execution_control": (
        "ExecutionAdmission",
        "SecureExecutor",
        "Sandbox",
        "CapabilityGateway",
    ),
    "host_enforcement": (
        "EnforcementApplication",
        "EnforcementApplicationContext",
        "AppArmor",
        "Cgroup",
        "Seccomp",
        "Namespace",
        "NoNewPrivs",
        "Landlock",
    ),
    "verification_provenance": (
        "Evidence",
        "Provenance",
        "Audit",
        "EnforcementEvidence",
        "Qualification",
    ),
}


def lhicf_surface_analysis(
    symbols: list[Symbol],
    tests: list[Path],
) -> dict:
    result: dict[str, dict] = {}

    for name, terms in LHICF_SURFACES.items():
        runtime = matches(
            symbols,
            terms,
        )

        test_surface = test_matches(
            tests,
            terms,
        )

        result[name] = {
            "runtime_count": len(runtime),
            "test_count": len(test_surface),
            "runtime_symbols": [
                symbol.qualified
                for symbol in runtime[:30]
            ],
            "tests": test_surface[:30],
        }

    return result


# ---------------------------------------------------------------------------
# C. Detect possible authority/execution duplication
# ---------------------------------------------------------------------------

AUTHORITY_TERMS = (
    "AegisAuthorizationService",
    "AuthorizationGuard",
    "CapabilityGateway",
    "ExecutionAdmission",
    "SecureExecutor",
)


def duplication_scan(
    modules: list[Module],
) -> dict:
    result: dict[str, list[str]] = {}

    for module in modules:
        source = module.path.read_text(
            encoding="utf-8",
        ).lower()

        signals: list[str] = []

        if "authorize(" in source:
            signals.append("authorization")

        if "executionadmission" in source:
            signals.append("execution_admission")

        if "secureexecutor" in source:
            signals.append("secure_executor")

        if "sandbox" in source:
            signals.append("sandbox")

        if (
            "subprocess" in source
            or "os.system" in source
            or "create_subprocess" in source
        ):
            signals.append("direct_process_execution_surface")

        if signals:
            result[module.name] = sorted(
                set(signals)
            )

    return result


# ---------------------------------------------------------------------------
# D. Boundary ownership interpretation
# ---------------------------------------------------------------------------

def evaluate_lhicf(
    surfaces: dict[str, dict],
) -> tuple[str, list[str]]:
    present = {
        name
        for name, data in surfaces.items()
        if data["runtime_count"] > 0
    }

    required = {
        "identity_and_context",
        "capability_discovery",
        "adapter_boundary",
        "host_operations",
        "execution_control",
        "host_enforcement",
        "verification_provenance",
    }

    missing = sorted(
        required - present
    )

    if not missing:
        return (
            "IMPLICIT_LHICF_BOUNDARY_CANDIDATE",
            [],
        )

    if len(present) >= 4:
        return (
            "PARTIAL_LHICF_RESPONSIBILITY_SURFACE",
            missing,
        )

    return (
        "INSUFFICIENT_LHICF_REPRESENTATION",
        missing,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 100)
    print(
        "LYRION PB-DOC-005 TASK BINDING + LHICF "
        "BOUNDARY CONTRACT REVIEW"
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

    paths = source_files()
    tests = test_files()

    modules, parse_failures = parse_sources(
        paths,
    )

    symbols = all_symbols(
        modules,
    )

    print()
    print("-" * 100)
    print("SOURCE INVENTORY")
    print("-" * 100)
    print(f"Runtime Python files : {len(paths)}")
    print(f"Runtime modules      : {len(modules)}")
    print(f"Runtime symbols      : {len(symbols)}")
    print(f"Project test files   : {len(tests)}")
    print(f"AST failures         : {len(parse_failures)}")

    if parse_failures:
        for failure in parse_failures[:20]:
            print(f"  PARSE FAIL: {failure}")

        print(
            "Decision: STATIC_ANALYSIS_INCOMPLETE"
        )
        return 3

    # --------------------------------------------------------------
    # Task binding
    # --------------------------------------------------------------

    task = task_binding_analysis(
        symbols,
        tests,
    )

    print()
    print("=" * 100)
    print("PB-DOC-005 TASK BINDING REVIEW")
    print("=" * 100)

    print(f"State                  : {task['state']}")
    print(
        f"Runtime representation : "
        f"{task['runtime_count']}"
    )
    print(
        f"Contract representation: "
        f"{task['contract_count']}"
    )
    print(
        f"Test representation    : "
        f"{task['test_count']}"
    )
    print(
        f"Task-specific symbols  : "
        f"{task['task_specific_count']}"
    )
    print(
        f"Execution binding      : "
        f"{task['execution_binding_count']}"
    )

    print()
    print("Task-related runtime symbols:")

    for value in task["runtime_symbols"][:30]:
        print(f"  - {value}")

    print()
    print("Task-related tests:")

    for value in task["tests"][:30]:
        print(f"  - {value}")

    # --------------------------------------------------------------
    # LHICF
    # --------------------------------------------------------------

    surfaces = lhicf_surface_analysis(
        symbols,
        tests,
    )

    print()
    print("=" * 100)
    print("LHICF RESPONSIBILITY SURFACE REVIEW")
    print("=" * 100)

    for name, data in surfaces.items():
        print()
        print(
            f"{name:28s} "
            f"runtime={data['runtime_count']:3d} "
            f"tests={data['test_count']:3d}"
        )

        for symbol in data["runtime_symbols"][:8]:
            print(
                f"  - {symbol}"
            )

    lhicf_state, missing = evaluate_lhicf(
        surfaces,
    )

    print()
    print(f"LHICF STATE: {lhicf_state}")

    if missing:
        print("Missing responsibility surfaces:")
        for value in missing:
            print(f"  - {value}")

    # --------------------------------------------------------------
    # Explicit LHICF symbols
    # --------------------------------------------------------------

    explicit = matches(
        symbols,
        (
            "LHICF",
            "HostIntegrationControlFabric",
        ),
    )

    print()
    print("=" * 100)
    print("EXPLICIT LHICF SYMBOL CHECK")
    print("=" * 100)

    if explicit:
        print(
            "EXPLICIT LHICF SYMBOLS FOUND:"
        )

        for symbol in explicit:
            print(
                f"  - {symbol.qualified}"
            )
    else:
        print(
            "No explicit LHICF implementation symbol found."
        )

    # --------------------------------------------------------------
    # Protected architecture
    # --------------------------------------------------------------

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

    print()
    print("=" * 100)
    print("PROTECTED SECURITY / EXECUTION BOUNDARY")
    print("=" * 100)

    boundary_counts: dict[str, int] = {}

    for boundary, terms in boundary_terms.items():
        found = matches(
            symbols,
            terms,
        )

        boundary_counts[boundary] = len(
            found
        )

        print(
            f"{boundary:24s}: "
            f"{len(found):3d}"
        )

    # --------------------------------------------------------------
    # Duplication scan
    # --------------------------------------------------------------

    duplication = duplication_scan(
        modules,
    )

    print()
    print("=" * 100)
    print("AUTHORITY / EXECUTION DUPLICATION SIGNALS")
    print("=" * 100)

    suspicious = {
        module: signals
        for module, signals in duplication.items()
        if (
            "direct_process_execution_surface"
            in signals
            and (
                "authorization" in signals
                or "execution_admission" in signals
                or "secure_executor" in signals
            )
        )
    }

    print(
        f"Potential mixed authority/execution modules: "
        f"{len(suspicious)}"
    )

    for module, signals in list(
        sorted(suspicious.items())
    )[:50]:
        print(
            f"  {module}: "
            + ", ".join(signals)
        )

    # --------------------------------------------------------------
    # Final interpretation
    # --------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL CONTRACT-BOUNDARY INTERPRETATION")
    print("=" * 100)

    print(
        "PB-DOC-005 Task Binding:"
    )

    if task["task_specific_count"]:
        print(
            "  Existing task-specific implementation "
            "representation is present."
        )
    elif task["execution_binding_count"]:
        print(
            "  Task binding appears to be represented "
            "through existing execution contracts."
        )
    else:
        print(
            "  No confirmed task-binding representation."
        )

    print()
    print(
        "LHICF:"
    )

    if explicit:
        print(
            "  Explicit LHICF implementation boundary exists."
        )
    elif lhicf_state == (
        "IMPLICIT_LHICF_BOUNDARY_CANDIDATE"
    ):
        print(
            "  Existing host integration responsibilities "
            "form an implicit LHICF candidate."
        )
        print(
            "  Formalization may be possible without "
            "duplicating host enforcement."
        )
    else:
        print(
            "  Existing implementation does not fully "
            "represent the LHICF responsibility set."
        )

    print()
    print(
        "Security invariant:"
    )
    print(
        "  LHICF MUST remain downstream of:"
    )
    print(
        "  Aegis -> Capability Gateway -> Execution Admission "
        "-> Secure Executor -> Sandbox"
    )

    print()
    print(
        "Boundary rule:"
    )
    print(
        "  LHICF may integrate with the host, but must not "
        "become an authorization authority."
    )

    print()
    print(
        "Task Binding rule:"
    )
    print(
        "  Task binding may associate identity, task, authority, "
        "capability and admission context, but must not create "
        "independent execution authority."
    )

    print()
    print(
        "NO IMPLEMENTATION CHANGE IS PERFORMED."
    )

    # --------------------------------------------------------------
    # Evidence boundary
    # --------------------------------------------------------------

    print()
    print("-" * 100)
    print("EVIDENCE BOUNDARY")
    print("-" * 100)
    print(
        "Analysis type                 : "
        "FINAL STATIC CONTRACT-BOUNDARY REVIEW"
    )
    print("Executed validation           : NOT ASSESSED")
    print("Acceptance evidence           : NOT ASSESSED")
    print("Production implementation     : BLOCKED")
    print("Production certification      : NOT CLAIMED")
    print("G46.5 reconstruction          : NOT PERFORMED")
    print("G47 reconstruction            : NOT PERFORMED")
    print("R097 modification             : NONE")
    print("Source/test/document mutation : NONE")

    # --------------------------------------------------------------
    # Machine summary
    # --------------------------------------------------------------

    summary = {
        "decision": (
            "PB_DOC_005_TASK_BINDING_LHICF_BOUNDARY_REVIEW_COMPLETE"
        ),
        "head": head,
        "origin_main": origin,
        "runtime_python_files": len(paths),
        "runtime_modules": len(modules),
        "runtime_symbols": len(symbols),
        "project_test_files": len(tests),
        "parse_failures": len(parse_failures),
        "task_binding": task,
        "lhicf": {
            "explicit_symbols": [
                symbol.qualified
                for symbol in explicit
            ],
            "state": lhicf_state,
            "missing_surfaces": missing,
            "surfaces": surfaces,
        },
        "protected_boundary_counts": boundary_counts,
        "potential_mixed_authority_execution_modules": suspicious,
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
        "PB_DOC_005_TASK_BINDING_LHICF_BOUNDARY_REVIEW_COMPLETE"
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

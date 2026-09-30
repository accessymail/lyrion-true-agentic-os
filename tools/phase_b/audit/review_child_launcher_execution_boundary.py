#!/usr/bin/env python3
"""
LYRION True Agentic OS
Child Launcher Execution Boundary Review

READ-ONLY ENGINEERING REVIEW.

Purpose:
    Determine whether lyrion.execution.process_boundary.child_launcher
    is strictly a downstream execution mechanism or whether it exposes
    an alternate execution/authority path.

Expected architectural path:

    Authorization / Aegis
        ->
    Capability Gateway
        ->
    Execution Admission
        ->
    Secure Executor
        ->
    Sandbox / Enforcement
        ->
    Process Boundary / Child Launcher
        ->
    Host Operation
        ->
    Verification / Provenance

This tool does NOT modify source, tests, documentation, manifests, or Git.

It performs:
    - AST parsing
    - import analysis
    - symbol analysis
    - constructor/parameter contract inspection
    - direct call analysis
    - subprocess/process primitive detection
    - authorization/admission dependency detection
    - sandbox/enforcement dependency detection
    - test-surface discovery
    - static boundary classification

It does NOT:
    - execute child_launcher
    - execute subprocesses
    - access credentials/secrets
    - access external networks
    - perform privileged operations
    - modify source/tests/docs
    - modify Git
    - reconstruct G46.5/G47
    - modify R097
    - claim production certification
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

TARGET_MODULE = (
    "src/lyrion/execution/process_boundary/child_launcher.py"
)

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
    "review_child_launcher_execution_boundary.py",
}


@dataclass(frozen=True)
class Symbol:
    qualified: str
    short: str
    kind: str
    line: int
    col: int


@dataclass
class Finding:
    category: str
    severity: str
    evidence: str
    line: int | None = None


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

        failures.append(
            f"unexpected worktree change: {line}"
        )

    return not failures, failures


def target_path() -> Path:
    path = REPO_ROOT / TARGET_MODULE

    if not path.is_file():
        raise FileNotFoundError(
            f"Target module not found: {path}"
        )

    return path


def read_target() -> str:
    return target_path().read_text(
        encoding="utf-8",
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


class TargetVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[str] = []
        self.symbols: list[Symbol] = []
        self.calls: list[tuple[str, int]] = []
        self.attributes: list[tuple[str, int]] = []
        self.strings: list[tuple[str, int]] = []
        self.assignments: list[tuple[str, int]] = []
        self.parameters: list[tuple[str, int]] = []
        self.annotations: list[tuple[str, int]] = []
        self.class_stack: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
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
                *self.class_stack,
                node.name,
            ]
        )

        self.symbols.append(
            Symbol(
                qualified=qualified,
                short=node.name,
                kind="class",
                line=node.lineno,
                col=node.col_offset,
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
                *self.class_stack,
                node.name,
            ]
        )

        self.symbols.append(
            Symbol(
                qualified=qualified,
                short=node.name,
                kind="function",
                line=node.lineno,
                col=node.col_offset,
            )
        )

        for arg in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            self.parameters.append(
                (
                    arg.arg,
                    arg.lineno,
                )
            )

            if arg.annotation:
                annotation = ast.unparse(
                    arg.annotation,
                )

                self.annotations.append(
                    (
                        annotation,
                        arg.lineno,
                    )
                )

        if node.returns:
            self.annotations.append(
                (
                    ast.unparse(node.returns),
                    node.returns.lineno,
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
        function = ast.unparse(node.func)

        self.calls.append(
            (
                function,
                node.lineno,
            )
        )

        self.generic_visit(node)

    def visit_Attribute(
        self,
        node: ast.Attribute,
    ) -> None:
        self.attributes.append(
            (
                ast.unparse(node),
                node.lineno,
            )
        )

        self.generic_visit(node)

    def visit_Constant(
        self,
        node: ast.Constant,
    ) -> None:
        if isinstance(node.value, str):
            self.strings.append(
                (
                    node.value,
                    node.lineno,
                )
            )

        self.generic_visit(node)

    def visit_Assign(
        self,
        node: ast.Assign,
    ) -> None:
        self.assignments.append(
            (
                ast.unparse(node),
                node.lineno,
            )
        )

        self.generic_visit(node)


def parse_target(
    source: str,
) -> tuple[ast.Module, TargetVisitor]:
    tree = ast.parse(
        source,
        filename=TARGET_MODULE,
    )

    visitor = TargetVisitor()
    visitor.visit(tree)

    return tree, visitor


def contains(
    values: list[str],
    terms: tuple[str, ...],
) -> list[str]:
    lowered = [
        value.lower()
        for value in values
    ]

    result: list[str] = []

    for value, original in zip(
        lowered,
        values,
    ):
        if any(
            term.lower() in value
            for term in terms
        ):
            result.append(original)

    return sorted(set(result))


def call_findings(
    calls: list[tuple[str, int]],
    terms: tuple[str, ...],
) -> list[Finding]:
    findings: list[Finding] = []

    for call, line in calls:
        if any(
            term.lower() in call.lower()
            for term in terms
        ):
            findings.append(
                Finding(
                    "call",
                    "SIGNAL",
                    call,
                    line,
                )
            )

    return findings


def test_surface(
    tests: list[Path],
) -> list[str]:
    terms = (
        "child_launcher",
        "ChildLauncher",
        "process_boundary",
        "ProcessBoundary",
        "launch_child",
        "child process",
    )

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
                str(path.relative_to(REPO_ROOT))
            )

    return sorted(result)


def main() -> int:
    print("=" * 100)
    print("LYRION CHILD LAUNCHER EXECUTION BOUNDARY REVIEW")
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

    path = target_path()
    source = read_target()

    print()
    print("-" * 100)
    print("TARGET MODULE")
    print("-" * 100)
    print(f"Path : {TARGET_MODULE}")
    print(f"SHA256 : {sha256(path)}")
    print(f"Bytes : {path.stat().st_size}")

    try:
        tree, visitor = parse_target(
            source,
        )
    except SyntaxError as exc:
        print(
            f"AST parse failure: {exc}"
        )
        print(
            "Decision: STATIC_ANALYSIS_INCOMPLETE"
        )
        return 3

    print(
        "AST parse : PASS"
    )

    print()
    print("-" * 100)
    print("SYMBOLS")
    print("-" * 100)

    for symbol in visitor.symbols:
        print(
            f"{symbol.kind:10s} "
            f"{symbol.qualified:60s} "
            f"line={symbol.line}"
        )

    # ------------------------------------------------------------------
    # Import boundary
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("DEPENDENCY / IMPORT BOUNDARY")
    print("=" * 100)

    important_import_terms = (
        "aegis",
        "authorization",
        "capabilit",
        "execution",
        "admission",
        "secure_executor",
        "sandbox",
        "enforcement",
        "host",
        "adapter",
        "process",
        "subprocess",
        "resource",
        "provenance",
        "audit",
        "verification",
    )

    relevant_imports = contains(
        visitor.imports,
        important_import_terms,
    )

    for value in relevant_imports:
        print(f"  - {value}")

    if not relevant_imports:
        print(
            "  - No relevant security/execution "
            "imports detected."
        )

    # ------------------------------------------------------------------
    # Contract parameters / annotations
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PARAMETER / TYPE CONTRACTS")
    print("=" * 100)

    contract_terms = (
        "authorization",
        "admission",
        "capability",
        "execution",
        "sandbox",
        "policy",
        "context",
        "principal",
        "authority",
        "task",
        "resource",
        "provenance",
        "evidence",
    )

    relevant_annotations = [
        annotation
        for annotation, _line in visitor.annotations
        if any(
            term.lower()
            in annotation.lower()
            for term in contract_terms
        )
    ]

    for annotation in sorted(
        set(relevant_annotations)
    ):
        print(
            f"  - {annotation}"
        )

    if not relevant_annotations:
        print(
            "  - No relevant security/execution "
            "type annotation detected."
        )

    # ------------------------------------------------------------------
    # Calls
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("EXECUTION / SECURITY CALLS")
    print("=" * 100)

    security_call_terms = (
        "authorize",
        "authorization",
        "require_authorized",
        "admit",
        "require_admission",
        "validate",
        "sandbox",
        "execute",
        "enforce",
        "audit",
        "verify",
        "provenance",
        "checkpoint",
    )

    security_calls = call_findings(
        visitor.calls,
        security_call_terms,
    )

    for finding in security_calls:
        print(
            f"  [{finding.line}] "
            f"{finding.evidence}"
        )

    if not security_calls:
        print(
            "  - No direct security/execution "
            "control call detected."
        )

    # ------------------------------------------------------------------
    # Process primitives
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("PROCESS CREATION / CHILD EXECUTION PRIMITIVES")
    print("=" * 100)

    process_terms = (
        "subprocess",
        "popen",
        "run",
        "check_call",
        "check_output",
        "create_subprocess_exec",
        "create_subprocess_shell",
        "os.system",
        "os.spawn",
        "os.exec",
        "fork",
        "posix_spawn",
    )

    process_calls = call_findings(
        visitor.calls,
        process_terms,
    )

    for finding in process_calls:
        print(
            f"  [{finding.line}] "
            f"{finding.evidence}"
        )

    process_imports = contains(
        visitor.imports,
        process_terms,
    )

    for value in process_imports:
        print(
            f"  IMPORT: {value}"
        )

    process_surface = bool(
        process_calls
        or process_imports
    )

    if not process_surface:
        print(
            "  - No process creation primitive detected."
        )

    # ------------------------------------------------------------------
    # Direct authority signals
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("DIRECT AUTHORITY SIGNALS")
    print("=" * 100)

    authority_terms = (
        "AegisAuthorizationService",
        "AuthorizationGuard",
        "CapabilityGateway",
        "ExecutionAdmission",
        "require_authorized",
        "authorize",
        "grant",
        "delegate",
        "revoke",
        "policy",
    )

    authority_calls = call_findings(
        visitor.calls,
        authority_terms,
    )

    authority_imports = contains(
        visitor.imports,
        tuple(
            term.lower()
            for term in authority_terms
        ),
    )

    for finding in authority_calls:
        print(
            f"  CALL [{finding.line}] "
            f"{finding.evidence}"
        )

    for value in authority_imports:
        print(
            f"  IMPORT {value}"
        )

    if not authority_calls and not authority_imports:
        print(
            "  - No direct authority-management "
            "signal detected."
        )

    # ------------------------------------------------------------------
    # Sandbox / enforcement signals
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("SANDBOX / ENFORCEMENT SIGNALS")
    print("=" * 100)

    sandbox_terms = (
        "sandbox",
        "SandboxPolicy",
        "SandboxPolicyEvaluator",
        "AppArmor",
        "Landlock",
        "Cgroup",
        "Seccomp",
        "Namespace",
        "NoNewPrivs",
        "enforcement",
        "resource",
    )

    sandbox_calls = call_findings(
        visitor.calls,
        sandbox_terms,
    )

    sandbox_imports = contains(
        visitor.imports,
        tuple(
            term.lower()
            for term in sandbox_terms
        ),
    )

    for finding in sandbox_calls:
        print(
            f"  CALL [{finding.line}] "
            f"{finding.evidence}"
        )

    for value in sandbox_imports:
        print(
            f"  IMPORT {value}"
        )

    if not sandbox_calls and not sandbox_imports:
        print(
            "  - No direct sandbox/enforcement "
            "signal detected."
        )

    # ------------------------------------------------------------------
    # Host integration signals
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("HOST / LHICF INTEGRATION SIGNALS")
    print("=" * 100)

    host_terms = (
        "HostContext",
        "HostOperation",
        "HostAdapter",
        "PrimitiveAdapter",
        "LHICF",
        "HostIntegration",
        "filesystem",
        "process",
        "service",
        "network",
        "application",
        "desktop",
        "device",
        "clipboard",
    )

    host_calls = call_findings(
        visitor.calls,
        host_terms,
    )

    host_imports = contains(
        visitor.imports,
        tuple(
            term.lower()
            for term in host_terms
        ),
    )

    for finding in host_calls:
        print(
            f"  CALL [{finding.line}] "
            f"{finding.evidence}"
        )

    for value in host_imports:
        print(
            f"  IMPORT {value}"
        )

    if not host_calls and not host_imports:
        print(
            "  - No direct host/LHICF "
            "integration signal detected."
        )

    # ------------------------------------------------------------------
    # Test evidence
    # ------------------------------------------------------------------

    tests = test_surface(
        test_files(),
    )

    print()
    print("=" * 100)
    print("TEST SURFACE")
    print("=" * 100)

    print(
        f"Related test files: {len(tests)}"
    )

    for value in tests[:100]:
        print(
            f"  - {value}"
        )

    # ------------------------------------------------------------------
    # Static architectural classification
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("STATIC ARCHITECTURAL CLASSIFICATION")
    print("=" * 100)

    has_process = process_surface
    has_authority = bool(
        authority_calls
        or authority_imports
    )
    has_sandbox = bool(
        sandbox_calls
        or sandbox_imports
    )
    has_host = bool(
        host_calls
        or host_imports
    )
    has_security_control = bool(
        security_calls
    )

    if (
        has_process
        and not has_authority
        and (
            has_sandbox
            or has_host
            or has_security_control
        )
    ):
        classification = (
            "DOWNSTREAM_EXECUTION_MECHANISM_CANDIDATE"
        )
    elif (
        has_process
        and has_authority
    ):
        classification = (
            "POTENTIAL_AUTHORITY_EXECUTION_MIX_REQUIRES_REVIEW"
        )
    elif has_process:
        classification = (
            "PROCESS_EXECUTION_SURFACE_REQUIRES_REVIEW"
        )
    else:
        classification = (
            "NO_DIRECT_PROCESS_EXECUTION_SURFACE_DETECTED"
        )

    print(
        f"Classification: {classification}"
    )

    # ------------------------------------------------------------------
    # Final architectural checks
    # ------------------------------------------------------------------

    checks = {
        "process_creation_present": has_process,
        "direct_authority_present": has_authority,
        "sandbox_or_enforcement_present": has_sandbox,
        "host_integration_present": has_host,
        "security_control_calls_present": has_security_control,
        "related_tests_present": bool(tests),
    }

    print()
    print("=" * 100)
    print("ARCHITECTURAL BOUNDARY CHECKS")
    print("=" * 100)

    for name, value in checks.items():
        print(
            f"{name:42s}: "
            f"{'PRESENT' if value else 'NOT_DETECTED'}"
        )

    # ------------------------------------------------------------------
    # Important interpretation
    # ------------------------------------------------------------------

    print()
    print("=" * 100)
    print("ARCHITECTURAL INTERPRETATION")
    print("=" * 100)

    print(
        "This is static evidence only."
    )

    print(
        "Process creation does NOT by itself imply "
        "an alternate authorization path."
    )

    print(
        "The critical question is whether child_launcher "
        "receives already-admitted execution context "
        "or independently creates authority."
    )

    if has_authority:
        print(
            "WARNING: direct authority-related signals "
            "were detected and require engineering review."
        )
    else:
        print(
            "No direct authority-management signal was "
            "detected in the target module."
        )

    if has_process:
        print(
            "The module contains process-execution "
            "capability and therefore remains a "
            "security-sensitive downstream boundary."
        )

    print(
        "Any future LHICF boundary must remain downstream "
        "of Aegis, Capability Gateway, Execution Admission, "
        "Secure Executor and Sandbox."
    )

    print(
        "No implementation slice is selected by this tool."
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
        "STATIC CHILD-LAUNCHER SECURITY BOUNDARY REVIEW"
    )
    print("Executed validation           : NOT ASSESSED")
    print("Acceptance evidence           : NOT ASSESSED")
    print("Production implementation     : BLOCKED")
    print("Production certification      : NOT CLAIMED")
    print("G46.5 reconstruction          : NOT PERFORMED")
    print("G47 reconstruction            : NOT PERFORMED")
    print("R097 modification             : NONE")
    print("Source/test/document mutation : NONE")

    summary = {
        "decision": (
            "CHILD_LAUNCHER_EXECUTION_BOUNDARY_REVIEW_COMPLETE"
        ),
        "head": head,
        "origin_main": origin,
        "target": TARGET_MODULE,
        "target_sha256": sha256(path),
        "runtime_python_files": len(
            source_files()
        ),
        "project_test_files": len(
            test_files()
        ),
        "symbols": [
            {
                "qualified": symbol.qualified,
                "kind": symbol.kind,
                "line": symbol.line,
            }
            for symbol in visitor.symbols
        ],
        "relevant_imports": relevant_imports,
        "relevant_annotations": sorted(
            set(relevant_annotations)
        ),
        "security_calls": [
            {
                "call": finding.evidence,
                "line": finding.line,
            }
            for finding in security_calls
        ],
        "process_calls": [
            {
                "call": finding.evidence,
                "line": finding.line,
            }
            for finding in process_calls
        ],
        "authority_calls": [
            {
                "call": finding.evidence,
                "line": finding.line,
            }
            for finding in authority_calls
        ],
        "authority_imports": authority_imports,
        "sandbox_calls": [
            {
                "call": finding.evidence,
                "line": finding.line,
            }
            for finding in sandbox_calls
        ],
        "sandbox_imports": sandbox_imports,
        "host_calls": [
            {
                "call": finding.evidence,
                "line": finding.line,
            }
            for finding in host_calls
        ],
        "host_imports": host_imports,
        "related_tests": tests,
        "classification": classification,
        "checks": checks,
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
        "CHILD_LAUNCHER_EXECUTION_BOUNDARY_REVIEW_COMPLETE"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

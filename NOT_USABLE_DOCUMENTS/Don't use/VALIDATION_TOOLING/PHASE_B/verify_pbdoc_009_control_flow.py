from __future__ import annotations

import ast
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

SOURCE_FILES = (
    REPO_ROOT / "src/lyrion/capabilities/gateway.py",
    REPO_ROOT / "src/lyrion/execution/contracts.py",
    REPO_ROOT / "src/lyrion/execution/executor.py",
    REPO_ROOT / "src/lyrion/execution/validator.py",
    REPO_ROOT / "src/lyrion/integration/proactive_execution.py",
    REPO_ROOT / "src/lyrion/persistence/execution_runner.py",
    REPO_ROOT / "src/lyrion/piae/action_loop.py",
    REPO_ROOT / "src/lyrion/piae/proactive_cycle.py",
    REPO_ROOT / "src/lyrion/rpii/contracts.py",
    REPO_ROOT / "src/lyrion/rpii/service.py",
)

TEST_FILES = (
    REPO_ROOT / "tests/integration/test_postgresql_execution_runner.py",
    REPO_ROOT / "tests/integration/test_postgresql_execution_runner_uow.py",
    REPO_ROOT / "tests/unit/execution/test_secure_executor_enforcement_boundary.py",
)

REQUIRED_SYMBOLS = {
    "gateway": (
        "src/lyrion/capabilities/gateway.py",
        "CapabilityGateway",
        "admit",
    ),
    "admission": (
        "src/lyrion/capabilities/gateway.py",
        "ExecutionAdmission",
        None,
    ),
    "executor": (
        "src/lyrion/execution/executor.py",
        "SecureExecutor",
        "execute",
    ),
    "validator": (
        "src/lyrion/execution/validator.py",
        "ExecutionValidator",
        None,
    ),
}

KEY_SECURITY_TERMS = (
    "authorization",
    "capability",
    "executionadmission",
    "sandbox",
    "policy",
    "validator",
    "audit",
    "provenance",
)

TARGET_REQUIREMENTS = (
    ("TR-001", "Capability Gateway", "admission"),
    ("TR-008", "validation", "validator"),
    ("TR-009", "secure execution", "executor"),
    ("TR-010", "provenance", "executor"),
)


@dataclass(frozen=True)
class SymbolRecord:
    path: Path
    qualified_name: str
    kind: str
    line: int
    end_line: int
    source: str


@dataclass(frozen=True)
class FlowEvidence:
    source: SymbolRecord
    target: SymbolRecord
    relationship: str
    evidence_lines: tuple[int, ...]


@dataclass(frozen=True)
class VerificationResult:
    requirement: str
    description: str
    state: str
    evidence: tuple[str, ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_ast(path: Path) -> tuple[str, ast.AST]:
    source = path.read_text(
        encoding="utf-8",
        errors="strict",
    )
    return source, ast.parse(source)


def qualified_name(prefix: str, node_name: str) -> str:
    if prefix:
        return f"{prefix}.{node_name}"
    return node_name


def collect_symbols(path: Path) -> list[SymbolRecord]:
    try:
        source, tree = load_ast(path)
    except (OSError, UnicodeError, SyntaxError):
        return []

    records: list[SymbolRecord] = []

    def visit(
        node: ast.AST,
        prefix: str,
    ) -> None:
        if isinstance(node, ast.ClassDef):
            class_name = qualified_name(prefix, node.name)

            records.append(
                SymbolRecord(
                    path=path,
                    qualified_name=class_name,
                    kind="class",
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    source=ast.get_source_segment(source, node) or "",
                )
            )

            for child in node.body:
                visit(child, class_name)

            return

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_name = qualified_name(prefix, node.name)

            records.append(
                SymbolRecord(
                    path=path,
                    qualified_name=function_name,
                    kind=(
                        "async_function"
                        if isinstance(node, ast.AsyncFunctionDef)
                        else "function"
                    ),
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    source=ast.get_source_segment(source, node) or "",
                )
            )

            for body_node in node.body:
                if isinstance(
                    body_node,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                ):
                    visit(body_node, function_name)

            return

        for child_node in ast.iter_child_nodes(node):
            visit(child_node, prefix)

    visit(tree, "")
    return records


def all_symbols() -> list[SymbolRecord]:
    records: list[SymbolRecord] = []

    for path in SOURCE_FILES:
        if path.is_file():
            records.extend(collect_symbols(path))

    return records


def find_symbol(
    symbols: list[SymbolRecord],
    path_suffix: str,
    name: str,
    kind: str | None = None,
) -> list[SymbolRecord]:
    results = []

    for symbol in symbols:
        if not str(symbol.path).endswith(path_suffix):
            continue

        if symbol.qualified_name.split(".")[-1] != name:
            continue

        if kind is not None and symbol.kind != kind:
            continue

        results.append(symbol)

    return results


def source_contains_terms(
    symbol: SymbolRecord,
    terms: tuple[str, ...],
) -> list[str]:
    lowered = symbol.source.lower()

    return [
        term
        for term in terms
        if term.lower() in lowered
    ]


def call_names(node: ast.AST) -> list[str]:
    names: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            function = child.func

            if isinstance(function, ast.Name):
                names.append(function.id)

            elif isinstance(function, ast.Attribute):
                names.append(function.attr)

    return names


def symbol_calls(
    source_symbol: SymbolRecord,
    target_name: str,
) -> tuple[int, ...]:
    try:
        _, tree = load_ast(source_symbol.path)
    except (OSError, UnicodeError, SyntaxError):
        return ()

    target_line_start = source_symbol.line
    target_line_end = source_symbol.end_line

    matching_lines: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        line = getattr(node, "lineno", 0)

        if not (
            target_line_start
            <= line
            <= target_line_end
        ):
            continue

        function = node.func

        called_name: str | None = None

        if isinstance(function, ast.Name):
            called_name = function.id
        elif isinstance(function, ast.Attribute):
            called_name = function.attr

        if called_name == target_name:
            matching_lines.append(line)

    return tuple(sorted(set(matching_lines)))


def imports_name(
    path: Path,
    target_name: str,
) -> tuple[int, ...]:
    try:
        _, tree = load_ast(path)
    except (OSError, UnicodeError, SyntaxError):
        return ()

    lines: list[int] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == target_name:
                    lines.append(node.lineno)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported = alias.name.split(".")[-1]

                if imported == target_name:
                    lines.append(node.lineno)

    return tuple(sorted(set(lines)))


def find_text_lines(
    path: Path,
    terms: tuple[str, ...],
) -> tuple[int, ...]:
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
    except (OSError, UnicodeError):
        return ()

    matches: list[int] = []

    for number, line in enumerate(lines, start=1):
        lowered = line.lower()

        if any(term.lower() in lowered for term in terms):
            matches.append(number)

    return tuple(matches)


def verify_requirement(
    requirement: tuple[str, str, str],
    symbols: list[SymbolRecord],
) -> VerificationResult:
    requirement_id, description, target = requirement

    evidence: list[str] = []

    if target == "admission":
        gateway_path = (
            REPO_ROOT
            / "src/lyrion/capabilities/gateway.py"
        )

        gateway_candidates = [
            symbol
            for symbol in symbols
            if symbol.path.resolve() == gateway_path.resolve()
            and symbol.qualified_name == "CapabilityGateway"
            and symbol.kind == "class"
        ]

        admission_candidates = [
            symbol
            for symbol in symbols
            if symbol.path.resolve() == gateway_path.resolve()
            and symbol.qualified_name == "ExecutionAdmission"
            and symbol.kind == "class"
        ]

        admit_candidates = [
            symbol
            for symbol in symbols
            if symbol.path.resolve() == gateway_path.resolve()
            and symbol.qualified_name == "CapabilityGateway.admit"
            and symbol.kind in {"function", "async_function"}
        ]

        if not gateway_candidates:
            return VerificationResult(
                requirement_id,
                description,
                "NOT_VERIFIED",
                (
                    "Concrete CapabilityGateway class was not "
                    "resolved in gateway.py.",
                ),
            )

        if not admission_candidates:
            return VerificationResult(
                requirement_id,
                description,
                "NOT_VERIFIED",
                (
                    "Concrete ExecutionAdmission class was not "
                    "resolved in gateway.py.",
                ),
            )

        if not admit_candidates:
            return VerificationResult(
                requirement_id,
                description,
                "PARTIALLY_VERIFIED",
                (
                    "CapabilityGateway exists, but its concrete "
                    "admit() implementation was not resolved.",
                ),
            )

        admit = admit_candidates[0]

        admission_calls = symbol_calls(
            admit,
            "from_authorization",
        )

        terms = source_contains_terms(
            admit,
            KEY_SECURITY_TERMS,
        )

        evidence.append(
            "Concrete CapabilityGateway resolved at "
            f"{gateway_path}:L{gateway_candidates[0].line}."
        )

        evidence.append(
            "Concrete CapabilityGateway.admit resolved at "
            f"{gateway_path}:L{admit.line}."
        )

        if admission_calls:
            evidence.append(
                "CapabilityGateway.admit calls "
                "ExecutionAdmission.from_authorization "
                f"at lines {admission_calls}."
            )
        else:
            evidence.append(
                "CapabilityGateway.admit does not contain a "
                "direct from_authorization call."
            )

        if terms:
            evidence.append(
                "Admission path contains security-control terms: "
                + ", ".join(terms)
            )

        if admission_calls and terms:
            state = "VERIFIED"
        elif admission_calls or terms:
            state = "PARTIALLY_VERIFIED"
        else:
            state = "EVIDENCE_GAP"

        return VerificationResult(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    if target == "validator":
        validator_candidates = find_symbol(
            symbols,
            "src/lyrion/execution/validator.py",
            "ExecutionValidator",
            "class",
        )

        if not validator_candidates:
            return VerificationResult(
                requirement_id,
                description,
                "NOT_VERIFIED",
                ("ExecutionValidator class not found.",),
            )

        validator = validator_candidates[0]

        if source_contains_terms(
            validator,
            ("admission", "authorization", "policy", "expiry"),
        ):
            evidence.append(
                "ExecutionValidator contains admission/authorization/"
                "policy validation evidence."
            )

        method_names = [
            symbol.qualified_name
            for symbol in symbols
            if symbol.path == validator.path
            and symbol.qualified_name.startswith(
                "ExecutionValidator."
            )
        ]

        if method_names:
            evidence.append(
                "Validator methods discovered: "
                + ", ".join(method_names[:20])
            )

        if len(evidence) >= 2:
            state = "VERIFIED"
        elif evidence:
            state = "PARTIALLY_VERIFIED"
        else:
            state = "EVIDENCE_GAP"

        return VerificationResult(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    if target == "executor":
        executor_candidates = find_symbol(
            symbols,
            "src/lyrion/execution/executor.py",
            "SecureExecutor",
            "class",
        )

        if not executor_candidates:
            return VerificationResult(
                requirement_id,
                description,
                "NOT_VERIFIED",
                ("SecureExecutor class not found.",),
            )

        executor = executor_candidates[0]

        execute_methods = [
            symbol
            for symbol in symbols
            if symbol.path == executor.path
            and symbol.qualified_name.endswith(
                "SecureExecutor.execute"
            )
        ]

        if not execute_methods:
            return VerificationResult(
                requirement_id,
                description,
                "PARTIALLY_VERIFIED",
                ("SecureExecutor found; execute method not found.",),
            )

        execute = execute_methods[0]

        admission_imports = imports_name(
            execute.path,
            "ExecutionAdmission",
        )

        security_terms = source_contains_terms(
            execute,
            KEY_SECURITY_TERMS,
        )

        if admission_imports:
            evidence.append(
                "ExecutionAdmission is imported in executor "
                f"at lines {admission_imports}."
            )

        if security_terms:
            evidence.append(
                "SecureExecutor.execute contains security-control "
                "evidence: "
                + ", ".join(security_terms)
            )

        call_names_found = call_names(
            ast.parse(execute.source)
        )

        if "validate" in call_names_found:
            evidence.append(
                "SecureExecutor.execute directly calls a validate-like "
                "operation."
            )

        if len(evidence) >= 2:
            state = "VERIFIED"
        elif evidence:
            state = "PARTIALLY_VERIFIED"
        else:
            state = "EVIDENCE_GAP"

        return VerificationResult(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    return VerificationResult(
        requirement_id,
        description,
        "EVIDENCE_GAP",
        ("No verifier implemented for this target.",),
    )


def print_result(result: VerificationResult) -> None:
    print()
    print("-" * 78)
    print(
        f"{result.requirement} | "
        f"{result.state}"
    )
    print(f"Description: {result.description}")

    for evidence in result.evidence:
        print(f"  EVIDENCE: {evidence}")


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-009 — CONTROL-FLOW VERIFICATION")
    print("READ-ONLY SECURITY / ARCHITECTURE EVIDENCE")
    print()

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")

    if not SPECIFICATION.is_file():
        print("RESULT: FAIL — specification missing.")
        return 1

    print(f"Specification SHA256: {sha256(SPECIFICATION)}")

    specification_text = SPECIFICATION.read_text(
        encoding="utf-8"
    ).lower()

    if "pb-doc-009" not in specification_text:
        print("RESULT: FAIL — specification identity invalid.")
        return 1

    if "execution admission" not in specification_text:
        print("RESULT: FAIL — execution admission identity missing.")
        return 1

    missing_sources = [
        path
        for path in SOURCE_FILES
        if not path.is_file()
    ]

    if missing_sources:
        print("RESULT: FAIL — required source evidence missing:")

        for path in missing_sources:
            print(f"  - {path}")

        return 1

    symbols = all_symbols()

    print(f"AST symbols discovered: {len(symbols)}")

    print()
    print("=" * 78)
    print("1. REQUIRED SECURITY/EXECUTION SYMBOLS")
    print("=" * 78)

    for label, (
        path_suffix,
        name,
        kind,
    ) in REQUIRED_SYMBOLS.items():
        found = find_symbol(
            symbols,
            path_suffix,
            name,
            kind,
        )

        if found:
            for symbol in found:
                print(
                    f"PASS {label}: "
                    f"{symbol.qualified_name} "
                    f"{symbol.path}:L{symbol.line}"
                )
        else:
            print(f"FAIL {label}: {name}")

    print()
    print("=" * 78)
    print("2. TARGET REQUIREMENT VERIFICATION")
    print("=" * 78)

    results = [
        verify_requirement(
            requirement,
            symbols,
        )
        for requirement in TARGET_REQUIREMENTS
    ]

    for result in results:
        print_result(result)

    print()
    print("=" * 78)
    print("3. TEST EVIDENCE")
    print("=" * 78)

    for test_file in TEST_FILES:
        if not test_file.is_file():
            print(f"NOT_FOUND: {test_file}")
            continue

        lines = find_text_lines(
            test_file,
            (
                "ExecutionAdmission",
                "CapabilityGateway",
                "SecureExecutor",
                "authorization",
                "SandboxConfig",
                "ExecutionStatus",
            ),
        )

        print(f"TEST: {test_file}")

        if lines:
            print(
                "  Relevant evidence lines: "
                + ", ".join(str(line) for line in lines[:40])
            )
        else:
            print("  Relevant evidence lines: NONE")

    print()
    print("=" * 78)
    print("4. VERIFICATION SUMMARY")
    print("=" * 78)

    for result in results:
        print(
            f"{result.requirement}: "
            f"{result.state}"
        )

    print()
    print("=" * 78)
    print("5. ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 78)

    print("No architectural classification is performed.")
    print()
    print("NOT ASSIGNED:")
    print("  PRESERVE")
    print("  EXTEND")
    print("  NEW")
    print("  REFACTOR")
    print("  CONFLICT")

    print()
    print("=" * 78)
    print("6. SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 78)

    print("READ-ONLY: YES")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")

    print()
    print("=" * 78)
    print("7. FINAL RESULT")
    print("=" * 78)

    print(
        "RESULT: PASS — PB-DOC-009 CONTROL-FLOW "
        "VERIFICATION COMPLETED"
    )
    print(
        "NOTE: PASS means the verifier executed successfully; "
        "individual evidence states determine implementation support."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

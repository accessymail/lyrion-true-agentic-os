from __future__ import annotations

import ast
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src"
SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

RECOVERY_TARGETS = {
    "PersistentRecoveryOrchestrator.recover_one",
    "SQLAlchemyExecutionStore.requeue",
    "ExecutionStore.requeue",
}

QUEUED_TERMS = (
    "QUEUED",
    "queued",
    "find_recoverable",
    "claim",
    "create_queued",
    "requeue",
)

EXECUTION_TERMS = (
    "run_once_persistent",
    "PersistentExecutionRunner",
    "OpportunityConsumer",
    "execute",
    "execution",
)

ADMISSION_TERMS = (
    "ExecutionAdmission",
    "create_capability_request",
    "CapabilityGateway",
    "admit",
    "require_admission",
    "authorize",
    "authorization",
)

RECOVERY_TERMS = (
    "recover",
    "recovery",
    "requeue",
    "checkpoint",
    "resume",
)


@dataclass(frozen=True)
class Symbol:
    path: Path
    name: str
    line: int
    source: str
    calls: tuple[str, ...]


@dataclass(frozen=True)
class CallSite:
    path: Path
    line: int
    caller: str
    callee: str
    source_line: str


def read_source(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, UnicodeError):
        return ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node.func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return ast.unparse(node.func)


def collect_calls(node: ast.AST) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                call_name(item)
                for item in ast.walk(node)
                if isinstance(item, ast.Call)
            }
        )
    )


def collect_symbols(path: Path) -> list[Symbol]:
    source = read_source(path)

    if not source:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    symbols: list[Symbol] = []

    class Collector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self.class_stack.append(node.name)

            symbols.append(
                Symbol(
                    path=path,
                    name=".".join(self.class_stack),
                    line=node.lineno,
                    source=(
                        ast.get_source_segment(
                            source,
                            node,
                        )
                        or ""
                    ),
                    calls=collect_calls(node),
                )
            )

            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            prefix = ".".join(self.class_stack)

            name = (
                f"{prefix}.{node.name}"
                if prefix
                else node.name
            )

            symbols.append(
                Symbol(
                    path=path,
                    name=name,
                    line=node.lineno,
                    source=(
                        ast.get_source_segment(
                            source,
                            node,
                        )
                        or ""
                    ),
                    calls=collect_calls(node),
                )
            )

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            prefix = ".".join(self.class_stack)

            name = (
                f"{prefix}.{node.name}"
                if prefix
                else node.name
            )

            symbols.append(
                Symbol(
                    path=path,
                    name=name,
                    line=node.lineno,
                    source=(
                        ast.get_source_segment(
                            source,
                            node,
                        )
                        or ""
                    ),
                    calls=collect_calls(node),
                )
            )

    Collector().visit(tree)
    return symbols


def find_exact(
    symbols: list[Symbol],
    name: str,
) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols
        if symbol.name == name
    ]


def collect_callers_for_file(
    path: Path,
    source: str,
    tree: ast.AST,
    target_names: set[str],
) -> list[CallSite]:
    results: list[CallSite] = []
    lines = source.splitlines()

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []
            self.function_stack: list[str] = []

        def current_caller(self) -> str:
            parts = (
                self.class_stack
                + self.function_stack
            )

            return ".".join(parts) or "<module>"

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_Call(
            self,
            node: ast.Call,
        ) -> None:
            name = call_name(node)

            if name in target_names:
                line = getattr(
                    node,
                    "lineno",
                    1,
                )

                source_line = (
                    lines[line - 1].strip()
                    if 0 < line <= len(lines)
                    else ""
                )

                results.append(
                    CallSite(
                        path=path,
                        line=line,
                        caller=self.current_caller(),
                        callee=name,
                        source_line=source_line,
                    )
                )

            self.generic_visit(node)

    Visitor().visit(tree)
    return results


def find_callers(
    target_names: set[str],
) -> list[CallSite]:
    results: list[CallSite] = []

    for path in sorted(
        SOURCE_ROOT.rglob("*.py")
    ):
        source = read_source(path)

        if not source:
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        results.extend(
            collect_callers_for_file(
                path,
                source,
                tree,
                target_names,
            )
        )

    return results


def relevant_lines(
    symbol: Symbol,
    terms: tuple[str, ...],
) -> list[tuple[int, list[str], str]]:
    results: list[tuple[int, list[str], str]] = []

    for number, line in enumerate(
        symbol.source.splitlines(),
        start=symbol.line,
    ):
        matches = [
            term
            for term in terms
            if term.lower() in line.lower()
        ]

        if matches:
            results.append(
                (
                    number,
                    matches,
                    line.strip(),
                )
            )

    return results


def print_symbol(
    title: str,
    symbol: Symbol,
    terms: tuple[str, ...],
) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(f"NAME: {symbol.name}")
    print(
        f"LOCATION: {symbol.path}:L{symbol.line}"
    )

    print()
    print("CALLS:")

    for call in symbol.calls:
        print(f"  {call}")

    print()
    print("RELEVANT SOURCE:")

    evidence = relevant_lines(
        symbol,
        terms,
    )

    if not evidence:
        print("  NONE")
        return

    for number, matches, line in evidence:
        print(
            f"  L{number}: terms={matches} | {line}"
        )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 RECOVERY → QUEUED "
        "CONSUMER → ADMISSION TRACE"
    )
    print("READ-ONLY")
    print()

    if not SPECIFICATION.is_file():
        print(
            "RESULT: FAIL — execution admission "
            "specification missing."
        )
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    symbols: list[Symbol] = []

    for path in sorted(
        SOURCE_ROOT.rglob("*.py")
    ):
        symbols.extend(
            collect_symbols(path)
        )

    print()
    print("=" * 100)
    print("RECOVERY ENTRYPOINT")
    print("=" * 100)

    recovery_entry = find_exact(
        symbols,
        "PersistentRecoveryOrchestrator.recover_one",
    )

    if len(recovery_entry) != 1:
        print(
            "RESULT: FAIL — exact recovery entrypoint "
            "was not uniquely resolved."
        )
        return 1

    recover_one = recovery_entry[0]

    print_symbol(
        "RECOVERY ENTRYPOINT",
        recover_one,
        RECOVERY_TERMS + QUEUED_TERMS + EXECUTION_TERMS,
    )

    print()
    print("=" * 100)
    print("REQUEUE IMPLEMENTATION")
    print("=" * 100)

    requeue_symbols = [
        symbol
        for symbol in symbols
        if symbol.name.endswith(".requeue")
        and (
            "ExecutionStore" in symbol.name
            or "SQLAlchemyExecutionStore"
            in symbol.name
        )
    ]

    if not requeue_symbols:
        print(
            "RESULT: FAIL — requeue implementation "
            "not resolved."
        )
        return 1

    for symbol in requeue_symbols:
        print_symbol(
            "REQUEUE IMPLEMENTATION",
            symbol,
            QUEUED_TERMS + EXECUTION_TERMS,
        )

    print()
    print("=" * 100)
    print("CALLERS OF REQUEUE")
    print("=" * 100)

    requeue_callers = find_callers(
        {
            "self._execution_store.requeue",
            "execution_store.requeue",
            "store.requeue",
            "requeue",
        }
    )

    for caller in requeue_callers:
        print(
            f"{caller.path}:L{caller.line} | "
            f"caller={caller.caller} | "
            f"callee={caller.callee}"
        )
        print(
            f"  {caller.source_line}"
        )

    print()
    print("=" * 100)
    print("QUEUED CONSUMER DISCOVERY")
    print("=" * 100)

    queued_symbols = [
        symbol
        for symbol in symbols
        if (
            term_hits := [
                term
                for term in QUEUED_TERMS
                if term.lower()
                in symbol.source.lower()
            ]
        )
        and (
            "execution"
            in symbol.source.lower()
            or "runner"
            in symbol.source.lower()
            or "claim"
            in symbol.source.lower()
        )
    ]

    for symbol in queued_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )
        print(
            f"  QUEUED TERMS: "
            f"{', '.join(term_hits)}"
        )

    print()
    print("=" * 100)
    print("RECOVERY / REQUEUE → EXECUTION CALLERS")
    print("=" * 100)

    execution_targets = {
        "run_once_persistent",
        "self._action_loop.run_once_persistent",
        "action_loop.run_once_persistent",
        "runner.run",
        "self._runner.run",
        "self._execution_runner.run",
    }

    execution_callers = find_callers(
        execution_targets
    )

    for caller in execution_callers:
        print(
            f"{caller.path}:L{caller.line} | "
            f"caller={caller.caller} | "
            f"callee={caller.callee}"
        )
        print(
            f"  {caller.source_line}"
        )

    print()
    print("=" * 100)
    print("ADMISSION / CAPABILITY PATH")
    print("=" * 100)

    admission_symbols = [
        symbol
        for symbol in symbols
        if (
            "CapabilityGateway" in symbol.name
            or "ExecutionAdmission"
            in symbol.name
            or "create_capability_request"
            in symbol.name
            or symbol.name.endswith(".admit")
            or symbol.name.endswith(".require_admission")
        )
    ]

    for symbol in admission_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("R097 CONTROL-FLOW ASSESSMENT")
    print("=" * 100)

    recovery_calls_requeue = any(
        "requeue" in call.lower()
        for call in recover_one.calls
    )

    queued_consumer_found = bool(
        queued_symbols
    )

    execution_consumer_found = bool(
        execution_callers
    )

    admission_path_found = bool(
        admission_symbols
    )

    print(
        "RECOVERY ENTRYPOINT → REQUEUE:",
        "YES"
        if recovery_calls_requeue
        else "NOT ESTABLISHED",
    )

    print(
        "QUEUED EXECUTION CONSUMER:",
        "FOUND"
        if queued_consumer_found
        else "NOT ESTABLISHED",
    )

    print(
        "EXECUTION CALLER:",
        "FOUND"
        if execution_consumer_found
        else "NOT ESTABLISHED",
    )

    print(
        "ADMISSION PATH:",
        "FOUND"
        if admission_path_found
        else "NOT ESTABLISHED",
    )

    print()
    print(
        "CRITICAL SECURITY QUESTION:"
    )
    print(
        "Does the execution consumer of a requeued "
        "QUEUED record invoke the normal capability/"
        "authorization/admission path?"
    )

    print(
        "This verifier does not assume that QUEUED "
        "state implies fresh authorization."
    )

    print(
        "It also does not treat an existing "
        "ExecutionAdmission object as fresh authority."
    )

    if (
        recovery_calls_requeue
        and queued_consumer_found
        and execution_consumer_found
        and admission_path_found
    ):
        result = (
            "RECOVERY_TO_EXECUTION_BOUNDARIES_FOUND — "
            "EXACT REQUEUED-CONSUMER ADMISSION PROVENANCE "
            "REQUIRES TARGETED CALL-CHAIN TRACE"
        )
    elif (
        recovery_calls_requeue
        and queued_consumer_found
    ):
        result = (
            "RECOVERY_TO_QUEUED_CONSUMER_FOUND — "
            "ADMISSION PATH NOT FULLY ESTABLISHED"
        )
    else:
        result = (
            "RECOVERY_TO_QUEUED_EXECUTION_CONSUMER "
            "NOT ESTABLISHED"
        )

    print()
    print(f"R097 RESULT: {result}")

    print()
    print("=" * 100)
    print("EVIDENCE LIMITS")
    print("=" * 100)
    print("Static AST/source inspection only.")
    print("No application execution performed.")
    print("No recovery operation performed.")
    print("No privileged operation performed.")
    print("No source mutation.")
    print("No test mutation.")
    print("No documentation mutation.")
    print("No manifest mutation.")
    print("No governance mutation.")
    print("No authorization grant.")
    print("No production authorization.")
    print("No certification claim.")
    print(
        "No PRESERVE/EXTEND/NEW/REFACTOR/CONFLICT "
        "architecture decision."
    )

    print()
    print("=" * 100)
    print("FINAL RESULT")
    print("=" * 100)
    print(
        "RESULT: PASS — R097 RECOVERY → QUEUED "
        "CONSUMER TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

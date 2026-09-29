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

TARGET = (
    "PIAEActionLoop.run_once_persistent"
)

ADMISSION_TERMS = (
    "ExecutionAdmission",
    "admission",
    "admit",
    "require_admission",
    "CapabilityGateway",
    "authorize",
    "authorization",
    "Aegis",
    "authority",
)

RECOVERY_TERMS = (
    "recover",
    "recovery",
    "requeue",
    "checkpoint",
    "resume",
    "queued",
    "claim",
)

PROVENANCE_TERMS = (
    "request",
    "capability",
    "decision",
    "admission",
    "authorization",
    "execution",
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

def term_hits(
    source: str,
    terms: tuple[str, ...],
) -> list[str]:
    lowered = source.lower()

    return sorted(
        {
            term
            for term in terms
            if term.lower() in lowered
        }
    )


def relevant_lines(
    symbol: Symbol,
    terms: tuple[str, ...],
) -> list[tuple[int, list[str], str]]:
    lines = symbol.source.splitlines()
    results: list[tuple[int, list[str], str]] = []

    for offset, line in enumerate(
        lines,
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
                    offset,
                    matches,
                    line.strip(),
                )
            )

    return results


def print_symbol(
    title: str,
    symbol: Symbol,
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

    for number, terms, line in relevant_lines(
        symbol,
        ADMISSION_TERMS
        + RECOVERY_TERMS
        + PROVENANCE_TERMS,
    ):
        print(
            f"  L{number}: terms={terms} | {line}"
        )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 EXECUTION ADMISSION "
        "ORIGIN / PROVENANCE TRACE"
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

    targets = find_exact(
        symbols,
        TARGET,
    )

    print()
    print("=" * 100)
    print("TARGET")
    print("=" * 100)

    if len(targets) != 1:
        print(
            "RESULT: FAIL — expected exactly one "
            f"{TARGET}, found {len(targets)}."
        )
        return 1

    target = targets[0]

    print_symbol(
        "PIAE ACTION LOOP TARGET",
        target,
    )

    print()
    print("=" * 100)
    print("TARGET'S DIRECT CALLS")
    print("=" * 100)

    for call in target.calls:
        print(f"  {call}")

    print()
    print("=" * 100)
    print("ADMISSION VARIABLE / INPUT EVIDENCE")
    print("=" * 100)

    admission_lines = relevant_lines(
        target,
        (
            "admission",
            "ExecutionAdmission",
            "admit",
            "request",
            "capability",
        ),
    )

    for number, terms, line in admission_lines:
        print(
            f"L{number}: terms={terms} | {line}"
        )

    print()
    print("=" * 100)
    print("CALLERS OF PIAEActionLoop.run_once_persistent")
    print("=" * 100)

    callers = find_callers(
        {
            "run_once_persistent",
            "self._action_loop.run_once_persistent",
            "action_loop.run_once_persistent",
        }
    )

    for caller in callers:
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
    print("ADMISSION-CREATING SYMBOLS")
    print("=" * 100)

    admission_creators = [
        symbol
        for symbol in symbols
        if (
            "admit" in symbol.name.lower()
            or "from_authorization"
            in symbol.name.lower()
            or (
                "ExecutionAdmission"
                in symbol.name
                and (
                    "create" in symbol.name.lower()
                    or "from" in symbol.name.lower()
                )
            )
        )
    ]

    for symbol in admission_creators:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("RECOVERY → EXECUTION CANDIDATES")
    print("=" * 100)

    recovery_execution = [
        symbol
        for symbol in symbols
        if (
            term_hits(
                symbol.source,
                RECOVERY_TERMS,
            )
            and term_hits(
                symbol.source,
                (
                    "execution",
                    "admission",
                    "runner",
                    "coordinator",
                ),
            )
        )
    ]

    for symbol in recovery_execution:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("Aegis / CAPABILITY GATEWAY CANDIDATES")
    print("=" * 100)

    security_symbols = [
        symbol
        for symbol in symbols
        if (
            "CapabilityGateway" in symbol.name
            or "AegisAuthorizationService"
            in symbol.name
            or "AuthorizationGuard"
            in symbol.name
        )
    ]

    for symbol in security_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("R097 ORIGIN ANALYSIS")
    print("=" * 100)

    target_source_lower = target.source.lower()

    admission_input = (
        "admission" in target_source_lower
        and "ExecutionAdmission"
        in target.source
    )

    target_calls_admit = any(
        "admit" in call.lower()
        for call in target.calls
    )

    target_calls_gateway = any(
        "gateway" in call.lower()
        for call in target.calls
    )

    target_calls_recovery = any(
        term.lower() in target_source_lower
        for term in RECOVERY_TERMS
    )

    print(
        "TARGET RECEIVES EXECUTIONADMISSION:",
        "YES" if admission_input else "NOT ESTABLISHED",
    )
    print(
        "TARGET CREATES FRESH ADMISSION:",
        "YES"
        if target_calls_admit
        else "NO / NOT ESTABLISHED",
    )
    print(
        "TARGET DIRECTLY CALLS GATEWAY:",
        "YES"
        if target_calls_gateway
        else "NO / NOT ESTABLISHED",
    )
    print(
        "TARGET DIRECTLY PERFORMS RECOVERY:",
        "YES"
        if target_calls_recovery
        else "NO",
    )

    print()
    print(
        "KEY QUESTION:"
    )
    print(
        "The verifier must determine which upstream "
        "symbol creates the ExecutionAdmission supplied "
        "to run_once_persistent()."
    )
    print(
        "A pre-existing admission object is NOT treated "
        "as freshly authorized merely because it reaches "
        "SecureExecutor."
    )

    if (
        admission_input
        and not target_calls_admit
        and not target_calls_gateway
    ):
        result = (
            "ADMISSION_IS_UPSTREAM_OF_PERSISTENT_RUNNER — "
            "UPSTREAM ORIGIN MUST BE RESOLVED"
        )
    elif admission_input:
        result = (
            "ADMISSION_PRESENT_IN_TARGET — "
            "FRESHNESS REQUIRES DEEPER TRACE"
        )
    else:
        result = (
            "ADMISSION_INPUT_NOT_ESTABLISHED"
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
        "RESULT: PASS — R097 ADMISSION ORIGIN "
        "TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

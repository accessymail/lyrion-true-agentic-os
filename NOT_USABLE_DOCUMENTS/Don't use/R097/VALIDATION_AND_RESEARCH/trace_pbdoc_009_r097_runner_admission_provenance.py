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

TARGET_CLASS = "PersistentExecutionRunner"
TARGET_METHOD = "run"

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


def find_target_run(
    symbols: list[Symbol],
) -> Symbol | None:
    exact = [
        symbol
        for symbol in symbols
        if symbol.name == f"{TARGET_CLASS}.{TARGET_METHOD}"
    ]

    if len(exact) == 1:
        return exact[0]

    return None


def collect_run_call_sites_for_file(
    path: Path,
    source: str,
    tree: ast.AST,
) -> list[CallSite]:
    results: list[CallSite] = []

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

            if (
                name.endswith(".run")
                or name == "run"
            ):
                line = getattr(
                    node,
                    "lineno",
                    1,
                )

                lines = source.splitlines()

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


def find_run_call_sites() -> list[CallSite]:
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
            collect_run_call_sites_for_file(
                path,
                source,
                tree,
            )
        )

    return results

def term_hits(source: str, terms: tuple[str, ...]) -> list[str]:
    lowered = source.lower()

    return sorted(
        {
            term
            for term in terms
            if term.lower() in lowered
        }
    )


def print_symbol(
    label: str,
    symbol: Symbol,
) -> None:
    print()
    print("=" * 100)
    print(label)
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
    print("ADMISSION TERMS:")

    for term in term_hits(
        symbol.source,
        ADMISSION_TERMS,
    ):
        print(f"  {term}")

    print()
    print("RECOVERY TERMS:")

    for term in term_hits(
        symbol.source,
        RECOVERY_TERMS,
    ):
        print(f"  {term}")


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 RUNNER / "
        "ADMISSION PROVENANCE TRACE"
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

    target = find_target_run(symbols)

    print()
    print("=" * 100)
    print("TARGET: PersistentExecutionRunner.run")
    print("=" * 100)

    if target is None:
        print(
            "RESULT: FAIL — exact target symbol "
            "could not be resolved."
        )
        return 1

    print_symbol(
        "TARGET RUNNER",
        target,
    )

    print()
    print("=" * 100)
    print("CALLERS OF .run()")
    print("=" * 100)

    call_sites = find_run_call_sites()

    target_path = target.path.resolve()

    filtered_sites = [
        site
        for site in call_sites
        if site.path.resolve() != target_path
        or site.caller != target.name
    ]

    if not filtered_sites:
        print(
            "NO CALL SITES DISCOVERED."
        )
    else:
        for site in filtered_sites:
            print(
                f"{site.path}:L{site.line} | "
                f"caller={site.caller} | "
                f"callee={site.callee}"
            )
            print(
                f"  {site.source_line}"
            )

    print()
    print("=" * 100)
    print("KNOWN EXECUTION CALLERS / COORDINATORS")
    print("=" * 100)

    coordinator_symbols = [
        symbol
        for symbol in symbols
        if (
            "execute" in symbol.name.lower()
            or "run" in symbol.name.lower()
        )
        and (
            term_hits(
                symbol.source,
                ADMISSION_TERMS,
            )
        )
    ]

    for symbol in coordinator_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("RECOVERY / REQUEUE CANDIDATES")
    print("=" * 100)

    recovery_symbols = [
        symbol
        for symbol in symbols
        if term_hits(
            symbol.source,
            RECOVERY_TERMS,
        )
    ]

    for symbol in recovery_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("ADMISSION PROVENANCE CANDIDATES")
    print("=" * 100)

    admission_symbols = [
        symbol
        for symbol in symbols
        if term_hits(
            symbol.source,
            ADMISSION_TERMS,
        )
    ]

    for symbol in admission_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("R097 PROVENANCE INTERPRETATION")
    print("=" * 100)

    runner_accepts_admission = any(
        "admission" in parameter.lower()
        for parameter in (
            target.source.split(")")[0]
            if ")" in target.source
            else ""
        ).split(",")
    )

    has_runner_callers = bool(filtered_sites)

    has_recovery = bool(recovery_symbols)

    has_admission_candidates = bool(
        admission_symbols
    )

    has_direct_admit = any(
        (
            "self._gateway.admit" in symbol.source
            or "gateway.admit" in symbol.source
            or "require_admission" in symbol.source
        )
        for symbol in coordinator_symbols
    )

    print(
        "RUNNER ACCEPTS ADMISSION:",
        "YES" if runner_accepts_admission else "NOT ESTABLISHED",
    )
    print(
        "RUNNER CALLERS FOUND:",
        "YES" if has_runner_callers else "NO",
    )
    print(
        "RECOVERY / REQUEUE EVIDENCE:",
        "YES" if has_recovery else "NO",
    )
    print(
        "ADMISSION PROVENANCE EVIDENCE:",
        "YES" if has_admission_candidates else "NO",
    )
    print(
        "DIRECT ADMISSION IN EXECUTION COORDINATOR:",
        "YES" if has_direct_admit else "NOT ESTABLISHED",
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "This analyzer does not assume that an existing "
        "ExecutionAdmission is fresh."
    )
    print(
        "It does not treat textual presence of 'admit' "
        "as proof of recovery re-authorization."
    )
    print(
        "The decisive evidence is the actual caller and "
        "the provenance of the admission object supplied "
        "to PersistentExecutionRunner.run()."
    )

    if (
        has_runner_callers
        and has_recovery
        and has_admission_candidates
    ):
        result = (
            "RUNNER_CALLERS_AND_ADMISSION_PROVENANCE_FOUND — "
            "TRACE SUPPLY OF EXECUTIONADMISSION"
        )
    elif has_runner_callers:
        result = (
            "RUNNER_CALLERS_FOUND — "
            "ADMISSION PROVENANCE NOT FULLY ESTABLISHED"
        )
    else:
        result = (
            "RUNNER_CALLER_NOT_ESTABLISHED"
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
        "RESULT: PASS — R097 RUNNER / "
        "ADMISSION PROVENANCE TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

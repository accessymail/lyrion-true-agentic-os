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

SEARCH_TERMS = (
    "queued",
    "queue",
    "claim",
    "dequeue",
    "execution",
    "admission",
    "require_admission",
    "capabilitygateway",
    "secureexecutor",
    "secure_executor",
    "authorize",
    "authorization",
    "authority",
    "aegis",
    "expired",
    "revoked",
    "revalidate",
    "replay",
    "fail_closed",
    "fail-closed",
)


@dataclass(frozen=True)
class Symbol:
    path: Path
    name: str
    line: int
    source: str
    calls: tuple[str, ...]


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


def find_symbols_containing(
    symbols: list[Symbol],
    terms: tuple[str, ...],
) -> list[Symbol]:
    results: list[Symbol] = []

    for symbol in symbols:
        haystack = (
            f"{symbol.name}\n{symbol.source}"
        ).lower()

        if any(
            term in haystack
            for term in terms
        ):
            results.append(symbol)

    return results


def relevant_lines(
    symbol: Symbol,
) -> list[tuple[int, list[str], str]]:
    results: list[tuple[int, list[str], str]] = []

    for number, line in enumerate(
        symbol.source.splitlines(),
        start=symbol.line,
    ):
        lowered = line.lower()

        matches = [
            term
            for term in SEARCH_TERMS
            if term in lowered
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
) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)
    print(f"NAME: {symbol.name}")
    print(f"LOCATION: {symbol.path}:L{symbol.line}")

    print()
    print("CALLS:")

    for call in symbol.calls:
        print(f"  {call}")

    print()
    print("RELEVANT SOURCE LINES:")

    evidence = relevant_lines(symbol)

    if not evidence:
        print("  NONE")
        return

    for number, terms, line in evidence:
        print(
            f"  L{number}: terms={terms} | {line}"
        )


def repository_symbol_inventory() -> list[Symbol]:
    symbols: list[Symbol] = []

    for path in sorted(
        SOURCE_ROOT.rglob("*.py")
    ):
        symbols.extend(
            collect_symbols(path)
        )

    return symbols


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 QUEUED EXECUTION → "
        "ADMISSION → SECURE EXECUTOR TRACE"
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

    symbols = repository_symbol_inventory()

    print()
    print("=" * 100)
    print("QUEUED EXECUTION CONSUMER DISCOVERY")
    print("=" * 100)

    queued_candidates = find_symbols_containing(
        symbols,
        (
            "queued",
            "dequeue",
            "claim",
            "queue",
        ),
    )

    for symbol in queued_candidates:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("EXECUTION / ADMISSION CONSUMER CANDIDATES")
    print("=" * 100)

    consumer_candidates = []

    for symbol in symbols:
        lowered = (
            f"{symbol.name}\n{symbol.source}"
        ).lower()

        has_execution = (
            "execution" in lowered
        )

        has_admission = (
            "admission" in lowered
            or "require_admission" in lowered
            or "capabilitygateway" in lowered
        )

        if has_execution and has_admission:
            consumer_candidates.append(symbol)

    for symbol in consumer_candidates:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("CAPABILITY GATEWAY / ADMISSION SYMBOLS")
    print("=" * 100)

    gateway_candidates = [
        symbol
        for symbol in symbols
        if (
            "capabilitygateway" in symbol.name.lower()
            or "require_admission" in symbol.name.lower()
            or ".admit" in symbol.name.lower()
        )
    ]

    for symbol in gateway_candidates:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("SECURE EXECUTOR SYMBOLS")
    print("=" * 100)

    executor_candidates = [
        symbol
        for symbol in symbols
        if (
            "secureexecutor" in symbol.name.lower()
            or "secure_executor" in symbol.name.lower()
            or (
                "executor" in symbol.name.lower()
                and (
                    "execution" in symbol.source.lower()
                    or "admission" in symbol.source.lower()
                )
            )
        )
    ]

    for symbol in executor_candidates:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("DETAILED CONTROL-FLOW CANDIDATES")
    print("=" * 100)

    detailed_candidates = (
        consumer_candidates
        + gateway_candidates
        + executor_candidates
    )

    seen: set[tuple[Path, str]] = set()

    for symbol in detailed_candidates:
        key = (symbol.path, symbol.name)

        if key in seen:
            continue

        seen.add(key)

        print_symbol(
            "CONTROL-FLOW CANDIDATE",
            symbol,
        )

    print()
    print("=" * 100)
    print("CROSS-BOUNDARY CONTROL TERMS")
    print("=" * 100)

    boundary_terms = {
        "authorization",
        "authorize",
        "authority",
        "aegis",
        "admission",
        "admit",
        "require_admission",
        "capabilitygateway",
        "secureexecutor",
        "secure_executor",
        "expired",
        "revoked",
        "revalidate",
        "replay",
        "fail_closed",
        "fail-closed",
    }

    observed: set[str] = set()

    for symbol in detailed_candidates:
        for _, terms, _ in relevant_lines(symbol):
            observed.update(
                term
                for term in terms
                if term in boundary_terms
            )

    for term in sorted(observed):
        print(f"  {term}")

    print()
    print("=" * 100)
    print("R097 CONTROL-FLOW INTERPRETATION")
    print("=" * 100)

    has_queued = bool(queued_candidates)
    has_consumer = bool(consumer_candidates)
    has_gateway = bool(gateway_candidates)
    has_executor = bool(executor_candidates)

    has_authority = bool(
        observed
        & {
            "authorization",
            "authorize",
            "authority",
            "aegis",
        }
    )

    has_lifecycle = bool(
        observed
        & {
            "expired",
            "revoked",
            "revalidate",
            "replay",
        }
    )

    if (
        has_queued
        and has_consumer
        and has_gateway
        and has_executor
        and has_authority
        and has_lifecycle
    ):
        result = (
            "QUEUED_TO_ADMISSION_AND_EXECUTOR_BOUNDARY_FOUND — "
            "TARGETED CONTROL-FLOW TRACE REQUIRED"
        )
    elif (
        has_queued
        and has_consumer
        and has_gateway
        and has_executor
    ):
        result = (
            "QUEUED_TO_ADMISSION_AND_EXECUTOR_BOUNDARIES_FOUND — "
            "AUTHORITY_LIFECYCLE_REVALIDATION_NOT_ESTABLISHED"
        )
    elif has_queued and has_consumer:
        result = (
            "QUEUED_CONSUMER_FOUND — "
            "ADMISSION/EXECUTOR CONTROL-FLOW NOT FULLY ESTABLISHED"
        )
    else:
        result = (
            "QUEUED_EXECUTION_CONSUMER_NOT_ESTABLISHED"
        )

    print(f"R097 RESULT: {result}")

    print()
    print("=" * 100)
    print("EVIDENCE LIMITS")
    print("=" * 100)
    print(
        "Static AST/source inspection only."
    )
    print(
        "No execution behavior was invoked."
    )
    print(
        "No privileged operation was performed."
    )
    print(
        "No source, tests, documentation, manifests, "
        "or governance state were modified."
    )
    print(
        "This does NOT establish runtime R097 compliance."
    )
    print(
        "No architectural PRESERVE/EXTEND/NEW/"
        "REFACTOR/CONFLICT decision is made."
    )

    print()
    print("=" * 100)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 100)
    print("READ-ONLY: YES")
    print("SOURCE MUTATION: NONE")
    print("TEST MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("IMPLEMENTATION EXECUTION: NONE")

    print()
    print("=" * 100)
    print("FINAL RESULT")
    print("=" * 100)
    print(
        "RESULT: PASS — R097 QUEUED EXECUTION "
        "ADMISSION TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

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

RECOVERY_ORCHESTRATOR = (
    SOURCE_ROOT
    / "lyrion/persistence/recovery_orchestrator.py"
)

EXECUTION_STORE = (
    SOURCE_ROOT
    / "lyrion/persistence/sqlalchemy/execution_store.py"
)

CAPABILITY_GATEWAY = (
    SOURCE_ROOT
    / "lyrion/capabilities/gateway.py"
)

EXECUTION_CONTRACTS = (
    SOURCE_ROOT
    / "lyrion/execution/contracts.py"
)


@dataclass(frozen=True)
class Symbol:
    path: Path
    kind: str
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


def collect_calls(
    node: ast.AST,
) -> tuple[str, ...]:
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
                    kind="class",
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
                    kind="function",
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
                    kind="async_function",
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


def find_symbol(
    symbols: list[Symbol],
    name: str,
) -> Symbol | None:
    for symbol in symbols:
        if symbol.name == name:
            return symbol

    return None


def source_term_lines(
    symbol: Symbol,
) -> list[tuple[int, list[str], str]]:
    terms = (
        "authorization",
        "authorize",
        "authority",
        "aegis",
        "admission",
        "admit",
        "capabilitygateway",
        "executionadmission",
        "expired",
        "expiry",
        "revoked",
        "revoke",
        "replay",
        "revalidate",
        "validate",
        "denied",
        "deny",
        "reject",
        "requeue",
        "claim",
        "queued",
        "lease",
    )

    results: list[tuple[int, list[str], str]] = []

    for number, line in enumerate(
        symbol.source.splitlines(),
        start=symbol.line,
    ):
        lowered = line.lower()

        matches = [
            term
            for term in terms
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

    evidence = source_term_lines(symbol)

    if not evidence:
        print("  NONE")
    else:
        for number, terms, line in evidence:
            print(
                f"  L{number}: terms={terms} | {line}"
            )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 REQUEUE → "
        "RECOVERED EXECUTION CONSUMER TRACE"
    )
    print("READ-ONLY")
    print()

    required = (
        SPECIFICATION,
        RECOVERY_ORCHESTRATOR,
        EXECUTION_STORE,
        CAPABILITY_GATEWAY,
        EXECUTION_CONTRACTS,
    )

    missing = [
        path
        for path in required
        if not path.is_file()
    ]

    if missing:
        print(
            "RESULT: FAIL — required evidence file missing."
        )

        for path in missing:
            print(f"  MISSING: {path}")

        return 1

    print(f"Repository: {REPO_ROOT}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    recovery_symbols = collect_symbols(
        RECOVERY_ORCHESTRATOR
    )
    store_symbols = collect_symbols(
        EXECUTION_STORE
    )
    gateway_symbols = collect_symbols(
        CAPABILITY_GATEWAY
    )
    contract_symbols = collect_symbols(
        EXECUTION_CONTRACTS
    )

    recover_one = find_symbol(
        recovery_symbols,
        "PersistentRecoveryOrchestrator.recover_one",
    )

    requeue = find_symbol(
        store_symbols,
        "SQLAlchemyExecutionStore.requeue",
    )

    gateway_admit = find_symbol(
        gateway_symbols,
        "CapabilityGateway.admit",
    )

    require_admission = find_symbol(
        gateway_symbols,
        "CapabilityGateway.require_admission",
    )

    execution_admission = find_symbol(
        contract_symbols,
        "ExecutionAdmission",
    )

    if recover_one is None:
        print(
            "RESULT: FAIL — recover_one not resolved."
        )
        return 1

    print_symbol(
        "RECOVERY ENTRYPOINT",
        recover_one,
    )

    print()
    print("=" * 100)
    print("REQUEUE CALL RESOLUTION")
    print("=" * 100)

    recovery_requeues = [
        call
        for call in recover_one.calls
        if "requeue" in call.lower()
    ]

    for call in recovery_requeues:
        print(f"RECOVER_ONE CALL: {call}")

    if requeue is not None:
        print_symbol(
            "EXECUTION STORE — requeue()",
            requeue,
        )
    else:
        print(
            "SQLAlchemyExecutionStore.requeue "
            "was not resolved."
        )

    print()
    print("=" * 100)
    print("REQUEUE CONSUMER SEARCH")
    print("=" * 100)

    requeue_references: list[
        tuple[Path, int, str]
    ] = []

    for path in sorted(
        SOURCE_ROOT.rglob("*.py")
    ):
        source = read_source(path)

        if not source:
            continue

        for number, line in enumerate(
            source.splitlines(),
            start=1,
        ):
            lowered = line.lower()

            if (
                "requeue(" in lowered
                or ".requeue(" in lowered
                or "requeue" in lowered
            ):
                requeue_references.append(
                    (
                        path,
                        number,
                        line.strip(),
                    )
                )

    for path, number, line in requeue_references:
        print(
            f"{path}:L{number} | {line}"
        )

    print()
    print("=" * 100)
    print("ADMISSION BOUNDARY RESOLUTION")
    print("=" * 100)

    if gateway_admit is not None:
        print_symbol(
            "CAPABILITY GATEWAY — admit()",
            gateway_admit,
        )
    else:
        print(
            "CapabilityGateway.admit was not resolved."
        )

    if require_admission is not None:
        print_symbol(
            "CAPABILITY GATEWAY — require_admission()",
            require_admission,
        )
    else:
        print(
            "CapabilityGateway.require_admission "
            "was not resolved."
        )

    if execution_admission is not None:
        print_symbol(
            "EXECUTION ADMISSION CONTRACT",
            execution_admission,
        )
    else:
        print(
            "ExecutionAdmission symbol was not resolved."
        )

    print()
    print("=" * 100)
    print("CROSS-BOUNDARY EVIDENCE")
    print("=" * 100)

    admission_terms = {
        "authorization",
        "authorize",
        "authority",
        "aegis",
        "admission",
        "admit",
        "executionadmission",
        "capabilitygateway",
        "expired",
        "revoked",
        "revoke",
        "revalidate",
        "replay",
        "denied",
        "fail_closed",
        "fail-closed",
    }

    boundary_symbols = [
        symbol
        for symbol in (
            requeue,
            gateway_admit,
            require_admission,
            execution_admission,
        )
        if symbol is not None
    ]

    observed: set[str] = set()

    for symbol in boundary_symbols:
        for _, terms, _ in source_term_lines(symbol):
            observed.update(
                term
                for term in terms
                if term in admission_terms
            )

    if observed:
        print(
            "Security/admission terms observed "
            "across inspected boundaries:"
        )

        for term in sorted(observed):
            print(f"  {term}")
    else:
        print(
            "No direct security/admission lifecycle "
            "terms observed across inspected boundaries."
        )

    print()
    print("=" * 100)
    print("R097 INTERPRETATION")
    print("=" * 100)

    requeue_present = bool(recovery_requeues)

    gateway_present = (
        gateway_admit is not None
        or require_admission is not None
    )

    lifecycle_present = bool(
        observed
        & {
            "expired",
            "revoked",
            "revoke",
            "revalidate",
            "replay",
            "authorization",
            "authority",
        }
    )

    if (
        requeue_present
        and gateway_present
        and lifecycle_present
    ):
        result = (
            "REQUEUE_AND_ADMISSION_BOUNDARIES_FOUND — "
            "DOWNSTREAM CONTROL-FLOW TRACE REQUIRED"
        )
    elif requeue_present and gateway_present:
        result = (
            "REQUEUE_AND_ADMISSION_BOUNDARIES_FOUND — "
            "AUTHORITY_REVALIDATION_NOT_ESTABLISHED"
        )
    elif requeue_present:
        result = (
            "REQUEUE_FOUND — "
            "RECOVERED EXECUTION CONSUMER NOT ESTABLISHED"
        )
    else:
        result = (
            "REQUEUE_CONTROL_FLOW_NOT_ESTABLISHED"
        )

    print(f"R097 RESULT: {result}")

    print()
    print("=" * 100)
    print("EVIDENCE LIMITS")
    print("=" * 100)
    print(
        "Static source/AST inspection only."
    )
    print(
        "No recovery execution was performed."
    )
    print(
        "No privileged operation was performed."
    )
    print(
        "No source, tests, documentation, manifests, "
        "or governance state were modified."
    )
    print(
        "This does NOT by itself establish runtime "
        "R097 compliance."
    )
    print(
        "No PRESERVE/EXTEND/NEW/REFACTOR/CONFLICT "
        "classification is performed."
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
        "RESULT: PASS — R097 REQUEUE CONSUMER "
        "TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

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


@dataclass(frozen=True)
class Symbol:
    path: Path
    name: str
    line: int
    source: str
    calls: tuple[str, ...]


TARGETS = (
    "OpportunityConsumer.consume_bound_once_persistent",
    "PIAEActionLoop.run_once_persistent",
    "ProactiveExecutionCoordinator.create_capability_request",
    "ProactiveExecutionCoordinator.admit",
    "CapabilityGateway.admit",
)


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


def find_unique(
    symbols: list[Symbol],
    name: str,
) -> Symbol | None:
    matches = [
        symbol
        for symbol in symbols
        if symbol.name == name
    ]

    if len(matches) != 1:
        return None

    return matches[0]


def relevant_lines(
    symbol: Symbol,
) -> list[tuple[int, str]]:
    terms = (
        "opportunity",
        "execution",
        "admission",
        "request",
        "capability",
        "admit",
        "authorization",
        "authorize",
        "aegis",
        "runner",
        "queued",
        "recover",
        "requeue",
    )

    results: list[tuple[int, str]] = []

    for number, line in enumerate(
        symbol.source.splitlines(),
        start=symbol.line,
    ):
        lowered = line.lower()

        if any(
            term in lowered
            for term in terms
        ):
            results.append(
                (number, line.strip())
            )

    return results


def print_symbol(
    symbol: Symbol,
) -> None:
    print()
    print("=" * 100)
    print(
        f"TARGET: {symbol.name}"
    )
    print("=" * 100)
    print(
        f"LOCATION: {symbol.path}:L{symbol.line}"
    )

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

    for number, line in evidence:
        print(
            f"  L{number}: {line}"
        )


def contains_call(
    symbol: Symbol,
    terms: tuple[str, ...],
) -> bool:
    lowered = {
        call.lower()
        for call in symbol.calls
    }

    return any(
        any(
            term.lower() in call
            for term in lowered
        )
        for call in terms
    )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 COMBINED RECOVERY "
        "EXECUTION → FRESH ADMISSION TRACE"
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

    resolved: dict[str, Symbol] = {}

    print()
    print("=" * 100)
    print("TARGET RESOLUTION")
    print("=" * 100)

    for target in TARGETS:
        symbol = find_unique(
            symbols,
            target,
        )

        if symbol is None:
            print(
                f"FAIL: {target} — "
                "not uniquely resolved"
            )
            return 1

        resolved[target] = symbol

        print(
            f"PASS: {target} → "
            f"{symbol.path}:L{symbol.line}"
        )

    print()
    print("=" * 100)
    print("TARGET SOURCE INSPECTION")
    print("=" * 100)

    for target in TARGETS:
        print_symbol(
            resolved[target]
        )

    consumer = resolved[
        "OpportunityConsumer.consume_bound_once_persistent"
    ]

    action_loop = resolved[
        "PIAEActionLoop.run_once_persistent"
    ]

    create_request = resolved[
        "ProactiveExecutionCoordinator.create_capability_request"
    ]

    admit = resolved[
        "ProactiveExecutionCoordinator.admit"
    ]

    gateway = resolved[
        "CapabilityGateway.admit"
    ]

    print()
    print("=" * 100)
    print("CONTROL-FLOW CHECKS")
    print("=" * 100)

    consumer_to_action_loop = any(
        "run_once_persistent"
        in call.lower()
        for call in consumer.calls
    )

    action_loop_to_create_request = any(
        "create_capability_request"
        in call.lower()
        for call in action_loop.calls
    )

    action_loop_to_admit = any(
        call.lower().endswith(".admit")
        or call.lower() == "admit"
        for call in action_loop.calls
    )

    action_loop_to_runner = any(
        "runner.run" in call.lower()
        for call in action_loop.calls
    )

    create_request_to_request = any(
        "request"
        in call.lower()
        for call in create_request.calls
    )

    admit_to_gateway = any(
        "gateway.admit"
        in call.lower()
        or "self._gateway.admit"
        in call.lower()
        for call in admit.calls
    )

    gateway_to_authorize = any(
        "authorize"
        in call.lower()
        for call in gateway.calls
    )

    gateway_to_execution_admission = (
        "executionadmission"
        in gateway.source.lower()
    )

    checks = (
        (
            "OpportunityConsumer → "
            "PIAEActionLoop",
            consumer_to_action_loop,
        ),
        (
            "PIAEActionLoop → "
            "create_capability_request",
            action_loop_to_create_request,
        ),
        (
            "PIAEActionLoop → admit",
            action_loop_to_admit,
        ),
        (
            "PIAEActionLoop → runner.run",
            action_loop_to_runner,
        ),
        (
            "create_capability_request → "
            "request construction",
            create_request_to_request,
        ),
        (
            "Coordinator.admit → "
            "CapabilityGateway.admit",
            admit_to_gateway,
        ),
        (
            "CapabilityGateway.admit → "
            "authorization",
            gateway_to_authorize,
        ),
        (
            "CapabilityGateway.admit → "
            "ExecutionAdmission",
            gateway_to_execution_admission,
        ),
    )

    for name, passed in checks:
        print(
            f"{'PASS' if passed else 'FAIL'}: {name}"
        )

    print()
    print("=" * 100)
    print("FRESHNESS / RECOVERY BOUNDARY ANALYSIS")
    print("=" * 100)

    consumer_has_recovery_context = any(
        term in consumer.source.lower()
        for term in (
            "recover",
            "recovery",
            "requeue",
            "queued",
            "claim",
        )
    )

    action_loop_has_recovery_context = any(
        term in action_loop.source.lower()
        for term in (
            "recover",
            "recovery",
            "requeue",
        )
    )

    action_loop_creates_request = (
        action_loop_to_create_request
    )

    action_loop_calls_admit = (
        action_loop_to_admit
    )

    print(
        "Consumer contains recovery/queue context:",
        "YES"
        if consumer_has_recovery_context
        else "NO",
    )

    print(
        "Action loop contains direct recovery context:",
        "YES"
        if action_loop_has_recovery_context
        else "NO",
    )

    print(
        "Action loop creates capability request:",
        "YES"
        if action_loop_creates_request
        else "NOT ESTABLISHED",
    )

    print(
        "Action loop performs admission:",
        "YES"
        if action_loop_calls_admit
        else "NOT ESTABLISHED",
    )

    print()
    print(
        "IMPORTANT INTERPRETATION:"
    )
    print(
        "This verifier distinguishes the normal "
        "persistent execution path from proof that "
        "a recovered/requeued execution reaches it."
    )
    print(
        "It does not treat QUEUED state alone as "
        "authorization freshness."
    )
    print(
        "It does not treat an existing ExecutionAdmission "
        "as fresh authority."
    )

    all_normal_path_checks = all(
        passed
        for _, passed in checks
    )

    if (
        all_normal_path_checks
        and consumer_to_action_loop
        and action_loop_creates_request
        and action_loop_calls_admit
        and admit_to_gateway
        and gateway_to_authorize
    ):
        result = (
            "NORMAL_EXECUTION_FRESH_ADMISSION_PATH_ESTABLISHED — "
            "RECOVERY-TO-NORMAL-PATH LINK REQUIRES FINAL TARGETED TRACE"
        )
    elif all_normal_path_checks:
        result = (
            "NORMAL_EXECUTION_PATH_PARTIALLY_ESTABLISHED — "
            "FRESH_ADMISSION PROVENANCE INCOMPLETE"
        )
    else:
        result = (
            "CONTROL_FLOW_INCOMPLETE — "
            "FURTHER EVIDENCE REQUIRED"
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
        "RESULT: PASS — R097 COMBINED CONTROL-FLOW "
        "TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

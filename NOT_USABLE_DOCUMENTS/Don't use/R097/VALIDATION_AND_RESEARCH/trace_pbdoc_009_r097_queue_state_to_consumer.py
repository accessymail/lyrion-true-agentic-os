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


@dataclass(frozen=True)
class CallSite:
    path: Path
    line: int
    caller: str
    callee: str
    source_line: str


TARGETS = (
    "PersistentRecoveryOrchestrator.recover_one",
    "SQLAlchemyExecutionStore.requeue",
    "OpportunityConsumer.consume_bound_once_persistent",
    "PIAEActionLoop.run_once_persistent",
)


QUEUE_TERMS = (
    "QUEUED",
    "queued",
    "queue",
    "dequeue",
    "enqueue",
    "claim",
    "poll",
    "consume",
    "opportunity",
)


RECOVERY_TERMS = (
    "recover",
    "recovery",
    "requeue",
    "checkpoint",
    "resume",
)


ADMISSION_TERMS = (
    "create_capability_request",
    "ExecutionAdmission",
    "admit",
    "CapabilityGateway",
    "authorize",
    "authorization",
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
            return ".".join(
                self.class_stack
                + self.function_stack
            ) or "<module>"

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
                line = getattr(node, "lineno", 1)

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
) -> list[tuple[int, str]]:
    results: list[tuple[int, str]] = []

    for number, line in enumerate(
        symbol.source.splitlines(),
        start=symbol.line,
    ):
        lowered = line.lower()

        if any(
            term.lower() in lowered
            for term in terms
        ):
            results.append(
                (number, line.strip())
            )

    return results


def print_symbol(
    symbol: Symbol,
    terms: tuple[str, ...],
) -> None:
    print()
    print("=" * 100)
    print(f"TARGET: {symbol.name}")
    print("=" * 100)
    print(
        f"LOCATION: {symbol.path}:L{symbol.line}"
    )

    print()
    print("CALLS:")

    for call in symbol.calls:
        print(f"  {call}")

    print()
    print("RELEVANT SOURCE:")

    lines = relevant_lines(
        symbol,
        terms,
    )

    if not lines:
        print("  NONE")
        return

    for number, line in lines:
        print(
            f"  L{number}: {line}"
        )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 QUEUED STATE → "
        "QUEUE CONSUMER TRACE"
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
            resolved[target],
            QUEUE_TERMS
            + RECOVERY_TERMS
            + ADMISSION_TERMS,
        )

    recover_one = resolved[
        "PersistentRecoveryOrchestrator.recover_one"
    ]

    requeue = resolved[
        "SQLAlchemyExecutionStore.requeue"
    ]

    consumer = resolved[
        "OpportunityConsumer.consume_bound_once_persistent"
    ]

    action_loop = resolved[
        "PIAEActionLoop.run_once_persistent"
    ]

    print()
    print("=" * 100)
    print("RECOVERY → REQUEUE")
    print("=" * 100)

    recovery_calls_requeue = any(
        "requeue" in call.lower()
        for call in recover_one.calls
    )

    requeue_sets_queued = any(
        "queued" in line.lower()
        for _, line in relevant_lines(
            requeue,
            ("QUEUED", "queued"),
        )
    )

    requeue_clears_claim = (
        "lease_id" in requeue.source
        and "claimed_at" in requeue.source
    )

    print(
        "recover_one() → requeue():",
        "PASS"
        if recovery_calls_requeue
        else "FAIL",
    )

    print(
        "requeue() establishes QUEUED state:",
        "PASS"
        if requeue_sets_queued
        else "NOT ESTABLISHED",
    )

    print(
        "requeue() clears claim state:",
        "PASS"
        if requeue_clears_claim
        else "NOT ESTABLISHED",
    )

    print()
    print("=" * 100)
    print("QUEUE / DEQUEUE BOUNDARY")
    print("=" * 100)

    queue_symbols = [
        symbol
        for symbol in symbols
        if any(
            term.lower() in symbol.source.lower()
            for term in QUEUE_TERMS
        )
        and (
            "queue" in symbol.name.lower()
            or "consumer" in symbol.name.lower()
            or "opportunity" in symbol.name.lower()
            or "dequeue" in symbol.name.lower()
            or "claim" in symbol.name.lower()
        )
    ]

    for symbol in queue_symbols:
        print(
            f"{symbol.path}:L{symbol.line} | "
            f"{symbol.name}"
        )

    print()
    print("=" * 100)
    print("CALLERS OF QUEUE / CONSUMER BOUNDARIES")
    print("=" * 100)

    consumer_callers = find_callers(
        {
            "self._queue.dequeue",
            "queue.dequeue",
            "self._opportunity_queue.dequeue",
            "dequeue",
            "consume_bound_once_persistent",
            "self._action_loop.run_once_persistent",
        }
    )

    for caller in consumer_callers:
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
    print("CONSUMER → ACTION LOOP")
    print("=" * 100)

    consumer_to_action_loop = any(
        "run_once_persistent"
        in call.lower()
        for call in consumer.calls
    )

    print(
        "OpportunityConsumer → PIAEActionLoop:",
        "PASS"
        if consumer_to_action_loop
        else "FAIL",
    )

    print()
    print("=" * 100)
    print("ACTION LOOP → FRESH ADMISSION")
    print("=" * 100)

    action_creates_request = any(
        "create_capability_request"
        in call.lower()
        for call in action_loop.calls
    )

    action_admits = any(
        call.lower().endswith(".admit")
        or call.lower() == "admit"
        for call in action_loop.calls
    )

    action_passes_admission = (
        "admission=admission"
        in action_loop.source
    )

    print(
        "Action loop creates capability request:",
        "PASS"
        if action_creates_request
        else "FAIL",
    )

    print(
        "Action loop performs admission:",
        "PASS"
        if action_admits
        else "FAIL",
    )

    print(
        "Action loop passes resulting admission:",
        "PASS"
        if action_passes_admission
        else "NOT ESTABLISHED",
    )

    print()
    print("=" * 100)
    print("R097 DECISIVE BOUNDARY")
    print("=" * 100)

    recovery_to_queue = (
        recovery_calls_requeue
        and requeue_sets_queued
    )

    queue_to_consumer = (
        bool(consumer_callers)
        and consumer_to_action_loop
    )

    consumer_to_fresh_admission = (
        action_creates_request
        and action_admits
        and action_passes_admission
    )

    print(
        "RECOVERY → QUEUED:",
        "ESTABLISHED"
        if recovery_to_queue
        else "NOT ESTABLISHED",
    )

    print(
        "QUEUED → CONSUMER:",
        "ESTABLISHED"
        if queue_to_consumer
        else "NOT ESTABLISHED",
    )

    print(
        "CONSUMER → FRESH ADMISSION:",
        "ESTABLISHED"
        if consumer_to_fresh_admission
        else "NOT ESTABLISHED",
    )

    print()
    print(
        "IMPORTANT:"
    )
    print(
        "This verifier does not assume that a QUEUED "
        "database state automatically enters the consumer."
    )
    print(
        "It also does not assume that an existing "
        "ExecutionAdmission remains valid after recovery."
    )
    print(
        "Only an explicit control-flow relationship "
        "can establish the R097 recovery revalidation path."
    )

    if (
        recovery_to_queue
        and queue_to_consumer
        and consumer_to_fresh_admission
    ):
        result = (
            "R097_RECOVERY_TO_FRESH_ADMISSION_PATH_ESTABLISHED"
        )
    elif (
        recovery_to_queue
        and queue_to_consumer
    ):
        result = (
            "R097_RECOVERY_TO_CONSUMER_ESTABLISHED — "
            "FRESH_ADMISSION_LINK INCOMPLETE"
        )
    elif recovery_to_queue:
        result = (
            "R097_RECOVERY_TO_QUEUED_ESTABLISHED — "
            "QUEUE_CONSUMER LINK INCOMPLETE"
        )
    else:
        result = (
            "R097_RECOVERY_QUEUE_CONTROL_FLOW "
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
        "RESULT: PASS — R097 QUEUE STATE → "
        "CONSUMER TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

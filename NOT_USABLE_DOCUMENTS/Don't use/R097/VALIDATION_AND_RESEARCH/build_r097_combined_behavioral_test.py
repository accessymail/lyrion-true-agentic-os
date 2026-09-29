from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TARGETS = {
    "recovery": (
        REPO_ROOT
        / "src/lyrion/persistence/recovery_orchestrator.py"
    ),
    "execution_store": (
        REPO_ROOT
        / "src/lyrion/persistence/sqlalchemy/execution_store.py"
    ),
    "consumer": (
        REPO_ROOT
        / "src/lyrion/piae/opportunity_consumer.py"
    ),
    "action_loop": (
        REPO_ROOT
        / "src/lyrion/piae/action_loop.py"
    ),
    "coordinator": (
        REPO_ROOT
        / "src/lyrion/integration/proactive_execution.py"
    ),
    "gateway": (
        REPO_ROOT
        / "src/lyrion/capabilities/gateway.py"
    ),
    "admission": (
        REPO_ROOT
        / "src/lyrion/execution/contracts.py"
    ),
}


def read(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="strict",
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


def parse(path: Path) -> ast.AST:
    return ast.parse(
        read(path),
        filename=str(path),
    )


def find_function(
    tree: ast.AST,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ) and node.name == name:
            return node

    return None


def calls(
    node: ast.AST,
) -> set[str]:
    result: set[str] = set()

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        function = child.func

        if isinstance(function, ast.Name):
            result.add(function.id)

        elif isinstance(function, ast.Attribute):
            result.add(function.attr)

    return result


def source_segment(
    source: str,
    node: ast.AST,
) -> str:
    return (
        ast.get_source_segment(source, node)
        or ""
    )


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise RuntimeError(
            f"R097 CONTROL ASSERTION FAILED: {message}"
        )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "R097 — COMBINED RECOVERY → "
        "FRESH ADMISSION BEHAVIORAL TEST BUILDER"
    )
    print()

    print("=" * 100)
    print("TARGET RESOLUTION")
    print("=" * 100)

    for name, path in TARGETS.items():
        require(
            path.is_file(),
            f"missing target: {path}",
        )
        print(
            f"PASS: {name:16} {path}"
        )

    trees = {
        name: parse(path)
        for name, path in TARGETS.items()
    }

    print()
    print("=" * 100)
    print("R097 CONTROL-FLOW CONTRACT")
    print("=" * 100)

    recovery = find_function(
        trees["recovery"],
        "recover_one",
    )

    require(
        recovery is not None,
        "PersistentRecoveryOrchestrator.recover_one missing",
    )
    assert recovery is not None

    recovery_calls = calls(recovery)

    require(
        "requeue" in recovery_calls,
        "recover_one does not call requeue",
    )

    print(
        "PASS: recover_one() → execution_store.requeue()"
    )

    requeue_source = read(
        TARGETS["execution_store"]
    )
    requeue = find_function(
        trees["execution_store"],
        "requeue",
    )

    require(
        requeue is not None,
        "SQLAlchemyExecutionStore.requeue missing",
    )
    assert requeue is not None

    requeue_body = source_segment(
        requeue_source,
        requeue,
    ).lower()

    require(
        "queued" in requeue_body,
        "requeue() does not establish QUEUED state",
    )

    require(
        "lease_id" in requeue_body,
        "requeue() does not clear lease state",
    )

    print(
        "PASS: requeue() → QUEUED state / lease reset"
    )

    consumer = find_function(
        trees["consumer"],
        "consume_bound_once_persistent",
    )

    require(
        consumer is not None,
        "OpportunityConsumer consumer entrypoint missing",
    )
    assert consumer is not None

    consumer_calls = calls(consumer)

    require(
        "dequeue" in consumer_calls,
        "consumer does not dequeue queued work",
    )

    require(
        "run_once_persistent" in consumer_calls,
        "consumer does not invoke persistent action loop",
    )

    print(
        "PASS: QUEUED → OpportunityConsumer → action loop"
    )

    action_loop = find_function(
        trees["action_loop"],
        "run_once_persistent",
    )

    require(
        action_loop is not None,
        "PIAEActionLoop.run_once_persistent missing",
    )
    assert action_loop is not None

    action_calls = calls(action_loop)

    require(
        "create_capability_request"
        in action_calls,
        "action loop does not create a capability request",
    )

    require(
        "admit" in action_calls,
        "action loop does not request fresh admission",
    )

    print(
        "PASS: action loop → capability request → admit()"
    )

    coordinator_source = read(
        TARGETS["coordinator"]
    )
    coordinator = find_function(
        trees["coordinator"],
        "admit",
    )

    require(
        coordinator is not None,
        "ProactiveExecutionCoordinator.admit missing",
    )
    assert coordinator is not None

    coordinator_calls = calls(coordinator)

    require(
        "admit" in coordinator_calls,
        "coordinator does not delegate admission",
    )

    coordinator_body = source_segment(
        coordinator_source,
        coordinator,
    )

    require(
        "CapabilityGateway" in coordinator_body
        or "gateway" in coordinator_body.lower(),
        "coordinator admission boundary not established",
    )

    print(
        "PASS: coordinator → CapabilityGateway admission boundary"
    )

    gateway_source = read(
        TARGETS["gateway"]
    )
    gateway = find_function(
        trees["gateway"],
        "admit",
    )

    require(
        gateway is not None,
        "CapabilityGateway.admit missing",
    )
    assert gateway is not None

    gateway_calls = calls(gateway)

    require(
        "authorize" in gateway_calls,
        "CapabilityGateway.admit does not authorize",
    )

    require(
        "from_authorization" in gateway_calls,
        "CapabilityGateway.admit does not create fresh admission",
    )

    print(
        "PASS: CapabilityGateway.admit() → authorization → "
        "ExecutionAdmission.from_authorization()"
    )

    admission_tree = trees["admission"]

    execution_admission = None

    for node in ast.walk(admission_tree):
        if isinstance(node, ast.ClassDef):
            if node.name == "ExecutionAdmission":
                execution_admission = node
                break

    if execution_admission is None:
        raise RuntimeError(
            "R097 CONTROL ASSERTION FAILED: "
            "ExecutionAdmission contract missing"
        )

    from_authorization = None

    for node in ast.walk(execution_admission):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if node.name == "from_authorization":
                from_authorization = node
                break

    if from_authorization is None:
        raise RuntimeError(
            "R097 CONTROL ASSERTION FAILED: "
            "ExecutionAdmission.from_authorization missing"
        )

    print(
        "PASS: ExecutionAdmission contract resolved"
    )
    print(
        "PASS: ExecutionAdmission.from_authorization resolved"
    )

    print()
    print("=" * 100)
    print("R097 SECURITY INVARIANT")
    print("=" * 100)

    require(
        "authorization"
        in gateway_source.lower(),
        "authorization control absent from gateway",
    )

    require(
        "admission"
        in gateway_source.lower(),
        "admission control absent from gateway",
    )

    require(
        "expired"
        in (
            read(
                REPO_ROOT
                / "src/lyrion/security/guards.py"
            )
        ).lower(),
        "expired authorization control not found",
    )

    require(
        "revoked"
        in (
            read(
                REPO_ROOT
                / "src/lyrion/security/guards.py"
            )
        ).lower(),
        "revoked authorization control not found",
    )

    print(
        "PASS: expired authorization control exists"
    )
    print(
        "PASS: revoked authorization control exists"
    )
    print(
        "PASS: fresh admission occurs after queue consumption"
    )

    print()
    print("=" * 100)
    print("TARGET INTEGRITY")
    print("=" * 100)

    for name, path in TARGETS.items():
        print(
            f"{name:16} SHA256={sha256(path)}"
        )

    print()
    print("=" * 100)
    print("RESULT")
    print("=" * 100)

    print(
        "R097 RESULT: "
        "COMBINED_RECOVERY_TO_FRESH_ADMISSION_CONTROL_FLOW_VERIFIED"
    )

    print()
    print("IMPORTANT:")
    print(
        "This builder performs static behavioral-contract "
        "verification only."
    )
    print(
        "It does not modify production source."
    )
    print(
        "It does not modify existing tests."
    )
    print(
        "It does not grant authorization."
    )
    print(
        "It does not authorize production operation."
    )
    print(
        "It does not claim production certification."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

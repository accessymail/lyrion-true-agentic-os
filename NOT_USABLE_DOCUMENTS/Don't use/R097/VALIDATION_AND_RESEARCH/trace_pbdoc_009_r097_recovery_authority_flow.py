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

RECOVERY_FILE = (
    REPO_ROOT
    / "src/lyrion/persistence/recovery.py"
)

AUTHORIZATION_FILES = (
    REPO_ROOT / "src/lyrion/security/authorization.py",
    REPO_ROOT / "src/lyrion/security/guards.py",
    REPO_ROOT / "src/lyrion/security/policy.py",
    REPO_ROOT / "src/lyrion/security/rules.py",
    REPO_ROOT / "src/lyrion/security/replay.py",
)

GATEWAY_FILE = (
    REPO_ROOT / "src/lyrion/capabilities/gateway.py"
)

CHECKPOINT_FILE = (
    REPO_ROOT / "src/lyrion/execution/checkpoint.py"
)


@dataclass(frozen=True)
class FunctionInfo:
    path: Path
    qualified_name: str
    line: int
    source: str
    calls: tuple[str, ...]


@dataclass(frozen=True)
class Evidence:
    path: Path
    line: int
    category: str
    text: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_source(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, UnicodeError):
        return ""


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
    calls = {
        call_name(item)
        for item in ast.walk(node)
        if isinstance(item, ast.Call)
    }

    return tuple(sorted(calls))


def collect_functions(path: Path) -> list[FunctionInfo]:
    source = read_source(path)

    if not source:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    functions: list[FunctionInfo] = []

    class FunctionCollector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.prefix: list[str] = []

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self.prefix.append(node.name)
            self.generic_visit(node)
            self.prefix.pop()

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            qualified_name = ".".join(
                [*self.prefix, node.name]
            )

            segment = ast.get_source_segment(
                source,
                node,
            ) or ""

            functions.append(
                FunctionInfo(
                    path=path,
                    qualified_name=qualified_name,
                    line=node.lineno,
                    source=segment,
                    calls=collect_calls(node),
                )
            )

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            qualified_name = ".".join(
                [*self.prefix, node.name]
            )

            segment = ast.get_source_segment(
                source,
                node,
            ) or ""

            functions.append(
                FunctionInfo(
                    path=path,
                    qualified_name=qualified_name,
                    line=node.lineno,
                    source=segment,
                    calls=collect_calls(node),
                )
            )

    collector = FunctionCollector()
    collector.visit(tree)

    return functions


def find_function(
    path: Path,
    qualified_name: str,
) -> FunctionInfo | None:
    for function in collect_functions(path):
        if function.qualified_name == qualified_name:
            return function

    return None


def relevant_lines(
    path: Path,
) -> list[Evidence]:
    source = read_source(path)

    if not source:
        return []

    terms = (
        "authorization",
        "authority",
        "authorize",
        "is_authorized",
        "admission",
        "admit",
        "capabilitygateway",
        "executionadmission",
        "expired",
        "expiry",
        "revoked",
        "revoke",
        "replay",
        "checkpoint",
        "recovery",
        "recover",
        "restore",
        "resume",
        "revalidate",
        "validate",
        "deny",
        "denied",
        "reject",
        "fail",
        "fail_closed",
        "fail-closed",
    )

    evidence: list[Evidence] = []

    for line_number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        matched = [
            term
            for term in terms
            if term in lowered
        ]

        if matched:
            evidence.append(
                Evidence(
                    path=path,
                    line=line_number,
                    category="CONTROL_TERM",
                    text=(
                        f"terms={matched} | "
                        f"{line.strip()}"
                    ),
                )
            )

    return evidence


def classify_function(
    function: FunctionInfo,
) -> tuple[str, ...]:
    source = function.source.lower()
    calls = " ".join(function.calls).lower()

    markers: list[str] = []

    if any(
        term in source
        for term in (
            "authorization",
            "authorize",
            "is_authorized",
            "authority",
        )
    ):
        markers.append("AUTHORIZATION_REFERENCE")

    if any(
        term in source
        for term in (
            "admission",
            "admit",
            "executionadmission",
            "capabilitygateway",
        )
    ):
        markers.append("ADMISSION_REFERENCE")

    if any(
        term in source
        for term in (
            "expired",
            "expiry",
            "revoked",
            "revoke",
        )
    ):
        markers.append("EXPIRY_REVOCATION_REFERENCE")

    if any(
        term in source
        for term in (
            "checkpoint",
            "recovery",
            "recover",
            "restore",
            "resume",
        )
    ):
        markers.append("RECOVERY_REFERENCE")

    if any(
        term in source
        for term in (
            "revalidate",
            "validate",
            "deny",
            "denied",
            "reject",
            "fail_closed",
            "fail-closed",
        )
    ):
        markers.append("VALIDATION_OR_DENIAL_REFERENCE")

    if any(
        token in calls
        for token in (
            "authorize",
            "is_authorized",
            "admit",
            "recover_one",
        )
    ):
        markers.append("SECURITY_CALL")

    return tuple(sorted(set(markers)))


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — R097 RECOVERY → AUTHORITY "
        "CONTROL-FLOW TRACE"
    )
    print("READ-ONLY")
    print()

    required_files = (
        SPECIFICATION,
        RECOVERY_FILE,
        *AUTHORIZATION_FILES,
        GATEWAY_FILE,
        CHECKPOINT_FILE,
    )

    missing = [
        path
        for path in required_files
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
    print(f"Specification: {SPECIFICATION}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    print()
    print("=" * 100)
    print("PRIMARY RECOVERY ENTRYPOINT")
    print("=" * 100)

    recovery_entry = find_function(
        RECOVERY_FILE,
        "PersistentRecoveryOrchestrator.recover_one",
    )

    if recovery_entry is None:
        print(
            "RESULT: FAIL — "
            "PersistentRecoveryOrchestrator.recover_one "
            "was not resolved."
        )
        return 1

    print(
        f"RESOLVED: {recovery_entry.path}:"
        f"L{recovery_entry.line}"
    )

    print()
    print("DIRECT CALLS FROM recover_one():")

    for call in recovery_entry.calls:
        print(f"  CALL: {call}")

    print()
    print("RECOVERY CONTROL MARKERS:")

    for marker in classify_function(recovery_entry):
        print(f"  MARKER: {marker}")

    print()
    print("=" * 100)
    print("DOWNSTREAM SECURITY FUNCTION DISCOVERY")
    print("=" * 100)

    all_security_functions: list[FunctionInfo] = []

    for path in (
        RECOVERY_FILE,
        *AUTHORIZATION_FILES,
        GATEWAY_FILE,
        CHECKPOINT_FILE,
    ):
        all_security_functions.extend(
            collect_functions(path)
        )

    direct_names = set(
        recovery_entry.calls
    )

    matched_functions: list[FunctionInfo] = []

    for function in all_security_functions:
        short_name = function.qualified_name.split(".")[-1]

        if (
            function.qualified_name in direct_names
            or short_name in direct_names
        ):
            matched_functions.append(function)

    for function in sorted(
        matched_functions,
        key=lambda item: (
            str(item.path),
            item.line,
            item.qualified_name,
        ),
    ):
        print()
        print(
            f"FUNCTION: {function.qualified_name}"
        )
        print(
            f"LOCATION: {function.path}:L"
            f"{function.line}"
        )
        print(
            "MARKERS: "
            + (
                ", ".join(
                    classify_function(function)
                )
                or "NONE"
            )
        )

        print("CALLS:")

        for call in function.calls:
            print(f"  CALL: {call}")

    print()
    print("=" * 100)
    print("RECOVERY / SECURITY SOURCE EVIDENCE")
    print("=" * 100)

    evidence_paths = (
        RECOVERY_FILE,
        *AUTHORIZATION_FILES,
        GATEWAY_FILE,
        CHECKPOINT_FILE,
    )

    total_evidence = 0

    for path in evidence_paths:
        path_evidence = relevant_lines(path)

        if not path_evidence:
            continue

        print()
        print(f"FILE: {path}")

        for item in path_evidence[:40]:
            print(
                f"  {item.category}: "
                f"L{item.line} | {item.text}"
            )

        total_evidence += len(path_evidence)

    print()
    print("=" * 100)
    print("R097 FLOW QUESTIONS")
    print("=" * 100)

    recovery_source = recovery_entry.source.lower()

    direct_authorization = any(
        token in recovery_source
        for token in (
            "authorize(",
            "is_authorized(",
            "authorizationguard",
            "aegisauthorizationservice",
            "capabilitygateway",
            "executionadmission",
        )
    )

    direct_admission = any(
        token in recovery_source
        for token in (
            "admit(",
            "capabilitygateway",
            "executionadmission",
        )
    )

    direct_expiry = any(
        token in recovery_source
        for token in (
            "expired",
            "expiry",
            "expires_at",
        )
    )

    direct_revocation = any(
        token in recovery_source
        for token in (
            "revoked",
            "revoke",
        )
    )

    direct_revalidation = any(
        token in recovery_source
        for token in (
            "revalidate",
            "re-validation",
            "revalidate_authorization",
        )
    )

    fail_closed = any(
        token in recovery_source
        for token in (
            "fail_closed",
            "fail-closed",
            "denied",
            "reject",
            "raise",
        )
    )

    print(
        "recover_one directly references authorization: "
        f"{'YES' if direct_authorization else 'NO'}"
    )
    print(
        "recover_one directly references admission: "
        f"{'YES' if direct_admission else 'NO'}"
    )
    print(
        "recover_one directly evaluates expiry: "
        f"{'YES' if direct_expiry else 'NO'}"
    )
    print(
        "recover_one directly evaluates revocation: "
        f"{'YES' if direct_revocation else 'NO'}"
    )
    print(
        "recover_one explicitly revalidates authority: "
        f"{'YES' if direct_revalidation else 'NO'}"
    )
    print(
        "recover_one contains fail-closed/denial behavior: "
        f"{'YES' if fail_closed else 'NO'}"
    )

    reachable_security_call = bool(
        matched_functions
        and any(
            "SECURITY_CALL" in classify_function(
                function
            )
            for function in matched_functions
        )
    )

    print()
    print(
        "Reachable security function evidence: "
        f"{'PRESENT' if reachable_security_call else 'ABSENT'}"
    )

    if (
        direct_revalidation
        and (
            direct_authorization
            or direct_admission
        )
        and (
            direct_expiry
            or direct_revocation
        )
        and fail_closed
    ):
        state = "DIRECT_R097_REVALIDATION_CONTROL_FLOW"
    elif reachable_security_call and (
        direct_authorization
        or direct_admission
    ):
        state = "INDIRECT_AUTHORITY_CONTROL_FLOW_REQUIRES_DEEP_TRACE"
    elif reachable_security_call:
        state = "RECOVERY_SECURITY_CALL_CHAIN_PRESENT"
    else:
        state = "NO_AUTHORITY_REVALIDATION_FLOW_ESTABLISHED"

    print()
    print(
        "R097 RECOVERY FLOW RESULT: "
        f"{state}"
    )

    print()
    print("=" * 100)
    print("EVIDENCE LIMIT")
    print("=" * 100)
    print(
        "This verifier statically traces the recovery "
        "entrypoint and directly referenced functions."
    )
    print(
        "It does NOT execute recovery."
    )
    print(
        "It does NOT modify source, tests, documentation, "
        "manifests, or governance."
    )
    print(
        "It does NOT grant authorization."
    )
    print(
        "It does NOT classify architecture."
    )
    print(
        f"Total relevant source evidence lines: "
        f"{total_evidence}"
    )

    print()
    print("=" * 100)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 100)
    print("READ-ONLY: YES")
    print("SOURCE CODE MUTATION: NONE")
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
        "RESULT: PASS — R097 RECOVERY AUTHORITY "
        "FLOW TRACE COMPLETED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

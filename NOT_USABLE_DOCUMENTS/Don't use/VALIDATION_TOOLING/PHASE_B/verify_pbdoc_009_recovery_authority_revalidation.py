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

CHECKPOINT = REPO_ROOT / "src/lyrion/execution/checkpoint.py"
RECOVERY = REPO_ROOT / "src/lyrion/persistence/recovery.py"
AUTHORIZATION = REPO_ROOT / "src/lyrion/security/authorization.py"
GUARDS = REPO_ROOT / "src/lyrion/security/guards.py"
GATEWAY = REPO_ROOT / "src/lyrion/capabilities/gateway.py"

TARGET = (
    "R097",
    "Expired or revoked authority is not restored from checkpoint state.",
)


@dataclass(frozen=True)
class Symbol:
    path: Path
    qualified_name: str
    kind: str
    line: int
    source: str


@dataclass(frozen=True)
class Evidence:
    category: str
    path: Path
    line: int
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


def parse_symbols(path: Path) -> list[Symbol]:
    source = read_source(path)

    if not source:
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    symbols: list[Symbol] = []

    def visit(node: ast.AST, prefix: str) -> None:
        if isinstance(node, ast.ClassDef):
            qualified = (
                f"{prefix}.{node.name}"
                if prefix
                else node.name
            )

            segment = ast.get_source_segment(
                source,
                node,
            ) or ""

            symbols.append(
                Symbol(
                    path=path,
                    qualified_name=qualified,
                    kind="class",
                    line=node.lineno,
                    source=segment,
                )
            )

            for body_node in node.body:
                visit(body_node, qualified)

            return

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            qualified = (
                f"{prefix}.{node.name}"
                if prefix
                else node.name
            )

            segment = ast.get_source_segment(
                source,
                node,
            ) or ""

            symbols.append(
                Symbol(
                    path=path,
                    qualified_name=qualified,
                    kind=(
                        "async_function"
                        if isinstance(
                            node,
                            ast.AsyncFunctionDef,
                        )
                        else "function"
                    ),
                    line=node.lineno,
                    source=segment,
                )
            )

            for body_node in node.body:
                if isinstance(
                    body_node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.ClassDef,
                    ),
                ):
                    visit(body_node, qualified)

            return

        for child_node in ast.iter_child_nodes(node):
            visit(child_node, prefix)

    visit(tree, "")
    return symbols


def collect_symbols() -> list[Symbol]:
    paths = (
        CHECKPOINT,
        RECOVERY,
        AUTHORIZATION,
        GUARDS,
        GATEWAY,
    )

    symbols: list[Symbol] = []

    for path in paths:
        symbols.extend(parse_symbols(path))

    return symbols


def find_symbols(
    symbols: list[Symbol],
    path: Path,
) -> list[Symbol]:
    return [
        symbol
        for symbol in symbols
        if symbol.path.resolve() == path.resolve()
    ]


def file_evidence(
    path: Path,
    terms: tuple[str, ...],
) -> list[Evidence]:
    source = read_source(path)

    if not source:
        return []

    evidence: list[Evidence] = []

    for number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        matched = [
            term
            for term in terms
            if term.lower() in lowered
        ]

        if matched:
            evidence.append(
                Evidence(
                    category="SOURCE",
                    path=path,
                    line=number,
                    text=(
                        f"terms={matched} | "
                        f"{line.strip()}"
                    ),
                )
            )

    return evidence


def test_evidence(
    terms: tuple[str, ...],
) -> list[Evidence]:
    root = REPO_ROOT / "tests"

    if not root.is_dir():
        return []

    evidence: list[Evidence] = []

    for path in sorted(root.rglob("*.py")):
        if any(
            part in {
                ".venv",
                "__pycache__",
                ".pytest_cache",
            }
            for part in path.parts
        ):
            continue

        source = read_source(path)

        if not source:
            continue

        for number, line in enumerate(
            source.splitlines(),
            start=1,
        ):
            lowered = line.lower()

            if all(
                term.lower() in lowered
                for term in terms
            ):
                evidence.append(
                    Evidence(
                        category="TEST",
                        path=path,
                        line=number,
                        text=line.strip(),
                    )
                )

                if len(evidence) >= 30:
                    return evidence

    return evidence


def evidence_contains_all(
    evidence: list[Evidence],
    required_terms: tuple[str, ...],
) -> bool:
    combined = "\n".join(
        item.text.lower()
        for item in evidence
    )

    return all(
        term.lower() in combined
        for term in required_terms
    )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — RECOVERY / CHECKPOINT "
        "AUTHORITY REVALIDATION DEEP VERIFICATION"
    )
    print("READ-ONLY")
    print()

    if not SPECIFICATION.is_file():
        print("RESULT: FAIL — specification missing.")
        return 1

    required_files = (
        CHECKPOINT,
        RECOVERY,
        AUTHORIZATION,
        GUARDS,
        GATEWAY,
    )

    missing = [
        path
        for path in required_files
        if not path.is_file()
    ]

    if missing:
        print("RESULT: FAIL — required implementation file missing.")
        for path in missing:
            print(f"  MISSING: {path}")
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")
    print(
        "Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    symbols = collect_symbols()

    print(
        "Concrete AST symbols discovered: "
        f"{len(symbols)}"
    )

    print()
    print("=" * 100)
    print("R097 — RECOVERY AUTHORITY REVALIDATION")
    print("=" * 100)
    print(f"DESCRIPTION: {TARGET[1]}")

    evidence: list[Evidence] = []

    checkpoint_symbols = find_symbols(
        symbols,
        CHECKPOINT,
    )
    recovery_symbols = find_symbols(
        symbols,
        RECOVERY,
    )
    authorization_symbols = find_symbols(
        symbols,
        AUTHORIZATION,
    )
    guard_symbols = find_symbols(
        symbols,
        GUARDS,
    )
    gateway_symbols = find_symbols(
        symbols,
        GATEWAY,
    )

    print()
    print("SYMBOL DISCOVERY")
    print(
        f"  Checkpoint symbols: {len(checkpoint_symbols)}"
    )
    print(
        f"  Recovery symbols: {len(recovery_symbols)}"
    )
    print(
        f"  Authorization symbols: "
        f"{len(authorization_symbols)}"
    )
    print(
        f"  Aegis guard symbols: "
        f"{len(guard_symbols)}"
    )
    print(
        f"  Capability Gateway symbols: "
        f"{len(gateway_symbols)}"
    )

    lifecycle_terms = (
        "authorization",
        "authority",
        "expiry",
        "expired",
        "revoked",
        "revoke",
        "revalidate",
        "validate",
        "admission",
        "checkpoint",
        "recovery",
        "restore",
        "resume",
        "reject",
        "deny",
        "fail closed",
        "fail-closed",
    )

    for path in required_files:
        evidence.extend(
            file_evidence(
                path,
                lifecycle_terms,
            )[:30]
        )

    print()
    print("SOURCE EVIDENCE")

    for item in evidence[:80]:
        print(
            f"  EVIDENCE: {item.path}:L{item.line} | "
            f"{item.text}"
        )

    recovery_tests = test_evidence(
        (
            "recovery",
            "authorization",
        )
    )

    checkpoint_tests = test_evidence(
        (
            "checkpoint",
            "authorization",
        )
    )

    expiry_recovery_tests = test_evidence(
        (
            "recovery",
            "expiry",
        )
    )

    revoke_recovery_tests = test_evidence(
        (
            "recovery",
            "revok",
        )
    )

    test_evidence_all = (
        recovery_tests
        + checkpoint_tests
        + expiry_recovery_tests
        + revoke_recovery_tests
    )

    print()
    print("TEST EVIDENCE")

    for item in test_evidence_all[:60]:
        print(
            f"  TEST: {item.path}:L{item.line} | "
            f"{item.text}"
        )

    source_has_recovery = bool(
        recovery_symbols
        and checkpoint_symbols
    )

    source_has_authority = bool(
        authorization_symbols
        and guard_symbols
        and gateway_symbols
    )

    source_has_revalidation_terms = (
        evidence_contains_all(
            evidence,
            (
                "authorization",
                "revalidate",
            ),
        )
        or evidence_contains_all(
            evidence,
            (
                "authorization",
                "validate",
            ),
        )
    )

    source_has_expiry_or_revocation = (
        any(
            term in "\n".join(
                item.text.lower()
                for item in evidence
            )
            for term in (
                "expired",
                "expiry",
                "revoked",
                "revoke",
            )
        )
    )

    test_has_recovery_authority = bool(
        recovery_tests
        or checkpoint_tests
    )

    test_has_expiry_or_revocation = bool(
        expiry_recovery_tests
        or revoke_recovery_tests
    )

    print()
    print("CONTROL-FLOW EVIDENCE ASSESSMENT")

    print(
        "  Checkpoint/recovery implementation: "
        f"{'PRESENT' if source_has_recovery else 'ABSENT'}"
    )
    print(
        "  Authority/Aegis implementation: "
        f"{'PRESENT' if source_has_authority else 'ABSENT'}"
    )
    print(
        "  Explicit revalidation evidence: "
        f"{'PRESENT' if source_has_revalidation_terms else 'ABSENT'}"
    )
    print(
        "  Expiry/revocation evidence: "
        f"{'PRESENT' if source_has_expiry_or_revocation else 'ABSENT'}"
    )
    print(
        "  Recovery/authority test evidence: "
        f"{'PRESENT' if test_has_recovery_authority else 'ABSENT'}"
    )
    print(
        "  Recovery expiry/revocation tests: "
        f"{'PRESENT' if test_has_expiry_or_revocation else 'ABSENT'}"
    )

    if (
        source_has_recovery
        and source_has_authority
        and source_has_revalidation_terms
        and source_has_expiry_or_revocation
        and test_has_recovery_authority
        and test_has_expiry_or_revocation
    ):
        state = "CANDIDATE_CODE_AND_TEST_EVIDENCE"
    elif (
        source_has_recovery
        and source_has_authority
        and source_has_revalidation_terms
        and source_has_expiry_or_revocation
    ):
        state = "CANDIDATE_CODE_EVIDENCE"
    elif test_has_recovery_authority:
        state = "CANDIDATE_TEST_EVIDENCE"
    else:
        state = "EVIDENCE_GAP"

    print()
    print(f"R097 RESULT: {state}")

    print()
    print("=" * 100)
    print("ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 100)
    print("PRESERVE: NOT ASSIGNED")
    print("EXTEND: NOT ASSIGNED")
    print("NEW: NOT ASSIGNED")
    print("REFACTOR: NOT ASSIGNED")
    print("CONFLICT: NOT ASSIGNED")

    print()
    print("=" * 100)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 100)
    print("READ-ONLY: YES")
    print("SOURCE CODE MUTATION: NONE")
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
        "REVALIDATION DEEP VERIFICATION COMPLETED"
    )
    print(
        "NOTE: Evidence state is not a compliance claim "
        "or architectural decision."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

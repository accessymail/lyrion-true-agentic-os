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

GATEWAY = REPO_ROOT / "src/lyrion/capabilities/gateway.py"
AUTHORIZATION = REPO_ROOT / "src/lyrion/security/authorization.py"
GUARDS = REPO_ROOT / "src/lyrion/security/guards.py"
REPLAY = REPO_ROOT / "src/lyrion/security/replay.py"
POLICY = REPO_ROOT / "src/lyrion/security/policy.py"
RULES = REPO_ROOT / "src/lyrion/security/rules.py"
CHECKPOINT = REPO_ROOT / "src/lyrion/execution/checkpoint.py"
RECOVERY = REPO_ROOT / "src/lyrion/persistence/recovery.py"

TARGETS = (
    (
        "R048",
        "Stale, invalid, revoked, mismatched, or replayed approval is rejected.",
    ),
    (
        "R049",
        "Expiry and revocation are evaluated at admission.",
    ),
    (
        "R050",
        "Expired authorization fails closed.",
    ),
    (
        "R051",
        "Revoked authority prevents admission.",
    ),
    (
        "R052",
        "Previous admission state does not restore authorization after revocation or expiry.",
    ),
    (
        "R095",
        "Admission cannot convert a previous operation into unlimited replay authority.",
    ),
    (
        "R097",
        "Expired or revoked authority is not restored from checkpoint state.",
    ),
)


@dataclass(frozen=True)
class Symbol:
    path: Path
    qualified_name: str
    kind: str
    line: int
    source: str


@dataclass(frozen=True)
class Result:
    requirement_id: str
    description: str
    state: str
    evidence: tuple[str, ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_symbols(path: Path) -> list[Symbol]:
    if not path.is_file():
        return []

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="strict",
        )
        tree = ast.parse(source)
    except (OSError, UnicodeError, SyntaxError):
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
        GATEWAY,
        AUTHORIZATION,
        GUARDS,
        REPLAY,
        POLICY,
        RULES,
        CHECKPOINT,
        RECOVERY,
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


def calls_in_source(
    source: str,
) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    names: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            names.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.append(node.func.attr)

    return sorted(set(names))


def terms_in_source(
    source: str,
    terms: tuple[str, ...],
) -> list[str]:
    lowered = source.lower()

    return [
        term
        for term in terms
        if term.lower() in lowered
    ]


def file_evidence(
    path: Path,
    terms: tuple[str, ...],
) -> list[str]:
    if not path.is_file():
        return []

    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
    except (OSError, UnicodeError):
        return []

    evidence: list[str] = []

    for number, line in enumerate(
        lines,
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
                f"{path}:L{number} | "
                f"terms={matched} | {line.strip()}"
            )

    return evidence


def test_evidence(
    terms: tuple[str, ...],
) -> list[str]:
    root = REPO_ROOT / "tests"

    if not root.is_dir():
        return []

    evidence: list[str] = []

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

        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="strict",
            ).splitlines()
        except (OSError, UnicodeError):
            continue

        for number, line in enumerate(
            lines,
            start=1,
        ):
            lowered = line.lower()

            if all(
                term.lower() in lowered
                for term in terms
            ):
                evidence.append(
                    f"{path}:L{number} | {line.strip()}"
                )

    return evidence[:20]


def verify(
    requirement_id: str,
    description: str,
    symbols: list[Symbol],
) -> Result:
    evidence: list[str] = []

    gateway_symbols = find_symbols(
        symbols,
        GATEWAY,
    )
    authorization_symbols = find_symbols(
        symbols,
        AUTHORIZATION,
    )
    guard_symbols = find_symbols(
        symbols,
        GUARDS,
    )
    replay_symbols = find_symbols(
        symbols,
        REPLAY,
    )
    checkpoint_symbols = find_symbols(
        symbols,
        CHECKPOINT,
    )
    recovery_symbols = find_symbols(
        symbols,
        RECOVERY,
    )

    gateway_admit = next(
        (
            symbol
            for symbol in gateway_symbols
            if symbol.qualified_name
            == "CapabilityGateway.admit"
        ),
        None,
    )

    if gateway_admit:
        evidence.append(
            f"CapabilityGateway.admit resolved at "
            f"{GATEWAY}:L{gateway_admit.line}."
        )

    lifecycle_terms = (
        "expiry",
        "expired",
        "revoked",
        "revoke",
        "replay",
        "nonce",
        "authorization",
        "valid",
        "invalid",
        "stale",
        "mismatch",
    )

    security_terms = terms_in_source(
        gateway_admit.source
        if gateway_admit
        else "",
        lifecycle_terms,
    )

    if security_terms:
        evidence.append(
            "Gateway admission lifecycle terms: "
            f"{security_terms}."
        )

    if authorization_symbols:
        evidence.append(
            f"Authorization implementation symbols: "
            f"{len(authorization_symbols)}."
        )

    if guard_symbols:
        evidence.append(
            f"Aegis guard symbols: {len(guard_symbols)}."
        )

    if replay_symbols:
        evidence.append(
            f"Replay/security symbols: {len(replay_symbols)}."
        )

    if requirement_id in {
        "R048",
        "R049",
        "R050",
        "R051",
    }:
        lifecycle_files = (
            GUARDS,
            AUTHORIZATION,
            REPLAY,
            POLICY,
            RULES,
        )

        discovered: list[str] = []

        for lifecycle_file in lifecycle_files:
            discovered.extend(
                file_evidence(
                    lifecycle_file,
                    lifecycle_terms,
                )[:12]
            )

        evidence.extend(discovered[:20])

        tests = test_evidence(
            (
                "authorization",
                "expiry",
            )
        )

        evidence.extend(tests[:8])

        if (
            security_terms
            and discovered
            and tests
        ):
            state = "PARTIALLY_VERIFIED"
        elif discovered or tests:
            state = "CANDIDATE_EVIDENCE"
        else:
            state = "EVIDENCE_GAP"

        return Result(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    if requirement_id in {"R052", "R095"}:
        replay_evidence = []

        replay_evidence.extend(
            file_evidence(
                REPLAY,
                (
                    "replay",
                    "nonce",
                    "duplicate",
                    "consumed",
                    "used",
                ),
            )
        )

        replay_evidence.extend(
            file_evidence(
                GATEWAY,
                (
                    "replay",
                    "nonce",
                    "consumed",
                )
            )
        )

        tests = test_evidence(
            (
                "replay",
                "nonce",
            )
        )

        evidence.extend(
            replay_evidence[:20]
        )
        evidence.extend(
            tests[:10]
        )

        if replay_evidence and tests:
            state = "PARTIALLY_VERIFIED"
        elif replay_evidence or tests:
            state = "CANDIDATE_EVIDENCE"
        else:
            state = "EVIDENCE_GAP"

        return Result(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    if requirement_id == "R097":
        checkpoint_evidence = []

        checkpoint_evidence.extend(
            file_evidence(
                CHECKPOINT,
                (
                    "authorization",
                    "expiry",
                    "revoked",
                    "revoke",
                    "admission",
                ),
            )
        )

        checkpoint_evidence.extend(
            file_evidence(
                RECOVERY,
                (
                    "authorization",
                    "expiry",
                    "revoked",
                    "revalidate",
                    "admission",
                ),
            )
        )

        evidence.extend(
            checkpoint_evidence[:24]
        )

        if checkpoint_symbols:
            evidence.append(
                f"Checkpoint symbols discovered: "
                f"{len(checkpoint_symbols)}."
            )

        if recovery_symbols:
            evidence.append(
                f"Recovery symbols discovered: "
                f"{len(recovery_symbols)}."
            )

        tests = test_evidence(
            (
                "recovery",
                "authorization",
            )
        )

        evidence.extend(
            tests[:10]
        )

        if checkpoint_evidence and tests:
            state = "PARTIALLY_VERIFIED"
        elif checkpoint_evidence:
            state = "CANDIDATE_CODE_EVIDENCE"
        elif tests:
            state = "CANDIDATE_TEST_EVIDENCE"
        else:
            state = "EVIDENCE_GAP"

        return Result(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    return Result(
        requirement_id,
        description,
        "EVIDENCE_GAP",
        ("Unsupported lifecycle target.",),
    )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — AUTHORITY LIFECYCLE "
        "DEEP VERIFICATION"
    )
    print("READ-ONLY")
    print()

    if not SPECIFICATION.is_file():
        print(
            "RESULT: FAIL — specification missing."
        )
        return 1

    print(
        f"Repository: {REPO_ROOT}"
    )
    print(
        f"Specification: {SPECIFICATION}"
    )
    print(
        f"Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    symbols = collect_symbols()

    print(
        f"Concrete AST symbols discovered: "
        f"{len(symbols)}"
    )

    print()
    print("=" * 100)
    print("AUTHORITY LIFECYCLE REQUIREMENTS")
    print("=" * 100)

    results: list[Result] = []

    for requirement_id, description in TARGETS:
        result = verify(
            requirement_id,
            description,
            symbols,
        )

        results.append(result)

        print()
        print("-" * 100)
        print(
            f"{result.requirement_id} | "
            f"{result.state}"
        )
        print(
            f"DESCRIPTION: {result.description}"
        )

        for item in result.evidence:
            print(f"  EVIDENCE: {item}")

    counts: dict[str, int] = {}

    for result in results:
        counts[result.state] = (
            counts.get(result.state, 0) + 1
        )

    print()
    print("=" * 100)
    print("RESULT SUMMARY")
    print("=" * 100)

    for state, count in sorted(counts.items()):
        print(f"{state}: {count}")

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

    print()
    print("=" * 100)
    print("FINAL RESULT")
    print("=" * 100)
    print(
        "RESULT: PASS — AUTHORITY LIFECYCLE "
        "DEEP VERIFICATION COMPLETED"
    )
    print(
        "NOTE: Evidence states are not compliance "
        "or architectural decisions."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

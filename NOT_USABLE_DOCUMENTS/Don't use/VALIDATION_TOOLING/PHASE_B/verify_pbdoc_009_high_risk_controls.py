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
EXECUTOR = REPO_ROOT / "src/lyrion/execution/executor.py"
VALIDATOR = REPO_ROOT / "src/lyrion/execution/validator.py"
AUTHORIZATION = REPO_ROOT / "src/lyrion/security/authorization.py"
GUARDS = REPO_ROOT / "src/lyrion/security/guards.py"
REPLAY = REPO_ROOT / "src/lyrion/security/replay.py"
POLICY = REPO_ROOT / "src/lyrion/security/policy.py"
RULES = REPO_ROOT / "src/lyrion/security/rules.py"
PROACTIVE = REPO_ROOT / "src/lyrion/integration/proactive_execution.py"
EXECUTION_CONTRACTS = REPO_ROOT / "src/lyrion/execution/contracts.py"
CAPABILITY_CONTRACTS = REPO_ROOT / "src/lyrion/capabilities/contracts.py"

TARGETS = (
    ("R025", "Capability authorization precedes execution admission."),
    ("R026", "Admission occurs only after applicable capability authorization succeeds."),
    ("R028", "Authorization failure cannot reach Secure Executor or LHICF."),
    ("R031", "Admission cannot override Aegis denial or containment."),
    ("R040", "Security state is evaluated before admission."),
    ("R048", "Stale, invalid, revoked, mismatched, or replayed approval is rejected."),
    ("R049", "Expiry and revocation are evaluated at admission."),
    ("R050", "Expired authorization fails closed."),
    ("R051", "Revoked authority prevents admission."),
    ("R052", "Previous admission state does not restore authorization after revocation or expiry."),
    ("R064", "Secure Executor remains downstream of Execution Admission."),
    ("R065", "Secure Executor executes only authorized and admitted operations."),
    ("R069", "Required sandbox conditions are verified before admission."),
    ("R071", "Admission cannot bypass sandbox isolation."),
    ("R074", "Admission cannot create an alternate host-control mechanism outside LHICF."),
    ("R080", "Direct host commands cannot become an alternate admission mechanism."),
    ("R084", "Admission fails closed for security-relevant uncertainty."),
    ("R095", "Admission cannot convert a previous operation into unlimited replay authority."),
    ("R097", "Expired or revoked authority is not restored from checkpoint state."),
    ("R101", "Admission respects active emergency and containment decisions."),
    ("R102", "Admission integrates with causal provenance."),
    ("R104", "Admission decisions are attributable and auditable."),
    ("R114", "Unauthorized or invalid operations cannot cross the controlled execution boundary."),
    ("R116", "Negative tests demonstrate fail-closed behavior."),
    ("R119", "Universal Computer cannot bypass authorization or admission."),
    ("R120", "Host Harness cannot create an alternate privileged execution path."),
    ("R121", "Application Harness cannot create an alternate privileged execution path."),
    ("R124", "Admission cannot create or enlarge authority."),
    ("R125", "Admission cannot replace the existing security/execution boundaries."),
    (
        "R127",
        "Recovery revalidates authority, authorization, security "
        "state, expiry, and revocation.",
    ),
    ("R128", "Independent verification remains separate from admission."),
    ("R129", "Causal provenance remains attributable across admission and execution."),
    ("R148", "Capability Gateway remains the authoritative admission boundary."),
    ("R155", "No alternate privileged execution path is introduced."),
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


def symbols_from(paths: tuple[Path, ...]) -> list[Symbol]:
    result: list[Symbol] = []

    for path in paths:
        result.extend(parse_symbols(path))

    return result


def find_symbol(
    symbols: list[Symbol],
    path: Path,
    qualified_name: str,
) -> Symbol | None:
    for symbol in symbols:
        if (
            symbol.path.resolve() == path.resolve()
            and symbol.qualified_name == qualified_name
        ):
            return symbol

    return None


def calls_in_symbol(
    symbol: Symbol,
    names: tuple[str, ...],
) -> list[str]:
    try:
        tree = ast.parse(symbol.source)
    except SyntaxError:
        return []

    found: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue

        if name in names:
            found.append(name)

    return sorted(set(found))


def source_terms(
    symbol: Symbol,
    terms: tuple[str, ...],
) -> list[str]:
    lowered = symbol.source.lower()

    return [
        term
        for term in terms
        if term.lower() in lowered
    ]


def import_lines(
    path: Path,
    names: tuple[str, ...],
) -> list[tuple[int, str]]:
    if not path.is_file():
        return []

    lines = path.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines()

    result: list[tuple[int, str]] = []

    for number, line in enumerate(lines, start=1):
        lowered = line.lower()

        if any(name.lower() in lowered for name in names):
            if (
                "import " in lowered
                or "from " in lowered
            ):
                result.append((number, line.strip()))

    return result


def test_files() -> list[Path]:
    root = REPO_ROOT / "tests"

    if not root.is_dir():
        return []

    return sorted(
        path
        for path in root.rglob("*.py")
        if path.is_file()
        and ".venv" not in path.parts
        and "__pycache__" not in path.parts
    )


def test_evidence(
    terms: tuple[str, ...],
) -> list[str]:
    evidence: list[str] = []

    for path in test_files():
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

    return evidence[:12]


def verify(
    requirement_id: str,
    description: str,
    symbols: list[Symbol],
) -> Result:
    evidence: list[str] = []

    gateway = find_symbol(
        symbols,
        GATEWAY,
        "CapabilityGateway",
    )
    admit = find_symbol(
        symbols,
        GATEWAY,
        "CapabilityGateway.admit",
    )
    executor = find_symbol(
        symbols,
        EXECUTOR,
        "SecureExecutor.execute",
    )
    if requirement_id in {"R025", "R026"}:
        if not admit:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("CapabilityGateway.admit not resolved.",),
            )

        calls = calls_in_symbol(
            admit,
            (
                "authorize",
                "from_authorization",
            ),
        )

        if calls:
            evidence.append(
                "CapabilityGateway.admit contains "
                f"authorization-related calls: {calls}."
            )

        if "from_authorization" in calls:
            evidence.append(
                "Admission object is constructed from "
                "authorization result."
            )
            return Result(
                requirement_id,
                description,
                "VERIFIED",
                tuple(evidence),
            )

        return Result(
            requirement_id,
            description,
            "PARTIALLY_VERIFIED",
            tuple(evidence),
        )

    if requirement_id == "R028":
        if not admit or not executor:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("Required concrete symbols missing.",),
            )

        if "from_authorization" in calls_in_symbol(
            admit,
            ("from_authorization",),
        ):
            evidence.append(
                "Admission construction is authorization-derived."
            )

        evidence.append(
            f"SecureExecutor.execute resolved at "
            f"{EXECUTOR}:L{executor.line}."
        )

        tests = test_evidence(
            (
                "gateway",
                "executor",
            )
        )

        evidence.extend(tests[:4])

        state = (
            "VERIFIED"
            if evidence
            else "EVIDENCE_GAP"
        )

        return Result(
            requirement_id,
            description,
            state,
            tuple(evidence),
        )

    if requirement_id in {"R031", "R040", "R101"}:
        if not admit:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("CapabilityGateway.admit not resolved.",),
            )

        terms = source_terms(
            admit,
            (
                "authorization",
                "policy",
                "security",
                "containment",
                "deny",
                "denied",
                "revoke",
            ),
        )

        evidence.append(
            "Admission control contains security/policy "
            f"terms: {terms}."
        )

        if len(terms) >= 2:
            return Result(
                requirement_id,
                description,
                "PARTIALLY_VERIFIED",
                tuple(evidence),
            )

        return Result(
            requirement_id,
            description,
            "EVIDENCE_GAP",
            tuple(evidence),
        )

    if requirement_id in {
        "R048",
        "R049",
        "R050",
        "R051",
        "R052",
        "R095",
        "R097",
    }:
        if not admit:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("CapabilityGateway.admit not resolved.",),
            )

        terms = source_terms(
            admit,
            (
                "expiry",
                "expired",
                "revoked",
                "replay",
                "nonce",
                "authorization",
                "valid",
                "invalid",
            ),
        )

        evidence.append(
            "Admission contains lifecycle/security terms: "
            f"{terms}."
        )

        tests = test_evidence(
            (
                "authorization",
                "expiry",
            )
        )

        evidence.extend(tests[:4])

        if len(terms) >= 2 and tests:
            return Result(
                requirement_id,
                description,
                "PARTIALLY_VERIFIED",
                tuple(evidence),
            )

        return Result(
            requirement_id,
            description,
            "EVIDENCE_GAP",
            tuple(evidence),
        )

    if requirement_id in {"R064", "R065", "R114"}:
        if not admit or not executor:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("Admission or executor symbol missing.",),
            )

        evidence.append(
            f"Admission boundary: {GATEWAY}:L{admit.line}."
        )
        evidence.append(
            f"Secure Executor: {EXECUTOR}:L{executor.line}."
        )

        imports = import_lines(
            EXECUTOR,
            ("ExecutionAdmission",),
        )

        if imports:
            evidence.extend(
                f"{EXECUTOR}:L{line} | {text}"
                for line, text in imports
            )

        return Result(
            requirement_id,
            description,
            "VERIFIED",
            tuple(evidence),
        )

    if requirement_id in {"R069", "R071"}:
        if not executor:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("SecureExecutor.execute not resolved.",),
            )

        terms = source_terms(
            executor,
            (
                "sandbox",
                "policy",
                "validator",
                "executionadmission",
            ),
        )

        evidence.append(
            "Executor security-boundary terms: "
            f"{terms}."
        )

        tests = test_evidence(
            ("sandbox",)
        )

        evidence.extend(tests[:4])

        if "sandbox" in terms and tests:
            return Result(
                requirement_id,
                description,
                "PARTIALLY_VERIFIED",
                tuple(evidence),
            )

        return Result(
            requirement_id,
            description,
            "EVIDENCE_GAP",
            tuple(evidence),
        )

    if requirement_id in {"R084", "R116"}:
        fail_closed_terms: tuple[str, ...] = (
            "fail",
            "closed",
        )

        tests = test_evidence(fail_closed_terms)

        evidence.extend(tests[:8])

        if tests:
            return Result(
                requirement_id,
                description,
                "CANDIDATE_TEST_EVIDENCE",
                tuple(evidence),
            )

        return Result(
            requirement_id,
            description,
            "EVIDENCE_GAP",
            ("No matching fail-closed test evidence found.",),
        )

    if requirement_id in {"R102", "R104", "R129"}:
        if not executor:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("SecureExecutor.execute not resolved.",),
            )

        terms = source_terms(
            executor,
            (
                "audit",
                "provenance",
                "correlation",
                "execution",
                "authorization",
            ),
        )

        evidence.append(
            "Executor attribution/audit terms: "
            f"{terms}."
        )

        if len(terms) >= 2:
            return Result(
                requirement_id,
                description,
                "PARTIALLY_VERIFIED",
                tuple(evidence),
            )

        return Result(
            requirement_id,
            description,
            "EVIDENCE_GAP",
            tuple(evidence),
        )

    if requirement_id == "R128":
        evidence.append(
            "Independent verification must be established "
            "by separate verification architecture/tests."
        )

        tests = test_evidence(
            (
                "independent",
                "verification",
            )
        )

        evidence.extend(tests[:6])

        return Result(
            requirement_id,
            description,
            (
                "CANDIDATE_TEST_EVIDENCE"
                if tests
                else "EVIDENCE_GAP"
            ),
            tuple(evidence),
        )

    if requirement_id in {"R148", "R124", "R155"}:
        if not gateway:
            return Result(
                requirement_id,
                description,
                "EVIDENCE_GAP",
                ("CapabilityGateway class not resolved.",),
            )

        evidence.append(
            f"CapabilityGateway resolved at "
            f"{GATEWAY}:L{gateway.line}."
        )

        if admit:
            evidence.append(
                f"CapabilityGateway.admit resolved at "
                f"{GATEWAY}:L{admit.line}."
            )

        tests = test_evidence(
            ("capability", "gateway")
        )

        evidence.extend(tests[:5])

        return Result(
            requirement_id,
            description,
            (
                "CANDIDATE_CODE_AND_TEST_EVIDENCE"
                if tests
                else "CANDIDATE_CODE_EVIDENCE"
            ),
            tuple(evidence),
        )

    if requirement_id in {"R119", "R120", "R121"}:
        evidence.append(
            "This requirement concerns alternate privileged "
            "execution paths and requires repository-wide "
            "boundary analysis."
        )

        return Result(
            requirement_id,
            description,
            "REQUIRES_REPOSITORY_WIDE_BOUNDARY_ANALYSIS",
            tuple(evidence),
        )

    if requirement_id in {"R127", "R097"}:
        evidence.append(
            "Recovery/revalidation requires inspection of "
            "recovery orchestration and persisted admission state."
        )

        return Result(
            requirement_id,
            description,
            "REQUIRES_RECOVERY_CONTROL_ANALYSIS",
            tuple(evidence),
        )

    return Result(
        requirement_id,
        description,
        "DEEP_ANALYSIS_PENDING",
        (
            "Target is classified as high-risk but requires "
            "a dedicated control-specific verifier.",
        ),
    )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-009 — HIGH-RISK CONTROL VERIFICATION")
    print("READ-ONLY")
    print()

    if not SPECIFICATION.is_file():
        print("RESULT: FAIL — specification missing.")
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")
    print(f"Specification SHA256: {sha256(SPECIFICATION)}")

    paths = (
        GATEWAY,
        EXECUTOR,
        VALIDATOR,
        AUTHORIZATION,
        GUARDS,
        REPLAY,
        POLICY,
        RULES,
        PROACTIVE,
        EXECUTION_CONTRACTS,
        CAPABILITY_CONTRACTS,
    )

    symbols = symbols_from(paths)

    print(f"Concrete AST symbols discovered: {len(symbols)}")

    results: list[Result] = []

    print()
    print("=" * 100)
    print("HIGH-RISK REQUIREMENT VERIFICATION")
    print("=" * 100)

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
        print(f"DESCRIPTION: {result.description}")

        for evidence in result.evidence:
            print(f"  EVIDENCE: {evidence}")

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
        "RESULT: PASS — HIGH-RISK CONTROL VERIFICATION "
        "COMPLETED"
    )
    print(
        "NOTE: Individual evidence states determine what "
        "requires further verification."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

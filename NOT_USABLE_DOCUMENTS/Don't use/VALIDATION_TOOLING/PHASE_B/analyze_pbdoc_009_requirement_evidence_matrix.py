from __future__ import annotations

import ast
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SPECIFICATION = (
    REPO_ROOT
    / "docs/phase-b/execution-admission/"
    / "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

SOURCE_ROOT = REPO_ROOT / "src"
TEST_ROOT = REPO_ROOT / "tests"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

NORMATIVE_PATTERN = re.compile(
    r"\b(?:SHALL|MUST|SHOULD|REQUIRED|"
    r"SHALL NOT|MUST NOT)\b",
    re.IGNORECASE,
)

HEADING_PATTERN = re.compile(
    r"^(#{1,6})\s+(.+?)\s*$"
)

TOKEN_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9_/-]{3,}"
)

STOPWORDS = {
    "shall",
    "must",
    "should",
    "required",
    "requirements",
    "the",
    "this",
    "that",
    "with",
    "from",
    "into",
    "only",
    "when",
    "where",
    "remain",
    "execution",
    "admission",
    "system",
    "operation",
    "operations",
    "component",
    "components",
    "request",
    "requests",
    "context",
    "contexts",
}


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    section: str
    line: int
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class CodeSymbol:
    path: Path
    qualified_name: str
    kind: str
    line: int
    source: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class TestEvidence:
    path: Path
    line: int
    text: str


@dataclass(frozen=True)
class EvidenceResult:
    requirement: Requirement
    code_matches: tuple[CodeSymbol, ...]
    test_matches: tuple[TestEvidence, ...]
    state: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []

    for token in TOKEN_PATTERN.findall(text.lower()):
        token = token.replace("-", "_").replace("/", "_")

        if token in STOPWORDS:
            continue

        if token not in tokens:
            tokens.append(token)

    return tuple(tokens)


def eligible(path: Path) -> bool:
    return not any(
        part in EXCLUDED_PARTS
        for part in path.parts
    )


def python_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []

    return sorted(
        path
        for path in root.rglob("*.py")
        if path.is_file() and eligible(path)
    )


def parse_symbols(path: Path) -> list[CodeSymbol]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="strict",
        )
        tree = ast.parse(source)
    except (OSError, UnicodeError, SyntaxError):
        return []

    symbols: list[CodeSymbol] = []

    def visit(
        node: ast.AST,
        prefix: str,
    ) -> None:
        if isinstance(node, ast.ClassDef):
            qualified = (
                f"{prefix}.{node.name}"
                if prefix
                else node.name
            )

            segment = (
                ast.get_source_segment(
                    source,
                    node,
                )
                or ""
            )

            symbols.append(
                CodeSymbol(
                    path=path,
                    qualified_name=qualified,
                    kind="class",
                    line=node.lineno,
                    source=segment,
                    tokens=normalize_tokens(
                        f"{qualified} {segment}"
                    ),
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

            segment = (
                ast.get_source_segment(
                    source,
                    node,
                )
                or ""
            )

            symbols.append(
                CodeSymbol(
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
                    tokens=normalize_tokens(
                        f"{qualified} {segment}"
                    ),
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


def collect_symbols() -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []

    for path in python_files(SOURCE_ROOT):
        symbols.extend(parse_symbols(path))

    return symbols


def extract_requirements() -> list[Requirement]:
    lines = SPECIFICATION.read_text(
        encoding="utf-8",
        errors="strict",
    ).splitlines()

    requirements: list[Requirement] = []
    section = "UNSPECIFIED"

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        heading = HEADING_PATTERN.match(line)

        if heading:
            section = heading.group(2).strip()

        if not NORMATIVE_PATTERN.search(line):
            continue

        text = line.strip()

        if not text:
            continue

        tokens = normalize_tokens(text)

        if not tokens:
            continue

        requirements.append(
            Requirement(
                requirement_id=(
                    f"PB-DOC-009-R{len(requirements) + 1:03d}"
                ),
                section=section,
                line=line_number,
                text=text,
                tokens=tokens,
            )
        )

    return requirements


def test_evidence_for_requirement(
    requirement: Requirement,
) -> list[TestEvidence]:
    if not TEST_ROOT.is_dir():
        return []

    evidence: list[TestEvidence] = []

    important_tokens = set(requirement.tokens)

    for path in python_files(TEST_ROOT):
        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="strict",
            ).splitlines()
        except (OSError, UnicodeError):
            continue

        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            lowered = line.lower()

            matched = sum(
                1
                for token in important_tokens
                if token in lowered
            )

            if matched >= 2:
                evidence.append(
                    TestEvidence(
                        path=path,
                        line=line_number,
                        text=line.strip(),
                    )
                )

    return evidence


def code_score(
    requirement: Requirement,
    symbol: CodeSymbol,
) -> int:
    requirement_tokens = set(requirement.tokens)
    symbol_tokens = set(symbol.tokens)

    overlap = requirement_tokens & symbol_tokens

    score = len(overlap)

    name = symbol.qualified_name.lower()
    requirement_text = requirement.text.lower()

    if name in requirement_text:
        score += 8

    # Strong signals for security/control symbols.
    for strong_token in (
        "authorize",
        "authorization",
        "capability",
        "admission",
        "validate",
        "validator",
        "policy",
        "sandbox",
        "audit",
        "provenance",
        "executor",
        "gateway",
        "identity",
        "authority",
    ):
        if strong_token in requirement_tokens:
            if strong_token in symbol_tokens:
                score += 2

    return score


def code_matches(
    requirement: Requirement,
    symbols: list[CodeSymbol],
) -> list[CodeSymbol]:
    scored: list[tuple[int, CodeSymbol]] = []

    for symbol in symbols:
        score = code_score(
            requirement,
            symbol,
        )

        if score >= 3:
            scored.append((score, symbol))

    scored.sort(
        key=lambda item: (
            -item[0],
            str(item[1].path),
            item[1].line,
        )
    )

    return [
        symbol
        for _, symbol in scored[:10]
    ]


def evidence_state(
    code: list[CodeSymbol],
    tests: list[TestEvidence],
) -> str:
    if code and tests:
        return "CANDIDATE_CODE_AND_TEST_EVIDENCE"

    if code:
        return "CANDIDATE_CODE_EVIDENCE"

    if tests:
        return "TEST_EVIDENCE_ONLY"

    return "EVIDENCE_GAP"


def analyze(
    requirement: Requirement,
    symbols: list[CodeSymbol],
) -> EvidenceResult:
    matches = code_matches(
        requirement,
        symbols,
    )

    tests = test_evidence_for_requirement(
        requirement,
    )

    return EvidenceResult(
        requirement=requirement,
        code_matches=tuple(matches),
        test_matches=tuple(tests[:10]),
        state=evidence_state(
            matches,
            tests,
        ),
    )


def print_result(
    result: EvidenceResult,
) -> None:
    requirement = result.requirement

    print()
    print("-" * 90)
    print(
        f"{requirement.requirement_id} | "
        f"{result.state} | "
        f"SPEC:L{requirement.line}"
    )
    print(f"SECTION: {requirement.section}")
    print(f"REQUIREMENT: {requirement.text}")

    if result.code_matches:
        print("CODE CANDIDATES:")

        for symbol in result.code_matches:
            print(
                f"  {symbol.kind:<16} "
                f"{symbol.qualified_name} | "
                f"{symbol.path}:L{symbol.line}"
            )
    else:
        print("CODE CANDIDATES: NONE")

    if result.test_matches:
        print("TEST CANDIDATES:")

        for evidence in result.test_matches:
            print(
                f"  {evidence.path}:L{evidence.line} | "
                f"{evidence.text}"
            )
    else:
        print("TEST CANDIDATES: NONE")


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — REQUIREMENT-LEVEL "
        "EVIDENCE MATRIX"
    )
    print("READ-ONLY")
    print()

    print(f"Repository: {REPO_ROOT}")
    print(f"Specification: {SPECIFICATION}")

    if not SPECIFICATION.is_file():
        print(
            "RESULT: FAIL — authoritative "
            "PB-DOC-009 specification missing."
        )
        return 1

    specification = SPECIFICATION.read_text(
        encoding="utf-8",
        errors="strict",
    ).lower()

    if "pb-doc-009" not in specification:
        print(
            "RESULT: FAIL — specification identity "
            "does not contain PB-DOC-009."
        )
        return 1

    if "execution admission" not in specification:
        print(
            "RESULT: FAIL — Execution Admission "
            "identity missing."
        )
        return 1

    print(
        f"Specification SHA256: "
        f"{sha256(SPECIFICATION)}"
    )

    requirements = extract_requirements()

    if not requirements:
        print(
            "RESULT: FAIL — no normative requirements "
            "discovered."
        )
        return 1

    symbols = collect_symbols()

    print(
        f"Normative requirements discovered: "
        f"{len(requirements)}"
    )
    print(
        f"Source symbols discovered: "
        f"{len(symbols)}"
    )

    print()
    print("=" * 90)
    print("REQUIREMENT → CODE → TEST EVIDENCE")
    print("=" * 90)

    results = [
        analyze(
            requirement,
            symbols,
        )
        for requirement in requirements
    ]

    for result in results:
        print_result(result)

    states: dict[str, int] = {}

    for result in results:
        states[result.state] = (
            states.get(result.state, 0) + 1
        )

    print()
    print("=" * 90)
    print("EVIDENCE STATE SUMMARY")
    print("=" * 90)

    for state, count in sorted(states.items()):
        print(f"{state}: {count}")

    print()
    print("=" * 90)
    print("IMPORTANT EVIDENCE LIMITATION")
    print("=" * 90)

    print(
        "This analyzer discovers candidate evidence."
    )
    print(
        "It does NOT establish compliance merely from "
        "keyword overlap."
    )
    print(
        "It does NOT prove control-flow correctness."
    )
    print(
        "It does NOT assign PRESERVE / EXTEND / NEW / "
        "REFACTOR / CONFLICT."
    )

    print()
    print("=" * 90)
    print("ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 90)

    print("PRESERVE: NOT ASSIGNED")
    print("EXTEND: NOT ASSIGNED")
    print("NEW: NOT ASSIGNED")
    print("REFACTOR: NOT ASSIGNED")
    print("CONFLICT: NOT ASSIGNED")

    print()
    print("=" * 90)
    print("SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 90)

    print("READ-ONLY: YES")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")

    print()
    print("=" * 90)
    print("FINAL RESULT")
    print("=" * 90)

    print(
        "RESULT: PASS — PB-DOC-009 REQUIREMENT-LEVEL "
        "EVIDENCE MATRIX GENERATED"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

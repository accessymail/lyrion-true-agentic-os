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

SOURCE_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
)

PB_DOC = "PB-DOC-009"

REQUIREMENT_PATTERN = re.compile(
    r"\b(?:SHALL|MUST|REQUIRED|SHOULD|MUST NOT|SHALL NOT)\b",
    re.IGNORECASE,
)

HEADING_PATTERN = re.compile(
    r"^(#{1,6})\s+(.+?)\s*$"
)

CODE_PATTERN = re.compile(
    r"`([^`]+)`"
)

TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_/-]{2,}")

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "shall",
    "must",
    "should",
    "from",
    "into",
    "only",
    "not",
    "remain",
    "when",
    "where",
    "their",
    "have",
    "does",
    "doesnt",
    "mustnot",
    "shallnot",
    "required",
    "requirements",
    "system",
    "execution",
    "admission",
}


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    section: str
    line_number: int
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class Symbol:
    path: Path
    name: str
    kind: str
    line_number: int
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceMatch:
    requirement: Requirement
    symbol: Symbol
    score: int


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_tokens(text: str) -> tuple[str, ...]:
    raw = TOKEN_PATTERN.findall(text.lower())

    normalized: list[str] = []

    for token in raw:
        token = token.replace("-", "_").replace("/", "_")

        if token in STOPWORDS:
            continue

        if len(token) < 4:
            continue

        if token not in normalized:
            normalized.append(token)

    return tuple(normalized)


def extract_code_tokens(text: str) -> tuple[str, ...]:
    tokens: list[str] = []

    for code in CODE_PATTERN.findall(text):
        for token in normalize_tokens(code):
            if token not in tokens:
                tokens.append(token)

    return tuple(tokens)


def validate_specification() -> None:
    if not SPECIFICATION.is_file():
        raise RuntimeError(
            f"Authoritative PB-DOC-009 specification missing: "
            f"{SPECIFICATION}"
        )

    text = SPECIFICATION.read_text(
        encoding="utf-8"
    ).lower()

    if "pb-doc-009" not in text:
        raise RuntimeError(
            "Resolved specification does not identify PB-DOC-009."
        )

    if "execution admission" not in text:
        raise RuntimeError(
            "Resolved specification does not identify Execution Admission."
        )


def extract_requirements() -> list[Requirement]:
    lines = SPECIFICATION.read_text(
        encoding="utf-8"
    ).splitlines()

    requirements: list[Requirement] = []

    current_section = "UNSPECIFIED"

    for line_number, line in enumerate(lines, start=1):
        heading = HEADING_PATTERN.match(line)

        if heading:
            current_section = heading.group(2).strip()

        if not REQUIREMENT_PATTERN.search(line):
            continue

        stripped = line.strip()

        if not stripped:
            continue

        tokens = list(normalize_tokens(stripped))

        for token in extract_code_tokens(stripped):
            if token not in tokens:
                tokens.append(token)

        if not tokens:
            continue

        requirement_id = f"PB-DOC-009-R{len(requirements) + 1:03d}"

        requirements.append(
            Requirement(
                requirement_id=requirement_id,
                section=current_section,
                line_number=line_number,
                text=stripped,
                tokens=tuple(tokens),
            )
        )

    return requirements


def source_files() -> list[Path]:
    files: list[Path] = []

    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue

            files.append(path)

    return sorted(set(files))


def symbol_tokens(name: str, source: str) -> tuple[str, ...]:
    tokens = list(normalize_tokens(name))

    for token in normalize_tokens(source):
        if token not in tokens:
            tokens.append(token)

        if len(tokens) >= 80:
            break

    return tuple(tokens)


def extract_symbols(path: Path) -> list[Symbol]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="strict",
        )
        tree = ast.parse(source)
    except (OSError, UnicodeError, SyntaxError):
        return []

    symbols: list[Symbol] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = (
                "async_function"
                if isinstance(node, ast.AsyncFunctionDef)
                else "function"
            )

            symbols.append(
                Symbol(
                    path=path,
                    name=node.name,
                    kind=kind,
                    line_number=node.lineno,
                    tokens=symbol_tokens(
                        node.name,
                        ast.get_source_segment(source, node) or "",
                    ),
                )
            )

        elif isinstance(node, ast.ClassDef):
            symbols.append(
                Symbol(
                    path=path,
                    name=node.name,
                    kind="class",
                    line_number=node.lineno,
                    tokens=symbol_tokens(
                        node.name,
                        ast.get_source_segment(source, node) or "",
                    ),
                )
            )

    return symbols


def collect_symbols() -> list[Symbol]:
    symbols: list[Symbol] = []

    for path in source_files():
        symbols.extend(extract_symbols(path))

    return symbols


def score_match(
    requirement: Requirement,
    symbol: Symbol,
) -> int:
    requirement_tokens = set(requirement.tokens)
    symbol_token_set = set(symbol.tokens)

    overlap = requirement_tokens & symbol_token_set

    score = len(overlap)

    requirement_text = requirement.text.lower()
    symbol_name = symbol.name.lower()

    if symbol_name in requirement_text:
        score += 8

    for code_token in extract_code_tokens(requirement.text):
        if code_token.lower() == symbol_name:
            score += 10

    return score


def find_matches(
    requirement: Requirement,
    symbols: list[Symbol],
) -> list[EvidenceMatch]:
    matches: list[EvidenceMatch] = []

    for symbol in symbols:
        score = score_match(requirement, symbol)

        if score >= 2:
            matches.append(
                EvidenceMatch(
                    requirement=requirement,
                    symbol=symbol,
                    score=score,
                )
            )

    return sorted(
        matches,
        key=lambda match: (
            -match.score,
            str(match.symbol.path),
            match.symbol.line_number,
        ),
    )


def print_requirement(
    requirement: Requirement,
    matches: list[EvidenceMatch],
) -> None:
    print()
    print("-" * 78)
    print(
        f"{requirement.requirement_id} | "
        f"Specification L{requirement.line_number}"
    )
    print(f"Section: {requirement.section}")
    print(f"Requirement: {requirement.text}")

    if not matches:
        print("IMPLEMENTATION SYMBOL EVIDENCE: NONE")
        return

    print("IMPLEMENTATION SYMBOL CANDIDATES:")

    for match in matches[:8]:
        print(
            f"  SCORE={match.score:02d} | "
            f"{match.symbol.kind} "
            f"{match.symbol.name} | "
            f"{match.symbol.path}:L{match.symbol.line_number}"
        )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-009 — REQUIREMENT / IMPLEMENTATION EVIDENCE ANALYSIS")
    print("READ-ONLY")
    print()

    print(f"Repository: {REPO_ROOT}")
    print(f"PB-DOC: {PB_DOC}")
    print(f"Specification: {SPECIFICATION}")

    if not REPO_ROOT.is_dir():
        print("RESULT: FAIL — repository root missing.")
        return 1

    try:
        validate_specification()
    except RuntimeError as exc:
        print()
        print(f"RESULT: FAIL — {exc}")
        print("GOVERNANCE MUTATION: NONE")
        print("AUTHORIZATION GRANT: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        return 1

    print(f"Specification SHA256: {sha256(SPECIFICATION)}")

    requirements = extract_requirements()

    if not requirements:
        print()
        print("RESULT: FAIL — no normative requirements discovered.")
        return 1

    print(f"Normative requirement statements discovered: {len(requirements)}")

    print()
    print("=" * 78)
    print("1. SOURCE SYMBOL INVENTORY")
    print("=" * 78)

    symbols = collect_symbols()

    print(f"Python source symbols discovered: {len(symbols)}")

    source_symbol_counts: dict[Path, int] = {}

    for symbol in symbols:
        source_symbol_counts[symbol.path] = (
            source_symbol_counts.get(symbol.path, 0) + 1
        )

    for path, count in sorted(source_symbol_counts.items()):
        print(f"{path}: {count} symbols")

    print()
    print("=" * 78)
    print("2. REQUIREMENT → IMPLEMENTATION EVIDENCE")
    print("=" * 78)

    matched_requirements = 0
    unmatched_requirements = 0

    for requirement in requirements:
        matches = find_matches(requirement, symbols)

        if matches:
            matched_requirements += 1
        else:
            unmatched_requirements += 1

        print_requirement(
            requirement,
            matches,
        )

    print()
    print("=" * 78)
    print("3. COVERAGE SUMMARY")
    print("=" * 78)

    print(f"Normative requirements: {len(requirements)}")
    print(f"Requirements with candidate symbols: {matched_requirements}")
    print(f"Requirements without candidate symbols: {unmatched_requirements}")

    print()
    print("IMPORTANT:")
    print(
        "Candidate symbol matching is evidence discovery, "
        "not proof of implementation compliance."
    )

    print()
    print("=" * 78)
    print("4. ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 78)

    print("This analyzer does NOT classify:")
    print("  PRESERVE")
    print("  EXTEND")
    print("  NEW")
    print("  REFACTOR")
    print("  CONFLICT")

    print()
    print(
        "Those classifications require control-flow, security-control, "
        "and test-level verification."
    )

    print()
    print("=" * 78)
    print("5. SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 78)

    print("READ-ONLY: YES")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")

    print()
    print("=" * 78)
    print("6. FINAL RESULT")
    print("=" * 78)

    print(
        "RESULT: PASS — PB-DOC-009 REQUIREMENT / "
        "IMPLEMENTATION EVIDENCE DISCOVERY COMPLETED"
    )
    print("ARCHITECTURAL DECISION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")

    return 0


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PB_DOC = "PB-DOC-009"

SEARCH_ROOTS = (
    REPO_ROOT / "docs",
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
    REPO_ROOT / "tools",
)

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

SEARCH_TERMS = (
    "PB-DOC-009",
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION",
    "Execution Admission Specification",
    "execution-admission",
    "execution admission",
)

PATH_PATTERN = re.compile(
    r"(?:docs/|Library/)[^\s`|)\]>,]+(?:\.md|\.markdown)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Match:
    path: Path
    line_number: int
    line: str
    matched_terms: tuple[str, ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def discover_files() -> list[Path]:
    files: set[Path] = set()

    for root in SEARCH_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if should_skip(path):
                continue

            if path.suffix.lower() not in {".md", ".markdown", ".py", ".txt"}:
                continue

            files.add(path)

    return sorted(files)


def inspect_file(path: Path) -> list[Match]:
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
    except (OSError, UnicodeError):
        return []

    matches: list[Match] = []

    for line_number, line in enumerate(lines, start=1):
        lowered = line.lower()

        matched_terms = tuple(
            term
            for term in SEARCH_TERMS
            if term.lower() in lowered
        )

        if matched_terms:
            matches.append(
                Match(
                    path=path,
                    line_number=line_number,
                    line=line,
                    matched_terms=matched_terms,
                )
            )

    return matches


def collect_matches() -> list[Match]:
    matches: list[Match] = []

    for path in discover_files():
        matches.extend(inspect_file(path))

    return matches


def print_context(matches: list[Match]) -> None:
    grouped: dict[Path, list[Match]] = {}

    for match in matches:
        grouped.setdefault(match.path, []).append(match)

    for path in sorted(grouped):
        print()
        print("=" * 78)
        print(f"SOURCE: {path}")
        print(f"SHA256: {sha256(path)}")
        print("=" * 78)

        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="strict",
            ).splitlines()
        except (OSError, UnicodeError):
            print("UNABLE TO READ SOURCE FOR CONTEXT")
            continue

        displayed: set[int] = set()

        for match in grouped[path]:
            start = max(1, match.line_number - 3)
            end = min(len(lines), match.line_number + 3)

            for line_number in range(start, end + 1):
                if line_number in displayed:
                    continue

                displayed.add(line_number)
                print(
                    f"L{line_number}: "
                    f"{lines[line_number - 1]}"
                )


def extract_path_candidates(matches: list[Match]) -> set[str]:
    candidates: set[str] = set()

    for match in matches:
        for candidate in PATH_PATTERN.findall(match.line):
            candidates.add(candidate)

    return candidates


def classify_match(match: Match) -> str:
    terms = {term.lower() for term in match.matched_terms}

    if (
        "pb-doc-009" in terms
        and "execution admission specification" in terms
    ):
        return "PB-DOC-009 + SPECIFICATION IDENTITY"

    if "pb-doc-009" in terms:
        return "PB-DOC-009 REFERENCE"

    if (
        "lyrion_unified_core_execution_admission_specification"
        in terms
    ):
        return "EXPLICIT SPECIFICATION FILENAME"

    if "execution-admission" in terms:
        return "EXECUTION-ADMISSION PATH/REFERENCE"

    if "execution admission" in terms:
        return "EXECUTION ADMISSION REFERENCE"

    return "OTHER"


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-009 — REPOSITORY REFERENCE RESOLUTION")
    print("READ-ONLY EVIDENCE DISCOVERY")
    print()

    print(f"Repository: {REPO_ROOT}")
    print(f"PB-DOC: {PB_DOC}")
    print()

    if not REPO_ROOT.is_dir():
        print("RESULT: FAIL — repository root does not exist.")
        return 1

    matches = collect_matches()

    print("=" * 78)
    print("1. SEARCH SCOPE")
    print("=" * 78)

    for root in SEARCH_ROOTS:
        print(f"  - {root}")

    print()
    print(f"Files inspected: {len(discover_files())}")
    print(f"Matching lines: {len(matches)}")

    if not matches:
        print()
        print("RESULT: FAIL — no PB-DOC-009 related references discovered.")
        print("GOVERNANCE MUTATION: NONE")
        print("AUTHORIZATION GRANT: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        return 1

    print()
    print("=" * 78)
    print("2. MATCH CLASSIFICATION")
    print("=" * 78)

    counts: dict[str, int] = {}

    for match in matches:
        classification = classify_match(match)
        counts[classification] = counts.get(classification, 0) + 1

    for classification in sorted(counts):
        print(f"{classification}: {counts[classification]}")

    print()
    print("=" * 78)
    print("3. REPOSITORY REFERENCE EVIDENCE")
    print("=" * 78)

    print_context(matches)

    print()
    print("=" * 78)
    print("4. EXPLICIT TECHNICAL SPECIFICATION PATH CANDIDATES")
    print("=" * 78)

    path_candidates = extract_path_candidates(matches)

    if path_candidates:
        for candidate in sorted(path_candidates):
            print(f"  - {candidate}")
    else:
        print("NONE")

    print()
    print("=" * 78)
    print("5. SPECIFICATION FILENAME REFERENCES")
    print("=" * 78)

    specification_matches = [
        match
        for match in matches
        if "lyrion_unified_core_execution_admission_specification"
        in match.line.lower()
    ]

    if specification_matches:
        for match in specification_matches:
            print(
                f"{match.path}:L{match.line_number}: "
                f"{match.line.strip()}"
            )
    else:
        print("NONE")

    print()
    print("=" * 78)
    print("6. GOVERNANCE / ARCHITECTURAL BOUNDARY")
    print("=" * 78)

    print("This analyzer is evidence discovery only.")
    print()
    print("It does NOT:")
    print("  - select an authoritative specification")
    print("  - infer authority from filename")
    print("  - modify governance")
    print("  - modify documentation")
    print("  - modify source code")
    print("  - grant implementation authorization")
    print("  - authorize production")
    print("  - claim certification")
    print("  - assign PRESERVE / EXTEND / NEW / REFACTOR / CONFLICT")

    print()
    print("=" * 78)
    print("7. FINAL RESULT")
    print("=" * 78)

    if path_candidates:
        print(
            "RESULT: PASS — REPOSITORY REFERENCE DISCOVERY COMPLETED"
        )
        print(
            "FINDING: One or more explicit Markdown path candidates "
            "were discovered and require authoritative-link validation."
        )
    elif specification_matches:
        print(
            "RESULT: PASS — REPOSITORY REFERENCE DISCOVERY COMPLETED"
        )
        print(
            "FINDING: The technical specification filename is referenced, "
            "but no explicit Markdown path was discovered."
        )
    else:
        print(
            "RESULT: PASS — REPOSITORY REFERENCE DISCOVERY COMPLETED"
        )
        print(
            "FINDING: PB-DOC-009 references exist, but no explicit "
            "technical specification linkage was discovered."
        )

    print()
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")

    return 0


if __name__ == "__main__":
    sys.exit(main())

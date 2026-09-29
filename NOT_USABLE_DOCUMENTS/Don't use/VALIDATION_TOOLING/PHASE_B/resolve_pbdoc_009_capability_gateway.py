from __future__ import annotations

import ast
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SEARCH_ROOTS = (
    REPO_ROOT / "src",
    REPO_ROOT / "tests",
    REPO_ROOT / "docs" / "phase-b",
)

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}

SEARCH_TERMS = (
    "CapabilityGateway",
    "ExecutionAdmission",
    "execution-admission boundary",
    "execution admission boundary",
    "capability authorization",
    "def admit(",
    ".admit(",
)

PYTHON_SUFFIX = ".py"
DOC_SUFFIXES = {".md", ".txt"}


@dataclass(frozen=True)
class SymbolEvidence:
    path: Path
    name: str
    kind: str
    line: int
    end_line: int
    source: str


@dataclass(frozen=True)
class TextEvidence:
    path: Path
    line: int
    text: str
    term: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def eligible(path: Path) -> bool:
    return not any(
        part in EXCLUDED_PARTS
        for part in path.parts
    )


def repository_files() -> list[Path]:
    files: list[Path] = []

    for root in SEARCH_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if not eligible(path):
                continue

            if path.suffix in {PYTHON_SUFFIX, *DOC_SUFFIXES}:
                files.append(path)

    return sorted(set(files))


def extract_symbols(path: Path) -> list[SymbolEvidence]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="strict",
        )
        tree = ast.parse(source)
    except (OSError, UnicodeError, SyntaxError):
        return []

    results: list[SymbolEvidence] = []

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

            results.append(
                SymbolEvidence(
                    path=path,
                    name=qualified,
                    kind="class",
                    line=node.lineno,
                    end_line=getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    source=ast.get_source_segment(
                        source,
                        node,
                    )
                    or "",
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

            results.append(
                SymbolEvidence(
                    path=path,
                    name=qualified,
                    kind=(
                        "async_function"
                        if isinstance(
                            node,
                            ast.AsyncFunctionDef,
                        )
                        else "function"
                    ),
                    line=node.lineno,
                    end_line=getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    source=ast.get_source_segment(
                        source,
                        node,
                    )
                    or "",
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

    return results


def collect_python_symbols(
    files: list[Path],
) -> list[SymbolEvidence]:
    results: list[SymbolEvidence] = []

    for path in files:
        if path.suffix != PYTHON_SUFFIX:
            continue

        results.extend(
            extract_symbols(path)
        )

    return results


def collect_text_evidence(
    files: list[Path],
) -> list[TextEvidence]:
    results: list[TextEvidence] = []

    for path in files:
        if path.suffix not in {
            PYTHON_SUFFIX,
            *DOC_SUFFIXES,
        }:
            continue

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

            for term in SEARCH_TERMS:
                if term.lower() in lowered:
                    results.append(
                        TextEvidence(
                            path=path,
                            line=line_number,
                            text=line.strip(),
                            term=term,
                        )
                    )

    return results


def calls_in_symbol(
    symbol: SymbolEvidence,
) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(symbol.source)
    except SyntaxError:
        return []

    calls: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func

        if isinstance(function, ast.Name):
            name = function.id
        elif isinstance(function, ast.Attribute):
            name = function.attr
        else:
            continue

        calls.append(
            (
                name,
                getattr(node, "lineno", 0),
            )
        )

    return calls


def print_symbol(
    symbol: SymbolEvidence,
) -> None:
    print(
        f"  {symbol.kind:<15} "
        f"{symbol.name} "
        f"| {symbol.path}:L{symbol.line}"
    )


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print(
        "PB-DOC-009 — CAPABILITY GATEWAY "
        "REFERENCE RESOLUTION"
    )
    print("READ-ONLY")
    print()

    print(f"Repository: {REPO_ROOT}")

    if not REPO_ROOT.is_dir():
        print("RESULT: FAIL — repository root missing.")
        return 1

    files = repository_files()

    print(
        f"Searchable repository files: {len(files)}"
    )

    symbols = collect_python_symbols(files)
    text_evidence = collect_text_evidence(files)

    print(
        f"Python symbols discovered: {len(symbols)}"
    )
    print(
        f"Text/reference matches discovered: "
        f"{len(text_evidence)}"
    )

    print()
    print("=" * 78)
    print("1. EXACT CAPABILITY GATEWAY SYMBOLS")
    print("=" * 78)

    gateway_symbols = [
        symbol
        for symbol in symbols
        if "CapabilityGateway" in symbol.name
    ]

    if gateway_symbols:
        for symbol in gateway_symbols:
            print_symbol(symbol)
    else:
        print(
            "NO EXACT CapabilityGateway SYMBOL FOUND"
        )

    print()
    print("=" * 78)
    print("2. EXACT ADMISSION SYMBOLS")
    print("=" * 78)

    admission_symbols = [
        symbol
        for symbol in symbols
        if "ExecutionAdmission" in symbol.name
    ]

    if admission_symbols:
        for symbol in admission_symbols:
            print_symbol(symbol)
    else:
        print(
            "NO EXACT ExecutionAdmission SYMBOL FOUND"
        )

    print()
    print("=" * 78)
    print("3. ADMIT SYMBOLS")
    print("=" * 78)

    admit_symbols = [
        symbol
        for symbol in symbols
        if symbol.name.split(".")[-1] == "admit"
    ]

    if admit_symbols:
        for symbol in admit_symbols:
            print_symbol(symbol)
    else:
        print("NO admit() SYMBOL FOUND")

    print()
    print("=" * 78)
    print("4. EXACT REFERENCE LOCATIONS")
    print("=" * 78)

    important_matches = [
        evidence
        for evidence in text_evidence
        if evidence.term
        in {
            "CapabilityGateway",
            "ExecutionAdmission",
            "execution-admission boundary",
            "execution admission boundary",
        }
    ]

    for evidence in important_matches:
        print(
            f"{evidence.term:<32} "
            f"{evidence.path}:L{evidence.line}"
        )
        print(f"  {evidence.text}")

    if not important_matches:
        print("NO EXACT REFERENCE LOCATIONS FOUND")

    print()
    print("=" * 78)
    print("5. ADMISSION CALL-SITE ANALYSIS")
    print("=" * 78)

    for symbol in admit_symbols:
        calls = calls_in_symbol(symbol)

        print(
            f"{symbol.name} "
            f"| {symbol.path}:L{symbol.line}"
        )

        if not calls:
            print("  Calls: NONE")
            continue

        unique_calls: list[str] = []

        for name, line in calls:
            entry = f"{name}:L{line}"

            if entry not in unique_calls:
                unique_calls.append(entry)

        for entry in unique_calls[:50]:
            print(f"  CALL: {entry}")

    print()
    print("=" * 78)
    print("6. PB-DOC-009 REFERENCE INTERPRETATION")
    print("=" * 78)

    if gateway_symbols:
        print(
            "CapabilityGateway concrete symbol: FOUND"
        )
    else:
        print(
            "CapabilityGateway concrete symbol: NOT FOUND"
        )

    if admission_symbols:
        print(
            "ExecutionAdmission concrete symbol: FOUND"
        )
    else:
        print(
            "ExecutionAdmission concrete symbol: NOT FOUND"
        )

    if admit_symbols:
        print(
            "admit() implementation symbol: FOUND"
        )
    else:
        print(
            "admit() implementation symbol: NOT FOUND"
        )

    print()
    print(
        "This resolver does NOT assume that a similarly named "
        "component is the authoritative execution-admission boundary."
    )

    print()
    print("=" * 78)
    print("7. ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 78)

    print("NO CLASSIFICATION PERFORMED")
    print("PRESERVE: NOT ASSIGNED")
    print("EXTEND: NOT ASSIGNED")
    print("NEW: NOT ASSIGNED")
    print("REFACTOR: NOT ASSIGNED")
    print("CONFLICT: NOT ASSIGNED")

    print()
    print("=" * 78)
    print("8. SECURITY / GOVERNANCE BOUNDARY")
    print("=" * 78)

    print("READ-ONLY: YES")
    print("SOURCE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")
    print("MANIFEST MUTATION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")

    print()
    print("=" * 78)
    print("9. FINAL RESULT")
    print("=" * 78)

    print(
        "RESULT: PASS — CAPABILITY GATEWAY "
        "REFERENCE RESOLUTION COMPLETED"
    )

    print(
        "IMPORTANT: PASS means repository analysis completed; "
        "it does not establish architectural authority."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

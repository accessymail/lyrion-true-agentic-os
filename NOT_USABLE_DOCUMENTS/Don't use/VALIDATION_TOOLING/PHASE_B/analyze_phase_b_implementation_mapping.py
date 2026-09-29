from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


REPO_DEFAULT = Path("/home/aniket/lyrion-migration-verified")

MANIFEST_DEFAULT = Path(
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

SOURCE_ROOTS = (
    "src",
    "tests",
)

DOCUMENT_ROOTS = (
    "docs/phase-b",
)

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

PB_DOC_RE = re.compile(
    r"^\|\s*(PB-DOC-\d{3})\s*\|"
    r"\s*([^|]+?)\s*\|"
    r"\s*([^|]+?)\s*\|"
    r"\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

PATH_RE = re.compile(
    r"^(?:docs|src|tests|tools|scripts|config|configs|artifacts)/"
    r"[A-Za-z0-9_./-]+$"
)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")

STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "phase",
    "specification",
    "architecture",
    "document",
    "model",
    "system",
    "unified",
    "core",
    "implementation",
    "baseline",
    "validation",
    "pending",
    "planned",
    "closed",
    "open",
}


@dataclass(frozen=True)
class PbDoc:
    doc_id: str
    title: str
    reference: str
    status: str


@dataclass(frozen=True)
class Evidence:
    path: str
    score: int
    matched_terms: tuple[str, ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def normalize(value: str) -> str:
    value = value.strip()

    if (
        len(value) >= 2
        and value.startswith("`")
        and value.endswith("`")
    ):
        value = value[1:-1].strip()

    return value


def tokenize(value: str) -> set[str]:
    return {
        token.casefold()
        for token in WORD_RE.findall(value)
        if token.casefold() not in STOP_WORDS
    }


def parse_pb_docs(manifest_text: str) -> list[PbDoc]:
    documents: list[PbDoc] = []

    for match in PB_DOC_RE.finditer(manifest_text):
        documents.append(
            PbDoc(
                doc_id=match.group(1),
                title=normalize(match.group(2)),
                reference=normalize(match.group(3)),
                status=normalize(match.group(4)),
            )
        )

    return documents


def is_candidate_file(path: Path) -> bool:
    if not path.is_file():
        return False

    if any(part in IGNORED_DIRECTORIES for part in path.parts):
        return False

    return path.suffix.casefold() in {
        ".py",
        ".rs",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".java",
        ".kt",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
        ".md",
        ".yaml",
        ".yml",
        ".toml",
        ".json",
    }


def collect_files(repo: Path, roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []

    for root_name in roots:
        root = repo / root_name

        if not root.exists():
            continue

        for path in root.rglob("*"):
            if is_candidate_file(path):
                files.append(path)

    return sorted(set(files))


def safe_relative(repo: Path, path: Path) -> str:
    return path.resolve().relative_to(repo.resolve()).as_posix()


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def evidence_score(
    document: PbDoc,
    path: Path,
    content: str,
) -> Evidence | None:
    terms = tokenize(
        " ".join(
            (
                document.title,
                document.reference,
            )
        )
    )

    if not terms:
        return None

    path_terms = tokenize(path.stem)
    content_lower = content.casefold()

    matched: set[str] = set()

    for term in terms:
        if term in path_terms:
            matched.add(term)
            continue

        if re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(term)}"
            rf"(?![A-Za-z0-9_])",
            content_lower,
        ):
            matched.add(term)

    if not matched:
        return None

    score = 0

    for term in matched:
        if term in path_terms:
            score += 3
        else:
            score += 1

    return Evidence(
        path=path.as_posix(),
        score=score,
        matched_terms=tuple(sorted(matched)),
    )


def find_evidence(
    repo: Path,
    document: PbDoc,
    files: list[Path],
    limit: int,
) -> list[Evidence]:
    results: list[Evidence] = []

    for path in files:
        content = read_text_safely(path)

        if not content:
            continue

        evidence = evidence_score(
            document=document,
            path=path,
            content=content,
        )

        if evidence is not None:
            results.append(
                Evidence(
                    path=safe_relative(repo, path),
                    score=evidence.score,
                    matched_terms=evidence.matched_terms,
                )
            )

    results.sort(
        key=lambda item: (
            -item.score,
            item.path,
        )
    )

    return results[:limit]


def find_document_evidence(
    repo: Path,
    document: PbDoc,
    files: list[Path],
    limit: int,
) -> list[Evidence]:
    return find_evidence(
        repo=repo,
        document=document,
        files=files,
        limit=limit,
    )


def classify_reference(reference: str) -> str:
    normalized = normalize(reference)

    if normalized.casefold() in {
        "",
        "planned",
        "tbd",
        "to be defined",
        "not yet defined",
        "not defined",
    }:
        return "PLANNED"

    if PATH_RE.fullmatch(normalized):
        return "PATH"

    return "REFERENCE"


def print_document_header(
    document: PbDoc,
    reference_class: str,
) -> None:
    print()
    print("=" * 78)
    print(
        f"{document.doc_id} — {document.title}"
    )
    print("=" * 78)
    print(f"Status:             {document.status}")
    print(f"Reference:          {document.reference}")
    print(f"Reference class:    {reference_class}")


def print_evidence(
    heading: str,
    evidence: list[Evidence],
) -> None:
    print()
    print(heading)

    if not evidence:
        print("  NONE DISCOVERED")
        return

    for item in evidence:
        terms = ", ".join(item.matched_terms)

        print(
            f"  score={item.score:02d} | "
            f"{item.path} | "
            f"terms=[{terms}]"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Phase-B implementation mapping and "
            "candidate evidence analyzer."
        )
    )

    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_DEFAULT,
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_DEFAULT,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Maximum candidate evidence files per category.",
    )

    args = parser.parse_args()

    if args.limit < 1 or args.limit > 100:
        print("ERROR: --limit must be between 1 and 100.")
        return 2

    repo = args.repo_root.expanduser().resolve()

    manifest = args.manifest

    if not manifest.is_absolute():
        manifest = repo / manifest

    manifest = manifest.resolve()

    if not repo.is_dir():
        print(f"ERROR: repository root does not exist: {repo}")
        return 2

    if not (repo / ".git").exists():
        print(f"ERROR: repository is not a Git repository: {repo}")
        return 2

    if not manifest.is_file():
        print(
            "ERROR: authoritative Phase-B Master Manifest "
            f"not found: {manifest}"
        )
        return 2

    manifest_text = read_text_safely(manifest)

    if not manifest_text:
        print("ERROR: unable to read authoritative Master Manifest.")
        return 2

    documents = parse_pb_docs(manifest_text)

    if not documents:
        print(
            "ERROR: no PB-DOC registry entries found "
            "in the authoritative Master Manifest."
        )
        return 2

    source_files = collect_files(
        repo,
        SOURCE_ROOTS,
    )

    document_files = collect_files(
        repo,
        DOCUMENT_ROOTS,
    )

    print("===== PHASE-B IMPLEMENTATION MAPPING ANALYZER =====")
    print(f"Repository:        {repo}")
    print(f"Git HEAD:          ", end="")

    try:
        import subprocess

        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "rev-parse",
                "HEAD",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print(result.stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        print("UNAVAILABLE")

    print(
        "Manifest:          "
        f"{manifest.relative_to(repo)}"
    )
    print(f"Manifest SHA256:   {sha256(manifest)}")
    print(f"Source files:      {len(source_files)}")
    print(f"Document files:    {len(document_files)}")
    print(f"PB-DOC entries:    {len(documents)}")

    print()
    print(
        "IMPORTANT: Evidence discovery only. "
        "No architectural decision is made."
    )
    print(
        "DECISION STATES: PRESERVE / EXTEND / NEW / REFACTOR / "
        "CONFLICT / UNVERIFIED are NOT assigned by this tool."
    )

    for document in documents:
        reference_class = classify_reference(
            document.reference
        )

        print_document_header(
            document=document,
            reference_class=reference_class,
        )

        source_evidence = find_evidence(
            repo=repo,
            document=document,
            files=source_files,
            limit=args.limit,
        )

        test_evidence = [
            item
            for item in source_evidence
            if item.path.startswith("tests/")
        ]

        implementation_evidence = [
            item
            for item in source_evidence
            if item.path.startswith("src/")
        ]

        document_evidence = find_document_evidence(
            repo=repo,
            document=document,
            files=document_files,
            limit=args.limit,
        )

        print_evidence(
            "SOURCE IMPLEMENTATION CANDIDATES",
            implementation_evidence,
        )

        print_evidence(
            "TEST CANDIDATES",
            test_evidence,
        )

        print_evidence(
            "PHASE-B DOCUMENT CANDIDATES",
            document_evidence,
        )

        print()
        print(
            "ARCHITECTURAL ASSESSMENT: "
            "UNVERIFIED — HUMAN REVIEW REQUIRED"
        )

    print()
    print("=" * 78)
    print("===== ANALYZER RESULT =====")
    print("=" * 78)
    print("RESULT: PASS — READ-ONLY EVIDENCE DISCOVERY COMPLETED")
    print("ARCHITECTURAL DECISION: NONE")
    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("SOURCE CODE MUTATION: NONE")
    print("DOCUMENTATION MUTATION: NONE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

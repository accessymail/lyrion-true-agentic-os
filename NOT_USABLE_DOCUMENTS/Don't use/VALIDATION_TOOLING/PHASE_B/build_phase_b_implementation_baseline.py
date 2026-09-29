from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_DEFAULT = Path("/home/aniket/lyrion-migration-verified")

MANIFEST_DEFAULT = Path(
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

PB_DOC_RE = re.compile(
    r"^\|\s*(PB-DOC-\d{3})\s*\|"
    r"\s*([^|]+?)\s*\|"
    r"\s*([^|]+?)\s*\|"
    r"\s*([^|]+?)\s*\|",
    re.MULTILINE,
)

REPOSITORY_PATH_RE = re.compile(
    r"^(?:"
    r"docs|src|tests|tools|scripts|config|configs|artifacts"
    r")/"
    r"[A-Za-z0-9_./-]+$"
)

PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?:docs|src|tests|tools|config|configs|scripts|artifacts)"
    r"/[A-Za-z0-9_./-]+"
)


PLANNED_VALUES = {
    "",
    "planned",
    "tbd",
    "to be defined",
    "not yet defined",
    "not defined",
    "pending definition",
}


@dataclass(frozen=True)
class PbDoc:
    doc_id: str
    status: str
    path_reference: str
    description: str


@dataclass(frozen=True)
class ClassifiedPath:
    classification: str
    normalized_path: str | None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def git_value(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def normalize_reference(value: str) -> str:
    normalized = value.strip()

    if (
        len(normalized) >= 2
        and normalized.startswith("`")
        and normalized.endswith("`")
    ):
        normalized = normalized[1:-1].strip()

    return normalized


def classify_path_reference(value: str) -> ClassifiedPath:
    normalized = normalize_reference(value)
    lowered = normalized.casefold()

    if lowered in PLANNED_VALUES:
        return ClassifiedPath(
            classification="PLANNED",
            normalized_path=None,
        )

    if REPOSITORY_PATH_RE.fullmatch(normalized):
        return ClassifiedPath(
            classification="PATH",
            normalized_path=normalized,
        )

    return ClassifiedPath(
        classification="INVALID_REFERENCE",
        normalized_path=None,
    )


def parse_pb_docs(manifest_text: str) -> list[PbDoc]:
    documents: list[PbDoc] = []

    for match in PB_DOC_RE.finditer(manifest_text):
        documents.append(
            PbDoc(
                doc_id=match.group(1),
                status=match.group(2).strip(),
                path_reference=match.group(3).strip(),
                description=match.group(4).strip(),
            )
        )

    return documents


def safe_repo_path(repo: Path, relative: str) -> Path | None:
    candidate = (repo / relative).resolve()
    repository = repo.resolve()

    try:
        candidate.relative_to(repository)
    except ValueError:
        return None

    return candidate


def print_pbdoc_registry(repo: Path, documents: list[PbDoc]) -> None:
    print("===== AUTHORITATIVE PB-DOC REGISTRY =====")

    counts = {
        "PRESENT": 0,
        "PLANNED": 0,
        "MISSING": 0,
        "INVALID_REFERENCE": 0,
    }

    for item in documents:
        classified = classify_path_reference(item.path_reference)

        if classified.classification == "PLANNED":
            counts["PLANNED"] += 1
            print(
                f"{item.doc_id} | PLANNED | "
                f"{item.status} | {item.path_reference} | "
                f"{item.description}"
            )
            continue

        if classified.classification == "INVALID_REFERENCE":
            counts["INVALID_REFERENCE"] += 1
            print(
                f"{item.doc_id} | INVALID_REFERENCE | "
                f"{item.status} | {item.path_reference} | "
                f"{item.description}"
            )
            continue

        assert classified.normalized_path is not None

        target = safe_repo_path(repo, classified.normalized_path)

        if target is not None and target.is_file():
            counts["PRESENT"] += 1
            state = "PRESENT"
        else:
            counts["MISSING"] += 1
            state = "MISSING"

        print(
            f"{item.doc_id} | {state} | "
            f"{item.status} | {classified.normalized_path} | "
            f"{item.description}"
        )

    print()
    print("PB-DOC CLASSIFICATION SUMMARY")
    print(f"PRESENT:           {counts['PRESENT']}")
    print(f"PLANNED:           {counts['PLANNED']}")
    print(f"MISSING:           {counts['MISSING']}")
    print(f"INVALID_REFERENCE: {counts['INVALID_REFERENCE']}")
    print()


def print_implementation_surface(repo: Path) -> None:
    print("===== IMPLEMENTATION SURFACE INVENTORY =====")

    roots = (
        "src",
        "tests",
        "tools",
        "scripts",
        "config",
        "configs",
    )

    for root_name in roots:
        root = repo / root_name

        if not root.exists():
            continue

        count = sum(
            1
            for path in root.rglob("*")
            if path.is_file()
        )

        print(f"{root_name}/ | files={count}")

    print()


def print_manifest_references(
    repo: Path,
    manifest_text: str,
) -> None:
    print("===== MANIFEST-REFERENCED REPOSITORY PATHS =====")

    references = sorted(
        {
            normalize_reference(path)
            for path in PATH_TOKEN_RE.findall(manifest_text)
        }
    )

    missing = 0

    for relative in references:
        target = safe_repo_path(repo, relative)

        if target is None:
            print(f"INVALID | {relative}")
            continue

        if target.exists():
            print(f"PRESENT | {relative}")
        else:
            print(f"MISSING | {relative}")
            missing += 1

    print()

    print(
        "Manifest referenced-path summary: "
        f"{len(references)} references, {missing} missing."
    )
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a read-only Phase-B implementation baseline "
            "from the authoritative Master Manifest."
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

    args = parser.parse_args()

    repo = args.repo_root.expanduser().resolve()

    manifest = args.manifest

    if not manifest.is_absolute():
        manifest = repo / manifest

    manifest = manifest.resolve()

    if not repo.is_dir():
        print(f"ERROR: repository root does not exist: {repo}")
        return 2

    if not (repo / ".git").exists():
        print(f"ERROR: repository root is not a Git repository: {repo}")
        return 2

    if not manifest.is_file():
        print(
            "ERROR: authoritative Phase-B Master Manifest "
            f"not found: {manifest}"
        )
        return 2

    manifest_text = manifest.read_text(encoding="utf-8")

    documents = parse_pb_docs(manifest_text)

    if not documents:
        print(
            "ERROR: no PB-DOC registry entries found "
            "in the authoritative Master Manifest"
        )
        return 2

    commit = git_value(repo, "rev-parse", "HEAD")
    branch = git_value(repo, "branch", "--show-current")
    status = git_value(repo, "status", "--short")

    print("===== PHASE-B IMPLEMENTATION BASELINE =====")
    print(f"Repository: {repo}")
    print(f"Git branch: {branch or '(detached)'}")
    print(f"Git HEAD:   {commit}")
    print(f"Manifest:   {manifest.relative_to(repo)}")
    print(f"Manifest SHA256: {sha256(manifest)}")
    print()

    print_pbdoc_registry(repo, documents)
    print_implementation_surface(repo)
    print_manifest_references(repo, manifest_text)

    print("===== WORKTREE STATE =====")

    if status:
        print(status)
    else:
        print("CLEAN")

    print()

    classified_documents = [
        classify_path_reference(item.path_reference)
        for item in documents
    ]

    missing_documents = sum(
        1
        for item in classified_documents
        if item.classification == "MISSING"
    )

    invalid_documents = sum(
        1
        for item in classified_documents
        if item.classification == "INVALID_REFERENCE"
    )

    print("===== BASELINE DECISION =====")

    if missing_documents or invalid_documents:
        print(
            "RESULT: REVIEW REQUIRED — "
            "PHASE-B IMPLEMENTATION BASELINE HAS REFERENCE GAPS"
        )
    else:
        print(
            "RESULT: PASS — READ-ONLY PHASE-B "
            "IMPLEMENTATION BASELINE GENERATED"
        )

    print("MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("IMPLEMENTATION EXECUTION: NONE")

    return 0 if not missing_documents and not invalid_documents else 1


if __name__ == "__main__":
    raise SystemExit(main())

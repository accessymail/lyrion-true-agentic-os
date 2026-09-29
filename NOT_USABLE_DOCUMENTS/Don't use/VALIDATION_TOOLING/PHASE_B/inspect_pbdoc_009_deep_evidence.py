from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

PB_DOC = "PB-DOC-009"

MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

GAP_REGISTER = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md"
)

EXPECTED_SPEC_FILENAME = (
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

SOURCE_CANDIDATES = (
    "src/lyrion/capabilities/gateway.py",
    "src/lyrion/execution/contracts.py",
    "src/lyrion/execution/executor.py",
    "src/lyrion/execution/validator.py",
    "src/lyrion/integration/proactive_execution.py",
    "src/lyrion/persistence/execution_runner.py",
    "src/lyrion/piae/action_loop.py",
    "src/lyrion/piae/proactive_cycle.py",
    "src/lyrion/rpii/contracts.py",
    "src/lyrion/rpii/service.py",
)

TEST_CANDIDATES = (
    "tests/integration/test_postgresql_execution_runner.py",
    "tests/integration/test_postgresql_execution_runner_uow.py",
)

TOKEN_GROUPS = {
    "admission": (
        "ExecutionAdmission",
        "admission",
        "authorization",
    ),
    "execution": (
        "ExecutionRequest",
        "ExecutionResult",
        "ExecutionStatus",
        "executor",
        "execute",
    ),
    "policy": (
        "policy",
        "policy_version",
        "sandbox",
        "validator",
    ),
    "provenance": (
        "audit",
        "authorization_reference",
        "principal",
        "provenance",
    ),
}


@dataclass(frozen=True)
class Evidence:
    path: Path
    exists: bool
    matching_lines: tuple[tuple[int, str], ...]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relevant_lines(path: Path, tokens: tuple[str, ...]) -> tuple[tuple[int, str], ...]:
    if not path.exists():
        return ()

    results: list[tuple[int, str]] = []

    for line_number, line in enumerate(
        read_text(path).splitlines(),
        start=1,
    ):
        lowered = line.lower()
        if any(token.lower() in lowered for token in tokens):
            results.append((line_number, line.strip()))

    return tuple(results)


def discover_authoritative_spec() -> Path:
    """
    Resolve PB-DOC-009 through governance/reference documents.

    The Master Manifest and Gap Register are references, not themselves
    the technical PB-DOC-009 specification.

    Fail closed if:
      - governance/reference files are missing,
      - no explicit technical specification path is found,
      - multiple distinct technical specification paths are found,
      - the resolved path does not exist,
      - the resolved file does not identify itself as PB-DOC-009.
    """
    governance_files = (MANIFEST, GAP_REGISTER)

    missing = [str(path) for path in governance_files if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Required governance/reference document(s) missing:\n"
            + "\n".join(f"  - {path}" for path in missing)
        )

    candidate_paths: set[Path] = set()

    filename_pattern = re.compile(
        re.escape(EXPECTED_SPEC_FILENAME),
        re.IGNORECASE,
    )

    path_pattern = re.compile(
        r"(?:docs/phase-b/execution-admission/"
        r"Lyrion_Unified_Core_Execution_Admission_Specification_v1\.md"
        r"|docs/phase-b/execution-admission/"
        r"LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1\.md)",
        re.IGNORECASE,
    )

    for governance_path in governance_files:
        text = read_text(governance_path)

        for match in filename_pattern.finditer(text):
            del match
            candidate_paths.add(
                REPO_ROOT
                / "docs/phase-b/execution-admission/"
                / EXPECTED_SPEC_FILENAME
            )

        for match in path_pattern.finditer(text):
            del match
            candidate_paths.add(
                REPO_ROOT
                / "docs/phase-b/execution-admission/"
                / EXPECTED_SPEC_FILENAME
            )

    if not candidate_paths:
        raise RuntimeError(
            "PB-DOC-009 authoritative technical specification path "
            "was not explicitly referenced by the governance/reference documents."
        )

    if len(candidate_paths) != 1:
        formatted = "\n".join(f"  - {path}" for path in sorted(candidate_paths))
        raise RuntimeError(
            "Multiple distinct PB-DOC-009 technical specifications discovered; "
            f"failing closed.\n{formatted}"
        )

    specification = next(iter(candidate_paths))

    if not specification.is_file():
        raise RuntimeError(
            "Governance references PB-DOC-009 specification, "
            f"but the file does not exist: {specification}"
        )

    specification_text = read_text(specification).lower()

    if "pb-doc-009" not in specification_text:
        raise RuntimeError(
            "Resolved PB-DOC-009 specification does not identify itself "
            "as PB-DOC-009."
        )

    if "execution admission" not in specification_text:
        raise RuntimeError(
            "Resolved PB-DOC-009 specification does not identify "
            "Execution Admission."
        )

    return specification


def inspect_file(path: Path, tokens: tuple[str, ...]) -> Evidence:
    return Evidence(
        path=path,
        exists=path.is_file(),
        matching_lines=relevant_lines(path, tokens),
    )


def print_evidence(evidence: Evidence) -> None:
    print(f"\nPATH: {evidence.path}")
    print(f"EXISTS: {'YES' if evidence.exists else 'NO'}")

    if not evidence.exists:
        return

    if not evidence.matching_lines:
        print("MATCHING EVIDENCE: NONE")
        return

    for line_number, line in evidence.matching_lines[:40]:
        print(f"  L{line_number}: {line}")


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-009 — EXECUTION ADMISSION")
    print("DEEP EVIDENCE INSPECTION")
    print()

    if not REPO_ROOT.is_dir():
        print("RESULT: FAIL — repository root does not exist.")
        return 1

    if not MANIFEST.is_file():
        print(f"RESULT: FAIL — Master Manifest missing: {MANIFEST}")
        return 1

    print(f"Repository: {REPO_ROOT}")
    print(f"PB-DOC: {PB_DOC}")
    print(f"Manifest: {MANIFEST}")
    print(f"Manifest SHA256: {sha256(MANIFEST)}")
    print()

    print("=" * 78)
    print("1. GOVERNANCE-AWARE AUTHORITATIVE SPECIFICATION RESOLUTION")
    print("=" * 78)

    try:
        specification = discover_authoritative_spec()
    except RuntimeError as exc:
        print()
        print("RESULT: FAIL — PB-DOC-009 DEEP EVIDENCE INSPECTION ABORTED")
        print(f"REASON: {exc}")
        print("GOVERNANCE MUTATION: NONE")
        print("AUTHORIZATION GRANT: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        print("SOURCE CODE MUTATION: NONE")
        print("DOCUMENTATION MUTATION: NONE")
        print("MANIFEST MUTATION: NONE")
        return 1

    print(f"Authoritative specification: {specification}")
    print(f"Specification SHA256: {sha256(specification)}")

    spec_lines = read_text(specification).splitlines()

    print(f"Specification lines: {len(spec_lines)}")
    print("Resolution result: PASS")

    print()
    print("=" * 78)
    print("2. REQUIREMENT EVIDENCE")
    print("=" * 78)

    requirement_tokens = (
        "requirement",
        "shall",
        "must",
        "execution admission",
        "authorization",
        "admission",
        "fail closed",
        "verification",
        "provenance",
    )

    requirement_evidence = relevant_lines(
        specification,
        requirement_tokens,
    )

    if requirement_evidence:
        for line_number, line in requirement_evidence[:120]:
            print(f"L{line_number}: {line}")
    else:
        print("WARNING: No requirement evidence lines discovered.")

    print()
    print("=" * 78)
    print("3. SOURCE IMPLEMENTATION EVIDENCE")
    print("=" * 78)

    for relative_path in SOURCE_CANDIDATES:
        evidence = inspect_file(
            REPO_ROOT / relative_path,
            tuple(
                token
                for group in TOKEN_GROUPS.values()
                for token in group
            ),
        )
        print_evidence(evidence)

    print()
    print("=" * 78)
    print("4. TEST EVIDENCE")
    print("=" * 78)

    for relative_path in TEST_CANDIDATES:
        evidence = inspect_file(
            REPO_ROOT / relative_path,
            tuple(
                token
                for group in TOKEN_GROUPS.values()
                for token in group
            ),
        )
        print_evidence(evidence)

    print()
    print("=" * 78)
    print("5. EVIDENCE MATRIX")
    print("=" * 78)

    matrix_rows = (
        ("Requirement", bool(requirement_evidence)),
        (
            "Specification",
            specification.is_file(),
        ),
        (
            "Source implementation candidates",
            all(
                (REPO_ROOT / path).is_file()
                for path in SOURCE_CANDIDATES
            ),
        ),
        (
            "Test candidates",
            all(
                (REPO_ROOT / path).is_file()
                for path in TEST_CANDIDATES
            ),
        ),
    )

    for label, present in matrix_rows:
        print(f"{label}: {'PRESENT' if present else 'MISSING'}")

    print()
    print("=" * 78)
    print("6. ARCHITECTURAL DECISION BOUNDARY")
    print("=" * 78)

    print("This inspection performs evidence discovery only.")
    print("It does NOT assign:")
    print("  PRESERVE")
    print("  EXTEND")
    print("  NEW")
    print("  REFACTOR")
    print("  CONFLICT")
    print()
    print("A later architectural classification requires explicit")
    print("requirement-to-control-flow-to-test analysis.")

    print()
    print("=" * 78)
    print("7. SECURITY / GOVERNANCE BOUNDARY")
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
    print("8. FINAL RESULT")
    print("=" * 78)

    if not requirement_evidence:
        print(
            "RESULT: WARNING — AUTHORITATIVE SPECIFICATION RESOLVED, "
            "BUT REQUIREMENT EVIDENCE WAS NOT DISCOVERED."
        )
        return 0

    print("RESULT: PASS — GOVERNANCE-AWARE PB-DOC-009")
    print("DEEP EVIDENCE DISCOVERY COMPLETED")
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

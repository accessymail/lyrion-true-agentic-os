from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

GOVERNANCE_FILES = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    REPO_ROOT
    / "docs/phase-b/governance/"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md",
)

PB_DOC = "PB-DOC-009"

REFERENCE_TERMS = (
    "PB-DOC-009",
    "Execution Admission",
    "execution admission",
    "specification",
    "reference",
    "path",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def print_matching_context(
    path: Path,
    lines: list[str],
    match_lines: list[int],
) -> None:
    print()
    print("=" * 78)
    print(f"SOURCE: {path}")
    print(f"SHA256: {sha256(path)}")
    print("=" * 78)

    if not match_lines:
        print("NO PB-DOC-009 MATCHES")
        return

    displayed: set[int] = set()

    for match_line in match_lines:
        start = max(1, match_line - 5)
        end = min(len(lines), match_line + 5)

        for line_number in range(start, end + 1):
            if line_number in displayed:
                continue

            displayed.add(line_number)
            print(f"L{line_number}: {lines[line_number - 1]}")


def main() -> int:
    print("LYRION TRUE AGENTIC OS")
    print("PB-DOC-009 — GOVERNANCE REFERENCE INSPECTION")
    print("READ-ONLY EXACT-REFERENCE ANALYSIS")
    print()

    print(f"Repository: {REPO_ROOT}")
    print(f"PB-DOC: {PB_DOC}")
    print()

    missing = [
        str(path)
        for path in GOVERNANCE_FILES
        if not path.is_file()
    ]

    if missing:
        print("RESULT: FAIL — GOVERNANCE FILES MISSING")
        for path in missing:
            print(f"  - {path}")

        print("GOVERNANCE MUTATION: NONE")
        print("AUTHORIZATION GRANT: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        return 1

    total_matches = 0
    all_match_locations: list[tuple[Path, int, str]] = []

    for governance_path in GOVERNANCE_FILES:
        lines = governance_path.read_text(encoding="utf-8").splitlines()

        match_lines: list[int] = []

        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()

            if PB_DOC.lower() in lowered:
                match_lines.append(line_number)
                all_match_locations.append(
                    (governance_path, line_number, line)
                )

        print_matching_context(
            governance_path,
            lines,
            match_lines,
        )

        total_matches += len(match_lines)

    print()
    print("=" * 78)
    print("PB-DOC-009 EXACT MATCH SUMMARY")
    print("=" * 78)

    print(f"Total PB-DOC-009 matching lines: {total_matches}")

    if not all_match_locations:
        print("RESULT: FAIL — PB-DOC-009 NOT FOUND IN GOVERNANCE DOCUMENTS")
        print("GOVERNANCE MUTATION: NONE")
        print("AUTHORIZATION GRANT: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        return 1

    print()
    print("MATCH LOCATIONS:")

    for match_path, line_number, line in all_match_locations:
        print(f"  {match_path}:L{line_number}")
        print(f"    {line.strip()}")

    print()
    print("=" * 78)
    print("TECHNICAL SPECIFICATION REFERENCE DETECTION")
    print("=" * 78)

    candidate_paths: set[str] = set()

    path_pattern = re.compile(
        r"(?:docs/|Library/)[^\s`|)]+\.md",
        re.IGNORECASE,
    )

    for match_path, line_number, line in all_match_locations:
        del match_path, line_number

        for match in path_pattern.findall(line):
            candidate_paths.add(match)

    if candidate_paths:
        print("Markdown path candidates found on PB-DOC-009 lines:")

        for candidate in sorted(candidate_paths):
            print(f"  - {candidate}")
    else:
        print(
            "NO EXPLICIT MARKDOWN PATH FOUND ON PB-DOC-009 "
            "GOVERNANCE LINES."
        )

    print()
    print("=" * 78)
    print("EXECUTION ADMISSION REFERENCE ANALYSIS")
    print("=" * 78)

    execution_admission_lines = []

    for governance_path in GOVERNANCE_FILES:
        lines = governance_path.read_text(encoding="utf-8").splitlines()

        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()

            if (
                "execution admission" in lowered
                or "execution_admission" in lowered
            ):
                execution_admission_lines.append(
                    (governance_path, line_number, line)
                )

    print(
        "Execution Admission reference lines found: "
        f"{len(execution_admission_lines)}"
    )

    for match_path, line_number, line in execution_admission_lines:
        print(f"  {match_path}:L{line_number}")
        print(f"    {line.strip()}")

    print()
    print("=" * 78)
    print("GOVERNANCE DECISION BOUNDARY")
    print("=" * 78)

    print("This tool performs evidence discovery only.")
    print("It does NOT:")
    print("  - modify governance documents")
    print("  - modify the Master Manifest")
    print("  - modify PB-DOC specifications")
    print("  - grant implementation authorization")
    print("  - authorize production")
    print("  - execute privileged operations")
    print("  - select an authoritative specification by assumption")
    print("  - assign PRESERVE / EXTEND / NEW / REFACTOR / CONFLICT")

    print()
    print("=" * 78)
    print("FINAL RESULT")
    print("=" * 78)

    if not candidate_paths:
        print(
            "RESULT: PASS — GOVERNANCE REFERENCE INSPECTION COMPLETED"
        )
        print(
            "FINDING: PB-DOC-009 exists, but its technical specification "
            "path is not explicitly established on the PB-DOC-009 "
            "governance lines."
        )
        print("NEXT ACTION: REQUIRE FURTHER REFERENCE RESOLUTION")
    else:
        print(
            "RESULT: PASS — GOVERNANCE REFERENCE INSPECTION COMPLETED"
        )
        print(
            "FINDING: Candidate technical specification references "
            "were discovered and require validation."
        )

    print("GOVERNANCE MUTATION: NONE")
    print("AUTHORIZATION GRANT: NONE")
    print("PRIVILEGED EXECUTION: NONE")

    return 0


if __name__ == "__main__":
    sys.exit(main())

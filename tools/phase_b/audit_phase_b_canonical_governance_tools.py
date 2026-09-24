#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "tools" / "phase_b"

TARGETS = (
    "validate_phase_b_documentation.py",
    "review_phase_b_architecture_approval_gate.py",
    "consolidate_phase_b_architecture_approval_evidence.py",
    "record_phase_b_architecture_approval.py",
    "reconcile_phase_b_documents.py",
    "formal_architecture_approval_review.py",
    "reconcile_phase_b_cross_document_semantic_v3.py",
)

REFERENCE_TARGETS = {
    "review_phase_b_architecture_approval_gate.py",
    "consolidate_phase_b_architecture_approval_evidence.py",
    "record_phase_b_architecture_approval.py",
    "reconcile_phase_b_documents.py",
    "formal_architecture_approval_review.py",
    "reconcile_phase_b_cross_document_semantic_v3.py",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Unable to decode {path}: {exc}") from exc


def classify_mutation(text: str) -> str:
    mutation_patterns = (
        r"\.write_text\s*\(",
        r"\.write_bytes\s*\(",
        r"\.mkdir\s*\(",
        r"\.unlink\s*\(",
        r"\.rename\s*\(",
        r"\.replace\s*\(",
        r"shutil\.copy",
        r"shutil\.move",
        r"subprocess\.run\s*\(",
        r"subprocess\.Popen\s*\(",
    )

    for pattern in mutation_patterns:
        if re.search(pattern, text):
            return "MUTATING_OR_PROCESS"

    return "READ_ONLY"


def extract_docstring(text: str) -> str:
    match = re.search(
        r'^\s*(?:"""(.*?)"""|\'\'\'(.*?)\'\'\')',
        text,
        re.DOTALL,
    )
    if not match:
        return ""

    return (match.group(1) or match.group(2) or "").strip()


def extract_declared_references(text: str) -> list[str]:
    candidates = set()

    for match in re.findall(r"[A-Za-z0-9_]+\.py", text):
        if match in TARGETS or match in REFERENCE_TARGETS:
            candidates.add(match)

    return sorted(candidates)


def inspect_file(filename: str) -> dict[str, object]:
    path = TOOLS_DIR / filename

    if not path.exists():
        return {
            "name": filename,
            "exists": False,
            "classification": "MISSING",
            "references": [],
            "docstring": "",
        }

    text = read_text(path)

    return {
        "name": filename,
        "exists": True,
        "classification": classify_mutation(text),
        "references": extract_declared_references(text),
        "docstring": extract_docstring(text),
        "lines": len(text.splitlines()),
        "bytes": path.stat().st_size,
        "executable": bool(path.stat().st_mode & 0o111),
    }


def reference_audit() -> dict[str, list[str]]:
    references: dict[str, list[str]] = {
        name: [] for name in TARGETS
    }

    for source in sorted(TOOLS_DIR.glob("*.py")):
        if ".pre-" in source.name:
            continue

        if source.name == Path(__file__).name:
            continue

        try:
            text = read_text(source)
        except RuntimeError:
            continue

        for target in TARGETS:
            if target == source.name:
                continue

            if target in text:
                references[target].append(source.name)

    for target in references:
        references[target].sort()

    return references


def main() -> int:
    print("=" * 72)
    print("LYRION TRUE AGENTIC OS")
    print("PHASE-B CANONICAL GOVERNANCE TOOL AUDIT")
    print("=" * 72)
    print()
    print(f"Repository: {ROOT}")
    print(f"Tool directory: {TOOLS_DIR}")
    print()

    results = [inspect_file(name) for name in TARGETS]

    print("===== TOOL CLASSIFICATION =====")

    for result in results:
        print()
        print(f"[{result['name']}]")

        if not result["exists"]:
            print("  STATUS: MISSING")
            continue

        print(f"  STATUS: PRESENT")
        print(f"  CLASSIFICATION: {result['classification']}")
        print(f"  LINES: {result['lines']}")
        print(f"  BYTES: {result['bytes']}")
        print(f"  EXECUTABLE: {result['executable']}")

        references = result["references"]
        if references:
            print("  DECLARED REFERENCES:")
            for reference in references:
                print(f"    - {reference}")
        else:
            print("  DECLARED REFERENCES: NONE")

    print()
    print("===== REPOSITORY REFERENCE GRAPH =====")

    references = reference_audit()

    for target in TARGETS:
        print()
        print(f"{target}")

        sources = references.get(target, [])

        if not sources:
            print("  referenced by: NONE")
        else:
            for source in sources:
                print(f"  referenced by: {source}")

    print()
    print("===== BACKUP / INTERMEDIATE FILE CHECK =====")

    backups = sorted(
        list(TOOLS_DIR.glob("*.pre-*"))
        + list(
            (ROOT / "docs" / "phase-b" / "governance").glob("*.pre-*")
        )
    )

    if backups:
        for path in backups:
            print(f"  EXCLUDE: {path.relative_to(ROOT)}")
    else:
        print("  NONE FOUND")

    print()
    print("===== GOVERNANCE STATE CHECK =====")

    manifest = (
        ROOT
        / "docs"
        / "phase-b"
        / "governance"
        / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
    )

    if not manifest.exists():
        print("  MANIFEST: MISSING")
        return 2

    manifest_text = read_text(manifest)

    expected = {
        "Architecture Approval": "APPROVED",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    governance_pass = True

    for field, expected_value in expected.items():
        pattern = rf"{re.escape(field)}:\s*\**\s*([A-Z][A-Z _-]*)"
        match = re.search(pattern, manifest_text)

        if not match:
            print(f"  {field}: NOT FOUND")
            governance_pass = False
            continue

        actual = match.group(1).strip().rstrip("*").strip()

        print(f"  {field}: {actual}")

        if actual != expected_value:
            governance_pass = False

    print()
    print("===== FINAL RESULT =====")

    missing = [
        result["name"]
        for result in results
        if not result["exists"]
    ]

    if missing:
        print("RESULT: REVIEW")
        print("Missing canonical candidate(s):")
        for name in missing:
            print(f"  - {name}")
        return 2

    if not governance_pass:
        print("RESULT: FAIL — GOVERNANCE STATE MISMATCH")
        return 1

    print("RESULT: PASS — CANONICAL GOVERNANCE TOOL AUDIT PASSED")
    print("Architecture Approval: APPROVED")
    print("Implementation Authorization: NOT AUTHORIZED")
    print("Production Implementation: BLOCKED")
    print("Production Certification: NOT CLAIMED")
    print()
    print("NO FILES WERE MODIFIED BY THIS AUDIT.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "phase_b"
MANIFEST = (
    ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

CANDIDATES = (
    "tools/phase_b/validate_phase_b_documentation.py",
    "tools/phase_b/review_phase_b_architecture_approval_gate.py",
    "tools/phase_b/consolidate_phase_b_architecture_approval_evidence.py",
    "tools/phase_b/record_phase_b_architecture_approval.py",
    "tools/phase_b/reconcile_phase_b_documents.py",
    "tools/phase_b/formal_architecture_approval_review.py",
    "tools/phase_b/reconcile_phase_b_cross_document_semantic_v3.py",
    "tools/phase_b/audit_phase_b_canonical_governance_tools.py",
    "docs/phase-b/governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
)

EXCLUDED_PATTERNS = (
    ".pre-",
    ".lyrion-g47-evidence",
    "docs/g47/",
    "docs/OLD DOCS/",
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def check_compile() -> bool:
    print("===== PYTHON COMPILE =====")

    ok = True

    for relative in CANDIDATES:
        path = ROOT / relative

        if path.suffix != ".py":
            continue

        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

        if result.returncode == 0:
            print(f"PASS  {relative}")
        else:
            ok = False
            print(f"FAIL  {relative}")
            print(result.stderr.strip())

    return ok


def check_candidates() -> bool:
    print()
    print("===== CANDIDATE FILES =====")

    ok = True

    for relative in CANDIDATES:
        path = ROOT / relative

        if path.exists():
            print(f"PASS  {relative}")
        else:
            ok = False
            print(f"FAIL  MISSING {relative}")

    return ok


def check_exclusions() -> bool:
    print()
    print("===== EXCLUSION CHECK =====")

    ok = True

    output = run_git("status", "--short", "--untracked-files=all")

    for line in output.splitlines():
        if not line:
            continue

        path = line[3:] if len(line) >= 3 else line

        if any(pattern in path for pattern in EXCLUDED_PATTERNS):
            print(f"EXCLUDE  {path}")

    print("PASS  No excluded-path candidate will be staged by this audit.")

    return ok


def check_manifest() -> bool:
    print()
    print("===== GOVERNANCE MANIFEST =====")

    if not MANIFEST.exists():
        print("FAIL  Manifest missing")
        return False

    text = MANIFEST.read_text(encoding="utf-8")

    expected = {
        "Architecture Approval": "APPROVED",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    ok = True

    for field, expected_value in expected.items():
        pattern = rf"{re.escape(field)}:\s*\**\s*([A-Z][A-Z _-]*)"
        match = re.search(pattern, text)

        if not match:
            print(f"FAIL  {field}: NOT FOUND")
            ok = False
            continue

        actual = match.group(1).strip().rstrip("*").strip()

        if actual == expected_value:
            print(f"PASS  {field}: {actual}")
        else:
            print(
                f"FAIL  {field}: expected={expected_value!r} "
                f"actual={actual!r}"
            )
            ok = False

    return ok


def check_g47_separation() -> bool:
    print()
    print("===== G47 / OLD-DOC SEPARATION =====")

    status = run_git("status", "--short", "--untracked-files=all")

    protected = []

    for line in status.splitlines():
        path = line[3:] if len(line) >= 3 else line

        if (
            ".lyrion-g47-evidence" in path
            or path.startswith("docs/g47/")
            or path.startswith("docs/OLD DOCS/")
        ):
            protected.append(path)

    if protected:
        for path in protected:
            print(f"PASS  SEPARATE: {path}")
    else:
        print("PASS  No G47/OLD DOCS files detected.")

    return True


def check_git_diff() -> bool:
    print()
    print("===== TRACKED DIFF =====")

    diff = run_git("diff", "--", str(MANIFEST.relative_to(ROOT)))

    if diff:
        print(diff)
    else:
        print("INFO  No tracked manifest diff detected.")

    return True


def main() -> int:
    print("=" * 72)
    print("LYRION TRUE AGENTIC OS")
    print("FINAL PHASE-B COMMIT BOUNDARY AUDIT")
    print("=" * 72)
    print()
    print(f"Repository: {ROOT}")

    checks = (
        check_candidates(),
        check_compile(),
        check_manifest(),
        check_exclusions(),
        check_g47_separation(),
        check_git_diff(),
    )

    print()
    print("===== FINAL RESULT =====")

    if all(checks):
        print("RESULT: PASS — FINAL COMMIT BOUNDARY AUDIT PASSED")
        print()
        print("NO FILES WERE STAGED.")
        print("NO FILES WERE COMMITTED.")
        print("NO FILES WERE PUSHED.")
        print()
        print("Architecture Approval: APPROVED")
        print("Implementation Authorization: NOT AUTHORIZED")
        print("Production Implementation: BLOCKED")
        print("Production Certification: NOT CLAIMED")
        return 0

    print("RESULT: FAIL — COMMIT BOUNDARY AUDIT FAILED")
    print("DO NOT STAGE OR COMMIT.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

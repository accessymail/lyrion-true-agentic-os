#!/usr/bin/env python3
"""
LYRION True Agentic OS
Aegis Bounded Slice Documentation Synchronization

CONTROLLED DOCUMENTATION OPERATION.

Scope:
    Synchronize the accepted Aegis bounded slice into the governed
    documentation/manifests without claiming full PB-DOC-010 validation.

This tool:
    - verifies the accepted Aegis evidence
    - verifies the accepted repository state
    - creates immutable backups before modification
    - updates only explicitly targeted documentation
    - creates the bounded Aegis acceptance record
    - creates a synchronization report

This tool does NOT:
    - modify src/
    - modify tests/
    - modify Aegis runtime implementation
    - modify G46.5/G47
    - modify R097
    - claim production certification
    - claim full PB-DOC-010 validation
    - commit Git
    - push GitHub
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]

EXPECTED_HEAD = "48f5a790e381785282d7703d6a7efa7aeb5f527c"

EVIDENCE_GLOB = "lyrion-aegis-bounded-validation-*"

TARGETS = [
    REPO / "Manifest.md",
    REPO / "docs/Manifest.md",
    REPO / "docs/phase-b/governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
    REPO / "docs/phase-b/execution-admission/LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
]

ACCEPTANCE_RECORD = (
    REPO
    / "docs/phase-b/validation/AEGIS_BOUNDED_SLICE_ACCEPTANCE_RECORD_v1.md"
)

BACKUP_ROOT = (
    REPO
    / "NOT_USABLE_DOCUMENTS"
    / "Don't use"
    / "PHASE_B_DOCUMENTATION_SYNC_BACKUPS"
)

REPORT_PATH = (
    REPO
    / "tools/phase_b/audit/aegis_documentation_sync_report.json"
)


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def latest_evidence() -> Path | None:
    candidates = sorted(
        path
        for path in Path("/tmp").glob(EVIDENCE_GLOB)
        if path.is_dir()
    )

    return candidates[-1] if candidates else None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def verify_repository() -> None:
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")

    require(
        head == EXPECTED_HEAD,
        f"Unexpected HEAD: {head}",
    )

    require(
        origin == EXPECTED_HEAD,
        f"Unexpected origin/main: {origin}",
    )


def verify_evidence(evidence: Path) -> dict:
    required = [
        "environment.txt",
        "A_static_compile.txt",
        "B_aegis_core.txt",
        "C_gateway.txt",
        "D_secure_executor.txt",
        "E_result_state.txt",
        "post_validation_integrity.txt",
    ]

    for filename in required:
        require(
            (evidence / filename).is_file(),
            f"Missing evidence file: {filename}",
        )

    expected_counts = {
        "B_aegis_core.txt": 68,
        "C_gateway.txt": 30,
        "D_secure_executor.txt": 48,
        "E_result_state.txt": 6,
    }

    results = {}

    for filename, expected in expected_counts.items():
        text = (evidence / filename).read_text(encoding="utf-8")

        marker = f"{expected} passed"

        require(
            marker in text,
            f"Expected pytest result not found in {filename}: {marker}",
        )

        results[filename] = expected

    return results


def verify_runtime_boundaries() -> None:
    diff = git(
        "diff",
        "--name-only",
        EXPECTED_HEAD,
        "--",
        "src",
        "tests",
    )

    require(
        diff == "",
        f"Runtime/test modifications detected:\n{diff}",
    )


def create_backup(timestamp: str) -> Path:
    backup_root = BACKUP_ROOT / timestamp
    backup_root.mkdir(parents=True, exist_ok=False)

    for target in TARGETS:
        require(
            target.is_file(),
            f"Required documentation target missing: {target}",
        )

        relative = target.relative_to(REPO)
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(target, destination)

        require(
            sha256(target) == sha256(destination),
            f"Backup verification failed: {target}",
        )

    return backup_root


def bounded_status_block() -> str:
    return """
### Aegis Policy Decision Boundary — Bounded Slice Status

- **Bounded Aegis implementation:** PRESENT
- **Controlled validation:** 152/152 PASS
- **Controlled evidence review:** VERIFIED
- **Bounded Aegis slice acceptance:** ACCEPTED
- **Scope:** bounded policy-decision validation slice only
- **Full PB-DOC-010 validation:** NOT VALIDATED
- **Phase-B production implementation:** BLOCKED
- **Production certification:** NOT CLAIMED
- **G46.5/G47:** NOT RECONSTRUCTED / BLOCKED
- **R097:** UNCHANGED

This status records acceptance of the bounded Aegis validation slice only.
It does not constitute full PB-DOC-010 validation, production operation,
or production certification.
""".strip()


def update_manifest(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    marker = "### Aegis Policy Decision Boundary — Bounded Slice Status"

    if marker in text:
        return

    insertion = "\n\n" + bounded_status_block() + "\n"

    path.write_text(
        text.rstrip() + insertion,
        encoding="utf-8",
    )


def update_execution_spec(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    marker = "### Bounded Aegis Slice Acceptance Status"

    if marker in text:
        return

    block = """
### Bounded Aegis Slice Acceptance Status

The Aegis policy-decision boundary has completed a controlled bounded
validation and acceptance cycle.

- Controlled validation: **152/152 PASS**
- Controlled evidence review: **VERIFIED**
- Bounded slice acceptance: **ACCEPTED**
- Full PB-DOC-010 validation: **NOT VALIDATED**
- Production implementation: **BLOCKED**
- Production certification: **NOT CLAIMED**

This entry does not change the validation requirements or production
acceptance requirements of the full Execution Admission specification.
""".strip()

    path.write_text(
        text.rstrip() + "\n\n" + block + "\n",
        encoding="utf-8",
    )


def create_acceptance_record(
    evidence: Path,
    timestamp: str,
    backup_root: Path,
    results: dict,
) -> None:
    record = f"""# Aegis Bounded Slice Acceptance Record

**Project:** LYRION True Agentic OS  
**Boundary:** Aegis Policy Decision Boundary  
**Record Version:** 1.0.0  
**Acceptance Date UTC:** {timestamp}  
**Validated Commit:** `{EXPECTED_HEAD}`

## Acceptance Decision

**AEGIS_BOUNDED_SLICE_ACCEPTED**

## Evidence

Controlled validation evidence directory:

`{evidence}`

Controlled validation results:

| Validation Group | Result |
|---|---:|
| A — Static compilation | PASS |
| B — Aegis policy / authorization / guards / replay | {results["B_aegis_core.txt"]} passed |
| C — Capability contracts / gateway | {results["C_gateway.txt"]} passed |
| D — Secure executor | {results["D_secure_executor.txt"]} passed |
| E — Execution result state | {results["E_result_state.txt"]} passed |
| **Total** | **152 passed / 0 failed** |

## Integrity

The final acceptance review verified:

- Runtime SHA-256 integrity preserved.
- Test SHA-256 integrity preserved.
- Git HEAD preserved.
- `origin/main` preserved.
- Protected `src/`, `tests/`, `docs/`, and `Manifest.md` paths preserved.
- Controlled evidence artifacts present.
- Aegis bounded validation scope preserved.

## Governance Boundary

This record accepts only the bounded Aegis policy-decision validation
slice.

It does **not** establish:

- full PB-DOC-010 validation;
- Phase-B production implementation;
- production operation;
- production certification;
- G46.5 recovery;
- G47 recovery or closure;
- any change to R097.

## Documentation Synchronization

Documentation backups were created before synchronization:

`{backup_root}`

No runtime implementation or test files were modified by this
documentation synchronization operation.

## Status

**BOUNDARY ACCEPTED — PRODUCTION BLOCKED — CERTIFICATION NOT CLAIMED**
"""

    ACCEPTANCE_RECORD.parent.mkdir(parents=True, exist_ok=True)

    if ACCEPTANCE_RECORD.exists():
        existing = ACCEPTANCE_RECORD.read_text(encoding="utf-8")

        if "AEGIS_BOUNDED_SLICE_ACCEPTED" in existing:
            return

        raise RuntimeError(
            f"Acceptance record already exists with unexpected content: "
            f"{ACCEPTANCE_RECORD}"
        )

    ACCEPTANCE_RECORD.write_text(record, encoding="utf-8")


def write_report(
    timestamp: str,
    evidence: Path,
    backup_root: Path,
    before: dict[str, str],
    after: dict[str, str],
    results: dict,
) -> None:
    report = {
        "project": "LYRION True Agentic OS",
        "operation": "Aegis bounded slice documentation synchronization",
        "timestamp_utc": timestamp,
        "decision": "DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW",
        "validated_commit": EXPECTED_HEAD,
        "evidence_directory": str(evidence),
        "acceptance_record": str(ACCEPTANCE_RECORD.relative_to(REPO)),
        "backup_root": str(backup_root.relative_to(REPO)),
        "validation_results": results,
        "before_sha256": before,
        "after_sha256": after,
        "runtime_modified": False,
        "tests_modified": False,
        "g46_5_reconstructed": False,
        "g47_reconstructed": False,
        "r097_modified": False,
        "production_certification_claimed": False,
        "git_commit_created": False,
        "git_push_performed": False,
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    print("=" * 82)
    print("LYRION TRUE AGENTIC OS")
    print("AEGIS BOUNDED SLICE DOCUMENTATION SYNCHRONIZATION")
    print("CONTROLLED OPERATION")
    print("=" * 82)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    print("\nPRE-SYNCHRONIZATION VALIDATION")

    verify_repository()
    print("[PASS] HEAD == origin/main == validated commit")

    evidence = latest_evidence()
    require(
        evidence is not None,
        "No Aegis controlled-validation evidence directory found.",
    )

    print(f"[PASS] Evidence: {evidence}")

    results = verify_evidence(evidence)
    print("[PASS] Controlled evidence contains expected validation results")

    verify_runtime_boundaries()
    print("[PASS] No src/tests tracked modifications")

    before = {
        str(path.relative_to(REPO)): sha256(path)
        for path in TARGETS
    }

    print("[PASS] Documentation target hashes captured")

    print("\nBACKUP")

    backup_root = create_backup(timestamp)
    print(f"[PASS] Backups created: {backup_root}")

    print("\nDOCUMENTATION SYNCHRONIZATION")

    for target in TARGETS:
        if target.name == "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md":
            update_execution_spec(target)
        else:
            update_manifest(target)

        print(f"[PASS] synchronized: {target.relative_to(REPO)}")

    create_acceptance_record(
        evidence,
        timestamp,
        backup_root,
        results,
    )
    print(
        f"[PASS] acceptance record: "
        f"{ACCEPTANCE_RECORD.relative_to(REPO)}"
    )

    after = {
        str(path.relative_to(REPO)): sha256(path)
        for path in TARGETS
    }

    write_report(
        timestamp,
        evidence,
        backup_root,
        before,
        after,
        results,
    )

    print(
        f"[PASS] synchronization report: "
        f"{REPORT_PATH.relative_to(REPO)}"
    )

    print("\nPOST-SYNCHRONIZATION SAFETY REVIEW")

    verify_repository()
    print("[PASS] HEAD/origin unchanged")

    verify_runtime_boundaries()
    print("[PASS] src/tests remain unchanged")

    print("\n" + "=" * 82)
    print("DOCUMENTATION SYNCHRONIZATION DECISION")
    print("=" * 82)

    print("DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW")
    print()
    print("PASS: Aegis bounded acceptance recorded.")
    print("PASS: Documentation backups preserved.")
    print("PASS: Runtime implementation untouched.")
    print("PASS: Tests untouched.")
    print("PASS: G46.5/G47 untouched.")
    print("PASS: R097 untouched.")
    print("PASS: Production certification NOT CLAIMED.")
    print()
    print("NEXT: independent documentation-diff review required.")
    print("NO GIT COMMIT OR PUSH PERFORMED.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/aniket/lyrion-migration-verified")

MASTER = ROOT / (
    "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

EXECUTION_SPEC = ROOT / (
    "docs/phase-b/execution-admission/"
    "LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md"
)

MANIFEST = ROOT / "Manifest.md"
DOCS_MANIFEST = ROOT / "docs/Manifest.md"

ACCEPTANCE = ROOT / (
    "docs/phase-b/validation/"
    "EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md"
)

BACKUP_ROOT = ROOT / (
    "NOT_USABLE_DOCUMENTS/Don't use/"
    "PHASE_B_DOCUMENTATION_SYNC_BACKUPS"
)

EXPECTED_HEAD = "7b1f7fd676d32194748d8ba4f603a42edb3cf4cc"

PB021_SHA = (
    "0173c17f0a0856074fe0abe72be158bbea2170ab94b4b7a29993c405f805fdf9"
)

RUNTIME = [
    ROOT / "src/lyrion/capabilities/gateway.py",
    ROOT / "src/lyrion/execution/contracts.py",
    ROOT / "src/lyrion/execution/validator.py",
    ROOT / "src/lyrion/execution/executor.py",
]


def cmd(*args: str) -> str:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_files() -> None:
    for path in [MASTER, EXECUTION_SPEC, MANIFEST, DOCS_MANIFEST]:
        if not path.is_file():
            raise RuntimeError(f"Missing required file: {path}")


def verify_baseline() -> None:
    head = cmd("git", "rev-parse", "HEAD")
    origin = cmd("git", "rev-parse", "origin/main")

    if head != EXPECTED_HEAD or origin != EXPECTED_HEAD:
        raise RuntimeError(
            "Repository baseline mismatch:\n"
            f"HEAD={head}\n"
            f"origin/main={origin}\n"
            f"expected={EXPECTED_HEAD}"
        )

    if MANIFEST.read_bytes() != DOCS_MANIFEST.read_bytes():
        raise RuntimeError(
            "Manifest.md and docs/Manifest.md are not identical."
        )


def backup(path: Path, timestamp: str) -> None:
    destination = (
        BACKUP_ROOT
        / timestamp
        / path.relative_to(ROOT)
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(path.read_bytes())


def append_once(path: Path, marker: str, block: str) -> bool:
    text = path.read_text(encoding="utf-8")

    if marker in text:
        return False

    path.write_text(
        text.rstrip() + "\n\n" + block.strip() + "\n",
        encoding="utf-8",
    )
    return True


def create_acceptance_record(timestamp: str, hashes: dict[str, str]) -> None:
    if ACCEPTANCE.exists():
        existing = ACCEPTANCE.read_text(encoding="utf-8")

        if "EXECUTION_ADMISSION_SLICE_ACCEPTED" not in existing:
            raise RuntimeError(
                f"Refusing to overwrite unrelated file: {ACCEPTANCE}"
            )
        return

    ACCEPTANCE.parent.mkdir(parents=True, exist_ok=True)

    content = f"""# LYRION TRUE AGENTIC OS — Execution Admission Slice Acceptance Record

**Document Type:** Controlled Validation / Acceptance Record  
**Version:** 1.0.0  
**Timestamp UTC:** {timestamp}

## Scope

This record covers only the bounded Execution Admission implementation-
validation slice reviewed on 2026-09-29.

It does not constitute:

- full PB-DOC-009 validation;
- production implementation approval;
- production operation;
- production certification;
- G46.5 reconstruction;
- G47 reconstruction;
- R097 closure or modification;
- authorization for unrelated Phase-B implementation.

## Governance

- Phase-B Implementation Authorization: `AUTHORIZED`
- Production Implementation: `BLOCKED`
- Production Certification: `NOT CLAIMED`
- PB-DOC-021 SHA-256: `{PB021_SHA}`

## Controlled Validation

- Runtime compilation: `4/4 PASS`
- Test A: `53 passed`
- Test B: `6 passed`
- Test C: `27 passed`
- Total: `86 passed / 0 failed`
- Evidence review: `CONTROLLED_VALIDATION_EVIDENCE_VERIFIED`
- Slice acceptance: `EXECUTION_ADMISSION_SLICE_ACCEPTED`

## Runtime Integrity

"""

    for path in RUNTIME:
        key = str(path.relative_to(ROOT))
        content += f"- `{key}` — `{hashes[key]}`\n"

    content += """
## Protected Boundaries

- Production certification: NOT CLAIMED
- G46.5 reconstruction: NOT PERFORMED
- G47 reconstruction: NOT PERFORMED
- R097 modification: NOT PERFORMED
- Git commit: NOT PERFORMED
- Git push: NOT PERFORMED

## Final State

**EXECUTION_ADMISSION_SLICE_ACCEPTED**

Full PB-DOC-009 validation remains distinct and is not claimed by this
bounded acceptance record.
"""

    ACCEPTANCE.write_text(content, encoding="utf-8")


def main() -> int:
    timestamp = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    require_files()
    verify_baseline()

    before_runtime = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in RUNTIME
    }

    for path in [MASTER, EXECUTION_SPEC, MANIFEST, DOCS_MANIFEST]:
        backup(path, timestamp)

    create_acceptance_record(timestamp, before_runtime)

    master_block = f"""
## Controlled Execution Admission Slice Validation Record

- Bounded slice: `Execution Admission`
- State: `EXECUTION_ADMISSION_SLICE_ACCEPTED`
- Runtime compilation: `4/4 PASS`
- Controlled validation: `86 PASSED / 0 FAILED`
- Evidence review: `CONTROLLED_VALIDATION_EVIDENCE_VERIFIED`
- Full PB-DOC-009 validation: `NOT CLAIMED`
- Production implementation: `BLOCKED`
- Production certification: `NOT CLAIMED`
- G46.5/G47 reconstruction: `NOT PERFORMED`
- R097 modification: `NOT PERFORMED`
- Acceptance record:
  `docs/phase-b/validation/EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md`
"""

    execution_block = """
## Controlled Implementation-Validation Slice Record

The bounded Execution Admission implementation-validation slice has
evidence-backed acceptance.

- Runtime compilation: `4/4 PASS`
- Tests: `86 PASSED / 0 FAILED`
- Evidence review: `CONTROLLED_VALIDATION_EVIDENCE_VERIFIED`
- Slice acceptance: `EXECUTION_ADMISSION_SLICE_ACCEPTED`
- Full PB-DOC-009 validation: `NOT CLAIMED`
- Production implementation: `BLOCKED`
- Production certification: `NOT CLAIMED`

Acceptance record:

`docs/phase-b/validation/EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md`
"""

    manifest_block = """
## Execution Admission Slice Validation Synchronization

- Bounded slice: `Execution Admission`
- Result: `EXECUTION_ADMISSION_SLICE_ACCEPTED`
- Validation: `86 PASSED / 0 FAILED`
- Full PB-DOC-009 validation: `NOT CLAIMED`
- Production certification: `NOT CLAIMED`
- G46.5/G47 reconstruction: `NOT PERFORMED`
- R097 modification: `NOT PERFORMED`
"""

    append_once(
        MASTER,
        "## Controlled Execution Admission Slice Validation Record",
        master_block,
    )

    append_once(
        EXECUTION_SPEC,
        "## Controlled Implementation-Validation Slice Record",
        execution_block,
    )

    append_once(
        MANIFEST,
        "## Execution Admission Slice Validation Synchronization",
        manifest_block,
    )

    append_once(
        DOCS_MANIFEST,
        "## Execution Admission Slice Validation Synchronization",
        manifest_block,
    )

    after_runtime = {
        str(path.relative_to(ROOT)): sha256(path)
        for path in RUNTIME
    }

    if before_runtime != after_runtime:
        raise RuntimeError(
            "Runtime source integrity changed."
        )

    if MANIFEST.read_bytes() != DOCS_MANIFEST.read_bytes():
        raise RuntimeError(
            "Project manifests diverged."
        )

    if cmd("git", "rev-parse", "HEAD") != EXPECTED_HEAD:
        raise RuntimeError("Git HEAD changed.")

    if cmd("git", "rev-parse", "origin/main") != EXPECTED_HEAD:
        raise RuntimeError("origin/main changed.")

    report = {
        "decision": "DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW",
        "timestamp_utc": timestamp,
        "head": EXPECTED_HEAD,
        "origin_main": EXPECTED_HEAD,
        "runtime_integrity": "UNCHANGED",
        "project_manifests": "BYTE_IDENTICAL",
        "production_certification": "NOT_CLAIMED",
        "g46_5_reconstruction": "NOT_PERFORMED",
        "g47_reconstruction": "NOT_PERFORMED",
        "r097_modification": "NOT_PERFORMED",
        "git_commit": "NOT_PERFORMED",
        "git_push": "NOT_PERFORMED",
        "acceptance_record": str(
            ACCEPTANCE.relative_to(ROOT)
        ),
    }

    report_path = ROOT / (
        "tools/phase_b/audit/"
        "execution_admission_documentation_sync_report.json"
    )

    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=" * 70)
    print("LYRION EXECUTION ADMISSION DOCUMENTATION SYNC")
    print("=" * 70)
    print("RESULT                 : DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW")
    print(f"HEAD                   : {EXPECTED_HEAD}")
    print("Runtime mutation       : NONE")
    print("Test mutation          : NONE")
    print("G46.5 reconstruction   : NOT PERFORMED")
    print("G47 reconstruction     : NOT PERFORMED")
    print("R097 modification      : NOT PERFORMED")
    print("Production certification: NOT CLAIMED")
    print("Git commit             : NOT PERFORMED")
    print("Git push               : NOT PERFORMED")
    print()
    print(f"Acceptance record: {ACCEPTANCE.relative_to(ROOT)}")
    print(f"Report           : {report_path.relative_to(ROOT)}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SYNC FAILURE: {exc}", file=sys.stderr)
        raise SystemExit(1)

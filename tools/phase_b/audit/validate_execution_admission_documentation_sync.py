#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path("/home/aniket/lyrion-migration-verified")

EXPECTED_HEAD = "7b1f7fd676d32194748d8ba4f603a42edb3cf4cc"

PB021_SHA = (
    "0173c17f0a0856074fe0abe72be158bbea2170ab94b4b7a29993c405f805fdf9"
)

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

SYNC_REPORT = ROOT / (
    "tools/phase_b/audit/"
    "execution_admission_documentation_sync_report.json"
)

RUNTIME = [
    ROOT / "src/lyrion/capabilities/gateway.py",
    ROOT / "src/lyrion/execution/contracts.py",
    ROOT / "src/lyrion/execution/validator.py",
    ROOT / "src/lyrion/execution/executor.py",
]


def run(*args: str) -> str:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    print("=" * 76)
    print("LYRION EXECUTION ADMISSION DOCUMENTATION POST-SYNC VALIDATION")
    print("=" * 76)

    # ------------------------------------------------------------------
    # 1. Required artifacts
    # ------------------------------------------------------------------
    required = [
        MASTER,
        EXECUTION_SPEC,
        MANIFEST,
        DOCS_MANIFEST,
        ACCEPTANCE,
        SYNC_REPORT,
    ]

    for path in required:
        require(path.is_file(), f"Missing required artifact: {path}")

    print("[PASS] Required synchronization artifacts exist")

    # ------------------------------------------------------------------
    # 2. Git baseline
    # ------------------------------------------------------------------
    head = run("git", "rev-parse", "HEAD")
    origin = run("git", "rev-parse", "origin/main")

    require(head == EXPECTED_HEAD, f"Unexpected HEAD: {head}")
    require(origin == EXPECTED_HEAD, f"Unexpected origin/main: {origin}")

    print("[PASS] HEAD == origin/main == expected baseline")

    # ------------------------------------------------------------------
    # 3. Project manifests
    # ------------------------------------------------------------------
    manifest_sha = sha256(MANIFEST)
    docs_manifest_sha = sha256(DOCS_MANIFEST)

    require(
        MANIFEST.read_bytes() == DOCS_MANIFEST.read_bytes(),
        "Manifest.md and docs/Manifest.md differ",
    )

    print("[PASS] Project manifests remain byte-identical")
    print(f"       SHA-256: {manifest_sha}")

    # ------------------------------------------------------------------
    # 4. Acceptance record semantics
    # ------------------------------------------------------------------
    acceptance = ACCEPTANCE.read_text(encoding="utf-8")

    required_acceptance_terms = [
        "EXECUTION_ADMISSION_SLICE_ACCEPTED",
        "86 passed / 0 failed",
        "CONTROLLED_VALIDATION_EVIDENCE_VERIFIED",
        "Production Certification: `NOT CLAIMED`",
        "G46.5 reconstruction: NOT PERFORMED",
        "G47 reconstruction: NOT PERFORMED",
        "R097 modification: NOT PERFORMED",
        "Git commit: NOT PERFORMED",
        "Git push: NOT PERFORMED",
        "Full PB-DOC-009 validation remains distinct",
    ]

    for term in required_acceptance_terms:
        require(
            term in acceptance,
            f"Acceptance record missing required statement: {term}",
        )

    require(PB021_SHA in acceptance, "PB-DOC-021 SHA missing")

    print("[PASS] Acceptance record semantics verified")

    # ------------------------------------------------------------------
    # 5. Master manifest semantics
    # ------------------------------------------------------------------
    master = MASTER.read_text(encoding="utf-8")

    require(
        "EXECUTION_ADMISSION_SLICE_ACCEPTED" in master,
        "Master Manifest missing bounded slice acceptance",
    )

    require(
        "86 PASSED / 0 FAILED" in master,
        "Master Manifest missing validation result",
    )

    require(
        "Full PB-DOC-009 validation: `NOT CLAIMED`" in master,
        "Master Manifest incorrectly lacks PB-DOC-009 boundary",
    )

    require(
        "Production certification: `NOT CLAIMED`" in master,
        "Master Manifest missing certification boundary",
    )

    print("[PASS] Phase-B Master Manifest bounded-slice state verified")

    # ------------------------------------------------------------------
    # 6. Execution Admission specification semantics
    # ------------------------------------------------------------------
    spec = EXECUTION_SPEC.read_text(encoding="utf-8")

    require(
        "EXECUTION_ADMISSION_SLICE_ACCEPTED" in spec,
        "Execution Admission specification missing slice state",
    )

    require(
        "86 PASSED / 0 FAILED" in spec,
        "Execution Admission specification missing validation result",
    )

    require(
        "Full PB-DOC-009 validation: `NOT CLAIMED`" in spec,
        "Execution Admission specification incorrectly lacks scope boundary",
    )

    require(
        "Production certification: `NOT CLAIMED`" in spec,
        "Execution Admission specification missing certification boundary",
    )

    print("[PASS] Execution Admission specification bounded-slice state verified")

    # ------------------------------------------------------------------
    # 7. Runtime integrity
    # ------------------------------------------------------------------
    expected_runtime_hashes = {
        "src/lyrion/capabilities/gateway.py":
            "a7ce8f4a00e54f137d559c8c13e9026e50d1b3eafbd8bc3d1029c90d35f19fa9",
        "src/lyrion/execution/contracts.py":
            "ca8af0c9e94789b7e561fc43a32e037c7c1d8aade1eaa73985f3118c7c40def2",
        "src/lyrion/execution/validator.py":
            "1a39ac52d29d2ab27bcfac9788a0aae1b0ddcc85d5ba7105790793a866ad69a8",
        "src/lyrion/execution/executor.py":
            "8c1687dda5defc35d439264ad824de92a8aa20726e144f809b330b90c26efd05",
    }

    for path in RUNTIME:
        key = str(path.relative_to(ROOT))
        actual = sha256(path)

        require(
            actual == expected_runtime_hashes[key],
            f"Runtime hash changed: {key}\n"
            f"expected={expected_runtime_hashes[key]}\n"
            f"actual={actual}",
        )

    print("[PASS] All four reviewed runtime files retain validated SHA-256")

    # ------------------------------------------------------------------
    # 8. Protected claims
    # ------------------------------------------------------------------
    protected_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            MASTER,
            EXECUTION_SPEC,
            MANIFEST,
            DOCS_MANIFEST,
            ACCEPTANCE,
        ]
    )

    forbidden = [
        "PRODUCTION CERTIFIED",
        "Production Certification: CERTIFIED",
        "Production Certification = CERTIFIED",
        "G46.5 reconstructed",
        "G47 reconstructed",
    ]

    for term in forbidden:
        require(
            term not in protected_text,
            f"Forbidden claim detected: {term}",
        )

    print("[PASS] No prohibited certification/reconstruction claims")

    # ------------------------------------------------------------------
    # 9. Synchronization report
    # ------------------------------------------------------------------
    report = SYNC_REPORT.read_text(encoding="utf-8")

    report_terms = [
        '"decision": "DOCUMENTATION_SYNC_VALIDATED_PENDING_REVIEW"',
        '"runtime_integrity": "UNCHANGED"',
        '"project_manifests": "BYTE_IDENTICAL"',
        '"production_certification": "NOT_CLAIMED"',
        '"g46_5_reconstruction": "NOT_PERFORMED"',
        '"g47_reconstruction": "NOT_PERFORMED"',
        '"r097_modification": "NOT_PERFORMED"',
        '"git_commit": "NOT_PERFORMED"',
        '"git_push": "NOT_PERFORMED"',
    ]

    for term in report_terms:
        require(term in report, f"Sync report missing: {term}")

    print("[PASS] Synchronization report verified")

    # ------------------------------------------------------------------
    # 10. Git safety
    # ------------------------------------------------------------------
    status = run("git", "status", "--short", "--untracked-files=all")

    for line in status.splitlines():
        if not line:
            continue

        path = line[3:] if len(line) >= 4 else line

        require(
            not path.startswith("src/"),
            f"Unexpected source mutation: {line}",
        )

        require(
            not path.startswith("tests/"),
            f"Unexpected test mutation: {line}",
        )

    print("[PASS] No src/ or tests/ mutation detected")

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------
    print()
    print("=" * 76)
    print("DECISION: EXECUTION_ADMISSION_DOCUMENTATION_SYNC_ACCEPTED")
    print("=" * 76)
    print("Bounded slice              : ACCEPTED")
    print("Documentation integrity    : PASS")
    print("Manifest synchronization   : PASS")
    print("Runtime integrity          : PASS")
    print("Certification claim       : NONE")
    print("G46.5/G47 reconstruction  : NONE")
    print("R097 modification         : NONE")
    print("Git commit                : NOT PERFORMED")
    print("Git push                  : NOT PERFORMED")
    print()
    print("STOP: commit/push remains a separate controlled gate.")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"VALIDATION FAILURE: {exc}", file=sys.stderr)
        raise SystemExit(1)

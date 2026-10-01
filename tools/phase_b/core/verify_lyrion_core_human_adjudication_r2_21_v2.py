#!/usr/bin/env python3
"""
LYRION Core R2.21 V2 Independent Verification Tool.

Purpose
-------
Read-only, fail-closed verification of the corrected R2.21 V2
human-adjudication reconciliation artifact and its controlled
validation record.

Security / governance properties
--------------------------------
- Read-only.
- Never creates or modifies project artifacts.
- Never records adjudications.
- Never accepts or rejects evidence.
- Never performs production validation.
- Never performs production certification.
- Never promotes evidence.
- Never changes governance state.
- Separates physical SHA-256 from canonical payload SHA-256.
- Verifies historical R2.20 provenance separately from current HEAD.
- Verifies current R2.21.1 coverage and reconciliation counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

TOOL_ID = "LYRION-CORE-R2-21-V2-INDEPENDENT-VERIFIER"
TOOL_VERSION = "1.0.0"

DEFAULT_REPOSITORY = Path(__file__).resolve().parents[3]

SOURCE_RELATIVE = Path(
    "artifacts/phase_b/core/"
    "LYRION_CORE_HUMAN_ADJUDICATION_RECONCILIATION_R2_21_V2_CORRECTED.json"
)

VALIDATION_RELATIVE = Path(
    "artifacts/phase_b/core/"
    "LYRION_CORE_HUMAN_ADJUDICATION_RECONCILIATION_R2_21_V2_CORRECTED_"
    "CONTROLLED_VALIDATION.json"
)

EXPECTED_SOURCE_PHYSICAL_SHA = (
    "dd7eb17c876b93e235192c82802532f25440311a72f73f775d1062b41f2a1971"
)

EXPECTED_SOURCE_CANONICAL_SHA = (
    "d4ca99224a46bd9ae66bc6b179c12cade4cb6622c21289ef0eb755a4730a3816"
)

EXPECTED_VALIDATION_CANONICAL_SHA = (
    "42be6e5bbcff1762b717593db4e65a7f3ccaee9a38c315b200b695f5b6cbd7f3"
)

EXPECTED_CURRENT_HEAD = (
    "281bcaf0e2077badb561fcbb1ab21e743f196654"
)

EXPECTED_R2_20_HEAD = (
    "96ef24c2ed16b9556ce5af0540d214aec7404896"
)


class VerificationError(RuntimeError):
    """Raised when a required verification condition fails."""


def sha256_file(path: Path) -> str:
    """Calculate the physical SHA-256 of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_sha(payload: dict[str, Any]) -> str:
    """
    Calculate canonical SHA-256.

    Self-referential integrity fields are excluded. The physical file
    SHA is deliberately not part of canonical payload hashing.
    """
    normalized = dict(payload)
    normalized.pop("artifact_sha256", None)
    normalized.pop("validation_record_sha256", None)

    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    """Read and structurally validate a JSON object."""
    if not path.is_file():
        raise VerificationError(f"required file missing: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"unable to read valid JSON from {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise VerificationError(f"JSON root is not an object: {path}")

    return payload


def git_head(repository: Path) -> str:
    """Read current repository HEAD without changing repository state."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(
            f"unable to determine current Git HEAD: {exc}"
        ) from exc

    return result.stdout.strip()


def require_equal(
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    """Fail closed when an expected value does not match."""
    if actual != expected:
        raise VerificationError(
            f"{label}: actual={actual!r}, expected={expected!r}"
        )


def require_true(value: Any, label: str) -> None:
    """Fail closed unless a value is exactly True."""
    if value is not True:
        raise VerificationError(
            f"{label}: expected True, actual={value!r}"
        )


def verify(repository: Path) -> dict[str, Any]:
    """Perform the complete read-only verification."""
    source_path = repository / SOURCE_RELATIVE
    validation_path = repository / VALIDATION_RELATIVE

    source = read_json(source_path)
    validation = read_json(validation_path)

    # ------------------------------------------------------------
    # Artifact physical integrity
    # ------------------------------------------------------------

    source_physical_sha = sha256_file(source_path)
    validation_physical_sha = sha256_file(validation_path)

    require_equal(
        source_physical_sha,
        EXPECTED_SOURCE_PHYSICAL_SHA,
        "source physical SHA",
    )

    # The validation record's physical SHA is reported, not compared
    # with its canonical self-hash. These are intentionally distinct.
    validation_canonical_sha = canonical_sha(validation)

    recorded_validation_canonical_sha = validation.get(
        "validation_record_sha256"
    )

    require_equal(
        recorded_validation_canonical_sha,
        validation_canonical_sha,
        "validation canonical SHA",
    )

    require_equal(
        validation_canonical_sha,
        EXPECTED_VALIDATION_CANONICAL_SHA,
        "expected validation canonical SHA",
    )

    # ------------------------------------------------------------
    # Source canonical integrity
    # ------------------------------------------------------------

    source_canonical_sha = canonical_sha(source)

    require_equal(
        source_canonical_sha,
        EXPECTED_SOURCE_CANONICAL_SHA,
        "source canonical SHA",
    )

    source_section = validation.get("source")

    if not isinstance(source_section, dict):
        raise VerificationError("validation source section missing")

    require_equal(
        source_section.get("physical_artifact_sha256"),
        source_physical_sha,
        "validation-to-source physical SHA linkage",
    )

    require_equal(
        source_section.get("canonical_artifact_sha256"),
        source_canonical_sha,
        "validation-to-source canonical SHA linkage",
    )

    require_equal(
        source_section.get("recorded_artifact_sha256"),
        source_canonical_sha,
        "recorded source artifact canonical SHA",
    )

    # ------------------------------------------------------------
    # Validation semantics
    # ------------------------------------------------------------

    require_equal(
        validation.get("validation_status"),
        "PASS",
        "validation status",
    )

    require_equal(
        validation.get("validation_mode"),
        "READ-ONLY-SOURCE-VALIDATION",
        "validation mode",
    )

    reconciliation = validation.get("reconciliation")

    if not isinstance(reconciliation, dict):
        raise VerificationError("reconciliation section missing")

    expected_reconciliation = {
        "workflow_record_count": 27,
        "historical_r2_21_decisions": 27,
        "current_r2_21_1_decisions": 1,
        "current_decision_coverage": "1/27",
        "pending_current_adjudications": 26,
        "current_conflicts": 0,
        "current_duplicates": 0,
        "unknown_workflow_ids": 0,
    }

    for key, expected in expected_reconciliation.items():
        require_equal(
            reconciliation.get(key),
            expected,
            f"reconciliation.{key}",
        )

    # ------------------------------------------------------------
    # Lineage
    # ------------------------------------------------------------

    lineage = validation.get("lineage")

    if not isinstance(lineage, dict):
        raise VerificationError("lineage section missing")

    require_equal(
        lineage.get("r2_20_historical_head"),
        EXPECTED_R2_20_HEAD,
        "R2.20 historical HEAD",
    )

    current_head = git_head(repository)

    require_equal(
        current_head,
        EXPECTED_CURRENT_HEAD,
        "current Git HEAD",
    )

    require_equal(
        lineage.get("current_repository_head"),
        current_head,
        "validation current repository HEAD",
    )

    require_true(
        lineage.get("repository_advanced_since_r2_20"),
        "repository_advanced_since_r2_20",
    )

    require_true(
        lineage.get("historical_provenance_preserved"),
        "historical_provenance_preserved",
    )

    require_equal(
        lineage.get("r2_20_002_historical_decision"),
        "DEFER",
        "R2-20-002 historical decision",
    )

    require_equal(
        lineage.get("r2_20_002_current_decision"),
        "DEFER",
        "R2-20-002 current decision",
    )

    require_true(
        lineage.get("r2_20_002_lineage_verified"),
        "R2-20-002 lineage verification",
    )

    # ------------------------------------------------------------
    # Integrity declarations
    # ------------------------------------------------------------

    integrity = validation.get("integrity_checks")

    if not isinstance(integrity, dict):
        raise VerificationError("integrity_checks section missing")

    required_integrity_flags = [
        "physical_artifact_sha256_verified",
        "canonical_artifact_sha256_verified",
        "record_count_verified",
        "historical_decision_count_verified",
        "current_decision_count_verified",
        "current_coverage_verified",
        "pending_count_verified",
        "conflict_count_verified",
        "duplicate_count_verified",
        "unknown_workflow_id_count_verified",
        "r2_20_002_lineage_verified",
        "governance_verified",
    ]

    for key in required_integrity_flags:
        require_true(
            integrity.get(key),
            f"integrity_checks.{key}",
        )

    # ------------------------------------------------------------
    # Governance boundary
    # ------------------------------------------------------------

    governance = validation.get("governance")

    if not isinstance(governance, dict):
        raise VerificationError("governance section missing")

    expected_governance = {
        "evidence_accepted": False,
        "evidence_validated_for_production": False,
        "production_certified": False,
        "promotion": False,
        "governance_changed": False,
    }

    for key, expected in expected_governance.items():
        require_equal(
            governance.get(key),
            expected,
            f"governance.{key}",
        )

    decision_boundary = validation.get("decision_boundary")

    if not isinstance(decision_boundary, dict):
        raise VerificationError("decision_boundary section missing")

    expected_boundary = {
        "human_adjudication_only": True,
        "automatic_acceptance": False,
        "automatic_rejection": False,
        "automatic_validation": False,
        "automatic_certification": False,
        "automatic_promotion": False,
    }

    for key, expected in expected_boundary.items():
        require_equal(
            decision_boundary.get(key),
            expected,
            f"decision_boundary.{key}",
        )

    return {
        "tool_id": TOOL_ID,
        "tool_version": TOOL_VERSION,
        "source": str(source_path.relative_to(repository)),
        "validation_record": str(
            validation_path.relative_to(repository)
        ),
        "source_physical_sha256": source_physical_sha,
        "source_canonical_sha256": source_canonical_sha,
        "validation_physical_sha256": validation_physical_sha,
        "validation_canonical_sha256": validation_canonical_sha,
        "current_head": current_head,
        "historical_r2_20_head": EXPECTED_R2_20_HEAD,
        "workflow_record_count": 27,
        "historical_r2_21_decisions": 27,
        "current_r2_21_1_decisions": 1,
        "current_decision_coverage": "1/27",
        "pending_current_adjudications": 26,
        "current_conflicts": 0,
        "current_duplicates": 0,
        "unknown_workflow_ids": 0,
        "evidence_accepted": False,
        "evidence_validated_for_production": False,
        "production_certified": False,
        "promotion": False,
        "governance_changed": False,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Read-only independent verification of the corrected "
            "LYRION Core R2.21 V2 reconciliation."
        )
    )

    parser.add_argument(
        "--repository",
        type=Path,
        default=DEFAULT_REPOSITORY,
        help="LYRION repository root.",
    )

    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()

    print("=== LYRION CORE R2.21 V2 INDEPENDENT VERIFIER ===")
    print(f"Tool       : {TOOL_ID}")
    print(f"Version    : {TOOL_VERSION}")
    print("Mode       : READ-ONLY")
    print("Adjudicate : NO")
    print("Promote    : NO")
    print("Modify     : NO")
    print()

    try:
        result = verify(args.repository.resolve())
    except VerificationError as exc:
        print(f"FAIL: {exc}")
        return 1

    print("Artifact existence            : PASS")
    print("Source physical SHA           : PASS")
    print("Source canonical SHA          : PASS")
    print("Validation canonical SHA      : PASS")
    print("Source-to-validation linkage  : PASS")
    print("Reconciliation semantics      : PASS")
    print("Historical provenance         : PASS")
    print("Current Git provenance        : PASS")
    print("R2-20-002 lineage             : PASS")
    print("Integrity declarations        : PASS")
    print("Governance boundary           : PASS")
    print("Decision boundary             : PASS")
    print()
    print("Source physical SHA           :", result["source_physical_sha256"])
    print("Source canonical SHA          :", result["source_canonical_sha256"])
    print(
        "Validation physical SHA      :",
        result["validation_physical_sha256"],
    )
    print(
        "Validation canonical SHA     :",
        result["validation_canonical_sha256"],
    )
    print()
    print("Workflow records              : 27")
    print("Historical R2.21 decisions    : 27")
    print("Current R2.21.1 decisions     : 1")
    print("Current coverage              : 1/27")
    print("Pending current decisions     : 26")
    print("Current conflicts             : 0")
    print("Current duplicates            : 0")
    print("Unknown workflow IDs          : 0")
    print()
    print("Evidence accepted             : NO")
    print("Evidence validated            : NO")
    print("Production certified          : NO")
    print("Promotion                     : NO")
    print("Governance changed            : NO")
    print()
    print("=== INDEPENDENT VERIFICATION: PASS ===")
    print("No files modified.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

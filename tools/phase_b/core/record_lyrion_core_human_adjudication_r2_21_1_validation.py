#!/usr/bin/env python3
"""
LYRION True Agentic OS
R2.21.1 Controlled Validation Record Generator

Purpose
-------
Create a separate, immutable validation record documenting a successful
read-only controlled verification of the existing R2.21.1 human-adjudication
artifact.

Safety / Governance Boundary
----------------------------
This tool:

- DOES NOT modify R2.20.
- DOES NOT modify R2.21.
- DOES NOT modify the R2.21.1 adjudication artifact.
- DOES NOT create or modify an adjudication.
- DOES NOT accept or reject evidence.
- DOES NOT validate production readiness.
- DOES NOT certify production.
- DOES NOT promote evidence.
- DOES NOT alter governance state.
- FAILS CLOSED unless the controlled verification passes.

The generated validation record is a separate governance/evidence artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]

VERIFY_TOOL = (
    REPOSITORY
    / "tools"
    / "phase_b"
    / "core"
    / "verify_lyrion_core_human_adjudication_r2_21_1_controlled.py"
)

ARTIFACT_DIR = REPOSITORY / "artifacts" / "phase_b" / "core"

WORKFLOW_RECORD_ID = "R2-20-002"
REQUIREMENT_ID = "CORE-003"
EVIDENCE_TYPE = "IMPLEMENTATION"
DECISION = "DEFER"
REVIEWER = "Aniket Pawar"
REVIEW_REFERENCE = "LYRION-R2-HUMAN-ADJ-002"

SCHEMA_VERSION = "1.0.0"
RECORD_VERSION = "1.0.0"
TOOL_ID = "LYRION-R2.21.1-VALIDATION-RECORDER"

EXPECTED_GOVERNANCE = {
    "architecture_approval": "APPROVED",
    "documentation_freeze": "NOT AUTHORIZED",
    "implementation_authorization": "AUTHORIZED",
    "production_certification": "NOT CLAIMED",
    "production_implementation": "BLOCKED",
    "self_awareness_family": "FUTURE-RESERVED",
    "self_evolution": "HELD",
    "self_learning": "HELD",
}

EXPECTED_PROVENANCE = ["R2.13"]


class ValidationFailure(RuntimeError):
    """Raised when fail-closed validation cannot be established."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ValidationFailure(f"Required file does not exist: {path}")
    return sha256_bytes(path.read_bytes())


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    )


def canonical_payload_sha256(payload: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(payload))


def run_command(
    args: list[str],
    *,
    cwd: Path = REPOSITORY,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def git_output(*args: str) -> str:
    result = run_command(["git", *args])
    if result.returncode != 0:
        raise ValidationFailure(
            f"Git command failed: git {' '.join(args)}\n"
            f"stdout={result.stdout.strip()}\n"
            f"stderr={result.stderr.strip()}"
        )
    return result.stdout.strip()


def current_head() -> str:
    return git_output("rev-parse", "HEAD")


def current_repository() -> str:
    return git_output("rev-parse", "--show-toplevel")


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationFailure(f"Required JSON file does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationFailure(
            f"Invalid JSON in {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValidationFailure(f"Expected JSON object in {path}")

    return payload


def locate_r2_21_1_artifact() -> Path:
    matches = sorted(
        ARTIFACT_DIR.glob(
            "LYRION_CORE_HUMAN_ADJUDICATION_DECISION_R2_21_1_"
            "R2-20-002_*.json"
        )
    )

    if len(matches) != 1:
        raise ValidationFailure(
            "Expected exactly one immutable R2.21.1 artifact for "
            f"{WORKFLOW_RECORD_ID}; found {len(matches)}."
        )

    return matches[0]


def verify_artifact_schema(artifact: dict[str, Any]) -> None:
    required_top_level = {
        "artifact_sha256",
        "decision",
        "decision_policy",
        "decision_record",
        "document_id",
        "future_reserved",
        "git",
        "governance",
        "promotion_boundary",
        "record_version",
        "schema_version",
        "source",
        "tool_id",
    }

    missing = sorted(required_top_level - set(artifact))
    if missing:
        raise ValidationFailure(
            f"R2.21.1 artifact missing required top-level fields: {missing}"
        )

    decision_record = artifact["decision_record"]
    if not isinstance(decision_record, dict):
        raise ValidationFailure("decision_record must be an object")

    required_record = {
        "authority",
        "classification",
        "decision",
        "decision_reason",
        "decision_timestamp",
        "evidence_type",
        "path",
        "promotion_eligible",
        "provenance",
        "rationale",
        "requirement_id",
        "review_reference",
        "reviewer",
        "source_sha256",
        "workflow_record_id",
    }

    missing_record = sorted(required_record - set(decision_record))
    if missing_record:
        raise ValidationFailure(
            f"decision_record missing required fields: {missing_record}"
        )

    if decision_record["workflow_record_id"] != WORKFLOW_RECORD_ID:
        raise ValidationFailure("Unexpected workflow_record_id")

    if decision_record["requirement_id"] != REQUIREMENT_ID:
        raise ValidationFailure("Unexpected requirement_id")

    if decision_record["evidence_type"] != EVIDENCE_TYPE:
        raise ValidationFailure("Unexpected evidence_type")

    if decision_record["decision"] != DECISION:
        raise ValidationFailure("Unexpected adjudication decision")

    if decision_record["reviewer"] != REVIEWER:
        raise ValidationFailure("Unexpected reviewer")

    if decision_record["review_reference"] != REVIEW_REFERENCE:
        raise ValidationFailure("Unexpected review reference")

    if decision_record["provenance"] != EXPECTED_PROVENANCE:
        raise ValidationFailure("Unexpected evidence provenance")

    if decision_record["promotion_eligible"] is not False:
        raise ValidationFailure("Promotion eligibility must remain false")

    if artifact["decision"] != "IMMUTABLE-HUMAN-ADJUDICATION-RECORD":
        raise ValidationFailure("Unexpected top-level artifact decision")

    if decision_record["decision"] != DECISION:
        raise ValidationFailure("Unexpected decision_record decision")


def verify_canonical_artifact_hash(
    artifact: dict[str, Any],
) -> str:
    recorded_hash = artifact.get("artifact_sha256")
    if not isinstance(recorded_hash, str) or not recorded_hash:
        raise ValidationFailure("Missing artifact_sha256")

    canonical_payload = dict(artifact)
    canonical_payload.pop("artifact_sha256", None)

    calculated_hash = canonical_payload_sha256(canonical_payload)

    if calculated_hash != recorded_hash:
        raise ValidationFailure(
            "Canonical artifact SHA-256 mismatch: "
            f"recorded={recorded_hash} calculated={calculated_hash}"
        )

    return calculated_hash


def verify_governance(artifact: dict[str, Any]) -> None:
    governance = artifact["governance"]

    if not isinstance(governance, dict):
        raise ValidationFailure("governance must be an object")

    for key, expected in EXPECTED_GOVERNANCE.items():
        actual = governance.get(key)
        if actual != expected:
            raise ValidationFailure(
                f"Governance mismatch for {key}: "
                f"expected={expected!r} actual={actual!r}"
            )


def verify_promotion_boundary(artifact: dict[str, Any]) -> None:
    boundary = artifact["promotion_boundary"]

    if not isinstance(boundary, dict):
        raise ValidationFailure("promotion_boundary must be an object")

    forbidden_true_values = {
        "accepted",
        "validated",
        "certified",
        "promoted",
    }

    for key in forbidden_true_values:
        if boundary.get(key) is not False:
            raise ValidationFailure(
                f"Promotion boundary violation: {key} must be false"
            )


def verify_git_provenance(artifact: dict[str, Any]) -> dict[str, Any]:
    git_data = artifact["git"]

    if not isinstance(git_data, dict):
        raise ValidationFailure("git provenance must be an object")

    governed_head = git_data.get("governed_r2_20_head")
    head = git_data.get("head")
    head_match = git_data.get("head_match")

    actual_repository = current_repository()
    actual_head = current_head()

    if governed_head != head:
        raise ValidationFailure(
            "Artifact Git provenance governed_r2_20_head/head mismatch: "
            f"governed={governed_head!r} head={head!r}"
        )

    if head != actual_head:
        raise ValidationFailure(
            "Artifact Git provenance does not match current HEAD: "
            f"artifact={head} current={actual_head}"
        )

    if head_match is not True:
        raise ValidationFailure("Artifact Git head_match must be true")

    return {
        "repository": actual_repository,
        "governed_r2_20_head": governed_head,
        "head": head,
        "head_match": True,
    }


def run_controlled_verification() -> dict[str, Any]:
    result = run_command(
        [sys.executable, str(VERIFY_TOOL)],
    )

    combined = f"{result.stdout}{result.stderr}"

    if result.returncode != 0:
        raise ValidationFailure(
            "Controlled R2.21.1 verification failed.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    if "=== CONTROLLED VERIFICATION: PASS ===" not in combined:
        raise ValidationFailure(
            "Controlled verification exited successfully but did not "
            "emit the required PASS marker."
        )

    required_markers = [
        "R2.20 modified        : NO",
        "R2.21 modified        : NO",
        "R2.21.1 artifact      : VERIFIED",
        "Canonical SHA-256     : VERIFIED",
        "Duplicate protection  : VERIFIED",
        "Evidence validated    : NO",
        "Evidence accepted     : NO",
        "Production certified  : NO",
        "Promotion             : NO",
        "Artifact created      : NO",
    ]

    missing = [
        marker for marker in required_markers if marker not in combined
    ]

    if missing:
        raise ValidationFailure(
            "Controlled verification PASS output is incomplete; "
            f"missing markers: {missing}"
        )

    return {
        "returncode": result.returncode,
        "pass_marker": True,
        "required_markers_verified": True,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def build_validation_payload(
    *,
    artifact_path: Path,
    physical_artifact_sha: str,
    canonical_payload_sha: str,
    controlled_verification: dict[str, Any],
    git_provenance: dict[str, Any],
) -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()

    return {
        "document_id": "LYRION-R2.21.1-CONTROLLED-VALIDATION-001",
        "schema_version": SCHEMA_VERSION,
        "record_version": RECORD_VERSION,
        "tool_id": TOOL_ID,
        "validation_timestamp": timestamp,
        "validation_status": "PASS",
        "validation_scope": "CONTROLLED-READ-ONLY-VERIFICATION",
        "purpose": (
            "Record the successful controlled verification of the immutable "
            "R2.21.1 human-adjudication artifact."
        ),
        "source": {
            "workflow_record_id": WORKFLOW_RECORD_ID,
            "requirement_id": REQUIREMENT_ID,
            "evidence_type": EVIDENCE_TYPE,
            "decision": DECISION,
            "reviewer": REVIEWER,
            "review_reference": REVIEW_REFERENCE,
            "provenance": EXPECTED_PROVENANCE,
            "artifact_path": str(artifact_path.relative_to(REPOSITORY)),
            "physical_artifact_sha256": physical_artifact_sha,
            "canonical_payload_sha256": canonical_payload_sha,
        },
        "controlled_verification": {
            "tool": str(VERIFY_TOOL.relative_to(REPOSITORY)),
            "mode": "READ-ONLY",
            "adjudicate": False,
            "promote": False,
            "result": "PASS",
            "required_markers_verified": controlled_verification[
                "required_markers_verified"
            ],
        },
        "governance": dict(EXPECTED_GOVERNANCE),
        "promotion_boundary": {
            "accepted": False,
            "validated": False,
            "certified": False,
            "promoted": False,
        },
        "git": git_provenance,
        "non_claims": [
            "Evidence acceptance is not claimed.",
            "Production validation is not claimed.",
            "Production certification is not claimed.",
            "Evidence promotion is not claimed.",
            "Implementation completion is not claimed.",
            "No governance state was changed by this record.",
        ],
    }


def write_immutable_validation_record(
    payload: dict[str, Any],
    *,
    timestamp: str,
) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    payload_without_hash = dict(payload)
    record_sha = canonical_payload_sha256(payload_without_hash)

    final_payload = dict(payload_without_hash)
    final_payload["record_sha256"] = record_sha

    safe_timestamp = (
        timestamp.replace("-", "")
        .replace(":", "")
        .replace("+00:00", "Z")
        .replace(".", "")
    )

    output = (
        ARTIFACT_DIR
        / "LYRION_CORE_HUMAN_ADJUDICATION_R2_21_1_"
        f"CONTROLLED_VALIDATION_{safe_timestamp}.json"
    )

    if output.exists():
        raise ValidationFailure(
            f"Refusing to overwrite existing validation record: {output}"
        )

    output.write_text(
        json.dumps(
            final_payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    reloaded = load_json(output)
    recorded_hash = reloaded.get("record_sha256")
    canonical = dict(reloaded)
    canonical.pop("record_sha256", None)
    recalculated = canonical_payload_sha256(canonical)

    if recorded_hash != recalculated:
        output.unlink(missing_ok=True)
        raise ValidationFailure(
            "Post-write validation-record SHA-256 verification failed."
        )

    return output


def perform_validation() -> Path:
    if not VERIFY_TOOL.is_file():
        raise ValidationFailure(
            f"Controlled verification tool missing: {VERIFY_TOOL}"
        )

    artifact_path = locate_r2_21_1_artifact()
    artifact = load_json(artifact_path)

    verify_artifact_schema(artifact)
    canonical_payload_sha = verify_canonical_artifact_hash(artifact)
    physical_artifact_sha = sha256_file(artifact_path)
    verify_governance(artifact)
    verify_promotion_boundary(artifact)

    git_provenance = verify_git_provenance(artifact)
    controlled_verification = run_controlled_verification()

    timestamp = datetime.now(UTC).isoformat()

    payload = build_validation_payload(
        artifact_path=artifact_path,
        physical_artifact_sha=physical_artifact_sha,
        canonical_payload_sha=canonical_payload_sha,
        controlled_verification=controlled_verification,
        git_provenance=git_provenance,
    )

    output = write_immutable_validation_record(
        payload,
        timestamp=timestamp,
    )

    return output


def self_test() -> None:
    sample = {
        "b": 2,
        "a": 1,
    }

    first = canonical_payload_sha256(sample)
    second = canonical_payload_sha256(
        {
            "a": 1,
            "b": 2,
        }
    )

    if first != second:
        raise ValidationFailure(
            "Canonical JSON hashing is not deterministic."
        )

    if len(first) != 64:
        raise ValidationFailure(
            "SHA-256 output length is invalid."
        )

    print("SELF-TEST: PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a fail-closed validation record for the already-verified "
            "LYRION R2.21.1 human-adjudication artifact."
        )
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic internal self-tests only.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.self_test:
            self_test()
            return 0

        output = perform_validation()

        print("=== LYRION CORE R2.21.1 VALIDATION RECORD ===")
        print()
        print("Mode                  : READ-ONLY SOURCE VERIFICATION")
        print("Controlled verification: PASS")
        print("Validation record     : CREATED")
        print(f"Validation artifact   : {output}")
        print()
        print("Evidence accepted     : NO")
        print("Production certified  : NO")
        print("Promotion             : NO")
        print("Governance changed    : NO")
        print()
        print("=== VALIDATION RECORD: PASS ===")

        return 0

    except ValidationFailure as exc:
        print("=== VALIDATION RECORD: FAIL ===", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

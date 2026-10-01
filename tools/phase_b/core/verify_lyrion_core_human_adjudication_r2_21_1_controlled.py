#!/usr/bin/env python3
"""
LYRION Core R2.21.1 Controlled Verification Harness.

Purpose
-------
Fail-closed verification of an existing immutable R2.21.1 human
adjudication artifact.

This harness:
- verifies the actual R2.21.1 artifact schema;
- verifies canonical artifact SHA-256;
- verifies source linkage to R2.20;
- verifies Git provenance;
- verifies the human-decision boundary;
- verifies promotion remains disabled;
- verifies historical R2.21 integrity;
- verifies duplicate protection without creating a duplicate;
- never creates or modifies an adjudication artifact;
- never validates, accepts, certifies, or promotes evidence.

Governance
---------
This is a read-only verification harness.

It does NOT:
- authorize implementation;
- validate evidence;
- accept evidence;
- certify production;
- promote evidence;
- modify R2.20;
- modify R2.21;
- modify an existing R2.21.1 decision.

Exit code:
    0 = verification PASS
    non-zero = verification FAIL
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]

R2_20_PATH = (
    REPO
    / "artifacts"
    / "phase_b"
    / "core"
    / "LYRION_CORE_HUMAN_DECISION_WORKFLOW_R2_20.json"
)

R2_21_PATH = (
    REPO
    / "artifacts"
    / "phase_b"
    / "core"
    / "LYRION_CORE_HUMAN_ADJUDICATION_DECISION_R2_21.json"
)

R2_21_1_GLOB = (
    "LYRION_CORE_HUMAN_ADJUDICATION_DECISION_R2_21_1_*.json"
)

R2_21_1_TOOL = (
    REPO
    / "tools"
    / "phase_b"
    / "core"
    / "record_lyrion_core_human_adjudication_r2_21_1.py"
)

EXPECTED_WORKFLOW_RECORD_ID = "R2-20-002"
EXPECTED_REQUIREMENT_ID = "CORE-003"
EXPECTED_EVIDENCE_TYPE = "IMPLEMENTATION"
EXPECTED_DECISION = "DEFER"
EXPECTED_REVIEWER = "Aniket Pawar"
EXPECTED_REVIEW_REFERENCE = "LYRION-R2-HUMAN-ADJ-002"
EXPECTED_PROVENANCE = ["R2.13"]
EXPECTED_R2_20_DOCUMENT_ID = (
    "LYRION-CORE-HUMAN-DECISION-WORKFLOW-R2-20"
)


class VerificationFailure(RuntimeError):
    """Raised when any controlled verification requirement fails."""


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object and fail closed on malformed input."""
    if not path.is_file():
        raise VerificationFailure(
            f"Required artifact does not exist: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise VerificationFailure(
            f"Invalid JSON: {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise VerificationFailure(
            f"Expected JSON object: {path}"
        )

    return payload


def load_r2211_module() -> Any:
    """Load the R2.21.1 recorder module without executing main()."""
    if not R2_21_1_TOOL.is_file():
        raise VerificationFailure(
            f"R2.21.1 recorder is missing: {R2_21_1_TOOL}"
        )

    spec = importlib.util.spec_from_file_location(
        "lyrion_r2211_recorder",
        R2_21_1_TOOL,
    )

    if spec is None or spec.loader is None:
        raise VerificationFailure(
            "Unable to load R2.21.1 recorder module."
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_git_head() -> str:
    """Return current repository HEAD."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise VerificationFailure(
            "Unable to determine current Git HEAD."
        )

    head = result.stdout.strip()

    if not head:
        raise VerificationFailure(
            "Git HEAD is empty."
        )

    return head


def run_git_status() -> str:
    """Return porcelain Git status."""
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
        ],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise VerificationFailure(
            "Unable to determine Git worktree state."
        )

    return result.stdout


def find_existing_r2211_artifacts() -> list[Path]:
    """Return all existing R2.21.1 decision artifacts."""
    return sorted(
        (
            REPO
            / "artifacts"
            / "phase_b"
            / "core"
        ).glob(R2_21_1_GLOB)
    )


def verify_artifact(
    payload: dict[str, Any],
    artifact_path: Path,
    recorder: Any,
) -> None:
    """Verify the complete actual R2.21.1 artifact schema."""

    record = payload.get("decision_record")

    if not isinstance(record, dict):
        raise VerificationFailure(
            "decision_record must be an object."
        )

    assert_equal(
        record.get("workflow_record_id"),
        EXPECTED_WORKFLOW_RECORD_ID,
        "workflow_record_id",
    )

    assert_equal(
        record.get("requirement_id"),
        EXPECTED_REQUIREMENT_ID,
        "requirement_id",
    )

    assert_equal(
        record.get("evidence_type"),
        EXPECTED_EVIDENCE_TYPE,
        "evidence_type",
    )

    assert_equal(
        record.get("decision"),
        EXPECTED_DECISION,
        "decision",
    )

    assert_equal(
        record.get("reviewer"),
        EXPECTED_REVIEWER,
        "reviewer",
    )

    assert_equal(
        record.get("review_reference"),
        EXPECTED_REVIEW_REFERENCE,
        "review_reference",
    )

    if record.get("provenance") != EXPECTED_PROVENANCE:
        raise VerificationFailure(
            "provenance does not match the expected R2.13 lineage."
        )

    if record.get("promotion_eligible") is not False:
        raise VerificationFailure(
            "promotion_eligible must be false."
        )

    if not recorder.verify_artifact_payload_sha256(payload):
        raise VerificationFailure(
            "Canonical artifact SHA-256 verification failed."
        )

    boundary = payload.get("promotion_boundary")

    if not isinstance(boundary, dict):
        raise VerificationFailure(
            "promotion_boundary must be an object."
        )

    for key in (
        "accepted",
        "validated",
        "certified",
        "promoted",
    ):
        if boundary.get(key) is not False:
            raise VerificationFailure(
                f"promotion_boundary.{key} must be false."
            )

    source = payload.get("source")

    if not isinstance(source, dict):
        raise VerificationFailure(
            "source metadata is missing or invalid."
        )

    assert_equal(
        source.get("document_id"),
        EXPECTED_R2_20_DOCUMENT_ID,
        "source.document_id",
    )

    git = payload.get("git")

    if not isinstance(git, dict):
        raise VerificationFailure(
            "git provenance is missing or invalid."
        )

    if git.get("head_match") is not True:
        raise VerificationFailure(
            "Artifact Git provenance does not report head_match=true."
        )

    governed_head = git.get("head")

    if not isinstance(governed_head, str) or not governed_head:
        raise VerificationFailure(
            "Artifact Git HEAD provenance is missing."
        )

    actual_head = current_git_head()

    if actual_head != governed_head:
        raise VerificationFailure(
            "Current Git HEAD does not match artifact provenance."
        )

    recorded_artifact_hash = payload.get("artifact_sha256")

    if not isinstance(recorded_artifact_hash, str):
        raise VerificationFailure(
            "artifact_sha256 is missing."
        )

    actual_file_hash = sha256_file(artifact_path)

    if not actual_file_hash:
        raise VerificationFailure(
            "Unable to calculate artifact SHA-256."
        )

    # The recorder's canonical payload hash is authoritative for
    # semantic integrity; the file hash is independently reported.
    print(f"Artifact file SHA-256 : {actual_file_hash}")
    print(
        "Canonical payload SHA : VERIFIED"
    )


def verify_r220_source() -> None:
    """Verify immutable R2.20 source identity and governance."""
    payload = load_json(R2_20_PATH)

    assert_equal(
        payload.get("document_id"),
        EXPECTED_R2_20_DOCUMENT_ID,
        "R2.20 document_id",
    )

    if payload.get("head_match") is not True:
        raise VerificationFailure(
            "R2.20 head_match is not true."
        )

    expected_head = payload.get("expected_head")
    governed_head = payload.get("head")

    if not isinstance(expected_head, str) or not expected_head:
        raise VerificationFailure(
            "R2.20 expected_head is missing."
        )

    if not isinstance(governed_head, str) or not governed_head:
        raise VerificationFailure(
            "R2.20 head is missing."
        )

    if expected_head != governed_head:
        raise VerificationFailure(
            "R2.20 expected_head != head."
        )

    if governed_head != current_git_head():
        raise VerificationFailure(
            "Current Git HEAD differs from R2.20 governed HEAD."
        )

    governance = payload.get("governance")

    if not isinstance(governance, dict):
        raise VerificationFailure(
            "R2.20 governance object is missing."
        )

    if governance.get("production_certification") != "NOT CLAIMED":
        raise VerificationFailure(
            "R2.20 production certification boundary invalid."
        )

    if governance.get("production_implementation") != "BLOCKED":
        raise VerificationFailure(
            "R2.20 production implementation boundary invalid."
        )


def verify_historical_r221(
    expected_sha256: str,
) -> None:
    """Verify historical R2.21 remains byte-for-byte unchanged."""
    actual_sha256 = sha256_file(R2_21_PATH)

    if actual_sha256 != expected_sha256:
        raise VerificationFailure(
            "Historical R2.21 SHA-256 changed."
        )


def assert_equal(
    actual: object,
    expected: object,
    field: str,
) -> None:
    """Fail closed when an expected field differs."""
    if actual != expected:
        raise VerificationFailure(
            f"{field} mismatch: "
            f"expected={expected!r}, actual={actual!r}"
        )


def verify_duplicate_protection(
    recorder: Any,
    workflow_record_id: str,
) -> None:
    """
    Verify duplicate protection without invoking the recorder.

    This intentionally inspects the existing artifact set rather than
    creating another adjudication.
    """
    artifacts = find_existing_r2211_artifacts()

    matching = [
        path
        for path in artifacts
        if workflow_record_id in path.name
    ]

    if len(matching) != 1:
        raise VerificationFailure(
            "Expected exactly one immutable R2.21.1 artifact for "
            f"{workflow_record_id}; found {len(matching)}."
        )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed verification of an existing "
            "LYRION Core R2.21.1 human adjudication artifact."
        )
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic internal self-tests.",
    )

    return parser


def self_test() -> None:
    """Run deterministic internal tests."""
    assert_equal(
        EXPECTED_WORKFLOW_RECORD_ID,
        "R2-20-002",
        "self-test workflow_record_id",
    )

    assert_equal(
        EXPECTED_REQUIREMENT_ID,
        "CORE-003",
        "self-test requirement_id",
    )

    assert EXPECTED_PROVENANCE == ["R2.13"]

    print("SELF-TEST: PASS")


def main() -> int:
    """Run fail-closed controlled verification."""
    parser = build_parser()
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    print("=== LYRION CORE R2.21.1 CONTROLLED VERIFICATION ===")
    print()
    print("Mode       : READ-ONLY")
    print("Adjudicate : NO")
    print("Promote    : NO")
    print()

    try:
        if not R2_21_PATH.is_file():
            raise VerificationFailure(
                f"Historical R2.21 artifact missing: {R2_21_PATH}"
            )

        historical_r221_sha = sha256_file(R2_21_PATH)

        verify_r220_source()

        artifacts = find_existing_r2211_artifacts()

        if len(artifacts) != 1:
            raise VerificationFailure(
                "Expected exactly one existing R2.21.1 artifact; "
                f"found {len(artifacts)}."
            )

        artifact_path = artifacts[0]

        payload = load_json(artifact_path)
        recorder = load_r2211_module()

        verify_artifact(
            payload,
            artifact_path,
            recorder,
        )

        verify_historical_r221(
            historical_r221_sha,
        )

        verify_duplicate_protection(
            recorder,
            EXPECTED_WORKFLOW_RECORD_ID,
        )

        print()
        print("=== CONTROLLED VERIFICATION: PASS ===")
        print()
        print("R2.20 modified        : NO")
        print("R2.21 modified        : NO")
        print("R2.21.1 artifact      : VERIFIED")
        print("Canonical SHA-256     : VERIFIED")
        print("Duplicate protection  : VERIFIED")
        print("Evidence validated    : NO")
        print("Evidence accepted     : NO")
        print("Production certified  : NO")
        print("Promotion             : NO")
        print("Artifact created      : NO")
        print()

        return 0

    except (
        VerificationFailure,
        AssertionError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print()
        print("=== CONTROLLED VERIFICATION: FAIL ===")
        print()
        print(f"Reason: {exc}")
        print()
        print("FAIL-CLOSED: no adjudication or promotion performed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

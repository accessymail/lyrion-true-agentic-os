#!/usr/bin/env python3
"""
LYRION True Agentic OS
R2.21 Human Adjudication Reconciliation

Purpose
-------
Perform a deterministic, read-only reconciliation between:

1. The immutable R2.20 human-decision workflow.
2. Historical R2.21 adjudication artifacts.
3. Immutable R2.21.1 per-record adjudication artifacts.

This tool DOES NOT:
- create human decisions;
- modify existing decisions;
- accept or reject evidence;
- validate production readiness;
- certify production;
- promote evidence;
- modify governance state;
- modify source documentation;
- modify R2.20/R2.21/R2.21.1 artifacts.

It produces a reconciliation artifact describing the current
decision coverage and integrity state.

Security / Governance Boundary
------------------------------
Observation != Opportunity != Reasoning != Decision != Agency
!= Authority != Capability != Execution != Verification

Human adjudication remains exclusively human-authorized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOOL_ID = "LYRION-CORE-HUMAN-ADJUDICATION-RECONCILIATION-R2-21-V2"
SCHEMA_VERSION = "1.0.0"
DOCUMENT_ID = "LYRION-CORE-HUMAN-ADJUDICATION-RECONCILIATION-R2-21-V2"

REPOSITORY = Path("/home/aniket/lyrion-migration-verified")
ARTIFACT_DIR = REPOSITORY / "artifacts" / "phase_b" / "core"

WORKFLOW_PATH = (
    ARTIFACT_DIR / "LYRION_CORE_HUMAN_DECISION_WORKFLOW_R2_20.json"
)

HISTORICAL_R2_21_PATH = (
    ARTIFACT_DIR / "LYRION_CORE_HUMAN_ADJUDICATION_DECISION_R2_21.json"
)

OUTPUT_PATH = (
    ARTIFACT_DIR / "LYRION_CORE_HUMAN_ADJUDICATION_RECONCILIATION_R2_21_V2_CORRECTED.json"
)

ALLOWED_DECISIONS = {"ACCEPT", "REJECT", "DEFER"}


class ReconciliationError(RuntimeError):
    """Raised when controlled reconciliation cannot proceed safely."""


@dataclass(frozen=True)
class WorkflowRecord:
    workflow_record_id: str
    adjudication_id: str
    requirement_id: str
    path: str
    evidence_type: str
    workflow_decision: str


@dataclass(frozen=True)
class DecisionObservation:
    source_file: str
    source_kind: str
    workflow_record_id: str
    decision: str
    reviewer: str | None
    review_reference: str | None
    source_sha256: str | None
    artifact_sha256: str | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def canonical_json_sha256(payload: dict[str, Any]) -> str:
    normalized = dict(payload)
    normalized.pop("artifact_sha256", None)
    normalized.pop("record_sha256", None)

    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ReconciliationError(f"Required artifact missing: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReconciliationError(
            f"Invalid JSON artifact: {path}: {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise ReconciliationError(
            f"Artifact root must be a JSON object: {path}"
        )

    return payload


def git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY,
        check=True,
        capture_output=True,
        text=True,
    )

    head = result.stdout.strip()

    if not head:
        raise ReconciliationError("Unable to determine Git HEAD.")

    return head


def load_workflow() -> tuple[dict[str, Any], list[WorkflowRecord]]:
    payload = read_json(WORKFLOW_PATH)

    required = {
        "document_id",
        "record_count",
        "records",
        "governance",
        "expected_head",
        "head",
        "head_match",
    }

    missing = sorted(required - payload.keys())

    if missing:
        raise ReconciliationError(
            f"R2.20 missing required fields: {', '.join(missing)}"
        )

    records = payload["records"]

    if not isinstance(records, list):
        raise ReconciliationError("R2.20 records must be a list.")

    workflow_records: list[WorkflowRecord] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ReconciliationError(
                f"R2.20 record {index} is not an object."
            )

        required_record_fields = {
            "workflow_record_id",
            "adjudication_id",
            "requirement_id",
            "path",
            "evidence_type",
            "decision",
        }

        missing_record_fields = sorted(
            required_record_fields - record.keys()
        )

        if missing_record_fields:
            raise ReconciliationError(
                f"R2.20 record {index} missing: "
                f"{', '.join(missing_record_fields)}"
            )

        workflow_id = str(record["workflow_record_id"])

        if workflow_id in seen_ids:
            raise ReconciliationError(
                f"Duplicate R2.20 workflow_record_id: {workflow_id}"
            )

        seen_ids.add(workflow_id)

        workflow_records.append(
            WorkflowRecord(
                workflow_record_id=workflow_id,
                adjudication_id=str(record["adjudication_id"]),
                requirement_id=str(record["requirement_id"]),
                path=str(record["path"]),
                evidence_type=str(record["evidence_type"]),
                workflow_decision=str(record["decision"]),
            )
        )

    if payload["record_count"] != len(workflow_records):
        raise ReconciliationError(
            "R2.20 record_count does not match actual record count."
        )

    if len(workflow_records) != 27:
        raise ReconciliationError(
            f"Unexpected R2.20 workflow record count: "
            f"{len(workflow_records)}; expected 27."
        )

    return payload, workflow_records


def validate_r2_20_git(
    workflow: dict[str, Any],
    current_head: str,
) -> dict[str, Any]:
    expected_head = str(workflow["expected_head"])
    recorded_head = str(workflow["head"])
    head_match = workflow["head_match"]

    if expected_head != recorded_head:
        raise ReconciliationError(
            "R2.20 expected_head != recorded head."
        )

    if head_match is not True:
        raise ReconciliationError(
            "R2.20 head_match is not True."
        )

    if len(expected_head) != 40:
        raise ReconciliationError(
            "R2.20 expected_head is not a valid full Git SHA-1."
        )

    if len(recorded_head) != 40:
        raise ReconciliationError(
            "R2.20 recorded head is not a valid full Git SHA-1."
        )

    return {
        "r2_20_expected_head": expected_head,
        "r2_20_recorded_head": recorded_head,
        "r2_20_internal_provenance_match": True,
        "current_repository_head": current_head,
        "repository_advanced_since_r2_20": (
            current_head != recorded_head
        ),
    }


def extract_historical_r2_21(
    payload: dict[str, Any],
) -> list[DecisionObservation]:
    """
    R2.21 is the historical multi-record artifact.

    Its schema is intentionally treated separately from R2.21.1.
    """

    required = {
        "decision",
        "records",
        "selected_record",
        "governance",
        "expected_head",
        "head",
        "head_match",
    }

    missing = sorted(required - payload.keys())

    if missing:
        raise ReconciliationError(
            "R2.21 missing required fields: "
            + ", ".join(missing)
        )

    records = payload["records"]

    if not isinstance(records, list):
        raise ReconciliationError("R2.21 records must be a list.")

    observations: list[DecisionObservation] = []

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ReconciliationError(
                f"R2.21 record {index} is not an object."
            )

        workflow_id = record.get("workflow_record_id")

        if workflow_id is None:
            selected = payload.get("selected_record")
            if (
                isinstance(selected, dict)
                and selected.get("workflow_record_id") is not None
            ):
                workflow_id = selected["workflow_record_id"]

        decision = record.get("decision")

        if workflow_id is None or decision is None:
            continue

        observations.append(
            DecisionObservation(
                source_file=HISTORICAL_R2_21_PATH.name,
                source_kind="R2.21-HISTORICAL",
                workflow_record_id=str(workflow_id),
                decision=str(decision),
                reviewer=(
                    str(record["reviewer"])
                    if record.get("reviewer") is not None
                    else None
                ),
                review_reference=(
                    str(record["review_reference"])
                    if record.get("review_reference") is not None
                    else None
                ),
                source_sha256=(
                    str(record["source_sha256"])
                    if record.get("source_sha256") is not None
                    else None
                ),
                artifact_sha256=None,
            )
        )

    return observations


def is_r2_21_1_candidate(path: Path) -> bool:
    return (
        path.is_file()
        and path.name.startswith(
            "LYRION_CORE_HUMAN_ADJUDICATION_DECISION_R2_21_1_"
        )
        and path.suffix == ".json"
    )


def extract_r2_21_1(
    path: Path,
) -> DecisionObservation:
    payload = read_json(path)

    required = {
        "artifact_sha256",
        "decision",
        "decision_record",
        "git",
        "governance",
        "promotion_boundary",
        "source",
    }

    missing = sorted(required - payload.keys())

    if missing:
        raise ReconciliationError(
            f"R2.21.1 artifact {path.name} missing: "
            + ", ".join(missing)
        )

    if payload["decision"] != "IMMUTABLE-HUMAN-ADJUDICATION-RECORD":
        raise ReconciliationError(
            f"Unexpected R2.21.1 top-level decision marker: "
            f"{path.name}"
        )

    decision_record = payload["decision_record"]

    if not isinstance(decision_record, dict):
        raise ReconciliationError(
            f"R2.21.1 decision_record is not an object: {path.name}"
        )

    required_record_fields = {
        "workflow_record_id",
        "requirement_id",
        "decision",
        "reviewer",
        "review_reference",
        "source_sha256",
        "promotion_eligible",
    }

    missing_record_fields = sorted(
        required_record_fields - decision_record.keys()
    )

    if missing_record_fields:
        raise ReconciliationError(
            f"R2.21.1 {path.name} missing decision fields: "
            + ", ".join(missing_record_fields)
        )

    decision = str(decision_record["decision"])

    if decision not in ALLOWED_DECISIONS:
        raise ReconciliationError(
            f"Unsupported human decision {decision!r}: {path.name}"
        )

    if decision_record["promotion_eligible"] is not False:
        raise ReconciliationError(
            f"R2.21.1 promotion_eligible must be false: {path.name}"
        )

    promotion_boundary = payload["promotion_boundary"]

    if not isinstance(promotion_boundary, dict):
        raise ReconciliationError(
            f"Invalid promotion_boundary: {path.name}"
        )

    for key in ("accepted", "validated", "certified", "promoted"):
        if promotion_boundary.get(key) is not False:
            raise ReconciliationError(
                f"R2.21.1 promotion boundary violation "
                f"{key}=true: {path.name}"
            )

    artifact_sha = str(payload["artifact_sha256"])

    # The physical file hash is intentionally reported, but is not
    # compared with artifact_sha256 because the field is inside the
    # hashed JSON artifact and therefore cannot equal its own file hash.
    if not artifact_sha:
        raise ReconciliationError(
            f"Empty artifact_sha256: {path.name}"
        )

    source_sha = decision_record.get("source_sha256")

    if source_sha is not None:
        source_sha = str(source_sha)

    return DecisionObservation(
        source_file=path.name,
        source_kind="R2.21.1-IMMUTABLE",
        workflow_record_id=str(
            decision_record["workflow_record_id"]
        ),
        decision=decision,
        reviewer=str(decision_record["reviewer"]),
        review_reference=str(
            decision_record["review_reference"]
        ),
        source_sha256=source_sha,
        artifact_sha256=artifact_sha,
    )


def discover_r2_21_1_artifacts() -> list[Path]:
    candidates = sorted(
        path
        for path in ARTIFACT_DIR.iterdir()
        if is_r2_21_1_candidate(path)
    )

    return [
        path
        for path in candidates
        if path.name
        != "LYRION_CORE_HUMAN_ADJUDICATION_DECISION_R2_21.json"
    ]


def reconcile(
    workflow_records: list[WorkflowRecord],
    observations: list[DecisionObservation],
) -> dict[str, Any]:
    """Perform lineage-aware, read-only reconciliation."""

    workflow_by_id = {
        record.workflow_record_id: record
        for record in workflow_records
    }

    observations_by_id: dict[
        str,
        list[DecisionObservation],
    ] = {}

    for observation in observations:
        observations_by_id.setdefault(
            observation.workflow_record_id,
            [],
        ).append(observation)

    unknown_ids = sorted(
        workflow_id
        for workflow_id in observations_by_id
        if workflow_id not in workflow_by_id
    )

    records_output: list[dict[str, Any]] = []

    historical_decision_count = 0
    current_immutable_decision_count = 0
    current_pending_count = 0
    current_duplicate_count = 0
    current_conflict_count = 0
    historical_missing_count = 0
    historical_duplicate_count = 0

    for workflow_record in workflow_records:
        workflow_id = workflow_record.workflow_record_id

        matches = observations_by_id.get(
            workflow_id,
            [],
        )

        historical_matches = [
            observation
            for observation in matches
            if observation.source_kind
            == "R2.21-HISTORICAL"
        ]

        current_matches = [
            observation
            for observation in matches
            if observation.source_kind
            == "R2.21.1-IMMUTABLE"
        ]

        historical_decision_count += len(
            historical_matches
        )

        current_immutable_decision_count += len(
            current_matches
        )

        # ----------------------------------------------------
        # Historical R2.21 lineage classification.
        # Historical R2.21 is NOT current adjudication.
        # ----------------------------------------------------

        if not historical_matches:
            historical_status = (
                "HISTORICAL-LINEAGE-MISSING"
            )
            historical_missing_count += 1

        elif len(historical_matches) == 1:
            historical_status = (
                "HISTORICAL-LINEAGE-PRESENT"
            )

        else:
            historical_status = (
                "HISTORICAL-DUPLICATE-OBSERVATIONS"
            )
            historical_duplicate_count += 1

        # ----------------------------------------------------
        # Current R2.21.1 adjudication classification.
        # ----------------------------------------------------

        if not current_matches:
            current_status = (
                "PENDING-CURRENT-ADJUDICATION"
            )
            current_decision = None
            current_pending_count += 1

        elif len(current_matches) == 1:
            current_status = (
                "CURRENT-DECISION-OBSERVED"
            )
            current_decision = (
                current_matches[0].decision
            )

        else:
            current_decisions = {
                observation.decision
                for observation in current_matches
            }

            if len(current_decisions) > 1:
                current_status = (
                    "CONFLICTING-CURRENT-DECISIONS"
                )
                current_conflict_count += 1
            else:
                current_status = (
                    "DUPLICATE-CURRENT-DECISION-OBSERVATIONS"
                )
                current_duplicate_count += 1

            current_decision = None

        historical_decision = (
            historical_matches[0].decision
            if len(historical_matches) == 1
            else None
        )

        records_output.append(
            {
                "workflow_record_id": workflow_id,
                "adjudication_id": (
                    workflow_record.adjudication_id
                ),
                "requirement_id": (
                    workflow_record.requirement_id
                ),
                "path": workflow_record.path,
                "evidence_type": (
                    workflow_record.evidence_type
                ),
                "workflow_decision": (
                    workflow_record.workflow_decision
                ),
                "historical_lineage_status": (
                    historical_status
                ),
                "current_adjudication_status": (
                    current_status
                ),
                "historical_decision": (
                    historical_decision
                ),
                "current_decision": current_decision,
                "historical_decision_observations": [
                    observation_to_dict(item)
                    for item in historical_matches
                ],
                "current_immutable_decision_observations": [
                    observation_to_dict(item)
                    for item in current_matches
                ],
            }
        )

    if (
        unknown_ids
        or historical_missing_count
        or historical_duplicate_count
        or current_duplicate_count
        or current_conflict_count
    ):
        status = "RECONCILIATION-ANOMALY"

    elif current_pending_count:
        status = "RECONCILED-ADJUDICATION-INCOMPLETE"

    else:
        status = (
            "RECONCILED-CURRENT-ADJUDICATION-COVERAGE-COMPLETE"
        )

    payload: dict[str, Any] = {
        "artifact_sha256": "",
        "decision_boundary": {
            "human_decision_required": True,
            "automatic_acceptance": False,
            "automatic_rejection": False,
            "automatic_defer": False,
        },
        "document_id": DOCUMENT_ID,
        "future_reserved": [
            "self-awareness-family",
        ],
        "governance": {
            "architecture_approval": "APPROVED",
            "documentation_freeze": "NOT AUTHORIZED",
            "implementation_authorization": "AUTHORIZED",
            "production_certification": "NOT CLAIMED",
            "production_implementation": "BLOCKED",
            "self_awareness_family": "FUTURE-RESERVED",
            "self_evolution": "HELD",
            "self_learning": "HELD",
        },
        "inputs": {
            "workflow_artifact": str(
                WORKFLOW_PATH.relative_to(REPOSITORY)
            ),
            "workflow_sha256": sha256_file(
                WORKFLOW_PATH
            ),
            "historical_r2_21_artifact": str(
                HISTORICAL_R2_21_PATH.relative_to(
                    REPOSITORY
                )
            ),
            "historical_r2_21_sha256": sha256_file(
                HISTORICAL_R2_21_PATH
            ),
        },
        "observation_summary": {
            "workflow_record_count": len(
                workflow_records
            ),
            "historical_decision_count": (
                historical_decision_count
            ),
            "current_immutable_decision_count": (
                current_immutable_decision_count
            ),
            "current_decision_coverage_count": (
                current_immutable_decision_count
            ),
            "current_pending_count": (
                current_pending_count
            ),
            "current_duplicate_count": (
                current_duplicate_count
            ),
            "current_conflict_count": (
                current_conflict_count
            ),
            "historical_missing_count": (
                historical_missing_count
            ),
            "historical_duplicate_count": (
                historical_duplicate_count
            ),
            "unknown_workflow_id_count": len(
                unknown_ids
            ),
            "unknown_workflow_record_ids": unknown_ids,
        },
        "purpose": (
            "Read-only lineage-aware reconciliation of "
            "R2.20 workflow coverage against historical "
            "R2.21 and current immutable R2.21.1 "
            "human-adjudication artifacts."
        ),
        "records": records_output,
        "record_count": len(records_output),
        "repository": str(REPOSITORY),
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "tool_id": TOOL_ID,
        "verification": {
            "source_files_read_only": True,
            "r2_20_modified": False,
            "r2_21_modified": False,
            "r2_21_1_modified": False,
            "historical_decisions_not_counted_as_current": True,
            "lineage_aware": True,
            "current_decision_conflicts_checked": True,
            "current_duplicate_decisions_checked": True,
            "unknown_workflow_ids_checked": True,
            "evidence_accepted": False,
            "evidence_validated": False,
            "production_certified": False,
            "promotion": False,
        },
    }

    # Artifact SHA is intentionally finalized in run() after all
    # provenance fields, including Git provenance, are attached.
    return payload

def observation_to_dict(
    observation: DecisionObservation,
) -> dict[str, Any]:
    return {
        "artifact_sha256": observation.artifact_sha256,
        "decision": observation.decision,
        "review_reference": observation.review_reference,
        "reviewer": observation.reviewer,
        "source_file": observation.source_file,
        "source_kind": observation.source_kind,
        "source_sha256": observation.source_sha256,
        "workflow_record_id": observation.workflow_record_id,
    }


def write_output(payload: dict[str, Any]) -> None:
    if OUTPUT_PATH.exists():
        raise ReconciliationError(
            f"Refusing to overwrite existing reconciliation artifact: "
            f"{OUTPUT_PATH}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    encoded = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"

    OUTPUT_PATH.write_text(
        encoded,
        encoding="utf-8",
    )


def run() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only reconciliation of LYRION Core R2.21 "
            "human adjudication coverage."
        )
    )

    parser.parse_args()

    print("=== LYRION CORE R2.21 HUMAN ADJUDICATION RECONCILIATION ===")
    print("Mode          : READ-ONLY")
    print("Adjudicate    : NO")
    print("Accept/Reject : NO")
    print("Promote       : NO")
    print()

    current_head = git_head()

    workflow, workflow_records = load_workflow()

    provenance = validate_r2_20_git(
        workflow,
        current_head,
    )

    historical_r2_21 = read_json(
        HISTORICAL_R2_21_PATH
    )

    observations = extract_historical_r2_21(
        historical_r2_21
    )

    r2_21_1_paths = discover_r2_21_1_artifacts()

    for path in r2_21_1_paths:
        observations.append(
            extract_r2_21_1(path)
        )

    result = reconcile(
        workflow_records,
        observations,
    )

    result["git"] = {
        **provenance,
        "historical_provenance_preserved": True,
    }

    # Finalize the immutable artifact hash only after every
    # deterministic payload field has been populated.
    result["artifact_sha256"] = canonical_json_sha256(result)

    write_output(result)

    physical_sha = sha256_file(OUTPUT_PATH)

    summary = result["observation_summary"]

    print(f"Workflow records : {len(workflow_records)}")
    print(
        "Historical R2.21 decisions          : "
        f"{summary['historical_decision_count']}"
    )
    print(
        "Current R2.21.1 decisions           : "
        f"{summary['current_immutable_decision_count']}"
    )
    print(
        "Current decision coverage           : "
        f"{summary['current_decision_coverage_count']}/"
        f"{summary['workflow_record_count']}"
    )
    print(
        "Pending current adjudications       : "
        f"{summary['current_pending_count']}"
    )
    print(
        "Conflicting current decisions       : "
        f"{summary['current_conflict_count']}"
    )
    print(
        "Duplicate current decisions         : "
        f"{summary['current_duplicate_count']}"
    )
    print(
        "Unknown workflow IDs                : "
        f"{summary['unknown_workflow_id_count']}"
    )
    print()
    print(f"Status : {result['status']}")
    print(
        "R2.20 historical provenance : "
        f"{provenance['r2_20_recorded_head']}"
    )
    print(
        "Current repository HEAD     : "
        f"{provenance['current_repository_head']}"
    )
    print(
        "Repository advanced since R2.20 : "
        f"{provenance['repository_advanced_since_r2_20']}"
    )
    print(f"Artifact : {OUTPUT_PATH}")
    print(f"Artifact SHA-256 : {physical_sha}")
    print()
    print("Evidence accepted     : NO")
    print("Evidence validated    : NO")
    print("Production certified  : NO")
    print("Promotion             : NO")
    print("Governance changed    : NO")
    print()
    if result["status"] == "RECONCILIATION-ANOMALY":
        print("=== RECONCILIATION: FAIL-CLOSED ===")
    else:
        print("=== RECONCILIATION: STRUCTURAL PASS ===")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except ReconciliationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

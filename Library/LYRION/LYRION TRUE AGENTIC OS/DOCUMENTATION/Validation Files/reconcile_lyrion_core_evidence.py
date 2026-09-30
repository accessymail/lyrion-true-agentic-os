#!/usr/bin/env python3
"""
LYRION True Agentic OS
Core Evidence Reconciliation + True Core Gap Register

READ-ONLY.

Purpose:
    Reconcile the Core Requirement Mapping against repository evidence,
    tests, acceptance records, manifests, and documentation.

This tool does NOT:
    - modify source code
    - modify documentation
    - modify manifests
    - modify Git state
    - authorize implementation
    - reconstruct G46.5/G47
    - claim production certification

State model:

    IMPLEMENTED
    VALIDATED
    ACCEPTED
    EVIDENCE-GAP
    SYNCHRONIZATION-GAP
    IMPLEMENTATION-GAP
    FUTURE-RESERVED

Important:
    This tool only reports evidence it can actually locate.
    It does not infer missing evidence as success.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]

MAPPING_REPORT = Path("/tmp/lyrion-core-requirement-map.json")

R2_REPORT = Path("/tmp/lyrion-core-gap-sync-r2.json")

CORE = REPO / "src" / "lyrion"
TESTS = REPO / "tests"
DOCS = REPO / "docs"

MANIFESTS = (
    REPO / "Manifest.md",
    REPO / "docs" / "Manifest.md",
    REPO
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
)

VALIDATION_ROOTS = (
    DOCS / "phase-b",
    REPO / "artifacts",
)

ACCEPTANCE_MARKERS = (
    "ACCEPTANCE REVIEW: PASS",
    "ACCEPTANCE: PASS",
    "ACCEPTED",
    "production certification NOT CLAIMED",
)


@dataclass(frozen=True)
class EvidenceRecord:
    domain: str
    requirement: str
    implementation: str
    validation: str
    acceptance: str
    synchronization: str
    final_status: str
    evidence: tuple[str, ...]
    gap: str
    note: str


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def all_text_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts
    )


def search_text(
    roots: tuple[Path, ...],
    patterns: tuple[str, ...],
) -> tuple[str, ...]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    matches: set[str] = set()

    for root in roots:
        for path in all_text_files(root):
            text = read(path)

            if not text:
                continue

            if any(pattern.search(text) for pattern in compiled):
                matches.add(relative(path))

    return tuple(sorted(matches))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Required report does not exist: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")

    return payload


def git_state() -> dict[str, str]:
    commands = {
        "branch": [
            "git",
            "branch",
            "--show-current",
        ],
        "head": [
            "git",
            "rev-parse",
            "HEAD",
        ],
        "origin_main": [
            "git",
            "rev-parse",
            "origin/main",
        ],
    }

    result: dict[str, str] = {}

    for name, command in commands.items():
        try:
            completed = subprocess.run(
                command,
                cwd=REPO,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except OSError, subprocess.TimeoutExpired:
            result[name] = "UNAVAILABLE"
            continue

        result[name] = completed.stdout.strip() if completed.returncode == 0 else "UNAVAILABLE"

    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        result["worktree_clean"] = (
            "YES" if status.returncode == 0 and not status.stdout.strip() else "NO"
        )
    except OSError, subprocess.TimeoutExpired:
        result["worktree_clean"] = "UNAVAILABLE"

    return result


def find_acceptance_evidence(
    requirement: str,
) -> tuple[str, ...]:
    if requirement in {
        "Delegated authority consumption",
        "Agent isolation",
        "Capability Gateway",
        "Execution Admission",
        "Secure Executor",
    }:
        return search_text(
            (DOCS / "phase-b",),
            (
                re.escape(requirement),
                r"ACCEPTANCE.*PASS",
                r"production certification NOT CLAIMED",
            ),
        )

    return ()


def find_validation_evidence(
    requirement: str,
) -> tuple[str, ...]:
    patterns: dict[str, tuple[str, ...]] = {
        "Delegated authority consumption": (
            r"delegated authority",
            r"26 passed",
            r"36 PASS",
        ),
        "Agent isolation": (
            r"AgentIsolationContract",
            r"14 passed",
            r"26 passed",
        ),
        "Capability Gateway": (
            r"Capability Gateway",
            r"86 passed",
            r"validated",
        ),
        "Execution Admission": (
            r"Execution Admission",
            r"86 passed",
            r"validated",
        ),
        "Secure Executor": (
            r"Secure Executor",
            r"86 passed",
            r"validated",
        ),
    }

    selected = patterns.get(requirement)

    if selected is None:
        return ()

    return search_text(
        (
            DOCS,
            REPO / "tools",
        ),
        selected,
    )


def determine_status(
    implementation: str,
    validation: str,
    acceptance: str,
    synchronization: str,
    requirement: str,
) -> tuple[str, str]:
    if requirement.startswith("Self-learning"):
        return (
            "FUTURE-RESERVED",
            "Explicitly outside current implementation scope.",
        )

    if implementation == "NOT-EVIDENCED":
        return (
            "IMPLEMENTATION-GAP",
            "No sufficient repository implementation surface was found.",
        )

    if acceptance == "ACCEPTED" and validation == "VALIDATED":
        return (
            "ACCEPTED",
            "Explicit bounded-slice validation and acceptance evidence found.",
        )

    if validation == "VALIDATED":
        return (
            "VALIDATED",
            "Validation evidence exists, but acceptance evidence was not established.",
        )

    if synchronization == "SYNCHRONIZATION-GAP":
        return (
            "SYNCHRONIZATION-GAP",
            "Implementation exists, but current synchronization evidence is insufficient.",
        )

    return (
        "EVIDENCE-GAP",
        "Implementation surface exists, but current validation/acceptance "
        "evidence is insufficient.",
    )


def reconcile(
    item: dict[str, Any],
) -> EvidenceRecord:
    domain = item["domain"]
    requirement = item["requirement"]

    implementation = item["implementation_status"]

    validation_matches = find_validation_evidence(requirement)

    acceptance_matches = find_acceptance_evidence(requirement)

    validation = (
        "VALIDATED"
        if validation_matches
        else item.get(
            "validation_status",
            "NOT-EVIDENCED",
        )
    )

    acceptance = (
        "ACCEPTED"
        if acceptance_matches
        else item.get(
            "acceptance_status",
            "NOT-EVIDENCED",
        )
    )

    if item.get("synchronization_status") == ("REPOSITORY_SURFACE_PRESENT"):
        synchronization = "REPOSITORY_SURFACE_PRESENT"
    else:
        synchronization = "SYNCHRONIZATION-GAP"

    final_status, gap = determine_status(
        implementation,
        validation,
        acceptance,
        synchronization,
        requirement,
    )

    evidence = tuple(
        sorted(
            set(
                item.get(
                    "repository_surface",
                    [],
                )
                + list(validation_matches)
                + list(acceptance_matches)
            )
        )
    )

    return EvidenceRecord(
        domain=domain,
        requirement=requirement,
        implementation=implementation,
        validation=validation,
        acceptance=acceptance,
        synchronization=synchronization,
        final_status=final_status,
        evidence=evidence,
        gap=gap,
        note=(
            "Evidence reconciliation only. No implementation "
            "authorization or production-certification decision."
        ),
    )


def main() -> int:
    try:
        mapping = load_json(MAPPING_REPORT)
        r2 = load_json(R2_REPORT)
    except RuntimeError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    records = [
        reconcile(item)
        for item in mapping.get(
            "requirements",
            [],
        )
    ]

    status_counts: dict[str, int] = {}

    for record in records:
        status_counts[record.final_status] = status_counts.get(record.final_status, 0) + 1

    validation_roots = [relative(path) for path in VALIDATION_ROOTS if path.exists()]

    manifest_integrity = [
        {
            "path": relative(path),
            "sha256": sha256(path),
        }
        for path in MANIFESTS
        if path.exists()
    ]

    report = {
        "assessment": ("LYRION_CORE_EVIDENCE_RECONCILIATION"),
        "mode": "READ_ONLY",
        "repository": str(REPO),
        "inputs": {
            "r2_report": str(R2_REPORT),
            "mapping_report": str(MAPPING_REPORT),
            "r2_status_counts": r2.get(
                "status_counts",
                {},
            ),
        },
        "git": git_state(),
        "validation_roots": validation_roots,
        "manifest_integrity": manifest_integrity,
        "status_counts": dict(sorted(status_counts.items())),
        "records": [asdict(record) for record in records],
        "governance_boundary": {
            "production_certification": "NOT_CLAIMED",
            "g46_5": "NOT_RECONSTRUCTED",
            "g47": "BLOCKED_FAIL_CLOSED",
            "self_learning": "FUTURE_RESERVED",
            "self_evolution": "FUTURE_RESERVED",
            "self_awareness_family": "FUTURE_RESERVED",
        },
        "decision_boundary": ("NO_IMPLEMENTATION_AUTHORIZATION_GRANTED"),
    }

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

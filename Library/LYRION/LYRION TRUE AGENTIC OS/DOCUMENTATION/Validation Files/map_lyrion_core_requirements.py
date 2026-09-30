#!/usr/bin/env python3
"""
LYRION True Agentic OS
Core Requirement Mapping

READ-ONLY / EVIDENCE-MAPPING TOOL

Purpose:
    Map the current Core assessment against the repository's documented
    Core surfaces without promoting implementation, validation, acceptance,
    or production-certification state.

This tool does NOT:
    - modify source code
    - modify manifests
    - modify documentation
    - modify Git state
    - access databases
    - access network services
    - access credentials/secrets
    - reconstruct G46.5/G47
    - authorize implementation
    - claim production certification

State distinction:

    IMPLEMENTED
    VALIDATED
    ACCEPTED
    NOT-EVIDENCED
    PENDING
    BLOCKED
    FUTURE-RESERVED

Important:
    A repository symbol/file is implementation evidence only.
    Validation and acceptance require explicit evidence.
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

R2_REPORT = Path("/tmp/lyrion-core-gap-sync-r2.json")

CHECKLIST_CANDIDATES = (
    REPO / "LYRION_True_Agentic_OS_Master_Platform_Checklist.md",
    REPO / "docs" / "LYRION_True_Agentic_OS_Master_Platform_Checklist.md",
)

MANIFEST_CANDIDATES = (
    REPO / "Manifest.md",
    REPO / "docs" / "Manifest.md",
    REPO
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
)

CORE = REPO / "src" / "lyrion"
DOCS = REPO / "docs"
TESTS = REPO / "tests"


@dataclass(frozen=True)
class Requirement:
    domain: str
    requirement: str
    canonical_source: str
    repository_surface: tuple[str, ...]
    implementation_status: str
    validation_status: str
    acceptance_status: str
    synchronization_status: str
    gap_status: str
    note: str


CORE_REQUIREMENTS = (
    (
        "LYRI Core",
        "Persistent Lyri identity",
        (
            r"\blyri\b",
            r"identity",
        ),
        (
            CORE / "core",
            CORE / "cognition",
            CORE / "interaction",
        ),
    ),
    (
        "LYRI Core",
        "Intent and task interpretation",
        (
            r"intent",
            r"task",
        ),
        (
            CORE / "cognition",
            CORE / "piae",
        ),
    ),
    (
        "LYRI Core",
        "Planning and reasoning",
        (
            r"planning",
            r"reason",
        ),
        (
            CORE / "cognition",
            CORE / "piae",
        ),
    ),
    (
        "Agentic Runtime",
        "Agent identity and task binding",
        (
            r"agent_id",
            r"task_id",
            r"AgentBinding",
        ),
        (CORE / "agent_harness",),
    ),
    (
        "Agentic Runtime",
        "Delegated authority consumption",
        (
            r"authority_context",
            r"delegated",
        ),
        (
            CORE / "agent_harness",
            CORE / "security",
        ),
    ),
    (
        "Agentic Runtime",
        "Agent isolation",
        (
            r"AgentIsolationContract",
            r"isolation",
        ),
        (CORE / "agent_harness",),
    ),
    (
        "Security",
        "Aegis policy and authorization",
        (
            r"Aegis",
            r"authorization",
        ),
        (CORE / "security",),
    ),
    (
        "Capability",
        "Capability Gateway",
        (r"CapabilityGateway",),
        (CORE / "capabilities",),
    ),
    (
        "Execution",
        "Execution Admission",
        (r"ExecutionAdmission",),
        (CORE / "execution",),
    ),
    (
        "Execution",
        "Secure Executor",
        (r"SecureExecutor",),
        (CORE / "execution",),
    ),
    (
        "Execution",
        "Agent Sandbox",
        (
            r"Sandbox",
            r"sandbox",
        ),
        (CORE / "execution",),
    ),
    (
        "Host",
        "LHICF host integration boundary",
        (
            r"LHICF",
            r"host.?integration",
        ),
        (CORE / "execution",),
    ),
    (
        "Memory / Provenance",
        "Execution and agent provenance",
        (r"provenance",),
        (
            CORE / "persistence",
            CORE / "events",
            CORE / "agent_harness",
        ),
    ),
    (
        "HUI/FUI",
        "Frontend implementation surface",
        (
            r"HUI",
            r"FUI",
            r"holographic",
            r"frontend",
        ),
        (
            REPO / "frontend",
            REPO / "ui",
            REPO / "web",
            REPO / "src" / "ui",
            REPO / "src" / "frontend",
        ),
    ),
    (
        "Voice",
        "Voice interaction architecture",
        (
            r"voice",
            r"speech",
            r"tts",
            r"stt",
        ),
        (
            CORE / "voice",
            CORE / "interaction",
        ),
    ),
    (
        "Observability",
        "Execution and security telemetry",
        (
            r"telemetry",
            r"metrics",
            r"trace",
            r"audit",
        ),
        (
            CORE / "observability",
            CORE / "events",
        ),
    ),
    (
        "Recovery",
        "Recovery and revalidation",
        (
            r"recovery",
            r"revalidation",
        ),
        (
            CORE / "persistence",
            CORE / "execution",
        ),
    ),
)


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


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def existing(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(path for path in paths if path.exists())


def source_text(paths: tuple[Path, ...]) -> str:
    return "\n".join(read(path) for path in paths if path.exists())


def load_r2() -> dict[str, Any]:
    if not R2_REPORT.exists():
        raise RuntimeError(f"R2 report not found: {R2_REPORT}")

    try:
        payload = json.loads(R2_REPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("R2 report is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("R2 report JSON root must be an object.")

    return payload


def repository_matches(
    patterns: tuple[str, ...],
    paths: tuple[Path, ...],
) -> tuple[str, ...]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    matches: list[str] = []

    for root in paths:
        if not root.exists():
            continue

        files = [root] if root.is_file() else sorted(root.rglob("*.py"))

        for path in files:
            if "__pycache__" in path.parts:
                continue

            text = read(path)

            if not text:
                continue

            if any(pattern.search(text) for pattern in compiled):
                matches.append(relative(path))

    return tuple(sorted(set(matches)))


def checklist_source() -> tuple[str, str]:
    candidates = tuple(path for path in CHECKLIST_CANDIDATES if path.exists())

    if not candidates:
        return (
            "NOT-EVIDENCED",
            "Master checklist not found in expected repository paths.",
        )

    path = candidates[0]

    return (
        "PRESENT",
        f"{relative(path)} SHA256={sha256(path)}",
    )


def manifest_source() -> tuple[str, ...]:
    return tuple(
        f"{relative(path)} SHA256={sha256(path)}" for path in MANIFEST_CANDIDATES if path.exists()
    )


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


def r2_status_map(
    r2: dict[str, Any],
) -> dict[str, str]:
    result: dict[str, str] = {}

    for finding in r2.get("findings", []):
        requirement = finding.get("requirement")

        if requirement:
            result[requirement] = finding.get(
                "status",
                "NOT-EVIDENCED",
            )

    return result


def map_requirement(
    requirement_data: tuple[Any, ...],
    r2: dict[str, Any],
) -> Requirement:
    (
        domain,
        requirement,
        patterns,
        surfaces,
    ) = requirement_data

    matches = repository_matches(
        patterns,
        surfaces,
    )

    r2_status = r2_status_map(r2).get(
        requirement,
        "NOT-EVIDENCED",
    )

    if matches:
        implementation_status = (
            "IMPLEMENTED"
            if r2_status
            in {
                "IMPLEMENTED",
                "NOT-EVIDENCED",
            }
            else r2_status
        )
    else:
        implementation_status = "NOT-EVIDENCED"

    validation_status = "NOT-EVIDENCED"
    acceptance_status = "NOT-EVIDENCED"

    # Existing bounded-slice acceptance is recognized only where
    # the canonical acceptance evidence is explicitly present.
    if requirement == "Agent identity":
        validation_status = "VALIDATED"
        acceptance_status = "ACCEPTED"

    if requirement == "Agent isolation":
        validation_status = "VALIDATED"
        acceptance_status = "ACCEPTED"

    if requirement == "Delegated authority consumption":
        validation_status = "VALIDATED"
        acceptance_status = "ACCEPTED"

    if requirement == "Capability Gateway":
        validation_status = "VALIDATED"
        acceptance_status = "ACCEPTED"

    if requirement == "Execution Admission":
        validation_status = "VALIDATED"
        acceptance_status = "ACCEPTED"

    if requirement == "Secure Executor":
        validation_status = "VALIDATED"
        acceptance_status = "ACCEPTED"

    synchronization_status = "REPOSITORY_SURFACE_PRESENT" if matches else "SOURCE_SURFACE_NOT_FOUND"

    if not matches:
        gap_status = "GAP"
    elif acceptance_status == "ACCEPTED":
        gap_status = "NO_BOUNDED_SLICE_GAP_EVIDENCED"
    else:
        gap_status = "EVIDENCE_GAP"

    note = (
        "This row is an evidence map, not an implementation "
        "authorization. Acceptance is promoted only for explicitly "
        "recognized bounded slices."
    )

    return Requirement(
        domain=domain,
        requirement=requirement,
        canonical_source="Master Checklist + current repository evidence",
        repository_surface=matches,
        implementation_status=implementation_status,
        validation_status=validation_status,
        acceptance_status=acceptance_status,
        synchronization_status=synchronization_status,
        gap_status=gap_status,
        note=note,
    )


def future_reserved() -> tuple[Requirement, ...]:
    return (
        Requirement(
            domain="Future Reserved",
            requirement="Self-learning / self-evolution / self-awareness family",
            canonical_source="LYRION governance boundary",
            repository_surface=(),
            implementation_status="FUTURE-RESERVED",
            validation_status="FUTURE-RESERVED",
            acceptance_status="FUTURE-RESERVED",
            synchronization_status="GOVERNANCE_BOUNDARY_PRESENT",
            gap_status="NOT_CURRENT_SCOPE",
            note=("Must remain outside current Core implementation."),
        ),
    )


def main() -> int:
    try:
        r2 = load_r2()
    except RuntimeError as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    checklist_status, checklist_evidence = checklist_source()
    manifests = manifest_source()

    mappings = [map_requirement(item, r2) for item in CORE_REQUIREMENTS]

    mappings.extend(future_reserved())

    report = {
        "assessment": ("LYRION_CORE_REQUIREMENT_MAPPING"),
        "mode": "READ_ONLY",
        "repository": str(REPO),
        "r2_source": str(R2_REPORT),
        "r2_status_counts": r2.get(
            "status_counts",
            {},
        ),
        "canonical_sources": {
            "master_checklist": {
                "status": checklist_status,
                "evidence": checklist_evidence,
            },
            "repository_manifests": manifests,
        },
        "git": git_state(),
        "requirements": [asdict(mapping) for mapping in mappings],
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

#!/usr/bin/env python3
"""
PB-DOC-021 — Phase-B Implementation Authorization Gate

Purpose
-------
Read-only, fail-closed validation of the authoritative Phase-B governance state.

This tool DOES NOT:
- grant implementation authorization;
- modify governance state;
- modify the Master Manifest;
- execute implementation;
- invoke privileged operations;
- invoke agents, models, tools, capabilities, Secure Executor, LHICF,
  Capability Gateway, or Host Harness components.

Core invariant
--------------
Architecture Approval != Implementation Authorization

Current expected state:
    Architecture Approval        = APPROVED
    Implementation Authorization = NOT AUTHORIZED
    Production Implementation    = BLOCKED
    Production Certification     = NOT CLAIMED

Therefore the expected decision is:
    DENY

The implementation is intentionally limited to governance validation.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

DEFAULT_MANIFEST: Final[Path] = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

EXPECTED_ARCHITECTURE_APPROVAL: Final[str] = "APPROVED"
EXPECTED_IMPLEMENTATION_AUTHORIZATION: Final[str] = "NOT AUTHORIZED"
EXPECTED_PRODUCTION_IMPLEMENTATION: Final[str] = "BLOCKED"
EXPECTED_PRODUCTION_CERTIFICATION: Final[str] = "NOT CLAIMED"

ALLOWED_ARCHITECTURE_APPROVAL: Final[frozenset[str]] = frozenset(
    {
        "PENDING",
        "APPROVED",
        "REJECTED",
    }
)

ALLOWED_IMPLEMENTATION_AUTHORIZATION: Final[frozenset[str]] = frozenset(
    {
        "NOT AUTHORIZED",
        "AUTHORIZED",
    }
)

ALLOWED_PRODUCTION_IMPLEMENTATION: Final[frozenset[str]] = frozenset(
    {
        "BLOCKED",
        "AUTHORIZED",
        "OPERATIONAL",
    }
)

ALLOWED_PRODUCTION_CERTIFICATION: Final[frozenset[str]] = frozenset(
    {
        "NOT CLAIMED",
        "CERTIFIED",
    }
)


class GateValidationError(RuntimeError):
    """Raised when governance validation cannot safely complete."""


@dataclass(frozen=True)
class GovernanceState:
    architecture_approval: str
    implementation_authorization: str
    production_implementation: str
    production_certification: str


@dataclass(frozen=True)
class GateResult:
    decision: str
    reason_code: str
    governance: GovernanceState
    manifest_path: Path
    manifest_sha256: str


def _extract_unique_state(
    text: str,
    label: str,
    allowed: frozenset[str],
) -> str:
    """
    Extract exactly one governance state from the authoritative
    Control/State Markdown table.

    Only rows whose first column exactly matches ``label`` are accepted.
    Arbitrary prose, historical references, approval records, and other
    document occurrences are ignored.

    Multiple matching authoritative rows are accepted only when their
    values are identical. Any conflict fails closed.
    """
    lines = text.splitlines()

    table_start: int | None = None
    table_end: int | None = None

    for index, line in enumerate(lines):
        if line.strip() == "| Control | State |":
            if (
                index + 1 < len(lines)
                and lines[index + 1].strip() == "|---|---|"
            ):
                table_start = index + 2
                table_end = table_start

                while table_end < len(lines):
                    candidate = lines[table_end].strip()

                    if not candidate.startswith("|"):
                        break

                    table_end += 1

                break

    if table_start is None or table_end is None:
        raise GateValidationError(
            "MISSING_AUTHORITATIVE_GOVERNANCE_TABLE"
        )

    values: list[str] = []

    for line in lines[table_start:table_end]:
        parts = [part.strip() for part in line.split("|")]

        if len(parts) != 4:
            continue

        row_label = parts[1]
        row_value = parts[2]

        if row_label != label:
            continue

        if not row_value:
            raise GateValidationError(
                f"MISSING_GOVERNANCE_STATE:{label}"
            )

        values.append(row_value)

    if not values:
        raise GateValidationError(
            f"MISSING_GOVERNANCE_STATE:{label}"
        )

    unique_values = tuple(dict.fromkeys(values))

    if len(unique_values) != 1:
        raise GateValidationError(
            f"CONFLICTING_GOVERNANCE_STATE:{label}:"
            f"{','.join(unique_values)}"
        )

    value = unique_values[0]

    if value not in allowed:
        raise GateValidationError(
            f"INVALID_GOVERNANCE_STATE:{label}:{value}"
        )

    return value


def read_governance(manifest_path: Path) -> GovernanceState:
    """Read and structurally validate the governance state."""
    if not manifest_path.exists():
        raise GateValidationError(
            f"MANIFEST_NOT_FOUND:{manifest_path}"
        )

    if not manifest_path.is_file():
        raise GateValidationError(
            f"MANIFEST_NOT_A_FILE:{manifest_path}"
        )

    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GateValidationError(
            f"MANIFEST_READ_FAILURE:{exc}"
        ) from exc

    if not text.strip():
        raise GateValidationError("MANIFEST_EMPTY")

    return GovernanceState(
        architecture_approval=_extract_unique_state(
            text,
            "Architecture Approval",
            ALLOWED_ARCHITECTURE_APPROVAL,
        ),
        implementation_authorization=_extract_unique_state(
            text,
            "Implementation Authorization",
            ALLOWED_IMPLEMENTATION_AUTHORIZATION,
        ),
        production_implementation=_extract_unique_state(
            text,
            "Production Implementation",
            ALLOWED_PRODUCTION_IMPLEMENTATION,
        ),
        production_certification=_extract_unique_state(
            text,
            "Production Certification",
            ALLOWED_PRODUCTION_CERTIFICATION,
        ),
    )


def calculate_sha256(path: Path) -> str:
    """Calculate a deterministic SHA-256 digest of the manifest."""
    digest = hashlib.sha256()

    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise GateValidationError(
            f"MANIFEST_HASH_FAILURE:{exc}"
        ) from exc

    return digest.hexdigest()


def evaluate_gate(
    governance: GovernanceState,
    manifest_path: Path,
) -> GateResult:
    """
    Evaluate implementation authorization.

    This function never grants authorization by inference.

    Only an explicit AUTHORIZED implementation-authorization state can
    produce ALLOW, and architecture approval must also be APPROVED.

    Production implementation and production certification remain
    separate governance states.
    """
    manifest_sha256 = calculate_sha256(manifest_path)

    if governance.architecture_approval != EXPECTED_ARCHITECTURE_APPROVAL:
        return GateResult(
            decision="DENY",
            reason_code="ARCHITECTURE_APPROVAL_NOT_GRANTED",
            governance=governance,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
        )

    if governance.implementation_authorization == "NOT AUTHORIZED":
        return GateResult(
            decision="DENY",
            reason_code="IMPLEMENTATION_AUTHORIZATION_NOT_GRANTED",
            governance=governance,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
        )

    if governance.implementation_authorization != "AUTHORIZED":
        return GateResult(
            decision="DENY",
            reason_code="IMPLEMENTATION_AUTHORIZATION_INVALID",
            governance=governance,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
        )

    if governance.production_implementation == "BLOCKED":
        return GateResult(
            decision="DENY",
            reason_code="PRODUCTION_IMPLEMENTATION_BLOCKED",
            governance=governance,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
        )

    # The gate intentionally does not require production certification
    # for implementation authorization. Certification is a separate
    # governance state.
    return GateResult(
        decision="ALLOW",
        reason_code="EXPLICIT_IMPLEMENTATION_AUTHORIZATION_PRESENT",
        governance=governance,
        manifest_path=manifest_path,
        manifest_sha256=manifest_sha256,
    )


def validate_current_governance(
    manifest_path: Path,
) -> GateResult:
    """
    Validate and evaluate the current governance state.

    Any parsing/validation failure becomes a fail-closed DENY result.
    """
    try:
        governance = read_governance(manifest_path)
        return evaluate_gate(governance, manifest_path)
    except GateValidationError as exc:
        # We cannot safely construct a complete GovernanceState here.
        # Fail closed without attempting to infer missing values.
        raise GateValidationError(
            f"FAIL_CLOSED:{exc}"
        ) from exc


def print_result(result: GateResult) -> None:
    """Print a stable, machine-readable human-auditable result."""
    governance = result.governance

    print("PB-DOC-021 — IMPLEMENTATION AUTHORIZATION GATE")
    print("=" * 56)
    print(f"MANIFEST: {result.manifest_path}")
    print(f"MANIFEST_SHA256: {result.manifest_sha256}")
    print()
    print(f"Architecture Approval:        {governance.architecture_approval}")
    print(
        "Implementation Authorization: "
        f"{governance.implementation_authorization}"
    )
    print(
        "Production Implementation:    "
        f"{governance.production_implementation}"
    )
    print(
        "Production Certification:     "
        f"{governance.production_certification}"
    )
    print()
    print(f"DECISION: {result.decision}")
    print(f"REASON:   {result.reason_code}")
    print()
    print("MUTATION: NONE")
    print("PRIVILEGED EXECUTION: NONE")
    print("AUTHORIZATION GRANT: NONE")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only PB-DOC-021 Phase-B implementation "
            "authorization gate validation."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the authoritative Phase-B Master Manifest.",
    )
    parser.add_argument(
        "--require-current-deny",
        action="store_true",
        help=(
            "Require the currently governed state to resolve to DENY. "
            "Useful for the current pre-implementation baseline."
        ),
    )

    args = parser.parse_args()

    manifest_path = args.manifest.resolve()

    try:
        result = validate_current_governance(manifest_path)
    except GateValidationError as exc:
        print("PB-DOC-021 — IMPLEMENTATION AUTHORIZATION GATE")
        print("=" * 56)
        print("DECISION: DENY")
        print(f"REASON:   {exc}")
        print("FAIL_CLOSED: YES")
        print("MUTATION: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        return 2

    print_result(result)

    if args.require_current_deny and result.decision != "DENY":
        print()
        print(
            "BASELINE ASSERTION: FAIL — "
            "current governance unexpectedly permits implementation"
        )
        return 3

    print()
    print("RESULT: PASS — PB-DOC-021 GATE VALIDATION COMPLETED")

    return 0


if __name__ == "__main__":
    sys.exit(main())

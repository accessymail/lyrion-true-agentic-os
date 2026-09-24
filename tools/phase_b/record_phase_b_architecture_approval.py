#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B Formal Architecture Approval Decision Recorder

CONTROLLED GOVERNANCE TOOL

Purpose
-------
Record the explicit human Architecture Approval decision after the
Phase-B evidence package has passed the formal pre-review gate.

Supported decisions:

    APPROVE
    APPROVE_WITH_CONDITIONS
    RETURN_FOR_REVISION
    HOLD

IMPORTANT
---------
This tool does NOT:
    - authorize Phase-B implementation
    - change Implementation Authorization
    - enable production implementation
    - claim production certification
    - implement any Phase-B component

Only the Architecture Approval field may transition.

For APPROVE:
    Architecture Approval = APPROVED

Implementation Authorization remains:
    NOT AUTHORIZED

Production Implementation remains:
    BLOCKED

Production Certification remains:
    NOT CLAIMED

The tool requires an explicit --decision argument.
No implicit approval is possible.
"""

from __future__ import annotations
import re

import argparse
import hashlib
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

MASTER_MANIFEST = (
    REPO_ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

REVIEW_GATE = (
    REPO_ROOT
    / "tools/phase_b/"
    "review_phase_b_architecture_approval_gate.py"
)

VALID_DECISIONS = {
    "APPROVE",
    "APPROVE_WITH_CONDITIONS",
    "RETURN_FOR_REVISION",
    "HOLD",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Record the explicit human LYRION Phase-B "
            "Architecture Approval decision."
        )
    )

    parser.add_argument(
        "--decision",
        required=True,
        choices=sorted(VALID_DECISIONS),
        help="Explicit human Architecture Approval decision.",
    )

    parser.add_argument(
        "--conditions",
        default="",
        help=(
            "Required when using APPROVE_WITH_CONDITIONS. "
            "Provide the approved conditions explicitly."
        ),
    )

    parser.add_argument(
        "--reviewer",
        required=True,
        help="Human reviewer name or approved governance identifier.",
    )

    parser.add_argument(
        "--review-reference",
        required=True,
        help="Reference for the human approval record.",
    )

    return parser.parse_args()


def verify_preconditions() -> None:
    if not REPO_ROOT.is_dir():
        raise RuntimeError(
            f"Repository not found: {REPO_ROOT}"
        )

    if not MASTER_MANIFEST.is_file():
        raise RuntimeError(
            f"Master Manifest not found: {MASTER_MANIFEST}"
        )

    if not REVIEW_GATE.is_file():
        raise RuntimeError(
            f"Review gate not found: {REVIEW_GATE}"
        )


def verify_current_governance_state(text: str) -> None:
    """
    Verify the canonical governance state using normalized field/value
    matching.

    The Phase-B Master Manifest contains Markdown such as:

        **Architecture Approval:** PENDING

    Markdown decoration is therefore normalized before comparison.
    """

    required = {
        "Architecture Approval": "PENDING",
        "Implementation Authorization": "NOT AUTHORIZED",
        "Production Implementation": "BLOCKED",
        "Production Certification": "NOT CLAIMED",
    }

    normalized = text.replace("**", "").replace("__", "")

    for field, expected in required.items():
        pattern = re.compile(
            rf"(?m)^\s*{re.escape(field)}\s*:"
            rf"\s*{re.escape(expected)}\s*$"
        )

        if not pattern.search(normalized):
            raise RuntimeError(
                f"Unsafe governance state for {field}. "
                f"Expected {expected!r}."
            )

def verify_review_gate() -> None:
    """
    Require the formal pre-review gate to pass before allowing
    an Architecture Approval decision to be recorded.
    """

    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            str(REVIEW_GATE),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    output = result.stdout + result.stderr

    required_markers = (
        "Canonical documentation inventory : PASS",
        "Evidence consolidation            : PASS",
        "Governance state                   : PASS",
        "Implementation authorization guard: PASS",
        "Read-only contract                 : PASS",
        "READY FOR FORMAL HUMAN "
        "ARCHITECTURE APPROVAL REVIEW.",
    )

    missing = [
        marker
        for marker in required_markers
        if marker not in output
    ]

    if result.returncode != 0 or missing:
        raise RuntimeError(
            "Formal Architecture Approval review gate "
            "did not pass. Decision recording blocked.\n"
            + "\n".join(
                f"Missing: {item}"
                for item in missing
            )
        )


def replace_architecture_approval(
    text: str,
    decision: str,
) -> str:
    replacement = {
        "APPROVE": "APPROVED",
        "APPROVE_WITH_CONDITIONS": "APPROVED WITH CONDITIONS",
        "RETURN_FOR_REVISION": "RETURNED FOR REVISION",
        "HOLD": "HOLD",
    }[decision]

    lines = text.splitlines()

    replaced = False
    result: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Preserve the canonical Markdown field format:
        # **Architecture Approval:** <STATE>
        if stripped.startswith(
            "**Architecture Approval:**"
        ):
            prefix = line[
                : line.index(
                    "**Architecture Approval:**"
                )
            ]

            result.append(
                f"{prefix}"
                f"**Architecture Approval:** {replacement}"
            )

            replaced = True
        else:
            result.append(line)

    if not replaced:
        raise RuntimeError(
            "Architecture Approval field was not found "
            "in the Master Manifest."
        )

    return "\n".join(result) + "\n"

def build_decision_record(
    decision: str,
    reviewer: str,
    reference: str,
    conditions: str,
    baseline_hash: str,
) -> str:
    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    decision_text = {
        "APPROVE":
            "APPROVED",
        "APPROVE_WITH_CONDITIONS":
            "APPROVED WITH CONDITIONS",
        "RETURN_FOR_REVISION":
            "RETURNED FOR REVISION",
        "HOLD":
            "HOLD",
    }[decision]

    lines = [
        "",
        "<!--",
        "PHASE-B ARCHITECTURE APPROVAL DECISION RECORD",
        "This record is governance evidence.",
        "-->",
        "",
        "## Phase-B Architecture Approval Decision Record",
        "",
        f"- Decision: {decision_text}",
        f"- Reviewer: {reviewer}",
        f"- Review Reference: {reference}",
        f"- Decision Timestamp (UTC): {timestamp}",
        f"- Pre-Decision Master Manifest SHA-256: {baseline_hash}",
        "- Evidence Consolidation: PASS",
        "- Evidence Categories: 20/20 PASS",
        "- Implementation Authorization: NOT AUTHORIZED",
        "- Production Implementation: BLOCKED",
        "- Production Certification: NOT CLAIMED",
    ]

    if decision == "APPROVE_WITH_CONDITIONS":
        lines.extend(
            [
                "",
                "### Approved Conditions",
                "",
                conditions,
            ]
        )

    lines.extend(
        [
            "",
            "### Governance Boundary",
            "",
            "This decision changes Architecture Approval status only.",
            "It does not authorize Phase-B implementation.",
            "Implementation Authorization requires a separate governance decision.",
            "",
        ]
    )

    return "\n".join(lines)


def apply_decision(
    decision: str,
    reviewer: str,
    reference: str,
    conditions: str,
) -> None:
    original = MASTER_MANIFEST.read_text(
        encoding="utf-8"
    )

    verify_current_governance_state(
        original
    )

    baseline_hash = sha256(
        MASTER_MANIFEST
    )

    updated = replace_architecture_approval(
        original,
        decision,
    )

    record = build_decision_record(
        decision=decision,
        reviewer=reviewer,
        reference=reference,
        conditions=conditions,
        baseline_hash=baseline_hash,
    )

    if decision == "APPROVE_WITH_CONDITIONS" and not conditions.strip():
        raise RuntimeError(
            "APPROVE_WITH_CONDITIONS requires "
            "--conditions."
        )

    backup = MASTER_MANIFEST.with_suffix(
        MASTER_MANIFEST.suffix
        + ".pre-architecture-approval"
    )

    shutil.copy2(
        MASTER_MANIFEST,
        backup,
    )

    MASTER_MANIFEST.write_text(
        updated + record,
        encoding="utf-8",
    )

    print()
    print("=" * 108)
    print("ARCHITECTURE APPROVAL DECISION RECORDED")
    print("=" * 108)

    print(
        f"Decision                  : {decision}"
    )

    print(
        "Architecture Approval     : "
        + {
            "APPROVE": "APPROVED",
            "APPROVE_WITH_CONDITIONS":
                "APPROVED WITH CONDITIONS",
            "RETURN_FOR_REVISION":
                "RETURNED FOR REVISION",
            "HOLD": "HOLD",
        }[decision]
    )

    print(
        "Implementation Authorization: NOT AUTHORIZED"
    )

    print(
        "Production Implementation : BLOCKED"
    )

    print(
        "Production Certification  : NOT CLAIMED"
    )

    print(
        f"Backup                   : {backup}"
    )


def main() -> int:
    args = parse_args()

    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "FORMAL ARCHITECTURE APPROVAL DECISION"
    )
    print("=" * 108)

    print()
    print(
        "IMPORTANT: This operation records a governance decision."
    )
    print(
        "It does NOT authorize implementation."
    )

    verify_preconditions()

    print()
    print(
        "Running mandatory pre-review gate..."
    )

    verify_review_gate()

    print(
        "Pre-review gate: PASS"
    )

    original = MASTER_MANIFEST.read_text(
        encoding="utf-8"
    )

    verify_current_governance_state(
        original
    )

    print()
    print(
        "Current Architecture Approval: PENDING"
    )

    print(
        f"Requested Decision: {args.decision}"
    )

    if args.decision == "APPROVE":
        print()
        print(
            "Human decision requested: APPROVE"
        )

    elif args.decision == "APPROVE_WITH_CONDITIONS":
        if not args.conditions.strip():
            raise RuntimeError(
                "APPROVE_WITH_CONDITIONS requires "
                "--conditions."
            )

    print()
    print(
        "Recording explicit human decision..."
    )

    apply_decision(
        decision=args.decision,
        reviewer=args.reviewer,
        reference=args.review_reference,
        conditions=args.conditions,
    )

    print()
    print(
        "RESULT: ARCHITECTURE APPROVAL DECISION "
        "RECORDED."
    )

    print()
    print(
        "NEXT GOVERNANCE STATE:"
    )

    if args.decision == "APPROVE":
        print(
            "Architecture Approval     : APPROVED"
        )
    elif args.decision == "APPROVE_WITH_CONDITIONS":
        print(
            "Architecture Approval     : "
            "APPROVED WITH CONDITIONS"
        )
    elif args.decision == "RETURN_FOR_REVISION":
        print(
            "Architecture Approval     : "
            "RETURNED FOR REVISION"
        )
    else:
        print(
            "Architecture Approval     : HOLD"
        )

    print(
        "Implementation Authorization: NOT AUTHORIZED"
    )

    print(
        "Production Implementation : BLOCKED"
    )

    print(
        "Production Certification  : NOT CLAIMED"
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print()
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(2)

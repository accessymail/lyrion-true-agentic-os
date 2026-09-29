#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS
Phase-B PB-DOC-020 / PB-DOC-003 Traceability Reconciliation

READ-ONLY AUDIT.

Purpose:
  1. Discover the actual PB-DOC-020 document.
  2. Compare discovered identity/path with the canonical registry.
  3. Inspect PB-DOC-003 for TR-001..TR-009 evidence.
  4. Distinguish literal traceability from substantive architectural evidence.
  5. Produce a reconciliation report.

This tool NEVER:
  - modifies documentation;
  - modifies manifests;
  - modifies the Gap Register;
  - closes findings;
  - grants architecture approval;
  - grants implementation authorization;
  - claims production certification.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = ROOT / "docs" / "phase-b"

PB003 = (
    DOC_ROOT
    / "identity-authority"
    / "LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md"
)

EXPECTED_PB020_PATH = (
    DOC_ROOT
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

TR_IDS = tuple(f"TR-{i:03d}" for i in range(1, 10))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def print_header(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def discover_pb020() -> list[Path]:
    """
    Discover likely PB-DOC-020 files without assuming the canonical path.
    """

    candidates: list[Path] = []

    for path in sorted(DOC_ROOT.rglob("*.md")):
        try:
            text = read(path)
        except OSError:
            continue

        lowered = text.lower()

        identity_match = bool(
            re.search(
                r"\bPB-DOC-020\b",
                text,
                re.IGNORECASE,
            )
        )

        master_manifest_match = (
            "phase-b master manifest" in lowered
            or "phase b master manifest" in lowered
        )

        if identity_match or master_manifest_match:
            candidates.append(path)

    return candidates


def extract_document_id(text: str) -> str | None:
    patterns = (
        r"^\s*(?:\*\*)?Document ID(?:\*\*)?\s*:\s*(.+?)\s*$",
        r"^\s*Document_ID\s*:\s*(.+?)\s*$",
    )

    for line in text.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()

    return None


def extract_governance(text: str) -> dict[str, str]:
    labels = (
        "Architecture Approval",
        "Implementation Authorization",
        "Production Implementation",
        "Production Certification",
    )

    result: dict[str, str] = {}

    for line in text.splitlines():
        for label in labels:
            pattern = (
                rf"^\s*(?:\*\*)?{re.escape(label)}"
                rf"(?:\*\*)?\s*:\s*(.+?)\s*$"
            )

            match = re.match(pattern, line, re.IGNORECASE)

            if match:
                result[label] = match.group(1).strip()

    return result


def line_context(
    text: str,
    pattern: str,
    radius: int = 2,
    limit: int = 6,
) -> list[tuple[int, str]]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines = text.splitlines()
    output: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    for index, line in enumerate(lines):
        if not regex.search(line):
            continue

        start = max(0, index - radius)
        end = min(len(lines), index + radius + 1)

        for position in range(start, end):
            item = (position + 1, lines[position].strip())

            if item in seen:
                continue

            seen.add(item)
            output.append(item)

        if len(output) >= limit * (radius * 2 + 1):
            break

    return output


def pb020_audit() -> int:
    print_header("PB-DOC-020 CANONICAL PATH RECONCILIATION")

    print(f"Expected registry path:")
    print(f"  {EXPECTED_PB020_PATH}")

    print()
    print(
        "Expected path exists:",
        "PASS" if EXPECTED_PB020_PATH.is_file() else "FAIL",
    )

    candidates = discover_pb020()

    print()
    print(f"Discovered PB-DOC-020/master-manifest candidates: {len(candidates)}")

    for path in candidates:
        print(f"  {path}")

        try:
            text = read(path)
        except OSError as exc:
            print(f"    READ ERROR: {exc}")
            continue

        document_id = extract_document_id(text)

        print(f"    Document ID: {document_id or 'NOT DETECTED'}")

        governance = extract_governance(text)

        for label in (
            "Architecture Approval",
            "Implementation Authorization",
            "Production Implementation",
            "Production Certification",
        ):
            print(
                f"    {label}: "
                f"{governance.get(label, 'NOT DETECTED')}"
            )

    if EXPECTED_PB020_PATH.is_file():
        return 0

    if len(candidates) == 1:
        print()
        print(
            "RECONCILIATION FINDING: "
            "A PB-DOC-020/master-manifest document exists, "
            "but the validator's canonical path does not resolve."
        )
        return 1

    if len(candidates) == 0:
        print()
        print(
            "RECONCILIATION FINDING: "
            "No PB-DOC-020/master-manifest document was discovered."
        )
        return 1

    print()
    print(
        "RECONCILIATION FINDING: "
        "Multiple possible PB-DOC-020/master-manifest documents exist."
    )
    return 1


def pb003_audit() -> int:
    print_header("PB-DOC-003 FOCUSED TRACEABILITY REVIEW")

    if not PB003.is_file():
        print(f"FAIL: PB-DOC-003 not found: {PB003}")
        return 1

    text = read(PB003)

    print(f"Canonical PB-DOC-003 path: {PB003}")
    print(f"Document ID: {extract_document_id(text) or 'NOT DETECTED'}")

    print()
    print("Governance:")

    governance = extract_governance(text)

    for label in (
        "Architecture Approval",
        "Implementation Authorization",
        "Production Implementation",
        "Production Certification",
    ):
        print(
            f"  {label}: "
            f"{governance.get(label, 'NOT DETECTED')}"
        )

    print()
    print("TR-001..TR-009 literal-reference audit:")

    missing: list[str] = []

    for tr_id in TR_IDS:
        references = line_context(
            text,
            rf"(?<![A-Z0-9]){re.escape(tr_id)}(?![A-Z0-9])",
            radius=2,
            limit=4,
        )

        if references:
            print(f"  {tr_id}: DIRECT")
            for line_number, line in references:
                print(f"    {line_number}: {line}")
        else:
            print(f"  {tr_id}: NO_LITERAL_REFERENCE")
            missing.append(tr_id)

    print()
    print("PB-DOC-003 substantive architecture evidence:")

    evidence_groups = {
        "Identity / Authority separation": (
            r"identity.*authority|authority.*identity",
        ),
        "Authority attenuation": (
            r"authority attenuation|attenuation",
        ),
        "Least privilege": (
            r"least privilege|least-privilege",
        ),
        "Delegation": (
            r"delegat",
        ),
        "Revocation / revalidation": (
            r"revocation|revalidation|revoked|expired",
        ),
        "Capability separation": (
            r"capability.*authorization|authorization.*capability",
        ),
        "Execution separation": (
            r"execution.*authorization|authorization.*execution",
        ),
        "Verification": (
            r"verification",
        ),
        "Provenance": (
            r"provenance",
        ),
        "Agent / Host boundary": (
            r"agent.*host|host.*agent",
        ),
        "Fail-closed": (
            r"fail-closed|fail closed|deny-by-default|deny by default",
        ),
        "Trust boundary": (
            r"trust boundary|trust-boundar",
        ),
    }

    evidence_count = 0

    for name, patterns in evidence_groups.items():
        matches: list[tuple[int, str]] = []

        for pattern in patterns:
            matches.extend(
                line_context(
                    text,
                    pattern,
                    radius=1,
                    limit=2,
                )
            )

        if matches:
            # De-duplicate.
            unique: list[tuple[int, str]] = []
            seen: set[tuple[int, str]] = set()

            for item in matches:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)

            print(f"  {name}: PRESENT")
            for line_number, line in unique[:3]:
                print(f"    {line_number}: {line}")

            evidence_count += 1
        else:
            print(f"  {name}: NOT_DETECTED")

    print()
    print("Internal requirement identifiers:")

    identifier_patterns = (
        r"\bCORE-[A-Z0-9_-]+-\d{1,4}\b",
        r"\bREQ-[A-Z0-9_-]+\b",
        r"\bIDENTITY-[A-Z0-9_-]+\b",
    )

    identifiers: set[str] = set()

    for pattern in identifier_patterns:
        identifiers.update(
            re.findall(pattern, text, re.IGNORECASE)
        )

    for identifier in sorted(identifiers):
        print(f"  {identifier}")

    print()
    print("Cross-document references from PB-DOC-003:")

    pb_refs = sorted(
        set(
            re.findall(
                r"\bPB-DOC-\d{3}\b",
                text,
                re.IGNORECASE,
            )
        )
    )

    for reference in pb_refs:
        print(f"  {reference}")

    if not pb_refs:
        print("  NONE")

    print()
    print("Focused interpretation:")
    print(
        f"  Literal TR references found: "
        f"{9 - len(missing)}/9"
    )
    print(
        f"  Substantive evidence groups detected: "
        f"{evidence_count}/{len(evidence_groups)}"
    )
    print(
        f"  Internal requirement identifiers detected: "
        f"{len(identifiers)}"
    )

    if missing:
        print(
            "  RESULT: PB-DOC-003 requires semantic traceability review "
            "for TR identifiers without literal references."
        )
    else:
        print(
            "  RESULT: PB-DOC-003 contains direct TR-001..TR-009 "
            "references."
        )

    return 0 if not missing else 1


def governance_safety() -> None:
    print_header("GOVERNANCE SAFETY")

    print("Architecture Approval        : PENDING")
    print("Implementation Authorization : NOT AUTHORIZED")
    print("Production Implementation   : BLOCKED")
    print("Production Certification    : NOT CLAIMED")

    print()
    print("READ-ONLY GUARANTEE")
    print("  No Phase-B document modified.")
    print("  No manifest modified.")
    print("  No Gap Register state modified.")
    print("  No governance state modified.")
    print("  No implementation authorization granted.")


def main() -> int:
    try:
        pb020_status = pb020_audit()
        pb003_status = pb003_audit()
        governance_safety()

        print_header("FINAL RECONCILIATION RESULT")

        if pb020_status == 0 and pb003_status == 0:
            print(
                "RESULT: RECONCILIATION PASS — "
                "PB-DOC-020 canonical path resolves and "
                "PB-DOC-003 contains direct TR traceability."
            )
            return 0

        if pb020_status != 0 and pb003_status != 0:
            print(
                "RESULT: REVIEW REQUIRED — "
                "PB-DOC-020 path reconciliation and "
                "PB-DOC-003 traceability require review."
            )
            return 1

        if pb020_status != 0:
            print(
                "RESULT: REVIEW REQUIRED — "
                "PB-DOC-020 canonical path requires reconciliation."
            )
            return 1

        print(
            "RESULT: REVIEW REQUIRED — "
            "PB-DOC-003 traceability requires semantic reconciliation."
        )
        return 1

    except Exception as exc:
        print(f"FATAL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

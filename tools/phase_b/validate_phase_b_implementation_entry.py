#!/usr/bin/env python3
"""
LYRION TRUE AGENTIC OS — Phase-B Implementation Entry Gate

Purpose
-------
Validate that Phase-B implementation may enter its authorized
implementation lifecycle after the separate human authorization
decision has been recorded.

This gate is intentionally distinct from the pre-authorization
Implementation Readiness Evidence Gate.

Security / governance properties
---------------------------------
- READ-ONLY
- FAIL-CLOSED
- DETERMINISTIC
- NON-PRIVILEGED
- NON-MUTATING
- DOES NOT GRANT AUTHORIZATION
- DOES NOT MODIFY GOVERNANCE STATE
- DOES NOT EXECUTE IMPLEMENTATION
- DOES NOT AUTHORIZE PRODUCTION
- DOES NOT CLAIM PRODUCTION CERTIFICATION

Required authoritative governance state
---------------------------------------
Architecture Approval        = APPROVED
Implementation Authorization = AUTHORIZED
Production Implementation    = BLOCKED
Production Certification     = NOT CLAIMED
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MASTER_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase-b"
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

EXPECTED_GOVERNANCE = {
    "Architecture Approval": "APPROVED",
    "Implementation Authorization": "AUTHORIZED",
    "Production Implementation": "BLOCKED",
    "Production Certification": "NOT CLAIMED",
}

GOVERNANCE_KEYS = tuple(EXPECTED_GOVERNANCE)

AUTHORIZATION_SECTION = "## Formal Implementation Authorization Decision"

AUTHORIZATION_REQUIRED_PATTERNS = (
    r"\*\*Decision:\*\*\s*AUTHORIZE",
    r"\*\*Reviewer:\*\*\s*[^\r\n]+",
    r"\*\*Review Reference:\*\*\s*[A-Za-z0-9][A-Za-z0-9._:-]{0,199}",
    r"\*\*Decision Timestamp UTC:\*\*\s*"
    r"\d{4}-\d{2}-\d{2}T"
    r"\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2}",
    r"\*\*Evidence Baseline:\*\*\s*"
    r"READY_FOR_FORMAL_IMPLEMENTATION_AUTHORIZATION_REVIEW",
    r"\*\*Architecture Approval:\*\*\s*APPROVED",
    r"\*\*Implementation Authorization:\*\*\s*AUTHORIZED",
    r"\*\*Production Implementation:\*\*\s*BLOCKED",
    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
    r"\*\*Implementation Executed:\*\*\s*NO",
    r"\*\*Privileged Execution:\*\*\s*NONE",
    r"\*\*Authorization Mechanism:\*\*\s*Explicit human governance decision",
    r"\*\*Pre-Decision Master Manifest SHA256:\*\*\s*"
    r"[0-9a-f]{64}",
    r"\*\*Governance Rule:\*\*\s*Implementation authorization does not "
    r"authorize production operation or certification\.",
)


class ImplementationEntryError(RuntimeError):
    """Raised when implementation-entry validation cannot safely complete."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ImplementationEntryError(
            f"FAIL_CLOSED:HASH_READ_FAILED:{path}:{exc}"
        ) from exc

    return digest.hexdigest()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ImplementationEntryError(
            f"FAIL_CLOSED:MISSING_REQUIRED_FILE:{label}:{path}"
        )


def read_text(path: Path, label: str) -> str:
    require_file(path, label)

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ImplementationEntryError(
            f"FAIL_CLOSED:UNREADABLE_REQUIRED_FILE:{label}:{exc}"
        ) from exc


def parse_authoritative_governance(text: str) -> dict[str, str]:
    """
    Parse ONLY the authoritative governance table.

    Historical decision records and prose cannot override the
    authoritative current-state table.
    """
    table_pattern = re.compile(
        r"^\|\s*Control\s*\|\s*State\s*\|\s*$"
        r".*?"
        r"^\|\s*---+\s*\|\s*---+\s*\|\s*$"
        r"(?P<body>.*?)(?=^\s*$|^#)",
        re.MULTILINE | re.DOTALL,
    )

    match = table_pattern.search(text)

    if not match:
        raise ImplementationEntryError(
            "FAIL_CLOSED:MISSING_AUTHORITATIVE_GOVERNANCE_TABLE"
        )

    states: dict[str, str] = {}

    row_pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$",
        re.MULTILINE,
    )

    for row in row_pattern.finditer(match.group("body")):
        key = row.group(1).strip()
        value = row.group(2).strip()

        if key in EXPECTED_GOVERNANCE:
            if key in states:
                raise ImplementationEntryError(
                    f"FAIL_CLOSED:DUPLICATE_GOVERNANCE_STATE:{key}"
                )

            states[key] = value

    missing = [
        key for key in EXPECTED_GOVERNANCE if key not in states
    ]

    if missing:
        raise ImplementationEntryError(
            "FAIL_CLOSED:MISSING_GOVERNANCE_STATE:"
            + ",".join(missing)
        )

    return states


def verify_manifest_identity(text: str) -> None:
    required = (
        r"\*\*Document ID:\*\*\s*TAOS-PHASE-B-MANIFEST-001",
        r"\*\*Version:\*\*\s*1\.0\.0",
        r"\*\*Project:\*\*\s*LYRION True Agentic OS",
        r"\*\*Phase:\*\*\s*Phase B",
    )

    for pattern in required:
        if not re.search(pattern, text):
            raise ImplementationEntryError(
                "FAIL_CLOSED:MASTER_MANIFEST_IDENTITY_MISMATCH:"
                + pattern
            )


def verify_governance(text: str) -> dict[str, str]:
    states = parse_authoritative_governance(text)

    for key, expected in EXPECTED_GOVERNANCE.items():
        actual = states[key]

        if actual != expected:
            raise ImplementationEntryError(
                "GOVERNANCE_STATE_MISMATCH:"
                f"{key}:expected={expected}:actual={actual}"
            )

        print(f"PASS: {key} = {actual}")

    return states


def extract_latest_authorization_record(text: str) -> str:
    """
    Select the latest formal implementation-authorization record.

    Historical architecture-approval records are deliberately not
    rewritten and therefore may contain the previous authorization
    state. The latest formal authorization record is the current
    provenance record for the authorization transition.
    """
    positions = [
        match.start()
        for match in re.finditer(
            re.escape(AUTHORIZATION_SECTION),
            text,
        )
    ]

    if not positions:
        raise ImplementationEntryError(
            "FAIL_CLOSED:MISSING_FORMAL_IMPLEMENTATION_AUTHORIZATION_RECORD"
        )

    return text[positions[-1] :]


def verify_authorization_record(text: str) -> None:
    record = extract_latest_authorization_record(text)

    for pattern in AUTHORIZATION_REQUIRED_PATTERNS:
        if not re.search(pattern, record):
            raise ImplementationEntryError(
                "FAIL_CLOSED:INVALID_FORMAL_AUTHORIZATION_RECORD:"
                + pattern
            )

    print("PASS: formal implementation authorization record")
    print("PASS: human authorization decision = AUTHORIZE")
    print("PASS: authorization provenance present")
    print("PASS: implementation execution = NO")
    print("PASS: privileged execution = NONE")


def verify_no_production_authority(text: str) -> None:
    states = parse_authoritative_governance(text)

    if states["Production Implementation"] != "BLOCKED":
        raise ImplementationEntryError(
            "FAIL_CLOSED:PRODUCTION_IMPLEMENTATION_NOT_BLOCKED"
        )

    if states["Production Certification"] != "NOT CLAIMED":
        raise ImplementationEntryError(
            "FAIL_CLOSED:PRODUCTION_CERTIFICATION_STATE_INVALID"
        )

    print("PASS: production implementation remains BLOCKED")
    print("PASS: production certification remains NOT CLAIMED")


def verify_read_only_contract() -> None:
    source = Path(__file__).read_text(encoding="utf-8")

    import ast

    try:
        tree = ast.parse(source, filename=str(Path(__file__)))
    except SyntaxError as exc:
        raise ImplementationEntryError(
            f"FAIL_CLOSED:READ_ONLY_AST_PARSE_FAILED:{exc}"
        ) from exc

    forbidden_calls = {
        "os.system",
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "os.execv",
        "os.execve",
        "os.execl",
        "os.execlp",
        "os.execle",
        "os.execvp",
        "os.execvpe",
        "os.remove",
        "os.unlink",
        "shutil.copy",
        "shutil.copy2",
        "shutil.copyfile",
        "shutil.move",
        "Path.unlink",
        "Path.rename",
        "Path.replace",
        "Path.write_text",
        "Path.write_bytes",
    }

    def qualified_name(node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call):
            return None

        function = node.func

        if isinstance(function, ast.Attribute):
            if isinstance(function.value, ast.Name):
                return f"{function.value.id}.{function.attr}"

            if (
                isinstance(function.value, ast.Name)
                and function.value.id == "Path"
            ):
                return f"Path.{function.attr}"

        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = qualified_name(node)

        if name in forbidden_calls:
            raise ImplementationEntryError(
                "FAIL_CLOSED:READ_ONLY_FORBIDDEN_CALL:"
                f"{name}:line={node.lineno}"
            )

    print("PASS: read-only implementation-entry contract")


def verify_manifest_unchanged(
    manifest: Path,
    before_hash: str,
) -> None:
    after_hash = sha256(manifest)

    if before_hash != after_hash:
        raise ImplementationEntryError(
            "FAIL_CLOSED:MASTER_MANIFEST_MUTATED_DURING_VALIDATION"
        )

    print("PASS: Master Manifest unchanged")
    print(f"Master Manifest SHA256: {after_hash}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate authorized Phase-B implementation-entry state "
            "without granting authority or mutating governance."
        )
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MASTER_MANIFEST,
        help="Phase-B Master Manifest to validate.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    manifest = args.manifest.resolve()

    print("=" * 108)
    print(
        "LYRION TRUE AGENTIC OS — "
        "PHASE-B IMPLEMENTATION ENTRY GATE"
    )
    print("=" * 108)
    print(f"Repository: {REPO_ROOT}")
    print(f"Manifest:   {manifest}")
    print("Mode: READ-ONLY")
    print("Authority: Implementation-entry validation only")
    print()

    try:
        verify_read_only_contract()

        manifest_text = read_text(
            manifest,
            "Phase-B Master Manifest",
        )

        before_hash = sha256(manifest)

        print("===== MASTER MANIFEST =====")
        verify_manifest_identity(manifest_text)

        print("PASS: Master Manifest identity")

        print()
        print("===== AUTHORITATIVE GOVERNANCE =====")
        verify_governance(manifest_text)

        print()
        print("===== FORMAL AUTHORIZATION PROVENANCE =====")
        verify_authorization_record(manifest_text)

        print()
        print("===== PRODUCTION BOUNDARY =====")
        verify_no_production_authority(manifest_text)

        verify_manifest_unchanged(
            manifest,
            before_hash,
        )

        print()
        print("=" * 108)
        print("IMPLEMENTATION ENTRY DECISION")
        print("=" * 108)

        print("Architecture Approval        : APPROVED")
        print("Implementation Authorization : AUTHORIZED")
        print("Production Implementation    : BLOCKED")
        print("Production Certification     : NOT CLAIMED")
        print()
        print(
            "IMPLEMENTATION ENTRY DECISION: "
            "READY_FOR_PHASE_B_IMPLEMENTATION"
        )
        print()
        print("AUTHORIZATION GRANT: NONE")
        print("GOVERNANCE MUTATION: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        print("IMPLEMENTATION EXECUTION: NONE")
        print()
        print(
            "IMPORTANT: This gate validates an existing authorization "
            "decision."
        )
        print(
            "It does NOT grant implementation authorization."
        )
        print(
            "It does NOT authorize production operation."
        )
        print(
            "It does NOT claim production certification."
        )
        print()
        print(
            "RESULT: PASS — IMPLEMENTATION ENTRY VALIDATION COMPLETED"
        )

        return 0

    except ImplementationEntryError as exc:
        print()
        print("=" * 108)
        print("IMPLEMENTATION ENTRY DECISION")
        print("=" * 108)
        print("IMPLEMENTATION ENTRY DECISION: FAIL_CLOSED")
        print(f"REASON: {exc}")
        print("AUTHORIZATION GRANT: NONE")
        print("GOVERNANCE MUTATION: NONE")
        print("PRIVILEGED EXECUTION: NONE")
        print("IMPLEMENTATION EXECUTION: NONE")
        print("RESULT: FAIL")
        return 2


if __name__ == "__main__":
    sys.exit(main())

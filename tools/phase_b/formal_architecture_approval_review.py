#!/usr/bin/env python3
"""
LYRION True Agentic OS
Phase-B Formal Architecture Approval Review

Purpose:
    Perform a read-only governance review of the Phase-B architecture
    approval evidence.

Safety:
    - Does not modify Phase-B architecture documents.
    - Does not modify the Master Manifest.
    - Does not authorize implementation.
    - Does not grant production status.
    - Does not grant certification.
    - Does not silently change governance state.

Decision semantics:
    PASS / OPEN / BLOCKING are evidence states only.

    READY_FOR_FORMAL_DECISION means the evidence package satisfies the
    review checks implemented here. It is NOT Architecture Approval.

    Architecture Approval remains a separate human/governance decision.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path.cwd()
DOC_ROOT = ROOT / "docs" / "phase-b"

MASTER_MANIFEST = (
    DOC_ROOT
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md"
)

GAP_REGISTER = (
    DOC_ROOT
    / "governance"
    / "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md"
)

TRACEABILITY = (
    DOC_ROOT
    / "requirements"
    / "LYRION_CORE_PRD_TRACEABILITY_ACCEPTANCE_MATRIX_v1.md"
)


CANONICAL_DOCUMENTS = {
    "PB-DOC-001": DOC_ROOT
    / "requirements/LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md",
    "PB-DOC-002": DOC_ROOT
    / "agentic-runtime/LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",
    "PB-DOC-003": DOC_ROOT
    / "identity-authority/LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",
    "PB-DOC-004": DOC_ROOT
    / "capability/LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",
    "PB-DOC-005": DOC_ROOT
    / "agent-harness/LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-006": DOC_ROOT
    / "host-harness/LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-007": DOC_ROOT
    / "universal-computer/LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",
    "PB-DOC-008": DOC_ROOT
    / "application-harness/LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-009": DOC_ROOT
    / "execution-admission/LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
    "PB-DOC-010": DOC_ROOT
    / "aegis/LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",
    "PB-DOC-011": DOC_ROOT
    / "secure-execution/LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",
    "PB-DOC-012": DOC_ROOT
    / "interfaces/LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",
    "PB-DOC-013": DOC_ROOT
    / "data/LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",
    "PB-DOC-014": DOC_ROOT
    / "memory/LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",
    "PB-DOC-015": DOC_ROOT
    / "observability/LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",
    "PB-DOC-016": DOC_ROOT
    / "validation/LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",
    "PB-DOC-017": DOC_ROOT
    / "security-testing/LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",
    "PB-DOC-018": DOC_ROOT
    / "operations/LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",
    "PB-DOC-019": DOC_ROOT
    / "recovery/LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",
    "PB-DOC-020": MASTER_MANIFEST,
}


EXPECTED_GLOBAL_GOVERNANCE = {
    "Architecture Approval": "PENDING",
    "Implementation Authorization": "NOT AUTHORIZED",
    "Production Implementation": "BLOCKED",
    "Production Certification": "NOT CLAIMED",
}


REQUIRED_SECURITY_CONCEPTS = (
    "fail-closed",
    "provenance",
    "audit",
    "least privilege",
)


REQUIRED_SECURITY_BOUNDARIES = (
    "Capability Gateway",
    "Execution Admission",
    "Secure Executor",
    "Aegis",
    "Agent Sandbox",
    "LHICF",
    "Universal Computer",
    "Application Harness",
    "Host Harness",
)


REQUIRED_TRACEABILITY = tuple(
    f"TR-{index:03d}" for index in range(1, 10)
)


@dataclass(frozen=True)
class Finding:
    status: str
    category: str
    message: str


class Review:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def pass_(self, category: str, message: str) -> None:
        self.findings.append(
            Finding("PASS", category, message)
        )

    def open(self, category: str, message: str) -> None:
        self.findings.append(
            Finding("OPEN", category, message)
        )

    def block(self, category: str, message: str) -> None:
        self.findings.append(
            Finding("BLOCKING", category, message)
        )

    @staticmethod
    def read(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    @staticmethod
    def contains(text: str, pattern: str) -> bool:
        return re.search(
            pattern,
            text,
            flags=re.IGNORECASE | re.MULTILINE,
        ) is not None

    def review_document_registry(self) -> dict[str, str]:
        corpus: dict[str, str] = {}

        for doc_id, path in sorted(CANONICAL_DOCUMENTS.items()):
            if not path.is_file():
                self.block(
                    "Documentation Registry",
                    f"{doc_id}: canonical document missing: {path}",
                )
                continue

            text = self.read(path)

            if text is None:
                self.block(
                    "Documentation Registry",
                    f"{doc_id}: canonical document unreadable: {path}",
                )
                continue

            corpus[doc_id] = text

            self.pass_(
                "Documentation Registry",
                f"{doc_id}: canonical document present",
            )

            document_id = re.search(
                r"^\s*\*\*Document ID:\*\*\s*([^\r\n]+)",
                text,
                flags=re.MULTILINE,
            )

            if document_id and document_id.group(1).strip():
                self.pass_(
                    "Document Identity",
                    f"{doc_id}: non-empty Document ID present",
                )
            else:
                self.block(
                    "Document Identity",
                    f"{doc_id}: Document ID missing or empty",
                )

        if len(corpus) == len(CANONICAL_DOCUMENTS):
            self.pass_(
                "Documentation Registry",
                "PB-DOC-001 through PB-DOC-020 resolved",
            )

        return corpus

    def review_global_governance(self, manifest: str) -> None:
        for field, expected in EXPECTED_GLOBAL_GOVERNANCE.items():
            pattern = (
                rf"\*\*{re.escape(field)}:\*\*\s*"
                rf"{re.escape(expected)}"
            )

            if self.contains(manifest, pattern):
                self.pass_(
                    "Governance",
                    f"{field} = {expected}",
                )
            else:
                self.block(
                    "Governance",
                    f"{field} is not explicitly {expected}",
                )

    def review_security(self, corpus: dict[str, str]) -> None:
        combined = "\n".join(corpus.values())

        for concept in REQUIRED_SECURITY_CONCEPTS:
            if self.contains(combined, re.escape(concept)):
                self.pass_(
                    "Security Architecture",
                    f"Required security concept present: {concept}",
                )
            else:
                self.block(
                    "Security Architecture",
                    f"Required security concept missing: {concept}",
                )

        invariants = (
            r"capability\s*[≠!=]\s*authority",
            r"authority\s*[≠!=]\s*authorization",
            r"authorization\s*[≠!=]\s*execution",
            r"execution\s*[≠!=]\s*verification",
        )

        for invariant in invariants:
            if self.contains(combined, invariant):
                self.pass_(
                    "Security Separation",
                    f"Invariant present: {invariant}",
                )
            else:
                self.block(
                    "Security Separation",
                    f"Invariant missing: {invariant}",
                )

        for boundary in REQUIRED_SECURITY_BOUNDARIES:
            if self.contains(combined, re.escape(boundary)):
                self.pass_(
                    "Privileged Boundaries",
                    f"Boundary represented: {boundary}",
                )
            else:
                self.block(
                    "Privileged Boundaries",
                    f"Boundary missing: {boundary}",
                )

    def review_forbidden_shortcuts(
        self,
        corpus: dict[str, str],
    ) -> None:
        """
        Detect actual authorization-grant assertions without treating
        security prohibitions as violations.

        Examples that MUST remain safe:

            Model output does not grant authorization.
            Model output cannot grant authorization.
            Model output never grants authorization.
            Model output is not authorization.

        Examples that MUST be detected:

            Model output grants authorization.
            Model output authorizes execution.
        """

        combined = "\n".join(corpus.values())

        rules = (
            (
                "model output grants authorization",
                re.compile(
                    r"\\bmodel\\s+output\\b"
                    r"(?:(?![.!?]).){0,120}?"
                    r"\\bgrants?\\s+authorization\\b",
                    re.IGNORECASE,
                ),
            ),
            (
                "model output is authorization",
                re.compile(
                    r"\\bmodel\\s+output\\b"
                    r"(?:(?![.!?]).){0,80}?"
                    r"\\bis\\s+(?:the\\s+)?authorization\\b",
                    re.IGNORECASE,
                ),
            ),
            (
                "capability discovery grants authorization",
                re.compile(
                    r"\\bcapability\\s+discovery\\b"
                    r"(?:(?![.!?]).){0,100}?"
                    r"\\bgrants?\\s+authorization\\b",
                    re.IGNORECASE,
                ),
            ),
            (
                "interface grants authority",
                re.compile(
                    r"\\binterface\\b"
                    r"(?:(?![.!?]).){0,100}?"
                    r"\\bgrants?\\s+authority\\b",
                    re.IGNORECASE,
                ),
            ),
            (
                "message grants authority",
                re.compile(
                    r"\\bmessage\\b"
                    r"(?:(?![.!?]).){0,100}?"
                    r"\\bgrants?\\s+authority\\b",
                    re.IGNORECASE,
                ),
            ),
            (
                "agent request grants authority",
                re.compile(
                    r"\\bagent\\s+request\\b"
                    r"(?:(?![.!?]).){0,100}?"
                    r"\\bgrants?\\s+authority\\b",
                    re.IGNORECASE,
                ),
            ),
            (
                "tool discovery grants authorization",
                re.compile(
                    r"\\btool\\s+discovery\\b"
                    r"(?:(?![.!?]).){0,100}?"
                    r"\\bgrants?\\s+authorization\\b",
                    re.IGNORECASE,
                ),
            ),
        )

        # Explicit negation immediately before the authorization assertion
        # is treated as a security prohibition, not a shortcut.
        negation = re.compile(
            r"\\b(?:does\\s+not|do\\s+not|cannot|can\\s+not|"
            r"never|is\\s+not|isn't|is\\s+never)\\b",
            re.IGNORECASE,
        )

        for description, pattern in rules:
            violation = False

            for match in pattern.finditer(combined):
                context_start = max(0, match.start() - 120)
                context = combined[context_start:match.start()]

                if negation.search(context):
                    continue

                violation = True
                break

            if violation:
                self.block(
                    "Authorization Safety",
                    f"Forbidden authorization shortcut detected: {description}",
                )
            else:
                self.pass_(
                    "Authorization Safety",
                    f"Forbidden authorization shortcut absent: {description}",
                )

    def review_traceability(self, corpus: dict[str, str]) -> None:
        combined = "\n".join(corpus.values())

        for trace_id in REQUIRED_TRACEABILITY:
            if self.contains(combined, rf"\b{trace_id}\b"):
                self.pass_(
                    "Traceability",
                    f"{trace_id}: reference present",
                )
            else:
                self.block(
                    "Traceability",
                    f"{trace_id}: reference missing",
                )

    def review_gap_register(self) -> None:
        """
        Evaluate the structured Markdown gap-register rows.

        The register may contain historical/reconciliation sections that
        legitimately contain words such as CRITICAL and OPEN. Those textual
        references are not themselves current gap state.

        For each PB-DOC entry, the LAST structured table row is treated as
        the current recorded state. This prevents historical snapshots from
        becoming false blocking findings.

        A blocking finding is emitted only when the latest row for a
        document explicitly contains:

            Severity = CRITICAL
            State = OPEN

        All other states remain non-blocking unless another review check
        independently establishes a blocking condition.
        """

        if not GAP_REGISTER.is_file():
            self.block(
                "Gap Register",
                f"Gap Register missing: {GAP_REGISTER}",
            )
            return

        text = self.read(GAP_REGISTER)

        if text is None:
            self.block(
                "Gap Register",
                "Gap Register could not be read",
            )
            return

        self.pass_(
            "Gap Register",
            "Phase-B documentation Gap Register present",
        )

        # Structured Markdown rows:
        # | PB-DOC-001 | Description | SEVERITY | STATE |
        row_pattern = re.compile(
            r"^\|\s*"
            r"(PB-DOC-\d{3})"
            r"\s*\|\s*"
            r"([^|]*)"
            r"\|\s*"
            r"([^|]*)"
            r"\|\s*"
            r"([^|]*)"
            r"\|\s*$",
            re.IGNORECASE | re.MULTILINE,
        )

        latest_rows: dict[str, tuple[str, str, str]] = {}

        for match in row_pattern.finditer(text):
            doc_id = match.group(1).upper()
            description = match.group(2).strip()
            severity = match.group(3).strip().upper()
            state = match.group(4).strip().upper()

            latest_rows[doc_id] = (
                description,
                severity,
                state,
            )

        if not latest_rows:
            self.block(
                "Gap Register",
                "No structured PB-DOC gap-register rows could be parsed",
            )
            return

        blocking = []

        for doc_id in sorted(latest_rows):
            description, severity, state = latest_rows[doc_id]

            if severity == "CRITICAL" and re.fullmatch(
                r"OPEN(?:\s*[-—].*)?",
                state,
            ):
                blocking.append(doc_id)
                continue

            self.pass_(
                "Gap Register",
                f"{doc_id}: latest structured state is "
                f"{severity} / {state}",
            )

        if blocking:
            self.block(
                "Gap Register",
                "Current structured CRITICAL OPEN gap(s): "
                + ", ".join(blocking),
            )
        else:
            self.pass_(
                "Gap Register",
                "No current structured CRITICAL OPEN documentation gap detected",
            )

    def review_traceability_file(self) -> None:
        if TRACEABILITY.is_file():
            self.pass_(
                "Traceability Matrix",
                "PRD traceability matrix present",
            )
        else:
            self.block(
                "Traceability Matrix",
                f"Traceability matrix missing: {TRACEABILITY}",
            )

    def review_manifest_reference_state(
        self,
        manifest: str,
    ) -> None:
        referenced = set(
            re.findall(
                r"\bPB-DOC-\d{3}\b",
                manifest,
            )
        )

        expected = set(CANONICAL_DOCUMENTS)

        missing = sorted(expected - referenced)

        if not missing:
            self.pass_(
                "Master Manifest Registry",
                "Manifest references all canonical PB-DOC entries",
            )
            return

        # These are explicitly non-blocking here because the current
        # reconciliation validator already classified the same findings
        # as OPEN / NON-BLOCKING. They must not be silently converted into
        # approval blockers.
        for doc_id in missing:
            self.open(
                "Master Manifest Registry",
                f"Manifest textual registry reference absent: {doc_id}",
            )

    def run(self) -> int:
        print("=" * 76)
        print("LYRION TRUE AGENTIC OS — FORMAL PHASE-B ARCHITECTURE REVIEW")
        print("=" * 76)
        print(f"Repository: {ROOT}")
        print(f"Documentation root: {DOC_ROOT}")
        print()

        corpus = self.review_document_registry()

        manifest = corpus.get("PB-DOC-020")

        if manifest is None:
            self.block(
                "Master Manifest",
                "PB-DOC-020 Master Manifest unavailable",
            )
        else:
            self.review_global_governance(manifest)
            self.review_manifest_reference_state(manifest)

        self.review_security(corpus)
        self.review_forbidden_shortcuts(corpus)
        self.review_traceability(corpus)
        self.review_gap_register()
        self.review_traceability_file()

        print()
        print("REVIEW FINDINGS")
        print("-" * 76)

        for finding in self.findings:
            print(
                f"{finding.status}: "
                f"{finding.category}: "
                f"{finding.message}"
            )

        blocking = [
            item for item in self.findings
            if item.status == "BLOCKING"
        ]

        opens = [
            item for item in self.findings
            if item.status == "OPEN"
        ]

        print()
        print("=" * 76)

        if blocking:
            print("RESULT: BLOCKED — FORMAL APPROVAL NOT READY")
            print(f"Blocking findings: {len(blocking)}")
        else:
            print("RESULT: READY FOR FORMAL GOVERNANCE DECISION")
            print(f"Non-blocking OPEN findings: {len(opens)}")

        print("ARCHITECTURE APPROVAL: PENDING")
        print("IMPLEMENTATION AUTHORIZATION: NOT AUTHORIZED")
        print("PRODUCTION IMPLEMENTATION: BLOCKED")
        print("PRODUCTION CERTIFICATION: NOT CLAIMED")
        print("=" * 76)

        # IMPORTANT:
        # This tool can NEVER return a governance approval.
        # Exit 0 means only that the evidence package is ready for a
        # separate formal governance decision.
        return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(Review().run())

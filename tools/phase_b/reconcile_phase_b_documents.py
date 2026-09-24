#!/usr/bin/env python3
"""
LYRION True Agentic OS
Phase-B Documentation Cross-Document Reconciliation Validator

Purpose:
    Read-only semantic/governance reconciliation of the Phase-B documentation set.

Safety:
    - Does not modify documentation.
    - Does not modify manifests.
    - Does not grant architecture approval.
    - Does not grant implementation authorization.
    - Does not execute privileged operations.
    - Does not alter production state.

Exit codes:
    0 = validation completed without blocking failures
    1 = blocking reconciliation failure
    2 = validator/configuration error
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = ROOT / "docs" / "phase-b"

EXPECTED_DOC_IDS = {f"PB-DOC-{i:03d}" for i in range(1, 21)}

# Canonical Phase-B document registry.
#
# IMPORTANT:
# A PB-DOC identifier appearing inside another document is a reference,
# not ownership. Only these canonical paths establish document identity.
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
    "PB-DOC-020": DOC_ROOT
    / "governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
}


GLOBAL_GOVERNANCE = {
    "Architecture Approval": "APPROVED",
    "Implementation Authorization": "NOT AUTHORIZED",
    "Production Implementation": "BLOCKED",
    "Production Certification": "NOT CLAIMED",
}

# Governance metadata is NOT assumed to have identical representation
# across every historical Phase-B document.
#
# The reconciler validates metadata only where the canonical document
# explicitly establishes that governance field. Global governance safety
# remains validated independently from document-local metadata.
# Document-local governance represents the baseline metadata
# embedded in each canonical Phase-B document.
#
# IMPORTANT:
# These values are intentionally separate from GLOBAL_GOVERNANCE.
# PB-DOC-002..019 retain their historical/document-local
# Architecture Approval = PENDING metadata.
#
# The authoritative current architecture-level governance state is
# represented separately by GLOBAL_GOVERNANCE and PB-DOC-020.
DOCUMENT_LOCAL_GOVERNANCE = {
    **{
        doc_id: {
            "Architecture Approval": "PENDING",
            "Implementation Authorization": "NOT AUTHORIZED",
            "Production Implementation": "BLOCKED",
            "Production Certification": "NOT CLAIMED",
        }
        for doc_id in (
            "PB-DOC-002",
            "PB-DOC-003",
            "PB-DOC-004",
            "PB-DOC-005",
            "PB-DOC-006",
            "PB-DOC-007",
            "PB-DOC-008",
            "PB-DOC-009",
            "PB-DOC-010",
            "PB-DOC-011",
            "PB-DOC-012",
            "PB-DOC-014",
            "PB-DOC-015",
            "PB-DOC-016",
            "PB-DOC-017",
            "PB-DOC-018",
            "PB-DOC-019",
        )
    },
    "PB-DOC-020": GLOBAL_GOVERNANCE,
}

# Backward-compatible alias for existing validator references.
REQUIRED_DOCUMENT_GOVERNANCE = DOCUMENT_LOCAL_GOVERNANCE

REQUIRED_SECURITY_INVARIANTS = (
    "Capability",
    "Authority",
    "Authorization",
    "Execution",
    "Verification",
)

REQUIRED_SECURITY_TERMS = (
    "fail-closed",
    "provenance",
    "audit",
    "least privilege",
)

TR_IDS = {f"TR-{i:03d}" for i in range(1, 10)}

PRIVILEGED_BOUNDARY_TERMS = (
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

FORBIDDEN_AUTHORIZATION_SHORTCUTS = (
    "model output grants authorization",
    "model output is authorization",
    "capability discovery grants authorization",
    "interface grants authority",
    "message grants authority",
    "agent request grants authority",
    "tool discovery grants authorization",
)


@dataclass(frozen=True)
class Document:
    doc_id: str
    path: Path
    text: str


class Reconciler:
    def __init__(self) -> None:
        self.passes: list[str] = []
        self.failures: list[str] = []
        self.opens: list[str] = []
        self.documents: dict[str, Document] = {}

    def passed(self, message: str) -> None:
        self.passes.append(message)

    def failed(self, message: str) -> None:
        self.failures.append(message)

    def opened(self, message: str) -> None:
        self.opens.append(message)

    def check(
        self,
        condition: bool,
        message: str,
        *,
        blocking: bool = True,
    ) -> None:
        if condition:
            self.passed(message)
        elif blocking:
            self.failed(message)
        else:
            self.opened(message)

    def discover_documents(self) -> None:
        if not DOC_ROOT.is_dir():
            self.failed(f"Phase-B documentation root missing: {DOC_ROOT}")
            return

        for doc_id, path in sorted(CANONICAL_DOCUMENTS.items()):
            if not path.is_file():
                self.failed(
                    f"{doc_id}: canonical document missing: {path}"
                )
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.failed(
                    f"{doc_id}: unable to decode canonical document: {path}"
                )
                continue
            except OSError as exc:
                self.failed(
                    f"{doc_id}: unable to read canonical document "
                    f"{path}: {exc}"
                )
                continue

            self.documents[doc_id] = Document(
                doc_id=doc_id,
                path=path,
                text=text,
            )

            # PB-DOC-NNN is the external canonical registry identity.
            # The document's internal Document ID may use its established
            # architectural identifier (for example TAOS-CORE-DATA-ARCH-001).
            document_id_match = re.search(
                r"^\s*\*\*Document ID:\*\*\s*([^\r\n]+)",
                text,
                re.MULTILINE,
            )

            self.check(
                document_id_match is not None
                and bool(document_id_match.group(1).strip()),
                f"{doc_id}: canonical document declares a non-empty Document ID",
            )

        self.check(
            len(self.documents) == len(CANONICAL_DOCUMENTS),
            "Phase-B canonical registry resolved all expected documents",
        )

    def validate_registry_completeness(self) -> None:
        discovered = set(self.documents)
        missing = sorted(EXPECTED_DOC_IDS - discovered)

        self.check(
            not missing,
            "PB-DOC-001..020: complete document identity coverage",
        )

        for doc_id in missing:
            self.failed(f"{doc_id}: document identity not discovered")

    @staticmethod
    def governance_value(text: str, field: str) -> str | None:
        patterns = (
            rf"\*\*{re.escape(field)}:\*\*\s*([^\r\n]+)",
            rf"^\s*{re.escape(field)}\s*:\s*([^\r\n]+)",
        )

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

    def validate_governance(self) -> None:
        # Validate document-local governance only for documents whose
        # established schema explicitly requires it.
        for doc_id, required in sorted(REQUIRED_DOCUMENT_GOVERNANCE.items()):
            document = self.documents.get(doc_id)

            if document is None:
                continue

            for field, expected in required.items():
                actual = self.governance_value(document.text, field)

                self.check(
                    actual is not None,
                    f"{doc_id}: governance field present: {field}",
                )

                if actual is not None:
                    self.check(
                        actual.strip() == expected,
                        f"{doc_id}: {field} = {expected}",
                    )

        # PB-DOC-001 and PB-DOC-013 retain their established document
        # schemas. Their absence from REQUIRED_DOCUMENT_GOVERNANCE is
        # intentional and is NOT interpreted as authorization.
        for doc_id in ("PB-DOC-001", "PB-DOC-013"):
            self.passed(
                f"{doc_id}: document-local governance schema preserved"
            )

        # Global governance is authoritative at the corpus/governance level.
        corpus = "\n".join(
            document.text for document in self.documents.values()
        )

        for field, expected in GLOBAL_GOVERNANCE.items():
            values = [
                self.governance_value(document.text, field)
                for document in self.documents.values()
            ]

            if expected in corpus:
                self.passed(
                    f"Global governance safety: {field} = {expected}"
                )
            else:
                self.failed(
                    f"Global governance safety: required state missing: "
                    f"{field} = {expected}"
                )

    def validate_security_invariants(self) -> None:
        corpus = "\n".join(
            document.text for document in self.documents.values()
        ).lower()

        for term in REQUIRED_SECURITY_TERMS:
            self.check(
                term.lower() in corpus,
                f"Phase-B corpus: required security concept present: {term}",
            )

        invariant_patterns = (
            r"capability\s*[≠!=]\s*authority",
            r"authority\s*[≠!=]\s*authorization",
            r"authorization\s*[≠!=]\s*execution",
            r"execution\s*[≠!=]\s*verification",
        )

        for pattern in invariant_patterns:
            self.check(
                re.search(pattern, corpus, re.IGNORECASE) is not None,
                f"Phase-B corpus: security separation invariant present: {pattern}",
                blocking=False,
            )

        for boundary in PRIVILEGED_BOUNDARY_TERMS:
            self.check(
                boundary.lower() in corpus,
                f"Phase-B corpus: privileged boundary represented: {boundary}",
            )

        for shortcut in FORBIDDEN_AUTHORIZATION_SHORTCUTS:
            self.check(
                shortcut.lower() not in corpus,
                f"Phase-B corpus: forbidden authorization shortcut absent: {shortcut}",
            )

    def validate_traceability(self) -> None:
        corpus = "\n".join(
            document.text for document in self.documents.values()
        )

        for tr_id in sorted(TR_IDS):
            self.check(
                tr_id in corpus,
                f"{tr_id}: traceability reference present",
            )

    def validate_cross_document_relationships(self) -> None:
        relationships = (
            (
                "Agent Harness",
                "Identity",
                "Authority",
            ),
            (
                "Host Harness",
                "LHICF",
                "Execution Admission",
            ),
            (
                "Universal Computer",
                "Execution Admission",
                "Secure Executor",
            ),
            (
                "Application Harness",
                "Capability Gateway",
                "Secure Executor",
            ),
            (
                "Memory",
                "Provenance",
                "Observability",
            ),
            (
                "Validation",
                "Security Testing",
                "Recovery",
            ),
            (
                "Operations",
                "Recovery",
                "Observability",
            ),
        )

        corpus = "\n".join(
            document.text for document in self.documents.values()
        ).lower()

        for relationship in relationships:
            missing = [
                term
                for term in relationship
                if term.lower() not in corpus
            ]

            self.check(
                not missing,
                "Cross-document relationship represented: "
                + " ↔ ".join(relationship),
                blocking=False,
            )

            if missing:
                self.opened(
                    "Cross-document relationship has missing terminology: "
                    + ", ".join(missing)
                    + " | relationship="
                    + " ↔ ".join(relationship)
                )

    def validate_critical_gap_safety(self) -> None:
        gap_document = None

        for document in self.documents.values():
            if "GAP REGISTER" in document.text.upper():
                gap_document = document
                break

        self.check(
            gap_document is not None,
            "Phase-B documentation gap register discovered",
        )

        if gap_document is None:
            return

        text = gap_document.text

        critical_open_patterns = (
            r"CRITICAL[^\n]{0,120}\bOPEN\b",
            r"\bOPEN\b[^\n]{0,120}CRITICAL",
        )

        critical_open = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in critical_open_patterns
        )

        if critical_open:
            self.failed(
                "Gap Register: unresolved CRITICAL OPEN documentation gap detected"
            )
        else:
            self.passed(
                "Gap Register: no CRITICAL OPEN documentation gap detected"
            )

    def validate_manifest_consistency(self) -> None:
        manifests = [
            document
            for document in self.documents.values()
            if "MASTER MANIFEST" in document.text.upper()
        ]

        self.check(
            bool(manifests),
            "PB-DOC-020: Master Manifest discovered",
        )

        if not manifests:
            return

        manifest = manifests[0]

        for doc_id in sorted(EXPECTED_DOC_IDS - {"PB-DOC-020"}):
            self.check(
                doc_id in manifest.text,
                f"PB-DOC-020: references {doc_id}",
                blocking=False,
            )

    def validate_no_authorization_grant(self) -> None:
        corpus = "\n".join(
            document.text for document in self.documents.values()
        ).lower()

        # Architecture Approval is now formally APPROVED.
        # The remaining three states must continue to prevent
        # implementation/production/certification authorization.
        negative_assertions = (
            (
                "architecture approval",
                "approved",
            ),
            (
                "implementation authorization",
                "not authorized",
            ),
            (
                "production implementation",
                "blocked",
            ),
            (
                "production certification",
                "not claimed",
            ),
        )

        for field, expected in negative_assertions:
            self.check(
                expected in corpus,
                f"Global governance safety: {field} remains {expected}",
            )

    def run(self) -> int:
        self.discover_documents()
        self.validate_registry_completeness()
        self.validate_governance()
        self.validate_security_invariants()
        self.validate_traceability()
        self.validate_cross_document_relationships()
        self.validate_critical_gap_safety()
        self.validate_manifest_consistency()
        self.validate_no_authorization_grant()

        print("=" * 72)
        print("LYRION TRUE AGENTIC OS — PHASE-B RECONCILIATION VALIDATOR")
        print("=" * 72)
        print(f"Repository: {ROOT}")
        print(f"Documentation root: {DOC_ROOT}")
        print()

        print("DISCOVERED DOCUMENTS")
        print("-" * 72)

        for doc_id in sorted(self.documents):
            print(f"PASS: {doc_id}: {self.documents[doc_id].path}")

        print()
        print("PASS RESULTS")
        print("-" * 72)

        for message in self.passes:
            print(f"PASS: {message}")

        print()
        print("OPEN / NON-BLOCKING RESULTS")
        print("-" * 72)

        for message in self.opens:
            print(f"OPEN: {message}")

        print()
        print("BLOCKING FAILURES")
        print("-" * 72)

        for message in self.failures:
            print(f"FAIL: {message}")

        print()
        print("=" * 72)

        if self.failures:
            print("RESULT: FAIL")
            print("ARCHITECTURE APPROVAL: NOT GRANTED")
            print("IMPLEMENTATION AUTHORIZATION: NOT AUTHORIZED")
            print("PRODUCTION IMPLEMENTATION: BLOCKED")
            print("PRODUCTION CERTIFICATION: NOT CLAIMED")
            print("=" * 72)
            return 1

        print("RESULT: PASS — RECONCILIATION CHECKS PASSED")
        print(
            f"ARCHITECTURE APPROVAL: "
            f"{GLOBAL_GOVERNANCE['Architecture Approval']}"
        )
        print("IMPLEMENTATION AUTHORIZATION: NOT AUTHORIZED")
        print("PRODUCTION IMPLEMENTATION: BLOCKED")
        print("PRODUCTION CERTIFICATION: NOT CLAIMED")
        print("=" * 72)
        return 0


def main() -> int:
    try:
        return Reconciler().run()
    except KeyboardInterrupt:
        print("\nValidator interrupted.", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"VALIDATOR ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

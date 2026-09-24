#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DOCUMENTS = {
    "PB-DOC-002": ROOT
    / "docs/phase-b/agentic-runtime/LYRION_UNIFIED_CORE_AGENTIC_RUNTIME_SPECIFICATION_v1.md",
    "PB-DOC-003": ROOT
    / "docs/phase-b/identity-authority/LYRION_UNIFIED_CORE_AGENT_IDENTITY_AUTHORITY_SPECIFICATION_v1.md",
    "PB-DOC-004": ROOT
    / "docs/phase-b/capability/LYRION_UNIFIED_CORE_CAPABILITY_MODEL_SPECIFICATION_v1.md",
    "PB-DOC-005": ROOT
    / "docs/phase-b/agent-harness/LYRION_UNIFIED_CORE_AGENT_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-006": ROOT
    / "docs/phase-b/host-harness/LYRION_UNIFIED_CORE_HOST_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-007": ROOT
    / "docs/phase-b/universal-computer/LYRION_UNIFIED_CORE_UNIVERSAL_COMPUTER_SPECIFICATION_v1.md",
    "PB-DOC-008": ROOT
    / "docs/phase-b/application-harness/LYRION_UNIFIED_CORE_APPLICATION_HARNESS_SPECIFICATION_v1.md",
    "PB-DOC-009": ROOT
    / "docs/phase-b/execution-admission/LYRION_UNIFIED_CORE_EXECUTION_ADMISSION_SPECIFICATION_v1.md",
    "PB-DOC-010": ROOT
    / "docs/phase-b/aegis/LYRION_UNIFIED_CORE_AEGIS_GOVERNANCE_SPECIFICATION_v1.md",
    "PB-DOC-011": ROOT
    / "docs/phase-b/secure-execution/LYRION_UNIFIED_CORE_SECURE_EXECUTION_SPECIFICATION_v1.md",
    "PB-DOC-012": ROOT
    / "docs/phase-b/interfaces/LYRION_UNIFIED_CORE_INTERFACE_CONTRACT_SPECIFICATION_v1.md",
    "PB-DOC-013": ROOT
    / "docs/phase-b/data/LYRION_UNIFIED_CORE_DATA_ARCHITECTURE_v1.md",
    "PB-DOC-014": ROOT
    / "docs/phase-b/memory/LYRION_UNIFIED_CORE_MEMORY_PROVENANCE_SPECIFICATION_v1.md",
    "PB-DOC-015": ROOT
    / "docs/phase-b/observability/LYRION_UNIFIED_CORE_OBSERVABILITY_SPECIFICATION_v1.md",
    "PB-DOC-016": ROOT
    / "docs/phase-b/validation/LYRION_UNIFIED_CORE_VALIDATION_SPECIFICATION_v1.md",
    "PB-DOC-017": ROOT
    / "docs/phase-b/security-testing/LYRION_UNIFIED_CORE_SECURITY_TESTING_SPECIFICATION_v1.md",
    "PB-DOC-018": ROOT
    / "docs/phase-b/operations/LYRION_UNIFIED_CORE_OPERATIONS_SPECIFICATION_v1.md",
    "PB-DOC-019": ROOT
    / "docs/phase-b/recovery/LYRION_UNIFIED_CORE_RECOVERY_RESILIENCE_SPECIFICATION_v1.md",
    "PB-DOC-020": ROOT
    / "docs/phase-b/governance/LYRION_TRUE_AGENTIC_OS_PHASE_B_MASTER_MANIFEST_v1.md",
}

GAP_REGISTER = (
    ROOT
    / "docs/phase-b/governance/"
    "LYRION_TRUE_AGENTIC_OS_PHASE_B_DOCUMENTATION_GAP_REGISTER_v1.md"
)

TRACEABILITY = (
    ROOT
    / "docs/phase-b/requirements/"
    "LYRION_CORE_PRD_TRACEABILITY_ACCEPTANCE_MATRIX_v1.md"
)

EXPECTED_CLOSED_STATE = (
    "CLOSED — BASELINE VALIDATED; IMPLEMENTATION VALIDATION PENDING"
)


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passes: list[str] = []
        self.opens: list[str] = []

    def passed(self, message: str) -> None:
        self.passes.append(message)

    def failed(self, message: str) -> None:
        self.errors.append(message)

    def opened(self, message: str) -> None:
        self.opens.append(message)

    @staticmethod
    def read(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def has(text: str, pattern: str) -> bool:
        return re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE) is not None

    def require_file(self, name: str, path: Path) -> str | None:
        if not path.is_file():
            self.failed(f"{name}: file missing: {path}")
            return None

        self.passed(f"{name}: file present")
        return self.read(path)

    def validate_document_metadata(
        self,
        name: str,
        text: str,
    ) -> None:
        # PB-DOC-013 is the Data Architecture baseline. Its governance model
        # explicitly states that the document SHALL NOT be interpreted as authorization to begin,
        # but it does not duplicate the Architecture Approval metadata used by
        # the later specification documents.
        if name == "PB-DOC-020":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-PHASE-B-MANIFEST-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — PHASE-B DOCUMENTATION MASTER MANIFEST",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*APPROVED",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 35):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            for ref in (
                "PB-DOC-013",
                "PB-DOC-014",
                "PB-DOC-015",
                "PB-DOC-016",
                "PB-DOC-017",
                "PB-DOC-018",
                "PB-DOC-019",
                "PB-DOC-020",
            ):
                if ref in text:
                    self.passed(f"{name}: registry reference {ref}")
                else:
                    self.failed(f"{name}: missing registry reference {ref}")

            required_terms = (
                "Aegis",
                "Capability Gateway",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Universal Computer",
                "Recursive Memory Architecture",
                "Recursive Language Model",
                "replay-resistant",
                "revalidation",
                "provenance",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            for ref in (
                "TR-001",
                "TR-002",
                "TR-003",
                "TR-004",
                "TR-005",
                "TR-006",
                "TR-007",
                "TR-008",
                "TR-009",
            ):
                if ref in text:
                    self.passed(f"{name}: traceability reference {ref}")
                else:
                    self.failed(f"{name}: missing traceability reference {ref}")

            if self.has(
                text,
                r"PB-DOC-020 Status:\*\* DRAFT — MASTER MANIFEST BASELINE",
            ):
                self.passed(f"{name}: acceptance state present")
            else:
                self.failed(f"{name}: acceptance state missing")

            # Markdown hard-break syntax uses exactly two trailing spaces.
            # Treat those as intentional formatting, while rejecting
            # other trailing whitespace.
            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-011":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-SECURE-EXECUTION-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-23",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — SECURE EXECUTION BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Secure Executor",
                "Execution Request",
                "Execution Admission",
                "Capability Gateway",
                "Capability",
                "Aegis",
                "Agent Sandbox",
                "LHICF",
                "Host Adapter",
                "Universal Computer",
                "Application Harness",
                "HITL",
                "fail closed",
                "Resource Constraints",
                "Resource Exhaustion",
                "Timeout Handling",
                "Cancellation",
                "Credential Isolation",
                "Network Isolation",
                "Filesystem and Process Isolation",
                "Independent Verification",
                "Provenance and Audit",
                "Observability",
                "Replay and Idempotency",
                "Recovery and Revalidation",
                "Emergency Controls",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing Requirements",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Semantic Reconciliation",
                "Acceptance Criteria",
                "Governance and Approval",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            semantic_checks = (
                (
                    "Secure Executor does not create authority",
                    r"Secure Executor SHALL NOT create, enlarge, infer, or delegate authority",
                ),
                (
                    "raw model output is not authorization",
                    r"raw model-generated commands as authorization",
                ),
                (
                    "Execution Admission remains upstream",
                    r"Execution Admission SHALL remain the authoritative upstream execution-entry decision",
                ),
                (
                    "Aegis remains independent",
                    r"Aegis SHALL remain the independent governance, security, trust, policy, risk, and containment authority",
                ),
                (
                    "Capability Authorization remains outside executor",
                    r"Capability authorization SHALL remain outside the executor's authority boundary",
                ),
                (
                    "Agent Sandbox remains boundary",
                    r"Applicable agent execution SHALL occur within an explicit sandbox boundary",
                ),
                (
                    "LHICF remains controlled host boundary",
                    r"LHICF SHALL remain the controlled boundary between LYRION and the host environment",
                ),
                (
                    "Universal Computer has no alternate privileged path",
                    r"Universal Computer SHALL NOT create an alternate privileged execution path",
                ),
                (
                    "Application Harness does not bypass execution controls",
                    r"Application adapters SHALL NOT bypass the Secure Executor",
                ),
                (
                    "HITL approval required before execution",
                    r"Operations requiring human authorization SHALL NOT execute before the applicable approval",
                ),
                (
                    "fail-closed behavior",
                    r"Secure Executor SHALL fail closed",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired or revoked authority SHALL remain invalid",
                ),
                (
                    "verification remains independent",
                    r"Secure Executor SHALL NOT declare independent verification success on behalf of the verifier",
                ),
                (
                    "recovery revalidates authority",
                    r"identity\s*;\s*(?:-\s*)?task\s*;\s*(?:-\s*)?policy\s*;\s*(?:-\s*)?delegated authority\s*;\s*(?:-\s*)?capability\s*;\s*(?:-\s*)?execution admission",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency controls SHALL remain independent of model and agent authority",
                ),
                (
                    "no alternate privileged execution path",
                    r"No alternate privileged execution path SHALL be introduced",
                ),
            )

            for label, pattern in semantic_checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: {label} missing")

            for traceability_id in (
                "TR-001",
                "TR-002",
                "TR-003",
                "TR-004",
                "TR-005",
                "TR-006",
                "TR-007",
                "TR-008",
                "TR-009",
            ):
                if self.has(text, re.escape(traceability_id)):
                    self.passed(
                        f"{name}: traceability reference {traceability_id}"
                    )
                else:
                    self.failed(
                        f"{name}: traceability reference {traceability_id} missing"
                    )

            if self.has(
                text,
                r"\*\*Structural Validation:\*\*\s*PENDING",
            ):
                self.passed(f"{name}: structural validation state present")
            else:
                self.failed(f"{name}: structural validation state missing")

            if self.has(
                text,
                r"\*\*Semantic Reconciliation:\*\*\s*PENDING",
            ):
                self.passed(f"{name}: semantic reconciliation state present")
            else:
                self.failed(f"{name}: semantic reconciliation state missing")

            if self.has(
                text,
                r"\*\*Architecture Approval:\*\*\s*PENDING",
            ):
                self.passed(f"{name}: architecture approval remains pending")
            else:
                self.failed(f"{name}: architecture approval boundary missing")

            if self.has(
                text,
                r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
            ):
                self.passed(f"{name}: implementation remains NOT AUTHORIZED")
            else:
                self.failed(
                    f"{name}: implementation authorization boundary missing"
                )

            if self.has(
                text,
                r"\*\*Production Implementation:\*\*\s*BLOCKED",
            ):
                self.passed(f"{name}: production implementation remains BLOCKED")
            else:
                self.failed(
                    f"{name}: production implementation boundary missing"
                )

            if self.has(
                text,
                r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
            ):
                self.passed(f"{name}: production certification remains unclaimed")
            else:
                self.failed(
                    f"{name}: production certification boundary missing"
                )

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-010":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-AEGIS-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — AEGIS GOVERNANCE BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Aegis",
                "independent governance",
                "security authority",
                "Trust Governance",
                "Policy Governance",
                "Risk Evaluation",
                "Threat Evaluation",
                "Authority Validation",
                "Capability Governance",
                "Denial and Fail-Closed Behavior",
                "Approval and HITL Coordination",
                "Authority Revocation",
                "Agent Quarantine",
                "Execution Containment",
                "Emergency Controls",
                "Capability Gateway",
                "Execution Admission",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Universal Computer",
                "Host Harness",
                "Application Harness",
                "Memory and RMA Boundary",
                "RLM Boundary",
                "Inter-Agent and Swarm Boundary",
                "Resource Governance",
                "Recovery and Revalidation",
                "Provenance and Audit",
                "Observability",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Traceability",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
                "Governance and Change Control",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "Aegis remains independent",
                    r"Aegis remains an independent governance and security authority",
                ),
                (
                    "Aegis is not an alternate execution path",
                    r"Aegis SHALL NOT become an alternate execution path",
                ),
                (
                    "independence from agent reasoning",
                    r"Aegis SHALL operate independently of the agent's own reasoning",
                ),
                (
                    "models cannot modify governing policy",
                    r"Models and agents SHALL NOT modify, override, disable, or redefine their own governing security policy",
                ),
                (
                    "trusted-system enforcement",
                    r"Policy enforcement SHALL be performed by trusted system components",
                ),
                (
                    "fail-closed behavior",
                    r"operations SHALL fail closed",
                ),
                (
                    "Capability Authorization remains upstream",
                    r"Capability Authorization remains upstream of Execution Admission",
                ),
                (
                    "Capability Gateway remains authoritative",
                    r"Capability Gateway SHALL remain the authoritative execution-admission boundary",
                ),
                (
                    "Secure Executor remains downstream",
                    r"Secure Executor SHALL remain downstream of authorization and admission",
                ),
                (
                    "Agent Sandbox remains boundary",
                    r"Agent Sandbox remains an execution isolation boundary",
                ),
                (
                    "LHICF remains boundary",
                    r"LHICF remains the controlled host-integration boundary",
                ),
                (
                    "Universal Computer does not bypass controls",
                    r"Universal Computer SHALL NOT bypass Aegis, Capability Authorization, Capability Gateway, Secure Executor, Agent Sandbox, LHICF, or required HITL controls",
                ),
                (
                    "Host and Application Harness have no alternate path",
                    r"Host Harness and Application Harness SHALL NOT create alternate privileged execution paths",
                ),
                (
                    "delegation does not authorize execution",
                    r"Delegation SHALL NOT itself authorize execution",
                ),
                (
                    "HITL is not unrestricted execution authority",
                    r"HITL approval SHALL remain scoped to the approved request and SHALL NOT become unrestricted execution authority",
                ),
                (
                    "revoked authority remains invalid",
                    r"Revoked authority SHALL remain invalid",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired authority SHALL remain invalid",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency Controls SHALL remain independent of normal agent/model authority",
                ),
                (
                    "agents cannot disable emergency controls",
                    r"Agents and models SHALL NOT disable or modify their own emergency controls",
                ),
                (
                    "recovery revalidates authority",
                    r"Recovery SHALL revalidate applicable identity, task, policy, authority, capability, resource, and security state",
                ),
                (
                    "verification remains independent",
                    r"Verification remains independent of admission",
                ),
                (
                    "causal provenance",
                    r"Provenance remains causal and attributable",
                ),
                (
                    "security-critical resource controls",
                    r"Security-critical resource limits SHALL NOT depend solely on model instructions",
                ),
                (
                    "failure does not expand privilege",
                    r"Failure of governance dependencies SHALL NOT cause silent privilege expansion",
                ),
                (
                    "implementation remains unauthorized",
                    r"Implementation Authorization:\*\* NOT AUTHORIZED",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            for ref in (
                "TR-001",
                "TR-002",
                "TR-003",
                "TR-004",
                "TR-005",
                "TR-006",
                "TR-007",
                "TR-008",
                "TR-009",
            ):
                if ref in text:
                    self.passed(f"{name}: traceability reference {ref}")
                else:
                    self.failed(f"{name}: missing traceability reference {ref}")

            if self.has(
                text,
                r"\*\*Structural Validation:\*\*\s*PASS",
            ):
                self.passed(f"{name}: structural validation state present")
            else:
                self.failed(f"{name}: structural validation state missing")

            if self.has(
                text,
                r"\*\*Semantic Reconciliation:\*\*\s*RECONCILED",
            ):
                self.passed(f"{name}: semantic reconciliation state present")
            else:
                self.failed(f"{name}: semantic reconciliation state missing")

            if self.has(
                text,
                r"\*\*Architecture Approval:\*\*\s*PENDING",
            ):
                self.passed(f"{name}: architecture approval remains pending")
            else:
                self.failed(f"{name}: architecture approval boundary missing")

            if self.has(
                text,
                r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
            ):
                self.passed(f"{name}: production certification remains unclaimed")
            else:
                self.failed(f"{name}: production certification boundary missing")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-009":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-EXEC-ADMISSION-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — EXECUTION ADMISSION BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 46):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Execution Admission",
                "Admission Request",
                "Admission Context",
                "Delegated Authority",
                "Capability Authorization",
                "Aegis",
                "Capability Gateway",
                "execution-admission boundary",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Universal Computer",
                "Host Harness",
                "Application Harness",
                "HITL",
                "expiry",
                "revocation",
                "replay",
                "fail-closed",
                "recovery",
                "revalidation",
                "verification",
                "provenance",
                "Observability",
                "Emergency Controls",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
                "Governance and Change Control",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "Capability Authorization remains upstream",
                    r"Capability Authorization remains upstream of Execution Admission",
                ),
                (
                    "Capability Gateway remains authoritative",
                    r"Capability Gateway (?:SHALL remain|remains) the authoritative execution-admission boundary",
                ),
                (
                    "Aegis remains independent",
                    r"Aegis remains an independent governance and security authority",
                ),
                (
                    "Secure Executor remains downstream",
                    r"Secure Executor remains downstream of authorization and admission",
                ),
                (
                    "Agent Sandbox remains boundary",
                    r"Agent Sandbox remains an execution isolation boundary",
                ),
                (
                    "LHICF remains boundary",
                    r"LHICF remains the (?:controlled )?host-integration boundary",
                ),
                (
                    "Universal Computer does not bypass admission",
                    r"Universal Computer.*(?:SHALL NOT|does not).*bypass.*(?:authorization|admission)",
                ),
                (
                    "Host Harness has no alternate privileged path",
                    r"Host Harness.*(?:SHALL NOT|does not).*alternate privileged",
                ),
                (
                    "Application Harness has no alternate privileged path",
                    r"Application Harness.*(?:SHALL NOT|does not).*alternate privileged",
                ),
                (
                    "admission does not enlarge delegated authority",
                    r"Execution Admission does not enlarge delegated authority",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired authority SHALL remain invalid",
                ),
                (
                    "revoked authority remains invalid",
                    r"Revoked authority SHALL remain invalid",
                ),
                (
                    "replay resistance",
                    r"replay resistance",
                ),
                (
                    "fail-closed behavior",
                    r"fail-closed",
                ),
                (
                    "recovery revalidates authority",
                    r"recovery revalidates authority and security state",
                ),
                (
                    "independent verification",
                    r"verification remains independent of admission",
                ),
                (
                    "causal provenance",
                    r"provenance remains causal and attributable",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency controls SHALL remain independent",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            for ref in (
                "TR-001",
                "TR-002",
                "TR-003",
                "TR-004",
                "TR-005",
                "TR-006",
                "TR-007",
                "TR-008",
                "TR-009",
            ):
                if ref in text:
                    self.passed(f"{name}: traceability reference {ref}")
                else:
                    self.failed(f"{name}: missing traceability reference {ref}")

            if self.has(
                text,
                r"\*\*Structural Validation:\*\*\s*PASS",
            ):
                self.passed(f"{name}: structural validation state present")
            else:
                self.failed(f"{name}: structural validation state missing")

            if self.has(
                text,
                r"\*\*Semantic Reconciliation:\*\*\s*RECONCILED",
            ):
                self.passed(f"{name}: semantic reconciliation state present")
            else:
                self.failed(f"{name}: semantic reconciliation state missing")

            if self.has(
                text,
                r"\*\*Architecture Approval:\*\*\s*PENDING",
            ):
                self.passed(f"{name}: architecture approval remains pending")
            else:
                self.failed(f"{name}: architecture approval boundary missing")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-008":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-APPLICATION-HARNESS-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — APPLICATION HARNESS BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Application Harness Definition",
                "Application Identity",
                "Application Context",
                "Application Discovery",
                "Application Identification",
                "Application Capability Discovery",
                "Application Availability and State",
                "Application Capability Model",
                "Application Capability Binding",
                "Application Authority Mapping",
                "Application Authorization Boundary",
                "Target Identification and Binding",
                "Operation Identification and Binding",
                "Application Adapter Model",
                "Adapter Discovery and Selection",
                "Application Interaction Model",
                "Universal Computer Relationship",
                "Host Harness Relationship",
                "Capability Gateway Boundary",
                "Secure Execution Boundary",
                "Agent Sandbox Boundary",
                "LHICF Boundary",
                "Desktop and UI Interaction",
                "Application API Interaction",
                "MCP, A2A, and External Integration",
                "Data and Credential Boundary",
                "Resource Governance",
                "Verification",
                "Provenance and Audit",
                "Observability",
                "Failure and Fail-Closed Behavior",
                "Partial and Uncertain Application Effects",
                "Emergency Controls",
                "Recovery and Revalidation",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
                "Governance and Change Control",
                "Final Application Harness Invariant",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "application discovery does not grant authority",
                    r"Application discovery SHALL NOT grant authority",
                ),
                (
                    "capability discovery does not grant authorization",
                    r"Application capability discovery SHALL NOT grant authorization",
                ),
                (
                    "application availability does not grant authority",
                    r"Application availability SHALL NOT grant authority",
                ),
                (
                    "application state does not override policy",
                    r"Application state SHALL NOT override policy",
                ),
                (
                    "application mapping does not enlarge authority",
                    r"Application mapping SHALL NOT enlarge authority",
                ),
                (
                    "adapter selection does not bypass authorization",
                    r"Adapter selection SHALL NOT bypass authorization",
                ),
                (
                    "Application Harness is not independent security authority",
                    r"Application Harness SHALL NOT become an independent security authority",
                ),
                (
                    "Application Harness is not alternate authorization authority",
                    r"Application Harness SHALL NOT become an alternate authorization authority",
                ),
                (
                    "Application Harness is not alternate privileged execution",
                    r"Application Harness SHALL NOT become an alternate privileged execution path",
                ),
                (
                    "Capability Authorization remains explicit",
                    r"Capability Authorization SHALL remain explicit",
                ),
                (
                    "Capability Gateway remains execution-admission boundary",
                    r"Capability Gateway SHALL remain the execution-admission boundary",
                ),
                (
                    "Secure Executor executes authorized operations only",
                    r"Secure Executor SHALL execute only authorized operations",
                ),
                (
                    "application interaction remains sandboxed",
                    r"Application interaction SHALL remain sandboxed where required",
                ),
                (
                    "LHICF remains controlled host-integration boundary",
                    r"LHICF SHALL remain the controlled host-integration boundary",
                ),
                (
                    "MCP/A2A/API messages do not grant authorization",
                    r"MCP/A2A/API messages SHALL NOT independently grant authorization",
                ),
                (
                    "model output is not authorization",
                    r"Model output SHALL NOT constitute authorization",
                ),
                (
                    "agent intent is not authorization",
                    r"Agent intent SHALL NOT constitute authorization",
                ),
                (
                    "application metadata is not authorization",
                    r"Application metadata SHALL NOT constitute authorization",
                ),
                (
                    "unsupported operations fail closed",
                    r"Unsupported or ambiguous operations SHALL fail closed where required",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired authority SHALL remain invalid",
                ),
                (
                    "revoked authority remains invalid",
                    r"Revoked authority SHALL remain invalid",
                ),
                (
                    "recovery does not expand authority",
                    r"Recovery SHALL NOT expand authority",
                ),
                (
                    "consequential operations are independently verifiable",
                    r"Consequential application operations SHALL be independently verifiable",
                ),
                (
                    "application operations retain provenance",
                    r"Application operations SHALL retain provenance and auditability",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency controls SHALL remain independent",
                ),
                (
                    "no alternate privileged path",
                    r"No alternate privileged path SHALL be introduced",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: security invariant present: {label}")
                else:
                    self.failed(f"{name}: missing security invariant: {label}")

            execution_terms = (
                "Aegis",
                "Capability Authorization",
                "Capability Gateway",
                "Execution Admission",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Host/Application Adapter",
                "Universal Computer",
                "Independent Verification",
                "Provenance",
            )

            for term in execution_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "Architecture Approval",
                "Implementation Authorization",
                "Production Implementation",
                "Production Certification",
                "NOT AUTHORIZED",
                "BLOCKED",
                "NOT CLAIMED",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary term: {term}"
                    )

            if self.has(
                text,
                r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
            ):
                self.passed(
                    f"{name}: implementation remains NOT AUTHORIZED"
                )
            else:
                self.failed(
                    f"{name}: implementation authorization boundary missing"
                )

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-007":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-UNIVERSAL-COMPUTER-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — UNIVERSAL COMPUTER BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Universal Computer Definition",
                "Canonical Operation Flow",
                "Operation Identity",
                "Host and Environment Abstraction",
                "Environment Discovery",
                "Host Discovery",
                "Application Discovery",
                "Capability Discovery",
                "Capability-to-Operation Mapping",
                "Authority Preservation",
                "Authorization Boundary",
                "Aegis Boundary",
                "Capability Gateway Boundary",
                "Secure Executor Boundary",
                "Agent Sandbox Boundary",
                "LHICF Boundary",
                "Host Adapter Model",
                "Adapter Discovery and Selection",
                "Host Mapping",
                "Application Mapping",
                "Cross-Platform Abstraction",
                "Unsupported Capability Handling",
                "Universal Computer and Host Harness",
                "Universal Computer and Application Harness",
                "MCP, A2A, and External Integration",
                "Resource Governance",
                "HITL Boundary",
                "Verification",
                "Provenance and Audit",
                "Observability",
                "Failure Handling",
                "Partial and Uncertain Effects",
                "Recovery and Revalidation",
                "Emergency Controls",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
                "Governance and Change Control",
                "Final Universal Computer Invariant",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "Universal Computer does not grant authority",
                    r"Universal Computer SHALL NOT itself grant authority",
                ),
                (
                    "capability discovery does not grant authorization",
                    r"Capability discovery SHALL NOT grant authorization",
                ),
                (
                    "host discovery does not grant execution authority",
                    r"Host discovery SHALL NOT grant execution authority",
                ),
                (
                    "adapter discovery does not grant authority",
                    r"Adapter discovery SHALL NOT grant authority",
                ),
                (
                    "adapter selection does not bypass authorization",
                    r"Adapter selection SHALL NOT bypass authorization",
                ),
                (
                    "host mapping does not enlarge authority",
                    r"Host mapping SHALL NOT enlarge authority",
                ),
                (
                    "application mapping does not enlarge authority",
                    r"Application mapping SHALL NOT enlarge authority",
                ),
                (
                    "Universal Computer does not bypass Aegis",
                    r"Universal Computer SHALL NOT bypass Aegis",
                ),
                (
                    "Universal Computer does not bypass Capability Gateway",
                    r"Universal Computer SHALL NOT bypass Capability Gateway",
                ),
                (
                    "Universal Computer does not bypass Secure Executor",
                    r"Universal Computer SHALL NOT bypass Secure Executor",
                ),
                (
                    "Universal Computer does not bypass Agent Sandbox",
                    r"Universal Computer SHALL NOT bypass Agent Sandbox",
                ),
                (
                    "Universal Computer does not bypass LHICF",
                    r"Universal Computer SHALL NOT bypass LHICF",
                ),
                (
                    "HITL requirements cannot be bypassed",
                    r"HITL requirements SHALL NOT be bypassed",
                ),
                (
                    "unsupported operations fail closed",
                    r"Unsupported operations SHALL fail closed where required",
                ),
                (
                    "arbitrary shell is not Universal Computer authorization",
                    r"Arbitrary shell access SHALL NOT constitute Universal Computer authorization",
                ),
                (
                    "model output is not authorization",
                    r"Model output SHALL NOT constitute authorization",
                ),
                (
                    "agent intent is not authorization",
                    r"Agent intent SHALL NOT constitute authorization",
                ),
                (
                    "external protocol messages are not authorization",
                    r"External protocol messages SHALL NOT constitute authorization",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired authority SHALL remain invalid",
                ),
                (
                    "revoked authority remains invalid",
                    r"Revoked authority SHALL remain invalid",
                ),
                (
                    "recovery does not expand authority",
                    r"Recovery SHALL NOT expand authority",
                ),
                (
                    "no alternate privileged path",
                    r"Universal Computer SHALL NOT create an alternate privileged path",
                ),
                (
                    "consequential operations independently verifiable",
                    r"Consequential operations SHALL remain independently verifiable",
                ),
                (
                    "provenance remains attributable",
                    r"Provenance SHALL remain attributable across abstraction boundaries",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency controls SHALL remain independent",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: invariant present: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            execution_terms = (
                "Aegis",
                "Capability Gateway",
                "Capability Authorization",
                "Execution Admission",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Host Adapter",
                "Host OS",
                "Independent Verification",
                "Provenance",
            )

            for term in execution_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "This specification defines an architectural and documentation baseline.",
                "Implementation Authorization SHALL remain a separate governance decision.",
                "Production Implementation SHALL remain BLOCKED",
                "Production Certification SHALL remain NOT CLAIMED",
                "Implementation SHALL NOT begin solely because this specification exists.",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary: {term}"
                    )

            if re.search(r"[^\S\n]{3,}$", text, flags=re.MULTILINE):
                self.failed(f"{name}: trailing whitespace detected")
            else:
                self.passed(f"{name}: no unintended trailing whitespace")

            return

        if name == "PB-DOC-006":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-HOST-HARNESS-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — HOST HARNESS BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Host Harness Definition",
                "Host Environment Context",
                "Host Identity",
                "Host Discovery",
                "Host Capability Discovery",
                "Capability-to-Host Mapping",
                "Host Adapter Model",
                "Adapter Selection",
                "Host Operation Model",
                "Host Operation Authorization Boundary",
                "LHICF Boundary",
                "Filesystem Mediation",
                "Process Mediation",
                "Service Mediation",
                "Network Mediation",
                "Application Mediation",
                "Desktop and UI Mediation",
                "Device Mediation",
                "Clipboard Mediation",
                "Notification Mediation",
                "Operating-System State Mediation",
                "Resource Governance",
                "Security State",
                "Universal Computer Boundary",
                "Unsupported Capability Handling",
                "Host Operation Verification",
                "Provenance and Audit",
                "Observability",
                "Failure Handling",
                "Emergency Controls",
                "Recovery and Revalidation",
                "Partial and Uncertain Host Effects",
                "Host Isolation and Boundary Protection",
                "External and Application Integration",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
                "Governance and Change Control",
                "Final Host Harness Invariant",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "host discovery does not grant execution authority",
                    r"Host discovery SHALL NOT grant execution authority",
                ),
                (
                    "capability discovery does not grant authorization",
                    r"Capability discovery SHALL NOT grant authorization",
                ),
                (
                    "host mapping does not enlarge authority",
                    r"Host mapping SHALL NOT enlarge authority",
                ),
                (
                    "adapter selection does not bypass authorization",
                    r"Adapter selection SHALL NOT bypass authorization",
                ),
                (
                    "Host Harness is not an independent security authority",
                    r"Host Harness SHALL NOT become an independent security authority",
                ),
                (
                    "unrestricted host access prohibited",
                    r"Host Harness SHALL NOT provide unrestricted host access",
                ),
                (
                    "LHICF remains controlled host boundary",
                    r"LHICF SHALL remain the controlled host-integration boundary",
                ),
                (
                    "unsupported operations fail closed",
                    r"Unsupported operations SHALL fail closed where required",
                ),
                (
                    "model claims do not establish execution success",
                    r"Agent or model claims SHALL NOT by themselves establish successful host execution",
                ),
                (
                    "recovery revalidates authority",
                    r"Recovery SHALL revalidate authority and capability before consequential continuation",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired authority SHALL remain invalid",
                ),
                (
                    "revoked authority remains invalid",
                    r"Revoked authority SHALL remain invalid",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency controls SHALL remain independent of the Host Harness and agent",
                ),
                (
                    "no alternate privileged path",
                    r"The Host Harness SHALL NOT create an alternate privileged path",
                ),
                (
                    "arbitrary shell is not Universal Computer authorization",
                    r"Arbitrary shell access SHALL NOT constitute Universal Computer authorization",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: invariant present: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            execution_terms = (
                "Aegis",
                "Capability Gateway",
                "Capability Authorization",
                "Execution Admission",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Host Adapter",
                "Host OS",
                "Independent Verification",
            )

            for term in execution_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "This specification defines an architectural and documentation baseline.",
                "Implementation Authorization SHALL remain a separate governance decision.",
                "Production Implementation:** BLOCKED",
                "Production Certification:** NOT CLAIMED",
                "Implementation SHALL NOT begin solely because this specification exists.",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary: {term}"
                    )

            if re.search(r"[^\S\n]{3,}$", text, flags=re.MULTILINE):
                self.failed(f"{name}: trailing whitespace detected")
            else:
                self.passed(f"{name}: no unintended trailing whitespace")

            return

        if name == "PB-DOC-005":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-AGENT-HARNESS-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — AGENT HARNESS BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Agent Harness Definition",
                "Agent Control Plane Relationship",
                "Agent Identity",
                "Agent Registration",
                "Agent Lifecycle",
                "Lifecycle Transition Control",
                "Task Binding",
                "Task Execution Boundary",
                "Capability Binding",
                "Authority Validation",
                "Least Privilege",
                "Delegated Authority",
                "Authority Attenuation",
                "Tool Invocation",
                "Tool and External-Service Boundary",
                "Runtime Isolation",
                "Resource Enforcement",
                "Inter-Agent Communication",
                "Agent-to-Agent Delegation",
                "Agent Swarm Boundary",
                "Agent Control Plane Boundary",
                "Aegis Boundary",
                "Capability Gateway Boundary",
                "Secure Execution Boundary",
                "Universal Computer Boundary",
                "Memory and RMA Boundary",
                "RLM Boundary",
                "Provenance and Audit",
                "Observability",
                "Failure Handling",
                "Emergency Controls",
                "Recovery and Revalidation",
                "Durable Runtime State",
                "Voice and External Protocol Boundary",
                "Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
                "Governance and Change Control",
                "Final Agent Harness Invariant",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "ACP is not an independent security authority",
                    r"Agent Control Plane SHALL NOT become an independent security authority",
                ),
                (
                    "Agent Harness is not an independent security authority",
                    r"Agent Harness SHALL NOT itself become an independent security authority",
                ),
                (
                    "registration does not grant execution authority",
                    r"Registration SHALL NOT itself grant execution authority",
                ),
                (
                    "lifecycle state does not grant authority",
                    r"Lifecycle state SHALL NOT independently grant authority",
                ),
                (
                    "task scheduling does not authorize execution",
                    r"Task scheduling SHALL NOT constitute execution authorization",
                ),
                (
                    "capability binding does not bypass authorization",
                    r"Capability binding SHALL NOT bypass independent authorization",
                ),
                (
                    "delegation does not authorize execution",
                    r"Delegation SHALL NOT itself authorize execution",
                ),
                (
                    "child authority cannot exceed parent",
                    r"Child authority SHALL NOT exceed valid parent authority",
                ),
                (
                    "model output is not authorization",
                    r"RLM output SHALL NOT constitute:",
                ),
                (
                    "unrestricted host access prohibited",
                    r"Agent Harness SHALL NOT provide unrestricted host access",
                ),
                (
                    "no direct privileged host execution",
                    r"Agent Harness SHALL NOT directly execute privileged host operations",
                ),
                (
                    "runtime state is not authority",
                    r"Runtime state SHALL NOT constitute current authority",
                ),
                (
                    "expired authority remains invalid",
                    r"Expired authority SHALL remain invalid",
                ),
                (
                    "revoked authority remains invalid",
                    r"Revoked authority SHALL remain invalid",
                ),
                (
                    "emergency controls remain independent",
                    r"Emergency controls SHALL remain independent of the agent and model",
                ),
                (
                    "no alternate privileged path",
                    r"Agent Harness SHALL NOT create an alternate privileged path",
                ),
                (
                    "consequential execution is independently verifiable",
                    r"Consequential execution SHALL remain independently verifiable",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: invariant present: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            execution_terms = (
                "Aegis",
                "Capability Gateway",
                "Capability Authorization",
                "Execution Admission",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Host",
                "Independent Verification",
            )

            for term in execution_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "This specification defines an architectural and documentation baseline.",
                "Implementation Authorization SHALL remain a separate governance decision.",
                "Production Implementation:** BLOCKED",
                "Production Certification:** NOT CLAIMED",
                "The existence of this specification SHALL NOT be treated as evidence that the controls are implemented.",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary: {term}"
                    )

            if re.search(r"[^\S\n]{3,}$", text, flags=re.MULTILINE):
                self.failed(f"{name}: trailing whitespace detected")
            else:
                self.passed(f"{name}: no unintended trailing whitespace")

            return

        if name == "PB-DOC-004":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-CAPABILITY-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — CAPABILITY MODEL BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Capability Definition",
                "Capability Identity",
                "Capability Classification",
                "Capability Scope",
                "Capability Binding",
                "Capability and Authority Relationship",
                "Capability Attenuation",
                "Capability Gateway",
                "Capability Authorization",
                "Capability Admission",
                "Target Binding",
                "Operation Binding",
                "Resource Constraints",
                "Time Constraints",
                "Revocation",
                "Replay Resistance",
                "Approval Requirements",
                "Aegis Boundary",
                "Secure Executor Boundary",
                "Sandbox Boundary",
                "LHICF Boundary",
                "Host Capability Mapping",
                "Application Capability Mapping",
                "Universal Computer Boundary",
                "Inter-Agent Capability Boundary",
                "Agent Swarm Boundary",
                "RLM Boundary",
                "RMA / Memory Boundary",
                "Verification",
                "Provenance and Audit",
                "Observability",
                "Failure and Fail-Closed Behavior",
                "Emergency Controls",
                "Recovery and Revalidation",
                "Capability Security Invariants",
                "Validation Requirements",
                "Security Testing",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
                "Semantic Reconciliation",
                "Implementation Boundary",
                "Acceptance State",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "capability does not imply unlimited authority",
                    r"Capability SHALL NOT imply unlimited authority",
                ),
                (
                    "capability discovery does not grant authority",
                    r"Capability discovery SHALL NOT grant authority",
                ),
                (
                    "capability binding does not bypass authorization",
                    r"Capability binding SHALL NOT bypass authorization",
                ),
                (
                    "delegation does not expand capability scope",
                    r"Delegation SHALL NOT expand capability scope",
                ),
                (
                    "child capability scope bounded",
                    r"Child capability scope SHALL NOT exceed parent authority",
                ),
                (
                    "capability authorization explicit",
                    r"Capability authorization SHALL be explicit",
                ),
                (
                    "Capability Gateway is execution-admission boundary",
                    r"Capability Gateway SHALL remain the execution-admission boundary",
                ),
                (
                    "Secure Executor only executes authorized operations",
                    r"Secure Executor SHALL execute only authorized operations",
                ),
                (
                    "unsupported host capabilities fail closed",
                    r"Unsupported host capabilities SHALL fail closed",
                ),
                (
                    "no alternate privileged path",
                    r"No alternate privileged path SHALL exist",
                ),
                (
                    "expired authorization not executable",
                    r"Expired authorization SHALL NOT be executable",
                ),
                (
                    "revoked authorization not restored",
                    r"Revoked authorization SHALL NOT be restored by recovery",
                ),
                (
                    "model output not authorization",
                    r"Model output SHALL NOT constitute capability authorization",
                ),
                (
                    "agent intent not authorization",
                    r"Agent intent SHALL NOT constitute capability authorization",
                ),
                (
                    "memory not automatic authorization",
                    r"Memory SHALL NOT automatically constitute capability authorization",
                ),
                (
                    "messages do not grant capability authority",
                    r"Inter-agent messages SHALL NOT grant capability authority",
                ),
                (
                    "independent verification required",
                    r"Consequential execution SHALL receive independent verification",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: invariant present: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            execution_terms = (
                "Aegis",
                "Capability Gateway",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Host Adapter",
                "Host OS",
                "Execution Admission",
                "Independent Verification",
            )

            for term in execution_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "This document is an architectural/specification baseline.",
                "Implementation Authorization remains NOT AUTHORIZED.",
                "Production Implementation remains BLOCKED.",
                "Production Certification remains NOT CLAIMED.",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary: {term}"
                    )

            if re.search(r"[^\S\n]{3,}$", text, flags=re.MULTILINE):
                self.failed(f"{name}: trailing whitespace detected")
            else:
                self.passed(f"{name}: no unintended trailing whitespace")

            return

        if name == "PB-DOC-003":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-IDENTITY-AUTHORITY-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — IDENTITY & AUTHORITY BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            # PB-DOC-003 contains sections 1 through 49.
            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Agent Identity",
                "Principal Model",
                "Agent Identity Binding",
                "Identity Stability",
                "Identity Lifecycle",
                "Authentication",
                "Attribution",
                "Authority Model",
                "Authority Binding",
                "Least Privilege",
                "Authority Scope",
                "Capability Binding",
                "Delegated Authority",
                "Authority Attenuation",
                "Child Authority",
                "Authority Expiration",
                "Authority Revocation",
                "replay resistance",
                "Impersonation Resistance",
                "Inter-Agent Identity",
                "Cross-Task Isolation",
                "Agent Registry Boundary",
                "Agent Control Plane Boundary",
                "Aegis Boundary",
                "Capability Gateway Boundary",
                "Secure Execution Boundary",
                "Emergency Controls",
                "Recovery and Revalidation",
                "Durable State",
                "provenance",
                "RLM output SHALL NOT constitute authorization",
                "RMA",
                "Voice Boundary",
                "External Protocol Boundary",
                "Universal Computer Boundary",
                "Resource Authority",
                "Security Invariants",
                "Validation Requirements",
                "Cross-Document Dependencies",
                "Governance Boundary",
                "Acceptance Criteria",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            invariants = (
                (
                    "identity distinct from human identity",
                    r"Agent identity is distinct from human identity",
                ),
                (
                    "identity does not grant execution authority",
                    r"Identity does not itself grant execution authority",
                ),
                (
                    "registry does not grant execution authority",
                    r"Registry membership does not grant execution authority",
                ),
                (
                    "ACP is not independent security authority",
                    r"ACP SHALL NOT become an independent security authority",
                ),
                (
                    "delegation does not authorize execution",
                    r"Delegation does not itself authorize execution",
                ),
                (
                    "child authority bounded",
                    r"Child authority SHALL NOT exceed parent authority",
                ),
                (
                    "agents cannot manufacture authority",
                    r"Agents cannot manufacture authority claims",
                ),
                (
                    "messages do not grant authority",
                    r"Messages do not implicitly grant authority",
                ),
                (
                    "model output does not constitute authority",
                    r"Model output does not constitute authority",
                ),
                (
                    "memory does not automatically constitute authority",
                    r"Memory content does not automatically constitute authority",
                ),
                (
                    "expired authority cannot be used",
                    r"Expired authority cannot be used",
                ),
                (
                    "revoked authority cannot be restored",
                    r"Revoked authority cannot be restored merely from runtime state",
                ),
                (
                    "recovery cannot expand authority",
                    r"Recovery cannot silently expand authority",
                ),
                (
                    "no alternate privileged path",
                    r"No alternate privileged execution path may be introduced",
                ),
                (
                    "emergency controls independent",
                    r"Emergency controls remain independent of agent authority",
                ),
            )

            for label, pattern in invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: invariant present: {label}")
                else:
                    self.failed(f"{name}: missing invariant: {label}")

            execution_terms = (
                "Agent → Delegated Authority → Aegis",
                "Capability Authorization",
                "Execution Admission",
                "Secure Executor → Agent Sandbox → LHICF → Host",
                "Independent verification",
            )

            for term in execution_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "This document is an architectural/specification baseline.",
                "Production Implementation:** BLOCKED",
                "Production Certification:** NOT CLAIMED",
                "Implementation Authorization:** NOT AUTHORIZED",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary: {term}"
                    )

            if not any(
                line.rstrip() != line and not line.endswith("  ")
                for line in text.splitlines()
            ):
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-002":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-AGENT-RUNTIME-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — AGENTIC RUNTIME BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            # PB-DOC-002 contains sections 1 through 49.
            for section in range(1, 50):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            required_terms = (
                "Agent Registry",
                "Agent Identity Boundary",
                "Agent Lifecycle",
                "Agent Control Plane",
                "Delegated Authority",
                "Capability Gateway",
                "Aegis",
                "Secure Executor",
                "Agent Sandbox",
                "LHICF",
                "Universal Computer",
                "Recursive Language Model",
                "Recursive Memory Architecture",
                "inter-agent communication",
                "replay protection",
                "revalidate",
                "provenance",
                "fail closed",
                "observability",
                "emergency controls",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            required_invariants = (
                (
                    "ACP is not independent security authority",
                    r"Agent Control Plane SHALL NOT become:\s*-\s*an independent security authority",
                ),
                (
                    "scheduling does not authorize execution",
                    r"Scheduling SHALL NOT itself constitute execution authorization",
                ),
                (
                    "registry does not grant execution authority",
                    r"Registry membership SHALL NOT grant execution authority",
                ),
                (
                    "delegation does not authorize execution",
                    r"Delegation SHALL NOT itself authorize execution",
                ),
                (
                    "runtime does not directly execute privileged host operations",
                    r"Agentic Runtime SHALL NOT directly execute privileged host",
                ),
                (
                    "recovery does not restore revoked authority",
                    r"Expired or revoked authority SHALL NOT be restored",
                ),
                (
                    "RLM does not constitute authorization",
                    r"RLM output SHALL remain reasoning/evidence\s+and SHALL NOT constitute\s+authorization",
                ),
                (
                    "no alternate privileged path",
                    r"No alternate privileged path SHALL be introduced by the runtime",
                ),
                (
                    "swarm bounded",
                    r"Unlimited recursive agent spawning SHALL NOT be permitted",
                ),
                (
                    "agents cannot modify emergency controls",
                    r"Agents SHALL NOT modify, disable or bypass emergency controls",
                ),
            )

            for label, pattern in required_invariants:
                if self.has(text, pattern):
                    self.passed(f"{name}: invariant present: {label}")
                else:
                    self.failed(
                        f"{name}: missing required invariant: {label}"
                    )

            execution_chain_terms = (
                "Agent → Delegated Authority → Aegis",
                "Capability Authorization",
                "Execution Admission",
                "Secure Executor → Sandbox → LHICF → Host",
                "Independent Verification",
            )

            for term in execution_chain_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: execution boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing execution boundary term: {term}"
                    )

            governance_terms = (
                "This document is an architectural/specification baseline.",
                "Production implementation remains blocked",
                "Production Certification:** NOT CLAIMED",
                "Implementation Authorization:** NOT AUTHORIZED",
            )

            for term in governance_terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: governance boundary present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing governance boundary: {term}"
                    )

            # Markdown hard-break syntax uses exactly two trailing spaces.
            # Treat those as intentional formatting, while rejecting
            # other trailing whitespace.
            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-012":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-INTERFACE-CONTRACT-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-23",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — INTERFACE / CONTRACT BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: {label} missing")

            section_numbers = re.findall(
                r"^##\s+(\d+)\.\s+.+$",
                text,
                flags=re.MULTILINE,
            )
            expected_sections = [str(i) for i in range(1, 50)]

            if section_numbers == expected_sections:
                self.passed(f"{name}: sections 1-49 present and ordered")
            else:
                self.failed(f"{name}: sections 1-49 missing or out of order")

            required_terms = (
                "Contract Identity",
                "Contract Ownership",
                "Contract Versioning",
                "Agent Contracts",
                "Identity and Authority Contracts",
                "Delegation Contracts",
                "Capability Contracts",
                "Governance Contracts",
                "Action Proposal Contracts",
                "Capability Authorization Contracts",
                "Execution Admission Contracts",
                "Secure Execution Contracts",
                "Sandbox Contracts",
                "LHICF Contracts",
                "Universal Computer Contracts",
                "Host Harness Contracts",
                "Application Harness Contracts",
                "Tool and API Contracts",
                "MCP and A2A Contracts",
                "Event Contracts",
                "Inter-Agent Communication Contracts",
                "Memory and RMA Contracts",
                "RLM Contracts",
                "Verification Contracts",
                "Provenance Contracts",
                "Error Contracts",
                "Recovery Contracts",
                "Resource Contracts",
                "HITL Contracts",
                "Authentication and Transport Contracts",
                "Session and Context Contracts",
                "Contract Validation and Schema Rules",
                "Contract Compatibility and Change Control",
                "Security Invariants",
                "Traceability",
                "Validation Requirements",
                "Security Testing Requirements",
                "Observability and Audit",
                "Failure and Fail-Closed Behavior",
                "Cross-Document Dependencies",
                "Acceptance Criteria",
                "Final Interface / Contract Invariant",
                "Documentation Status",
                "Governance and Approval",
            )

            for term in required_terms:
                if term.lower() in text.lower():
                    self.passed(f"{name}: required section/term: {term}")
                else:
                    self.failed(f"{name}: required section/term missing: {term}")

            semantic_checks = (
                (
                    "contracts do not grant authority",
                    r"contract(?:s)?\s+(?:shall|do|does)\s+not\s+grant\s+authority|contracts?\s+(?:do|does)\s+not\s+grant\s+authority",
                ),
                (
                    "message content does not grant authority",
                    r"message content\s+(?:does not|shall not)\s+grant\s+authority",
                ),
                (
                    "identity and authority remain distinct",
                    r"identity\s*(?:is|≠|!=)\s*authority|identity.*(?:shall not|does not).*authority|identity.*authority.*(?:distinct|separate)",
                ),
                (
                    "delegation does not authorize execution",
                    r"delegation\s+(?:does not|shall not)\s+(?:itself\s+)?authorize\s+execution",
                ),
                (
                    "capability discovery does not grant authorization",
                    r"capability discovery\s+(?:does not|shall not)\s+grant\s+authorization",
                ),
                (
                    "Aegis remains independent",
                    r"Aegis\s+remains\s+(?:the\s+)?independent\s+governance\s+and\s+security\s+authority",
                ),
                (
                    "action proposal does not authorize execution",
                    r"Action Proposal.*(?:does not|shall not).*authoriz",
                ),
                (
                    "Capability Authorization precedes Execution Admission",
                    r"Capability Authorization.*Execution Admission",
                ),
                (
                    "Secure Executor cannot expand authority",
                    r"Secure Executor.*(?:does not|shall not).*(?:grant|expand|infer|bypass).*authority",
                ),
                (
                    "Universal Computer cannot bypass authorization",
                    r"Universal Computer.*(?:shall not|does not).*bypass.*(?:security controls|Capability Authorization|Capability Gateway)",
                ),
                (
                    "Application Harness cannot bypass authorization",
                    r"Application Harness.*(?:shall not|does not).*bypass.*(?:Capability Authorization|Capability Gateway)",
                ),
                (
                    "MCP/A2A cannot grant authority",
                    r"MCP.*A2A.*(?:does not|shall not).*grant.*author",
                ),
                (
                    "RMA and RLM remain separate",
                    r"RMA.*(?:distinct|separate).*RLM|RLM.*(?:distinct|separate).*RMA",
                ),
                (
                    "model output is not automatically trusted memory",
                    r"(?:generated\s+)?model\s+output.*(?:does not|shall not).*trusted.*memory",
                ),
                (
                    "execution completion is not verification",
                    r"execution completion.*(?:does not|shall not).*verified success",
                ),
                (
                    "expired and revoked authority remain invalid",
                    r"expired.*revoked.*(?:invalid|remain invalid)|revoked.*expired.*(?:invalid|remain invalid)",
                ),
                (
                    "recovery revalidates authority",
                    r"recovery.*revalidat.*(?:identity|task|policy).*delegated authority.*capability|Recovery.*(?:shall require|shall)\s+revalidation",
                ),
                (
                    "HITL does not create an alternate path",
                    r"(?:approval|HITL).*?(?:does not|shall not).*?(?:create|become).*?(?:alternate|privileged).*?(?:path|authority)|HITL\s+contracts\s+shall\s+represent\s+approval\s+requirements\s+without\s+creating\s+an\s+alternate\s+execution\s+authority",
                ),
                (
                    "critical resource limits remain external to model control",
                    r"(?:critical limits|resource limits|security-critical resource limits).*?(?:external to model|outside model instructions)",
                ),
                (
                    "fail-closed behavior",
                    r"fail[- ]closed",
                ),
                (
                    "no alternate privileged path",
                    r"no alternate privileged path",
                ),
            )

            for label, pattern in semantic_checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: {label} missing")

            for tr in [f"TR-{i:03d}" for i in range(1, 10)]:
                if tr in text:
                    self.passed(f"{name}: traceability reference {tr}")
                else:
                    self.failed(f"{name}: traceability reference {tr} missing")

            governance_checks = (
                (
                    "structural validation pending",
                    r"Structural Validation:\s*PENDING|Structural Validation\s*=\s*PENDING",
                ),
                (
                    "semantic reconciliation pending",
                    r"Semantic Reconciliation:\s*PENDING|Semantic Reconciliation\s*=\s*PENDING",
                ),
                (
                    "architecture approval remains pending",
                    r"Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "implementation remains NOT AUTHORIZED",
                    r"Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production remains BLOCKED",
                    r"Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "certification remains NOT CLAIMED",
                    r"Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in governance_checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: {label} missing")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-018":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-OPS-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — OPERATIONS BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            required_terms = (
                "Aegis",
                "Capability Gateway",
                "Execution Admission",
                "Secure Executor",
                "LHICF",
                "Application Harness",
                "provenance",
                "revalidation",
                "replay protection",
                "fail closed",
                "observability",
                "operational evidence",
                "real-infrastructure evidence",
                "emergency controls",
                "backup",
                "restore",
                "rollback",
                "supply-chain",
                "Production Certification",
            )

            for term in required_terms:
                if self.has(text, re.escape(term)):
                    self.passed(f"{name}: required term present: {term}")
                else:
                    self.failed(f"{name}: missing required term: {term}")

            semantic_checks = (
                (
                    "operational authority boundary",
                    r"Operations SHALL remain subordinate to the approved LYRION True Agentic OS architecture",
                ),
                (
                    "no alternate operational authority path",
                    r"Operations SHALL NOT create an alternate execution, authorization, identity, security, or privileged-control path",
                ),
                (
                    "operational state is not authorization",
                    r"Lifecycle state SHALL NOT itself constitute authorization",
                ),
                (
                    "startup security validation",
                    r"Startup SHALL verify applicable",
                ),
                (
                    "security-critical initialization fail closed",
                    r"Failure of security-critical initialization SHALL fail closed",
                ),
                (
                    "shutdown external-effect safety",
                    r"Consequential operations SHALL use appropriate idempotency or compensation mechanisms",
                ),
                (
                    "health is not authorization",
                    r"A healthy process SHALL NOT automatically be considered authorized or safe for consequential execution",
                ),
                (
                    "secret protection",
                    r"Secrets SHALL NOT be embedded in source code, prompts, model context, logs, telemetry, memory objects, or unprotected configuration",
                ),
                (
                    "identity separation",
                    r"Human principal[\s\S]*Lyri identity[\s\S]*Session[\s\S]*Agent identity[\s\S]*Task identity[\s\S]*Execution identity",
                ),
                (
                    "agent operations do not grant capabilities",
                    r"Operational control SHALL NOT grant an agent capabilities that were not authorized through the governing authority chain",
                ),
                (
                    "delegated authority replay protection",
                    r"Replay protection SHALL prevent reuse of expired, revoked, or previously consumed delegated-authority artifacts",
                ),
                (
                    "recovery revalidates authority",
                    r"Recovery SHALL revalidate:[\s\S]*Identity[\s\S]*Task[\s\S]*Policy[\s\S]*Authority[\s\S]*Capability[\s\S]*Resources[\s\S]*Security state",
                ),
                (
                    "persisted state does not override authorization",
                    r"Persisted state SHALL NOT override current authorization",
                ),
                (
                    "capability availability is not authorization",
                    r"Capability availability SHALL NOT imply authorization",
                ),
                (
                    "canonical execution chain",
                    r"Aegis\s*→\s*Capability Gateway\s*→\s*Execution Admission\s*→\s*Secure Executor\s*→\s*Sandbox\s*→\s*LHICF\s*→\s*Host",
                ),
                (
                    "no alternate privileged execution path",
                    r"Operations SHALL NOT create an alternate privileged execution path",
                ),
                (
                    "observability boundary",
                    r"Operational observability SHALL provide appropriate visibility",
                ),
                (
                    "security operations independence",
                    r"Security operations SHALL remain independent from model-generated authorization",
                ),
                (
                    "alert execution boundary",
                    r"Alert generation SHALL NOT itself execute consequential actions unless an independently authorized control path explicitly permits the action",
                ),
                (
                    "resource limits outside model instructions",
                    r"Security-critical resource limits SHALL be enforced outside model instructions",
                ),
                (
                    "degraded operation fail closed",
                    r"Security-critical degradation SHALL fail closed",
                ),
                (
                    "emergency-control independence",
                    r"Emergency controls SHALL remain independent of model and agent authority",
                ),
                (
                    "agent emergency-control protection",
                    r"Agents SHALL NOT disable, weaken, or modify their own emergency controls",
                ),
                (
                    "memory/RLM separation",
                    r"RMA SHALL remain distinct from RLM reasoning",
                ),
                (
                    "authoritative data boundary",
                    r"Primary authoritative state SHALL follow the approved Data Architecture",
                ),
                (
                    "network restriction",
                    r"Agents SHALL NOT obtain unrestricted network access",
                ),
                (
                    "LHICF host mediation",
                    r"LHICF SHALL provide controlled host mediation",
                ),
                (
                    "arbitrary privileged shell prohibited",
                    r"Operational tooling SHALL NOT replace LHICF with arbitrary privileged shell access",
                ),
                (
                    "application security chain",
                    r"Application Harness operations SHALL preserve:[\s\S]*Discovery[\s\S]*Identification[\s\S]*Capability Discovery[\s\S]*Authorization[\s\S]*Interaction[\s\S]*Verification[\s\S]*Provenance",
                ),
                (
                    "deployment authorization",
                    r"Deployment SHALL support controlled:[\s\S]*Artifact identification[\s\S]*Version verification[\s\S]*Integrity verification[\s\S]*Dependency verification[\s\S]*Configuration validation[\s\S]*Security checks[\s\S]*Deployment authorization[\s\S]*Health verification[\s\S]*Rollback",
                ),
                (
                    "unverified artifact protection",
                    r"Unverified artifacts SHALL NOT be promoted into a production-authorized state",
                ),
                (
                    "rollback authority protection",
                    r"Rollback SHALL not restore obsolete or revoked security authority",
                ),
                (
                    "research dependency boundary",
                    r"Research references SHALL NOT automatically become trusted runtime dependencies",
                ),
                (
                    "operational access control",
                    r"Operational interfaces SHALL enforce least privilege",
                ),
                (
                    "administrative boundary",
                    r"Administrative interfaces SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Sandbox, LHICF",
                ),
                (
                    "operational evidence",
                    r"Operational evidence SHALL include, where applicable",
                ),
                (
                    "reference versus real infrastructure evidence",
                    r"Reference-environment evidence SHALL remain distinct from real-infrastructure evidence",
                ),
                (
                    "operational readiness gate boundary",
                    r"Passing an operational gate SHALL NOT independently authorize production deployment",
                ),
                (
                    "operational regression",
                    r"Operational controls SHALL be revalidated after applicable",
                ),
                (
                    "failure fail closed",
                    r"Security-critical failures SHALL fail closed",
                ),
                (
                    "ambiguous authorization is not authorization",
                    r"Unknown or ambiguous authorization state SHALL NOT be interpreted as authorization",
                ),
                (
                    "production implementation boundary",
                    r"Production implementation remains blocked",
                ),
                (
                    "G47 historical evidence separation",
                    r"Historical G47 evidence SHALL remain clearly separated from current Phase-B operational evidence",
                ),
                (
                    "baseline validation acceptance",
                    r"PB-DOC-018 SHALL be considered baseline-validated only when",
                ),
                (
                    "implementation boundary",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production boundary",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "certification boundary",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in semantic_checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: missing required {label}")

            if self.has(
                text,
                r"Cross-document references are consistent",
            ):
                self.passed(
                    f"{name}: cross-document traceability requirement present"
                )
            else:
                self.failed(
                    f"{name}: missing cross-document traceability requirement"
                )

            for section in range(1, 51):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-017":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-SEC-TEST-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — SECURITY TESTING BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            semantic_checks = (
                (
                    "security testing non-authorization boundary",
                    r"does not itself authorize implementation or production deployment",
                ),
                (
                    "security testing authority separation",
                    r"architectural intent[\s\S]*implemented control[\s\S]*test execution[\s\S]*test evidence[\s\S]*security acceptance[\s\S]*production certification",
                ),
                (
                    "security states remain distinct",
                    r"NOT SPECIFIED[\s\S]*SPECIFIED[\s\S]*IMPLEMENTED[\s\S]*TESTED[\s\S]*VALIDATED[\s\S]*SECURITY ACCEPTED[\s\S]*PRODUCTION OPERATIONAL[\s\S]*CERTIFIED",
                ),
                (
                    "security test categories",
                    r"Static security validation[\s\S]*Unit security tests[\s\S]*Integration security tests[\s\S]*Negative-path tests[\s\S]*Fail-closed tests[\s\S]*Adversarial tests",
                ),
                (
                    "threat coverage",
                    r"prompt injection",
                ),
                (
                    "identity security testing",
                    r"human identity is distinct from agent identity",
                ),
                (
                    "authentication fail-closed",
                    r"Authentication failure SHALL fail closed",
                ),
                (
                    "authorization deny-by-default",
                    r"deny-by-default behavior",
                ),
                (
                    "model output is not authorization",
                    r"Model output SHALL never constitute authorization",
                ),
                (
                    "delegated authority attenuation",
                    r"A child authority SHALL never exceed its parent authority",
                ),
                (
                    "delegation does not authorize execution",
                    r"Delegation SHALL NOT itself authorize execution",
                ),
                (
                    "ACP alternate path prohibited",
                    r"ACP SHALL not become an alternate privileged execution path",
                ),
                (
                    "inter-agent integrity",
                    r"message integrity",
                ),
                (
                    "inter-agent replay protection",
                    r"replay protection",
                ),
                (
                    "swarm boundary",
                    r"Swarm functionality SHALL not be treated as a foundational requirement",
                ),
                (
                    "Aegis independence",
                    r"Aegis SHALL be tested as an independent security and governance boundary",
                ),
                (
                    "Aegis self-control protection",
                    r"An agent SHALL not modify, disable, or bypass its own Aegis controls",
                ),
                (
                    "HITL alternate path prohibited",
                    r"HITL approval SHALL not create an alternate execution path",
                ),
                (
                    "Capability Gateway testing",
                    r"Capability Gateway Testing",
                ),
                (
                    "Execution Admission testing",
                    r"Execution Admission Testing",
                ),
                (
                    "Secure Executor testing",
                    r"Secure Executor Testing",
                ),
                (
                    "Sandbox testing",
                    r"Sandbox Security Testing",
                ),
                (
                    "LHICF testing",
                    r"LHICF Security Testing",
                ),
                (
                    "Universal Computer boundary",
                    r"Universal Computer SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Sandbox, LHICF, HITL, or verification",
                ),
                (
                    "Application Harness boundary",
                    r"Application Harness SHALL NOT bypass Capability Authorization,\s*Capability Gateway,\s*Execution Admission,\s*Secure Executor,\s*Sandbox",
                ),
                (
                    "injection testing",
                    r"Prompt and Indirect Injection Testing",
                ),
                (
                    "tool poisoning testing",
                    r"Tool and Skill Poisoning Testing",
                ),
                (
                    "memory security testing",
                    r"Memory and RMA Security Testing",
                ),
                (
                    "RLM security testing",
                    r"RLM Security Testing",
                ),
                (
                    "credential and secret security",
                    r"Credential and Secret Security Testing",
                ),
                (
                    "tenant isolation",
                    r"Data and Tenant Isolation Testing",
                ),
                (
                    "network and egress security",
                    r"Network and Egress Security Testing",
                ),
                (
                    "resource exhaustion",
                    r"Resource Exhaustion Testing",
                ),
                (
                    "recovery security",
                    r"Recovery Security Testing",
                ),
                (
                    "emergency controls",
                    r"Emergency Control Testing",
                ),
                (
                    "MCP and A2A security",
                    r"MCP and A2A Security Testing",
                ),
                (
                    "supply-chain security",
                    r"Supply-Chain Security Testing",
                ),
                (
                    "observability and provenance security",
                    r"Observability and Provenance Security Testing",
                ),
                (
                    "negative and fail-closed testing",
                    r"Negative-Path and Fail-Closed Testing",
                ),
                (
                    "adversarial testing",
                    r"Adversarial testing SHALL attempt to defeat the complete security chain",
                ),
                (
                    "fuzz testing",
                    r"Applicable interfaces SHALL undergo fuzz testing",
                ),
                (
                    "real-infrastructure distinction",
                    r"Reference or simulated tests SHALL be distinguished from real-infrastructure tests",
                ),
                (
                    "real infrastructure requirement",
                    r"the applicable real infrastructure SHALL be tested",
                ),
                (
                    "security evidence integrity",
                    r"Evidence SHALL be attributable, reproducible, integrity-protected, and appropriately access-controlled",
                ),
                (
                    "historical evidence separation",
                    r"Historical evidence SHALL NOT be silently represented as current evidence",
                ),
                (
                    "security test traceability",
                    r"Every security test SHALL map to one or more of",
                ),
                (
                    "unmapped test boundary",
                    r"Unmapped security tests SHALL be classified as exploratory or research tests",
                ),
                (
                    "security acceptance gates",
                    r"Gate S1 — Security Test Planning",
                ),
                (
                    "production security readiness gate",
                    r"Gate S10 — Production Security Readiness",
                ),
                (
                    "finding classification",
                    r"Security Finding Classification",
                ),
                (
                    "finding retention",
                    r"No finding SHALL be silently discarded",
                ),
                (
                    "security regression",
                    r"Security regression suites SHALL be versioned and reproducible",
                ),
                (
                    "production certification boundary",
                    r"Passing security tests SHALL NOT by itself establish production certification",
                ),
                (
                    "G47 historical boundary",
                    r"G47 evidence SHALL NOT be used to claim that newly introduced Phase-B security controls are currently implemented or validated",
                ),
                (
                    "CORE security-testing traceability",
                    r"TR-009",
                ),
                (
                    "implementation remains unauthorized",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production implementation remains blocked",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "production certification remains unclaimed",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
                (
                    "no alternate privileged path",
                    r"No model, agent, tool, memory object, RLM process, protocol adapter, recovery checkpoint, or external integration may create an alternate privileged execution path",
                ),
            )

            for label, pattern in semantic_checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 52):
                if self.has(text, rf"^## {section}\."):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-016":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-VAL-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — VALIDATION BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            semantic_checks = (
                (
                    "validation does not grant authority",
                    r"Validation SHALL NOT itself grant authority",
                ),
                (
                    "validation is distinct from authorization",
                    r"Validation Evidence\s*≠\s*Authorization\s*≠\s*Production Acceptance\s*≠\s*Certification",
                ),
                (
                    "validation state model",
                    r"NOT VALIDATED[\s\S]*VALIDATED[\s\S]*ACCEPTED[\s\S]*PRODUCTION-OPERATIONAL[\s\S]*CERTIFIED",
                ),
                (
                    "traceable validation evidence",
                    r"Every accepted Core component SHALL have traceable validation evidence",
                ),
                (
                    "validation evidence traceability",
                    r"Validation evidence without traceability SHALL NOT be treated as sufficient acceptance evidence",
                ),
                (
                    "validation hierarchy",
                    r"Static validation[\s\S]*Unit validation[\s\S]*Component validation[\s\S]*Integration validation",
                ),
                (
                    "security validation",
                    r"Security validation SHALL verify security-boundary requirements",
                ),
                (
                    "negative security validation",
                    r"Security validation SHALL include negative and denial-path testing",
                ),
                (
                    "adversarial validation",
                    r"Adversarial validation SHALL address applicable threats",
                ),
                (
                    "failure and recovery validation",
                    r"Failure validation SHALL verify controlled behavior",
                ),
                (
                    "recovery authority revalidation",
                    r"Recovery SHALL revalidate identity, task, policy, authority, capability, resources",
                ),
                (
                    "reference versus real infrastructure",
                    r"reference.*real-infrastructure",
                ),
                (
                    "evidence classification",
                    r"Evidence Classification",
                ),
                (
                    "evidence provenance",
                    r"Evidence Provenance",
                ),
                (
                    "evidence integrity",
                    r"Evidence Integrity",
                ),
                (
                    "evidence completeness",
                    r"Evidence Completeness",
                ),
                (
                    "evidence reproducibility",
                    r"Evidence Reproducibility",
                ),
                (
                    "validation environment control",
                    r"Validation Environment Control",
                ),
                (
                    "test data governance",
                    r"Test Data and Fixture Governance",
                ),
                (
                    "negative and fail-closed validation",
                    r"Negative and Fail-Closed Validation",
                ),
                (
                    "regression and revalidation",
                    r"Regression and Revalidation",
                ),
                (
                    "independent assurance",
                    r"Independent Assurance",
                ),
                (
                    "acceptance gates",
                    r"Acceptance Gates",
                ),
                (
                    "core baseline acceptance",
                    r"Core Baseline Acceptance",
                ),
                (
                    "expansion authorization boundary",
                    r"Expansion Authorization Boundary",
                ),
                (
                    "production certification boundary",
                    r"Production Certification Boundary",
                ),
                (
                    "historical evidence boundary",
                    r"G47 and Historical Evidence Boundary",
                ),
                (
                    "validation records auditability",
                    r"Validation Records and Auditability",
                ),
                (
                    "validation reporting",
                    r"Validation Reporting",
                ),
                (
                    "CORE-VAL-001",
                    r"CORE-VAL-001",
                ),
                (
                    "CORE-VAL-002",
                    r"CORE-VAL-002",
                ),
                (
                    "CORE-VAL-003",
                    r"CORE-VAL-003",
                ),
                (
                    "CORE-VAL-004",
                    r"CORE-VAL-004",
                ),
                (
                    "TR-008",
                    r"TR-008",
                ),
                (
                    "implementation remains unauthorized",
                    r"Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production remains unclaimed",
                    r"Production Certification:\*\*\s*NOT CLAIMED",
                ),
                (
                    "no false production certification",
                    r"local validation does not equal production certification",
                ),
            )

            for label, pattern in semantic_checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label}")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 42):
                if self.has(text, rf"^# {section}\."):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-015":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-OBS-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — OBSERVABILITY BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
                (
                    "observability authority boundary",
                    r"Observability SHALL provide visibility into system behavior without\s+becoming a source of authority",
                ),
                (
                    "no authorization through observability",
                    r"Telemetry SHALL remain evidence about system behavior rather than a\s+mechanism for permitting system behavior",
                ),
                (
                    "causal provenance",
                    r"The minimum provenance chain SHALL be",
                ),
                (
                    "provenance reconstruction",
                    r"Provenance SHALL support applicable",
                ),
                (
                    "agentic observability",
                    r"Observability SHALL provide visibility across the agentic runtime",
                ),
                (
                    "agentic state separation",
                    r"Observability SHALL distinguish",
                ),
                (
                    "execution is not verification",
                    r"An execution event SHALL NOT itself constitute proof that the intended\s+external effect occurred",
                ),
                (
                    "verification separation",
                    r"Verification evidence SHALL be distinguishable from",
                ),
                (
                    "security telemetry",
                    r"Security telemetry SHALL cover applicable",
                ),
                (
                    "memory observability",
                    r"Memory-related telemetry SHALL remain consistent with the Memory /\s+Provenance Specification",
                ),
                (
                    "model telemetry boundary",
                    r"Model output SHALL NOT be treated as authorization merely because it is\s+observable or logged",
                ),
                (
                    "RMA/RLM separation",
                    r"Observability SHALL preserve the architectural separation between the\s+Recursive Memory Architecture \(RMA\) and Recursive Language Model \(RLM\)",
                ),
                (
                    "RLM authority boundary",
                    r"RLM observability SHALL NOT imply",
                ),
                (
                    "RMA/RLM telemetry separation",
                    r"Observability SHALL NOT collapse RMA state, RLM reasoning, authorization\s+or execution into a single telemetry state",
                ),
                (
                    "resource observability",
                    r"Observability SHALL support visibility into applicable resource",
                ),
                (
                    "recovery observability",
                    r"Recovery operations SHALL generate appropriate auditable telemetry",
                ),
                (
                    "recovery authority revalidation",
                    r"Expired or revoked authority SHALL NOT be represented as valid merely\s+because a recovery checkpoint contains it",
                ),
                (
                    "emergency-control observability",
                    r"Emergency controls SHALL generate auditable provenance",
                ),
                (
                    "emergency-control independence",
                    r"Emergency-control telemetry SHALL remain outside model-controlled\s+authorization paths",
                ),
                (
                    "tamper evidence",
                    r"# 19\. Tamper Evidence",
                ),
                (
                    "evidence integrity",
                    r"Observability data SHALL support detection of applicable",
                ),
                (
                    "evidence completeness",
                    r"Observability SHALL support assessment of whether required events were\s+produced",
                ),
                (
                    "missing evidence boundary",
                    r"Missing evidence SHALL NOT silently be interpreted as successful\s+execution or successful verification",
                ),
                (
                    "sensitive data protection",
                    r"Observability SHALL protect sensitive information",
                ),
                (
                    "data minimization",
                    r"Telemetry SHOULD use data minimization and redaction where appropriate",
                ),
                (
                    "observability access control",
                    r"Observability data SHALL remain subject to applicable",
                ),
                (
                    "no capability escalation through telemetry",
                    r"Observability access SHALL NOT become an indirect capability-escalation\s+path",
                ),
                (
                    "secret boundary",
                    r"Observability SHALL NOT become an unrestricted secret-disclosure\s+mechanism",
                ),
                (
                    "provenance relationship",
                    r"Provenance establishes causal lineage",
                ),
                (
                    "persistence boundary",
                    r"Observability persistence SHALL follow the approved Data Architecture",
                ),
                (
                    "derived telemetry boundary",
                    r"Derived telemetry stores\s+SHALL NOT silently become the authoritative",
                ),
                (
                    "failure behavior",
                    r"# 27\. Failure Behavior",
                ),
                (
                    "observability failure boundary",
                    r"A telemetry subsystem failure\s+SHALL NOT create an alternate execution",
                ),
                (
                    "security execution chain",
                    r"Aegis\s+→ Capability Gateway\s+→ Secure Executor\s+→ Agent Sandbox\s+→ LHICF\s+→ Host",
                ),
                (
                    "operational reconstruction",
                    r"The observability system SHOULD support reconstruction of consequential\s+operations from available evidence",
                ),
                (
                    "environment classification",
                    r"Observability records SHALL identify the environment in which evidence\s+was produced where relevant",
                ),
                (
                    "validation requirements",
                    r"Validation SHALL cover, as applicable",
                ),
                (
                    "CORE-OBS-001",
                    r"CORE-OBS-001\s*[—-]\s*Auditability",
                ),
                (
                    "CORE-OBS-002",
                    r"CORE-OBS-002\s*[—-]\s*Causal Provenance",
                ),
                (
                    "CORE-OBS-003",
                    r"CORE-OBS-003\s*[—-]\s*Tamper Evidence",
                ),
                (
                    "CORE-OBS-004",
                    r"CORE-OBS-004\s*[—-]\s*No False Evidence",
                ),
                (
                    "implementation boundary",
                    r"Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production boundary",
                    r"Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "certification boundary",
                    r"Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 37):
                if self.has(text, rf"^# {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            trailing_whitespace = [
                line
                for line in text.splitlines()
                if line.rstrip() != line
                and not line.endswith("  ")
            ]

            if not trailing_whitespace:
                self.passed(f"{name}: no unintended trailing whitespace")
            else:
                self.failed(f"{name}: trailing whitespace detected")

            return

        if name == "PB-DOC-014":
            checks = (
                (
                    "Document ID",
                    r"\*\*Document ID:\*\*\s*TAOS-CORE-MEM-PROV-001",
                ),
                (
                    "Version",
                    r"\*\*Version:\*\*\s*1\.0\.0",
                ),
                (
                    "Date",
                    r"\*\*Date:\*\*\s*2026-09-22",
                ),
                (
                    "Status",
                    r"\*\*Status:\*\*\s*DRAFT — MEMORY / PROVENANCE BASELINE",
                ),
                (
                    "Architecture Approval",
                    r"\*\*Architecture Approval:\*\*\s*PENDING",
                ),
                (
                    "Implementation Authorization",
                    r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "Production Implementation",
                    r"\*\*Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "Production Certification",
                    r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
                ),
                (
                    "non-authorization boundary",
                    r"SHALL NOT be interpreted as authorization to begin\s+production implementation",
                ),
                (
                    "memory authority boundary",
                    r"Memory SHALL NOT.*authorize",
                ),
                (
                    "scoped memory",
                    r"Memory SHALL be scoped according to applicable",
                ),
                (
                    "memory object contract",
                    r"memory object",
                ),
                (
                    "evidence/source distinction",
                    r"Memory SHALL distinguish information from its supporting evidence",
                ),
                (
                    "provenance",
                    r"Memory provenance SHALL establish",
                ),
                (
                    "trust/confidence/validation separation",
                    r"Trust, confidence and validation SHALL remain distinct concepts",
                ),
                (
                    "model output not trusted memory",
                    r"Model output SHALL NOT automatically receive durable trusted-memory",
                ),
                (
                    "RMA lifecycle",
                    r"# 12\. RMA Lifecycle",
                ),
                (
                    "candidate memory",
                    r"Candidate memory represents",
                ),
                (
                    "durable trusted memory",
                    r"Promotion to trusted durable memory SHALL require",
                ),
                (
                    "conflict detection",
                    r"The memory architecture SHALL support detection of conflicting",
                ),
                (
                    "supersession",
                    r"Supersession SHALL preserve historical lineage",
                ),
                (
                    "retention and expiration",
                    r"Memory SHALL support applicable retention and expiration controls",
                ),
                (
                    "revocation and deletion",
                    r"Memory SHALL support applicable revocation and deletion controls",
                ),
                (
                    "integrity/versioning",
                    r"Memory objects SHALL support integrity protection and versioning",
                ),
                (
                    "authoritative persistence",
                    r"Authoritative memory persistence SHALL follow the approved Data",
                ),
                (
                    "retrieval cannot grant authority",
                    r"Retrieval SHALL NOT grant new capability or authority",
                ),
                (
                    "derived retrieval boundary",
                    r"Derived structures SHOULD be reconstructible from authoritative state",
                ),
                (
                    "RMA/RLM separation",
                    r"Recursive Memory Architecture \(RMA\) and Recursive Language Model \(RLM\)",
                ),
                (
                    "RLM output is not authorization",
                    r"RLM outputs SHALL be treated as reasoning or evidence, not authorization",
                ),
                (
                    "world-state boundary",
                    r"Memory SHALL NOT unilaterally redefine authoritative external state",
                ),
                (
                    "causal provenance",
                    r"The minimum provenance chain SHALL be",
                ),
                (
                    "memory-to-agentic lineage",
                    r"This lineage SHALL support reconstruction of how information entered",
                ),
                (
                    "auditability",
                    r"Applicable memory lifecycle and provenance operations SHALL be",
                ),
                (
                    "security/privacy boundary",
                    r"# 29\. Security and Privacy Boundary",
                ),
                (
                    "memory poisoning resistance",
                    r"# 30\. Memory Poisoning Resistance",
                ),
                (
                    "backup/restore/recovery",
                    r"Authoritative memory state SHALL participate in the Data Architecture",
                ),
                (
                    "fail-closed behavior",
                    r"memory integrity, provenance, scope or validation state cannot be",
                ),
                (
                    "validation requirements",
                    r"Validation SHALL cover, as applicable",
                ),
                (
                    "CORE-MEM-001",
                    r"CORE-MEM-001\s*[—-]\s*Scoped Memory",
                ),
                (
                    "CORE-MEM-002",
                    r"CORE-MEM-002\s*[—-]\s*Provenance",
                ),
                (
                    "CORE-MEM-003",
                    r"CORE-MEM-003\s*[—-]\s*Trust",
                ),
                (
                    "CORE-MEM-004",
                    r"CORE-MEM-004\s*[—-]\s*Validation",
                ),
                (
                    "CORE-MEM-005",
                    r"CORE-MEM-005\s*[—-]\s*Conflict Handling",
                ),
                (
                    "CORE-MEM-006",
                    r"CORE-MEM-006\s*[—-]\s*Memory Lifecycle",
                ),
                (
                    "CORE-MEM-007",
                    r"CORE-MEM-007\s*[—-]\s*Memory Data Integrity",
                ),
                (
                    "CORE-MEM-008",
                    r"CORE-MEM-008\s*[—-]\s*RMA Separation",
                ),
                (
                    "implementation boundary",
                    r"Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production boundary",
                    r"Production Implementation:\*\*\s*BLOCKED",
                ),
                (
                    "certification boundary",
                    r"Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(f"{name}: missing required {label}")

            for section in range(1, 39):
                if self.has(text, rf"^# {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            return

        if name == "PB-DOC-013":
            checks = (
                (
                    "Status",
                    r"\*\*Status:\*\*\s*.+",
                ),
                (
                    "non-authorization boundary",
                    r"does not authorize implementation",
                ),
                (
                    "authoritative state",
                    r"authoritative primary state|authoritative memory state",
                ),
                (
                    "strong consistency",
                    r"strongly consistent",
                ),
                (
                    "transactional consistency",
                    r"transactional consistency|transactional model",
                ),
                (
                    "derived-state boundary",
                    r"secondary indexes\s*-\s*derived retrieval structures",
                ),
                (
                    "authoritative-state hierarchy",
                    r"Authoritative State.*Derived State.*Cache.*Retrieval Index.*Model Context",
                ),
                (
                    "scope isolation",
                    r"scope isolation",
                ),
                (
                    "provenance",
                    r"provenance",
                ),
                (
                    "integrity protection",
                    r"integrity protection",
                ),
                (
                    "memory lifecycle",
                    r"Memory Lifecycle",
                ),
                (
                    "backup architecture",
                    r"Backup Architecture",
                ),
                (
                    "restore architecture",
                    r"Restore Architecture",
                ),
                (
                    "migration architecture",
                    r"Migration Architecture",
                ),
                (
                    "corruption detection",
                    r"Corruption Detection",
                ),
                (
                    "corruption recovery",
                    r"Corruption Recovery",
                ),
                (
                    "secondary reconstruction",
                    r"secondary-index reconstruction|secondary structures.*rebuild",
                ),
                (
                    "fail-closed data behavior",
                    r"fail closed\s+where security or integrity cannot be\s+established",
                ),
                (
                    "RMA authority boundary",
                    r"RMA SHALL NOT:\s*-\s*grant capabilities\s*-\s*grant delegated authority\s*-\s*authorize execution",
                ),
                (
                    "RMA/RLM separation",
                    r"RMA and RLM Separation",
                ),
                (
                    "restricted authoritative-memory access",
                    r"SHALL\s+receive unrestricted direct access to authoritative memory",
                ),
                (
                    "CORE-MEM-007",
                    r"CORE-MEM-007\s*[—-]\s*Memory Data Integrity",
                ),
                (
                    "TR-004",
                    r"TR-004\s*[—-]\s*Memory Data Integrity",
                ),
                (
                    "TR-004 strong consistency contract",
                    r"Primary authoritative state SHALL remain strongly consistent",
                ),
                (
                    "TR-004 recovery validation",
                    r"Backup,\s*restore,\s*migration,\s*and corruption recovery SHALL\s+be tested",
                ),
                (
                    "implementation boundary",
                    r"Implementation Authorization:\*\*\s*NOT AUTHORIZED",
                ),
                (
                    "production certification boundary",
                    r"Production Certification:\*\*\s*NOT CLAIMED",
                ),
            )

            for label, pattern in checks:
                if self.has(text, pattern):
                    self.passed(f"{name}: {label} present")
                else:
                    self.failed(
                        f"{name}: missing required {label}"
                    )

            for section in range(1, 36):
                if self.has(text, rf"^## {section}\.",):
                    self.passed(f"{name}: section {section} present")
                else:
                    self.failed(f"{name}: missing section {section}")

            return

        required = (
            ("Status", r"\*\*Status:\*\*\s*.+"),
            (
                "Architecture Approval",
                r"\*\*Architecture Approval:\*\*\s*PENDING",
            ),
            (
                "Implementation Authorization",
                r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
            ),
        )

        for label, pattern in required:
            if self.has(text, pattern):
                self.passed(f"{name}: {label} metadata present")
            else:
                self.failed(f"{name}: missing required {label} metadata")

    def validate_gap_register(self, text: str) -> None:
        required_rows = {
            "PB-DOC-013": EXPECTED_CLOSED_STATE,
            "PB-DOC-014": EXPECTED_CLOSED_STATE,
            "PB-DOC-015": EXPECTED_CLOSED_STATE,
            "PB-DOC-016": EXPECTED_CLOSED_STATE,
            "PB-DOC-017": EXPECTED_CLOSED_STATE,
            "PB-DOC-018": EXPECTED_CLOSED_STATE,
            "PB-DOC-019": EXPECTED_CLOSED_STATE,
            "PB-DOC-020": EXPECTED_CLOSED_STATE,
        }

        for doc_id, state in required_rows.items():
            pattern = rf"\|\s*{re.escape(doc_id)}\s*\|[^|]+\|\s*[^|]+\|\s*{re.escape(state)}\s*\|"

            if self.has(text, pattern):
                self.passed(f"Gap Register: {doc_id} CLOSED")
            else:
                self.failed(
                    f"Gap Register: {doc_id} missing expected CLOSED state"
                )

        pb020 = (
            r"\|\s*PB-DOC-020\s*\|[^|]+\|\s*CRITICAL\s*\|\s*"
            + re.escape(EXPECTED_CLOSED_STATE)
            + r"\s*\|"
        )

        if self.has(text, pb020):
            self.passed("Gap Register: PB-DOC-020 CLOSED")
        else:
            self.failed(
                "Gap Register: PB-DOC-020 missing expected CLOSED state"
            )

        governance = (
            (
                "Architecture Approval",
                r"\*\*Architecture Approval:\*\*\s*PENDING",
            ),
            (
                "Implementation Authorization",
                r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
            ),
            (
                "Production Implementation",
                r"\*\*Production Implementation:\*\*\s*BLOCKED",
            ),
            (
                "Production Certification",
                r"\*\*Production Certification:\*\*\s*NOT CLAIMED",
            ),
        )

        for label, pattern in governance:
            if self.has(text, pattern):
                self.passed(f"Gap Register governance: {label}")
            else:
                self.failed(
                    f"Gap Register governance: missing {label}"
                )

    def validate_cross_document_security_boundaries(
        self,
        documents: dict[str, str],
    ) -> None:
        # These are only checked where they are architecturally applicable.
        #
        # PB-DOC-014 is a Memory / Provenance specification. It is NOT required
        # to reproduce every execution-boundary term such as LHICF.
        #
        # PB-DOC-015..019 must preserve the core execution/security boundary
        # terminology relevant to their operational scope.

        scoped_requirements = {
            "PB-DOC-015": ("Aegis", "Capability Gateway"),
            "PB-DOC-016": ("Aegis", "Capability Gateway"),
            "PB-DOC-017": (
                "Aegis",
                "Capability Gateway",
                "Secure Executor",
                "Sandbox",
                "LHICF",
            ),
            "PB-DOC-018": (
                "Aegis",
                "Capability Gateway",
                "Secure Executor",
                "Sandbox",
                "LHICF",
            ),
            "PB-DOC-019": (
                "Aegis",
                "Capability Gateway",
                "Secure Executor",
                "Sandbox",
                "LHICF",
            ),
        }

        for name, terms in scoped_requirements.items():
            text = documents.get(name, "")

            for term in terms:
                if self.has(text, re.escape(term)):
                    self.passed(
                        f"{name}: security boundary term present: {term}"
                    )
                else:
                    self.failed(
                        f"{name}: missing applicable security boundary term: {term}"
                    )

    def validate_rma_rlm_separation(
        self,
        documents: dict[str, str],
    ) -> None:
        for name in (
            "PB-DOC-014",
            "PB-DOC-015",
            "PB-DOC-016",
            "PB-DOC-017",
            "PB-DOC-018",
            "PB-DOC-019",
        ):
            text = documents.get(name, "")

            rma = self.has(text, r"\bRMA\b|Recursive Memory Architecture")
            rlm = self.has(text, r"\bRLM\b|Recursive Language Model")

            if rma and rlm:
                self.passed(f"{name}: RMA/RLM terminology present")
            else:
                self.failed(
                    f"{name}: RMA/RLM separation terminology incomplete"
                )

    def validate_traceability(self, text: str) -> None:
        required_refs = ("TR-007", "TR-008", "TR-009")

        for ref in required_refs:
            if self.has(text, rf"\b{re.escape(ref)}\b"):
                self.passed(f"Traceability Matrix: {ref} present")
            else:
                self.failed(f"Traceability Matrix: {ref} missing")

        # Authorization is intentionally case-insensitive because the matrix
        # uses both "Implementation authorization" and
        # "Implementation Authorization".
        auth_pattern = (
            r"\*\*Implementation\s+Authorization:\*\*\s*"
            r"NOT\s+AUTHORIZED"
        )

        if self.has(text, auth_pattern):
            self.passed(
                "Traceability Matrix: implementation authorization boundary present"
            )
        else:
            self.failed(
                "Traceability Matrix: implementation authorization boundary missing"
            )

    def validate_pbdoc019(self, text: str) -> None:
        required_terms = (
            "replay protection",
            "policy version",
            "fail-closed",
            "provenance",
            "evidence",
            "revalidation",
        )

        for term in required_terms:
            if self.has(text, re.escape(term)):
                self.passed(f"PB-DOC-019: recovery control present: {term}")
            else:
                self.failed(
                    f"PB-DOC-019: missing recovery control: {term}"
                )

    def validate_governance_consistency(
        self,
        documents: dict[str, str],
    ) -> None:
        # Individual documents retain their own DRAFT baseline status.
        # Closure state belongs to the Gap Register. Therefore this validator
        # deliberately does NOT require the individual documents to contain:
        #
        # CLOSED — BASELINE VALIDATED; IMPLEMENTATION VALIDATION PENDING
        #
        # This prevents false failures caused by conflating document status
        # with governance closure state.

        for name, text in documents.items():
            if self.has(
                text,
                r"\*\*Implementation Authorization:\*\*\s*NOT AUTHORIZED",
            ):
                self.passed(
                    f"{name}: implementation remains NOT AUTHORIZED"
                )
            else:
                self.failed(
                    f"{name}: implementation authorization boundary missing"
                )

    def run(self) -> int:
        print("=" * 78)
        print("LYRION TRUE AGENTIC OS — PHASE-B DOCUMENTATION REVALIDATION")
        print("=" * 78)
        print(f"Repository: {ROOT}")
        print()

        documents: dict[str, str] = {}

        for name, path in DOCUMENTS.items():
            text = self.require_file(name, path)
            if text is not None:
                documents[name] = text

        print()

        if GAP_REGISTER.is_file():
            gap_text = self.read(GAP_REGISTER)
            self.passed("Gap Register: file present")
            self.validate_gap_register(gap_text)
        else:
            self.failed(f"Gap Register missing: {GAP_REGISTER}")

        print()

        for name, text in documents.items():
            self.validate_document_metadata(name, text)

        print()

        self.validate_governance_consistency(documents)

        print()

        if "PB-DOC-002" in documents:
            self.validate_document_metadata(
                "PB-DOC-002",
                documents["PB-DOC-002"],
            )

        print()

        self.validate_cross_document_security_boundaries(documents)

        print()

        self.validate_rma_rlm_separation(documents)

        print()

        if TRACEABILITY.is_file():
            traceability_text = self.read(TRACEABILITY)
            self.passed("Traceability Matrix: file present")
            self.validate_traceability(traceability_text)
        else:
            self.failed(f"Traceability Matrix missing: {TRACEABILITY}")

        print()

        if "PB-DOC-019" in documents:
            self.validate_pbdoc019(documents["PB-DOC-019"])

        print()
        print("=" * 78)
        print("VALIDATION SUMMARY")
        print("=" * 78)

        for item in self.passes:
            print(f"PASS: {item}")

        for item in self.opens:
            print(f"OPEN: {item}")

        for item in self.errors:
            print(f"FAIL: {item}")

        print()

        if self.errors:
            print("RESULT: FAIL")
            print(f"Failures: {len(self.errors)}")
            return 1

        print("RESULT: PASS")
        print(f"Passes: {len(self.passes)}")
        print("No documentation files were modified.")
        print("=" * 78)

        return 0


if __name__ == "__main__":
    sys.exit(Validator().run())

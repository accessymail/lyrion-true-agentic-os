# LYRION True Agentic OS — Core PRD Traceability & Acceptance Matrix

**Document ID:** TAOS-CORE-TRM-001
**Version:** 1.0.0
**Status:** DRAFT — REVIEW ARTIFACT
**Parent:** LYRION_UNIFIED_CORE_REQUIREMENTS_PRD_v1.md
**Date:** 2026-09-22

---

## 1. Purpose

This document establishes traceability between the Unified Core PRD,
the canonical TAOS architecture, security boundaries, validation
methods and acceptance evidence.

It is a review artifact and does not itself authorize implementation.

---

## 2. Traceability Model

Every accepted requirement SHALL ultimately trace:

Requirement
→ Architecture
→ Component
→ Security Control
→ Contract
→ Implementation
→ Validation
→ Evidence
→ Acceptance

---

## 3. Authoritative Baseline

The matrix SHALL preserve the established source hierarchy:

1. Canonical TAOS Architecture
2. TAOS Manifest
3. Normative TAOS Requirements
4. TAOS Platform Blueprint
5. Security Threat Model and Controls
6. Implementation / Validation / Acceptance Gates
7. Supporting RLM / RMA / Migration / Gap documentation

---

# 4. Requirement Family Traceability

| Family | IDs | Architectural Mapping | Primary Security Boundary | Validation |
|---|---|---|---|---|
| Functional | CORE-FR-001..014 | Interaction, Identity, Intelligence, Application Runtime, Live Development & Execution Workspace | Identity / Session / Aegis / Capability Gateway / Execution Admission | Unit + Integration + E2E + workspace/security-boundary validation |
| Agentic | CORE-AG-001..008 | Agent Identity, Registry, ACP, Delegation, Communication | Aegis + Authority | Contract + Identity + ACP + Adversarial |
| Security | CORE-SEC-001..010 | Aegis, HITL, Governance | Independent authorization | Security + adversarial |
| Execution | CORE-EXEC-001..006 | Capability Gateway, Secure Executor, Sandbox, LHICF | Execution Admission | Integration + host E2E + escape tests |
| Memory | CORE-MEM-001..008 | RMA / Memory Fabric | Scope + provenance + validation | Integrity + poisoning + lifecycle |
| RLM | CORE-RLM-001..003 | Cognitive / RLM Runtime | External resource + sandbox controls | Recursion + isolation + exhaustion |
| Observability | CORE-OBS-001..004 | Provenance / Audit / Evaluation | Integrity + redaction | Tamper + completeness |
| Reliability | CORE-REL-001..005 | Durable Execution / Recovery | Authority revalidation | Failure injection + recovery |
| Resources | CORE-RES-001..002 | Resource Governance | External enforcement | Exhaustion / runaway tests |
| Interoperability | CORE-INT-001..003 | MCP / A2A / API / Connector adapters | Trust + Aegis + Capability Gateway | Protocol + abuse tests |
| Host | CORE-HOST-001..003 | LHICF / Host adapters | Secure Executor + Sandbox | Host E2E |
| Privacy | CORE-PRIV-001..003 | Data / Memory / Runtime | Access + isolation + secrets | Leakage + retention tests |
| Supply Chain | CORE-SC-001..002 | Resource / Trust Admission | Integrity + provenance | Dependency + provenance validation |
| Performance | CORE-PERF-001..003 | Runtime / Resource Fabric | Security-preserving limits | Load + exhaustion |
| UI | CORE-UI-001..003 | HUI/FUI / Interaction Fabric | No UI authority | Browser/E2E |
| Validation | CORE-VAL-001..004 | Validation / Evidence Plane | Evidence integrity | Full validation suite |

---

# 5. Mandatory Canonical Requirement Reconciliation

## TR-001 — Inter-Agent Message Integrity

**Source requirement:** Communication SHALL be attributable,
integrity-protected, scoped and replay-resistant.

**Current PRD:** CORE-AG-007 explicitly establishes attribution, integrity protection, replay resistance, scope enforcement, impersonation resistance and cross-task/tenant isolation. CORE-AG-007 also establishes that message content does not grant authority.

**Finding:** Requirement definition closed in the Core PRD; implementation validation remains required.

**Required closure:**

Communication SHALL explicitly require:

- attribution
- integrity protection
- replay resistance
- scope enforcement
- impersonation resistance
- cross-task/tenant isolation
- no authority through message content

**Validation:**

- tamper tests
- replay tests
- impersonation tests
- cross-scope leakage tests

**Status:** CLOSED — REQUIREMENT DEFINED; IMPLEMENTATION VALIDATION PENDING

---

## TR-002 — RLM Isolation

**Source requirement:** RLM code/REPL execution SHALL occur only
inside governed isolation.

**Current PRD:** CORE-RLM-001..003 establish bounded recursion, governed isolation, no authority/isolation bypass and output validation.

**Finding:** Requirement definition closed in the Core PRD; implementation validation remains required.

**Required closure:**

RLM execution environments SHALL be isolated according to the
approved execution/sandbox architecture.

**Validation:**

- sandbox escape tests
- filesystem isolation tests
- network isolation tests
- resource exhaustion tests

**Status:** CLOSED — REQUIREMENT DEFINED; IMPLEMENTATION VALIDATION PENDING

---

## TR-003 — Memory Lifecycle

**Source requirement:** Memory SHALL support provenance, source,
trust, confidence, scope, sensitivity, integrity/version,
retention, revocation, conflict handling, deletion and audit.

**Current PRD:** CORE-MEM-001..008 establish scoped memory, provenance, trust, validation, conflict handling, lifecycle, data integrity and explicit RMA/RLM separation.

**Finding:** Requirement definition closed in the Core PRD; the
Memory / Provenance baseline now provides the detailed lifecycle,
provenance and memory-governance specification. Implementation
validation remains required.

**Resolution:** Memory / Provenance Specification
`TAOS-CORE-MEM-PROV-001` defines scoped memory, provenance,
trust/validation separation, lifecycle controls, conflict handling,
retention/revocation/deletion, integrity/versioning, causal provenance,
auditability and RMA/RLM separation. Cross-document consistency was
validated against the Core Data Architecture and Core Architecture
§§22–24 and §29.

**Required closure:**

The Core PRD SHALL explicitly preserve lifecycle controls for:

- integrity/version
- retention
- revocation
- deletion
- audit

**Status:** CLOSED — MEMORY / PROVENANCE BASELINE VALIDATED; IMPLEMENTATION VALIDATION PENDING

---

## TR-004 — Memory Data Integrity

**Source requirement:** Primary relational state SHALL remain strongly
consistent and secondary indexes SHOULD be reconstructible where
feasible.

Backup/restore, migration and corruption recovery SHALL be tested
before production acceptance.

**Current PRD:** Not sufficiently explicit.

**Finding:** TRACE TO DATA ARCHITECTURE.

**Resolution:** Data Architecture baseline TAOS-CORE-DATA-ARCH-001
defines authoritative primary-state consistency, secondary-index
reconstruction, backup/restore, migration, corruption detection and
corruption recovery requirements. Cross-document consistency review
completed against CORE-MEM-007 and Core Architecture §24.

**Status:** CLOSED — DATA ARCHITECTURE BASELINE VALIDATED;
IMPLEMENTATION VALIDATION PENDING

---

## TR-005 — Supply-Chain Admission

**Source requirement:** Models, tools, agents, dependencies, images,
adapters, MCP servers, A2A peers and connectors require
evidence-backed admission.

**Current PRD:** CORE-SC-001..002 explicitly establish evidence-based supply-chain admission and prohibit privileged authority merely through integration.

**Finding:** Requirement definition closed in the Core PRD; implementation validation remains required.

**Required evidence:**

- provenance
- version
- integrity
- vulnerability state
- ownership
- license
- security review
- approval status

**Status:** CLOSED — REQUIREMENT DEFINED; IMPLEMENTATION VALIDATION PENDING

---

## TR-006 — Agent Swarm Governance

**Source requirement:** Swarms require identity, lineage, bounded
depth/width, capability attenuation, budgets, namespace isolation,
communication authorization, cancellation and emergency stop.

**Current PRD:** CORE-AG-008 establishes swarm as an incremental Agentic Expansion capability rather than a prerequisite for the foundational Core.

**Finding:** Core boundary decision resolved in the Core PRD; swarm is deferred Agentic Expansion.

The Core PRD records swarm as a deferred Agentic Expansion capability. Swarm implementation remains subject to the same Aegis, delegated-authority, capability, execution, sandbox, provenance and verification boundaries.

**Status:** CLOSED — DEFERRED AGENTIC EXPANSION

---

# 6. Security Invariant Traceability

The following invariant SHALL remain globally enforced:

OBSERVATION
≠ OPPORTUNITY
≠ REASONING
≠ DECISION
≠ AGENCY
≠ AUTHORITY
≠ CAPABILITY
≠ EXECUTION
≠ VERIFICATION

Trace:

Model output
→ non-authoritative

Agent intent
→ non-authoritative

Memory
→ non-authoritative

Voice identity
→ non-authoritative

Frontend state
→ non-authoritative

MCP/A2A/API/plugin message
→ non-authoritative

Aegis
→ independent security/policy/trust authority

Capability Gateway
→ execution admission

Secure Executor
→ authorized execution

Sandbox
→ isolation

LHICF
→ host mediation

Verification
→ independent outcome confirmation

---

# 7. Canonical Execution Traceability

The Core SHALL preserve:

Human Intent
→ Authenticated Principal
→ Lyri Interpretation
→ Root Task
→ Goal / Plan
→ PIAE / Cognitive Runtime
→ Agent Control Plane
→ Agent
→ Delegated Authority
→ Action Proposal
→ Aegis
→ HITL when required
→ Capability Authorization
→ Execution Admission
→ Secure Executor
→ Sandbox
→ LHICF
→ Host / External System
→ Independent Verification
→ World State
→ Memory / Audit / Provenance
→ Lyri
→ Human

No alternate privileged path is permitted.

---

# 8. Acceptance Evidence Classes

Each requirement SHALL eventually identify:

- Architecture evidence
- Contract evidence
- Implementation evidence
- Unit evidence
- Integration evidence
- Security evidence
- Adversarial evidence where applicable
- E2E evidence where applicable
- Operational evidence where applicable
- Production evidence where applicable

A local/reference PASS SHALL NOT automatically become production
acceptance.

---

# 9. Requirement Closure Rule

A requirement SHALL NOT be marked ACCEPTED merely because:

- a document exists;
- an interface exists;
- code compiles;
- unit tests pass;
- a reference implementation works;
- an architectural diagram exists.

Acceptance requires the evidence appropriate to the requirement.

---

# 10. Current Review Decision

**Structural PRD validation:** PASS

**Architecture alignment:** PASS WITH FINDINGS

**Traceability:** PARTIAL — THIS MATRIX ESTABLISHES THE BASELINE

**Completeness:** OPEN

**Security reconciliation:** OPEN

**Swarm boundary decision:** OPEN

**PRD approval:** PENDING

**Implementation authorization:** NOT AUTHORIZED

---

# 11. Required Closure Sequence

1. Preserve TR-001 closure and validate implementation evidence
2. Preserve TR-002 closure and validate implementation evidence
3. Preserve TR-003 closure and validate implementation evidence
4. Resolve TR-004 through the approved Data Architecture
5. Preserve TR-005 closure and validate implementation evidence
6. Preserve TR-006 as Deferred Agentic Expansion
7. Update Core PRD
8. Re-run structural validation
9. Perform final architecture traceability review
10. Perform security consistency review
11. Record PRD approval decision

Only after these steps may the Core PRD become an approved
requirements baseline.

---

## TR-007 — Observability Specification

**Source requirements:** CORE-OBS-001 through CORE-OBS-004.

**Resolution:** Observability Specification `TAOS-CORE-OBS-001`
defines auditability, causal provenance, tamper evidence, evidence
classification, security telemetry, agentic runtime observability,
execution-to-verification visibility, sensitive-data protection,
observability access control, RMA/RLM observability separation,
authoritative/derived telemetry boundaries, recovery and emergency-
control observability, and validation requirements.

Cross-document consistency was validated against the Unified Core
Architecture §§29–30, Unified Core Data Architecture, Memory /
Provenance Specification, and Phase-B Security Architecture.

**Technical Validation:** PASS — PB-DOC-015 final validation gate.

**Status:** CLOSED — OBSERVABILITY BASELINE VALIDATED; IMPLEMENTATION
VALIDATION PENDING

**Implementation Authorization:** NOT AUTHORIZED

---

## TR-008 — Core Validation Specification

**Source requirements:** CORE-VAL-001 through CORE-VAL-004.

**Requirement coverage:** CORE-VAL-001, CORE-VAL-002, CORE-VAL-003,
and CORE-VAL-004 are explicitly covered by the Core Validation
Specification `TAOS-CORE-VAL-001`.

**Resolution:** Core Validation Specification `TAOS-CORE-VAL-001`
defines traceable validation evidence, applicable validation methods,
reference versus real-infrastructure validation, evidence classification
and provenance, security and adversarial validation, failure and recovery
validation, performance and resource validation, frontend/browser
validation, voice/realtime validation, provenance validation, Core Gates
A–H, G47 historical-evidence boundaries, and separation of validation
evidence from authorization, production acceptance and certification.

**Validation scope:** Core Gates A–H cover the applicable baseline
validation and acceptance path. Validation includes structural,
integration, security, adversarial, failure/recovery, performance/resource,
frontend/browser, voice/realtime, provenance, evidence-integrity, and
real-infrastructure validation as applicable.

Final semantic validation and final closure-readiness validation both
passed. Cross-document consistency was validated against the Unified Core
Architecture, Unified Core Data Architecture, Memory / Provenance
Specification, Observability Specification, and Phase-B Security
Architecture.

**Technical Validation:** PASS — PB-DOC-016 final closure-readiness
validation gate.

**Status:** CLOSED — VALIDATION BASELINE VALIDATED; IMPLEMENTATION
VALIDATION PENDING

**Architecture Approval:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Implementation:** BLOCKED

**Production Boundary:** PRODUCTION implementation remains BLOCKED;
production certification is NOT CLAIMED.

**Production Certification:** NOT CLAIMED


---

## TR-009 — Security Testing Specification

**Source requirements:** Core Security and validation requirements applicable to the Unified Core, including the security-testing controls defined by the approved Phase-B Security Architecture and CORE-VAL-001 through CORE-VAL-004 where security validation is applicable.

**Requirement coverage:** Security-testing requirements are governed by the Security Testing Specification `TAOS-CORE-SEC-TEST-001`, including identity, authentication, authorization, delegated authority, Agent Control Plane, inter-agent security, swarm boundaries, Aegis, HITL, Capability Gateway, Execution Admission, Secure Executor, Sandbox, LHICF, Universal Computer, Application Harness, injection, tool/skill poisoning, Memory/RMA, RLM, secrets, isolation, network/egress, resource exhaustion, recovery, emergency controls, MCP/A2A, supply-chain security, observability/provenance, negative-path, adversarial, fuzz, and real-infrastructure security testing.

**Resolution:** Security Testing Specification `TAOS-CORE-SEC-TEST-001` defines the security validation baseline, evidence requirements, security-test traceability, Security Gates S1–S10, security finding classification, regression/retesting, production-security boundary, and G47 historical-evidence boundary.

**Technical Validation:** PASS — PB-DOC-017 final baseline validation gate.

**Status:** CLOSED — SECURITY TESTING BASELINE VALIDATED; IMPLEMENTATION VALIDATION PENDING

**Architecture Approval:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Implementation:** BLOCKED

**Production Certification:** NOT CLAIMED

---

## End of Document

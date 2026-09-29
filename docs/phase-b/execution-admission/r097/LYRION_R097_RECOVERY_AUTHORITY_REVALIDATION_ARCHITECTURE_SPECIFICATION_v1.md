# LYRION True Agentic OS

# R097 — Recovery Authority Revalidation Architecture Specification

**Document ID:** PB-DOC-009-R097-ARCH  
**Version:** 1.0.0  
**Classification:** Phase-B Architecture / Security Control  
**Parent Specification:** PB-DOC-009 — Unified Core Execution Admission  
**Requirement:** R097  
**Status:** ARCHITECTURE DESIGN DRAFT  
**Implementation:** NOT AUTHORIZED BY THIS DOCUMENT  
**Production Operation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the architecture required to satisfy R097:

> Expired or revoked authority shall not be restored from checkpoint or recovery state.

Recovery may restore durable work state and execution lineage, but SHALL NOT restore execution authority merely because previous authorization or admission state existed before interruption.

---

## 2. Governing Principle

> **Recovery may restore work state, but it must never restore execution authority.**

The following distinctions SHALL remain permanent:

Work State ≠ Authority ≠ Capability ≠ Authorization ≠ Execution Admission ≠ Execution

Durable identifiers such as `execution_id` and `opportunity_id` preserve lineage and correlation. They SHALL NOT constitute authorization.

---

## 3. Existing Architecture

The R097 design SHALL reuse the existing:

- RecoveryManager
- PersistentRecoveryOrchestrator
- ExecutionStore
- OpportunityStore
- PIAEActionLoop
- CapabilityGateway
- AegisAuthorizationService
- AuthorizationGuard
- ExecutionAdmission
- PersistentExecutionRunner

Existing governed security chain:

AegisAuthorizationService → AuthorizationGuard → CapabilityGateway → ExecutionAdmission → PIAE → PersistentExecutionRunner

R097 SHALL NOT introduce an independent recovery authorization mechanism.

---

## 4. Architectural Gap

Repository investigation established persistent recovery, execution lineage, Aegis authorization, Capability Gateway admission, and the normal PIAE execution path.

The investigation did not establish a production runtime bridge proving that recovered work always re-enters the fresh authorization and admission path.

Therefore R097 requires an explicit governed recovery-to-fresh-admission architecture before implementation.


## 5. Required Governed Recovery Flow

The target architecture SHALL be:

RECOVERED EXECUTION
↓
LOAD PERSISTENT EXECUTION
↓
RESOLVE OPPORTUNITY
↓
RECONSTRUCT CURRENT EXECUTION CONTEXT
↓
REVALIDATE PRINCIPAL
↓
REVALIDATE DELEGATED AUTHORITY
↓
REVALIDATE POLICY
↓
REVALIDATE SECURITY STATE
↓
REVALIDATE EXPIRY
↓
REVALIDATE REVOCATION
↓
REVALIDATE TARGET
↓
CREATE FRESH CAPABILITY REQUEST
↓
AEGIS AUTHORIZATION
↓
CAPABILITY GATEWAY
↓
FRESH EXECUTION ADMISSION
↓
NORMAL PIAE GOVERNED PATH
↓
SECURE EXECUTION
↓
VERIFICATION
↓
PROVENANCE / AUDIT

---

## 6. Recovery Boundary

Recovery MAY:

- identify recoverable work;
- load durable execution state;
- inspect lease state;
- preserve execution lineage;
- resolve the associated opportunity;
- restore eligible work state;
- request governed re-evaluation.

Recovery SHALL NOT:

- grant authority;
- restore authorization;
- restore an old execution admission;
- bypass Aegis;
- bypass Capability Gateway;
- directly authorize execution;
- directly invoke privileged execution.

---

## 7. Current-State Reconstruction

Before resumed execution is permitted, the recovery path SHALL reconstruct the current execution context from authoritative state.

Where applicable, reconstruction SHALL account for:

- principal;
- agent identity;
- task;
- delegated authority;
- capability;
- target;
- operation;
- policy;
- security state;
- resource state;
- approval state;
- expiry;
- revocation;
- opportunity state;
- execution lineage.

Missing or inconsistent required state SHALL fail closed.

---

## 8. Authority Revalidation

Recovery SHALL NOT assume that authority existing before interruption remains valid.

Current authoritative state SHALL be evaluated.

Expired authority, revoked authority, invalid principal, invalid delegation, incompatible policy, incompatible target, invalid security state, invalid approval, or unavailable execution context SHALL prevent reuse of previous authority.


## 9. Expiry and Revocation

Expired or revoked authority SHALL NOT be restored from checkpoint state.

A historical ALLOWED result SHALL NOT override current EXPIRED or REVOKED state.

Recovery SHALL perform current authorization evaluation before resumed execution.

---

## 10. Policy and Target Revalidation

Recovery SHALL evaluate current applicable policy and target state.

Historical policy decisions SHALL NOT automatically remain authoritative after interruption.

Policy incompatibility, target incompatibility, or unavailable authoritative security state SHALL fail closed.

---

## 11. Fresh Capability Request

Recovered work SHALL create a new governed capability request representing the current execution context.

An old authorization result or execution admission SHALL NOT be blindly copied into the resumed execution path.

---

## 12. Aegis and Capability Gateway

The fresh capability request SHALL pass through:

AegisAuthorizationService.authorize()

The resulting authorization SHALL pass through the existing Capability Gateway.

Canonical relationship:

CapabilityRequest
→ AegisAuthorizationService
→ AuthorizationResult
→ CapabilityGateway
→ ExecutionAdmission

The Capability Gateway SHALL remain the authoritative execution-admission boundary.

---

## 13. Fresh Execution Admission

Every resumed execution attempt SHALL receive a fresh execution admission.

A previous execution admission SHALL NOT be restored merely because it was persisted or represented in checkpoint state.

---

## 14. PIAE and Secure Execution

After successful fresh admission, recovered work SHALL enter the existing governed PIAE path.

Recovery SHALL NOT directly invoke the Secure Executor or privileged host execution boundary.

Target:

Recovery
→ Current Context
→ Fresh CapabilityRequest
→ Aegis
→ CapabilityGateway
→ ExecutionAdmission
→ PIAEActionLoop
→ PersistentExecutionRunner
→ Secure Execution

---

## 15. Fail-Closed Requirements

Recovery SHALL fail closed when:

- required execution state is missing;
- opportunity cannot be resolved;
- authority cannot be reconstructed;
- authorization is ambiguous;
- expiry is uncertain;
- revocation is uncertain;
- policy is unavailable or incompatible;
- target cannot be validated;
- identity cannot be validated;
- fresh authorization cannot be produced;
- fresh admission cannot be produced;
- recovery state is unsupported.

No ambiguous recovery condition SHALL silently become executable authority.


## 16. Checkpoint Security Rule

Checkpoint state SHALL be treated as historical execution state.

Checkpoint state MAY provide recovery context.

Checkpoint state SHALL NOT independently establish:

- current authority;
- current authorization;
- current execution admission;
- current policy validity;
- current security validity.

---

## 17. Execution Lineage and Provenance

Recovery SHALL preserve execution lineage.

Where applicable, provenance SHALL distinguish:

- original execution identity;
- recovery event;
- recovery decision;
- recovered opportunity;
- current execution context;
- fresh capability request;
- fresh authorization result;
- fresh execution admission;
- execution result;
- verification result.

Lineage provides correlation and SHALL NOT grant authority.

---

## 18. Prohibited Architecture

The following are prohibited:

- RESTORE_PREVIOUS_AUTHORIZATION
- RESTORE_PREVIOUS_EXECUTION_ADMISSION
- TRUST_CHECKPOINT_AS_CURRENT_AUTHORITY
- BYPASS_AEGIS
- BYPASS_CAPABILITY_GATEWAY
- DIRECT_SECURE_EXECUTOR_INVOCATION
- RESTORE_EXPIRED_AUTHORITY
- RESTORE_REVOKED_AUTHORITY
- FAIL_OPEN_ON_SECURITY_UNCERTAINTY
- SILENTLY_EXECUTE_UNSUPPORTED_RECOVERY_STATE

---

## 19. Required Validation

Before implementation acceptance, validation SHALL prove:

- valid recovery produces fresh authorization;
- expired authority is denied;
- revoked authority is denied;
- stale checkpoint authorization is not reused;
- current policy is evaluated;
- current target is validated;
- fresh execution admission is generated;
- recovery reaches the governed PIAE path;
- recovery cannot bypass Aegis;
- recovery cannot bypass Capability Gateway;
- recovery cannot directly invoke privileged execution;
- ambiguous recovery state fails closed;
- provenance and execution lineage remain traceable.

---

## 20. Security Test Scenarios

R097-T01  Valid recovery
R097-T02  Expired authority
R097-T03  Revoked authority
R097-T04  Expired authorization
R097-T05  Revoked authorization
R097-T06  Stale checkpoint authorization
R097-T07  Policy-version change
R097-T08  Target change
R097-T09  Missing authority
R097-T10  Ambiguous security state
R097-T11  Fresh admission after recovery
R097-T12  Recovery-to-PIAE routing
R097-T13  Recovery cannot bypass gateway
R097-T14  Recovery cannot directly execute
R097-T15  Provenance continuity

These tests SHALL be implemented only after architecture approval.

---

## 21. Architectural Compatibility

R097 SHALL preserve:

- Aegis as authorization authority;
- Capability Gateway as execution-admission boundary;
- PIAE as governed action path;
- Secure Executor separation;
- LHICF and host security boundaries;
- durable execution lineage;
- least-privilege principles;
- existing Phase-A security foundations;
- Phase-B security strengthening architecture.

R097 SHALL NOT introduce an independent recovery authorization authority.

---

## 22. Implementation Constraints

This specification does NOT authorize implementation.

Before implementation:

1. Architecture review SHALL complete.
2. Security review SHALL complete.
3. Threat-model review SHALL complete.
4. Interface impact SHALL be reviewed.
5. Existing Phase-B contracts SHALL be checked for compatibility.
6. Required documentation updates SHALL be identified.
7. Implementation authorization SHALL remain a separate governance decision.

---

## 23. Acceptance Invariant

RECOVERY ≠ AUTHORITY RESTORATION

Required relationship:

RECOVERY
→ CURRENT STATE REVALIDATION
→ FRESH AUTHORIZATION
→ FRESH EXECUTION ADMISSION
→ GOVERNED EXECUTION

A recovered execution SHALL never become executable solely because it was previously authorized.

---

## 24. Current Status

R097 Evidence Investigation:             COMPLETE
R097 Architecture Design Contract:      COMPLETE
R097 Formal Architecture Specification:  DRAFT
Security Review:                         PENDING
Threat Review:                           PENDING
Architecture Approval:                   PENDING
Implementation Authorization:            NOT GRANTED BY THIS DOCUMENT
Implementation:                           BLOCKED
Production Operation:                    BLOCKED
Production Certification:                NOT CLAIMED

---

## 25. Non-Claims

This specification does NOT claim:

- R097 implementation;
- R097 implementation validation;
- production readiness;
- production certification;
- runtime recovery integration;
- successful recovery execution;
- privileged execution capability.

---

## 26. Governing Principle

> Recovery may restore work state and execution lineage, but it shall never restore execution authority.

Current authority must be re-established through the existing governed authorization and execution-admission architecture.

**END OF SPECIFICATION**

# LYRION True Agentic OS

# R097 — 3D-27-R5 Human Mechanism Selection & Approval Decision

**Document ID:** R097-DECISION-3D-27-R5
**Version:** 1.0.0
**Status:** HUMAN DECISION REQUIRED
**Decision Type:** Credential Mechanism Selection
**Implementation Authorization:** NOT AUTHORIZED
**Production Authorization:** NOT AUTHORIZED

---

## 1. Purpose

This document establishes the controlled human decision boundary for selecting
the credential-delivery mechanism for R097.

This document does NOT automatically select a mechanism.

The mechanism must be explicitly selected and approved by the authorized human
decision-maker before implementation authorization can be considered.

---

## 2. Reviewed Evidence

### R3 — Systemd Credential Mechanism Security Architecture Evaluation

Path:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_3D_27_R3_SYSTEMD_CREDENTIAL_MECHANISM_SECURITY_ARCHITECTURE_EVALUATION_v1.md`

SHA-256:

`af22948e0149c8cb4d2a75a0fef595779955af374d1c1d3ea303522727491158`

R3 evaluated systemd/systemd-creds as a candidate runtime credential mechanism
and identified architectural limitations requiring additional design.

### R4 — Credential Authority + Systemd Runtime Boundary Architecture

Path:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_3D_27_R4_CREDENTIAL_AUTHORITY_SYSTEMD_RUNTIME_BOUNDARY_ARCHITECTURE_v1.md`

SHA-256:

`3482ae7f22a45bcf5e7988fb7a04151a79c36a69ac8f08865089b4fe6268bebd`

R4 separates:

`Credential Authority → Credential Delivery → Database Authorization`

Systemd/systemd-creds remains a candidate runtime delivery component rather than
an automatically selected credential authority.

### R4 Architecture Security Review

Path:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_3D_27_R4_ARCHITECTURE_SECURITY_REVIEW_v1.md`

SHA-256:

`f3837470f8d7744196f6b12260c88deb36f131069f597d2985466491829ed493`

The review passed with 111 checks passed and 0 failures.

### R5-R1 — Corrected Formal Mechanism Decision Review

Path:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_3D_27_R5_FORMAL_MECHANISM_SELECTION_DECISION_REVIEW_R1_v1.md`

SHA-256:

`56628f58d8a01f928d4dbb76c6f89f5197e222041e3b950e77000768e1d7de8d`

R5-R1 classification:

`R097_3D_27_R5_R1_FORMAL_MECHANISM_DECISION_REVIEW_PASS`

Decision state:

`READY_FOR_EXPLICIT_HUMAN_MECHANISM_DECISION`

---

## 3. Candidate Mechanism

### Candidate A — Linux-native service credential mechanism

Candidate implementation family:

`systemd / systemd-creds`

Current state:

`CANDIDATE — NOT SELECTED`

Important:

Availability of systemd/systemd-creds does not by itself establish:

- credential authority ownership
- service identity governance
- credential issuance
- credential rotation
- credential revocation
- PostgreSQL privilege scope
- audit/provenance ownership
- emergency revocation
- environment separation
- recovery semantics
- LYRION authorization integration

Those controls remain architectural requirements.

---

## 4. Other Mechanism Classes

Previously evaluated mechanism classes include:

### Candidate B — Dedicated secret-management system

Potential characteristics:

- centralized credential authority
- lifecycle management
- rotation/revocation
- auditability
- service identity integration

Current state:

`NOT SELECTED`

### Candidate C — Encrypted local secret store

Potential characteristics:

- local encrypted storage
- host-bound protection
- controlled runtime retrieval

Current state:

`NOT SELECTED`

### Candidate D — Container/orchestration credential mechanism

Potential characteristics:

- workload identity
- runtime credential injection
- orchestration-managed lifecycle

Current state:

`NOT SELECTED`

No candidate is selected automatically by this document.

---

## 5. Mandatory Decision Criteria

The selected mechanism MUST be evaluated against the following:

1. Credential authority ownership
2. Service identity
3. Least privilege
4. Credential scope
5. Credential lifetime
6. Rotation
7. Revocation
8. Emergency revocation
9. Environment separation
10. Runtime exposure minimization
11. Agent isolation
12. Aegis integration
13. Capability Gateway integration
14. Execution Admission integration
15. Secure Executor integration
16. Agent Sandbox integration
17. LHICF boundary preservation
18. PostgreSQL authorization boundary
19. Auditability
20. Provenance
21. Failure handling
22. Recovery handling
23. Supply-chain security
24. Operational maintainability
25. Evidence generation and verification

---

## 6. Non-Negotiable Security Constraints

Regardless of selected mechanism:

- Credentials SHALL NOT enter model context.
- Credentials SHALL NOT enter agent memory.
- Credentials SHALL NOT be passed through ordinary tool arguments.
- Agents SHALL NOT directly bypass Aegis.
- Agents SHALL NOT bypass the Capability Gateway.
- Agents SHALL NOT bypass Execution Admission.
- Agents SHALL NOT bypass Secure Executor.
- Agents SHALL NOT bypass Agent Sandbox.
- Agents SHALL NOT bypass LHICF.
- PostgreSQL SHALL remain an independent authorization boundary.
- Credentials SHALL follow least privilege.
- Credential exposure SHALL be minimized.
- Revoked authority SHALL NOT silently become valid again.
- Recovery SHALL require fresh authorization where required.
- Credential values SHALL NOT be written into ordinary logs or telemetry.
- Production credentials SHALL NOT be reused in development environments.
- Credential lifecycle events SHALL be auditable without exposing credential values.

---

## 7. Decision Record

### Human Decision

**Selected mechanism:**

`[ HUMAN INPUT REQUIRED ]`

### Decision

`[ APPROVE / REJECT / DEFER ]`

### Rationale

`[ HUMAN INPUT REQUIRED ]`

### Authorized Decision-Maker

`[ HUMAN INPUT REQUIRED ]`

### Decision Date

`[ HUMAN INPUT REQUIRED ]`

### Additional Security Conditions

`[ HUMAN INPUT REQUIRED ]`

---

## 8. Approval Boundary

Selecting a mechanism does NOT automatically authorize implementation.

The required sequence remains:

`Human Mechanism Decision`
→
`Formal Mechanism Approval`
→
`Implementation Authorization`
→
`Implementation`
→
`Validation`
→
`Evidence`
→
`R097 Acceptance`

---

## 9. Implementation Prohibition

Until a separate implementation authorization is recorded:

- PostgreSQL role modification: **NOT AUTHORIZED**
- PostgreSQL password modification: **NOT AUTHORIZED**
- pg_hba modification: **NOT AUTHORIZED**
- systemd unit modification: **NOT AUTHORIZED**
- systemd credential deployment: **NOT AUTHORIZED**
- secret generation: **NOT AUTHORIZED**
- secret storage: **NOT AUTHORIZED**
- runtime credential injection: **NOT AUTHORIZED**
- production deployment: **NOT AUTHORIZED**

---

## 10. Safety Boundary

This decision package itself performs no:

- PostgreSQL connection
- PostgreSQL write
- role modification
- password modification
- pg_hba modification
- systemd modification
- credential read
- secret generation
- secret storage
- provider deployment
- runtime credential injection

---

## 11. Current Decision State

**HUMAN MECHANISM DECISION REQUIRED**

The architecture is ready for an explicit human mechanism decision.

No mechanism has been selected by this artifact.

No implementation is authorized.

---

## 12. Final Classification

`R097_3D_27_R5_HUMAN_MECHANISM_DECISION_PENDING`

# LYRION True Agentic OS

# R097 — 3D-27-R5 Mechanism Decision Comparison Matrix

**Document ID:** R097-COMPARISON-3D-27-R5
**Version:** 1.0.0
**Mode:** READ-ONLY / NO SELECTION
**Status:** HUMAN DECISION REQUIRED

## 1. Purpose

This artifact organizes the previously defined R097 mechanism classes against the mandatory decision criteria. It does not rank, score, recommend, or select a mechanism.

A human decision remains required.

## 2. Evidence Inputs

- R3 SHA-256: `af22948e0149c8cb4d2a75a0fef595779955af374d1c1d3ea303522727491158`
- R4 SHA-256: `3482ae7f22a45bcf5e7988fb7a04151a79c36a69ac8f08865089b4fe6268bebd`
- R5-R1 SHA-256: `56628f58d8a01f928d4dbb76c6f89f5197e222041e3b950e77000768e1d7de8d`
- Human Decision Package SHA-256: `dc93815366dd94ab5468e67a557619e8ad01341009dfaa2c42ed57f5fe1475fd`

## 3. Mechanism Classes

### A. systemd / systemd-creds

**Role:** Candidate runtime credential-delivery mechanism

**Architecture consideration:** Requires additional architecture for credential authority, lifecycle, authorization integration, revocation, audit/provenance, and recovery.

**Current selection state:** NOT SELECTED

### B. Dedicated secret-management system

**Role:** Potential centralized credential authority

**Architecture consideration:** Requires concrete provider evaluation, deployment architecture, identity integration, lifecycle design, and operational validation.

**Current selection state:** NOT SELECTED

### C. Encrypted local secret store

**Role:** Potential host-local protected credential storage

**Architecture consideration:** Requires concrete store selection, key ownership, lifecycle, runtime access control, recovery, and audit design.

**Current selection state:** NOT SELECTED

### D. Container/orchestration credential mechanism

**Role:** Potential workload/runtime credential boundary

**Architecture consideration:** Requires applicable orchestration architecture, workload identity, runtime isolation, lifecycle, and host-integration design.

**Current selection state:** NOT SELECTED

### E. DEFER / additional evaluation

**Role:** No mechanism selected

**Architecture consideration:** Permits additional controlled architecture/security research before selection.

**Current selection state:** NOT SELECTED

## 4. Mandatory Criteria

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

## 5. Neutral Comparison

| Criterion | A: systemd/systemd-creds | B: Dedicated secret-management | C: Encrypted local store | D: Container/orchestration | E: Defer |
|---|---|---|---|---|---|
| Credential authority ownership | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Service identity | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Least privilege | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Credential scope | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Credential lifetime | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Rotation | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Revocation | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Emergency revocation | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Environment separation | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Runtime exposure minimization | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Agent isolation | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Aegis integration | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Capability Gateway integration | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Execution Admission integration | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Secure Executor integration | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Agent Sandbox integration | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| LHICF boundary preservation | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| PostgreSQL authorization boundary | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Auditability | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Provenance | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Failure handling | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Recovery handling | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Supply-chain security | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Operational maintainability | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |
| Evidence generation and verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires design/verification | Requires further evaluation |

The neutral matrix intentionally does not assign scores or winners. The available R097 evidence is not sufficient to authorize a comparative security ranking of the mechanism classes.

## 6. Existing Systemd Evidence

R3 evaluated systemd/systemd-creds as a candidate runtime mechanism. R4 subsequently defined a controlled Credential Authority → Credential Delivery → Database Authorization separation.

Therefore:

- systemd/systemd-creds remains a candidate.
- It is not automatically the credential authority.
- It is not automatically selected.
- Implementation remains unauthorized.

## 7. Human Decision Record

**Selected mechanism:** `[ HUMAN INPUT REQUIRED ]`

**Decision:** `[ APPROVE / REJECT / DEFER ]`

**Rationale:** `[ HUMAN INPUT REQUIRED ]`

**Decision-maker:** `[ HUMAN INPUT REQUIRED ]`

**Decision date:** `[ HUMAN INPUT REQUIRED ]`

## 8. Authorization Boundary

This comparison does not authorize:

- PostgreSQL changes
- role/password changes
- pg_hba changes
- systemd changes
- credential deployment
- secret generation
- secret storage
- runtime credential injection
- production deployment

## 9. Current State

**Mechanism selection:** NONE

**Human decision:** PENDING

**Implementation authorization:** NOT AUTHORIZED

**Production authorization:** NOT AUTHORIZED

## 10. Final Classification

`R097_3D_27_R5_MECHANISM_COMPARISON_COMPLETE_HUMAN_DECISION_PENDING`

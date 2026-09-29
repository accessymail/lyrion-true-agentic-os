# LYRION True Agentic OS
# R097 — 3D-27-R4
# Credential Authority + systemd Runtime Boundary Architecture

**Document ID:** R097-DOC-ARCH-CREDENTIAL-AUTHORITY-SYSTEMD  
**Version:** 1.0.0  
**Phase:** Phase B  
**Requirement:** R097  
**Evaluation Stage:** 3D-27-R4  
**Status:** DRAFT — ARCHITECTURE REVIEW REQUIRED  
**Candidate Mechanism:** systemd/systemd-creds runtime boundary  
**Provider Selection:** NOT APPROVED  
**Implementation Authorization:** NOT AUTHORIZED

---

## 1. Purpose

This document defines the proposed architecture boundary between LYRION
credential authority and the Linux/systemd runtime credential-delivery layer.

The purpose is to determine whether systemd credential delivery can safely
operate as one component of the larger LYRION credential architecture.

This document does not authorize implementation.

It does not create credentials.

It does not modify PostgreSQL.

It does not modify systemd.

It does not select a concrete secret provider.

---

## 2. Source Baseline

Approved R097 credential architecture:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_DATABASE_CREDENTIAL_PROVISIONING_ARCHITECTURE_v1.md`

Architecture SHA-256:

`6b8e85c472c18977f0e47950abf8393443fa973dd345a3706733f283ced41ac7`

R097 mechanism decision analysis:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_DATABASE_CREDENTIAL_PROVISIONING_MECHANISM_DECISION_v1.md`

ADR SHA-256:

`49b2a04c193e3543302a90c8abd1d9b0d4ccb337b27d8f47b1a498429fbed4fb`

R097 3D-27-R3 systemd evaluation:

`/home/aniket/lyrion-migration-verified/docs/phase-b/execution-admission/r097/LYRION_R097_3D_27_R3_SYSTEMD_CREDENTIAL_MECHANISM_SECURITY_ARCHITECTURE_EVALUATION_v1.md`

R3 SHA-256:

`af22948e0149c8cb4d2a75a0fef595779955af374d1c1d3ea303522727491158`

---

## 3. Architectural Position

The proposed architecture separates:

**Credential Authority**

from

**Credential Delivery**

and from

**Database Authorization**.

systemd/systemd-creds is therefore treated as a potential controlled runtime
delivery boundary rather than automatically being treated as the authoritative
credential-management system.

---

## 4. Proposed Security Chain

```
Human / Authorized Principal
            |
            v
LYRION Governance
            |
            v
Authorization Decision
            |
            v
LYRION Service Identity
            |
            v
Credential Authority
            |
            v
Credential Provisioning Boundary
            |
            v
systemd Runtime Credential Boundary
            |
            v
Authorized LYRION Service
            |
            v
PostgreSQL Authentication
            |
            v
Scoped Database Operations
            |
            v
Verification
            |
            v
Audit / Provenance
```

No layer may silently bypass the preceding authorization boundary.

---

## 5. Separation of Responsibilities

### 5.1 LYRION Governance

Responsible for:

- authorization;
- policy;
- task authority;
- execution admission;
- security constraints;
- human approval where required.

It SHALL NOT directly expose raw database credentials to models or agents.

---

### 5.2 LYRION Service Identity

Responsible for:

- attributable service identity;
- service authorization;
- environment identity;
- identity lifecycle;
- revocation state.

The service identity SHALL be distinct from:

- human identity;
- model identity;
- agent identity;
- database credential material.

---

### 5.3 Credential Authority

Responsible for:

- authoritative credential ownership;
- credential issuance;
- credential scope;
- credential lifecycle;
- rotation;
- revocation;
- expiration;
- emergency revocation;
- environment separation;
- credential audit/provenance.

A concrete credential authority is intentionally NOT SELECTED by this document.

---

### 5.4 systemd Runtime Boundary

Potential responsibility:

- controlled delivery of credential material to an authorized service;
- reduction of credential exposure through ordinary process configuration;
- service-runtime boundary enforcement;
- host-level lifecycle integration.

systemd SHALL NOT be assumed to provide the complete LYRION credential
authority unless separately demonstrated and approved.

---

### 5.5 PostgreSQL

Responsible for:

- authentication;
- database authorization;
- role privileges;
- database-side access controls.

PostgreSQL SHALL remain downstream of the LYRION authorization chain.

---

## 6. Credential Flow

The proposed flow is:

```
1. Authorized operation is requested
        |
        v
2. LYRION evaluates authorization
        |
        v
3. Authorized service identity is established
        |
        v
4. Credential authority evaluates credential request
        |
        v
5. Credential material is provisioned into the controlled runtime boundary
        |
        v
6. Authorized service receives only required credential material
        |
        v
7. Service authenticates to PostgreSQL
        |
        v
8. Database operation executes within PostgreSQL privilege scope
        |
        v
9. Operation is verified
        |
        v
10. Audit/provenance evidence is generated
```

The model/agent does not receive the raw database credential.

---

## 7. Credential Exposure Boundary

The architecture SHALL prevent raw credentials from entering:

- prompts;
- model context;
- agent memory;
- normal tool arguments;
- task descriptions;
- user-facing responses;
- ordinary logs;
- telemetry;
- audit payloads.

Credential material SHALL remain inside the minimum required runtime boundary.

---

## 8. Runtime Boundary

The proposed systemd boundary is:

```
Credential Authority
        |
        | controlled provisioning
        v
systemd service credential boundary
        |
        | controlled runtime access
        v
LYRION database service
        |
        v
PostgreSQL
```

The application SHALL NOT expose raw credential material to unrelated
processes, agents, or user interfaces.

---

## 9. Service Identity Boundary

The runtime service SHALL have an attributable identity.

The final implementation design must define:

- service identity;
- identity owner;
- identity issuance;
- identity validation;
- identity expiration;
- identity revocation;
- identity-to-credential binding;
- environment binding;
- audit correlation.

No anonymous credential retrieval SHALL be permitted.

---

## 10. Credential Scope

Credential authority SHALL issue or provision only the minimum credential
authority required for the service.

The database authorization layer must independently enforce:

- permitted database;
- permitted schema;
- permitted tables;
- permitted operations;
- permitted service identity;
- environment boundary.

Credential possession SHALL NOT imply unrestricted database authority.

---

## 11. Lifecycle

The architecture requires:

```
ISSUE
  |
  v
SCOPE
  |
  v
USE
  |
  +----> AUDIT
  |
  v
ROTATE
  |
  v
REVOKE / EXPIRE
  |
  v
VERIFY
```

The final implementation must establish authoritative lifecycle ownership.

---

## 12. Rotation

Rotation SHALL be designed so that:

1. new credential material can be provisioned;
2. service transition can be controlled;
3. old material can be revoked;
4. failed rotation does not silently create stale authorization;
5. audit evidence records the lifecycle event;
6. application availability requirements are respected.

No rotation implementation is authorized by this document.

---

## 13. Revocation

Revocation must support:

- normal revocation;
- emergency revocation;
- identity revocation;
- credential revocation;
- environment isolation;
- post-revocation verification.

After revocation, the system SHALL NOT silently restore the revoked authority.

---

## 14. Failure Model

The design SHALL fail closed for:

- missing credential;
- unauthorized credential request;
- invalid service identity;
- revoked identity;
- expired credential;
- failed provisioning;
- failed authorization;
- invalid environment;
- invalid credential scope.

The application must not fall back to:

- hard-coded credentials;
- default privileged credentials;
- unrestricted environment credentials;
- interactive credential prompts that bypass governance;
- alternate unauthorized providers.

---

## 15. Recovery Model

Recovery SHALL require fresh authorization where the previous authority is
expired or revoked.

Recovery SHALL NOT:

- reuse stale credentials;
- bypass credential authority;
- bypass service identity;
- bypass LYRION authorization;
- automatically restore revoked access.

---

## 16. Environment Separation

The architecture requires independent boundaries for:

- development;
- test;
- validation;
- staging where applicable;
- production.

Production credentials SHALL NEVER be copied into lower environments.

Credential authority SHALL be environment-aware.

Service identity SHALL be environment-aware.

Audit records SHALL identify the environment.

---

## 17. Audit and Provenance

The architecture SHALL produce attributable evidence for:

- authorization decision;
- service identity;
- credential issuance;
- provisioning;
- credential use event;
- rotation;
- revocation;
- failure;
- recovery;
- database operation;
- verification.

Raw credentials SHALL NEVER appear in audit records.

Audit evidence must support causal reconstruction without exposing secret
material.

---

## 18. Observability

Observability may record:

- request identifier;
- task identifier;
- service identity;
- environment;
- credential lifecycle event;
- authorization decision;
- database operation class;
- success/failure;
- verification result.

Observability SHALL NOT record:

- passwords;
- raw tokens;
- private keys;
- secret contents;
- unrestricted credential material.

---

## 19. Emergency Controls

The final architecture must support emergency shutdown at appropriate
authorization boundaries.

Potential controls include:

- service disablement;
- identity revocation;
- credential revocation;
- execution-admission denial;
- database access denial.

Emergency controls must remain auditable.

---

## 20. systemd-Specific Boundary

systemd/systemd-creds is currently considered only as a potential runtime
credential-delivery component.

The final design must establish:

- how credentials enter the systemd boundary;
- who is authorized to provision them;
- which service receives them;
- how the service identity is verified;
- how runtime exposure is minimized;
- how restart behavior works;
- how rotation interacts with service lifecycle;
- how revocation interacts with running services;
- how evidence is correlated.

No systemd unit configuration is created by this document.

---

## 21. PostgreSQL Boundary

PostgreSQL remains an independent authorization boundary.

The final implementation must define:

- database role;
- role privilege scope;
- database;
- schema permissions;
- required SQL operations;
- connection policy;
- authentication method;
- environment;
- rotation procedure.

No PostgreSQL role or password modification is authorized by this document.

---

## 22. Agentic Execution Boundary

The credential architecture SHALL remain downstream of:

```
Human Intent
   |
Lyri Interpretation
   |
Task
   |
Agent Delegation
   |
Delegated Authority
   |
Aegis
   |
Capability Gateway
   |
Execution Admission
   |
Secure Executor
   |
Agent Sandbox
   |
LHICF
   |
Credential / Service Boundary
   |
PostgreSQL
```

Agents SHALL NOT directly bypass this chain to obtain database credentials.

---

## 23. Threat Controls

The design must address:

- prompt injection;
- indirect prompt injection;
- goal hijacking;
- tool poisoning;
- authority confusion;
- credential theft;
- credential replay;
- credential exfiltration;
- privilege escalation;
- service impersonation;
- stale authorization;
- runtime compromise;
- host compromise;
- secret leakage;
- supply-chain compromise.

---

## 24. Security Invariants

The following invariants are mandatory:

1. No raw credential in model context.
2. No raw credential in agent memory.
3. No raw credential in ordinary tool arguments.
4. No credential bypass around Aegis.
5. No credential bypass around Capability Gateway.
6. No credential bypass around Secure Executor.
7. No credential bypass around Agent Sandbox.
8. No credential bypass around LHICF.
9. No unrestricted agent credential.
10. No stale authorization after revocation.
11. No production credential reuse in development.
12. No credential values in audit evidence.

---

## 25. Implementation Preconditions

Before implementation authorization, the following must be resolved:

- credential authority;
- service identity;
- identity-to-credential binding;
- provisioning workflow;
- systemd runtime contract;
- PostgreSQL privilege model;
- rotation;
- revocation;
- recovery;
- environment separation;
- audit/provenance;
- threat controls;
- supply-chain validation;
- test plan;
- evidence plan.

---

## 26. Decision State

**systemd/systemd-creds:** CANDIDATE COMPONENT

**Complete credential architecture:** NOT APPROVED

**Concrete credential authority:** NOT SELECTED

**Provider selection:** NOT AUTHORIZED

**Implementation:** NOT AUTHORIZED

**PostgreSQL changes:** NOT AUTHORIZED

---

## 27. Architecture Review Gate

This document requires formal architecture review before proceeding.

Required review questions:

1. Does the separation between credential authority and runtime delivery remain
   clear?
2. Is systemd limited to an appropriate runtime boundary?
3. Is LYRION service identity sufficiently defined?
4. Is credential authority ownership explicit?
5. Are rotation and revocation independently enforceable?
6. Is PostgreSQL authorization independently scoped?
7. Is agent access sufficiently isolated?
8. Are recovery and failure paths fail-closed?
9. Are audit/provenance boundaries sufficient?
10. Can the design support future LYRION Agentic OS execution architecture?

---

## 28. Approval Boundary

**Architecture status:** DRAFT

**Architecture review:** REQUIRED

**Provider selection:** NOT APPROVED

**Implementation authorization:** NOT AUTHORIZED

**Human approval:** REQUIRED

Creation of this document does not constitute approval.

---

## 29. Safety Record

PostgreSQL writes:

**NONE**

PostgreSQL role changes:

**NONE**

PostgreSQL password changes:

**NONE**

pg_hba.conf changes:

**NONE**

Credential values read:

**NONE**

Secrets generated:

**NONE**

Secrets stored:

**NONE**

Secrets printed:

**NONE**

systemd configuration changed:

**NO**

systemd credential store modified:

**NO**

External provider contacted:

**NONE**

Production configuration changed:

**NO**

---

## 30. Controlled Sequence

```
3D-27-R1  Read-only mechanism evidence
      |
      v
3D-27-R2  Capability verification
      |
      v
3D-27-R3  systemd candidate evaluation
      |
      v
3D-27-R4  Credential Authority +
          systemd Runtime Boundary Design     CURRENT
      |
      v
Architecture Review
      |
      +---- REJECT / REVISE
      |
      +---- ACCEPT
              |
              v
3D-27-R5  Formal Mechanism Selection Decision
              |
              v
Implementation Authorization
              |
              v
3D-28  Controlled Implementation
              |
              v
Validation
              |
              v
Security Testing
              |
              v
Evidence
              |
              v
R097 Acceptance
```

---

## 31. Final Classification

**R097_3D_27_R4_CREDENTIAL_AUTHORITY_SYSTEMD_RUNTIME_BOUNDARY_DRAFT**

This document establishes the proposed architectural separation between
credential authority, LYRION authorization, service identity, systemd runtime
delivery, and PostgreSQL authorization.

It does not select a provider.

It does not authorize implementation.

It does not modify PostgreSQL or systemd.

**Architecture Review Required Before 3D-27-R5.**


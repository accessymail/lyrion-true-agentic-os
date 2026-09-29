# LYRION True Agentic OS

# R097 — 3D-27-R5 Advanced Credential Mechanism Architecture & Security Comparison

**Document ID:** R097-ARCH-SEC-CREDENTIAL-MECHANISM-COMPARISON
**Version:** 1.0.0
**Status:** READ-ONLY ARCHITECTURE EVALUATION
**Date:** 2026-09-28T10:29:40+00:00

---

## 1. Purpose

This document performs a controlled architecture and security comparison of
candidate credential-management mechanism classes for LYRION True Agentic OS.

This document:

- does not select a mechanism;
- does not recommend a mechanism;
- does not rank mechanisms;
- does not authorize implementation;
- does not modify PostgreSQL;
- does not modify systemd;
- does not read credentials;
- does not generate secrets;
- does not deploy a provider;
- does not inject runtime credentials.

The human mechanism decision remains a separate controlled gate.

---

## 2. Governing Architectural Boundary

The evaluation preserves the following conceptual separation:

Credential Authority
→ Credential Delivery
→ Database Authorization
→ Authorized Database Operations

The credential-delivery mechanism SHALL NOT become an implicit replacement
for LYRION authorization, Aegis, Capability Gateway, Execution Admission,
Secure Executor, Agent Sandbox, LHICF, or PostgreSQL authorization.

---

## 3. Security Invariants

Every candidate mechanism must be evaluated against:

1. Least privilege.
2. Attributable service identity.
3. Scoped credential authority.
4. Credential lifecycle management.
5. Rotation.
6. Revocation.
7. Emergency revocation.
8. Expiration where applicable.
9. Environment separation.
10. Runtime exposure minimization.
11. Fail-closed behavior.
12. Recovery with fresh authorization where required.
13. Auditability.
14. Provenance.
15. Credential-use traceability.
16. Protection against credential leakage.
17. Protection against agent/tool/model access.
18. Protection against unauthorized host access.
19. Supply-chain integrity.
20. Operational recoverability.

---

# 4. Candidate Mechanism Classes

## A — Linux-native systemd / systemd-creds

### Architectural concept

Use Linux/systemd credential facilities as part of the controlled runtime
credential-delivery boundary.

### Relevant deployment model

Native Linux service deployment.

### Potential architectural integration points

- systemd service identity
- systemd-managed runtime boundary
- systemd credential delivery
- restricted service environment
- host-level service lifecycle

### Required verification areas

- credential authority ownership
- credential provisioning lifecycle
- credential rotation
- credential revocation
- emergency revocation
- service identity binding
- runtime exposure
- filesystem exposure
- process exposure
- audit/provenance
- environment separation
- recovery behavior
- PostgreSQL authorization independence

### Important architectural limitation

Availability of systemd/systemd-creds does not itself establish:

- LYRION credential authority;
- LYRION authorization;
- PostgreSQL privilege design;
- credential lifecycle governance;
- audit/provenance;
- emergency revocation;
- production acceptance.

---

# 5. Candidate Mechanism Class B

## Dedicated Secret-Management System

### Architectural concept

Use a purpose-built secret-management system as the credential authority or
credential-management service.

### Potential capabilities requiring verification

- centralized secret lifecycle
- controlled access policies
- credential rotation
- revocation
- audit trails
- service identity
- short-lived credentials
- environment separation
- policy-based access
- recovery procedures

### Required architectural questions

- What establishes service identity?
- How does LYRION authenticate to the secret authority?
- How is the bootstrap trust established?
- How are credentials rotated?
- How are credentials revoked?
- What happens when the secret authority is unavailable?
- Can credential material enter agent/model context?
- How is credential use audited?
- What is the local development model?
- What is the native Linux production model?
- What is the operational dependency footprint?
- How is emergency access controlled?

No concrete provider is selected by this document.

---

# 6. Candidate Mechanism Class C

## Encrypted Local Secret Store

### Architectural concept

Store credential material in an encrypted local mechanism and expose it only
through a controlled runtime/application boundary.

### Required verification areas

- encryption-at-rest model
- key ownership
- key protection
- unlock mechanism
- service identity
- access-control boundary
- rotation
- revocation
- backup/restore
- recovery
- emergency revocation
- filesystem permissions
- process exposure
- local privilege escalation
- auditability
- provenance
- multi-environment separation

### Critical architectural questions

- Where does the decryption authority reside?
- Who can unlock the store?
- Can an agent indirectly trigger unlocking?
- Can another local process obtain the secret?
- How is rotation performed?
- How is revocation enforced?
- What happens after host compromise?
- How is recovery handled without restoring stale authorization?

No specific local secret-store technology is selected by this document.

---

# 7. Candidate Mechanism Class D

## Container / Orchestration Credential Mechanism

### Architectural concept

Use the credential-delivery facilities of a container or orchestration
environment.

### Relevant deployment model

Containerized or orchestrated LYRION deployment.

### Required verification areas

- container identity
- workload identity
- secret scope
- secret injection
- filesystem/process exposure
- orchestration control-plane trust
- rotation
- revocation
- workload restart behavior
- node compromise
- control-plane compromise
- environment separation
- auditability
- provenance
- recovery
- supply-chain security

### Architectural consideration

This mechanism class may introduce an additional infrastructure/control-plane
dependency and therefore requires explicit analysis of the relationship between
LYRION authorization and orchestration authorization.

No specific container/orchestration platform is selected by this document.

---

# 8. Cross-Mechanism Security Evaluation

| Security Domain | A: systemd | B: Dedicated Secret Manager | C: Encrypted Local Store | D: Container/Orchestration |
|---|---|---|---|---|
| Service identity | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| Least privilege | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| Credential authority | DESIGN REQUIRED | DESIGN REQUIRED | DESIGN REQUIRED | DESIGN REQUIRED |
| Credential delivery | DESIGN REQUIRED | DESIGN REQUIRED | DESIGN REQUIRED | DESIGN REQUIRED |
| Rotation | VERIFY | VERIFY | VERIFY | VERIFY |
| Revocation | VERIFY | VERIFY | VERIFY | VERIFY |
| Emergency revocation | VERIFY | VERIFY | VERIFY | VERIFY |
| Runtime isolation | VERIFY | VERIFY | VERIFY | VERIFY |
| Environment separation | VERIFY | VERIFY | VERIFY | VERIFY |
| Auditability | VERIFY | VERIFY | VERIFY | VERIFY |
| Provenance | VERIFY | VERIFY | VERIFY | VERIFY |
| Fail closed | VERIFY | VERIFY | VERIFY | VERIFY |
| Recovery | VERIFY | VERIFY | VERIFY | VERIFY |
| Agent isolation | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| Model-context isolation | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| PostgreSQL authorization | INDEPENDENT | INDEPENDENT | INDEPENDENT | INDEPENDENT |
| Supply-chain controls | REQUIRED | REQUIRED | REQUIRED | REQUIRED |
| Production evidence | REQUIRED | REQUIRED | REQUIRED | REQUIRED |

The table is an evaluation framework, not a score or ranking.

---

# 9. LYRION Agentic Security Chain

Regardless of mechanism, credential delivery SHALL remain downstream of
LYRION's authorization architecture:

Human Intent
→ Lyri Interpretation
→ Task
→ Agent Delegation
→ Delegated Authority
→ Aegis
→ Capability Gateway
→ Execution Admission
→ Secure Executor
→ Agent Sandbox
→ Credential Delivery Boundary
→ LHICF
→ Host / Database
→ Verification
→ Audit / Provenance

A credential mechanism SHALL NOT provide an alternate path around this chain.

---

# 10. Threat Evaluation

Each candidate requires explicit controls for:

### Prompt Injection

Credential material must never be exposed to model context or prompt-derived
execution parameters.

### Tool Poisoning

Untrusted tools must not acquire credential authority merely because they are
available to an agent.

### Agent Impersonation

Credential access must be attributable to an authenticated service identity.

### Authority Confusion

Possession of a capability must not automatically imply possession of
database credentials.

### Privilege Escalation

Credential delivery must not become a privilege-escalation primitive.

### Credential Exfiltration

Credential material must be protected from:

- logs
- telemetry
- agent memory
- prompts
- tool arguments
- ordinary application output
- unauthorized local processes

### Replay / Stale Credentials

Rotation, expiration, revocation and recovery must prevent stale authorization
from being silently restored.

### Host Compromise

The security consequences of local privilege escalation and host compromise
must be explicitly modeled.

### Supply-Chain Compromise

Dependencies, providers, runtime components and deployment artifacts require
provenance and integrity controls.

---

# 11. Operational Evaluation

Before implementation authorization, the selected mechanism would require
evidence for:

- provisioning
- startup
- authentication
- authorization
- credential rotation
- credential revocation
- emergency revocation
- service restart
- host restart
- application recovery
- database outage
- credential authority outage
- stale credential rejection
- unauthorized access rejection
- audit generation
- provenance preservation
- environment isolation
- secret exposure prevention

---

# 12. Development / Production Separation

The mechanism selected for native development must not automatically become
the production mechanism.

The architecture must explicitly define:

- development environment;
- validation environment;
- production environment;
- credential authority per environment;
- credential scope per environment;
- lifecycle per environment;
- audit/provenance per environment.

Environment-specific credentials SHALL NOT be silently reused across
environments.

---

# 13. Current Evidence References

**R4 Architecture SHA-256:**

`3482ae7f22a45bcf5e7988fb7a04151a79c36a69ac8f08865089b4fe6268bebd`

**R4 Architecture Review SHA-256:**

`f3837470f8d7744196f6b12260c88deb36f131069f597d2985466491829ed493`

**R5-R1 Decision Review SHA-256:**

`56628f58d8a01f928d4dbb76c6f89f5197e222041e3b950e77000768e1d7de8d`

**Existing Mechanism Matrix SHA-256:**

`de52f8f5aca7c36f27b3e71a384add00d30a7888c19dc221e7b9e823e1d37cfb`

---

# 14. Current Decision State

**Mechanism Selected:** NONE

**Human Mechanism Decision:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Authorization:** NOT AUTHORIZED

This document does not change those states.

---

# 15. Required Human Decision Boundary

The human decision must occur only after the architecture/security evidence
has been reviewed.

Possible human outcomes remain:

- Select mechanism A.
- Select mechanism B.
- Select mechanism C.
- Select mechanism D.
- Defer the mechanism decision for additional evaluation.

No mechanism is selected by this document.

---

# 16. Safety Result

This evaluation performed:

- PostgreSQL writes: NONE
- PostgreSQL role changes: NONE
- PostgreSQL password changes: NONE
- pg_hba changes: NONE
- Credential reads: NONE
- Secrets generated: NONE
- Secrets stored: NONE
- systemd configuration changes: NONE
- Provider deployment: NONE
- Runtime credential injection: NONE
- External secret-provider communication: NONE

---

# 17. Classification

`R097_3D_27_R5_ADVANCED_CREDENTIAL_MECHANISM_COMPARISON_COMPLETE`

**Decision state:** HUMAN DECISION REQUIRED

**Implementation state:** BLOCKED

**Production state:** BLOCKED

**Evaluation mode:** READ-ONLY

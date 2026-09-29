# LYRION True Agentic OS

# R097 — 3D-27-R5 Mechanism-Neutral Evidence Architecture & Evidence Collection Contract

**Document ID:** R097-MECHANISM-NEUTRAL-EVIDENCE-ARCHITECTURE-COLLECTION-CONTRACT
**Version:** 1.0.0
**Date:** 2026-09-28T10:52:17+00:00
**Status:** CONTROLLED / MECHANISM-NEUTRAL / NON-AUTHORIZING

---

## 1. Purpose

This contract defines the evidence architecture and evidence-collection
requirements that must apply before any future credential mechanism can
enter formal approval.

It does not select, rank, score, recommend, approve, implement, or deploy
a credential mechanism.

---

## 2. Current Decision State

**Mechanism selected:** NONE

**Human decision:** DEFER

**Formal approval:** NOT READY

**Implementation authorization:** NOT AUTHORIZED

**Production authorization:** NOT AUTHORIZED

This contract does not alter the current decision state.

---

## 3. Evidence Architecture

Future evidence shall be organized into the following evidence classes:

### E01 — Architecture Evidence

Must establish:

- trust boundaries;
- authority boundaries;
- credential-delivery boundaries;
- Universal Computer / Host / Application Harness boundaries;
- platform adapter boundaries;
- LHICF preservation;
- PostgreSQL authorization separation.

### E02 — Identity and Authority Evidence

Must establish:

- service identity;
- identity attribution;
- authority ownership;
- authorization scope;
- delegation boundaries;
- revocation authority.

### E03 — Credential Lifecycle Evidence

Must establish:

- issuance;
- activation;
- expiration;
- rotation;
- revocation;
- emergency revocation;
- recovery.

### E04 — Runtime Isolation Evidence

Must establish that credential material is not exposed through:

- model context;
- agent memory;
- unrestricted tool arguments;
- unrestricted filesystem access;
- logs;
- telemetry;
- ordinary audit payloads.

### E05 — Integration Evidence

Must establish controlled interaction between:

Credential Authority
→ Credential Delivery Boundary
→ Runtime Application Boundary
→ PostgreSQL Authentication
→ PostgreSQL Authorization.

### E06 — Security / Adversarial Evidence

Must establish resistance against relevant threats including:

- credential disclosure;
- authority confusion;
- privilege escalation;
- replay;
- credential theft;
- stale authorization;
- runtime boundary bypass;
- host/application boundary bypass.

### E07 — Failure / Recovery Evidence

Must establish fail-closed behavior for:

- invalid credentials;
- expired credentials;
- revoked credentials;
- authority failure;
- runtime failure;
- network failure;
- recovery;
- stale authorization.

### E08 — Audit / Provenance Evidence

Must establish attributable evidence for:

- authorization;
- credential use;
- lifecycle events;
- provisioning;
- rotation;
- revocation;
- recovery;
- validation.

### E09 — Supply-Chain Evidence

Must establish:

- component provenance;
- version integrity;
- dependency integrity;
- vulnerability assessment;
- deployment provenance;
- update/revocation controls.

### E10 — Operational Evidence

Must establish:

- operational procedures;
- emergency response;
- safe restart;
- rollback;
- recovery;
- incident handling;
- evidence retention.

---

## 4. Evidence Record Contract

Every future evidence record must identify, where applicable:

- evidence ID;
- requirement ID;
- evidence class;
- execution environment;
- execution timestamp;
- executor/owner;
- authorization state;
- source artifact;
- command or test procedure;
- result;
- artifact hash;
- reviewer;
- review result;
- provenance metadata.

Evidence must be attributable and reproducible.

---

## 5. Evidence Integrity Requirements

Future evidence must be:

1. Current.
2. Attributable.
3. Reproducible.
4. Environment-specific.
5. Tamper-evident.
6. Traceable to a requirement.
7. Traceable to an authorized procedure.
8. Independently reviewable where required.

Evidence must not be accepted solely because a command completed
successfully.

---

## 6. Evidence Collection Boundary

Evidence collection must not become a credential-exposure mechanism.

Evidence collection must not:

- print passwords;
- print secret values;
- place secrets into logs;
- place secrets into model context;
- place secrets into agent memory;
- place secrets into unrestricted artifacts;
- expose secret material through telemetry.

Redaction must be applied where sensitive metadata is unavoidable.

---

## 7. Authorization Boundary

Evidence collection does not imply implementation authorization.

The required future authorization sequence remains:

Human Decision
→ Mechanism Approval
→ Implementation Authorization
→ Controlled Implementation
→ Validation
→ Evidence
→ R097 Acceptance
→ Production Authorization.

No evidence procedure may silently grant a later authorization.

---

## 8. Mechanism-Neutrality Requirement

This contract intentionally does not prescribe:

- systemd credentials;
- systemd-creds;
- Vault;
- encrypted local secret stores;
- container credential mechanisms;
- Kubernetes secrets;
- cloud secret managers;
- OS keyrings;
- any other concrete credential provider.

Technology selection remains a separate future human decision.

---

## 9. Universal Harness Requirement

Any future implementation must preserve:

Universal Computer / Host / Application Harness
→ Platform-Specific Host/Application Adapter
→ Controlled LHICF Boundary.

Credential delivery must not create an unrestricted host capability.

---

## 10. Security Chain Requirement

Future implementation and evidence must preserve:

Aegis
→ Capability Gateway
→ Execution Admission
→ Secure Executor
→ Agent Sandbox
→ Universal Host/Application Harness
→ Platform/Application Adapter
→ LHICF
→ Host OS / Application.

Credential handling must not bypass this controlled execution boundary.

---

## 11. PostgreSQL Separation Requirement

Credential delivery and PostgreSQL authorization remain separate concerns.

Future evidence must independently establish:

- database authentication;
- database role;
- database privileges;
- database authorization;
- application credential handling.

Successful credential delivery alone must never be interpreted as
authorization to perform arbitrary database operations.

---

## 12. Evidence Acceptance Gate

A future mechanism-specific evidence package must not proceed to formal
approval unless the required evidence is:

- complete for its declared scope;
- internally consistent;
- attributable;
- reproducible;
- integrity-verifiable;
- security-reviewed;
- mapped to requirements;
- free of unauthorized credential exposure.

---

## 13. Current Readiness

The evidence architecture is now defined at a mechanism-neutral level.

Concrete mechanism-specific evidence remains blocked because:

**Mechanism selected: NONE**

**Human decision: DEFER**

Therefore:

**EVIDENCE COLLECTION CONTRACT: DEFINED**

**MECHANISM-SPECIFIC EVIDENCE: BLOCKED BY SELECTION**

---

## 14. Safety Boundary

This contract establishes no implementation.

Current safety state:

- PostgreSQL writes: NONE
- PostgreSQL role changes: NONE
- PostgreSQL password changes: NONE
- pg_hba changes: NONE
- Credential reads: NONE
- Secrets generated: NONE
- Secrets stored: NONE
- systemd changes: NONE
- Provider deployment: NONE
- Runtime credential injection: NONE

---

## 15. Source Integrity

### Evidence Readiness Matrix

`e23f74337f60554b5a8b239efa82b9b2239caff57f45104a8043c52e0a3eb4b5`

### Evidence Readiness Matrix Review

`70e30671891f9999140c1d7c11401bc085709a8a16dd109c9db722fc69118273`

### Deferred Mechanism Decision Checkpoint

`8585cf18e73db90a978d92b423b169297f61b285e40bdbb095bb22831ff8bfc1`

---

## 16. Classification

`R097_3D_27_R5_MECHANISM_NEUTRAL_EVIDENCE_COLLECTION_CONTRACT_CREATED`

**Mechanism:** NONE SELECTED

**Human decision:** DEFER

**Evidence architecture:** DEFINED

**Mechanism-specific evidence:** BLOCKED BY SELECTION

**Implementation:** BLOCKED

**Production:** BLOCKED

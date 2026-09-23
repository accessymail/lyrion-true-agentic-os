# LYRION Unified Core Data Architecture

**Document ID:** TAOS-CORE-DATA-ARCH-001
**Version:** 1.0.0
**Date:** 2026-09-22
**Status:** DRAFT — DATA ARCHITECTURE BASELINE

---

## 1. Purpose

This document defines the foundational Data Architecture for the LYRION
Unified Core.

It establishes the authoritative data-state model required by the Core
Requirements PRD, Core Architecture, Recursive Memory Architecture (RMA),
and TR-004 Memory Data Integrity traceability requirement.

This document defines data consistency, integrity, lifecycle, recovery,
secondary-derived data, provenance, scope, and persistence boundaries.

It does not authorize implementation or select a concrete database
technology.

---

## 2. Architectural Authority

This Data Architecture SHALL be interpreted together with:

- LYRION Existing Architecture and Capability Baseline
- LYRION Unified Core Requirements PRD
- LYRION Core PRD Traceability and Acceptance Matrix
- LYRION Unified Core Architecture
- LYRION Phase-B Security Architecture
- Recursive Memory Architecture requirements
- applicable governance and validation requirements

The architecture principle is:

**PRESERVE → EXTEND → INTEGRATE → VALIDATE → REDESIGN ONLY WHEN REQUIRED**

No Data Architecture rule SHALL bypass the established LYRION security,
authority, execution, provenance, or governance boundaries.

---

## 3. Scope

This architecture covers:

- authoritative memory state
- transactional persistence
- memory object representation
- scope isolation
- provenance
- trust and confidence
- validation state
- integrity and versioning
- lifecycle management
- conflict and supersession state
- secondary indexes
- derived retrieval structures
- backup
- restore
- migration
- corruption detection
- corruption recovery
- audit linkage
- data-access boundaries
- RMA persistence requirements
- RMA/RLM separation

This architecture does not define:

- model architecture
- RLM reasoning algorithms
- agent authorization
- capability authorization
- execution authorization
- host execution
- sandbox policy
- frontend behavior
- voice authentication
- agent swarm policy

Those remain governed by their respective architectural boundaries.

---

## 4. Core Data Authority Principle

LYRION SHALL distinguish:

**Authoritative State ≠ Derived State ≠ Cache ≠ Retrieval Index ≠ Model Context**

Only authoritative state SHALL constitute the system of record for durable
memory facts and lifecycle state.

Secondary and derived structures SHALL NOT independently establish
authoritative memory truth.

A vector index, embedding store, cache, search index, retrieval projection,
or model context SHALL NOT become authoritative merely because it is used
during retrieval.

---

## 5. Authoritative Primary State

The authoritative memory state SHALL use a strongly consistent
transactional persistence model.

The authoritative store SHALL provide:

- atomic transactional updates
- consistency guarantees
- durable persistence
- concurrency control
- integrity protection
- version control
- lifecycle state
- provenance linkage
- audit linkage
- recovery support

The authoritative state SHALL be the source of truth from which applicable
secondary structures can be reconstructed.

The concrete persistence technology SHALL be selected only after technology
evaluation against this architectural contract.

---

## 6. Transactional Consistency

Memory operations that modify authoritative state SHALL execute within
defined transaction boundaries.

A transaction SHALL preserve applicable invariants across related state.

Partial application of an authoritative memory mutation SHALL NOT be
accepted as a valid completed operation.

Failed transactions SHALL fail without leaving an inconsistent authoritative
state.

Concurrent modifications SHALL use an explicit concurrency-control strategy
appropriate to the selected persistence technology.

The implementation SHALL prevent lost updates, invalid state transitions,
and unauthorized cross-scope mutations.

---

## 7. Memory Object Data Contract

A durable memory object SHALL support applicable metadata for:

- unique identity
- principal
- tenant
- session
- task
- agent
- project
- sensitivity
- source
- provenance
- evidence reference
- content or structured value
- trust
- confidence
- validation state
- integrity state
- version
- creation metadata
- modification metadata
- validity interval
- retention policy
- expiry
- revocation state
- deletion state
- supersession relationship
- conflict information
- audit reference

Not every field is required for every memory class, but omission SHALL be
defined by the applicable memory schema rather than assumed.

---

## 8. Scope Isolation

Memory SHALL preserve applicable scope boundaries:

- principal
- tenant
- session
- task
- agent
- project
- sensitivity

A memory read SHALL NOT automatically imply authorization to access every
memory object visible to the underlying persistence layer.

Data access SHALL be evaluated according to the applicable identity,
authority, policy, and scope controls.

Cross-scope access SHALL require explicit authorization.

Cross-tenant data leakage SHALL be treated as a security failure.

---

## 9. Provenance

Durable memory SHALL preserve sufficient provenance to establish:

- where information originated
- how it entered the system
- which principal or process produced it
- which task or agent was involved
- which validation occurred
- when the state was established or changed
- which version produced the current state
- applicable source references

Provenance SHALL remain linked to the authoritative memory object.

Loss of required provenance SHALL prevent promotion to an applicable trusted
memory state.

---

## 10. Trust and Validation State

Memory SHALL distinguish:

**Evidence → Provenance → Confidence → Trust → Validation State**

Model-generated information SHALL NOT become durable trusted memory merely
because a model generated it.

Applicable validation evidence SHALL be persisted with the memory lifecycle
state.

Trust SHALL be treated as data state and SHALL NOT constitute execution
authority.

---

## 11. Integrity Protection

Authoritative memory state SHALL be integrity-protected.

Integrity controls SHALL support detection of:

- unauthorized modification
- unexpected version changes
- corruption
- incomplete persistence
- inconsistent related state
- invalid lifecycle transitions

Integrity metadata SHALL be associated with the applicable authoritative
state and SHALL support verification during recovery and migration.

Integrity verification SHALL be independent of model-generated claims.

---

## 12. Versioning

Authoritative memory objects SHALL support controlled versioning where
required by their lifecycle.

Versioning SHALL allow the system to determine:

- current version
- previous version
- predecessor relationship
- superseding version
- validity period
- applicable provenance
- audit history

A newer version SHALL NOT silently erase the historical state when retention
of the previous state is required.

Version transitions SHALL preserve applicable scope and provenance controls.

---

## 13. Conflict Handling

The data architecture SHALL represent applicable memory conflicts.

A conflict SHALL NOT be resolved merely because one candidate was generated
more recently or by a model.

Conflict handling SHALL support applicable:

- detection
- representation
- validation
- promotion
- supersession
- expiration
- auditability

The resulting state SHALL preserve sufficient provenance to explain the
resolution lifecycle.

---

## 14. Memory Lifecycle

The authoritative lifecycle SHALL support:

**Evidence
→ Normalize
→ Trust / Provenance
→ Candidate
→ Validate
→ Scoped Persistence
→ Retrieve / Link
→ Conflict Detection
→ Promote / Supersede / Expire
→ World-State Proposal
→ Independent Validation**

Lifecycle operations SHALL preserve:

- scope
- provenance
- integrity
- version
- auditability
- applicable retention rules

---

## 15. Retention and Expiration

Memory SHALL support defined retention behavior.

Retention SHALL be applicable to:

- memory class
- sensitivity
- scope
- legal or operational requirements
- project requirements
- security requirements

Expiration SHALL result in an explicit lifecycle transition.

Expired data SHALL NOT silently remain trusted as current memory.

---

## 16. Revocation and Deletion

The architecture SHALL support controlled revocation and deletion.

Revocation SHALL be distinguishable from ordinary supersession where the
semantic distinction is required.

Deletion operations SHALL preserve applicable audit and provenance evidence
without retaining prohibited content.

Deletion SHALL propagate to applicable derived structures according to the
defined lifecycle policy.

Residual copies SHALL be governed by the applicable backup, retention, and
recovery policy.

---

## 17. Secondary and Derived Data

Secondary structures MAY include:

- relational secondary indexes
- search indexes
- semantic indexes
- embeddings
- retrieval projections
- caches
- materialized views
- analytical projections

These structures SHALL be treated as derived unless explicitly designated
as authoritative by the approved Data Architecture.

Derived structures SHOULD be reconstructible from authoritative state where
feasible.

A corrupted or stale secondary structure SHALL NOT redefine authoritative
memory truth.

---

## 18. Retrieval Architecture Boundary

Retrieval SHALL operate against authorized data.

Retrieval results SHALL retain sufficient linkage to authoritative memory
objects and provenance.

A retrieval result SHALL NOT automatically become durable memory.

Retrieved context SHALL remain distinguishable from authoritative memory.

Model context SHALL be treated as transient reasoning input unless explicitly
promoted through the memory lifecycle.

---

## 19. Backup Architecture

Authoritative memory SHALL have an applicable backup strategy before
production acceptance.

Backup controls SHALL address:

- backup integrity
- completeness
- scope
- retention
- encryption where required
- access control
- provenance
- backup version
- restore compatibility
- corruption detection

Backups SHALL NOT be considered valid merely because a backup operation
completed successfully.

---

## 20. Restore Architecture

Restore SHALL be treated as a validated recovery operation.

A restore process SHALL establish:

1. backup identity
2. backup integrity
3. compatibility
4. restore target
5. restored state
6. integrity verification
7. consistency verification
8. provenance preservation
9. secondary-index reconstruction or validation
10. recovery acceptance result

A restored state SHALL NOT automatically be trusted until applicable
verification succeeds.

---

## 21. Migration Architecture

Data migration SHALL be controlled, versioned, and verifiable.

Migration SHALL define:

- source schema/version
- target schema/version
- transformation rules
- compatibility requirements
- provenance preservation
- integrity preservation
- scope preservation
- lifecycle preservation
- validation criteria
- rollback or recovery strategy
- migration evidence

Migration SHALL NOT silently alter the semantic meaning of authoritative
memory.

Failed migration SHALL fail safely without silently replacing valid
authoritative state with incomplete state.

---

## 22. Corruption Detection

The architecture SHALL support detection of applicable corruption including:

- record corruption
- relationship inconsistency
- integrity mismatch
- invalid version transitions
- incomplete transactions
- index inconsistency
- schema incompatibility
- backup corruption

Corruption detection SHALL produce auditable evidence.

---

## 23. Corruption Recovery

Corruption recovery SHALL follow a controlled process:

**Detect → Isolate → Identify Valid State → Recover → Verify → Rebuild Derived
State → Revalidate → Resume**

Recovery SHALL NOT silently promote corrupted or unverified data.

Secondary structures MAY be discarded and reconstructed from authoritative
state when feasible.

Recovery SHALL preserve applicable provenance, scope, lifecycle, and audit
requirements.

---

## 24. RMA Boundary

Recursive Memory Architecture (RMA) manages memory architecture and
lifecycle.

RMA SHALL NOT:

- grant capabilities
- grant delegated authority
- authorize execution
- bypass Aegis
- bypass Capability Gateway
- bypass Secure Executor
- bypass sandbox controls
- bypass LHICF
- modify governing security policy

Memory state SHALL never constitute execution authority.

---

## 25. RMA and RLM Separation

Recursive Memory Architecture and Recursive Language Model reasoning SHALL
remain separate systems.

RMA manages:

- durable memory state
- memory lifecycle
- provenance
- trust state
- validation state
- retrieval linkage
- conflict handling
- persistence
- recovery

RLM manages bounded recursive reasoning.

RLM output SHALL remain reasoning/evidence and SHALL NOT establish
authorization or privileged memory authority.

---

## 26. Data Access Security Boundary

All access to authoritative memory SHALL pass through applicable identity,
scope, policy, and authorization controls.

No model, agent, retrieval component, plugin, connector, or external service
SHALL receive unrestricted direct access to authoritative memory.

Sensitive data access SHALL be explicitly governed.

Data access SHALL be auditable where required.

---

## 27. Auditability

Authoritative memory mutations SHALL support audit evidence sufficient to
determine applicable:

- actor/principal
- agent
- task
- operation
- target object
- previous version
- resulting version
- provenance
- validation state
- timestamp
- lifecycle transition
- recovery or migration event

Audit data SHALL remain outside model-controlled modification paths where
independence is required.

---

## 28. Failure Behavior

Data operations SHALL fail closed where security or integrity cannot be
established.

Examples include:

- integrity verification failure
- scope verification failure
- corrupted authoritative state
- invalid migration
- invalid restore
- unavailable required integrity metadata
- inconsistent lifecycle state

The system SHALL prefer controlled degradation or refusal over silently
using unverified authoritative memory.

---

## 29. Recovery and Derived-State Rule

The architectural hierarchy is:

**Authoritative State
→ Validation
→ Derived-State Reconstruction
→ Retrieval Availability**

not:

**Derived Retrieval State
→ Reconstructed Authority**

If secondary indexes are lost but authoritative state remains valid, the
system SHALL be capable of rebuilding applicable secondary structures.

If authoritative state cannot be verified, derived structures SHALL NOT be
used to manufacture authoritative truth.

---

## 30. Technology Selection Boundary

This document intentionally does not mandate a specific database engine,
vector database, cache, search engine, or storage provider.

Technology selection SHALL subsequently evaluate:

- consistency guarantees
- transaction semantics
- durability
- integrity controls
- backup/restore
- migration support
- corruption recovery
- scalability
- performance
- security
- operational maturity
- licensing
- supply-chain risk
- observability
- recoverability
- reconstruction capability

The selected technology SHALL demonstrably satisfy this architecture before
implementation acceptance.

---

## 31. Required Validation

Before applicable production acceptance, validation SHALL include:

- schema validation
- transaction consistency testing
- concurrency testing
- integrity verification
- scope-isolation testing
- provenance preservation testing
- lifecycle testing
- conflict-handling testing
- deletion/revocation testing
- backup validation
- restore validation
- migration validation
- corruption detection testing
- corruption recovery testing
- secondary-index reconstruction testing
- recovery provenance testing
- adversarial data-access testing

Testing SHALL include both normal and failure conditions.

---

## 32. Acceptance Criteria

The Data Architecture SHALL NOT be considered implementation-complete until:

1. authoritative state is explicitly defined;
2. strong consistency requirements are implemented and tested;
3. memory scope controls are implemented and tested;
4. provenance is preserved;
5. integrity controls are implemented and tested;
6. versioning is implemented where applicable;
7. lifecycle controls are implemented;
8. secondary structures are demonstrably derived where required;
9. backup has been validated;
10. restore has been validated;
11. migration has been validated;
12. corruption detection has been validated;
13. corruption recovery has been validated;
14. RMA/RLM separation is preserved;
15. security boundaries are validated;
16. audit evidence is produced;
17. applicable production acceptance evidence exists.

---

## 33. Traceability

This architecture directly addresses:

- CORE-MEM-001 — Scoped Memory
- CORE-MEM-002 — Provenance
- CORE-MEM-003 — Trust
- CORE-MEM-004 — Validation
- CORE-MEM-005 — Conflict Handling
- CORE-MEM-006 — Memory Lifecycle
- CORE-MEM-007 — Memory Data Integrity
- CORE-MEM-008 — RMA Separation
- TR-004 — Memory Data Integrity

Primary TR-004 contract:

**Primary authoritative state SHALL remain strongly consistent and
secondary indexes SHOULD be reconstructible where feasible.**

Backup, restore, migration, and corruption recovery SHALL be tested before
production acceptance.

---

## 34. Approval and Implementation State

**Data Architecture Baseline:** CLOSED — BASELINE VALIDATED; IMPLEMENTATION VALIDATION PENDING

**TR-004:** CLOSED — DATA ARCHITECTURE BASELINE VALIDATED; IMPLEMENTATION VALIDATION PENDING

**Core PRD Approval:** PENDING

**Core Architecture Approval:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Certification:** NOT CLAIMED

Creation of this document SHALL NOT be interpreted as authorization to
implement the memory/data subsystem.

---

## 35. Governing Principle

The LYRION data architecture SHALL preserve a strict distinction between:

**Data → Memory → Retrieval → Reasoning → Decision → Authority → Capability → Execution**

Durable data provides state and evidence.

It does not independently provide authority.

Authoritative memory remains strongly consistent, scoped, provenance-rich,
integrity-protected, lifecycle-governed, recoverable, and independently
verifiable.


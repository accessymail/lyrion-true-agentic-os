# LYRION Unified Core Memory & Provenance Specification

**Document ID:** TAOS-CORE-MEM-PROV-001
**Version:** 1.0.0
**Date:** 2026-09-22
**Status:** DRAFT — MEMORY / PROVENANCE BASELINE
**Architecture Approval:** PENDING

**Governing Architecture:** LYRION Unified Core Architecture
**Data Authority:** LYRION Unified Core Data Architecture
**Requirements Authority:** LYRION Unified Core Requirements PRD
**Traceability:** LYRION Core PRD Traceability & Acceptance Matrix

**Implementation Authorization:** NOT AUTHORIZED
**Production Implementation:** BLOCKED
**Production Certification:** NOT CLAIMED

---

# 1. Purpose

This specification defines the unified memory and provenance architecture
for LYRION True Agentic OS Core.

It formalizes the existing Recursive Memory Architecture (RMA), memory
object contract, lifecycle controls, provenance requirements, trust and
validation model, conflict handling, retrieval boundary, and causal
agentic provenance.

This specification SHALL extend the approved architectural direction
without creating a competing memory authority or execution authority.

---

# 2. Architectural Authority

This specification SHALL remain subordinate to:

1. Existing LYRION True Agentic OS Architecture
2. Existing LYRION Security Architecture
3. Existing Platform Blueprint
4. LYRION Unified Core Requirements PRD
5. LYRION Unified Core Architecture
6. LYRION Unified Core Data Architecture

Where this specification conflicts with a higher-authority approved
architecture or security control, the higher-authority control SHALL
prevail until formally reconciled.

---

# 3. Scope

This specification covers:

- memory object structure
- memory scope and isolation
- evidence and provenance
- trust and confidence
- validation state
- memory lifecycle
- conflict handling
- promotion and supersession
- retention and expiration
- revocation and deletion
- integrity and versioning
- authoritative memory state
- derived retrieval structures
- memory retrieval boundaries
- causal provenance
- agentic lineage
- auditability
- RMA/RLM separation
- recovery implications
- validation requirements

This specification does not authorize execution, privilege escalation,
agent authority, capability acquisition, or policy modification.

---

# 4. Core Memory Authority Principle

Memory SHALL be treated as governed state and evidence.

Memory SHALL NOT constitute:

- execution authority
- capability authorization
- delegated authority
- authentication authority
- policy authority
- security-root authority

The existence of information in memory SHALL NOT by itself authorize
an agent, model, tool, connector, or process to perform an action.

---

# 5. Memory State Classification

LYRION SHALL distinguish at minimum:

- Authoritative Primary State
- Derived State
- Retrieval Index
- Cache
- Materialized Projection
- Model Context
- External Evidence

These categories SHALL NOT be treated as interchangeable.

Authoritative primary memory state SHALL remain the system of record
according to the approved Data Architecture.

Derived structures SHALL NOT silently become authoritative.

---

# 6. Memory Scope

Memory SHALL be scoped according to applicable:

- principal
- tenant
- session
- task
- agent
- project
- sensitivity

Scope information SHALL be preserved throughout memory lifecycle
operations.

A retrieval operation SHALL NOT broaden authority merely because
information is technically retrievable.

Cross-scope access SHALL require explicit authorization and applicable
policy controls.

---

# 7. Memory Object Contract

A memory object SHOULD contain, where applicable:

- stable memory identifier
- memory type
- source
- evidence reference
- provenance
- principal
- tenant
- session
- task
- agent
- project
- sensitivity classification
- trust state
- confidence
- validation state
- integrity information
- version
- creation timestamp
- update timestamp
- validity interval
- retention policy
- expiration
- revocation state
- deletion state
- supersession relationship
- conflict relationship
- validation evidence
- audit references

The exact physical representation SHALL be determined by the approved
Data Architecture and implementation design.

---

# 8. Evidence and Source

Memory SHALL distinguish information from its supporting evidence.

Where applicable, memory SHALL retain:

- source identity
- source type
- source reference
- acquisition context
- acquisition timestamp
- originating principal
- originating task
- originating agent
- integrity information
- evidence location or reference
- validation status

Model-generated information SHALL NOT automatically become trusted
evidence merely because a model produced it.

---

# 9. Provenance

Memory provenance SHALL establish where information originated and how
it entered the memory system.

Provenance SHOULD identify applicable:

- human principal
- task
- agent
- delegation
- capability
- tool
- execution
- source
- host action
- verification
- outcome

Provenance SHALL remain linked to memory objects throughout applicable
lifecycle transitions.

---

# 10. Trust, Confidence and Validation

Trust, confidence and validation SHALL remain distinct concepts.

Trust MAY represent the assessed trust state of a source or information
object.

Confidence MAY represent uncertainty associated with information.

Validation SHALL represent whether the information has passed the
required validation process.

These properties SHALL NOT be collapsed into a single model-generated
score.

Model output SHALL NOT automatically receive durable trusted-memory
status.

---

# 11. Validation State

Memory information SHOULD support explicit states such as:

- observed
- candidate
- pending validation
- validated
- trusted
- superseded
- expired
- revoked
- rejected

The exact state machine SHALL be constrained by the applicable lifecycle
and governance requirements.

State transitions SHALL be auditable.

---

# 12. RMA Lifecycle

The canonical memory lifecycle SHALL be:

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

Lifecycle transitions SHALL preserve applicable:

- scope
- provenance
- integrity
- validation evidence
- auditability
- lifecycle state

---

# 13. Candidate Memory

Candidate memory represents information that has entered the memory
pipeline but has not yet achieved durable trusted-memory status.

Candidate state SHALL NOT imply:

- truth
- authority
- execution permission
- policy validity
- security trust

Candidate information MAY be used for bounded reasoning where policy
permits, but its unvalidated state SHALL remain visible to applicable
runtime components.

---

# 14. Durable Trusted Memory

Information SHALL NOT become durable trusted memory solely because:

- a model generated it
- an agent generated it
- it was retrieved repeatedly
- it appeared in a previous context
- it has a high model confidence score

Promotion to trusted durable memory SHALL require the applicable
validation and governance process.

---

# 15. Conflict Detection

The memory architecture SHALL support detection of conflicting
information.

Conflict handling SHOULD identify:

- conflicting objects
- provenance
- source identity
- timestamps
- scope
- validation state
- trust state
- supersession relationships
- resolution evidence

Conflict resolution SHALL NOT silently overwrite historical provenance.

---

# 16. Promotion and Supersession

Memory MAY be promoted, superseded, expired or otherwise transitioned
according to validated lifecycle policy.

Supersession SHALL preserve historical lineage where required.

A newer object SHALL NOT automatically invalidate an older object merely
because it was created later.

The applicable validation and policy context SHALL determine the state
transition.

---

# 17. Retention and Expiration

Memory SHALL support applicable retention and expiration controls.

Retention SHALL consider:

- sensitivity
- scope
- legal or operational requirements
- project requirements
- policy
- data lifecycle
- provenance requirements

Expiration SHALL be enforceable independently of model preference.

---

# 18. Revocation and Deletion

Memory SHALL support applicable revocation and deletion controls.

Revocation SHALL be distinguishable from deletion where preservation of
historical audit or provenance requires retaining a record of the
revoked object.

Lifecycle operations SHALL preserve applicable provenance and scope
controls.

---

# 19. Integrity and Versioning

Memory objects SHALL support integrity protection and versioning.

Integrity controls SHALL allow applicable detection of:

- unauthorized modification
- corruption
- inconsistent state
- unexpected version changes

Version transitions SHALL be auditable.

---

# 20. Authoritative Persistence Boundary

Authoritative memory persistence SHALL follow the approved Data
Architecture.

The authoritative primary state SHALL use the consistency model defined
by that architecture.

Authoritative memory operations SHALL preserve the applicable
transactional consistency guarantees defined by the Data Architecture.

Secondary indexes and derived retrieval structures SHOULD be
reconstructible where feasible.

No retrieval index SHALL silently become the authoritative source of
truth.

---

# 21. Retrieval Boundary

Memory retrieval SHALL remain subject to:

- identity
- scope
- authorization
- sensitivity
- task context
- policy
- provenance
- applicable data-access controls

Retrieval SHALL NOT grant new capability or authority.

The ability to retrieve information SHALL NOT imply permission to act
upon it.

---

# 22. Derived Retrieval Structures

LYRION MAY use:

- keyword indexes
- semantic indexes
- embeddings
- vector retrieval
- materialized views
- caches
- analytical projections
- other derived retrieval structures

These SHALL remain subordinate to authoritative primary state unless
explicitly designated otherwise by an approved architecture.

Derived structures SHOULD be reconstructible from authoritative state
where feasible.

---

# 23. RMA and Retrieval Separation

RMA is the governed memory architecture.

Retrieval mechanisms are implementation mechanisms used to locate or
construct relevant information.

Retrieval technology SHALL NOT redefine the memory architecture.

In particular:

**Vector database ≠ complete memory architecture.**

---

# 24. RMA and RLM Separation

Recursive Memory Architecture (RMA) and Recursive Language Model (RLM)
are distinct architectural systems.

RMA governs memory state, lifecycle, provenance and persistence.

RLM provides bounded recursive reasoning.

RLM SHALL NOT:

- grant authority
- grant capabilities
- bypass Aegis
- bypass Capability Gateway
- bypass Secure Executor
- bypass sandbox controls
- access unrestricted secrets
- establish privileged execution
- modify governance policy

RLM outputs SHALL be treated as reasoning or evidence, not authorization.

---

# 25. World-State Interaction

Memory MAY contribute information to World-State proposals.

A memory-derived World-State proposal SHALL remain subject to
independent validation.

Memory SHALL NOT unilaterally redefine authoritative external state.

Consequential state changes SHALL follow the established security and
execution architecture.

---

# 26. Causal Provenance

LYRION SHALL maintain causal provenance across consequential agentic
operations.

The minimum provenance chain SHALL be:

**Human
→ Task
→ Agent
→ Delegation
→ Capability
→ Tool
→ Execution
→ Host Action
→ Verification
→ Outcome**

Where applicable, provenance SHALL also identify:

- immutable event identity
- parent/child relationships
- task identity
- agent identity
- delegation identity
- capability identity
- execution identity
- target identity
- timestamps
- policy context
- authorization context
- verification evidence
- outcome
- failure state
- recovery state

---

# 27. Memory-to-Agentic Lineage

Memory created or modified during agentic execution SHOULD retain
lineage to the relevant:

- human principal
- root task
- agent
- delegation
- capability
- tool
- execution
- host operation
- verification result

This lineage SHALL support reconstruction of how information entered
memory and how it influenced consequential operations.

---

# 28. Auditability

Applicable memory lifecycle and provenance operations SHALL be
auditable.

Audit records SHOULD support reconstruction of:

- who or what produced information
- where it originated
- which task caused its creation
- which agent handled it
- which validation occurred
- which policy context applied
- which lifecycle transition occurred
- which subsequent state depended upon it

Audit records SHALL themselves remain subject to integrity and access
controls.

---

# 29. Security and Privacy Boundary

The Memory Data Access Security Boundary SHALL govern access to
authoritative and derived memory data.

Memory SHALL be treated as a security-sensitive data plane.

Controls SHALL address applicable:

- tenant isolation
- principal isolation
- task isolation
- agent isolation
- sensitivity enforcement
- unauthorized retrieval
- provenance tampering
- memory poisoning
- cross-context leakage
- unauthorized modification
- data exfiltration
- retention violations

Memory SHALL NOT become an unrestricted data-access mechanism for
models, agents, plugins, connectors or external services.

---

# 30. Memory Poisoning Resistance

LYRION SHALL treat memory poisoning as a first-class threat.

Controls SHALL support detection or mitigation of:

- malicious injected information
- false provenance
- fabricated validation
- unauthorized promotion
- poisoned retrieval content
- cross-task contamination
- cross-agent contamination
- malicious supersession
- replayed historical state

Memory validation SHALL remain independent of model confidence alone.

---

# 31. Backup, Restore and Recovery

Authoritative memory state SHALL participate in the Data Architecture
backup and recovery model.

Applicable production validation SHALL include:

- backup integrity
- restore correctness
- version preservation
- provenance preservation
- scope preservation
- corruption recovery
- migration correctness
- derived-index reconstruction

Recovery SHALL NOT silently restore revoked authority or invalidated
memory state.

---

# 32. Failure Behavior

Where memory integrity, provenance, scope or validation state cannot be
established reliably, the affected operation SHALL fail closed or enter
an explicitly bounded degraded state according to policy.

The system SHALL NOT silently convert uncertainty into trusted memory.

Corrupted or unverifiable derived structures SHOULD be discarded and
reconstructed from authoritative state where feasible.

---

# 33. Technology Boundary

This specification is technology-neutral.

Selection of:

- relational database
- document store
- object store
- vector index
- search engine
- cache
- event store
- graph store

SHALL occur only through the approved implementation architecture,
security review and validation process.

Technology selection SHALL NOT change the governing memory model.

---

# 34. Validation Requirements

Validation SHALL cover, as applicable:

1. scope isolation
2. provenance integrity
3. trust/validation separation
4. lifecycle transitions
5. conflict handling
6. supersession
7. retention
8. revocation
9. deletion
10. integrity/versioning
11. authoritative-state consistency
12. derived-index reconstruction
13. backup/restore
14. migration
15. corruption detection/recovery
16. memory poisoning resistance
17. RMA/RLM separation
18. causal provenance reconstruction
19. auditability
20. cross-task and cross-agent isolation

Validation SHALL progress through the established LYRION validation
hierarchy.

---

# 35. Acceptance Criteria

PB-DOC-014 SHALL be considered technically complete only when:

- CORE-MEM-001 through CORE-MEM-008 are explicitly satisfied
- Data Architecture boundaries are consistent
- Core Architecture §§22–24 are consistent
- causal provenance requirements are consistent with Core Architecture §29
- RMA/RLM separation is preserved
- memory authority is separated from execution authority
- lifecycle controls are defined
- security/privacy boundaries are defined
- recovery requirements are defined
- validation requirements are defined
- traceability is recorded
- document integrity checks pass

Formal architecture approval remains a separate governance decision.

---

# 36. Traceability

Primary requirements:

- CORE-MEM-001 — Scoped Memory
- CORE-MEM-002 — Provenance
- CORE-MEM-003 — Trust
- CORE-MEM-004 — Validation
- CORE-MEM-005 — Conflict Handling
- CORE-MEM-006 — Memory Lifecycle
- CORE-MEM-007 — Memory Data Integrity
- CORE-MEM-008 — RMA Separation

Architectural dependencies:

- Unified Core Architecture §22 — Memory Architecture
- Unified Core Architecture §23 — RMA and RLM Separation
- Unified Core Architecture §24 — Data Integrity and Memory Persistence
- Unified Core Architecture §29 — Causal Provenance Architecture
- Unified Core Data Architecture §§7–18 — Memory/Data Contract
- Unified Core Data Architecture §§24–27 — RMA, Access Security and Auditability

---

# 37. Approval and Implementation State

**Memory / Provenance Specification:** DRAFT — BASELINE

**Technical Validation:** PENDING

**Architecture Approval:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Implementation:** BLOCKED

**Production Certification:** NOT CLAIMED

This specification SHALL NOT be interpreted as authorization to begin
production implementation.

---

# 38. Governing Principle

LYRION memory SHALL preserve evidence, scope, provenance, integrity,
validation state and lifecycle history while remaining subordinate to
human authority, system governance and the established security and
execution boundaries.

**Memory informs intelligence.
Memory does not become authority.
Memory does not become capability.
Memory does not become execution.**


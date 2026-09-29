# LYRION R097 Opportunity Recovery Context Implementation Contract

## 1. Document Identity

- Document ID: PB-DOC-009-R097-ORC-CONTRACT
- Version: 1.0.0
- Classification: Phase-B Implementation Contract / Persistence Security Control
- Parent Requirement: PB-DOC-009
- Requirement: R097
- Parent Architecture: PB-DOC-009-R097-ORC-ARCH
- Status: IMPLEMENTATION CONTRACT DRAFT
- Implementation: NOT STARTED
- Production Operation: BLOCKED
- Production Certification: NOT CLAIMED

## 2. Purpose

Define the exact implementation contract required to persist and reconstruct authoritative Opportunity context for R097 recovery.

The contract exists to solve the confirmed gap where PersistentOpportunity currently stores lifecycle state but does not contain the complete PIAE Opportunity required for safe recovery reconstruction.

## 3. Security Invariant

The Opportunity Recovery Context is immutable historical execution context.

It is never an authority artifact.

It must never contain or restore:

- AuthorizationResult
- ExecutionAdmission
- delegated authority
- capability grant
- security approval
- active execution lease
- reusable authorization credential
- bypass credential

Recovery must reconstruct context first and then enter the current authorization and execution-admission path.

## 4. Domain Contract

The implementation must introduce a dedicated immutable domain contract representing the persisted recovery context.

Conceptual contract:

OpportunityRecoveryContext

Required fields:

### Identity

- opportunity_id
- correlation_id

### Source lineage

- trigger_event_ids
- source_provenance_ref

### Opportunity semantics

- relevant_state_ids
- goal_context
- title
- description
- user_relevance
- expected_benefit
- interruption_cost
- risk_score
- reversibility
- urgency
- confidence

### Security-relevant opportunity requirements

- required_capabilities
- required_autonomy_level
- sensitivity
- trust_level

### Lifecycle

- created_at
- expires_at
- original_status

### Integrity/versioning

- schema_version
- context_revision
- integrity_digest

The contract must be immutable after creation.

## 5. Field Rules

All identity fields must be non-empty.

Tuple/list fields must be normalized deterministically.

Datetime values must be timezone-aware.

Numeric bounded fields must preserve the same validation semantics as the existing Opportunity contract.

The reconstructed Opportunity must preserve the original semantic values.

No field may silently receive a fabricated default when the original authoritative value is unavailable.

## 6. Opportunity Identity Binding

The following relationship must be enforced:

OpportunityRecoveryContext.opportunity_id
==
PersistentOpportunity.opportunity_id
==
PersistentExecution.opportunity_id

Mismatch must fail closed.

A recovery operation must never substitute one opportunity context for another.

## 7. Execution Lineage Binding

Recovery must preserve:

- opportunity_id
- execution_id
- task_id

The Recovery Context identifies the opportunity.

PersistentExecution identifies the execution lineage.

Neither artifact grants authority.

## 8. Persistence Model

A dedicated durable persistence representation must be introduced.

Conceptual table:

persistent_opportunity_recovery_context

Required columns:

- opportunity_id
- correlation_id
- trigger_event_ids
- source_provenance_ref
- relevant_state_ids
- goal_context
- title
- description
- user_relevance
- expected_benefit
- interruption_cost
- risk_score
- reversibility
- urgency
- confidence
- required_capabilities
- required_autonomy_level
- sensitivity
- trust_level
- created_at
- expires_at
- original_status
- schema_version
- context_revision
- integrity_digest

The opportunity_id must be the stable identity boundary.

## 9. Immutability

The persistence interface must support creation and retrieval.

Normal runtime recovery must not provide mutation operations for the immutable context.

Updates to opportunity lifecycle state must continue through PersistentOpportunity.

Recovery state must remain separate from immutable context.

If an immutable context must ever change because of a future schema evolution, a new context version must be created under an explicit migration policy rather than silently mutating historical context.

## 10. Store Contract

Introduce a dedicated store protocol conceptually equivalent to:

OpportunityRecoveryContextStore

Required operations:

- create(context)
- get(opportunity_id)
- exists(opportunity_id)

Optional bounded administrative inspection may exist outside the runtime recovery path.

Runtime recovery must not expose arbitrary mutation.

## 11. Serialization Contract

The integrity digest must be calculated from a deterministic canonical representation.

Canonical serialization must:

- use stable field ordering
- normalize tuples/sequences
- normalize datetime representation
- preserve schema version
- exclude the integrity_digest field itself
- produce deterministic bytes

The digest algorithm must be explicitly defined by the implementation security review before implementation.

A digest mismatch must fail closed.

## 12. Integrity Boundary

Integrity verifies context authenticity within the persistence trust boundary.

Integrity does not establish:

- authorization
- capability permission
- policy approval
- execution admission
- current security state

Successful integrity verification only establishes that the persisted context matches its stored canonical representation.

## 13. Reconstruction Contract

The reconstruction service must conceptually expose:

resolve_opportunity_context(
    opportunity_id,
    current_time
)

The operation must:

1. Load the immutable context.
2. Verify existence.
3. Verify schema version.
4. Verify integrity.
5. Verify opportunity identity.
6. Validate temporal semantics.
7. Reconstruct the Opportunity domain object.
8. Validate the reconstructed Opportunity.
9. Return the validated Opportunity.

It must not authorize execution.

## 14. Recovery Integration Contract

The recovery flow must become:

PersistentRecoveryOrchestrator
-> PersistentExecution
-> opportunity_id
-> OpportunityRecoveryContextStore
-> integrity validation
-> Opportunity reconstruction
-> OpportunityContextFactory
-> current decision/context processing
-> CapabilityRequest
-> AegisAuthorizationService
-> CapabilityGateway
-> fresh ExecutionAdmission
-> PIAE execution path

The recovery layer must not call SecureExecutor directly.

## 15. Expiry Contract

The persisted expires_at value represents Opportunity lifecycle semantics.

During reconstruction:

current_time >= expires_at

must cause the Opportunity to be considered expired according to the existing Opportunity contract.

Expired context must not become executable merely because the persistent execution record is recoverable.

## 16. Current Security Revalidation

The Recovery Context must not persist current authorization state.

After reconstruction, the existing security chain must independently evaluate:

- principal
- task
- delegated authority
- required capabilities
- policy
- security state
- target
- resource state
- approval
- expiry
- revocation

Fresh authorization must precede fresh ExecutionAdmission.

## 17. Provenance Contract

The implementation must preserve source provenance.

At minimum:

- opportunity_id
- correlation_id
- trigger_event_ids
- source_provenance_ref
- execution_id
- recovery operation identifier

Current authorization and admission identifiers must be recorded separately after revalidation.

Historical context must never be represented as current authorization.

## 18. Schema Versioning

schema_version is mandatory.

Unknown schema versions must fail closed.

Backward-compatible versions may be explicitly supported.

Migration logic must be deterministic and separately validated.

Schema migration must never reinterpret historical context as authority.

## 19. Revision Semantics

context_revision represents the immutable context version.

The same opportunity identity must not silently change semantic context under the same revision.

A conflicting context for the same opportunity_id and revision must fail closed.

## 20. Idempotency

Creation must be idempotent by opportunity identity and immutable revision.

Repeated creation of the identical context must not create conflicting executable state.

A different semantic payload for an already-established immutable identity must be rejected rather than overwritten.

Recovery retries must continue using the same opportunity_id and execution lineage.

Fresh authorization and admission remain independently generated.

## 21. Transaction Boundary

Creation of the Opportunity Recovery Context must occur in the same logical persistence transaction as the lifecycle state that first establishes durable opportunity execution lineage where practical.

The transaction must prevent a durable executable opportunity from being committed without its required recovery context.

If atomic creation cannot be achieved for an existing deployment migration, the system must explicitly represent the missing-context condition and fail closed during recovery.

## 22. Existing Record Compatibility

Existing PersistentOpportunity records must remain readable.

Existing PersistentExecution records must remain readable.

Existing records without an Opportunity Recovery Context must not be reconstructed by guessing missing fields.

Such records must enter an explicit non-executable recovery condition until authoritative context is available.

## 23. Migration Contract

The migration must be additive.

It must:

- create the recovery-context persistence structure
- preserve existing lifecycle tables
- preserve existing execution tables
- avoid destructive conversion
- avoid inventing historical Opportunity fields
- support rollback according to the repository migration framework

Migration success does not constitute runtime validation or production certification.

## 24. Failure Contract

The implementation must fail closed for:

- missing context
- malformed context
- invalid identity
- integrity mismatch
- unsupported schema version
- invalid revision
- inconsistent lineage
- expired opportunity
- invalid Opportunity reconstruction
- missing required fields
- conflicting immutable context
- policy denial
- authorization denial
- revocation
- capability mismatch
- target/resource drift

No failure may silently continue into execution.

## 25. API Boundary

The recovery-context API must remain below the authorization boundary.

Permitted:

Recovery
-> Context Store
-> Context Validation
-> Opportunity Reconstruction

Not permitted:

Recovery
-> Context Store
-> AuthorizationResult
-> ExecutionAdmission

Authorization and admission must remain owned by existing trusted components.

## 26. Test Contract

Required implementation tests:

### Positive

- valid context persists
- valid context retrieves
- canonical digest verifies
- valid context reconstructs the same Opportunity
- identity binding succeeds
- valid recovered opportunity enters existing PIAE flow
- fresh CapabilityRequest is created
- fresh authorization is performed
- fresh ExecutionAdmission is created

### Negative

- missing context
- corrupted digest
- malformed payload
- unknown schema version
- identity mismatch
- execution/opportunity mismatch
- expired opportunity
- conflicting immutable revision
- fabricated/missing required field
- duplicate conflicting creation
- revoked authority
- changed policy
- stale authorization
- stale admission
- direct SecureExecutor bypass

## 27. Static Validation Contract

Before runtime tests:

- Python compilation must pass.
- Ruff must pass.
- Mypy must pass.
- AST/control-flow inspection must pass.
- Import validation must pass.
- Persistence mapping validation must pass.
- Migration syntax validation must pass.
- Contract compatibility validation must pass.
- Security-boundary validation must pass.
- Traceability validation must pass.

## 28. Runtime Validation Contract

Runtime validation must prove:

- context creation
- context retrieval
- integrity verification
- reconstruction
- identity binding
- expiry behavior
- missing-context fail-closed behavior
- schema-version handling
- duplicate handling
- recovery-to-PIAE integration
- fresh authorization
- fresh admission
- execution verification
- provenance recording

## 29. Acceptance Criteria

The contract is accepted for implementation only when:

1. Domain contract is compatible with existing Opportunity.
2. Persistence model contains all required reconstruction data.
3. Store contract is deterministic and fail-closed.
4. Integrity boundary is explicit.
5. Identity binding is enforced.
6. Recovery cannot obtain authority from context.
7. Existing Aegis authorization remains authoritative.
8. Existing CapabilityGateway remains authoritative for admission.
9. Existing SecureExecutor remains downstream of admission.
10. Existing lifecycle records remain backward compatible.
11. Migration is additive.
12. Negative and positive tests are defined.
13. Static and runtime validation are defined.
14. Provenance requirements are preserved.
15. No source implementation is claimed by this contract.

## 30. Explicit Non-Goals

This contract does not implement:

- self-learning
- self-evolution
- autonomous authority acquisition
- new authorization architecture
- new capability-grant architecture
- direct host execution
- SecureExecutor bypass
- replacement of Aegis
- replacement of CapabilityGateway
- production certification

## 31. Governance

This contract does not authorize implementation.

Required sequence:

Contract Review
-> Security Review
-> Threat Review
-> Migration Review
-> Controlled Implementation Gate
-> Implementation
-> Static Validation
-> Runtime Validation
-> Security Validation
-> Evidence Capture
-> Manifest Synchronization
-> Git Commit
-> Git Push

Production implementation remains blocked until the applicable governance state explicitly permits it.

Production certification is not claimed.

## 32. Status

Architecture specification: VALIDATED

Formal design review: PASS

Implementation contract: DRAFT

Schema implementation: NOT STARTED

Source implementation: NOT STARTED

Migration: NOT STARTED

Runtime validation: NOT STARTED

Production readiness: NOT CLAIMED

Production certification: NOT CLAIMED

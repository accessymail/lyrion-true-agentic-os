# LYRION R097 Opportunity Recovery Context Architecture Specification

## 1. Document Identity

- Document ID: PB-DOC-009-R097-ORC-ARCH
- Version: 1.0.0
- Classification: Phase-B Architecture / Security Control
- Parent Requirement: PB-DOC-009
- Requirement: R097
- Status: ARCHITECTURE DESIGN DRAFT
- Implementation: NOT AUTHORIZED BY THIS DOCUMENT
- Production Operation: BLOCKED
- Production Certification: NOT CLAIMED

## 2. Purpose

Define the authoritative durable context required to reconstruct a recovered LYRION opportunity without restoring execution authority, authorization, admission, or security state from checkpoint data.

This specification addresses the confirmed architectural gap in R097 recovery.

## 3. Core Security Invariant

Recovery may restore work context and lineage.

Recovery must never restore execution authority.

The following must always be newly evaluated after recovery:

- principal identity
- task identity
- delegated authority
- capability requirements
- policy
- security state
- target and resource state
- approval requirements
- expiry
- revocation
- execution admission

## 4. Confirmed Existing Architecture

Current architecture contains:

Event
-> OpportunityDetector
-> full Opportunity
-> PersistentOpportunity lifecycle record
-> PersistentExecution
-> Recovery

The current PersistentOpportunity representation contains lifecycle information only.

It does not durably contain the complete PIAE Opportunity context required by OpportunityContextFactory.

Therefore a recovered execution cannot safely reconstruct the original Opportunity from the current lifecycle record alone.

## 5. Architectural Requirement

Introduce a durable Opportunity Recovery Context.

The context is a reconstruction and provenance artifact.

It is NOT:

- authorization
- delegated authority
- capability admission
- execution permission
- security approval
- checkpoint authority

## 6. Required Durable Context

The recovery context must preserve sufficient immutable information to reconstruct the original opportunity identity and semantic context.

Required categories:

### Identity and lineage

- opportunity_id
- correlation_id
- trigger_event_ids
- source provenance reference
- schema version

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

### Lifecycle information

- created_at
- expires_at
- original opportunity status
- immutable context revision

The persisted context must not contain a reusable authorization or admission artifact.

## 7. Immutability Boundary

The original opportunity context must be immutable after creation.

Mutable recovery state remains in the existing lifecycle records.

Conceptually:

Immutable:

OpportunityRecoveryContext

Mutable:

PersistentOpportunity
PersistentExecution
RuntimeLease
RecoveryState

This prevents recovery processing from silently changing the semantic identity of the original opportunity.

## 8. Reconstruction Contract

Recovery must resolve context using:

opportunity_id
-> authoritative OpportunityRecoveryContext
-> schema/version validation
-> integrity validation
-> expiry evaluation
-> current state reconstruction
-> current security evaluation
-> fresh CapabilityRequest
-> Aegis authorization
-> CapabilityGateway
-> fresh ExecutionAdmission
-> governed execution

Failure to resolve or validate the context must fail closed.

## 9. Authority Separation

The recovery context must never provide:

- AuthorizationResult
- ExecutionAdmission
- active lease authority
- delegated authority token
- security decision
- capability grant
- bypass credential

Those objects must be recreated through the current authorization and admission path.

## 10. Provenance

The reconstructed opportunity must preserve provenance sufficient to answer:

- Which opportunity was recovered
- Which source event created it
- Which execution referenced it
- Which recovery operation reconstructed it
- Which current policy evaluated it
- Which current authorization decision was produced
- Which fresh admission was created
- Which execution occurred afterward

Historical provenance must remain distinguishable from current authorization state.

## 11. Integrity

The recovery context must support integrity verification.

At minimum:

- schema version
- deterministic serialization
- integrity digest
- immutable identity
- revision
- provenance reference

Integrity failure must cause recovery to fail closed.

The integrity mechanism must not be interpreted as authorization.

## 12. Expiry

Opportunity expiry must be evaluated against current time during recovery.

A stored expiry timestamp is historical context.

It is not an authorization grant.

Expired opportunity context must not automatically produce a fresh capability request.

## 13. Revocation and Policy Drift

Recovery must re-evaluate current security state.

Historical context cannot establish that:

- a principal remains authorized
- delegated authority remains valid
- a capability remains permitted
- a target remains permitted
- a policy remains unchanged
- an approval remains valid

Any current revocation or policy restriction must take precedence.

## 14. Backward Compatibility

Existing lifecycle records must remain valid.

Existing PersistentOpportunity and PersistentExecution records must not be reinterpreted as containing the missing full opportunity context.

Recovery of records without recoverable authoritative context must fail closed or enter an explicit non-executable recovery state.

No fabricated Opportunity may be generated.

## 15. Integration Boundary

The new context must integrate with the existing PIAE architecture.

Target flow:

PersistentRecoveryOrchestrator
-> PersistentExecution
-> opportunity_id
-> OpportunityRecoveryContextStore
-> Opportunity reconstruction
-> OpportunityContextFactory
-> current decision and intent construction
-> CapabilityRequest
-> AegisAuthorizationService
-> CapabilityGateway
-> ExecutionAdmission
-> PIAE
-> PersistentExecutionRunner
-> SecureExecutor
-> verification
-> provenance

The implementation must not create a parallel authorization system.

## 16. Failure Handling

The following conditions must fail closed:

- missing recovery context
- unknown schema version
- integrity failure
- malformed context
- inconsistent opportunity identity
- expired opportunity
- revoked security state
- invalid authority
- policy denial
- target drift
- capability mismatch
- ambiguous reconstruction
- missing required context
- duplicate conflicting context
- unsupported context version

No failure may silently become executable work.

## 17. Idempotency

Recovery must preserve execution lineage.

The following identifiers must remain stable:

- opportunity_id
- execution_id
- task_id
- request lineage

Fresh authorization and fresh admission identifiers must be generated according to the existing contracts.

Recovery must not create duplicate executable work when the same recovery attempt is replayed.

## 18. Migration Requirement

Schema migration must be additive.

Existing persistent records must remain readable.

Migration must not convert historical lifecycle state into assumed authorization.

Existing records without recovery context must remain explicitly identifiable as requiring reconstruction or controlled non-executable handling.

## 19. Security Threat Coverage

The design must prevent:

- stale authority restoration
- checkpoint authority injection
- forged opportunity context
- context tampering
- identity substitution
- opportunity substitution
- policy bypass
- authorization bypass
- admission bypass
- direct SecureExecutor invocation
- fail-open recovery
- replay-driven duplicate execution

## 20. Required Validation

Before implementation acceptance:

1. Contract validation
2. Schema validation
3. Persistence mapping validation
4. Integrity validation
5. Reconstruction validation
6. Identity binding validation
7. Expiry validation
8. Revocation validation
9. Policy drift validation
10. Fail-closed validation
11. Idempotency validation
12. Provenance validation
13. Migration compatibility validation
14. Existing PIAE integration validation
15. Security boundary validation

## 21. Required Negative Tests

The implementation design must eventually prove:

- N01 missing context is rejected
- N02 corrupted context is rejected
- N03 wrong opportunity identity is rejected
- N04 wrong execution lineage is rejected
- N05 expired opportunity is rejected
- N06 revoked authority is rejected
- N07 changed policy is re-evaluated
- N08 old admission cannot be restored
- N09 old authorization cannot be restored
- N10 direct execution bypass is rejected
- N11 duplicate recovery cannot create duplicate executable work
- N12 unsupported context version is rejected

## 22. Required Positive Tests

The implementation must eventually prove:

- P01 valid context reconstructs the correct Opportunity
- P02 reconstructed Opportunity enters the existing PIAE path
- P03 a fresh CapabilityRequest is created
- P04 fresh authorization and fresh admission are created
- P05 valid recovered work can continue only after current governance checks succeed

## 23. Architectural Constraints

The implementation must:

- preserve existing PB-DOC-009 contracts
- preserve existing Aegis authorization
- preserve CapabilityGateway
- preserve ExecutionAdmission
- preserve SecureExecutor boundaries
- preserve existing execution lineage
- avoid parallel authorization
- avoid authority restoration
- avoid fabricated opportunity fields
- avoid fail-open recovery
- minimize source changes
- maintain backward compatibility

## 24. Design Decision

The current lifecycle-only PersistentOpportunity model is insufficient for safe R097 recovery reconstruction.

A dedicated durable Opportunity Recovery Context is therefore required before the recovery bridge can be implemented safely.

This context is a provenance and reconstruction mechanism only.

It does not grant authority.

## 25. Governance Boundary

This document does not authorize implementation.

Required sequence:

Architecture Review
-> Security Review
-> Threat Review
-> Contract Review
-> Implementation Authorization Check
-> Controlled Implementation
-> Static Validation
-> Runtime Validation
-> Security Validation
-> Evidence Capture
-> Manifest Synchronization
-> Git Commit
-> Git Push

Production implementation remains blocked until the applicable governance state explicitly permits it.

Production certification is not claimed.

## 26. Status

Architecture gap: CONFIRMED

Opportunity Recovery Context requirement: DEFINED

Implementation: NOT STARTED

Source modification: NONE

Validation: DESIGN VALIDATION PENDING

Production readiness: NOT CLAIMED

Production certification: NOT CLAIMED

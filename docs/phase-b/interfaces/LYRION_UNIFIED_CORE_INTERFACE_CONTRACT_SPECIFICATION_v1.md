# LYRION Unified Core — Interface / Contract Specification

**Document ID:** TAOS-CORE-INTERFACE-CONTRACT-001  
**Version:** 1.0.0  
**Date:** 2026-09-23  
**Status:** DRAFT — INTERFACE / CONTRACT BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the governed interface and contract architecture for the LYRION True Agentic OS Core.

It establishes explicit contracts between Core components while preserving the existing LYRION architecture and the Phase-B authority, security, execution, memory, observability, recovery, and host-integration boundaries.

---

## 2. Scope

This specification covers:

- Agent Contracts
- Identity and Authority Contracts
- Delegation Contracts
- Capability Contracts
- Governance Contracts
- Execution Contracts
- Host Contracts
- Application Contracts
- Tool/API Contracts
- Event Contracts
- Memory and Provenance Contracts
- Verification Contracts
- Recovery Contracts
- Security and operational contract requirements

Contracts SHALL remain subordinate to the approved architectural authority boundaries.

---

## 3. Terminology

For this specification:

**Contract** means a formally defined interface agreement governing structure, semantics, ownership, validation, authorization context, lifecycle, compatibility, security, and failure behavior.

**Interface** means a controlled interaction boundary between architectural components.

**Contract Owner** means the authoritative component responsible for defining and maintaining the contract semantics.

**Contract Consumer** means a component using a contract according to its permitted scope.

A contract SHALL NOT itself grant authority.

---

## 4. Architectural Position

Interfaces provide communication and integration boundaries across the LYRION Core.

They SHALL NOT become an independent security authority.

The canonical execution architecture remains:

**Human Intent → Authenticated Principal → Lyri Interpretation → Task → Planning → Agent Delegation → Delegated Authority → Aegis → Capability Authorization → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host/Application/Device → Independent Verification → Memory/Audit/Provenance → Lyri → Human**

Contracts SHALL integrate with this architecture rather than create parallel authority or execution paths.

---

## 5. Contract Design Principles

Contracts SHALL be:

- Explicit
- Versioned
- Owned
- Scoped
- Validated
- Authenticated where applicable
- Integrity-protected where applicable
- Replay-resistant where applicable
- Observable
- Provenance-aware
- Fail-closed for security-critical failures
- Backward-compatible only where explicitly permitted
- Revocable where applicable

Contract structure SHALL NOT be interpreted as authorization.

---

## 6. Contract Identity

Every security-relevant contract SHALL have an identifiable:

- Contract ID
- Version
- Owner
- Consumer scope
- Lifecycle state
- Compatibility policy
- Security classification
- Validation state
- Provenance context

Ambiguous or unidentified contracts SHALL fail closed where security significance exists.

---

## 7. Contract Ownership

Each contract SHALL have one authoritative owner.

Contract ownership SHALL define:

- Semantic authority
- Version authority
- Change authority
- Compatibility policy
- Validation responsibility
- Deprecation policy
- Security responsibility

Consumers SHALL NOT redefine owner-controlled semantics.

---

## 8. Contract Versioning

Contracts SHALL use explicit versioning.

Version changes SHALL distinguish:

- Compatible changes
- Additive changes
- Deprecated fields
- Breaking changes
- Security-sensitive changes
- Migration-required changes

Breaking changes SHALL NOT be silently accepted.

---

## 9. Agent Contracts

Agent contracts SHALL represent governed agent identity, lifecycle, task participation, communication, resources, and state.

Agent contracts SHALL preserve:

- Agent identity
- Principal context
- Task identity
- Delegation lineage
- Capability scope
- Resource scope
- Lifecycle state
- Provenance

Agent contract messages SHALL NOT grant authority merely through message content.

---

## 10. Identity and Authority Contracts

Identity contracts SHALL distinguish:

- Human principal
- Lyri identity
- Session identity
- Task identity
- Agent identity
- Model identity
- Provider identity
- Tool identity
- Application identity
- Host identity

Authority contracts SHALL represent delegated authority independently from identity.

Identity SHALL NOT automatically imply authority.

---

## 11. Delegation Contracts

Delegation contracts SHALL represent:

- Parent authority
- Child authority
- Task binding
- Agent binding
- Capability scope
- Target scope
- Time bounds
- Policy constraints
- Resource limits
- Revocation state
- Provenance

Delegation SHALL attenuate or preserve authority according to approved policy.

Delegation SHALL NOT itself authorize execution.

---

## 12. Capability Contracts

Capability contracts SHALL define the permitted capability semantics and boundaries.

Capability discovery SHALL NOT grant authorization.

Capability contracts SHALL preserve:

- Capability identity
- Scope
- Target
- Operation
- Constraints
- Required authority
- Policy requirements
- Resource requirements
- Verification requirements

Capability contracts SHALL integrate with the Capability Gateway and Capability Authorization boundary.

---

## 13. Governance Contracts

Governance contracts SHALL represent applicable:

- Policy decisions
- Trust decisions
- Risk decisions
- Approval requirements
- Denials
- Revocations
- Quarantine state
- Containment state
- Emergency controls

Aegis remains the independent governance and security authority.

Contracts SHALL NOT allow agents or models to modify governing policy.

---

## 14. Action Proposal Contracts

Action Proposal contracts SHALL represent proposed consequential actions before authorization and execution.

An action proposal SHALL preserve:

- Principal
- Task
- Agent
- Delegation
- Capability
- Target
- Operation
- Requested scope
- Risk context
- Resource context
- Provenance

Action proposals SHALL NOT be treated as authorization.

---

## 15. Capability Authorization Contracts

Capability Authorization contracts SHALL represent the authoritative authorization result applicable to a capability request.

Authorization SHALL be bound to applicable:

- Principal
- Agent
- Task
- Delegation
- Capability
- Target
- Operation
- Policy
- Time
- Resources
- Approval state

A contract consumer SHALL NOT enlarge an authorization decision.

---

## 16. Execution Admission Contracts

Execution Admission contracts SHALL represent the controlled transition from authorized intent to executable operation.

Admission SHALL validate applicable:

- Identity
- Authority
- Capability Authorization
- Target
- Operation
- Policy
- Resources
- Sandbox requirements
- Approval requirements
- Replay protection
- Expiry and revocation

Execution Admission SHALL remain upstream of Secure Executor.

---

## 17. Secure Execution Contracts

Secure Execution contracts SHALL define the request and result boundary for Secure Executor.

Secure Executor SHALL execute only operations that passed applicable authorization and execution admission.

Secure Executor SHALL NOT:

- Grant authority
- Expand capability
- Infer privilege
- Bypass Aegis
- Bypass Capability Authorization
- Bypass Execution Admission
- Bypass Agent Sandbox
- Bypass LHICF
- Create alternate privileged execution

---

## 18. Sandbox Contracts

Sandbox contracts SHALL define execution isolation requirements.

Applicable contract fields SHALL represent:

- Agent/task binding
- Filesystem scope
- Process scope
- Network scope
- Credential scope
- Environment scope
- Resource limits
- Timeout
- Cancellation
- Isolation state

Sandbox escape or boundary violation SHALL be treated as a security event.

---

## 19. LHICF Contracts

LHICF contracts SHALL define controlled host-integration operations.

LHICF SHALL mediate applicable:

- Filesystem operations
- Process operations
- Service operations
- Network operations
- Application operations
- Desktop/UI operations
- Device operations
- Clipboard operations
- Notification operations
- OS-state operations

LHICF SHALL NOT create an alternate authorization path.

---

## 20. Universal Computer Contracts

Universal Computer contracts SHALL represent governed host/application-neutral operations.

The Universal Computer contract flow is:

**Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Host Operation → Verification → Provenance**

Universal Computer contracts SHALL preserve the authority established upstream.

---

## 21. Host Harness Contracts

Host Harness contracts SHALL define:

- Host discovery
- Host identity
- Host capability discovery
- Capability-to-host mapping
- Adapter selection
- Host operation
- Host verification
- Host provenance

Host discovery SHALL NOT grant execution authority.

Host mapping SHALL NOT enlarge authority.

Host Harness SHALL NOT become an independent security authority.

---

## 22. Application Harness Contracts

Application Harness contracts SHALL define:

- Application identity
- Application discovery
- Capability discovery
- Application capability binding
- Target identification
- Operation identification
- Adapter selection
- Application interaction
- Verification
- Provenance

Application Harness requests SHALL NOT bypass Capability Authorization or Capability Gateway authorization where applicable.

---

## 23. Tool and API Contracts

Tool/API contracts SHALL define:

- Tool identity
- API identity
- Operation identity
- Input schema
- Output schema
- Authentication context
- Authorization context
- Resource limits
- Timeout
- Error behavior
- Provenance

Tool/API integration SHALL NOT create authorization.

---

## 24. MCP and A2A Contracts

MCP and A2A integrations SHALL be treated as external protocol contracts.

Protocol messages SHALL pass through:

**Identity → Trust → Policy → Capability Authorization → Execution Admission → Secure Execution**

MCP/A2A messages SHALL NOT grant authority merely through message content.

Untrusted or unauthenticated protocol peers SHALL fail closed where applicable.

---

## 25. Event Contracts

Event contracts SHALL define:

- Event identity
- Event type
- Producer
- Consumer
- Timestamp
- Correlation
- Causation
- Scope
- Payload classification
- Integrity
- Provenance
- Replay controls

Security-relevant events SHALL remain attributable and integrity-protected.

---

## 26. Inter-Agent Communication Contracts

Inter-agent contracts SHALL preserve:

- Sender identity
- Receiver identity
- Task scope
- Agent scope
- Delegation lineage
- Message integrity
- Replay protection
- Correlation
- Provenance

Message content SHALL NOT grant authority.

Cross-task or cross-tenant messages SHALL fail closed when scope is invalid.

---

## 27. Memory and RMA Contracts

Memory contracts SHALL preserve:

- Source
- Provenance
- Principal
- Tenant
- Session
- Task
- Agent
- Sensitivity
- Trust
- Confidence
- Integrity
- Version
- Retention
- Revocation
- Supersession
- Conflict state

Generated model output SHALL NOT become trusted durable memory merely because it was generated by a model.

RMA contracts SHALL remain distinct from RLM reasoning contracts.

---

## 28. RLM Contracts

RLM contracts SHALL represent bounded recursive reasoning operations.

RLM contracts SHALL preserve:

- Recursion limits
- Tool-call limits
- Context limits
- Time limits
- Token limits
- Resource limits
- Isolation requirements
- Provenance

RLM SHALL NOT obtain authority through its contract.

RLM SHALL NOT bypass security, sandbox, authorization, execution-admission, or host boundaries.

---

## 29. Verification Contracts

Verification contracts SHALL define independent validation of consequential outcomes.

Verification SHALL distinguish:

- Requested operation
- Admitted operation
- Executed operation
- Observed effect
- Verified outcome

Model claims SHALL NOT establish execution success.

Execution completion SHALL NOT automatically constitute verified success.

---

## 30. Provenance Contracts

Provenance contracts SHALL preserve the causal chain:

**Human → Task → Agent → Delegation → Capability → Tool → Execution → Host Action → Verification → Outcome**

Provenance SHALL remain attributable and tamper-evident where required.

---

## 31. Error Contracts

Error contracts SHALL use structured, bounded error representations.

Errors SHALL distinguish applicable:

- Invalid request
- Authentication failure
- Authorization denial
- Admission denial
- Policy denial
- Capability denial
- Timeout
- Cancellation
- Resource exhaustion
- Sandbox violation
- Backend unavailable
- Host failure
- Verification failure
- Recovery failure
- Security violation

Errors SHALL NOT expose secrets or unnecessary sensitive information.

---

## 32. Recovery Contracts

Recovery contracts SHALL require revalidation before consequential continuation.

Recovery SHALL revalidate applicable:

- Identity
- Task
- Policy
- Delegated authority
- Capability
- Authorization
- Execution Admission
- Resources
- Sandbox
- Security state

Expired or revoked authority SHALL remain invalid.

Checkpoint data SHALL NOT restore authority merely because it was previously valid.

---

## 33. Resource Contracts

Resource contracts SHALL define applicable budgets for:

- CPU
- Memory
- Storage
- Network
- Execution time
- Tool calls
- Tokens
- Retries
- Processes
- Agents
- Swarm depth
- Swarm width
- Artifacts
- Egress

Security-critical resource limits SHALL be enforced outside model instructions.

---

## 34. HITL Contracts

HITL contracts SHALL represent approval requirements without creating an alternate execution authority.

Applicable approval context SHALL bind:

- Authenticated human principal
- Request digest
- Task
- Action
- Capability
- Policy version
- Eligibility
- Expiry
- Replay protection
- Approval provenance

Approval SHALL remain subject to the normal authorization and execution chain.

---

## 35. Authentication and Transport Contracts

External interfaces SHALL use approved secure transport.

Applicable transport boundaries include:

- HTTPS/TLS for application APIs
- WSS for realtime control
- WebRTC for voice/media where applicable

Transport authentication SHALL bind to the authenticated principal.

Transport metadata SHALL NOT be treated as authorization without explicit policy.

---

## 36. Session and Context Contracts

Session contracts SHALL distinguish:

- Principal context
- Session context
- Task context
- Agent context
- Correlation context
- Turn context

Correlation metadata SHALL NOT be interpreted as authorization.

Turn context SHALL NOT grant execution authority.

Cross-principal session access SHALL fail closed.

---

## 37. Contract Validation and Schema Rules

Contracts SHALL be validated before acceptance.

Validation SHALL include where applicable:

- Schema validation
- Type validation
- Required-field validation
- Scope validation
- Identity validation
- Integrity validation
- Version validation
- Authorization-context validation
- Resource validation
- Replay validation
- Security-policy validation

Malformed security-relevant contracts SHALL fail closed.

---

## 38. Contract Compatibility and Change Control

Contract changes SHALL be controlled through versioned change management.

Changes SHALL identify:

- Contract owner
- Reason
- Security impact
- Compatibility impact
- Consumers
- Migration requirements
- Validation requirements
- Rollback requirements
- Provenance

Security-sensitive changes SHALL require appropriate review before adoption.

---

## 39. Security Invariants

The following SHALL remain invariant:

1. Contracts SHALL NOT grant authority.
2. Interfaces SHALL NOT become alternate authorization authorities.
3. Model output SHALL NOT be authorization.
4. Agent intent SHALL NOT be authorization.
5. Delegation SHALL NOT itself authorize execution.
6. Capability discovery SHALL NOT grant authorization.
7. Application/host discovery SHALL NOT grant authorization.
8. MCP/A2A/API messages SHALL NOT grant authorization.
9. Secure Executor SHALL NOT expand authority.
10. Universal Computer SHALL NOT bypass security controls.
11. Host Harness SHALL NOT create alternate privileged execution.
12. Application Harness SHALL NOT create alternate privileged execution.
13. Expired authority SHALL remain invalid.
14. Revoked authority SHALL remain invalid.
15. Recovery SHALL revalidate authority.
16. Consequential operations SHALL be independently verifiable.
17. Provenance SHALL remain attributable.
18. Emergency controls SHALL remain independent.
19. Security-critical failures SHALL fail closed.
20. No alternate privileged path SHALL exist.

---

## 40. Traceability

This specification SHALL maintain traceability to the Core requirements and validation matrix.

**TR-001 — Inter-Agent Message Integrity:** inter-agent contracts SHALL preserve attribution, integrity, scope, replay resistance, impersonation resistance, and SHALL NOT derive authority from message content.

**TR-002 — RLM Isolation:** RLM contracts SHALL preserve governed isolation and SHALL NOT provide authority or security-boundary bypass.

**TR-003 — Memory Lifecycle:** contract-generated memory, evidence, and provenance SHALL remain subject to governed memory lifecycle controls.

**TR-004 — Memory Data Integrity:** contract-generated persistent state SHALL follow the approved Data Architecture consistency, backup, restore, migration, and corruption-recovery requirements.

**TR-005 — Supply-Chain Admission:** contract participants, adapters, tools, MCP servers, A2A peers, dependencies, and related integrations SHALL remain subject to evidence-based supply-chain admission.

**TR-006 — Agent Swarm Governance:** if swarm execution is introduced, contracts SHALL preserve identity, lineage, bounded depth/width, capability attenuation, budgets, namespace isolation, communication authorization, cancellation, and emergency controls. Swarm remains deferred Agentic Expansion.

**TR-007 — Observability:** contract lifecycle, security events, provenance, execution, verification, and failures SHALL integrate with governed observability.

**TR-008 — Core Validation:** contracts SHALL be validated through the Core Validation Specification.

**TR-009 — Security Testing:** contracts SHALL be subject to applicable security testing, including authorization-boundary, integrity, replay, isolation, resource, recovery, emergency, and adversarial testing.

These references define traceability relationships only and SHALL NOT grant implementation authorization or production status.

---

## 41. Validation Requirements

Contract validation SHALL include:

- Structural validation
- Semantic validation
- Cross-document consistency
- Security validation
- Compatibility validation
- Negative testing
- Failure testing
- Replay testing
- Boundary testing
- Recovery testing
- Provenance testing
- Independent verification testing

No contract SHALL be considered production-valid solely because it is syntactically valid.

---

## 42. Security Testing Requirements

Security testing SHALL cover:

- Authentication failures
- Authorization failures
- Contract tampering
- Message replay
- Message impersonation
- Scope confusion
- Cross-task leakage
- Cross-tenant leakage
- Capability escalation
- Authority expansion
- Alternate-path attempts
- MCP/A2A abuse
- Tool/API abuse
- Resource exhaustion
- Malformed payloads
- Schema confusion
- Recovery with stale authority
- Expired authority
- Revoked authority
- Sandbox boundary violations
- Provenance tampering
- Emergency-control bypass

---

## 43. Observability and Audit

Contract processing SHALL produce appropriate observability data.

Security-relevant records SHALL support:

- Request identity
- Contract identity
- Version
- Producer
- Consumer
- Task
- Agent
- Authorization context
- Decision
- Execution state
- Verification state
- Failure state
- Provenance

Sensitive data SHALL be protected according to applicable security and privacy controls.

---

## 44. Failure and Fail-Closed Behavior

Security-critical contract failures SHALL fail closed.

This includes:

- Invalid identity
- Invalid signature/integrity
- Invalid scope
- Missing authorization context
- Expired authority
- Revoked authority
- Invalid capability
- Invalid admission
- Invalid policy
- Replay
- Unsupported contract version
- Invalid schema
- Security-state uncertainty

A contract failure SHALL NOT expand authority.

---

## 45. Cross-Document Dependencies

This specification depends upon and SHALL remain consistent with:

- Phase-B Architecture Baseline
- Phase-B Security Architecture
- Core Requirements PRD
- Agentic Runtime Specification
- Identity and Authority Specification
- Capability Model Specification
- Agent Harness Specification
- Host Harness Specification
- Universal Computer Specification
- Application Harness Specification
- Execution Admission Specification
- Aegis Governance Specification
- Secure Execution Specification
- Data Architecture
- Memory / Provenance Specification
- Observability Specification
- Validation Specification
- Security Testing Specification
- Operations Specification
- Recovery / Resilience Specification
- Phase-B Master Manifest

No contract SHALL override a higher-authority architecture or security boundary.

---

## 46. Acceptance Criteria

PB-DOC-012 SHALL be considered documentation-baseline valid only when:

- All required sections are present.
- Contract domains are defined.
- Ownership and versioning are defined.
- Identity and authority separation is explicit.
- Capability and execution boundaries are explicit.
- Security invariants are present.
- Traceability TR-001 through TR-009 is present.
- Recovery/revalidation is defined.
- Provenance and verification are defined.
- Cross-document dependencies are reconciled.
- Structural validation passes.
- Semantic reconciliation passes.
- Governance state remains correctly represented.

---

## 47. Final Interface / Contract Invariant

The LYRION True Agentic OS Core SHALL preserve:

**Interface ≠ Contract Authority ≠ Identity ≠ Delegated Authority ≠ Capability Authorization ≠ Execution Admission ≠ Secure Execution ≠ Verification**

No interface, contract, protocol, event, adapter, tool, API, MCP integration, A2A integration, Universal Computer operation, Host Harness operation, or Application Harness operation SHALL create an alternate privileged path.

---

## 48. Documentation Status

This document is an architectural and documentation baseline.

Current state:

**DOCUMENTATION BASELINE: DRAFT — INTERFACE / CONTRACT BASELINE**

**STRUCTURAL VALIDATION: PENDING**

**SEMANTIC RECONCILIATION: PENDING**

**ARCHITECTURE APPROVAL: PENDING**

**IMPLEMENTATION AUTHORIZATION: NOT AUTHORIZED**

**PRODUCTION IMPLEMENTATION: BLOCKED**

**PRODUCTION CERTIFICATION: NOT CLAIMED**

Documentation existence SHALL NOT authorize implementation.

---

## 49. Governance and Approval

PB-DOC-012 SHALL remain subject to the Phase-B governance process.

Implementation SHALL NOT begin solely because this specification exists.

Architecture approval, security review, threat-model review, interface review, validation approval, and implementation authorization remain separate governance decisions.

The specification SHALL be updated only through controlled change management.

**Final governance state:**

**Architecture Approval: PENDING**

**Implementation Authorization: NOT AUTHORIZED**

**Production Implementation: BLOCKED**

**Production Certification: NOT CLAIMED**

---

**End of PB-DOC-012 — Interface / Contract Specification**

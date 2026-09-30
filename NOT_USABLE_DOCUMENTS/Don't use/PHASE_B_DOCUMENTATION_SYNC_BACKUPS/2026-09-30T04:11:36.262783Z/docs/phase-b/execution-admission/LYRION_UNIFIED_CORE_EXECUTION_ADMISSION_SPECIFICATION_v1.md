# LYRION Unified Core — Execution Admission Specification

**Document ID:** TAOS-CORE-EXEC-ADMISSION-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Status:** DRAFT — EXECUTION ADMISSION BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Execution Admission boundary for the LYRION Unified Core.

Execution Admission determines whether an already-authorized operation is eligible to cross into the controlled execution path after applicable authority, capability authorization, policy, security, approval, resource, expiry, revocation, and related preconditions have been satisfied.

Execution Admission SHALL preserve the established separation between authority, capability, authorization, admission, execution, and verification.

---

## 2. Scope

This specification covers:

- execution-admission lifecycle;
- admission request structure;
- identity and task binding;
- delegated authority binding;
- capability authorization binding;
- Aegis decision binding;
- policy and security preconditions;
- resource constraints;
- approval and HITL state;
- expiry and revocation;
- replay resistance;
- target and operation binding;
- admission decision handling;
- Secure Executor integration;
- Agent Sandbox integration;
- LHICF integration;
- Universal Computer integration;
- Host Harness and Application Harness integration;
- fail-closed behavior;
- cancellation;
- recovery and revalidation;
- emergency controls;
- provenance;
- observability;
- validation and security testing.

This specification does not replace Aegis, Capability Gateway, Secure Executor, Agent Sandbox, LHICF, Universal Computer, Host Harness, Application Harness, or independent verification.

---

## 3. Source Hierarchy

The Execution Admission architecture SHALL remain subordinate to the approved Phase-B architecture, security architecture, capability model, identity and delegated-authority model, execution architecture, and applicable governance decisions.

Where this document conflicts with an approved higher-level architecture, the higher-level approved architecture governs and the conflict SHALL be recorded and resolved through the established governance process.

---

## 4. Architectural Principles

Execution Admission SHALL preserve the following distinctions:

- authority is not capability;
- capability is not authorization;
- authorization is not execution admission;
- execution admission is not execution;
- execution is not verification;
- verification is not authorization.

Execution Admission SHALL NOT infer authority or privilege from model output, natural-language intent, memory, tool metadata, application discovery, host discovery, or agent preference.

---

## 5. Execution Admission Definition

Execution Admission is the controlled decision boundary that determines whether a specific operation, already subject to applicable authorization, may proceed to the controlled execution mechanism.

Admission SHALL be:

- explicit;
- attributable;
- policy-bound;
- task-bound;
- agent-bound;
- capability-bound;
- target-bound;
- operation-bound;
- resource-bound;
- time-bound where applicable;
- revocable;
- replay-resistant;
- observable;
- auditable;
- fail-closed where required.

---

## 6. Admission Lifecycle

The admission lifecycle SHALL support:

1. admission request creation;
2. context binding;
3. authorization-state evaluation;
4. security-state evaluation;
5. approval-state evaluation;
6. resource-state evaluation;
7. expiry and revocation evaluation;
8. replay-resistance evaluation;
9. admission decision;
10. controlled handoff to Secure Executor;
11. execution-result correlation;
12. independent verification;
13. provenance recording.

An admission decision SHALL NOT create authority that was not already granted upstream.

---

## 7. Admission Request Contract

Each Admission Request SHALL include an attributable **Admission Context** sufficient to evaluate the applicable identity, task, agent, delegated authority, capability, authorization, policy, target, operation, security, resource, approval, expiry, revocation, replay, and provenance conditions.

The Admission Context SHALL remain bound to the specific request and SHALL NOT be interpreted as an independent grant of authority.

An execution-admission request SHALL identify sufficient context to determine exactly what operation is being considered.

Where applicable, the request SHALL preserve:

- initiating principal;
- session;
- task;
- agent;
- delegated authority;
- capability;
- capability authorization;
- target;
- operation;
- policy context;
- security context;
- approval state;
- resource constraints;
- expiry state;
- revocation state;
- provenance context;
- request identity;
- integrity information.

Incomplete or ambiguous security-relevant admission requests SHALL NOT be admitted.

---

## 8. Principal and Task Binding

Admission SHALL remain bound to the applicable authenticated principal and task context.

A request SHALL NOT become executable merely because an equivalent operation was previously authorized for:

- another principal;
- another task;
- another session;
- another agent;
- another target;
- another scope.

Cross-task or cross-principal substitution SHALL fail closed where applicable.

---

## 9. Agent Binding

Execution admission SHALL identify the agent responsible for the admitted operation where an agent is involved.

Agent identity SHALL remain distinct from:

- human principal;
- Lyri;
- session;
- task;
- model;
- model provider;
- tool;
- capability;
- delegated authority.

Agent identity SHALL NOT independently confer execution authority.

---

## 10. Delegated Authority Binding

Admission SHALL consume the applicable delegated-authority state.

Delegated authority SHALL remain:

- task-bound;
- agent-bound;
- capability-scoped;
- target-bound where applicable;
- time-bounded where applicable;
- revocable;
- policy-bound;
- replay-resistant.

Child authority SHALL NOT exceed the authority granted by the applicable parent delegation.

Execution Admission SHALL NOT enlarge delegated authority.

---

## 11. Capability Authorization Binding

Capability authorization SHALL precede execution admission.

Execution admission SHALL occur only after applicable capability authorization has succeeded.

Capability possession, capability discovery, capability metadata, or capability mapping SHALL NOT by themselves establish admission.

Requests failing applicable capability authorization SHALL NOT reach the Secure Executor or LHICF.

---

## 12. Aegis Decision Binding

Aegis SHALL remain independent of model and agent reasoning.

Execution Admission SHALL consume applicable Aegis security and governance decisions.

Aegis may provide applicable:

- policy decisions;
- risk decisions;
- denial;
- approval requirements;
- revocation;
- containment;
- quarantine;
- emergency controls.

Execution Admission SHALL NOT override, weaken, or reinterpret a governing Aegis denial or containment decision.

Agents and models SHALL NOT modify their governing security policy.

---

## 13. Policy Preconditions

Admission SHALL evaluate applicable policy conditions before allowing execution.

Policy evaluation SHALL consider applicable:

- operation policy;
- capability policy;
- task policy;
- agent policy;
- target policy;
- data policy;
- security policy;
- resource policy;
- approval policy;
- environmental restrictions.

Policy failure SHALL result in denial or other explicitly governed non-execution behavior.

---

## 14. Target and Operation Binding

The admitted operation SHALL identify the intended target and operation with sufficient precision for the applicable execution boundary.

Operation identity SHALL NOT be inferred solely from natural-language intent or model output.

Target substitution SHALL NOT be permitted merely because another target is discoverable, available, or technically accessible.

Where target or operation identity cannot be established reliably, admission SHALL fail closed where required.

---

## 15. Security Preconditions

Execution Admission SHALL evaluate applicable security state before admission.

Security preconditions MAY include:

- trusted runtime state;
- sandbox state;
- host-integrity state;
- credential state;
- security-control availability;
- policy state;
- authorization state;
- revocation state;
- emergency-control state.

Required security controls that are unavailable, invalid, or degraded beyond their permitted operating condition SHALL prevent admission where required.

---

## 16. Resource Preconditions

Admission SHALL preserve applicable resource limits.

Resource controls MAY include:

- CPU;
- memory;
- storage;
- network;
- execution time;
- tool calls;
- tokens;
- cost;
- process count;
- agent count;
- swarm depth;
- artifact size;
- egress;
- retries.

Resource limits SHALL be enforced outside model instructions where security-critical.

Resource exhaustion or unavailable required resources SHALL prevent admission where applicable.

---

## 17. Approval and HITL Preconditions

Where policy requires human approval, execution admission SHALL require the applicable approved HITL state.

Approval SHALL be bound to the relevant:

- authenticated human principal;
- request;
- task;
- operation;
- target;
- authorization context;
- policy version;
- expiry;
- provenance.

Approval SHALL NOT be treated as unlimited authority.

Execution Admission SHALL reject stale, invalid, revoked, mismatched, or replayed approval state.

---

## 18. Expiry and Revocation

Admission SHALL evaluate expiry and revocation state at the point of admission.

Expired authorization SHALL fail closed.

Revoked authority, capability authorization, approval, or security state SHALL prevent admission where applicable.

Previously valid admission state SHALL NOT automatically restore authorization after revocation or expiry.

---

## 19. Replay Resistance

Execution admission SHALL protect against unauthorized replay.

Admission requests and applicable admission records SHALL use sufficient binding to prevent reuse in an unrelated context.

Where applicable, replay protection SHALL preserve:

- request identity;
- principal binding;
- task binding;
- agent binding;
- capability binding;
- target binding;
- operation binding;
- authorization binding;
- provenance binding;
- expiry;
- uniqueness or nonce state.

A previously admitted operation SHALL NOT automatically authorize an unrelated new execution.

---

## 20. Admission Decision

The admission decision SHALL produce an explicit result.

The decision SHALL distinguish at minimum:

- admitted;
- denied;
- expired;
- revoked;
- approval required;
- security control unavailable;
- resource unavailable;
- invalid request;
- replay detected;
- target or operation mismatch;
- policy failure;
- containment or emergency stop.

An admission decision SHALL be attributable and auditable.

---

## 21. Admission Record

An admitted operation SHALL have sufficient admission evidence to correlate the decision with the operation that follows.

The admission record SHOULD preserve, where applicable:

- admission identifier;
- request identifier;
- principal;
- task;
- agent;
- delegated authority;
- capability;
- authorization state;
- Aegis decision;
- policy state;
- target;
- operation;
- approval state;
- resource constraints;
- security state;
- expiry;
- revocation state;
- timestamp;
- provenance;
- integrity metadata.

The admission record SHALL NOT itself constitute unrestricted authority.

---

## 22. Secure Executor Boundary

The Secure Executor SHALL remain downstream of Execution Admission.

The Secure Executor SHALL execute only operations already authorized and admitted by the governing architecture.

The Secure Executor SHALL NOT infer privilege from:

- model output;
- natural-language intent;
- memory;
- tool metadata;
- application discovery;
- host discovery;
- operation descriptions.

Execution Admission SHALL NOT duplicate Secure Executor enforcement.

---

## 23. Agent Sandbox Boundary

Operations requiring controlled execution SHALL remain within the applicable Agent Sandbox or execution boundary.

Execution Admission SHALL verify that required sandbox conditions are available before admission where applicable.

Sandbox enforcement SHALL remain independent of model cooperation.

Execution Admission SHALL NOT bypass sandbox isolation.

---

## 24. LHICF Boundary

Host operations SHALL pass through the established LYRION Host Integration & Control Fabric where applicable.

The canonical execution relationship SHALL remain:

**Aegis → Capability Gateway → Secure Executor → Agent Sandbox → LHICF → Host/Application Adapter → Host/Application → Independent Verification → Provenance**

Execution Admission SHALL NOT create an alternate host-control mechanism outside LHICF.

---

## 25. Universal Computer Relationship

The Universal Computer SHALL consume execution admission rather than redefine it.

The governed operation path SHALL remain:

**Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Operation → Independent Verification → Provenance**

Universal Computer operation descriptions SHALL NOT create privilege independently of admission.

---

## 26. Host Harness Relationship

Host Harness operations SHALL remain subject to the established authorization and execution-admission chain.

The Host Harness SHALL NOT independently authorize operations.

Direct host commands SHALL NOT constitute an alternate execution-admission mechanism.

---

## 27. Application Harness Relationship

Application Harness operations SHALL remain subject to the established execution-admission boundary.

Application discovery, application capability discovery, adapter selection, or application API availability SHALL NOT create execution authority.

Application interaction SHALL preserve admission, authorization, target, operation, resource, policy, security, verification, and provenance context.

---

## 28. Fail-Closed Behavior

Execution Admission SHALL fail closed where required for security-relevant uncertainty.

Fail-closed conditions SHALL include applicable:

- invalid authorization;
- missing authority;
- revoked authority;
- expired authority;
- invalid approval;
- replay;
- target mismatch;
- operation mismatch;
- unavailable security control;
- unavailable required sandbox;
- unavailable required verification;
- policy denial;
- containment;
- emergency stop;
- integrity failure.

Unknown security-relevant conditions SHALL NOT be converted into implicit permission.

---

## 29. Cancellation

Execution admission SHALL support cancellation before execution where applicable.

Cancellation SHALL be attributable and observable.

Cancellation SHALL NOT be treated as successful verification.

Where execution has already begun, cancellation behavior SHALL follow the Secure Executor and recovery architecture.

---

## 30. Idempotency and Duplicate Execution Protection

Consequential operations SHALL support appropriate duplicate-execution protection.

Where an operation is not safely repeatable, the execution path SHALL preserve sufficient request and execution identity to detect unauthorized duplication.

Execution Admission SHALL NOT convert a previously admitted consequential operation into unlimited replayable execution authority.

---

## 31. Recovery and Revalidation

Recovery SHALL revalidate applicable:

- principal;
- task;
- agent;
- delegated authority;
- capability;
- authorization;
- policy;
- security state;
- resource state;
- approval;
- expiry;
- revocation;
- target;
- operation.

Expired or revoked authority SHALL NOT be restored merely because a checkpoint contains previous admission state.

Consequential external effects SHALL use appropriate idempotency or compensation mechanisms.

---

## 32. Emergency Controls

Emergency controls SHALL remain independent of model and agent cooperation.

Applicable emergency actions MAY include:

- pause;
- revoke;
- quarantine;
- isolate;
- disconnect;
- terminate.

Agents SHALL NOT disable, weaken, or modify their own emergency controls.

Execution Admission SHALL respect active emergency and containment decisions.

---

## 33. Provenance and Audit

Execution Admission SHALL integrate with causal provenance.

Applicable provenance SHALL preserve the relationship:

**Human/Principal → Task → Agent → Delegation → Capability → Authorization → Execution Admission → Tool/Adapter → Execution → Host/Application Operation → Verification → Outcome**

Admission decisions SHALL be attributable and auditable.

Security-sensitive admission records SHALL use tamper-evident mechanisms where supported by the approved persistence architecture.

---

## 34. Observability

Execution Admission SHALL expose sufficient observability to determine:

- admission requests;
- decisions;
- denial reasons;
- policy decisions;
- authorization state;
- approval state;
- revocation state;
- resource state;
- security state;
- execution correlation;
- cancellation;
- recovery;
- emergency actions;
- verification outcome.

Observability SHALL NOT expose sensitive credentials or protected data unnecessarily.

---

## 35. Failure Handling

Failures SHALL be classified and handled according to their security and operational significance.

Security-relevant failures SHALL fail closed where required.

Partial execution SHALL be distinguishable from successful completion.

An admission success SHALL NOT be interpreted as execution success.

Execution failure SHALL NOT be converted into successful verification.

---

## 36. Validation Requirements

Execution Admission SHALL be validated through the established validation hierarchy:

1. static validation;
2. unit validation;
3. integration validation;
4. adversarial security validation;
5. real-infrastructure validation;
6. operational exercises;
7. independent assurance where applicable;
8. scoped security acceptance.

Validation SHALL demonstrate that unauthorized or invalid operations cannot cross the controlled execution boundary.

---

## 37. Security Testing

Security testing SHALL include, where applicable:

- missing authorization;
- invalid authority;
- revoked authority;
- expired authority;
- replay;
- request substitution;
- target substitution;
- operation substitution;
- stale approval;
- approval mismatch;
- policy denial;
- Aegis denial;
- resource exhaustion;
- sandbox failure;
- LHICF bypass attempt;
- Secure Executor bypass attempt;
- direct host execution attempt;
- application authorization bypass;
- recovery with stale authority;
- emergency-stop bypass;
- provenance tampering;
- cross-task execution;
- cross-agent execution;
- cross-principal execution;
- duplicate consequential execution.

Negative tests SHALL demonstrate fail-closed behavior.

---

## 38. Cross-Document Dependencies

Execution Admission depends upon and SHALL remain consistent with:

- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Identity and Delegated Authority Specification;
- Capability Model;
- Agent Harness Specification;
- Host Harness Specification;
- Universal Computer Specification;
- Application Harness Specification;
- Aegis Governance Specification;
- Secure Execution Specification;
- Agent Sandbox architecture;
- LHICF architecture;
- HITL Governance;
- Memory and Provenance architecture;
- Recovery and Resilience Specification;
- Core Validation Specification;
- Security Testing Specification;
- Phase-B Master Manifest.

---

## 39. Governance Boundary

### Security Invariants

The following Security Invariants SHALL remain authoritative for Execution Admission:

- Universal Computer SHALL NOT bypass authorization or Execution Admission.
- Host Harness SHALL NOT create or use an alternate privileged execution path.
- Application Harness SHALL NOT create or use an alternate privileged execution path.
- Expired authority SHALL remain invalid.
- Revoked authority SHALL remain invalid.
- Execution Admission SHALL NOT create or enlarge authority.
- Execution Admission SHALL NOT replace Capability Authorization, Aegis, Capability Gateway, Secure Executor, Agent Sandbox, LHICF, Universal Computer, Host Harness, Application Harness, or independent verification.
- Security-relevant uncertainty SHALL fail closed where required.
- Recovery SHALL revalidate applicable authority, authorization, security state, expiry, and revocation.
- Independent verification SHALL remain separate from the admission decision.
- Causal provenance SHALL remain attributable across the admission and execution lifecycle.

This specification defines the Execution Admission contract.

It SHALL NOT:

- grant authority;
- replace Aegis;
- replace Capability Authorization;
- replace the Capability Gateway;
- replace Secure Executor;
- replace Agent Sandbox;
- replace LHICF;
- replace Universal Computer;
- replace Host Harness;
- replace Application Harness;
- replace independent verification.

Architecture approval SHALL precede implementation authorization.

Implementation authorization SHALL precede production implementation.

Production certification SHALL require independent evidence according to the approved certification process.

---

## 40. Acceptance Criteria

### PRD Traceability References

PB-DOC-009 SHALL preserve explicit traceability to the approved Core PRD traceability matrix:

- **TR-001** — Inter-Agent Message Integrity: Execution Admission SHALL preserve attributable agent/task/delegation context and SHALL NOT admit operations when required identity, attribution, authorization, or integrity conditions are invalid.
- **TR-002** — RLM Isolation: Execution Admission SHALL NOT treat recursive reasoning output as authority or permit reasoning to bypass authorization, admission, sandbox, or execution boundaries.
- **TR-003** — Memory Lifecycle: Admission decisions and resulting execution records SHALL preserve applicable provenance and lifecycle relationships required by the approved memory architecture.
- **TR-004** — Memory Data Integrity: Admission SHALL rely on authoritative state and validated security/authorization state rather than treating derived or stale retrieval state as execution authority.
- **TR-005** — Supply Chain Admission: Execution Admission SHALL remain subject to approved capability, tool, adapter, dependency, integrity, and security admission controls where applicable.
- **TR-006** — Agent Swarm Governance: Any delegated or multi-agent execution SHALL remain subject to bounded identity, authority, capability, resource, and cancellation controls; Execution Admission SHALL NOT create unbounded swarm authority.
- **TR-007** — Observability: Admission requests, decisions, denials, authorization state, security state, execution correlation, recovery, emergency actions, and verification outcomes SHALL remain observable as defined by the approved observability architecture.
- **TR-008** — Core Validation: Execution Admission SHALL be validated through the approved validation hierarchy and SHALL demonstrate that unauthorized or invalid operations cannot cross the controlled execution boundary.
- **TR-009** — Security Testing: Execution Admission SHALL be subject to the approved security-testing specification, including negative tests for authorization, authority, replay, bypass, recovery, emergency-control, provenance, and cross-boundary failures.

PB-DOC-009 SHALL be considered documentation-baseline complete only when:

- required sections are present;
- terminology is consistent with approved Phase-B architecture;
- Capability Authorization precedes Execution Admission;
- Execution Admission does not become an alternate authorization authority;
- Aegis independence is preserved;
- Secure Executor remains downstream;
- Agent Sandbox remains enforced;
- LHICF remains the host-integration boundary;
- Universal Computer and Host/Application Harness boundaries remain intact;
- expiry and revocation are addressed;
- replay resistance is addressed;
- recovery revalidation is addressed;
- fail-closed behavior is defined;
- provenance is defined;
- validation and security-testing requirements are defined;
- semantic reconciliation identifies and resolves terminology or architectural conflicts;
- the Gap Register records the resulting state.

---

## 41. Semantic Reconciliation

PB-DOC-009 SHALL be reconciled against the existing Capability Model, Host Harness, Universal Computer, Phase-B Architecture Baseline, and Phase-B Security Architecture.

The reconciliation SHALL confirm that:

- Capability Authorization remains upstream of Execution Admission;
- Aegis remains an independent governance and security authority;
- The Capability Gateway SHALL remain the authoritative execution-admission boundary;
- Secure Executor remains downstream of authorization and admission;
- Agent Sandbox remains an execution isolation boundary;
- LHICF remains the controlled host-integration boundary;
- Universal Computer remains a host-independent operation abstraction;
- Host Harness and Application Harness do not create alternate privileged paths;
- execution admission does not enlarge delegated authority;
- verification remains independent of admission;
- provenance remains causal and attributable;
- recovery revalidates authority and security state.

The semantic reconciliation confirms that PB-DOC-009 preserves the established Capability Model, Universal Computer, Host Harness, Phase-B Architecture, and Phase-B Security Architecture boundaries.

Capability Authorization remains upstream of Execution Admission, and the Capability Gateway remains the authoritative execution-admission boundary.

Aegis remains an independent governance and security authority. Secure Executor remains downstream of authorization and admission. Agent Sandbox and LHICF remain enforced execution and host-integration boundaries.

Universal Computer, Host Harness, and Application Harness do not introduce alternate privileged execution paths. Execution Admission does not enlarge delegated authority.

Expiry, revocation, replay resistance, fail-closed behavior, recovery revalidation, independent verification, and causal provenance remain preserved.

The reconciliation precheck completed with 15/15 checks passing and 0 failures. Whitespace normalization was used only for source comparison and did not alter any source document.

No substantive semantic conflict was identified during the reconciliation.

---

## 42. Implementation Boundary

This document is a documentation and architecture baseline.

It does not authorize implementation.

Implementation SHALL begin only after the applicable Phase-B architecture approval and implementation authorization gates have been formally satisfied.

---

## 43. Acceptance State

**Structural Validation:** PASS  
**Semantic Reconciliation:** RECONCILED  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 44. Governance and Change Control

Changes to Execution Admission SHALL preserve compatibility with the approved Phase-B architecture and security model.

Security-boundary changes SHALL require appropriate architecture and security review.

Changes SHALL preserve provenance, traceability, validation evidence, and version history.

---

## 45. Final Execution Admission Invariant

The following invariant SHALL remain authoritative:

**Authority ≠ Capability ≠ Authorization ≠ Execution Admission ≠ Execution ≠ Verification**

And:

**Execution Admission SHALL NOT create authority.**

The canonical governed execution relationship remains:

**Human Intent → Lyri Interpretation → Task → Agent Delegation → Aegis → Capability Authorization → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host/Application → Independent Verification → Memory/Audit/Provenance → Lyri → Human**

No alternate privileged execution path SHALL be introduced.

## Controlled Implementation-Validation Slice Record

The bounded Execution Admission implementation-validation slice has
evidence-backed acceptance.

- Runtime compilation: `4/4 PASS`
- Tests: `86 PASSED / 0 FAILED`
- Evidence review: `CONTROLLED_VALIDATION_EVIDENCE_VERIFIED`
- Slice acceptance: `EXECUTION_ADMISSION_SLICE_ACCEPTED`
- Full PB-DOC-009 validation: `NOT CLAIMED`
- Production implementation: `BLOCKED`
- Production certification: `NOT CLAIMED`

Acceptance record:

`docs/phase-b/validation/EXECUTION_ADMISSION_SLICE_ACCEPTANCE_RECORD_v1.md`

# LYRION Unified Core Capability Model Specification

**Document ID:** TAOS-CORE-CAPABILITY-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Status:** DRAFT — CAPABILITY MODEL BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This document defines the capability model for the LYRION Unified Core.

The capability model establishes how capabilities are represented, scoped, bound,
authorized, admitted, executed, verified, revoked, observed, and attributed.

The model preserves the established distinction between authority, capability,
authorization, execution, and verification.

---

## 2. Scope

This specification covers:

- capability identity and definition;
- capability classification;
- capability scope;
- capability binding;
- capability-to-authority relationships;
- target binding;
- task binding;
- policy binding;
- resource constraints;
- approval requirements;
- expiration and revocation;
- capability authorization;
- Capability Gateway;
- execution admission;
- host capability mapping;
- unsupported capability handling;
- sandbox interaction;
- LHICF interaction;
- verification;
- provenance and audit;
- inter-agent capability delegation;
- Universal Computer capability boundaries;
- capability security invariants;
- validation requirements.

This specification does not replace the Secure Executor, Agent Sandbox,
LHICF, Host Harness, Universal Computer, Agent Harness, or Aegis specifications.

---

## 3. Source Hierarchy

Capability behavior SHALL remain consistent with the following authoritative
architecture sources:

1. LYRION Unified Core Requirements PRD;
2. LYRION Unified Core Architecture;
3. LYRION True Agentic OS Phase-B Architecture Baseline;
4. LYRION True Agentic OS Phase-B Security Architecture;
5. Phase-B Threat Model when approved;
6. Agent Identity and Authority Specification;
7. Secure Execution specifications;
8. Host Harness and Universal Computer specifications;
9. Validation and Security Testing specifications.

Where a downstream implementation conflicts with an approved higher-level
security or authority constraint, the higher-level constraint governs.

---

## 4. Architectural Principles

The capability model SHALL preserve these distinctions:

- Capability is not authority.
- Capability is not authorization.
- Authorization is not execution.
- Execution is not verification.
- Capability possession SHALL NOT imply unlimited authority.
- Capability discovery SHALL NOT grant authority.
- Capability description SHALL NOT grant authority.
- Model output SHALL NOT grant authority.
- Agent intent SHALL NOT grant authority.
- Tool output SHALL NOT grant authority.
- Memory content SHALL NOT automatically grant authority.
- External protocol messages SHALL NOT grant authority.

Consequential operations SHALL pass through the approved authorization and
execution architecture.

---

## 5. Capability Definition

A capability represents a bounded class of operation that LYRION may potentially
authorize.

A capability definition SHALL identify the operation class and applicable
constraints without itself granting authority.

Capability definitions SHOULD identify, as applicable:

- capability identifier;
- operation class;
- target class;
- supported environments;
- required authority class;
- applicable policy;
- resource constraints;
- risk classification;
- approval requirements;
- verification requirements;
- provenance requirements;
- supported adapters.

A capability definition SHALL NOT constitute authorization.

---

## 6. Capability Identity

Each capability SHALL have a stable identifier within its applicable namespace.

Capability identity SHALL be distinguishable from:

- human identity;
- Lyri identity;
- agent identity;
- session identity;
- task identity;
- model identity;
- provider identity;
- tool identity;
- external service identity.

Capability identifiers SHALL NOT be treated as principals.

---

## 7. Capability Classification

Capabilities SHOULD be classified according to their operational and security
characteristics.

Classification MAY consider:

- read versus write behavior;
- local versus external effects;
- reversible versus consequential effects;
- data sensitivity;
- privilege requirements;
- resource consumption;
- network exposure;
- credential exposure;
- process or service impact;
- approval requirements;
- verification requirements.

Classification SHALL support deny-by-default handling for privileged operations.

---

## 8. Capability Scope

Capability scope SHALL be explicit and bounded.

Applicable scope dimensions include:

- principal;
- tenant;
- session;
- task;
- agent;
- project;
- capability;
- target;
- operation;
- resource;
- environment;
- policy;
- time;
- approval state;
- security state.

A capability SHALL NOT be broader than the applicable authority and policy
under which it is bound.

---

## 9. Capability Binding

Capability binding associates a capability with the authority context in which
it may be considered for use.

Capability binding SHOULD include:

- principal;
- task;
- agent;
- delegated authority;
- capability;
- target;
- scope;
- policy;
- resource limits;
- time constraints;
- approval state;
- revocation state;
- provenance context.

Capability binding SHALL NOT bypass independent authorization.

---

## 10. Capability and Authority Relationship

Authority determines what a principal may be permitted to do.

A capability identifies a bounded operation class.

The effective permission SHALL be constrained by both authority and capability.

Conceptually:

**Effective Permission = Authority ∩ Capability ∩ Policy ∩ Scope ∩ Security State**

A capability SHALL NOT expand the authority of its holder.

---

## 11. Capability and Delegated Authority

Delegated authority SHALL constrain applicable capability use.

Delegation SHALL preserve:

- issuer;
- recipient;
- purpose;
- task;
- capability scope;
- target;
- resource scope;
- execution constraints;
- policy constraints;
- time constraints;
- revocation conditions;
- provenance.

A delegated capability SHALL NOT exceed the authority granted by the delegation.

---

## 12. Capability Attenuation

Capability scope SHALL be attenuable.

A child delegation or derived capability binding SHALL NOT enlarge the authority
or capability scope of its parent context.

Capability attenuation SHALL apply across:

- agent delegation;
- task decomposition;
- inter-agent communication;
- recursive agent creation;
- tool invocation;
- application interaction;
- host interaction.

Agents SHALL NOT enlarge capability scope through reasoning, prompts, tool output,
messages, self-declaration, or capability discovery.

---

## 13. Capability Gateway

The Capability Gateway SHALL remain the authoritative execution-admission
boundary for consequential capability use.

The Capability Gateway SHALL validate applicable:

- principal;
- task;
- agent;
- delegated authority;
- capability;
- target;
- policy;
- resource limits;
- security state;
- approval state;
- revocation state;
- expiry state.

Authorization SHALL be explicit.

Requests failing applicable authorization checks SHALL NOT reach the Secure
Executor or LHICF.

---

## 14. Capability Authorization

Capability authorization SHALL determine whether a specific capability request
is permitted within its applicable context.

Authorization SHALL consider the complete applicable authorization state rather
than capability identity alone.

Authorization SHALL NOT be inferred from:

- natural language;
- model output;
- agent intent;
- tool metadata;
- frontend requests;
- voice requests;
- memory content;
- capability descriptions.

---

## 15. Capability Admission

Capability authorization SHALL precede execution admission.

Execution admission SHALL occur only after applicable capability, authority,
policy, resource, approval, security, expiry, and revocation checks succeed.

Scheduling SHALL NOT constitute capability authorization.

Agent registration SHALL NOT constitute capability authorization.

Capability discovery SHALL NOT constitute capability authorization.

---

## 16. Target Binding

Consequential capabilities SHALL be target-bound where applicable.

Target binding MAY identify:

- file;
- directory;
- process;
- service;
- network destination;
- application;
- device;
- API;
- external service;
- data object;
- host;
- environment.

A capability authorized for one target SHALL NOT automatically authorize another
target.

---

## 17. Operation Binding

Capability authorization SHALL be bound to the permitted operation.

An authorization for one operation SHALL NOT automatically authorize a different
operation merely because both belong to the same capability family.

Operation expansion SHALL require an independent authorization decision.

---

## 18. Resource Constraints

Capability use SHALL respect applicable resource limits.

Resource constraints MAY include:

- CPU;
- memory;
- storage;
- network bandwidth;
- network destinations;
- execution duration;
- process count;
- tool calls;
- token usage;
- artifact size;
- retries;
- cost;
- egress;
- agent count.

Resource limits SHALL be enforced outside model reasoning where security-critical.

---

## 19. Time Constraints

Capability authorization SHOULD be time-bounded where appropriate.

The applicable authorization state SHALL include:

- issuance time;
- validity start;
- expiry;
- applicable renewal rules;
- revocation state.

Expired capability authorization SHALL fail closed.

Persisted runtime state SHALL NOT automatically restore expired capability
authorization.

---

## 20. Revocation

Capability authorization SHALL support revocation.

Revocation SHALL be enforceable independently of model or agent cooperation.

Revocation MAY be triggered by:

- authority revocation;
- policy change;
- security event;
- emergency control;
- task cancellation;
- agent termination;
- session termination;
- credential compromise;
- capability compromise;
- host security state;
- administrative control.

Revoked authorization SHALL NOT remain executable merely because a prior
checkpoint contains it.

---

## 21. Replay Resistance

Capability authorization SHALL be protected against unauthorized replay.

Where applicable, authorization requests SHALL use:

- unique request identifiers;
- nonce or equivalent freshness controls;
- bounded validity;
- authorization-state binding;
- task binding;
- principal binding;
- capability binding;
- provenance binding.

Previously valid authorization SHALL NOT automatically authorize a new unrelated
operation.

---

## 22. Approval Requirements

Capabilities with applicable risk or policy requirements SHALL require the
appropriate approval state before execution admission.

Approval requirements SHALL distinguish between:

- automatically permitted operations;
- policy-controlled operations;
- approval-required operations;
- prohibited operations.

High-risk authorization SHALL use the approved HITL governance architecture
where required.

Approval SHALL NOT bypass capability, authority, policy, security, or execution
checks.

---

## 23. Aegis Boundary

Aegis SHALL remain independent of the capability consumer's reasoning.

Aegis provides applicable:

- governance;
- trust evaluation;
- policy enforcement;
- risk evaluation;
- denial;
- approval requirements;
- authority revocation;
- containment;
- quarantine;
- emergency controls.

Agents and models SHALL NOT modify their governing security policy.

Capability authorization SHALL remain subject to applicable Aegis decisions.

---

## 24. Secure Executor Boundary

The Secure Executor SHALL execute only operations already admitted by the
authorization architecture.

The Secure Executor SHALL NOT infer privilege from:

- model output;
- agent claims;
- natural language;
- tool metadata;
- frontend requests;
- voice requests;
- memory content.

The Secure Executor SHALL remain downstream of capability and execution
admission.

---

## 25. Sandbox Boundary

Capability execution SHALL occur within an execution isolation boundary
appropriate to its risk.

Applicable sandbox controls include:

- process isolation;
- filesystem isolation;
- network isolation;
- credential isolation;
- IPC restrictions;
- resource fencing;
- execution-time limits;
- environment isolation;
- escape resistance.

Sandbox escape SHALL be treated as a security event.

---

## 26. LHICF Boundary

Host operations SHALL pass through the controlled LYRION Host Integration &
Control Fabric where applicable.

The capability chain SHALL remain:

**Aegis  
→ Capability Gateway  
→ Secure Executor  
→ Agent Sandbox  
→ LHICF  
→ Host Adapter  
→ Host OS**

LHICF SHALL validate operation type and applicable capability scope and enforce
host-specific policy.

LHICF SHALL NOT become an alternate authorization or privileged execution path.

---

## 27. Host Capability Mapping

Host-specific capabilities SHALL be mapped through approved Host Harness and
LHICF mechanisms.

Mapping SHALL account for:

- host environment;
- operating system;
- adapter;
- concrete operation;
- capability scope;
- authorization state;
- security policy;
- verification requirements.

Unsupported host capabilities SHALL fail closed.

---

## 28. Application Capability Mapping

Application capabilities SHALL use the governed Application Harness lifecycle:

**Discovery  
→ Identification  
→ Capability Discovery  
→ Authorization  
→ Interaction  
→ Verification  
→ Provenance**

Application capability discovery SHALL NOT itself grant authorization.

Application adapters SHALL NOT bypass Aegis, Capability Gateway, Secure
Executor, Sandbox, or LHICF where those boundaries apply.

---

## 29. Universal Computer Boundary

Universal Computer operations SHALL preserve the capability and authorization
chain.

The conceptual flow is:

**Agent Intent  
→ Capability  
→ Authority  
→ Execution Admission  
→ Universal Computer Operation  
→ Host/Application Adapter  
→ Concrete Host Operation  
→ Verification  
→ Provenance**

Universal Computer SHALL NOT provide arbitrary privileged execution.

Arbitrary shell access SHALL NOT be treated as a Universal Computer
implementation.

---

## 30. Inter-Agent Capability Boundary

Inter-agent messages SHALL NOT grant capability authority by themselves.

Agent-to-agent capability delegation SHALL preserve:

- identity;
- authority;
- capability scope;
- task scope;
- provenance;
- policy constraints;
- audit context;
- revocation state.

A receiving agent SHALL obtain only the explicitly delegated capability scope.

---

## 31. Agent Swarm Boundary

Agent swarm expansion SHALL remain bounded and governed.

Where swarm capabilities are introduced, controls SHALL include:

- agent identity;
- lineage;
- bounded depth;
- bounded width;
- capability attenuation;
- resource budgets;
- namespace isolation;
- communication authorization;
- cancellation;
- emergency stop.

Unlimited recursive capability expansion SHALL NOT be permitted.

---

## 32. RLM Boundary

Recursive Language Model reasoning SHALL remain separate from capability
authorization.

RLM output SHALL remain reasoning/evidence.

RLM SHALL NOT:

- grant capabilities;
- grant authority;
- bypass Aegis;
- bypass Capability Gateway;
- bypass Secure Executor;
- bypass Sandbox;
- bypass LHICF;
- access privileged host operations directly.

RLM output SHALL NOT constitute authorization.

---

## 33. RMA / Memory Boundary

Recursive Memory Architecture SHALL remain distinct from capability authorization.

Memory content SHALL NOT automatically create capability authorization.

Capability-relevant memory SHALL remain subject to:

- provenance;
- scope;
- trust;
- validation;
- policy;
- current authorization state.

Persisted memory SHALL NOT override current capability revocation or expiry.

---

## 34. Verification

Consequential capability execution SHALL have independent verification
appropriate to its risk.

Verification SHALL establish execution outcome independently of an agent or model
claim where required.

An agent/model claim of success SHALL NOT by itself establish successful
execution.

Verification results SHALL be attributable and recorded in applicable
provenance.

---

## 35. Provenance and Audit

Capability lifecycle events SHALL generate appropriate provenance and audit
records.

Applicable provenance SHALL identify:

- initiating principal;
- task;
- agent;
- delegated authority;
- capability;
- target;
- policy;
- authorization decision;
- execution;
- host operation;
- verification;
- outcome.

Capability decisions SHALL be traceable without relying solely on model-generated
narrative.

---

## 36. Observability

Capability operations SHALL be observable according to applicable security and
operational requirements.

Observability SHOULD cover:

- capability request;
- authorization decision;
- denial;
- approval requirement;
- admission;
- execution;
- resource use;
- revocation;
- expiry;
- failure;
- verification;
- security event;
- provenance linkage.

Observability mechanisms SHALL NOT become an alternate authorization mechanism.

---

## 37. Failure and Fail-Closed Behavior

Capability authorization failures SHALL fail closed.

Examples include:

- unknown capability;
- invalid identity;
- invalid authority;
- invalid delegation;
- expired authorization;
- revoked authorization;
- invalid target;
- policy denial;
- missing approval;
- resource violation;
- invalid security state;
- unsupported host capability;
- unavailable required control;
- failed provenance binding.

Failure SHALL NOT result in automatic privilege expansion.

---

## 38. Emergency Controls

Emergency controls SHALL remain independent of model and agent reasoning.

Emergency controls MAY:

- pause execution;
- revoke capability authorization;
- quarantine agents;
- isolate execution;
- disconnect resources;
- terminate execution;
- prevent further capability admission.

Agents SHALL NOT modify, disable, or bypass emergency controls.

---

## 39. Recovery and Revalidation

Recovery SHALL revalidate applicable:

- principal;
- agent identity;
- task;
- delegated authority;
- capability;
- target;
- policy;
- resource state;
- security state;
- approval state;
- revocation state;
- expiry state.

A persisted capability authorization SHALL NOT be restored merely because a
checkpoint contains it.

Recovery SHALL fail closed when required authorization state cannot be
revalidated.

---

## 40. Capability Security Invariants

The following invariants are mandatory:

1. Capability SHALL NOT imply unlimited authority.
2. Capability discovery SHALL NOT grant authority.
3. Capability description SHALL NOT grant authority.
4. Capability binding SHALL NOT bypass authorization.
5. Delegation SHALL NOT expand capability scope.
6. Child capability scope SHALL NOT exceed parent authority.
7. Capability authorization SHALL be explicit.
8. Capability Gateway SHALL remain the execution-admission boundary.
9. Secure Executor SHALL execute only authorized operations.
10. Sandbox SHALL remain an execution isolation boundary.
11. LHICF SHALL remain the controlled host boundary.
12. Unsupported host capabilities SHALL fail closed.
13. No alternate privileged path SHALL exist.
14. Expired authorization SHALL NOT be executable.
15. Revoked authorization SHALL NOT be restored by recovery.
16. Model output SHALL NOT constitute capability authorization.
17. Agent intent SHALL NOT constitute capability authorization.
18. Memory SHALL NOT automatically constitute capability authorization.
19. Inter-agent messages SHALL NOT grant capability authority.
20. Consequential execution SHALL receive independent verification appropriate
    to risk.

---

## 41. Validation Requirements

Validation SHALL include, as applicable:

- capability definition validation;
- capability identity uniqueness;
- capability scope validation;
- authority/capability intersection tests;
- target binding tests;
- task binding tests;
- policy enforcement tests;
- resource-limit tests;
- approval tests;
- expiration tests;
- revocation tests;
- replay tests;
- negative authorization tests;
- Capability Gateway bypass tests;
- Secure Executor privilege-inference tests;
- sandbox isolation tests;
- LHICF boundary tests;
- unsupported capability fail-closed tests;
- Universal Computer boundary tests;
- inter-agent capability tests;
- recovery revalidation tests;
- emergency-control tests;
- provenance tests;
- independent verification tests;
- adversarial capability-escalation tests.

Testing SHALL include negative-path and adversarial scenarios.

---

## 42. Security Testing

Capability security testing SHALL align with the approved Phase-B Security
Testing Specification.

Testing SHALL cover attempted:

- capability escalation;
- authority expansion;
- target substitution;
- task substitution;
- policy bypass;
- approval bypass;
- revocation bypass;
- expiry bypass;
- replay;
- impersonation;
- Gateway bypass;
- Secure Executor misuse;
- Sandbox escape;
- LHICF bypass;
- host capability substitution;
- cross-task capability leakage;
- cross-session capability leakage;
- cross-tenant capability leakage;
- inter-agent capability abuse.

Real-infrastructure validation SHALL be performed where applicable before
production acceptance.

---

## 43. Cross-Document Dependencies

This specification depends on and integrates with:

- Core Requirements PRD;
- Core Architecture;
- Phase-B Security Architecture;
- Threat Model;
- Agent Identity and Authority Specification;
- Agent Runtime Specification;
- Agent Harness;
- Host Harness;
- Universal Computer;
- Application Harness;
- Aegis;
- Secure Execution;
- Sandbox;
- LHICF;
- Memory/RMA;
- RLM;
- Observability and Provenance;
- Recovery/Resilience;
- Validation;
- Security Testing;
- Operations.

No dependency in this list is assumed to be implementation-complete merely
because this document exists.

---

## 44. Governance Boundary

This document is an architectural/specification baseline.

It does not authorize implementation.

It does not authorize privileged execution.

It does not constitute production acceptance.

Architecture Approval remains PENDING.

Implementation Authorization remains NOT AUTHORIZED.

Production Implementation remains BLOCKED.

Production Certification remains NOT CLAIMED.

Capability behavior SHALL remain subject to the approved authority, security,
execution, validation, and governance architecture.

---

## 45. Acceptance Criteria

PB-DOC-004 SHALL be considered structurally acceptable only when:

- metadata is complete;
- capability definitions are explicit;
- capability/authority separation is preserved;
- capability scope is defined;
- capability binding is defined;
- Capability Gateway boundary is explicit;
- execution admission is defined;
- Secure Executor boundary is preserved;
- Sandbox boundary is preserved;
- LHICF boundary is preserved;
- Universal Computer boundary is preserved;
- unsupported capabilities fail closed;
- revocation and expiry are defined;
- recovery revalidation is defined;
- independent verification is defined;
- provenance requirements are defined;
- security invariants are present;
- validation requirements are present;
- governance status remains accurate;
- persistent documentation validation passes.

---

## 46. Semantic Reconciliation

PB-DOC-004 SHALL be reconciled against:

- CORE-EXEC-001 through CORE-EXEC-006;
- Core Architecture capability and execution sections;
- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Agent Identity and Authority Specification;
- Secure Execution boundaries;
- Universal Computer architecture;
- Host Harness;
- Application Harness;
- Aegis governance;
- Memory/RMA;
- RLM;
- validation and security-testing specifications.

Semantic reconciliation SHALL identify contradictions before formal architecture
approval.

---

## 47. Implementation Boundary

Implementation SHALL NOT begin solely because PB-DOC-004 passes structural
validation.

Implementation authorization requires the broader Phase-B governance sequence,
including architecture, security, threat-model, interface, validation, and
approval closure.

Capability implementation SHALL preserve the documented execution chain.

No implementation SHALL introduce an alternate privileged capability path.

---

## 48. Acceptance State

Current acceptance state:

- Structural Validation: PENDING
- Semantic Reconciliation: PENDING
- Architecture Approval: PENDING
- Implementation Authorization: NOT AUTHORIZED
- Production Implementation: BLOCKED
- Production Certification: NOT CLAIMED

These states SHALL be updated only when corresponding evidence and governance
approval exist.

---

## 49. Final Capability Authority Invariant

The authoritative invariant is:

**A capability identifies a bounded operation; authority determines whether the
principal may use it; policy and security controls determine whether the
operation may be admitted; the Secure Executor performs only an already-authorized
operation; the Sandbox and LHICF constrain execution; and independent verification
determines the resulting outcome.**

Therefore:

**Capability ≠ Authority ≠ Authorization ≠ Execution ≠ Verification**

No model, agent, tool, memory object, message, frontend request, voice request,
capability description, or external protocol SHALL create an alternate path
around this invariant.

---

**End of PB-DOC-004 — Capability Model Specification v1.0.0**

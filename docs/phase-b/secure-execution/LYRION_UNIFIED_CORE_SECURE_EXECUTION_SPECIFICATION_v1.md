# LYRION Unified Core — Secure Execution Specification

**Document ID:** TAOS-CORE-SECURE-EXECUTION-001  
**Version:** 1.0.0  
**Date:** 2026-09-23  
**Status:** DRAFT — SECURE EXECUTION BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Secure Execution boundary of the LYRION Unified Core.

The Secure Executor SHALL execute only operations that have already passed the applicable authorization and execution-admission controls.

The Secure Executor SHALL NOT become an alternate authorization authority.

---

## 2. Scope

This specification covers:

- Secure Executor responsibilities;
- execution lifecycle;
- execution-request integrity;
- resource enforcement;
- process lifecycle;
- timeout and cancellation;
- execution result handling;
- execution metadata;
- provenance;
- sandbox integration;
- LHICF integration;
- fail-closed behavior;
- failure handling;
- recovery interaction;
- idempotency and replay protection where applicable;
- observability;
- security testing requirements.

It does not replace Aegis, Capability Authorization, Execution Admission, Agent Sandbox, LHICF, Universal Computer, Host Harness, Application Harness, verification, or recovery specifications.

---

## 3. Terminology

**Secure Executor:** The controlled runtime component that executes an already-authorized and admitted operation.

**Execution Request:** The structured request presented to the Secure Executor after applicable authorization and execution-admission controls.

**Execution Admission:** The upstream decision determining whether an operation may enter the controlled execution path.

**Execution Backend:** A registered execution implementation capable of performing a bounded operation.

**Agent Sandbox:** The runtime isolation boundary within which applicable agent execution occurs.

**LHICF:** LYRION Host Integration & Control Fabric, providing controlled mediation between LYRION and the host environment.

**Execution Instance:** A uniquely attributable runtime instance of an execution request.

---

## 4. Architectural Position

The Secure Executor belongs to the Execution Plane.

The Secure Executor SHALL operate downstream of authorization and execution admission.

The canonical relationship is:

**Aegis → Capability Gateway → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host**

The Secure Executor SHALL NOT bypass Aegis, Capability Gateway, Execution Admission, Agent Sandbox, LHICF, applicable HITL controls, or independent verification.

---

## 5. Secure Executor Authority Boundary

The Secure Executor SHALL NOT create, enlarge, infer, or delegate authority.

The Secure Executor SHALL consume the authority, capability, policy, resource, target, and execution constraints already established by upstream governance components.

Execution SHALL be denied when required admission context is missing, invalid, expired, revoked, inconsistent, or unverifiable.

---

## 6. Independence from Model Reasoning

The Secure Executor SHALL NOT trust raw model-generated commands as authorization.

Model output SHALL be treated as untrusted input unless transformed into a governed operation through the applicable LYRION control chain.

A model SHALL NOT directly invoke a privileged execution backend.

---

## 7. Execution Request Model

An execution request SHOULD contain, as applicable:

- execution identity;
- principal identity;
- agent identity;
- task identity;
- delegation context;
- capability identity;
- authorization decision;
- execution-admission decision;
- target;
- operation;
- scope;
- policy context;
- resource constraints;
- sandbox binding;
- timeout;
- cancellation context;
- idempotency information;
- provenance context;
- verification requirements.

Missing mandatory context SHALL result in fail-closed handling.

---

## 8. Execution Request Integrity

The Secure Executor SHALL verify that the execution request remains internally consistent.

The request presented for execution SHALL correspond to the operation that was authorized and admitted.

The Secure Executor SHALL reject requests whose identity, authority, capability, target, operation, scope, policy, resource, or admission context has been altered or cannot be established.

---

## 9. Authorization Non-Expansion

Execution SHALL NOT expand delegated authority.

The Secure Executor SHALL NOT interpret possession of a capability as unlimited authority.

The executor SHALL NOT convert an execution request into a broader capability.

Child execution context SHALL NOT exceed the applicable parent/task authority.

---

## 10. Execution Admission Dependency

The Secure Executor SHALL accept execution only after the applicable Execution Admission boundary has completed successfully.

The executor SHALL NOT replace Execution Admission with local heuristic authorization.

Execution Admission SHALL remain the authoritative upstream execution-entry decision.

---

## 11. Capability Boundary

The Secure Executor SHALL execute only operations associated with an authorized capability.

Capability authorization SHALL remain outside the executor's authority boundary.

The executor SHALL not dynamically create unrestricted capabilities.

---

## 12. Backend Registry

Execution backends SHALL be explicitly registered and identifiable.

A backend reference SHALL identify an approved execution implementation.

Backend identifiers SHALL NOT be interpreted as arbitrary executable code, module paths, shell strings, or unrestricted dynamic imports.

Unregistered or unavailable backends SHALL fail closed.

---

## 13. Backend Capability Ceiling

Each execution backend SHALL operate within its registered capability boundary.

A backend SHALL NOT acquire authority beyond the capability and execution context supplied to it.

Backend behavior SHALL remain subject to applicable sandbox, resource, host, and policy constraints.

---

## 14. Execution Lifecycle

The Secure Executor lifecycle SHALL support, as applicable:

1. request receipt;
2. request integrity verification;
3. admission-state verification;
4. execution-context binding;
5. sandbox binding;
6. resource binding;
7. backend selection;
8. execution start;
9. execution monitoring;
10. completion, cancellation, timeout, or failure;
11. result capture;
12. provenance recording;
13. independent verification handoff.

Lifecycle transitions SHALL be attributable and observable.

---

## 15. Process Lifecycle Control

The Secure Executor SHALL control the lifecycle of execution processes or equivalent runtime units within its responsibility.

Lifecycle handling SHALL include applicable:

- start;
- running;
- completion;
- cancellation;
- timeout;
- failure;
- termination;
- cleanup.

A failed lifecycle transition SHALL NOT silently become successful execution.

---

## 16. Resource Constraints

Execution SHALL operate within applicable resource constraints.

Resource controls MAY include:

- CPU;
- memory;
- storage;
- process count;
- execution duration;
- network usage;
- artifact size;
- tool calls;
- retries;
- egress;
- task-specific execution budgets.

Security-critical limits SHALL NOT depend solely on model instructions.

---

## 17. Resource Exhaustion

Resource exhaustion SHALL be treated as an execution failure or controlled termination condition.

The Secure Executor SHALL prevent an execution from exceeding applicable enforced limits.

Resource violations SHALL NOT result in successful completion being reported.

---

## 18. Timeout Handling

Execution SHALL support bounded timeout handling where a timeout is applicable.

When an execution exceeds its permitted duration, the executor SHALL transition it into the applicable timeout or termination state.

Timeout handling SHALL produce attributable execution evidence.

---

## 19. Cancellation

The Secure Executor SHALL support authorized cancellation.

Cancellation SHALL be distinguishable from successful completion.

Cancellation SHALL propagate to applicable execution resources and SHALL trigger appropriate cleanup.

A cancelled execution SHALL NOT be represented as successfully completed.

---

## 20. Agent Sandbox Boundary

Applicable agent execution SHALL occur within an explicit sandbox boundary.

Sandbox controls MAY include:

- filesystem restrictions;
- process restrictions;
- network restrictions;
- environment isolation;
- credential isolation;
- IPC restrictions;
- resource limits;
- execution-time limits.

Sandbox configuration SHALL NOT become an alternate authorization mechanism.

---

## 21. Sandbox Escape Handling

Sandbox escape or suspected escape SHALL be treated as a security event.

The execution SHALL be contained according to applicable security controls.

The event SHALL be recorded with sufficient provenance and evidence for investigation.

---

## 22. Credential Isolation

Credentials SHALL NOT be exposed to execution contexts beyond their authorized scope.

The Secure Executor SHALL NOT make unrestricted host credentials available to an operation.

Credential access SHALL remain governed by applicable identity, capability, policy, sandbox, and host controls.

---

## 23. Network Isolation

Network access SHALL remain bounded by applicable capability, policy, sandbox, resource, and host controls.

The Secure Executor SHALL NOT assume that execution implies unrestricted network access.

Unauthorized or unsupported network operations SHALL fail closed.

---

## 24. Filesystem and Process Isolation

Filesystem and process access SHALL remain bounded by the applicable execution and sandbox context.

The Secure Executor SHALL NOT provide unrestricted host filesystem or process access.

Host-specific mediation SHALL remain the responsibility of the applicable LHICF and host-adapter architecture.

---

## 25. LHICF Boundary

LHICF SHALL remain the controlled boundary between LYRION and the host environment.

The Secure Executor SHALL interact with host resources through the approved execution architecture.

The canonical relationship remains:

**Secure Executor → Agent Sandbox → LHICF → Host Adapter → Host**

The executor SHALL NOT bypass LHICF for governed host operations.

---

## 26. Host Adapter Boundary

Host adapters SHALL provide narrowly defined host mediation.

An adapter SHALL NOT automatically inherit another adapter's authority.

The Secure Executor SHALL not use adapter selection to enlarge authorization.

Unsupported host operations SHALL fail closed.

---

## 27. Universal Computer Boundary

Universal Computer operations SHALL remain governed operations.

The Secure Executor SHALL execute only the concrete operation that has passed the applicable authorization and execution-admission path.

Universal Computer SHALL NOT create an alternate privileged execution path.

The canonical relationship remains:

**Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Host Operation → Verification → Provenance**

---

## 28. Application Harness Boundary

Application Harness operations SHALL remain governed by the applicable identity, capability, authorization, execution-admission, host-mediation, and verification controls.

The Secure Executor SHALL NOT treat application discovery or application capability discovery as authorization.

Application adapters SHALL NOT bypass the Secure Executor where the governed execution architecture requires it.

---

## 29. HITL Boundary

Operations requiring human authorization SHALL NOT execute before the applicable approval has been successfully verified.

HITL approval SHALL NOT create an alternate execution path.

The Secure Executor SHALL consume the resulting governed execution context rather than independently interpreting human approval.

---

## 30. Aegis Boundary

Aegis SHALL remain the independent governance, security, trust, policy, risk, and containment authority.

The Secure Executor SHALL NOT override Aegis decisions.

Aegis SHALL remain upstream of execution admission and execution.

The executor SHALL not modify governing security policy.

---

## 31. Failure and Fail-Closed Behavior

The Secure Executor SHALL fail closed when required execution conditions cannot be established.

Failure conditions include, as applicable:

- invalid execution request;
- invalid admission state;
- missing capability;
- inconsistent authority;
- expired authority;
- revoked authority;
- unavailable policy;
- invalid sandbox binding;
- unavailable backend;
- invalid target;
- exceeded resource limit;
- timeout;
- cancellation;
- security violation;
- integrity failure.

Failure SHALL NOT silently expand privilege.

---

## 32. Execution Results

Execution results SHALL distinguish at least the applicable outcome state, such as:

- successful completion;
- rejected execution;
- cancelled execution;
- timeout;
- execution failure;
- security termination;
- resource termination;
- unavailable backend.

A result SHALL NOT be treated as verified success merely because the executor completed a process.

---

## 33. Independent Verification

Execution completion SHALL remain distinct from successful real-world outcome.

Consequential operations SHALL undergo independent verification where required.

Verification SHALL be capable of producing explicit outcomes such as:

**ACCEPT / REJECT / RETRY / ROLLBACK / ESCALATE / TERMINATE**

The Secure Executor SHALL NOT declare independent verification success on behalf of the verifier.

---

## 34. Provenance and Audit

Security-sensitive execution SHALL produce attributable provenance and audit records where supported by the persistence architecture.

Provenance SHALL preserve the applicable causal relationship:

**Human → Task → Agent → Delegation → Capability → Execution Admission → Execution → Host Action → Verification → Outcome**

Execution metadata SHOULD include:

- execution identity;
- principal;
- agent;
- task;
- capability;
- backend;
- target;
- timestamps;
- lifecycle state;
- resource state;
- result;
- failure state;
- verification state;
- provenance references.

---

## 35. Observability

Secure Execution SHALL integrate with the approved observability architecture.

Observable events SHOULD include:

- execution admission received;
- execution started;
- backend selected;
- sandbox bound;
- resource limits applied;
- timeout;
- cancellation;
- failure;
- security violation;
- termination;
- result;
- verification handoff.

Observability SHALL NOT create an alternate execution authority.

---

## 36. Replay and Idempotency

Execution requests with consequential external effects SHALL use applicable replay resistance and idempotency controls.

Where an idempotency key or equivalent execution identity is required, repeated requests SHALL be handled according to the approved execution contract.

Idempotency SHALL NOT be interpreted as authorization.

---

## 37. Recovery and Revalidation

Recovery SHALL NOT restore execution authority merely because a checkpoint contains a previously valid execution context.

Before consequential continuation, applicable:

- identity;
- task;
- policy;
- delegated authority;
- capability;
- execution admission;
- resource;
- sandbox;
- security state

SHALL be revalidated.

Expired or revoked authority SHALL remain invalid.

---

## 38. Emergency Controls

Emergency controls SHALL remain independent of model and agent authority.

Applicable controls MAY include:

- pause;
- revoke;
- quarantine;
- isolate;
- disconnect;
- terminate.

The Secure Executor SHALL respect applicable emergency controls.

An executing agent SHALL NOT disable or modify its own emergency controls.

---

## 39. Security Invariants

The following invariants SHALL remain authoritative:

1. Secure Executor does not grant authorization.
2. Secure Executor does not enlarge authority.
3. Raw model output is not execution authorization.
4. Execution Admission remains upstream of execution.
5. Unregistered backends fail closed.
6. Backend identifiers are not arbitrary executable code.
7. Resource controls are externally enforced.
8. Sandbox controls remain distinct from authorization.
9. LHICF remains the controlled host boundary.
10. Host adapters do not inherit authority automatically.
11. Timeout and cancellation are terminal execution states unless explicitly recovered through governed recovery.
12. Security violations fail closed.
13. Verification remains independent of execution.
14. Provenance remains causal and attributable.
15. Recovery revalidates authority and security state.
16. No alternate privileged execution path is permitted.

---

## 40. Validation Requirements

Secure Execution SHALL be validated through the applicable validation hierarchy:

1. static validation;
2. unit validation;
3. integration validation;
4. adversarial validation;
5. real-infrastructure validation;
6. operational exercises;
7. independent assurance where applicable;
8. scoped security acceptance.

Validation SHALL include both positive and negative execution paths.

---

## 41. Security Testing Requirements

Security testing SHALL cover, as applicable:

- raw model-command rejection;
- backend allowlisting;
- capability-boundary enforcement;
- authorization non-expansion;
- admission-state integrity;
- expired authority;
- revoked authority;
- replay;
- duplicate execution;
- resource exhaustion;
- timeout;
- cancellation;
- credential exposure;
- filesystem escape;
- process escape;
- network escape;
- IPC escape;
- sandbox escape;
- LHICF bypass;
- host-adapter bypass;
- Universal Computer bypass;
- Application Harness bypass;
- emergency-control enforcement;
- recovery with stale authority;
- provenance integrity.

Security testing SHALL include adversarial attempts to bypass the execution chain.

---

## 42. Cross-Document Dependencies

This specification depends on and SHALL remain consistent with:

- LYRION Unified Core Architecture;
- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Core Requirements PRD;
- Agent Identity & Authority Specification;
- Capability Model Specification;
- Agent Harness Specification;
- Host Harness Specification;
- Universal Computer Specification;
- Application Harness Specification;
- Execution Admission Specification;
- Aegis Governance Specification;
- Data Architecture;
- Memory / Provenance Specification;
- Observability Specification;
- Validation Specification;
- Security Testing Specification;
- Operations Specification;
- Recovery / Resilience Specification;
- Phase-B Master Manifest.

No semantic conflict SHALL be silently resolved by weakening an existing security boundary.

### Core Traceability References

PB-DOC-011 participates in the following canonical Core traceability requirements:

- **TR-001 — Inter-Agent Message Integrity:** Secure Execution SHALL preserve attributable, integrity-protected, scoped execution context and replay-resistant execution handling where inter-agent execution requests are applicable. Execution SHALL NOT derive authority from message content.
- **TR-002 — RLM Isolation:** Secure Execution SHALL NOT provide an execution path that bypasses governed RLM isolation or permits RLM reasoning to obtain unauthorized execution capability.
- **TR-003 — Memory Lifecycle:** Execution results, provenance and related evidence SHALL integrate with the governed memory lifecycle and SHALL remain subject to applicable provenance, scope, trust, integrity, retention and audit controls.
- **TR-004 — Memory Data Integrity:** Execution-generated persistent state or evidence SHALL remain subject to the approved Data Architecture consistency, backup, restore, migration and corruption-recovery requirements.
- **TR-005 — Supply-Chain Admission:** Secure execution backends and applicable adapters SHALL remain subject to evidence-based supply-chain admission and SHALL NOT gain privileged authority merely through integration.
- **TR-006 — Agent Swarm Governance:** If swarm execution is introduced, Secure Execution SHALL preserve applicable swarm identity, lineage, bounded depth/width, capability attenuation, resource budgets, namespace isolation, communication authorization, cancellation and emergency-control boundaries. Swarm remains deferred Agentic Expansion.
- **TR-007 — Observability Specification:** Secure Execution SHALL provide the execution lifecycle, verification, provenance, audit and security telemetry required by the governed Observability Specification.
- **TR-008 — Core Validation Specification:** Secure Execution SHALL be validated through the applicable requirements and evidence controls defined by the Core Validation Specification.
- **TR-009 — Security Testing Specification:** Secure Execution SHALL remain subject to the applicable security-testing requirements, including authorization-boundary, isolation, bypass, replay, resource, recovery, emergency-control and adversarial testing.

These references establish traceability relationships only. They SHALL NOT be interpreted as granting implementation authorization, architecture approval or production certification.

---

## 43. Governance Boundary

This document defines the Secure Execution documentation and architecture baseline.

It does not grant implementation authorization.

Implementation SHALL begin only after the applicable Phase-B architecture approval and implementation authorization gates have been formally satisfied.

---

## 44. Semantic Reconciliation

The Secure Execution architecture SHALL preserve the following distinctions:

**Authority ≠ Capability ≠ Authorization ≠ Execution Admission ≠ Execution ≠ Verification**

The Secure Executor SHALL remain an execution component, not a governance component.

No implementation detail SHALL be interpreted as authorization unless explicitly established by the governing authorization architecture.

---

## 45. Change Control

Changes to Secure Execution SHALL preserve compatibility with the approved Phase-B architecture and security model.

Security-boundary changes SHALL require appropriate architecture and security review.

Changes SHALL preserve:

- provenance;
- traceability;
- validation evidence;
- version history;
- security invariants;
- failure semantics.

---

## 46. Acceptance Criteria

PB-DOC-011 SHALL be considered documentation-baseline validated only when:

- required metadata is present;
- required sections are present;
- Secure Executor responsibilities are defined;
- execution-admission dependency is explicit;
- authorization non-expansion is explicit;
- sandbox boundaries are defined;
- LHICF boundaries are defined;
- fail-closed behavior is defined;
- timeout and cancellation are defined;
- resource controls are defined;
- provenance and observability are defined;
- recovery/revalidation is defined;
- security testing requirements are defined;
- cross-document dependencies are recorded;
- semantic reconciliation is complete;
- implementation remains unauthorized;
- production certification remains unclaimed;
- authoritative validation passes.

---

## 47. Final Secure Execution Invariant

The following invariant SHALL remain authoritative:

**Authorization ≠ Execution Admission ≠ Secure Execution ≠ Verification**

And:

**Secure Executor SHALL NOT create authority.**

The canonical governed execution relationship remains:

**Human Intent → Authenticated Principal → Lyri Interpretation → Task → Agent Delegation → Delegated Authority → Aegis → Capability Authorization → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host/Application/Device → Independent Verification → Memory/Audit/Provenance → Lyri → Human**

No alternate privileged execution path SHALL be introduced.

---

## 48. Documentation Status

**Structural Validation:** PENDING  
**Semantic Reconciliation:** PENDING  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

This document is a Phase-B documentation and architecture baseline only.

---

## 49. Governance and Approval

PB-DOC-011 requires formal review under the Phase-B governance process.

Approval SHALL consider:

- architecture consistency;
- security-boundary completeness;
- requirements traceability;
- validation coverage;
- operational implications;
- recovery implications;
- implementation feasibility;
- unresolved risks and documented assumptions.

No approval SHALL be inferred from document creation or structural validation alone.

**End of LYRION Unified Core — Secure Execution Specification v1.0.0**

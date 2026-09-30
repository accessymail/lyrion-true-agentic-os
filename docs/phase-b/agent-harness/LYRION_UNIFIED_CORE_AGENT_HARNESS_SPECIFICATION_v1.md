# LYRION Unified Core — Agent Harness Specification

**Document ID:** TAOS-CORE-AGENT-HARNESS-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Project:** LYRION True Agentic OS  
**Status:** DRAFT — AGENT HARNESS BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Agent Harness baseline for the LYRION Unified Core.

The Agent Harness provides the controlled runtime boundary for agents and establishes the contracts required for agent identity, lifecycle, task execution, capability binding, authority validation, tool invocation, runtime isolation, resource enforcement, audit integration, failure handling, and recovery.

The Agent Harness SHALL operate within the approved LYRION True Agentic OS security and execution architecture.

---

## 2. Scope

This specification covers:

- agent runtime boundary;
- agent registration;
- agent identity;
- agent lifecycle;
- task binding;
- capability binding;
- authority validation;
- tool invocation;
- runtime isolation;
- resource enforcement;
- inter-agent interaction;
- audit and provenance;
- failure handling;
- recovery;
- termination;
- security boundaries;
- execution boundaries;
- validation requirements.

This specification does not authorize implementation or production operation.

---

## 3. Source Hierarchy

The Agent Harness SHALL remain subordinate to the applicable approved and validated LYRION architecture and governance documents.

Relevant sources include:

1. LYRION Unified Core Requirements PRD;
2. LYRION Unified Core Architecture;
3. Phase-B Architecture Baseline;
4. Phase-B Security Architecture;
5. Agentic Runtime Specification;
6. Agent Identity and Authority Specification;
7. Capability Model Specification;
8. Validation Specification;
9. Security Testing Specification;
10. Recovery and Resilience Specification;
11. Phase-B governance and approval documents.

The governing architectural principle remains:

**PRESERVE → EXTEND → INTEGRATE → VALIDATE → REDESIGN ONLY WHEN REQUIRED**

---

## 4. Architectural Principles

The Agent Harness SHALL preserve:

- explicit agent identity;
- explicit lifecycle state;
- least privilege;
- capability-bound operation;
- delegated authority constraints;
- runtime isolation;
- resource limits;
- fail-closed behavior;
- auditability;
- provenance;
- independent security enforcement;
- controlled execution;
- recovery revalidation.

The Agent Harness SHALL NOT create an alternate privileged execution path.

---

## 5. Agent Harness Definition

The Agent Harness is the controlled runtime boundary for an agent.

It SHALL provide the runtime mechanisms required to:

- register an agent;
- establish agent identity;
- manage agent lifecycle;
- bind tasks;
- bind applicable capabilities;
- validate applicable authority;
- mediate tool invocation;
- enforce runtime constraints;
- enforce applicable resource limits;
- isolate the runtime;
- integrate audit and provenance;
- coordinate failure handling;
- support governed recovery.

The Agent Harness SHALL NOT itself become an independent security authority.

---

## 6. Agent Control Plane Relationship

The Agent Control Plane SHALL govern agent lifecycle and runtime mechanics including:

- registration;
- discovery;
- routing;
- scheduling;
- supervision;
- state;
- communication;
- resource management;
- recovery;
- termination;
- audit integration.

The Agent Harness SHALL provide the controlled runtime boundary in which the agent operates.

The Agent Control Plane and Agent Harness SHALL remain separate concerns.

ACP control functions SHALL NOT be interpreted as execution authorization.

---

## 7. Agent Identity

Every agent SHALL have an explicit identity.

Agent identity SHALL remain distinct from:

- human principal;
- Lyri;
- session;
- task;
- model;
- model provider;
- tool;
- external service.

Agent identity SHALL NOT be inferred solely from model output, prompts, tool output, memory, messages, or self-declaration.

---

## 8. Agent Registration

Agent registration SHALL be controlled.

Registration SHALL establish or associate applicable:

- agent identifier;
- agent type;
- lifecycle state;
- runtime context;
- applicable policy;
- provenance context;
- authority context;
- capability bindings.

Registration SHALL NOT itself grant execution authority.

Unauthorized registration SHALL fail closed.

---

## 9. Agent Lifecycle

The Agent Harness SHALL support governed lifecycle states as applicable.

Lifecycle operations SHALL include:

- creation;
- initialization;
- activation;
- suspension;
- resumption;
- termination;
- recovery.

Lifecycle transitions SHALL be attributable and auditable.

Lifecycle state SHALL NOT independently grant authority.

---

## 10. Lifecycle Transition Control

Lifecycle transitions SHALL be explicitly controlled.

Transitions SHALL verify applicable:

- identity;
- current lifecycle state;
- task state;
- authority state;
- capability state;
- policy state;
- security state;
- resource state.

Invalid or unauthorized transitions SHALL be rejected.

---

## 11. Task Binding

Agent execution SHALL occur within an applicable task context.

Task binding SHALL preserve:

- task identity;
- parent task where applicable;
- task scope;
- requesting principal;
- agent identity;
- delegated authority;
- capability scope;
- policy context;
- provenance context.

An agent SHALL NOT use task context to enlarge its authority.

---

## 12. Task Execution Boundary

The Agent Harness SHALL coordinate agent task execution but SHALL NOT independently authorize privileged execution.

Task execution SHALL remain subject to:

- identity;
- authority;
- capability;
- policy;
- resource;
- security;
- approval;
- execution-admission controls.

Task scheduling SHALL NOT constitute execution authorization.

---

## 13. Capability Binding

Capabilities SHALL be explicitly bound to applicable agent and task contexts.

Capability binding SHALL preserve applicable:

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
- provenance.

Capability binding SHALL NOT bypass independent authorization.

---

## 14. Authority Validation

The Agent Harness SHALL validate applicable authority before allowing an agent operation to proceed toward an authorization boundary.

Authority validation SHALL consider:

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
- security state.

The Agent Harness SHALL NOT infer authority from agent intent or model output.

---

## 15. Least Privilege

Agent runtime authority SHALL follow least privilege.

Authority SHALL be:

- task-bound;
- agent-bound;
- capability-scoped;
- target-bound where applicable;
- time-bounded where applicable;
- policy-bound;
- revocable;
- auditable;
- replay-resistant where applicable.

Privileged operations SHALL default to deny unless explicitly authorized.

---

## 16. Delegated Authority

The Agent Harness SHALL preserve delegated authority constraints.

Delegated authority SHALL include applicable:

- issuer;
- recipient;
- purpose;
- task;
- capability scope;
- resource scope;
- target scope;
- time constraints;
- execution constraints;
- policy constraints;
- revocation conditions;
- provenance context.

Delegation SHALL NOT itself authorize execution.

---

## 17. Authority Attenuation

Delegated authority SHALL be attenuated.

A child or derived agent context SHALL NOT enlarge authority through:

- reasoning;
- prompting;
- tool output;
- self-declaration;
- messages;
- capability discovery;
- task decomposition;
- recursive agent creation.

Child authority SHALL NOT exceed valid parent authority or applicable task authority.

---

## 18. Tool Invocation

Tool invocation SHALL occur through controlled interfaces.

The Agent Harness SHALL preserve:

- agent identity;
- task identity;
- capability context;
- authority context;
- policy context;
- provenance;
- resource constraints.

Tool metadata SHALL NOT independently grant authority.

Raw model-generated commands SHALL NOT be treated as trusted execution instructions.

---

## 19. Tool and External-Service Boundary

External tools and services SHALL be treated as bounded dependencies.

The Agent Harness SHALL NOT allow external tool responses to:

- modify authority;
- bypass policy;
- bypass Aegis;
- bypass Capability Gateway;
- bypass Secure Executor;
- bypass Sandbox;
- bypass LHICF;
- create unrestricted host access.

Tool output SHALL remain untrusted data unless independently validated.

---

## 20. Runtime Isolation

Agent execution SHALL occur within an explicit runtime boundary.

Isolation SHALL be risk-appropriate and SHALL address applicable:

- filesystem access;
- process access;
- network access;
- environment;
- credentials;
- IPC;
- resources;
- execution time;
- runtime state.

The Agent Harness SHALL NOT provide unrestricted host access.

---

## 21. Resource Enforcement

The Agent Harness SHALL operate under applicable resource constraints.

Resources MAY include:

- CPU;
- memory;
- storage;
- network;
- execution time;
- tool calls;
- model tokens;
- retries;
- agent count;
- swarm depth;
- artifact size;
- egress;
- cost.

Security-critical limits SHALL NOT depend solely on model instructions.

Resource exhaustion SHALL fail safely and shall not become an authority escalation mechanism.

---

## 22. Inter-Agent Communication

Inter-agent communication SHALL preserve:

- authenticated identity;
- attribution;
- authorization;
- integrity;
- scope;
- provenance;
- replay resistance;
- impersonation resistance;
- task isolation;
- session isolation;
- tenant isolation where applicable.

Inter-agent messages SHALL NOT implicitly grant authority.

---

## 23. Agent-to-Agent Delegation

Agent-to-agent delegation SHALL preserve:

- identity;
- authority;
- capability scope;
- task scope;
- provenance;
- policy constraints;
- audit context.

Delegating a task SHALL NOT implicitly transfer unrestricted authority.

Child authority SHALL remain bounded by applicable parent authority and task authority.

---

## 24. Agent Swarm Boundary

Governed swarm execution SHALL be treated as Agentic Expansion rather than a prerequisite for the foundational Core.

Where swarm capability is introduced, the Agent Harness SHALL support applicable controls for:

- agent identity;
- lineage;
- bounded depth;
- bounded width;
- capability attenuation;
- resource budgets;
- namespace isolation;
- communication authorization;
- cancellation;
- termination;
- emergency stop.

Unlimited recursive agent spawning SHALL NOT be permitted.

---

## 25. Agent Control Plane Boundary

The Agent Harness SHALL integrate with the Agent Control Plane for applicable:

- registration;
- lifecycle;
- routing;
- scheduling;
- supervision;
- state;
- communication;
- resources;
- recovery;
- termination;
- audit.

The Agent Control Plane SHALL NOT become an independent security authority.

The Agent Harness SHALL NOT treat ACP scheduling, routing, registration, or discovery as authorization.

---

## 26. Aegis Boundary

Aegis SHALL remain the independent governance, policy, trust, risk, and containment authority.

The Agent Harness SHALL NOT:

- replace Aegis;
- override Aegis decisions;
- modify Aegis policy;
- disable Aegis;
- bypass Aegis;
- create an alternative governance path.

---

## 27. Capability Gateway Boundary

Consequential capability use SHALL pass through the authoritative Capability Gateway / execution-admission boundary.

The Agent Harness SHALL NOT directly grant execution authorization.

Requests failing applicable authorization checks SHALL NOT proceed to Secure Executor or LHICF.

---

## 28. Secure Execution Boundary

The Agent Harness SHALL NOT directly execute privileged host operations.

The canonical execution chain SHALL remain:

**Agent → Delegated Authority → Aegis → Capability Authorization → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host**

The Secure Executor SHALL execute only operations already admitted through the applicable authorization boundary.

---

## 29. Universal Computer Boundary

The Agent Harness SHALL interact with Universal Computer / host abstractions only through defined capability and execution interfaces.

The Agent Harness SHALL NOT directly translate agent intent into unrestricted host commands.

The conceptual boundary remains:

**Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Operation → Verification**

Unsupported operations SHALL fail closed.

---

## 30. Memory and RMA Boundary

Agent runtime state SHALL remain distinct from durable trusted memory.

The Agent Harness SHALL NOT promote model-generated runtime information into trusted memory merely because an agent produced it.

Memory operations SHALL preserve applicable:

- scope;
- provenance;
- trust;
- confidence;
- validation;
- integrity;
- retention;
- revocation;
- audit.

Recursive Memory Architecture SHALL remain distinct from Recursive Language Model reasoning.

---

## 31. RLM Boundary

RLM reasoning SHALL remain subordinate to the Agent Harness and applicable governance boundaries.

RLM output SHALL remain reasoning or evidence.

RLM output SHALL NOT constitute:

- identity;
- authority;
- capability authorization;
- execution authorization;
- security policy.

RLM recursion SHALL remain bounded by externally enforced runtime limits.

---

## 32. Provenance and Audit

Agent Harness operations SHALL integrate with causal provenance and audit.

Applicable provenance SHALL capture:

- initiating principal;
- task;
- agent;
- delegation;
- capability;
- tool;
- execution request;
- authorization decision;
- host/application operation;
- verification;
- outcome.

Audit records SHALL be protected against unauthorized modification.

---

## 33. Observability

The Agent Harness SHALL expose appropriate operational and security telemetry.

Observability SHALL support detection and investigation of:

- lifecycle changes;
- authority changes;
- capability changes;
- tool invocation;
- resource consumption;
- policy decisions;
- failures;
- recovery;
- termination;
- security events;
- inter-agent communication;
- consequential execution.

Observability SHALL NOT itself constitute authority.

---

## 34. Failure Handling

Agent Harness failures SHALL fail safely.

Applicable failure conditions include:

- invalid identity;
- invalid authority;
- revoked authority;
- expired authority;
- unavailable capability;
- policy conflict;
- resource exhaustion;
- runtime isolation failure;
- dependency failure;
- security failure;
- integrity failure;
- ambiguous security state.

Unknown security-relevant conditions SHALL fail closed where applicable.

---

## 35. Emergency Controls

Emergency controls SHALL remain independent of the agent and model.

Applicable controls include:

- pause;
- cancellation;
- authority revocation;
- quarantine;
- isolation;
- termination;
- emergency stop.

Agents SHALL NOT modify, disable, suppress, or bypass emergency controls.

---

## 36. Recovery and Revalidation

Recovery SHALL NOT convert persisted state into authority.

Before consequential continuation, recovery SHALL revalidate applicable:

- human principal;
- Lyri identity;
- session;
- agent identity;
- task;
- delegated authority;
- capability;
- target;
- policy;
- resource limits;
- security state;
- revocation state;
- expiry state;
- dependency state.

Expired or revoked authority SHALL remain invalid.

---

## 37. Durable Runtime State

Persisted Agent Harness state SHALL be treated as runtime state rather than automatic authorization.

Checkpoints SHALL NOT override:

- current policy;
- current authorization;
- current capability state;
- current security state;
- revocation;
- expiry;
- resource limits.

Recovery SHALL preserve provenance and audit context where applicable.

---

## 38. Voice and External Protocol Boundary

Voice input SHALL NOT provide privileged Agent Harness authority.

External protocols such as MCP or A2A SHALL enter through controlled identity, trust, policy, capability, and execution boundaries.

External protocol messages SHALL NOT bypass:

- Aegis;
- Capability Gateway;
- Secure Executor;
- Sandbox;
- LHICF;
- verification.

---

## 39. Security Invariants

The following invariants SHALL hold:

1. Agent identity SHALL remain distinct from human, Lyri, session, model, provider and tool identity.
2. Agent registration SHALL NOT grant execution authority.
3. Lifecycle state SHALL NOT grant authority.
4. ACP SHALL NOT become an independent security authority.
5. Agent Harness SHALL NOT provide unrestricted host access.
6. Capability binding SHALL NOT bypass authorization.
7. Delegation SHALL NOT enlarge authority.
8. Delegation SHALL NOT itself authorize execution.
9. Model output SHALL NOT constitute authorization.
10. Tool output SHALL NOT constitute authorization.
11. Inter-agent messages SHALL NOT constitute authorization.
12. Runtime state SHALL NOT constitute current authority.
13. Expired authority SHALL remain invalid.
14. Revoked authority SHALL remain invalid.
15. Resource exhaustion SHALL NOT produce privilege escalation.
16. Emergency controls SHALL remain independent of the agent.
17. Agent Harness SHALL NOT create an alternate privileged path.
18. Privileged execution SHALL pass through the canonical security chain.
19. Recovery SHALL revalidate applicable authority and capability state.
20. Consequential execution SHALL remain independently verifiable.

---

## 40. Validation Requirements

Validation SHALL verify, as applicable:

- agent identity uniqueness;
- identity separation;
- registration controls;
- lifecycle transitions;
- lifecycle authorization;
- task binding;
- capability binding;
- authority validation;
- authority attenuation;
- tool invocation controls;
- runtime isolation;
- resource enforcement;
- inter-agent authentication;
- message integrity;
- replay resistance;
- impersonation resistance;
- cross-task isolation;
- cross-session isolation;
- cross-tenant isolation;
- emergency controls;
- recovery revalidation;
- termination enforcement;
- provenance;
- audit integrity;
- execution-boundary preservation.

Negative tests SHALL attempt unauthorized registration, identity substitution, authority escalation, capability escalation, tool abuse, resource bypass, sandbox bypass, recovery abuse and alternate execution paths.

---

## 41. Security Testing

Security testing SHALL address:

- prompt injection;
- indirect prompt injection;
- goal hijacking;
- tool poisoning;
- agent impersonation;
- confused deputy;
- privilege escalation;
- delegation abuse;
- replay;
- inter-agent tampering;
- cross-task leakage;
- cross-tenant leakage;
- credential exposure;
- data exfiltration;
- arbitrary execution;
- sandbox escape;
- host abuse;
- recursive runaway;
- resource exhaustion;
- stale authority after recovery;
- malicious MCP/A2A integration.

The existence of this specification SHALL NOT be treated as evidence that the controls are implemented.

---

## 42. Cross-Document Dependencies

PB-DOC-005 depends upon and SHALL remain consistent with:

- Unified Core Requirements PRD;
- Unified Core Architecture;
- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Agentic Runtime Specification;
- Agent Identity and Authority Specification;
- Capability Model Specification;
- Validation Specification;
- Security Testing Specification;
- Operations Specification;
- Recovery and Resilience Specification;
- Memory and Provenance architecture;
- Phase-B Master Manifest.

Any conflict SHALL be resolved through the applicable architecture and governance process.

---

## 43. Governance Boundary

This specification defines an architectural and documentation baseline.

It SHALL NOT by itself authorize:

- implementation;
- privileged execution;
- production deployment;
- autonomous host control;
- production certification.

Architecture Approval remains governed by the Phase-B Architecture Approval Gate.

Implementation Authorization SHALL remain a separate governance decision.

---

## 44. Acceptance Criteria

PB-DOC-005 SHALL be considered structurally acceptable only when:

- required metadata is valid;
- all required sections are present;
- Agent Harness responsibilities are explicitly defined;
- ACP/Harness boundaries are explicit;
- identity and lifecycle boundaries are defined;
- capability and authority boundaries are defined;
- execution boundaries are defined;
- runtime isolation is defined;
- resource controls are defined;
- inter-agent controls are defined;
- recovery controls are defined;
- provenance and audit requirements are defined;
- security invariants are defined;
- validation requirements are defined;
- cross-document dependencies are recorded;
- governance state remains accurate.

Semantic acceptance additionally requires reconciliation against the applicable Phase-B architecture and security specifications.

---

## 45. Semantic Reconciliation

PB-DOC-005 SHALL be reconciled against:

- CORE-AG-001 through CORE-AG-008;
- Core Architecture;
- Phase-B Architecture Baseline;
- Agentic Runtime Specification;
- Identity and Authority Specification;
- Capability Model;
- Security Architecture;
- Validation Specification;
- Security Testing Specification;
- Recovery and Resilience Specification.

Reconciliation SHALL verify that no Agent Harness responsibility creates:

- alternate authority;
- alternate authorization;
- alternate privileged execution;
- unrestricted host access;
- uncontrolled agent spawning;
- recovery-based privilege restoration.

---

## 46. Implementation Boundary

Implementation SHALL NOT begin solely because this specification exists.

Implementation requires applicable:

- architecture approval;
- requirements approval;
- security review;
- threat-model completion;
- interface contracts;
- validation planning;
- implementation authorization.

Any implementation SHALL preserve the documented security and execution boundaries.

---

## 47. Acceptance State

Current acceptance state:

**Structural Validation:** PENDING  
**Semantic Reconciliation:** PENDING  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED

---

## 48. Governance and Change Control

Changes to this specification SHALL be controlled.

Changes affecting:

- identity;
- authority;
- capability;
- execution;
- security boundaries;
- runtime isolation;
- resource governance;
- recovery;
- inter-agent communication;
- host access

SHALL undergo appropriate architecture and security review.

Validated artifacts SHALL be preserved according to the LYRION documentation governance process.

---

## 49. Final Agent Harness Invariant

The final architectural invariant is:

**Agent Identity ≠ Agent Authority ≠ Capability ≠ Authorization ≠ Execution**

and:

**Agent Control Plane ≠ Agent Harness ≠ Aegis ≠ Capability Gateway ≠ Secure Executor ≠ Sandbox ≠ LHICF**

The Agent Harness SHALL remain a controlled agent runtime boundary.

It SHALL NOT become an independent security authority, authorization authority, or privileged execution path.

The canonical execution boundary remains:

**Human Intent → Lyri Interpretation → Task → Agent → Delegated Authority → Aegis → Capability Authorization → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host → Independent Verification → Memory / Audit / Provenance → Lyri → Human**

---

**End of PB-DOC-005 — Agent Harness Specification v1.0.0**

## Acceptance Evidence

- Controlled validation: **PASS**
- Agent Harness tests: **26 passed / 0 failed**
- Ruff: **PASS**
- mypy: **PASS**
- Formal acceptance review: **36 PASS / 0 FAIL**
- Production certification: **NOT CLAIMED**
- Evidence: `docs/phase-b/agent-harness/validation/PB-DOC-005_ACCEPTANCE_EVIDENCE_v1.md`

The Agent Harness consumes existing governed security and execution
controls and does not create a parallel authorization, capability,
execution-admission, privileged-execution, or security-bypass path.

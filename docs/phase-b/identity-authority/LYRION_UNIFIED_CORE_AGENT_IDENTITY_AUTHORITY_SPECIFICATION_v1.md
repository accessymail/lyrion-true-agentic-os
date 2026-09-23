# LYRION Unified Core — Agent Identity & Authority Specification

**Document ID:** TAOS-CORE-IDENTITY-AUTHORITY-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Status:** DRAFT — IDENTITY & AUTHORITY BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Agent Identity and Authority Model for the
LYRION True Agentic OS Core.

It establishes the identity boundary, authority model, delegation model,
attenuation rules, authentication and attribution requirements, lifecycle
rules, revocation behavior, recovery requirements, and security invariants
applicable to agents.

This document does not independently authorize implementation or execution.

---

## 2. Scope

This specification covers:

- agent identity;
- principal identity;
- identity binding;
- authentication and attribution;
- agent lifecycle identity;
- delegated authority;
- authority scope;
- authority attenuation;
- delegation;
- revocation;
- expiration;
- replay resistance;
- impersonation resistance;
- inter-agent identity;
- authority propagation;
- recovery and revalidation;
- provenance;
- emergency controls;
- security boundaries;
- validation requirements.

---

## 3. Source Hierarchy

This specification SHALL remain subordinate to the approved LYRION True
Agentic OS architecture, applicable security architecture, approved
requirements, governance controls, and validation specifications.

Where a conflict exists, the higher-authority approved architectural or
security control SHALL govern until the conflict is formally resolved.

---

## 4. Architectural Principles

The identity and authority architecture SHALL preserve the following
separations:

**Observation ≠ Opportunity ≠ Reasoning ≠ Decision ≠ Agency ≠ Authority
≠ Capability ≠ Execution ≠ Verification.**

No identity, message, model output, memory object, registry entry, tool
description, frontend request, or external protocol message SHALL independently
create execution authority.

---

## 5. Identity and Authority Separation

Agent identity SHALL be distinct from authority.

Possession of an agent identity SHALL NOT itself grant privileged execution.

Authority SHALL be explicitly established through the applicable governance,
policy, delegation, capability, and authorization controls.

---

## 6. Principal Model

The system SHALL distinguish applicable principals, including:

- human principal;
- Lyri identity;
- agent identity;
- session identity;
- task identity;
- model identity;
- provider identity;
- tool identity;
- external service identity where applicable.

Identity relationships SHALL remain attributable and scoped.

---

## 7. Agent Identity

Every agent SHALL have a unique identity.

Agent identity SHALL be distinct from:

- human identity;
- Lyri identity;
- session identity;
- task identity;
- model identity;
- provider identity;
- tool identity.

Consequential agent operations SHALL be attributable to the authenticated
agent identity and applicable authority.

---

## 8. Agent Identity Binding

Agent identity SHALL be bound to applicable:

- agent identifier;
- agent type;
- lifecycle state;
- parent or delegating agent where applicable;
- capability bindings;
- authority scope;
- security policy;
- runtime instance;
- provenance context.

Identity SHALL NOT be inferred solely from model output.

---

## 9. Identity Stability

Agent identity SHALL remain stable across its authorized lifecycle.

A runtime restart SHALL NOT silently create a different security identity
while preserving authority.

Identity changes SHALL be explicitly governed and attributable.

---

## 10. Identity Lifecycle

Identity lifecycle SHALL support, as applicable:

- creation;
- initialization;
- activation;
- suspension;
- resumption;
- termination;
- recovery;
- revocation.

Lifecycle transitions SHALL be governed and auditable.

---

## 11. Authentication

Consequential operations SHALL require authentication appropriate to the
applicable principal, operation risk, and security architecture.

Authentication SHALL establish the identity context used for subsequent
authority evaluation.

Authentication SHALL NOT by itself constitute authorization for privileged
execution.

---

## 12. Attribution

Consequential agent actions SHALL be attributable to:

- initiating principal;
- agent identity;
- task;
- applicable delegated authority;
- capability;
- policy decision;
- execution context.

Attribution SHALL be preserved through applicable downstream execution
boundaries.

---

## 13. Authority Model

Authority SHALL be explicit.

Authority SHALL NOT be inferred from:

- agent existence;
- agent registration;
- model output;
- reasoning;
- prompts;
- tool output;
- memory content;
- messages;
- capability descriptions;
- frontend requests;
- external protocol messages.

---

## 14. Authority Binding

Delegated authority SHALL bind applicable:

- principal;
- task;
- agent;
- capability;
- target;
- scope;
- duration;
- policy;
- resource limits;
- revocation state.

Additional constraints SHALL be applied where required by the applicable
security architecture.

---

## 15. Least Privilege

Every agent SHALL receive only the minimum authority required for its current
task.

Privileged operations SHALL follow deny-by-default behavior unless explicitly
permitted by applicable policy and authorization controls.

---

## 16. Authority Scope

Authority SHALL be scoped according to applicable:

- task;
- agent;
- capability;
- target;
- resource;
- environment;
- session;
- tenant;
- time;
- policy.

Authority SHALL NOT be broader than necessary for the authorized operation.

---

## 17. Capability Binding

Authority SHALL be associated with explicitly permitted capabilities.

Capabilities SHALL NOT imply unlimited authority.

A capability SHALL remain subject to the applicable identity, authority,
policy, target, resource, execution-admission, and security controls.

---

## 18. Delegated Authority

Authority SHALL be explicitly delegated where delegated execution is required.

Delegation SHALL define applicable:

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

---

## 19. Authority Attenuation

Delegation SHALL attenuate rather than expand authority.

Conceptually:

**Child Authority ⊆ Parent Authority**

A delegated agent SHALL NOT acquire broader authority than the valid authority
available to its delegating principal and applicable task.

---

## 20. No Authority Escalation Through Delegation

An agent SHALL NOT enlarge its authority by:

- delegating work;
- reasoning;
- prompting;
- tool output;
- self-declaration;
- inter-agent messages;
- capability discovery;
- recursive agent creation.

Delegation SHALL NOT constitute an authority-escalation mechanism.

---

## 21. Delegation Is Not Execution Authorization

Delegation itself SHALL NOT constitute execution authorization.

Execution SHALL require the independent capability authorization and execution
admission controls defined by the security architecture.

---

## 22. Authority Expiration

Authority SHALL support expiration.

Expired authority SHALL NOT be used for consequential operations.

Runtime state or checkpoints SHALL NOT restore expired authority merely because
the authority appears in persisted state.

---

## 23. Authority Revocation

Authority SHALL be revocable.

Revocation SHALL invalidate applicable authority according to the governing
security and authority model.

Revoked authority SHALL NOT remain usable merely because an agent retains a
previous authority representation.

---

## 24. Replay Resistance

Authority-bearing requests and consequential delegated operations SHALL provide
replay resistance appropriate to the operation.

Applicable mechanisms SHALL bind requests to the relevant:

- identity;
- task;
- authority;
- context;
- nonce or equivalent freshness mechanism;
- validity period;
- provenance.

---

## 25. Impersonation Resistance

The identity architecture SHALL resist agent impersonation.

An agent SHALL NOT be able to claim another agent identity through:

- model output;
- message content;
- self-declaration;
- tool metadata;
- task metadata;
- external input.

Identity claims SHALL be validated against the applicable trusted identity
mechanism.

---

## 26. Inter-Agent Identity

Inter-agent communication SHALL preserve authenticated and attributable agent
identity.

Communication SHALL provide appropriate:

- authentication;
- attribution;
- authorization;
- integrity protection;
- replay resistance;
- scope enforcement;
- impersonation resistance.

---

## 27. Inter-Agent Authority Boundary

Inter-agent messages SHALL NOT grant authority merely because a message was
received from another agent.

Messages SHALL carry or reference only the authority context permitted by the
applicable protocol and security architecture.

Authority SHALL be independently validated.

---

## 28. Cross-Task Isolation

Identity and authority contexts SHALL remain isolated across tasks.

Authority from one task SHALL NOT silently transfer to another task.

Cross-session and cross-tenant isolation SHALL be enforced where applicable.

---

## 29. Agent Registry Boundary

The Agent Registry SHALL provide controlled discovery and identity metadata.

Registry membership SHALL NOT constitute execution authority.

Registry information SHALL NOT be treated as proof of authorization for a
privileged operation.

---

## 30. Agent Control Plane Boundary

The Agent Control Plane SHALL govern applicable agent mechanics, including:

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

ACP SHALL NOT become an independent security authority.

Scheduling SHALL NOT constitute execution authorization.

---

## 31. Aegis Boundary

Aegis SHALL remain the independent governance, policy, trust, risk, and
containment authority defined by the security architecture.

Agent identity SHALL NOT bypass Aegis.

Agent authority SHALL remain subject to applicable Aegis controls.

---

## 32. Capability Gateway Boundary

The Capability Gateway SHALL remain the execution-admission boundary.

Identity and delegated authority SHALL be evaluated before applicable execution
admission.

Capability possession SHALL NOT bypass authority validation.

---

## 33. Secure Execution Boundary

The Agent Identity and Authority Model SHALL NOT directly execute privileged
host operations.

The controlled execution chain SHALL remain:

**Agent → Delegated Authority → Aegis → Capability Authorization →
Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host**

Independent verification SHALL remain downstream of execution.

---

## 34. Emergency Controls

Emergency controls SHALL remain independent of agent authority.

Agents SHALL NOT:

- disable emergency controls;
- modify emergency controls;
- grant themselves emergency authority;
- restore revoked emergency authority;
- bypass quarantine or termination controls.

---

## 35. Recovery and Revalidation

Recovery SHALL revalidate applicable:

- principal identity;
- agent identity;
- task identity;
- delegated authority;
- capability;
- policy;
- resource constraints;
- security state;
- revocation state;
- validity period.

Recovery SHALL fail closed when required identity or authority state cannot
be revalidated.

---

## 36. Durable State

Persisted runtime state SHALL NOT itself constitute current authority.

Authority-bearing state SHALL be revalidated against the authoritative
identity, policy, delegation, revocation, and security state before consequential
continuation.

---

## 37. Provenance

Authority-relevant operations SHALL produce provenance sufficient to determine:

- who initiated the task;
- which agent acted;
- which authority was used;
- which delegation established that authority;
- which capability was invoked;
- which policy permitted the operation;
- which execution boundary admitted it;
- which host operation occurred;
- what result was produced;
- what verification occurred.

---

## 38. Model and Reasoning Boundary

Model output and reasoning SHALL remain untrusted proposed intent or reasoning
unless independently validated through the applicable governance and authority
controls.

RLM output SHALL NOT constitute authorization.

Reasoning SHALL NOT enlarge agent authority.

---

## 39. Memory Boundary

Memory content SHALL NOT automatically constitute authority.

RMA SHALL remain distinct from identity and authority enforcement.

Memory-derived information SHALL require applicable validation and governance
before influencing authority decisions.

---

## 40. Voice Boundary

Voice identity SHALL NOT independently grant privileged execution authority.

Voice processing SHALL remain subject to the applicable authenticated principal,
identity, policy, authority, and execution controls.

---

## 41. External Protocol Boundary

External protocol messages SHALL NOT directly establish authority.

MCP, A2A, APIs, application protocols, adapters, or external services SHALL
enter through the applicable identity, trust, policy, capability, and execution
boundaries.

---

## 42. Universal Computer Boundary

Universal Computer operations SHALL preserve the identity and authority chain.

The abstraction SHALL NOT create an alternate authority or privileged
execution path.

Applicable operations SHALL remain subject to:

- identity;
- authority;
- capability;
- execution admission;
- sandbox;
- LHICF;
- verification;
- provenance.

---

## 43. Resource Authority

Authority SHALL remain subject to applicable resource constraints.

Delegated authority SHALL NOT permit an agent to bypass:

- CPU limits;
- memory limits;
- storage limits;
- network limits;
- tool-call limits;
- time limits;
- token limits;
- agent-count limits;
- swarm limits;
- egress limits;
- artifact limits;
- retry limits.

---

## 44. Security Invariants

The following SHALL remain invariant:

1. Agent identity is distinct from human identity.
2. Identity does not itself grant execution authority.
3. Registry membership does not grant execution authority.
4. ACP is not an independent security authority.
5. Delegation does not itself authorize execution.
6. Child authority SHALL NOT exceed parent authority.
7. Agents cannot manufacture authority claims.
8. Messages do not implicitly grant authority.
9. Model output does not constitute authority.
10. Memory content does not automatically constitute authority.
11. Expired authority cannot be used.
12. Revoked authority cannot be restored merely from runtime state.
13. Recovery cannot silently expand authority.
14. No alternate privileged execution path may be introduced.
15. Emergency controls remain independent of agent authority.

---

## 45. Validation Requirements

Validation SHALL include, as applicable:

- identity uniqueness tests;
- lifecycle identity tests;
- authentication tests;
- attribution tests;
- authority-scope tests;
- delegation tests;
- attenuation tests;
- parent/child authority tests;
- revocation tests;
- expiration tests;
- replay tests;
- impersonation tests;
- cross-task isolation tests;
- cross-session isolation tests;
- cross-tenant isolation tests;
- recovery revalidation tests;
- negative authorization tests;
- emergency-control tests;
- adversarial authority-escalation tests;
- provenance tests.

Validation SHALL include negative-path testing demonstrating that unauthorized
identity or authority claims fail closed.

---

## 46. Cross-Document Dependencies

This specification depends on and SHALL remain consistent with:

- LYRION Unified Core Architecture;
- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Core Requirements PRD;
- Agentic Runtime Specification;
- Capability Model;
- Aegis Governance;
- Secure Execution;
- Memory/Provenance;
- Recovery/Resilience;
- Observability;
- Security Testing;
- Validation Specification;
- Phase-B Governance and Master Manifest.

No implementation-specific behavior SHALL be treated as authoritative until
the corresponding architecture and governance controls are approved.

---

## 47. Governance Boundary

This document is an architectural/specification baseline.

Structural validation of this document SHALL NOT constitute architecture
approval.

Architecture approval SHALL NOT constitute implementation authorization.

Implementation authorization SHALL NOT constitute production certification.

---

## 48. Acceptance Criteria

PB-DOC-003 may be considered structurally complete only when:

- all required sections are present;
- identity boundaries are explicit;
- authority boundaries are explicit;
- delegation and attenuation are explicit;
- revocation and expiration are explicit;
- replay and impersonation resistance are explicit;
- recovery revalidation is explicit;
- security execution boundaries are preserved;
- validation requirements are defined;
- cross-document dependencies are recorded;
- governance boundaries remain intact.

Formal closure requires successful structural validation and semantic
cross-document reconciliation.

---

## 49. Final Authority Invariant

The LYRION True Agentic OS Core SHALL preserve one coherent authority model.

No agent, model, tool, workflow, adapter, message, memory object, frontend,
external protocol, recovery checkpoint, or runtime component SHALL create an
alternate authority or privileged execution path.

**Identity ≠ Authority ≠ Capability ≠ Execution.**

**Evidence ≠ Authority.**

**Delegation ≠ Execution Authorization.**

**Architecture Approval ≠ Implementation Authorization.**

**Implementation Authorization ≠ Production Certification.**

---

## Acceptance State

**Structural Validation:** PENDING  
**Semantic Reconciliation:** PENDING  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED

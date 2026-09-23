# LYRION Unified Core — Aegis Governance Specification

**Document ID:** TAOS-CORE-AEGIS-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Status:** DRAFT — AEGIS GOVERNANCE BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Aegis governance boundary for the LYRION Unified Core.

Aegis SHALL provide independent governance, trust, policy, risk, defense, containment, and security decision functions without becoming an alternate privileged execution mechanism.

---

## 2. Scope

This specification covers:

- governance
- trust evaluation
- policy enforcement
- risk evaluation
- threat evaluation
- authority validation
- capability governance
- approval coordination
- denial
- revocation
- quarantine
- containment
- emergency controls
- security response
- governance interaction with execution boundaries
- validation and provenance

---

## 3. Terminology

For this specification:

- **Aegis** means the independent LYRION governance, security, trust, policy, risk, and containment authority.
- **Principal** means an authenticated identity participating in a governed operation.
- **Authority** means delegated permission within defined scope.
- **Capability** means an allowed class of operation.
- **Policy** means an authoritative governance rule.
- **Risk** means the assessed security or operational consequence associated with an operation.
- **Containment** means restricting or isolating execution or agent activity.
- **HITL** means governed human-in-the-loop approval.
- **Execution Admission** means the authoritative admission decision preceding consequential execution.

---

## 4. Architectural Position

Aegis SHALL remain an independent governance and security authority.

Aegis SHALL operate upstream of consequential execution and shall preserve the established security and execution boundaries.

Aegis SHALL NOT become an alternate execution path.

---

## 5. Aegis Authority Model

Aegis SHALL govern security-relevant decisions through trusted system components.

Aegis authority SHALL be bounded by the approved LYRION architecture and SHALL NOT be derived solely from model output, agent intent, memory, frontend state, external content, or tool messages.

---

## 6. Independence from Agent Reasoning

Aegis SHALL operate independently of the agent's own reasoning.

Models and agents SHALL NOT modify, override, disable, or redefine their own governing security policy.

Model output SHALL remain non-authoritative.

Agent intent SHALL remain non-authoritative until processed through the applicable governance and authorization boundaries.

---

## 7. Trust Governance

Aegis SHALL support trust evaluation for applicable principals, agents, capabilities, tools, integrations, execution contexts, and security-relevant operations.

Trust SHALL NOT be inferred solely from successful model generation or prior execution.

Trust decisions SHALL remain bounded by identity, provenance, scope, policy, risk, and applicable evidence.

---

## 8. Policy Governance

Aegis SHALL enforce applicable security and governance policy.

Policy enforcement SHALL be performed by trusted system components.

Unrecognized, unauthorized, or insufficiently scoped operations SHALL fail closed.

Policy evaluation SHALL NOT be delegated solely to the model or agent.

---

## 9. Risk Evaluation

Aegis SHALL support risk evaluation for governed operations.

Risk evaluation SHALL consider applicable operation, principal, authority, capability, target, context, policy, resources, and security state.

Risk classification SHALL determine whether additional governance or approval controls are required.

---

## 10. Threat Evaluation

Aegis SHALL support threat evaluation and runtime defense.

Threat evaluation SHALL consider applicable malicious, anomalous, unauthorized, compromised, replayed, manipulated, or otherwise unsafe activity.

Security-relevant threat decisions SHALL remain independent of agent reasoning.

---

## 11. Authority Validation

Aegis SHALL validate applicable authority before consequential operations proceed.

Authority SHALL remain:

- task-bound
- agent-bound
- capability-scoped
- target-bound where applicable
- time-bounded
- revocable
- replay-resistant
- policy-bound

Delegated authority SHALL NOT exceed its parent authority or governing task scope.

---

## 12. Capability Governance

Aegis SHALL govern applicable capability use.

Capability governance SHALL preserve the distinction between:

**Authority ≠ Capability ≠ Execution**

Possession or discovery of a capability SHALL NOT by itself grant unrestricted authority.

---

## 13. Action and Request Evaluation

Aegis SHALL evaluate applicable governed action requests before consequential execution.

Evaluation SHALL preserve principal, task, agent, delegated authority, capability, target, policy, resource, time, approval, and provenance context where applicable.

An action proposal SHALL NOT become an execution authorization merely because it was generated by an agent.

---

## 14. Denial and Fail-Closed Behavior

Aegis SHALL support explicit denial.

Where required security context, identity, authority, capability, policy, approval, trust, or resource conditions are absent or invalid, the governed operation SHALL fail closed.

Denial SHALL be auditable where applicable.

---

## 15. Approval and HITL Coordination

Aegis SHALL coordinate human approval when policy, risk, capability classification, or other governance requirements require HITL.

HITL approval SHALL remain scoped to the approved request and SHALL NOT become unrestricted execution authority.

Human approval SHALL NOT bypass applicable capability, execution, sandbox, host, verification, or provenance controls.

---

## 16. Authority Revocation

Aegis SHALL support authority revocation.

Revoked authority SHALL remain invalid.

Revocation SHALL propagate to applicable dependent authorization and execution state.

Revocation SHALL NOT be defeated by cached agent state, model context, memory, or previously generated plans.

---

## 17. Agent Quarantine

Aegis SHALL support agent quarantine when required by security or governance policy.

Quarantine SHALL restrict applicable agent activity according to policy.

A quarantined agent SHALL NOT independently remove or bypass its quarantine state.

---

## 18. Execution Containment

Aegis SHALL support execution containment.

Containment SHALL be coordinated with the Capability Gateway, Secure Executor, Agent Sandbox, LHICF, and other applicable trusted boundaries.

Aegis SHALL NOT replace these components with an alternate execution mechanism.

---

## 19. Emergency Controls

Emergency Controls SHALL remain independent of normal agent/model authority.

Emergency controls SHALL support applicable operations such as:

- pause
- revoke
- quarantine
- isolate
- disconnect
- terminate

Agents and models SHALL NOT disable or modify their own emergency controls.

---

## 20. Agent and Model Boundary

Aegis SHALL remain independent from model and agent instruction following.

Models and agents SHALL NOT:

- override Aegis policy
- grant themselves authority
- grant themselves capabilities
- modify governance policy
- disable emergency controls
- bypass authorization
- bypass execution admission

---

## 21. Delegated Authority Boundary

Aegis SHALL preserve delegated-authority constraints.

Delegation SHALL NOT itself authorize execution.

Child authority SHALL NOT exceed parent authority.

Authority attenuation SHALL be preserved across delegation and applicable agent expansion.

---

## 22. Capability Gateway Boundary

The Capability Gateway SHALL remain the authoritative execution-admission boundary.

Aegis governance decisions SHALL integrate with the Capability Gateway without creating an alternate privileged path.

Capability Authorization remains upstream of Execution Admission.

---

## 23. Execution Admission Boundary

Execution Admission SHALL evaluate only after applicable governance, identity, authority, capability, policy, and approval conditions are satisfied.

Execution Admission SHALL NOT enlarge delegated authority.

Aegis SHALL NOT be used as a substitute for Execution Admission.

---

## 24. Secure Executor Boundary

The Secure Executor SHALL remain downstream of authorization and admission.

Aegis SHALL not directly perform privileged host execution in place of the Secure Executor.

The Secure Executor SHALL execute operations only after applicable authorization and admission.

---

## 25. Agent Sandbox and LHICF Boundary

The Agent Sandbox remains an execution isolation boundary.

LHICF remains the controlled host-integration boundary.

Aegis SHALL preserve these boundaries and SHALL NOT authorize a bypass around them.

---

## 26. Universal Computer Boundary

Universal Computer operations SHALL remain governed by:

Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Host Operation → Independent Verification → Provenance.

Universal Computer SHALL NOT bypass Aegis, Capability Authorization, Capability Gateway, Secure Executor, Agent Sandbox, LHICF, or required HITL controls.

---

## 27. Host and Application Harness Boundary

Host Harness and Application Harness SHALL remain governed integration boundaries.

Host Harness and Application Harness SHALL NOT create alternate privileged execution paths.

Discovery SHALL NOT imply authorization.

Adapters SHALL translate governed operations and SHALL NOT independently enlarge authority.

---

## 28. Memory and RMA Boundary

Aegis SHALL treat memory and retrieved information as governed data rather than automatic authority.

Memory SHALL NOT authorize an operation merely because the information exists in memory.

RMA SHALL remain distinct from Aegis policy authority and from RLM reasoning.

Memory provenance, trust, validation, scope, conflict, revocation, and lifecycle controls SHALL remain applicable.

---

## 29. RLM Boundary

RLM reasoning SHALL remain bounded by externally enforced resource and security controls.

RLM output SHALL be reasoning or evidence and SHALL NOT become authorization.

RLM SHALL NOT modify Aegis policy, grant capabilities, bypass sandboxing, or obtain privileged execution through reasoning recursion.

---

## 30. Inter-Agent and Swarm Boundary

Inter-agent communication SHALL remain attributable, integrity-protected, scoped, replay-resistant, and authorization-bound.

Agent swarm expansion SHALL remain subject to the same Aegis, delegated-authority, capability, execution, sandbox, provenance, and verification boundaries.

Agent communication content SHALL NOT grant authority.

---

## 31. Resource Governance

Aegis SHALL preserve applicable resource governance.

Relevant limits may include:

- CPU
- memory
- storage
- network
- tool calls
- tokens
- execution time
- retries
- egress
- artifacts
- agent count
- swarm depth and width

Security-critical resource limits SHALL NOT depend solely on model instructions.

---

## 32. Recovery and Revalidation

Recovery SHALL revalidate applicable identity, task, policy, authority, capability, resource, and security state.

Expired authority SHALL remain invalid.

Revoked authority SHALL remain invalid.

A checkpoint SHALL NOT restore authority merely because the checkpoint contains previously valid authority.

---

## 33. Provenance and Audit

Aegis decisions SHALL support causal and attributable provenance.

Where applicable, provenance SHALL connect:

Human → Task → Agent → Delegation → Capability → Tool → Execution → Host Action → Verification → Outcome.

Security-relevant governance decisions SHALL be auditable subject to applicable privacy and retention controls.

---

## 34. Observability

Aegis SHALL produce or integrate with security-relevant observability.

Applicable events SHALL support investigation of:

- policy decisions
- risk decisions
- authorization decisions
- denials
- approvals
- revocations
- quarantine
- containment
- emergency controls
- security responses
- policy violations

Observability SHALL NOT itself become an authorization mechanism.

---

## 35. Failure Handling

Aegis failure handling SHALL preserve fail-closed behavior for security-critical operations.

Failure of governance dependencies SHALL NOT cause silent privilege expansion.

Where safe recovery is possible, recovery SHALL revalidate authority and security state before consequential execution resumes.

---

## 36. Security Invariants

The following invariant SHALL remain globally enforced:

**OBSERVATION ≠ OPPORTUNITY ≠ REASONING ≠ DECISION ≠ AGENCY ≠ AUTHORITY ≠ CAPABILITY ≠ EXECUTION ≠ VERIFICATION**

The following Aegis invariants SHALL also remain enforced:

- Aegis remains independent.
- Capability Authorization remains upstream of Execution Admission.
- Capability Gateway remains the authoritative execution-admission boundary.
- Secure Executor remains downstream of authorization and admission.
- Agent Sandbox remains an execution isolation boundary.
- LHICF remains the controlled host-integration boundary.
- Universal Computer does not bypass authorization or admission.
- Host Harness has no alternate privileged path.
- Application Harness has no alternate privileged path.
- Expired authority SHALL remain invalid.
- Revoked authority SHALL remain invalid.
- Emergency controls SHALL remain independent.
- Verification remains independent of admission.
- Provenance remains causal and attributable.

---

## 37. Validation Requirements

Aegis SHALL be validated through the applicable validation hierarchy:

1. Static validation
2. Unit validation
3. Integration validation
4. Adversarial validation
5. Real-infrastructure validation
6. Operational exercises
7. Independent assurance where required
8. Scoped security acceptance

Validation SHALL produce evidence sufficient to establish the tested control and its scope.

---

## 38. Security Testing

Security testing SHALL address applicable Aegis threats and failure modes, including:

- policy bypass
- authority escalation
- capability escalation
- confused deputy behavior
- agent impersonation
- replay
- stale authority
- revocation failure
- prompt or indirect injection
- tool or integration abuse
- memory poisoning
- inter-agent abuse
- emergency-control bypass
- containment bypass
- recovery abuse
- denial/fail-open behavior
- resource exhaustion
- alternate privileged execution paths

---

## 39. Cross-Document Dependencies

Aegis governance SHALL remain consistent with:

- Core Architecture
- Phase-B Security Architecture
- Core Requirements PRD
- Core PRD Traceability and Acceptance Matrix
- Agentic Runtime Specification
- Agent Identity and Authority Specification
- Capability Model Specification
- Agent Harness Specification
- Host Harness Specification
- Universal Computer Specification
- Application Harness Specification
- Execution Admission Specification
- Memory and Provenance Architecture
- Core Validation Specification
- Core Security Testing Specification
- Core Operations Specification
- Core Recovery and Resilience Specification
- Phase-B Master Manifest
- Phase-B Documentation Gap Register

---

## 40. Traceability

This specification SHALL maintain traceability to the Core security and governance requirements.

Required traceability references:

- TR-001
- TR-002
- TR-003
- TR-004
- TR-005
- TR-006
- TR-007
- TR-008
- TR-009

The Security requirement family SHALL remain mapped to Aegis, HITL, Governance, independent authorization, and security/adversarial validation.

---

## 41. Governance Boundary

Aegis governance SHALL remain distinct from:

- model reasoning
- agent cognition
- agent lifecycle management
- delegated authority issuance
- capability execution
- secure execution
- sandbox isolation
- host integration
- application integration
- verification
- memory persistence

Aegis SHALL govern applicable security and policy decisions without collapsing these architectural boundaries.

---

## 42. Governance and Change Control

Changes to Aegis governance SHALL be subject to controlled architectural review.

Security-critical changes SHALL preserve:

- independent governance
- deny-by-default behavior
- authority boundaries
- capability boundaries
- execution boundaries
- emergency controls
- provenance
- verification
- recovery revalidation

Changes SHALL NOT be accepted solely because an agent or model proposes them.

---

## 43. Acceptance Criteria

PB-DOC-010 SHALL be considered documentation-baseline validated only when:

- required metadata is present
- all required sections are present
- Aegis responsibilities are explicitly defined
- independence from model/agent reasoning is explicit
- governance and execution boundaries remain separated
- fail-closed behavior is preserved
- authority revocation is preserved
- emergency controls remain independent
- Universal Computer and harnesses have no alternate privileged path
- RMA and RLM boundaries remain preserved
- traceability references are present
- structural validation passes
- semantic reconciliation is complete
- no unintended trailing whitespace is present

Documentation validation SHALL NOT constitute architecture approval or implementation authorization.

---

## 44. Semantic Reconciliation

Aegis governance SHALL be reconciled against the approved Phase-B architecture and security architecture.

The reconciliation SHALL preserve:

- Aegis independence
- trusted-system enforcement
- policy governance
- risk evaluation
- authority validation
- capability governance
- containment
- emergency controls
- HITL coordination
- Capability Gateway authority
- Secure Executor boundary
- Agent Sandbox boundary
- LHICF boundary
- independent verification
- causal provenance

**Semantic Reconciliation:** RECONCILED

---

## 45. Implementation Boundary

This document defines the governance baseline only.

It does not authorize implementation.

Implementation SHALL NOT begin until the applicable Phase-B architecture approval and implementation authorization gates are satisfied.

**Implementation Authorization:** NOT AUTHORIZED

---

## 46. Acceptance State

**Structural Validation:** PASS

**Semantic Reconciliation:** RECONCILED

**Architecture Approval:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Implementation:** BLOCKED

**Production Certification:** NOT CLAIMED

---

## 47. Final Aegis Invariant

Aegis remains an independent governance and security authority.

Aegis SHALL remain the independent governance, trust, policy, risk, defense, and containment authority.

Aegis SHALL NOT become an alternate privileged execution path.

Models and agents SHALL NOT override, disable, or modify their own governing security controls.

Capability Authorization, Capability Gateway, Execution Admission, Secure Executor, Agent Sandbox, LHICF, independent verification, and provenance SHALL retain their respective architectural boundaries.

---

## 48. Documentation Status

This specification is a Phase-B documentation baseline.

It is not evidence that the Aegis implementation exists, has passed implementation validation, is production-ready, or is certified.

**Status:** DRAFT — AEGIS GOVERNANCE BASELINE

---

## 49. Governance and Approval

Formal approval SHALL require review against:

- Phase-B Architecture
- Phase-B Security Architecture
- Core Requirements PRD
- Core Traceability and Acceptance Matrix
- applicable Phase-B specifications
- validation requirements
- security testing requirements
- operations and recovery requirements
- Master Manifest
- Documentation Gap Register

Until formal approval is recorded:

**Architecture Approval: PENDING**

**Implementation Authorization: NOT AUTHORIZED**

**Production Implementation: BLOCKED**

**Production Certification: NOT CLAIMED**


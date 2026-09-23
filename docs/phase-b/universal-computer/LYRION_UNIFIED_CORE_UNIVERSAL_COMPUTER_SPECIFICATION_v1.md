# LYRION Unified Core — Universal Computer Specification

**Document ID:** TAOS-CORE-UNIVERSAL-COMPUTER-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Status:** DRAFT — UNIVERSAL COMPUTER BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Universal Computer architectural boundary for LYRION True Agentic OS Phase B.

The Universal Computer SHALL provide a controlled, host-independent abstraction for governed operations across supported hosts, operating environments, applications, devices, and execution environments.

The Universal Computer SHALL abstract environment-specific implementation without weakening identity, authority, capability, security, execution, verification, or provenance boundaries.

---

## 2. Scope

This specification covers:

- Universal Computer operations;
- host and environment abstraction;
- capability-to-operation mapping;
- authority preservation;
- host and application adapter selection;
- concrete operation mapping;
- unsupported capability handling;
- execution and security boundaries;
- verification;
- provenance;
- observability;
- resource constraints;
- recovery;
- emergency controls;
- validation and security testing.

This specification does not replace Aegis, Capability Gateway, Secure Executor, Agent Sandbox, LHICF, Host Harness, or Application Harness.

---

## 3. Source Hierarchy

The authoritative design sources are:

1. LYRION Unified Core Architecture;
2. Phase-B Architecture Baseline;
3. Existing Architecture Capability Baseline and TAOS Phase-B Reconciliation;
4. Core Requirements PRD;
5. Phase-B Security Architecture;
6. Agent Identity and Authority Specification;
7. Capability Model Specification;
8. Agent Harness Specification;
9. Host Harness Specification;
10. Core Validation Specification;
11. Security Testing Specification;
12. Recovery / Resilience Specification;
13. Phase-B Governance and Master Manifest artifacts.

Where a lower-level specification conflicts with an approved higher-level architecture, the conflict SHALL be resolved through formal architecture governance rather than silently overridden.

---

## 4. Architectural Principles

The Universal Computer SHALL follow these principles:

- abstraction without authority expansion;
- capability-bound operation;
- explicit authorization;
- least privilege;
- deny-by-default for privileged operations;
- security-chain preservation;
- host-independent operation modeling;
- adapter isolation;
- fail-closed unsupported behavior;
- independent verification;
- provenance preservation;
- observable operation lifecycle;
- controlled recovery;
- independent emergency control;
- no alternate privileged path.

Universal Computer abstraction SHALL NOT be treated as execution authorization.

---

## 5. Universal Computer Definition

Universal Computer is a controlled Phase-B abstraction architecture that represents governed computer operations independently from a particular host implementation.

The Universal Computer SHALL translate an authorized abstract operation into an appropriate host or application operation through governed adapters.

The Universal Computer SHALL NOT itself become a privileged execution authority.

---

## 6. Canonical Operation Flow

The canonical Universal Computer operation flow SHALL be:

**Agent Intent  
→ Capability  
→ Authority  
→ Execution Admission  
→ Universal Computer Operation  
→ Host/Application Adapter  
→ Concrete Host Operation  
→ Verification  
→ Provenance**

Each transition SHALL preserve applicable identity, task, authority, capability, policy, security, resource, approval, and provenance context.

---

## 7. Operation Identity

Each Universal Computer operation SHALL have an attributable operation identity.

The operation identity SHOULD include, as applicable:

- operation identifier;
- principal;
- task;
- agent;
- delegated authority;
- capability;
- target;
- operation class;
- host/environment;
- application;
- adapter;
- policy context;
- approval state;
- resource constraints;
- security state;
- provenance context.

Operation identity SHALL NOT be inferred solely from model output or natural-language intent.

---

## 8. Host and Environment Abstraction

The Universal Computer SHALL separate:

- agent intent;
- capability request;
- authority;
- Universal Computer operation;
- host environment;
- host-specific implementation.

Conceptually:

**Agent Intent  
→ Capability  
→ Universal Computer Operation  
→ Host Abstraction  
→ Host Adapter  
→ Concrete Host Operation**

This abstraction SHALL prevent agents from becoming tightly coupled to a particular operating-system implementation.

---

## 9. Environment Discovery

Universal Computer MAY use governed environment discovery to determine applicable execution environments.

Discovery MAY include:

- operating system;
- OS version;
- architecture;
- runtime environment;
- available interfaces;
- installed applications;
- available devices;
- available services;
- host capabilities;
- security state;
- resource state.

Environment discovery SHALL NOT grant execution authority.

---

## 10. Host Discovery

Universal Computer SHALL support controlled host discovery where required.

Host discovery MAY identify:

- host identity;
- host type;
- operating environment;
- supported adapters;
- supported capabilities;
- applicable security constraints;
- resource constraints;
- host availability.

Host discovery SHALL remain informational and operationally bounded.

Host discovery SHALL NOT bypass authorization or establish privilege.

---

## 11. Application Discovery

Universal Computer MAY discover applications and application capabilities through governed interfaces.

Application discovery SHALL distinguish:

- application identity;
- application capability;
- application availability;
- application state;
- supported interaction model;
- authorization state.

Application discovery SHALL NOT itself authorize application interaction.

---

## 12. Capability Discovery

Universal Computer SHALL support controlled capability discovery.

Capability discovery MAY determine:

- supported operation classes;
- supported host mappings;
- supported application mappings;
- required resources;
- required approvals;
- security restrictions;
- unsupported combinations.

Capability discovery SHALL NOT grant authority.

Capability availability SHALL NOT be interpreted as permission to execute.

---

## 13. Capability-to-Operation Mapping

Universal Computer SHALL map an authorized capability to a defined operation model.

The mapping SHALL preserve:

- principal;
- task;
- agent;
- delegated authority;
- capability scope;
- target;
- operation;
- policy;
- resource limits;
- approval state;
- revocation state;
- expiry state;
- provenance.

Capability-to-operation mapping SHALL NOT enlarge authority.

---

## 14. Authority Preservation

Universal Computer SHALL preserve applicable authority constraints.

Universal Computer SHALL NOT:

- manufacture authority;
- infer authority from intent;
- expand delegated authority;
- inherit unrestricted host privilege;
- treat capability discovery as authorization;
- treat adapter availability as authorization;
- treat host availability as authorization;
- treat model output as authorization.

Effective operation permission SHALL remain bounded by applicable authority, capability, policy, scope, security state, and execution admission.

---

## 15. Authorization Boundary

Universal Computer SHALL operate only after applicable authorization and execution-admission controls have been satisfied.

The Universal Computer SHALL NOT replace:

- Aegis;
- Capability Gateway;
- execution admission;
- HITL where required;
- Secure Executor;
- Agent Sandbox;
- LHICF.

Authorization SHALL remain explicit and policy-controlled.

---

## 16. Aegis Boundary

Aegis SHALL remain the independent governance, trust, policy, risk, and containment authority.

Universal Computer SHALL consume applicable security decisions rather than independently redefining privileged authority.

Universal Computer SHALL NOT modify, disable, or bypass Aegis controls.

---

## 17. Capability Gateway Boundary

The Capability Gateway SHALL remain the authoritative execution-admission boundary.

Universal Computer requests SHALL NOT bypass Capability Authorization or Capability Gateway authorization where applicable.

Failed authorization or admission checks SHALL NOT proceed into privileged execution.

Universal Computer SHALL NOT become an alternate Capability Gateway.

---

## 18. Secure Executor Boundary

Secure Executor SHALL execute only operations already authorized and admitted.

Universal Computer SHALL provide an operation representation, not an independent privilege mechanism.

Secure Executor SHALL remain responsible for controlled execution enforcement including applicable:

- resource limits;
- lifecycle;
- timeout;
- cancellation;
- execution metadata;
- result handling;
- provenance.

Universal Computer SHALL NOT infer privilege from operation descriptions.

---

## 19. Agent Sandbox Boundary

Universal Computer operations requiring execution SHALL remain within the applicable Agent Sandbox / execution boundary.

Sandboxing SHALL address applicable:

- process isolation;
- filesystem isolation;
- network isolation;
- credential isolation;
- resource fencing;
- IPC restrictions;
- escape resistance.

Universal Computer SHALL NOT provide unrestricted host access around the Sandbox.

---

## 20. LHICF Boundary

LHICF SHALL remain the controlled host-integration mediation boundary.

The canonical execution relationship SHALL remain:

**Aegis  
→ Capability Gateway  
→ Secure Executor  
→ Agent Sandbox  
→ LHICF  
→ Host Adapter  
→ Host OS**

Universal Computer SHALL integrate with LHICF rather than bypass it.

Universal Computer SHALL NOT create a second host-control mechanism outside LHICF.

---

## 21. Host Adapter Model

Host adapters SHALL translate governed Universal Computer operations into supported host-specific operations.

Each adapter SHALL have a narrowly defined responsibility.

An adapter SHALL preserve:

- operation identity;
- authority;
- capability scope;
- target;
- policy;
- security state;
- resource constraints;
- provenance.

An adapter SHALL NOT become an alternate authorization or privileged execution boundary.

---

## 22. Adapter Discovery and Selection

Universal Computer SHALL support controlled adapter discovery and selection.

Adapter selection MAY consider:

- host type;
- OS;
- architecture;
- application;
- capability;
- operation;
- version;
- compatibility;
- security state;
- policy;
- resource constraints.

Adapter selection SHALL NOT grant authority.

Adapter selection SHALL fail closed when a safe and authorized adapter cannot be established.

---

## 23. Host Mapping

Universal Computer SHALL map abstract operations to concrete host operations through governed host mappings.

Host mappings SHALL define, as applicable:

- operation semantics;
- host-specific implementation;
- input constraints;
- output representation;
- resource requirements;
- security requirements;
- verification method;
- failure behavior.

Host mapping SHALL NOT bypass the approved security chain.

---

## 24. Application Mapping

Universal Computer SHALL support governed mapping to application operations where applicable.

Application mappings SHALL preserve:

- application identity;
- application capability;
- authorization;
- target;
- operation;
- security policy;
- provenance;
- verification.

Application mapping SHALL NOT authorize interaction merely because an application is discoverable.

---

## 25. Cross-Platform Abstraction

Universal Computer SHALL provide a host-independent operation model where feasible.

Platform-specific behavior SHALL be isolated behind adapters.

Differences between hosts SHALL NOT cause implicit privilege expansion.

Unsupported platform behavior SHALL be represented explicitly rather than silently substituted with an unsafe operation.

---

## 26. Unsupported Capability Handling

Universal Computer SHALL fail closed when a requested capability or operation cannot be safely and authoritatively mapped.

Unsupported conditions MAY include:

- missing adapter;
- incompatible host;
- incompatible application;
- insufficient capability scope;
- insufficient authority;
- policy restriction;
- unavailable resource;
- unavailable security control;
- unavailable verification;
- uncertain operation semantics.

The system SHALL NOT substitute arbitrary shell execution for unsupported Universal Computer functionality.

---

## 27. Universal Computer and Host Harness

Host Harness SHALL provide governed host-environment interaction beneath the Universal Computer abstraction.

The Host Harness SHALL remain subordinate to the Universal Computer architecture.

The Host Harness SHALL NOT establish a second Universal Computer authorization mechanism.

The relationship SHALL preserve:

**Universal Computer Operation  
→ Host/Application Adapter  
→ Host Harness / Application Harness  
→ LHICF / approved boundary  
→ Concrete Operation**

---

## 28. Universal Computer and Application Harness

Application Harness SHALL provide governed application discovery, identification, capability discovery, interaction, verification, and provenance where applicable.

Universal Computer SHALL use Application Harness interfaces without bypassing authorization or security boundaries.

Application-specific interaction SHALL remain attributable and verifiable.

---

## 29. MCP, A2A, and External Integration

External protocols and integrations MAY provide operation requests or capability information.

MCP, A2A, APIs, tools, external services, and applications SHALL NOT independently grant Universal Computer authorization.

External requests SHALL enter the applicable identity, authority, policy, capability, admission, execution, and verification boundaries.

External protocol integration SHALL preserve provenance and attribution.

---

## 30. Resource Governance

Universal Computer operations SHALL remain subject to applicable resource limits.

Resource controls MAY include:

- CPU;
- memory;
- storage;
- network;
- execution time;
- tool calls;
- agent count;
- process count;
- file operations;
- egress;
- artifacts;
- retries;
- cost.

Security-critical limits SHALL NOT depend solely on model instructions.

---

## 31. HITL Boundary

High-risk or consequential Universal Computer operations SHALL require human approval where defined by applicable policy and risk classification.

HITL approval SHALL remain:

- authenticated;
- policy-bound;
- operation-bound;
- time-bounded;
- replay-resistant;
- auditable;
- revocable where applicable.

HITL SHALL NOT be bypassed by Universal Computer, Host Harness, Adapter, Agent, Model, or external protocol.

---

## 32. Verification

Universal Computer operations SHALL have independent verification appropriate to risk.

Verification SHALL determine whether the intended operation actually occurred and whether the resulting state matches applicable expectations.

An agent or model claim SHALL NOT by itself establish successful execution.

Verification MAY include:

- returned state;
- filesystem state;
- process state;
- service state;
- application state;
- device state;
- network state;
- cryptographic evidence;
- independent system observation.

---

## 33. Provenance and Audit

Universal Computer SHALL preserve causal provenance across the operation lifecycle.

Provenance SHOULD capture:

**Human → Task → Agent → Delegation → Capability → Authorization → Universal Computer Operation → Adapter → Host Operation → Verification → Outcome**

Audit records SHOULD include:

- principal;
- agent;
- task;
- capability;
- authority;
- policy;
- target;
- adapter;
- host;
- operation;
- approval;
- execution result;
- verification result;
- timestamps;
- security state;
- provenance identifiers.

---

## 34. Observability

Universal Computer SHALL expose appropriate operational observability.

Observability SHOULD cover:

- discovery;
- mapping;
- authorization;
- adapter selection;
- execution;
- failures;
- resource usage;
- verification;
- recovery;
- security events.

Observability data SHALL remain appropriately scoped and protected.

---

## 35. Failure Handling

Universal Computer SHALL use fail-closed behavior for security-critical uncertainty.

Failures SHALL be attributable and observable.

The system SHALL distinguish:

- rejected operation;
- unsupported operation;
- unavailable adapter;
- failed authorization;
- failed execution;
- partial effect;
- uncertain effect;
- failed verification.

Failure handling SHALL NOT silently convert a failed governed operation into unrestricted host execution.

---

## 36. Partial and Uncertain Effects

Universal Computer SHALL account for operations that may partially succeed or whose final state cannot immediately be determined.

The system SHOULD preserve:

- attempted operation;
- observed effect;
- uncertain effect;
- verification state;
- recovery state;
- compensation or reconciliation information where applicable.

An uncertain result SHALL NOT automatically be treated as successful.

---

## 37. Recovery and Revalidation

Recovery SHALL revalidate applicable:

- principal;
- agent identity;
- task;
- delegated authority;
- capability;
- policy;
- resource constraints;
- security state;
- approval state;
- revocation state;
- expiry state;
- adapter validity;
- host state.

Expired or revoked authority SHALL NOT be restored merely because runtime state contains it.

Recovery SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Sandbox, LHICF, HITL where required, or verification.

---

## 38. Emergency Controls

Emergency controls SHALL remain independent of Universal Computer and agent/model control.

Emergency mechanisms MAY:

- pause;
- revoke;
- quarantine;
- isolate;
- disconnect;
- terminate;
- deny further execution.

Universal Computer SHALL NOT modify or disable emergency controls.

---

## 39. Security Invariants

The following invariants SHALL hold:

1. Universal Computer SHALL NOT itself grant authority.
2. Capability discovery SHALL NOT grant authorization.
3. Host discovery SHALL NOT grant execution authority.
4. Adapter discovery SHALL NOT grant authority.
5. Adapter selection SHALL NOT bypass authorization.
6. Host mapping SHALL NOT enlarge authority.
7. Application mapping SHALL NOT enlarge authority.
8. Universal Computer SHALL NOT bypass Aegis.
9. Universal Computer SHALL NOT bypass Capability Gateway.
10. Universal Computer SHALL NOT bypass Secure Executor.
11. Universal Computer SHALL NOT bypass Agent Sandbox.
12. Universal Computer SHALL NOT bypass LHICF.
13. HITL requirements SHALL NOT be bypassed.
14. Unsupported operations SHALL fail closed where required.
15. Arbitrary shell access SHALL NOT constitute Universal Computer authorization.
16. Model output SHALL NOT constitute authorization.
17. Agent intent SHALL NOT constitute authorization.
18. External protocol messages SHALL NOT constitute authorization.
19. Expired authority SHALL remain invalid.
20. Revoked authority SHALL remain invalid.
21. Recovery SHALL NOT expand authority.
22. Universal Computer SHALL NOT create an alternate privileged path.
23. Consequential operations SHALL remain independently verifiable.
24. Provenance SHALL remain attributable across abstraction boundaries.
25. Emergency controls SHALL remain independent.

---

## 40. Validation Requirements

Validation SHALL cover, as applicable:

- environment discovery;
- host discovery;
- application discovery;
- capability discovery;
- adapter discovery;
- adapter selection;
- capability-to-operation mapping;
- authority preservation;
- authorization;
- execution admission;
- host mapping;
- application mapping;
- unsupported capability handling;
- fail-closed behavior;
- sandbox enforcement;
- LHICF mediation;
- Universal Computer bypass attempts;
- arbitrary shell substitution;
- resource limits;
- HITL enforcement;
- verification;
- provenance;
- recovery;
- emergency controls;
- partial effects;
- adversarial operation requests.

---

## 41. Security Testing

Security testing SHALL include negative-path and adversarial testing for:

- authorization bypass;
- capability escalation;
- authority expansion;
- adapter substitution;
- malicious adapter behavior;
- unsupported-operation fallback;
- arbitrary shell substitution;
- LHICF bypass;
- Sandbox bypass;
- Secure Executor bypass;
- Capability Gateway bypass;
- host isolation;
- application isolation;
- credential exposure;
- network abuse;
- resource exhaustion;
- replay;
- stale authority;
- recovery abuse;
- provenance tampering;
- verification spoofing.

Universal Computer SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Sandbox, LHICF, HITL where required, or independent verification.

---

## 42. Cross-Document Dependencies

This specification depends on:

- Core Architecture;
- Phase-B Architecture Baseline;
- Security Architecture;
- Identity and Authority Specification;
- Capability Model Specification;
- Agent Harness Specification;
- Host Harness Specification;
- Application Harness specification;
- Secure Execution specification;
- LHICF architecture;
- Validation Specification;
- Security Testing Specification;
- Recovery / Resilience Specification;
- Data and Provenance architecture;
- Observability specification.

Changes to these dependencies SHALL trigger semantic reconciliation where applicable.

---

## 43. Governance Boundary

This specification defines an architectural and documentation baseline.

It SHALL NOT be interpreted as evidence that Universal Computer is implemented, validated, accepted, production-operational, or certified.

Implementation Authorization SHALL remain a separate governance decision.

Production Implementation SHALL remain BLOCKED until applicable architecture, security, validation, and governance gates are satisfied.

Production Certification SHALL remain NOT CLAIMED.

The existence of this specification SHALL NOT be treated as evidence that the controls are implemented.

---

## 44. Acceptance Criteria

PB-DOC-007 SHALL be considered documentation-complete only when:

- required sections are present;
- architectural terminology is consistent;
- Universal Computer boundaries are explicit;
- authority and capability boundaries are explicit;
- Aegis boundary is preserved;
- Capability Gateway boundary is preserved;
- Secure Executor boundary is preserved;
- Sandbox boundary is preserved;
- LHICF boundary is preserved;
- Host/Application Adapter model is defined;
- unsupported behavior is defined;
- verification is defined;
- provenance is defined;
- recovery is defined;
- emergency controls are defined;
- validation requirements are defined;
- security testing requirements are defined;
- cross-document dependencies are recorded;
- semantic reconciliation is complete;
- governance state is correctly recorded.

---

## 45. Semantic Reconciliation

Semantic reconciliation SHALL compare this specification against:

- Core PRD;
- Core Architecture;
- Phase-B Architecture Baseline;
- Existing Capability Baseline;
- Security Architecture;
- Identity and Authority;
- Capability Model;
- Agent Harness;
- Host Harness;
- Application Harness;
- Validation;
- Security Testing;
- Recovery;
- Data Architecture;
- Observability.

No semantic conflict SHALL be accepted without formal architecture review and resolution.

---

## 46. Implementation Boundary

Implementation SHALL NOT begin solely because this specification exists.

Any implementation SHALL preserve:

- identity;
- authority;
- capability;
- authorization;
- Aegis;
- Capability Gateway;
- Execution Admission;
- Secure Executor;
- Sandbox;
- LHICF;
- Host/Application Adapter;
- verification;
- provenance;
- recovery;
- emergency controls.

No implementation SHALL introduce an alternate privileged path.

---

## 47. Acceptance State

Current acceptance state:

**Structural Validation:** PENDING  
**Semantic Reconciliation:** PENDING  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED

These states SHALL remain explicit until their corresponding gates are independently satisfied.

---

## 48. Governance and Change Control

Changes to Universal Computer architecture SHALL be reviewed for impact on:

- authority;
- capability;
- execution admission;
- security boundaries;
- host adapters;
- application adapters;
- LHICF;
- Host Harness;
- Application Harness;
- verification;
- provenance;
- recovery;
- emergency controls;
- validation;
- security testing.

Material changes SHALL trigger semantic reconciliation and applicable validation updates.

---

## 49. Final Universal Computer Invariant

Universal Computer SHALL remain a controlled abstraction layer:

**Agent Intent  
→ Capability  
→ Authority  
→ Execution Admission  
→ Universal Computer Operation  
→ Host/Application Adapter  
→ Concrete Host Operation  
→ Independent Verification  
→ Provenance**

Therefore:

**Universal Computer ≠ Authority ≠ Capability ≠ Authorization ≠ Execution ≠ Verification**

Universal Computer SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Agent Sandbox, LHICF, HITL where required, or independent verification.

Arbitrary shell access SHALL NOT constitute Universal Computer architecture.

The Universal Computer layer exists to provide governed abstraction across computer environments while preserving LYRION's security, authority, execution, verification, and provenance invariants.

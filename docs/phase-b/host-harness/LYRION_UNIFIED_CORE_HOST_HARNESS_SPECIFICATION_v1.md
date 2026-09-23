# LYRION Unified Core — Host Harness Specification

**Document ID:** TAOS-CORE-HOST-HARNESS-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Project:** LYRION True Agentic OS  
**Status:** DRAFT — HOST HARNESS BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Host Harness baseline for the LYRION Unified Core.

The Host Harness provides the controlled integration boundary between the LYRION runtime and the applicable host environment.

It establishes requirements for host discovery, host capability mapping, adapter selection, host operation mediation, resource constraints, verification, provenance, failure handling, and recovery.

This specification does not authorize implementation or production operation.

---

## 2. Scope

This specification covers:

- host environment discovery;
- host identity and environment context;
- host capability discovery;
- capability-to-host mapping;
- host adapter selection;
- host operation interfaces;
- filesystem mediation;
- process mediation;
- service mediation;
- network mediation;
- application mediation;
- desktop mediation;
- device mediation;
- clipboard mediation;
- notification mediation;
- operating-system state mediation;
- resource controls;
- fail-closed behavior;
- verification;
- provenance;
- observability;
- recovery;
- security boundaries;
- Universal Computer integration.

The Host Harness SHALL remain subordinate to the established LYRION security and execution architecture.

---

## 3. Source Hierarchy

The Host Harness SHALL remain consistent with the applicable LYRION architecture and governance documents, including:

1. LYRION Unified Core Requirements PRD;
2. LYRION Unified Core Architecture;
3. Phase-B Architecture Baseline;
4. Phase-B Security Architecture;
5. Agentic Runtime Specification;
6. Agent Identity and Authority Specification;
7. Capability Model Specification;
8. Agent Harness Specification;
9. Validation Specification;
10. Security Testing Specification;
11. Recovery and Resilience Specification;
12. Phase-B governance and approval documents.

The governing architectural principle remains:

**PRESERVE → EXTEND → INTEGRATE → VALIDATE → REDESIGN ONLY WHEN REQUIRED**

---

## 4. Architectural Principles

The Host Harness SHALL preserve:

- explicit host operations;
- capability-bound access;
- authority-bound access;
- policy enforcement;
- least privilege;
- deny-by-default behavior for privileged operations;
- runtime isolation;
- resource limits;
- host mediation;
- verification;
- provenance;
- fail-closed behavior;
- recovery revalidation.

The Host Harness SHALL NOT create an alternate authorization or privileged execution path.

---

## 5. Host Harness Definition

The Host Harness is the controlled host-environment integration boundary used by LYRION to interact with the applicable host environment.

It SHALL provide controlled mechanisms for:

- host environment discovery;
- capability mapping;
- host adapter selection;
- host operation requests;
- host operation mediation;
- result handling;
- verification integration;
- provenance integration;
- failure handling;
- recovery integration.

The Host Harness SHALL NOT independently grant authority.

---

## 6. Host Environment Context

The Host Harness SHALL maintain an explicit context for the applicable host environment.

Where applicable, host context SHALL identify:

- operating system;
- operating-system version;
- runtime environment;
- host identity;
- environment identity;
- available host interfaces;
- available applications;
- available devices;
- available services;
- applicable security state;
- applicable resource state.

Host context SHALL be treated as environmental information and SHALL NOT itself constitute authorization.

---

## 7. Host Identity

Host identity SHALL remain distinct from:

- human identity;
- Lyri identity;
- session identity;
- task identity;
- agent identity;
- capability identity;
- authorization state.

Host identity SHALL be attributable where required for consequential operations.

A host identifier SHALL NOT itself grant access to host resources.

---

## 8. Host Discovery

The Host Harness SHALL support controlled discovery of applicable host capabilities and environment characteristics.

Discovery MAY identify:

- filesystem capabilities;
- process capabilities;
- service capabilities;
- network capabilities;
- application capabilities;
- desktop capabilities;
- device capabilities;
- clipboard capabilities;
- notification capabilities;
- operating-system state capabilities.

Discovery SHALL NOT itself grant execution authorization.

---

## 9. Host Capability Discovery

Host capability discovery SHALL identify capabilities actually supported by the applicable host environment.

Capability discovery SHALL distinguish:

- supported;
- unsupported;
- unavailable;
- restricted;
- degraded;
- unknown.

Unsupported or ambiguous capabilities SHALL NOT be silently treated as available.

---

## 10. Capability-to-Host Mapping

The Host Harness SHALL map an authorized abstract capability to the applicable host capability.

Mapping SHALL preserve:

- principal;
- task;
- agent;
- delegated authority;
- capability;
- target;
- scope;
- policy;
- resource constraints;
- approval state;
- revocation state;
- provenance.

Host mapping SHALL NOT enlarge the authority granted upstream.

---

## 11. Host Adapter Model

Host-specific operations SHALL be mediated through defined adapters where applicable.

Adapters SHALL provide controlled mappings between:

- abstract LYRION operations;
- host capabilities;
- concrete host interfaces.

Adapters SHALL be isolated according to applicable security and reliability requirements.

An adapter SHALL NOT become an alternate authorization authority.

---

## 12. Adapter Selection

Adapter selection SHALL consider:

- host environment;
- operating system;
- host version;
- application context;
- device context;
- capability requirements;
- security policy;
- compatibility;
- resource constraints.

Adapter selection SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Sandbox, or LHICF.

---

## 13. Host Operation Model

A consequential host operation SHALL be represented as an explicit operation.

The operation SHALL preserve applicable:

- operation identity;
- principal;
- task;
- agent;
- authority;
- capability;
- target;
- parameters;
- policy;
- resource limits;
- approval state;
- security state;
- provenance.

Natural-language intent SHALL NOT be treated as direct host execution authority.

---

## 14. Host Operation Authorization Boundary

Host operations SHALL remain subject to the established authorization and execution-admission chain.

The Host Harness SHALL NOT independently authorize operations.

The canonical security chain SHALL remain:

**Aegis → Capability Gateway → Secure Executor → Agent Sandbox → LHICF → Host Adapter → Host OS**

Failed authorization or execution-admission checks SHALL prevent the operation from reaching the applicable host integration boundary.

---

## 15. LHICF Boundary

LHICF SHALL remain the controlled host-integration mediation boundary.

The Host Harness SHALL integrate with LHICF rather than bypass it.

LHICF SHALL mediate applicable host operations and provide controlled host integration.

The Host Harness SHALL NOT create a second host-control mechanism outside LHICF.

---

## 16. Filesystem Mediation

Filesystem operations SHALL be explicitly scoped and authorized.

Controls SHALL address, where applicable:

- path scope;
- operation type;
- read/write permissions;
- file identity;
- directory scope;
- symbolic-link behavior;
- mount boundaries;
- resource limits;
- sensitive-data handling;
- provenance;
- verification.

Arbitrary filesystem access SHALL NOT be granted through general agent intent.

---

## 17. Process Mediation

Process operations SHALL be explicitly scoped and authorized.

Controls SHALL address applicable:

- process identity;
- operation type;
- process lifecycle;
- parent/child relationships;
- signal authority;
- execution identity;
- resource limits;
- namespace boundaries;
- provenance;
- verification.

The Host Harness SHALL NOT provide unrestricted process control.

---

## 18. Service Mediation

Service operations SHALL be explicitly scoped and authorized.

Controls SHALL address applicable:

- service identity;
- operation type;
- lifecycle state;
- dependency state;
- privilege requirements;
- resource constraints;
- policy state;
- provenance;
- verification.

Service discovery SHALL NOT itself authorize service modification.

---

## 19. Network Mediation

Network operations SHALL be explicitly scoped and authorized.

Controls SHALL address applicable:

- destination;
- source context;
- protocol;
- port;
- network namespace;
- egress policy;
- credential scope;
- resource limits;
- data-exfiltration controls;
- provenance.

Network access SHALL NOT be inferred merely from task intent.

---

## 20. Application Mediation

Application interactions SHALL use controlled application boundaries.

Applicable operations SHALL preserve:

- application identity;
- target identity;
- capability;
- authorization;
- interaction scope;
- session context;
- resource limits;
- provenance;
- verification.

Application interaction SHALL NOT bypass the Application Harness or other applicable security boundaries.

---

## 21. Desktop and UI Mediation

Desktop interactions SHALL be mediated through controlled interfaces.

Where applicable, controls SHALL address:

- window identity;
- application identity;
- target identification;
- interaction type;
- authorization;
- session state;
- sensitive-data boundaries;
- verification;
- provenance.

UI presentation SHALL NOT be treated as authoritative security state.

---

## 22. Device Mediation

Device operations SHALL be explicitly scoped and authorized.

Applicable devices MAY include:

- cameras;
- microphones;
- displays;
- input devices;
- storage devices;
- other supported host peripherals.

Device access SHALL preserve applicable identity, capability, authorization, policy, resource and provenance controls.

---

## 23. Clipboard Mediation

Clipboard operations SHALL be treated as controlled data-transfer operations.

Controls SHALL address:

- source context;
- destination context;
- data sensitivity;
- authorization;
- target application;
- transfer direction;
- provenance;
- auditability.

Clipboard access SHALL NOT become an unrestricted cross-boundary data channel.

---

## 24. Notification Mediation

Notification operations SHALL be controlled and attributable.

Controls SHALL address:

- notification origin;
- target;
- content sensitivity;
- authorization;
- delivery channel;
- rate/resource limits;
- provenance.

Notifications SHALL NOT be used as an alternate authority or execution path.

---

## 25. Operating-System State Mediation

Operating-system state operations SHALL be explicitly scoped.

Applicable state MAY include:

- system configuration;
- service state;
- process state;
- resource state;
- security state;
- network state;
- device state.

State observation SHALL be distinguished from state modification.

Observation SHALL NOT automatically authorize modification.

---

## 26. Resource Governance

Host operations SHALL remain subject to applicable resource constraints.

Resources MAY include:

- CPU;
- memory;
- storage;
- network bandwidth;
- process count;
- execution duration;
- file size;
- artifact size;
- device usage;
- API/tool calls.

Security-critical limits SHALL be externally enforced where required.

Resource exhaustion SHALL fail safely.

---

## 27. Security State

The Host Harness SHALL consider applicable security state before consequential operations.

Security state MAY include:

- policy state;
- authorization state;
- revocation state;
- sandbox state;
- host integrity state;
- network security state;
- credential state;
- emergency-control state.

Unknown security-relevant state SHALL fail closed where required.

---

## 28. Universal Computer Boundary

The Host Harness SHALL remain subordinate to the Universal Computer architecture.

The conceptual operation path SHALL remain:

**Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Host Operation → Verification → Provenance**

The Host Harness SHALL NOT use direct host commands as an alternate Universal Computer authorization mechanism.

---

## 29. Unsupported Capability Handling

Unsupported, unavailable, ambiguous, or incompatible host capabilities SHALL be handled explicitly.

The Host Harness SHALL NOT silently substitute an unauthorized capability.

Unsupported operations SHALL fail closed where required.

The failure SHALL be observable and attributable.

---

## 30. Host Operation Verification

Consequential host operations SHALL have independent verification appropriate to risk.

Verification MAY examine:

- resulting host state;
- process state;
- filesystem state;
- service state;
- application state;
- device state;
- network state;
- operation result;
- expected effect.

Agent or model claims SHALL NOT by themselves establish successful host execution.

---

## 31. Provenance and Audit

Host operations SHALL integrate with causal provenance.

Applicable provenance SHALL preserve:

- initiating principal;
- task;
- agent;
- delegation;
- capability;
- tool;
- execution admission;
- host adapter;
- concrete host operation;
- verification;
- outcome.

Audit records SHALL be appropriately integrity protected.

---

## 32. Observability

Host Harness activity SHALL provide appropriate operational and security telemetry.

Observability SHALL support:

- host discovery;
- capability discovery;
- adapter selection;
- authorization decisions;
- host operations;
- failures;
- resource usage;
- security events;
- verification results;
- recovery;
- emergency actions.

Observability SHALL NOT itself grant authority.

---

## 33. Failure Handling

Host Harness failures SHALL fail safely.

Applicable failures include:

- host unavailable;
- adapter unavailable;
- unsupported capability;
- authorization failure;
- policy conflict;
- security-state ambiguity;
- resource exhaustion;
- host integrity failure;
- operation timeout;
- partial execution;
- dependency failure;
- verification failure.

Unknown security-relevant failures SHALL fail closed where required.

---

## 34. Emergency Controls

Emergency controls SHALL remain independent of the Host Harness and agent.

Applicable controls include:

- pause;
- cancellation;
- capability revocation;
- quarantine;
- isolation;
- host-operation blocking;
- termination;
- emergency stop.

The Host Harness SHALL NOT disable or bypass emergency controls.

---

## 35. Recovery and Revalidation

Recovery SHALL not restore host authority merely because a checkpoint contains prior host state.

Before consequential continuation, recovery SHALL revalidate applicable:

- principal;
- agent identity;
- task;
- delegated authority;
- capability;
- target;
- host environment;
- adapter;
- policy;
- resource limits;
- security state;
- revocation state;
- expiry state;
- dependency state.

Expired or revoked authority SHALL remain invalid.

---

## 36. Partial and Uncertain Host Effects

Recovery SHALL account for partial or uncertain host effects.

Operations with uncertain outcomes SHALL require appropriate verification before retry.

Where applicable, the system SHOULD use:

- idempotency keys;
- operation identifiers;
- effect journals;
- deduplication;
- transaction boundaries;
- compensation mechanisms.

Irreversible external effects SHALL NOT be repeated blindly.

---

## 37. Host Isolation and Boundary Protection

Host integration SHALL preserve isolation between:

- agents;
- tasks;
- sessions;
- tenants where applicable;
- applications;
- host resources;
- credentials;
- security domains.

The Host Harness SHALL NOT expose unrelated host state merely because an agent is executing on the host.

---

## 38. External and Application Integration

External applications, protocols, devices, and services SHALL enter through defined integration boundaries.

Applicable integrations SHALL preserve:

- identity;
- trust;
- policy;
- capability authorization;
- execution admission;
- host mediation;
- verification;
- provenance.

MCP, A2A, application APIs, desktop interfaces, and device interfaces SHALL NOT create alternate privileged paths.

---

## 39. Security Invariants

The following invariants SHALL hold:

1. Host identity SHALL remain distinct from principal and agent identity.
2. Host discovery SHALL NOT grant execution authority.
3. Capability discovery SHALL NOT grant authorization.
4. Host mapping SHALL NOT enlarge authority.
5. Adapter selection SHALL NOT bypass authorization.
6. Host Harness SHALL NOT become an independent security authority.
7. Host Harness SHALL NOT provide unrestricted host access.
8. Consequential host operations SHALL remain explicitly scoped.
9. Host operations SHALL pass through the established execution chain.
10. LHICF SHALL remain the controlled host-integration boundary.
11. Unsupported operations SHALL fail closed where required.
12. Filesystem access SHALL remain explicitly scoped.
13. Process access SHALL remain explicitly scoped.
14. Service operations SHALL remain explicitly scoped.
15. Network access SHALL remain explicitly scoped.
16. Application interaction SHALL remain explicitly scoped.
17. Device access SHALL remain explicitly scoped.
18. Clipboard operations SHALL remain controlled data-transfer operations.
19. Agent or model claims SHALL NOT establish successful host execution.
20. Recovery SHALL revalidate authority and capability before consequential continuation.
21. Expired authority SHALL remain invalid.
22. Revoked authority SHALL remain invalid.
23. Emergency controls SHALL remain independent.
24. The Host Harness SHALL NOT create an alternate privileged path.
25. Host operations SHALL retain provenance and auditability.

---

## 40. Validation Requirements

Validation SHALL verify, as applicable:

- host identity;
- host discovery;
- capability discovery;
- capability mapping;
- adapter selection;
- adapter authorization;
- filesystem mediation;
- process mediation;
- service mediation;
- network mediation;
- application mediation;
- desktop mediation;
- device mediation;
- clipboard mediation;
- notification mediation;
- OS-state mediation;
- resource enforcement;
- unsupported capability handling;
- fail-closed behavior;
- Universal Computer boundary;
- LHICF boundary;
- host isolation;
- verification;
- provenance;
- recovery;
- emergency controls.

Negative tests SHALL attempt:

- unauthorized host access;
- capability escalation;
- adapter bypass;
- Aegis bypass;
- Capability Gateway bypass;
- Secure Executor bypass;
- Sandbox bypass;
- LHICF bypass;
- arbitrary shell access;
- cross-task host access;
- cross-application access;
- credential exposure;
- network egress abuse;
- replay;
- stale authority after recovery.

---

## 41. Security Testing

Security testing SHALL address applicable:

- host boundary bypass;
- filesystem traversal;
- unauthorized process control;
- unauthorized service control;
- network abuse;
- application impersonation;
- device abuse;
- clipboard exfiltration;
- notification abuse;
- OS-state manipulation;
- sandbox escape;
- host abuse;
- privilege escalation;
- capability escalation;
- adapter compromise;
- malicious external integration;
- stale authority;
- replay;
- provenance manipulation.

LHICF SHALL be tested as the controlled host-integration boundary.

Arbitrary shell access SHALL NOT constitute Universal Computer authorization.

---

## 42. Cross-Document Dependencies

PB-DOC-006 depends upon and SHALL remain consistent with:

- Unified Core Requirements PRD;
- Unified Core Architecture;
- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Agentic Runtime Specification;
- Identity and Authority Specification;
- Capability Model Specification;
- Agent Harness Specification;
- Validation Specification;
- Security Testing Specification;
- Operations Specification;
- Recovery and Resilience Specification;
- Universal Computer Architecture;
- Application Harness Architecture;
- LHICF architecture;
- Phase-B Master Manifest.

Conflicts SHALL be resolved through the applicable architecture and governance process.

---

## 43. Governance Boundary

This specification defines an architectural and documentation baseline.

It SHALL NOT by itself authorize:

- implementation;
- privileged host access;
- production deployment;
- unrestricted host control;
- autonomous privileged execution;
- production certification.

Architecture Approval remains governed by the Phase-B Architecture Approval Gate.

Implementation Authorization SHALL remain a separate governance decision.

---

## 44. Acceptance Criteria

PB-DOC-006 SHALL be considered structurally acceptable only when:

- required metadata is valid;
- all required sections are present;
- Host Harness responsibilities are explicit;
- host discovery is defined;
- capability mapping is defined;
- adapter selection is defined;
- host-operation boundaries are defined;
- filesystem/process/service/network mediation is defined;
- application/device/desktop mediation is defined;
- clipboard/notification/OS-state mediation is defined;
- LHICF boundary is explicit;
- Universal Computer boundary is explicit;
- fail-closed behavior is defined;
- verification is defined;
- provenance is defined;
- recovery is defined;
- security invariants are defined;
- validation requirements are defined;
- cross-document dependencies are recorded;
- governance state remains accurate.

Semantic acceptance additionally requires reconciliation against applicable architecture and security specifications.

---

## 45. Semantic Reconciliation

PB-DOC-006 SHALL be reconciled against:

- CORE-HOST-001 through CORE-HOST-003;
- CORE-EXEC-001 through CORE-EXEC-006;
- Core Architecture;
- Phase-B Architecture Baseline;
- Capability Model;
- Agent Harness;
- Identity and Authority;
- Security Architecture;
- Validation Specification;
- Security Testing Specification;
- Recovery and Resilience Specification;
- Universal Computer architecture;
- LHICF architecture.

Reconciliation SHALL verify that no Host Harness responsibility creates:

- alternate authority;
- alternate authorization;
- alternate privileged execution;
- unrestricted host access;
- unsupported-capability ambiguity;
- recovery-based authority restoration.

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

Any implementation SHALL preserve the documented Host Harness, LHICF, Universal Computer, security and execution boundaries.

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

- host authority;
- host capabilities;
- filesystem access;
- process access;
- service access;
- network access;
- application integration;
- device access;
- LHICF;
- Universal Computer;
- resource governance;
- security boundaries;
- recovery;
- verification

SHALL undergo appropriate architecture and security review.

Validated artifacts SHALL be preserved according to LYRION documentation governance.

---

## 49. Final Host Harness Invariant

The final invariant is:

**Host Environment ≠ Host Capability ≠ Host Authority ≠ Host Authorization ≠ Host Execution**

and:

**Host Harness ≠ Aegis ≠ Capability Gateway ≠ Secure Executor ≠ Sandbox ≠ LHICF**

The Host Harness SHALL remain a controlled host-environment integration boundary.

It SHALL NOT become an independent security authority, authorization authority, or privileged execution path.

The canonical host execution path remains:

**Human Intent → Lyri Interpretation → Task → Agent → Delegated Authority → Aegis → Capability Authorization → Execution Admission → Secure Executor → Agent Sandbox → LHICF → Host Adapter → Host Operation → Independent Verification → Memory / Audit / Provenance → Lyri → Human**

---

**End of PB-DOC-006 — Host Harness Specification v1.0.0**

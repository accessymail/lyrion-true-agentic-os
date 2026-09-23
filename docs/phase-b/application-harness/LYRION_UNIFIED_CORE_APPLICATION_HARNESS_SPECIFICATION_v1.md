# LYRION Unified Core — Application Harness Specification

**Document ID:** TAOS-CORE-APPLICATION-HARNESS-001  
**Version:** 1.0.0  
**Date:** 2026-09-22  
**Status:** DRAFT — APPLICATION HARNESS BASELINE  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED  

---

## 1. Purpose

This specification defines the Application Harness boundary for LYRION True Agentic OS.

The Application Harness SHALL provide governed application discovery, identification, capability discovery, interaction, verification, and provenance where applicable.

The Application Harness SHALL operate as an application-integration boundary and SHALL NOT become an independent security authority, authorization authority, or privileged execution mechanism.

---

## 2. Scope

This specification covers:

- application identity;
- application discovery;
- application identification;
- application capability discovery;
- application state;
- application capability binding;
- authority mapping;
- authorization boundaries;
- application targets and operations;
- application adapters;
- desktop and UI interaction;
- application APIs;
- MCP/A2A and external integrations;
- credential and data boundaries;
- resource governance;
- verification;
- provenance;
- observability;
- failure handling;
- recovery;
- emergency controls;
- validation and security testing.

This specification SHALL remain subordinate to the approved LYRION authority, capability, execution, host, and security architecture.

---

## 3. Source Hierarchy

The authoritative design sources are:

1. LYRION Unified Core Requirements PRD;
2. LYRION Unified Core Architecture;
3. Phase-B Architecture Baseline;
4. Existing Architecture Capability Baseline and TAOS Phase-B Reconciliation;
5. Phase-B Security Architecture;
6. Agentic Runtime Specification;
7. Identity and Authority Specification;
8. Capability Model Specification;
9. Agent Harness Specification;
10. Host Harness Specification;
11. Universal Computer Specification;
12. Core Validation Specification;
13. Security Testing Specification;
14. Recovery / Resilience Specification;
15. Data / Provenance architecture;
16. Observability architecture;
17. Phase-B Governance and Master Manifest artifacts.

Where a lower-level specification conflicts with an approved higher-level architecture, the conflict SHALL be resolved through formal architecture governance.

---

## 4. Architectural Principles

The Application Harness SHALL preserve:

- identity separation;
- authority separation;
- capability separation;
- explicit authorization;
- least privilege;
- deny-by-default privileged behavior;
- execution admission;
- sandboxing;
- host mediation;
- independent verification;
- provenance;
- auditability;
- fail-closed behavior;
- recovery revalidation;
- emergency control independence.

Application discovery SHALL NOT itself authorize application interaction.

Application capability discovery SHALL NOT itself grant authority.

Application adapters SHALL NOT become alternate authorization or privileged execution paths.

---

## 5. Application Harness Definition

The Application Harness is the governed LYRION component responsible for controlled interaction with applications and application environments.

Its responsibilities MAY include:

- application discovery;
- application identification;
- capability discovery;
- capability mapping;
- target identification;
- operation mapping;
- interaction;
- adapter selection;
- result handling;
- verification;
- provenance;
- audit integration;
- observability;
- failure handling;
- recovery coordination.

The Application Harness SHALL NOT directly establish authority.

---

## 6. Application Identity

Application identity SHALL remain distinct from:

- human identity;
- Lyri identity;
- session identity;
- task identity;
- agent identity;
- capability identity;
- authority identity;
- operation identity;
- host identity.

Application identity SHOULD identify the applicable:

- application;
- application instance;
- version;
- environment;
- integration endpoint;
- interface;
- adapter context.

Application identity SHALL NOT constitute execution authorization.

---

## 7. Application Context

Application context MAY include:

- application identity;
- version;
- instance;
- availability;
- lifecycle state;
- supported interfaces;
- supported capabilities;
- target information;
- security state;
- integration state;
- host/environment context.

Application context is descriptive and operational information.

Application context SHALL NOT be treated as authority merely because it is available to an agent or model.

---

## 8. Application Discovery

The Application Harness SHALL support governed application discovery where applicable.

Discovery MAY identify:

- installed applications;
- running applications;
- available application services;
- application interfaces;
- application APIs;
- desktop applications;
- supported interaction models;
- application capabilities.

Application discovery SHALL remain informational unless an independently authorized operation uses the discovered information.

---

## 9. Application Identification

Application identification SHALL distinguish:

- application;
- application instance;
- target;
- interface;
- adapter;
- operation.

The Application Harness SHALL NOT assume that discovering an application establishes permission to interact with it.

Ambiguous application identity SHALL result in controlled failure or additional identification requirements.

---

## 10. Application Capability Discovery

Application capability discovery MAY determine:

- supported operations;
- supported interfaces;
- application API capabilities;
- UI capabilities;
- device/application integration capabilities;
- supported targets;
- adapter capabilities.

Capability discovery SHALL NOT grant authorization.

Discovered capability information SHALL remain subject to capability authorization, policy, authority, resource, target, and security constraints.

---

## 11. Application Availability and State

The Application Harness SHALL distinguish application:

- availability;
- lifecycle state;
- operational state;
- target state;
- authorization state;
- security state.

Application availability SHALL NOT imply authorization.

Application state SHALL NOT override policy or authority.

---

## 12. Application Capability Model

Application capabilities SHALL represent bounded classes of application interaction.

Examples MAY include:

- read application state;
- query application data;
- invoke an approved application operation;
- modify an explicitly authorized resource;
- interact with an explicitly authorized UI target.

Capabilities SHALL remain scoped to applicable:

- principal;
- tenant;
- session;
- task;
- agent;
- application;
- target;
- operation;
- resource;
- policy;
- environment;
- time;
- approval;
- security state.

---

## 13. Application Capability Binding

Application capability binding SHALL preserve:

- principal;
- task;
- agent;
- delegated authority;
- capability;
- application;
- target;
- operation;
- scope;
- policy;
- resource constraints;
- time constraints;
- approval state;
- revocation state;
- provenance.

Capability binding SHALL NOT bypass Capability Authorization or Execution Admission.

---

## 14. Application Authority Mapping

Application authority SHALL be mapped from an independently established authority context.

Application mapping SHALL NOT:

- infer authority from application discovery;
- infer authority from model output;
- infer authority from agent intent;
- infer authority from application metadata;
- infer authority from tool metadata;
- infer authority from MCP/A2A messages;
- enlarge delegated authority.

Child or application-specific authority SHALL NOT exceed the applicable parent authority.

---

## 15. Application Authorization Boundary

Application interaction SHALL require applicable authorization.

Authorization SHALL evaluate applicable:

- principal;
- task;
- agent;
- delegated authority;
- capability;
- application;
- target;
- operation;
- policy;
- resource limits;
- approval state;
- security state;
- revocation state;
- expiry state.

The Application Harness SHALL NOT independently authorize privileged application operations.

Capability Authorization and the Capability Gateway SHALL remain authoritative for applicable execution admission.

---

## 16. Target Identification and Binding

Application targets SHALL be explicitly identified where required.

Targets MAY include:

- application instance;
- document;
- record;
- account;
- window;
- UI element;
- API resource;
- service endpoint;
- device;
- data object.

Target binding SHALL prevent unintended interaction with unrelated application resources.

Ambiguous targets SHALL fail closed where required.

---

## 17. Operation Identification and Binding

Each application operation SHALL have an attributable operation identity.

The operation SHOULD include, as applicable:

- operation identifier;
- principal;
- task;
- agent;
- delegated authority;
- capability;
- application;
- target;
- operation class;
- adapter;
- policy;
- resource constraints;
- approval state;
- provenance.

Application operation identity SHALL remain stable enough to support audit, verification, replay resistance, and recovery controls.

---

## 18. Application Adapter Model

Application adapters SHALL translate governed LYRION application operations into application-specific interaction mechanisms.

Adapters MAY support:

- application APIs;
- RPC interfaces;
- desktop interfaces;
- UI automation;
- service interfaces;
- structured application protocols;
- approved external application interfaces.

Adapters SHALL NOT become authorization authorities.

Adapters SHALL execute only operations admitted through the applicable LYRION execution boundary.

---

## 19. Adapter Discovery and Selection

Adapter discovery SHALL identify compatible application interaction mechanisms.

Adapter selection SHALL consider:

- application identity;
- application version;
- environment;
- capability;
- operation;
- target;
- security policy;
- authorization;
- resource constraints;
- verification requirements.

Adapter selection SHALL NOT enlarge authority.

An unavailable, incompatible, ambiguous, or untrusted adapter SHALL NOT be silently substituted.

---

## 20. Application Interaction Model

Application interaction SHALL remain:

- explicit;
- scoped;
- attributable;
- authorized;
- policy-bound;
- resource-bound;
- observable;
- auditable;
- verifiable.

The Application Harness SHALL NOT expose unrestricted application control merely because an application interface is technically accessible.

---

## 21. Universal Computer Relationship

The Application Harness SHALL remain subordinate to the Universal Computer architecture.

The conceptual operation path SHALL remain:

**Agent Intent  
→ Capability  
→ Authority  
→ Execution Admission  
→ Universal Computer Operation  
→ Host/Application Adapter  
→ Application Harness / Application Adapter  
→ Concrete Application Operation  
→ Independent Verification  
→ Provenance**

The Application Harness SHALL NOT establish a second Universal Computer authorization mechanism.

---

## 22. Host Harness Relationship

Application operations that require host interaction SHALL remain subject to the Host Harness and LHICF boundaries.

The Application Harness SHALL NOT bypass:

- Host Harness;
- LHICF;
- Agent Sandbox;
- Secure Executor;
- Capability Gateway;
- Aegis;
- independent verification.

Host-specific application operations SHALL use approved host/application adapters.

---

## 23. Capability Gateway Boundary

The Capability Gateway SHALL remain the authoritative execution-admission boundary.

Application Harness requests SHALL NOT bypass Capability Authorization or Capability Gateway authorization where applicable.

Failed authorization or admission checks SHALL NOT proceed into privileged execution.

The Application Harness SHALL NOT become an alternate Capability Gateway.

---

## 24. Secure Execution Boundary

The Secure Executor SHALL execute only operations already authorized and admitted.

The Application Harness SHALL provide controlled application-operation representations rather than independent privilege mechanisms.

The Application Harness SHALL NOT directly execute privileged operations outside the Secure Executor boundary.

---

## 25. Agent Sandbox Boundary

Application interaction SHALL execute within the applicable Agent Sandbox / execution boundary.

Sandbox controls SHALL be appropriate to risk and MAY include:

- filesystem isolation;
- process isolation;
- network isolation;
- credential isolation;
- environment isolation;
- resource limits;
- IPC restrictions;
- execution time limits.

Application interaction SHALL NOT escape sandbox controls to obtain additional authority.

---

## 26. LHICF Boundary

Where application interaction requires host integration, the canonical boundary SHALL remain:

**Aegis  
→ Capability Gateway  
→ Secure Executor  
→ Agent Sandbox  
→ LHICF  
→ Host/Application Adapter  
→ Application**

LHICF SHALL remain the controlled host-integration mediation boundary.

The Application Harness SHALL NOT bypass LHICF where host integration is applicable.

---

## 27. Desktop and UI Interaction

Desktop and UI interaction SHALL remain explicitly scoped.

UI interaction MAY include:

- application launch where authorized;
- window interaction;
- UI element interaction;
- controlled text input;
- controlled selection;
- controlled navigation;
- approved visual state inspection.

Desktop automation SHALL NOT itself constitute authorization.

UI accessibility or visibility SHALL NOT be treated as permission to access unrelated data or operations.

---

## 28. Application API Interaction

Application APIs SHALL be treated as controlled integration interfaces.

API access SHALL preserve:

- identity;
- authority;
- capability;
- authorization;
- target;
- operation;
- policy;
- resource constraints;
- verification;
- provenance.

API availability SHALL NOT imply authorization.

Application APIs SHALL NOT create alternate privileged paths.

---

## 29. MCP, A2A, and External Integration

MCP, A2A, APIs, tools, external services, and application protocols MAY provide:

- requests;
- capability information;
- application metadata;
- operation results.

They SHALL NOT independently grant LYRION authorization.

External application requests SHALL enter the applicable:

**Identity → Authority → Policy → Capability → Capability Authorization → Execution Admission → Secure Execution → Verification → Provenance**

boundary.

External integration SHALL preserve attribution and provenance.

---

## 30. Data and Credential Boundary

Application interactions SHALL protect:

- application data;
- credentials;
- authentication material;
- session tokens;
- secrets;
- sensitive application state;
- private user data.

Application Harness SHALL NOT expose unrelated application or host state merely because the agent has access to the application environment.

Credentials SHALL NOT be treated as ordinary application data.

Secret access SHALL remain governed by applicable credential and security controls.

---

## 31. Resource Governance

Application operations SHALL remain subject to applicable resource limits.

Resource controls MAY include:

- CPU;
- memory;
- storage;
- network;
- execution time;
- tool calls;
- process count;
- application interaction count;
- data volume;
- egress;
- artifacts;
- retries.

Security-critical limits SHALL NOT depend solely on model instructions.

---

## 32. Verification

Consequential application operations SHALL have independent verification appropriate to risk.

Verification MAY examine:

- resulting application state;
- target state;
- data state;
- UI state;
- API response;
- application process state;
- host state;
- external side effects.

Agent or model claims SHALL NOT by themselves establish successful application execution.

---

## 33. Provenance and Audit

Application operations SHALL retain applicable provenance.

Provenance SHOULD establish:

**Human / Principal  
→ Task  
→ Agent  
→ Delegation  
→ Capability  
→ Authorization  
→ Application  
→ Target  
→ Operation  
→ Adapter  
→ Execution  
→ Verification  
→ Outcome**

Application interaction SHALL remain attributable and auditable.

---

## 34. Observability

Application Harness operations SHALL support appropriate observability.

Observability MAY include:

- operation identifiers;
- application identifiers;
- target identifiers;
- adapter selection;
- authorization decision reference;
- execution state;
- resource consumption;
- verification result;
- failures;
- provenance references.

Observability data SHALL NOT itself grant authority.

Sensitive application data SHALL be handled according to applicable data-security controls.

---

## 35. Failure and Fail-Closed Behavior

Application interaction SHALL fail closed where required when:

- authorization fails;
- capability is unavailable;
- target is ambiguous;
- application identity is uncertain;
- adapter is unavailable or untrusted;
- policy evaluation fails;
- security state is invalid;
- approval is missing;
- authority is expired;
- authority is revoked;
- required verification cannot be established.

The Application Harness SHALL NOT silently substitute an unauthorized operation.

Failures SHALL be observable and attributable.

---

## 36. Partial and Uncertain Application Effects

Application operations MAY produce:

- partial effects;
- delayed effects;
- uncertain effects;
- duplicate effects;
- externally observable effects.

The Application Harness SHALL distinguish:

- requested operation;
- admitted operation;
- attempted operation;
- observed operation;
- verified outcome.

Where consequential effects are uncertain, the system SHALL avoid falsely reporting success.

Idempotency, compensation, reconciliation, or additional verification SHALL be used where applicable.

---

## 37. Emergency Controls

Emergency controls SHALL remain independent of the Application Harness, agent, model, or application.

Emergency controls MAY:

- pause;
- revoke;
- quarantine;
- isolate;
- disconnect;
- terminate;
- prevent further execution.

The Application Harness SHALL NOT modify, disable, or bypass emergency controls.

---

## 38. Recovery and Revalidation

Recovery SHALL revalidate applicable:

- principal identity;
- agent identity;
- task;
- delegated authority;
- capability;
- application identity;
- target;
- operation;
- policy;
- resource constraints;
- approval state;
- revocation state;
- expiry state;
- security state.

Persisted application-operation state SHALL NOT itself constitute current authority.

Expired or revoked authority SHALL NOT be restored merely because a checkpoint contains it.

Recovery SHALL fail closed when required validation cannot be established.

---

## 39. Security Invariants

The following invariants SHALL hold:

1. Application identity SHALL remain distinct from principal and agent identity.
2. Application discovery SHALL NOT grant authority.
3. Application capability discovery SHALL NOT grant authorization.
4. Application availability SHALL NOT grant authority.
5. Application state SHALL NOT override policy.
6. Application mapping SHALL NOT enlarge authority.
7. Adapter selection SHALL NOT bypass authorization.
8. Application Harness SHALL NOT become an independent security authority.
9. Application Harness SHALL NOT become an alternate authorization authority.
10. Application Harness SHALL NOT become an alternate privileged execution path.
11. Capability Authorization SHALL remain explicit.
12. Capability Gateway SHALL remain the execution-admission boundary.
13. Secure Executor SHALL execute only authorized operations.
14. Application interaction SHALL remain sandboxed where required.
15. LHICF SHALL remain the controlled host-integration boundary.
16. MCP/A2A/API messages SHALL NOT independently grant authorization.
17. Model output SHALL NOT constitute authorization.
18. Agent intent SHALL NOT constitute authorization.
19. Application metadata SHALL NOT constitute authorization.
20. Unsupported or ambiguous operations SHALL fail closed where required.
21. Expired authority SHALL remain invalid.
22. Revoked authority SHALL remain invalid.
23. Recovery SHALL NOT expand authority.
24. Consequential application operations SHALL be independently verifiable.
25. Application operations SHALL retain provenance and auditability.
26. Emergency controls SHALL remain independent.
27. No alternate privileged path SHALL be introduced.

---

## 40. Validation Requirements

Validation SHALL verify, as applicable:

- application identity;
- application discovery;
- application identification;
- application capability discovery;
- capability mapping;
- authority mapping;
- authorization;
- target binding;
- operation binding;
- adapter discovery;
- adapter selection;
- desktop/UI mediation;
- application API mediation;
- MCP/A2A integration;
- data and credential protection;
- resource enforcement;
- unsupported capability handling;
- fail-closed behavior;
- Universal Computer boundary;
- Host Harness boundary;
- Capability Gateway boundary;
- Secure Executor boundary;
- Agent Sandbox boundary;
- LHICF boundary;
- verification;
- provenance;
- observability;
- recovery;
- emergency controls.

Negative tests SHALL attempt:

- unauthorized application access;
- capability escalation;
- adapter bypass;
- Aegis bypass;
- Capability Gateway bypass;
- Secure Executor bypass;
- Sandbox bypass;
- LHICF bypass;
- application discovery-to-authority escalation;
- MCP/A2A authorization bypass;
- API authorization bypass;
- cross-task application access;
- cross-application access;
- credential exposure;
- unauthorized data access;
- replay;
- stale authority after recovery;
- false success reporting.

---

## 41. Security Testing

Security testing SHALL cover applicable threats including:

- application impersonation;
- malicious application adapters;
- compromised application interfaces;
- API abuse;
- desktop/UI manipulation;
- MCP/A2A abuse;
- confused deputy behavior;
- capability escalation;
- authorization bypass;
- credential exposure;
- data exfiltration;
- cross-application leakage;
- cross-task leakage;
- replay;
- stale authority;
- malicious external integration;
- adapter compromise;
- provenance manipulation.

Application integration SHALL be tested as a security boundary.

---

## 42. Cross-Document Dependencies

PB-DOC-008 SHALL remain consistent with:

- Unified Core Requirements PRD;
- Unified Core Architecture;
- Phase-B Architecture Baseline;
- Phase-B Security Architecture;
- Agentic Runtime Specification;
- Identity and Authority Specification;
- Capability Model Specification;
- Agent Harness Specification;
- Host Harness Specification;
- Universal Computer Specification;
- Core Validation Specification;
- Security Testing Specification;
- Operations Specification;
- Recovery and Resilience Specification;
- Data Architecture;
- Provenance architecture;
- Observability architecture;
- LHICF architecture;
- Phase-B Master Manifest.

Conflicts SHALL be resolved through the applicable architecture and governance process.

---

## 43. Governance Boundary

This specification defines an architectural and documentation baseline.

It SHALL NOT by itself authorize:

- implementation;
- privileged application access;
- privileged host access;
- production deployment;
- unrestricted application control;
- autonomous privileged execution;
- production certification.

Architecture Approval remains governed by the Phase-B Architecture Approval Gate.

Implementation Authorization SHALL remain a separate governance decision.

Production Implementation SHALL remain BLOCKED until applicable gates are satisfied.

Production Certification SHALL remain NOT CLAIMED.

---

## 44. Acceptance Criteria

Structural acceptance requires that:

- application identity is defined;
- application discovery is defined;
- capability discovery is defined;
- authorization boundaries are explicit;
- target binding is defined;
- operation binding is defined;
- adapter model is defined;
- desktop/UI interaction is bounded;
- API interaction is bounded;
- MCP/A2A integration is bounded;
- data and credential boundaries are defined;
- Capability Gateway boundary is explicit;
- Secure Executor boundary is explicit;
- Sandbox boundary is explicit;
- LHICF boundary is explicit;
- Universal Computer relationship is explicit;
- verification is defined;
- provenance is defined;
- recovery is defined;
- security invariants are defined;
- validation requirements are defined;
- security testing requirements are defined;
- cross-document dependencies are recorded;
- governance state is accurate.

Semantic acceptance additionally requires reconciliation against applicable architecture and security specifications.

---

## 45. Semantic Reconciliation

PB-DOC-008 SHALL be reconciled against:

- Core PRD;
- Core Architecture;
- Phase-B Architecture Baseline;
- Existing Capability Baseline;
- Security Architecture;
- Identity and Authority;
- Capability Model;
- Agent Harness;
- Host Harness;
- Universal Computer;
- Validation;
- Security Testing;
- Recovery;
- Data Architecture;
- Provenance;
- Observability;
- LHICF architecture.

Reconciliation SHALL verify that no Application Harness responsibility creates:

- alternate authority;
- alternate authorization;
- alternate privileged execution;
- unrestricted application access;
- unauthorized capability expansion;
- unsupported-capability ambiguity;
- recovery-based authority restoration;
- provenance loss.

The semantic reconciliation confirms that PB-DOC-008 preserves the established
Universal Computer, Host Harness, security, authorization, execution, verification,
and provenance boundaries.

Capability-to-operation mapping and authority preservation remain governed by the
Universal Computer architecture and are not redefined by the Application Harness.
Host operation remains governed by the Host Harness and LHICF boundaries, while
PB-DOC-008 uses application-specific operation terminology at the application
boundary.

The Application Harness therefore does not introduce an alternate authority,
authorization, execution, host-control, or Universal Computer mechanism.

No semantic conflict was identified during the documented reconciliation precheck.

No semantic conflict SHALL be accepted without formal architecture review and resolution.

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

Any implementation SHALL preserve:

- identity;
- authority;
- capability;
- authorization;
- Aegis;
- Capability Gateway;
- Execution Admission;
- Secure Executor;
- Agent Sandbox;
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

**Structural Validation:** PASS  
**Semantic Reconciliation:** RECONCILED  
**Architecture Approval:** PENDING  
**Implementation Authorization:** NOT AUTHORIZED  
**Production Implementation:** BLOCKED  
**Production Certification:** NOT CLAIMED

These states SHALL remain explicit until their corresponding gates are independently satisfied.

---

## 48. Governance and Change Control

Changes to this specification SHALL be controlled.

Changes affecting:

- application authority;
- application capabilities;
- application authorization;
- application APIs;
- desktop/UI interaction;
- application adapters;
- MCP/A2A integration;
- credentials;
- data boundaries;
- Universal Computer;
- Host Harness;
- LHICF;
- resource governance;
- security boundaries;
- recovery;
- verification;
- provenance

SHALL undergo appropriate architecture and security review.

Validated artifacts SHALL be preserved according to LYRION documentation governance.

---

## 49. Final Application Harness Invariant

The final invariant is:

**Application Identity ≠ Application Capability ≠ Application Authority ≠ Application Authorization ≠ Application Execution ≠ Application Verification**

and:

**Application Harness ≠ Aegis ≠ Capability Gateway ≠ Secure Executor ≠ Agent Sandbox ≠ LHICF**

The Application Harness SHALL remain a controlled application-environment integration boundary.

It SHALL NOT become an independent security authority, authorization authority, or privileged execution path.

The canonical governed application flow SHALL remain:

**Agent Intent  
→ Capability  
→ Authority  
→ Capability Authorization  
→ Execution Admission  
→ Universal Computer Operation  
→ Application Harness / Application Adapter  
→ Concrete Application Operation  
→ Independent Verification  
→ Provenance**


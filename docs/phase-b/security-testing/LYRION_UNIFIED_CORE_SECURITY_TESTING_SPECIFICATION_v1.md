# LYRION Unified Core Security Testing Specification

**Document ID:** TAOS-CORE-SEC-TEST-001
**Version:** 1.0.0
**Date:** 2026-09-22
**Status:** DRAFT — SECURITY TESTING BASELINE
**Architecture Approval:** PENDING
**Implementation Authorization:** NOT AUTHORIZED
**Production Certification:** NOT CLAIMED

---

## 1. Purpose

This specification defines the security-testing baseline for the LYRION Unified Core and establishes traceable methods for validating the security controls defined by the approved Phase-B security architecture.

It converts security architecture requirements into testable security properties, negative-path tests, adversarial tests, evidence requirements, and security acceptance gates.

This specification does not itself authorize implementation or production deployment.

---

## 2. Architectural Authority

This specification is subordinate to and shall remain consistent with:

1. LYRION Unified Core Requirements PRD.
2. LYRION Unified Core Architecture.
3. LYRION Unified Core Data Architecture.
4. LYRION Unified Core Memory / Provenance Specification.
5. LYRION Unified Core Observability Specification.
6. LYRION True Agentic OS Phase-B Security Architecture.
7. LYRION Unified Core Validation Specification.
8. Existing validated LYRION security and execution architecture where retained by the Phase-B reconciliation baseline.

The governing architectural principle is:

**PRESERVE → EXTEND → INTEGRATE → VALIDATE → REDESIGN ONLY WHEN REQUIRED**

---

## 3. Scope

Security testing SHALL cover the Unified Core security boundary and all security-relevant interfaces between:

Human → Identity → Lyri → Task → Cognitive Runtime → Agent Control Plane → Delegated Authority → Aegis → Capability Gateway → Secure Executor → Sandbox → LHICF → Host/Application/Device → Verification → Memory/Provenance → Observability.

Testing SHALL include:

- preventive controls;
- detective controls;
- containment controls;
- recovery controls;
- fail-closed behavior;
- authorization boundaries;
- identity boundaries;
- data boundaries;
- execution boundaries;
- evidence boundaries.

---

## 4. Security Testing Authority Principle

Security testing SHALL distinguish:

- architectural intent;
- implemented control;
- test execution;
- test evidence;
- security acceptance;
- production certification.

A documented security control is not considered implemented merely because it exists in architecture documentation.

A passing test SHALL establish only the property actually tested.

No test result SHALL be interpreted as evidence of universal security.

---

## 5. Security Status Model

Security testing SHALL use the following state distinctions:

- NOT SPECIFIED
- SPECIFIED
- IMPLEMENTED
- TESTED
- TESTED WITH FINDINGS
- VALIDATED
- SECURITY ACCEPTED
- PRODUCTION OPERATIONAL
- CERTIFIED

These states SHALL NOT be collapsed.

---

## 6. Security Test Categories

Security testing SHALL include, where applicable:

1. Static security validation.
2. Unit security tests.
3. Integration security tests.
4. Interface/contract security tests.
5. End-to-end security tests.
6. Negative-path tests.
7. Fail-closed tests.
8. Adversarial tests.
9. Fuzz testing.
10. Isolation testing.
11. Abuse-case testing.
12. Resource-exhaustion testing.
13. Recovery testing.
14. Real-infrastructure security testing.
15. Operational security exercises.
16. Independent security assurance.

---

## 7. Threat Coverage

Testing SHALL address at minimum:

- prompt injection;
- indirect prompt injection;
- goal hijacking;
- tool/skill poisoning;
- model/provider compromise;
- memory/retrieval poisoning;
- agent impersonation;
- confused deputy;
- privilege escalation;
- delegation abuse;
- replay;
- inter-agent tampering;
- cross-task leakage;
- cross-tenant leakage;
- credential exposure;
- secret exposure;
- data exfiltration;
- arbitrary code execution;
- sandbox escape;
- host abuse;
- network abuse;
- recursive runaway;
- resource exhaustion;
- cascading failure;
- HITL manipulation;
- stale authority after recovery;
- supply-chain compromise;
- malicious MCP/A2A integration.

---

## 8. Identity Security Testing

Tests SHALL verify that:

- human identity is distinct from agent identity;
- agent identity is distinct from model/provider identity;
- session identity is distinct from task identity;
- task identity is distinct from capability identity;
- identity cannot be substituted through model output;
- unauthenticated principals cannot obtain protected authority;
- terminated identities cannot continue executing;
- identity transitions are auditable;
- identity context survives only where explicitly authorized.

Negative tests SHALL include forged, missing, expired, revoked, substituted, and replayed identity contexts.

---

## 9. Authentication Testing

Authentication controls SHALL be tested for:

- valid authentication;
- invalid authentication;
- expired authentication;
- revoked authentication;
- replay;
- credential substitution;
- session fixation;
- session confusion;
- authentication-context loss;
- authentication downgrade;
- authentication bypass.

Authentication failure SHALL fail closed.

---

## 10. Authorization Testing

Authorization testing SHALL verify:

- least privilege;
- deny-by-default behavior;
- task-bound authorization;
- agent-bound authorization;
- capability-scoped authorization;
- target-bound authorization;
- time-bound authorization;
- revocation;
- policy-version binding;
- authority attenuation.

Model output SHALL never constitute authorization.

---

## 11. Delegated Authority Testing

Delegated authority SHALL be tested for:

- parent-child authority lineage;
- authority attenuation;
- capability scope;
- target scope;
- temporal scope;
- task scope;
- revocation;
- expiry;
- replay resistance;
- delegation-chain integrity;
- unauthorized privilege amplification.

A child authority SHALL never exceed its parent authority or applicable task authority.

Delegation SHALL NOT itself authorize execution.

---

## 12. Agent Control Plane Security Testing

The Agent Control Plane SHALL be tested for:

- unauthorized agent registration;
- identity collision;
- unauthorized discovery;
- lifecycle manipulation;
- unauthorized scheduling;
- routing manipulation;
- resource-budget bypass;
- state corruption;
- unauthorized recovery;
- termination bypass;
- audit suppression.

ACP SHALL not become an alternate privileged execution path.

---

## 13. Inter-Agent Security Testing

Tests SHALL verify:

- authenticated agent identity;
- message attribution;
- message integrity;
- replay protection;
- authorization of inter-agent communication;
- namespace isolation;
- task isolation;
- tenant isolation;
- sender authenticity;
- receiver authorization;
- malicious-agent containment.

An agent SHALL not be able to impersonate another agent.

---

## 14. Swarm Boundary Testing

Where swarm functionality is implemented, testing SHALL verify:

- maximum swarm depth;
- maximum swarm width;
- lineage preservation;
- authority attenuation;
- resource budgets;
- namespace isolation;
- communication authorization;
- cancellation;
- termination;
- emergency stop;
- recursive-spawn prevention.

Unbounded recursive agent creation SHALL fail closed.

Swarm functionality SHALL not be treated as a foundational requirement for Core completion.

---

## 15. Aegis Security Testing

Aegis SHALL be tested as an independent security and governance boundary.

Testing SHALL verify:

- policy evaluation;
- trust evaluation;
- risk evaluation;
- containment;
- deny behavior;
- policy-version binding;
- security telemetry;
- quarantine;
- emergency response;
- independence from model-generated authorization.

An agent SHALL not modify, disable, or bypass its own Aegis controls.

---

## 16. HITL Security Testing

HITL controls SHALL be tested for:

- authenticated human principal;
- approver eligibility;
- request-digest binding;
- policy-version binding;
- bounded expiry;
- self-approval protection;
- signed evidence;
- tamper rejection;
- rejection handling;
- revocation;
- single-use approval;
- replay protection;
- provenance;
- durable state;
- notification integrity where applicable.

HITL approval SHALL not create an alternate execution path.

---

## 17. Capability Gateway Testing

The Capability Gateway SHALL be tested as the execution-admission boundary.

Tests SHALL verify:

- capability discovery;
- capability authorization;
- target binding;
- authority binding;
- policy binding;
- deny-by-default;
- capability revocation;
- expired authority rejection;
- unauthorized capability rejection;
- capability escalation rejection.

Possession of a capability SHALL not imply unlimited authority.

---

## 18. Execution Admission Testing

Execution admission SHALL verify that an operation cannot proceed unless all applicable:

- identity;
- task;
- delegation;
- authority;
- policy;
- capability;
- target;
- resource;
- security;
- HITL

requirements have been satisfied.

Missing or inconsistent admission state SHALL fail closed.

---

## 19. Secure Executor Testing

Secure Executor testing SHALL verify:

- execution of only admitted operations;
- no privilege inference;
- no unauthorized command construction;
- argument validation;
- resource limits;
- timeout enforcement;
- cancellation;
- output containment;
- error handling;
- audit generation;
- provenance generation.

Secure Executor SHALL NOT create authorization that was absent at admission.

---

## 20. Sandbox Security Testing

Sandbox testing SHALL verify applicable:

- process isolation;
- filesystem isolation;
- network isolation;
- credential isolation;
- resource fencing;
- privilege separation;
- namespace separation;
- escape resistance;
- process-tree containment;
- termination;
- cleanup.

Adversarial sandbox-escape testing SHALL be required before applicable security acceptance.

---

## 21. LHICF Security Testing

LHICF SHALL be tested as the controlled host-integration boundary.

Testing SHALL verify:

- adapter authorization;
- host mapping;
- operation validation;
- capability mapping;
- fail-closed unsupported operations;
- host boundary enforcement;
- filesystem mediation;
- process mediation;
- service mediation;
- network mediation;
- application mediation;
- device mediation;
- clipboard mediation;
- notification mediation;
- OS-state mediation;
- provenance.

Arbitrary shell access SHALL NOT constitute Universal Computer authorization.

---

## 22. Universal Computer Security Testing

Universal Computer operations SHALL be tested through:

Agent Intent → Capability → Authority → Execution Admission → Universal Computer Operation → Host/Application Adapter → Concrete Host Operation → Verification → Provenance.

Tests SHALL verify:

- environment discovery;
- capability discovery;
- adapter selection;
- host mapping;
- application mapping;
- authority mapping;
- unsupported capability handling;
- fail-closed behavior;
- verification;
- provenance.

Universal Computer SHALL NOT bypass Aegis, Capability Gateway, Secure Executor, Sandbox, LHICF, HITL, or verification.

---

## 23. Application Harness Security Testing

Application Harness testing SHALL verify:

Discovery → Identification → Capability Discovery → Authorization → Interaction → Verification → Provenance.

Tests SHALL cover:

- application identity spoofing;
- unauthorized interaction;
- UI manipulation;
- stale application state;
- target confusion;
- cross-application boundary violations;
- unauthorized data transfer;
- verification failure.

Application Harness SHALL NOT bypass Capability Authorization,
Capability Gateway, Execution Admission, Secure Executor, Sandbox,
LHICF, or independent verification.

---

## 24. Prompt and Indirect Injection Testing

Tests SHALL attempt to cause unauthorized behavior through:

- direct prompt injection;
- retrieved-content injection;
- web-content injection;
- document injection;
- tool output injection;
- application content injection;
- memory-content injection;
- inter-agent message injection.

Security controls SHALL prevent model-generated instructions from becoming authority without passing the governing security chain.

---

## 25. Tool and Skill Poisoning Testing

Tests SHALL verify:

- tool identity;
- tool provenance;
- integrity;
- version;
- ownership;
- dependency integrity;
- capability scope;
- network scope;
- credential scope;
- malicious output handling;
- tool replacement detection.

Untrusted tools SHALL not silently become trusted execution components.

---

## 26. Memory and RMA Security Testing

Memory testing SHALL verify:

- principal scope;
- tenant scope;
- session scope;
- task scope;
- agent scope;
- sensitivity scope;
- provenance;
- trust;
- confidence;
- validation;
- conflict detection;
- supersession;
- expiration;
- revocation;
- deletion;
- integrity;
- versioning;
- auditability.

Model-generated content SHALL not become trusted durable memory solely because a model generated it.

RMA SHALL remain distinct from RLM reasoning.

---

## 27. RLM Security Testing

RLM testing SHALL verify:

- bounded recursion;
- recursion depth limits;
- call budgets;
- tool budgets;
- token/context budgets;
- time limits;
- compute limits;
- memory limits;
- egress limits;
- artifact limits;
- retry limits;
- isolation.

RLM SHALL NOT:

- grant capabilities;
- modify policy;
- bypass Aegis;
- bypass Capability Gateway;
- access protected secrets without authorization;
- obtain privileged execution;
- create unrestricted agents;
- directly control the host.

RLM output SHALL be treated as reasoning/evidence, not authorization.

---

## 28. Credential and Secret Security Testing

Testing SHALL verify:

- secret isolation;
- least privilege;
- credential scope;
- credential lifetime;
- secret redaction;
- unauthorized retrieval rejection;
- logging protection;
- memory protection;
- tool-output protection;
- environment isolation;
- exfiltration resistance.

Secrets SHALL NOT be exposed through model context merely because a task requests them.

---

## 29. Data and Tenant Isolation Testing

Testing SHALL verify that data cannot cross unauthorized:

- principal;
- tenant;
- session;
- task;
- agent;
- project;
- sensitivity

boundaries.

Cross-boundary retrieval SHALL fail closed.

Derived indexes and caches SHALL respect the same authorization boundary as authoritative data.

---

## 30. Network and Egress Security Testing

Testing SHALL verify:

- destination authorization;
- protocol restrictions;
- egress policy;
- DNS/control-plane restrictions where applicable;
- credential isolation;
- network namespace isolation;
- unauthorized external communication rejection;
- data-exfiltration resistance;
- resource limits.

Network access SHALL not be inferred from general task intent.

---

## 31. Resource Exhaustion Testing

Security testing SHALL include bounded abuse of:

- CPU;
- memory;
- storage;
- network;
- tokens;
- model calls;
- tool calls;
- retries;
- execution time;
- agent count;
- swarm depth;
- swarm width;
- artifacts;
- egress.

Security-critical limits SHALL be enforced outside model instructions.

---

## 32. Recovery Security Testing

Recovery SHALL revalidate:

- identity;
- task;
- policy;
- authority;
- delegation;
- capability;
- resources;
- target;
- security state.

Expired or revoked authority SHALL NOT be restored merely because it exists in a checkpoint.

Consequential external operations SHALL use appropriate idempotency or compensation controls.

---

## 33. Emergency Control Testing

Emergency controls SHALL be tested for:

- pause;
- revoke;
- quarantine;
- isolate;
- disconnect;
- terminate.

Tests SHALL verify that emergency controls remain effective when:

- the model is malfunctioning;
- an agent is compromised;
- a tool is malicious;
- a task is looping;
- a sandbox is under attack;
- external connectivity is hostile.

Agents SHALL NOT disable or modify their own emergency controls.

---

## 34. MCP and A2A Security Testing

MCP/A2A integrations SHALL be tested through the LYRION boundary:

Adapter → Identity/Trust → Policy → Capability Authorization → LYRION Execution Boundary.

Tests SHALL verify:

- endpoint identity;
- trust;
- authentication;
- authorization;
- capability scope;
- input validation;
- output validation;
- replay resistance;
- malicious-server behavior;
- data leakage;
- unauthorized execution.

External protocol participation SHALL NOT create self-authorized execution.

---

## 35. Supply-Chain Security Testing

Security testing SHALL verify applicable:

- source provenance;
- authenticity;
- integrity;
- ownership;
- dependency versions;
- vulnerability scanning;
- license compliance;
- build reproducibility;
- artifact integrity;
- dependency graph;
- network scope;
- credential scope;
- capability scope;
- approval;
- bounded deployment;
- monitoring;
- revalidation;
- revocation.

Research references SHALL NOT automatically become trusted runtime dependencies.

---

## 36. Observability and Provenance Security Testing

Testing SHALL verify:

- causal provenance;
- security telemetry;
- tamper evidence;
- evidence classification;
- access control;
- sensitive-data protection;
- execution-to-verification visibility;
- recovery visibility;
- emergency-control visibility;
- RMA/RLM separation;
- authoritative versus derived telemetry boundaries.

Security telemetry SHALL not itself become an uncontrolled data-exfiltration channel.

---

## 37. Negative-Path and Fail-Closed Testing

Every security-critical boundary SHALL include negative-path testing.

At minimum, tests SHALL cover:

- missing identity;
- invalid identity;
- missing authority;
- expired authority;
- revoked authority;
- wrong task;
- wrong agent;
- wrong capability;
- wrong target;
- wrong policy version;
- missing HITL approval;
- invalid HITL approval;
- replayed approval;
- insufficient resources;
- unavailable security control;
- unavailable verification;
- unavailable host adapter;
- corrupted state.

Security-critical failures SHALL fail closed unless an explicitly approved safe-degradation policy exists.

---

## 38. Adversarial Testing

Adversarial testing SHALL attempt to defeat the complete security chain rather than testing individual controls only.

Tests SHALL include chained attacks involving combinations of:

- injection;
- malicious memory;
- compromised tools;
- agent impersonation;
- delegated-authority abuse;
- capability escalation;
- sandbox escape;
- host abuse;
- data exfiltration;
- recovery abuse;
- emergency-control manipulation.

Successful exploitation of a boundary SHALL be recorded with attack path, evidence, affected controls, containment, remediation, and retest requirements.

---

## 39. Fuzz Testing

Applicable interfaces SHALL undergo fuzz testing for:

- IPC;
- serialization;
- protocol messages;
- capability requests;
- authority objects;
- delegation objects;
- tool inputs;
- host adapters;
- application adapters;
- parser boundaries;
- untrusted external data.

Fuzz failures SHALL produce reproducible evidence where feasible.

---

## 40. Real-Infrastructure Security Testing

Reference or simulated tests SHALL be distinguished from real-infrastructure tests.

Where a security property depends on:

- Linux kernel behavior;
- namespaces;
- filesystem permissions;
- process isolation;
- networking;
- containers;
- desktop integration;
- devices;
- external services;

the applicable real infrastructure SHALL be tested before claiming corresponding operational validation.

---

## 41. Evidence Requirements

Every security test result SHALL preserve, as applicable:

- test identifier;
- requirement/control identifier;
- test objective;
- environment;
- software version;
- configuration;
- test data;
- execution timestamp;
- executor identity;
- inputs;
- outputs;
- logs;
- artifacts;
- hashes;
- verdict;
- failure information;
- remediation;
- retest result.

Evidence SHALL be attributable, reproducible, integrity-protected, and appropriately access-controlled.

---

## 42. Evidence Classification

Security evidence SHALL distinguish:

- reference evidence;
- development evidence;
- simulated evidence;
- local validation evidence;
- real-infrastructure evidence;
- adversarial evidence;
- operational evidence;
- independent assurance evidence;
- acceptance evidence;
- certification evidence.

Historical evidence SHALL NOT be silently represented as current evidence.

---

## 43. Security Test Traceability

Every security test SHALL map to one or more of:

- PRD requirement;
- CORE-SEC-001..010 security requirements;
- TR-009 security-testing traceability requirement;
- architecture control;
- security control;
- threat;
- capability;
- execution boundary;
- data boundary;
- validation gate;
- acceptance criterion.

Unmapped security tests SHALL be classified as exploratory or research tests rather than silently treated as acceptance evidence.

---

## 44. Security Acceptance Gates

Security acceptance SHALL require applicable completion of:

**Gate S1 — Security Test Planning**

Threats, controls, test methods, environments, and evidence requirements defined.

**Gate S2 — Control Validation**

Applicable security controls implemented and tested.

**Gate S3 — Negative-Path Validation**

Critical deny and fail-closed paths validated.

**Gate S4 — Adversarial Validation**

Applicable attack paths tested.

**Gate S5 — Isolation Validation**

Applicable sandbox, host, data, tenant, and credential boundaries validated.

**Gate S6 — Recovery and Emergency Validation**

Recovery and emergency controls validated.

**Gate S7 — Real-Infrastructure Validation**

Applicable infrastructure-dependent controls validated on real infrastructure.

**Gate S8 — Evidence Review**

Security evidence is complete, attributable, reproducible, and integrity-protected.

**Gate S9 — Security Acceptance**

Findings are dispositioned and applicable security acceptance is formally recorded.

**Gate S10 — Production Security Readiness**

Production security readiness is evaluated separately from architecture approval and implementation authorization.

---

## 45. Security Finding Classification

Findings SHALL be classified according to impact and exploitability using the project's approved risk methodology.

Each finding SHALL include:

- identifier;
- affected component;
- threat;
- attack path;
- affected boundary;
- evidence;
- severity;
- exploitability;
- impact;
- containment;
- remediation;
- owner;
- status;
- retest requirement.

No finding SHALL be silently discarded because a test subsequently passes.

---

## 46. Regression and Retesting

Security controls SHALL be retested after:

- security-sensitive code changes;
- authority-model changes;
- capability changes;
- sandbox changes;
- host-integration changes;
- protocol changes;
- dependency changes;
- model/provider changes where security-relevant;
- memory architecture changes;
- policy changes;
- recovery changes.

Security regression suites SHALL be versioned and reproducible.

---

## 47. Security Testing and Production Certification Boundary

Passing security tests SHALL NOT by itself establish production certification.

Production certification additionally requires the applicable:

- implementation evidence;
- real-infrastructure evidence;
- operational evidence;
- security acceptance;
- independent assurance where required;
- governance approval;
- certification authority decision.

This specification SHALL NOT be interpreted as a production certification statement.

---

## 48. G47 Historical Evidence Boundary

Existing G47 evidence SHALL remain explicitly classified as historical evidence unless independently revalidated for the current architecture and environment.

G47 evidence SHALL NOT be used to claim that newly introduced Phase-B security controls are currently implemented or validated.

The current G47 certification boundary remains unchanged.

---

## 49. Security Testing Governance State

At this baseline:

**Security Testing Specification:** DRAFT — SECURITY TESTING BASELINE

Architecture Approval: PENDING
Implementation Authorization: NOT AUTHORIZED
Production Implementation: BLOCKED

**Architecture Approval:** PENDING

**Implementation Authorization:** NOT AUTHORIZED

**Production Implementation:** BLOCKED

**Production Certification:** NOT CLAIMED

---

## 50. Acceptance Criteria

PB-DOC-017 may be considered baseline-validated only when:

1. The specification exists at the canonical path.
2. Required security-testing domains are covered.
3. Security architecture controls are traceable.
4. Threat families are covered.
5. Negative-path and fail-closed testing are defined.
6. Adversarial testing is defined.
7. Real-infrastructure boundaries are defined.
8. Evidence requirements are defined.
9. Security acceptance gates are defined.
10. Production certification remains explicitly separated.
11. G47 historical evidence remains separated from current evidence.
12. Governance remains PENDING / NOT AUTHORIZED / BLOCKED.
13. Structural and semantic validation passes.
14. Cross-document consistency passes against the Core Architecture, Security Architecture, Core Validation Specification, Data Architecture, Memory / Provenance Specification, and Observability Specification.

---

## 51. Governing Principle

LYRION security SHALL be validated as a system of independently testable security boundaries rather than as a collection of isolated security features.

The governing execution security chain remains:

**Human Intent → Authenticated Principal → Lyri Interpretation → Task → Planning → Agent Delegation → Delegated Authority → Aegis → Capability Authorization → Execution Admission → Secure Executor → Sandbox → LHICF → Host/Application/Device → Independent Verification → Memory/Provenance → Observability → Human**

No model, agent, tool, memory object, RLM process, protocol adapter, recovery checkpoint, or external integration may create an alternate privileged execution path.

**End of Document**

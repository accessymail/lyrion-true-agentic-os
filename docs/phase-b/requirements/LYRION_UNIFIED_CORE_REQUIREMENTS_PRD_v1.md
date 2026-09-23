# LYRION True Agentic OS — Unified Core Requirements / PRD

**Document:** Unified Core Requirements / Product Requirements Document
**Document ID:** TAOS-CORE-PRD-001
**Version:** 1.0.0
**Status:** DRAFT — REQUIREMENTS BASELINE
**Project:** LYRION True Agentic OS
**Date:** 2026-09-22

---

## 1. Document Purpose

This document defines the normative requirements for the foundational
LYRION True Agentic OS Core.

The Core is the foundational integrated system upon which later
agentic, host, application, enterprise and expansion capabilities
shall be built.

This document converts the existing approved LYRION True Agentic OS
architecture into implementation-oriented, testable and traceable
requirements.

This document does not replace the canonical architecture.

---

## 2. Authority and Source Hierarchy

The Core PRD SHALL remain subordinate to the established LYRION
documentation source hierarchy.

Primary sources:

1. LYRION_True_Agentic_OS_Architecture.md
2. Lyrion_True_Agentic_OS_Manifest.md
3. Lyrion_True_Agentic_OS_Requirements.md
4. LYRION_TAOS_PLATFORM_BLUEPRINT.md
5. Security_Threat_Model_and_Controls.md
6. Implementation_Validation_Acceptance_Gates.md
7. Resource_Verification_and_Approval.md
8. RLM_Recursive_Language_Model_Integration.md
9. Recursive_Memory_Architecture.md
10. Memory_Database_Architecture.md
11. Intelligence_OS_to_True_Agentic_OS_Migration.md
12. Terminology_Status_and_NonFalseClaims.md
13. LYRION_True_Agentic_OS_Implementation_Gap_Register.md

The reconciliation baseline is the immediate Phase-B bridge between
the existing architecture and this Core PRD.

---

## 3. Requirement Status Model

Each requirement SHALL ultimately have a status such as:

- PROPOSED
- APPROVED
- IMPLEMENTED
- VALIDATED
- ACCEPTED
- DEFERRED
- BLOCKED
- SUPERSEDED

Requirement status SHALL NOT be inferred from documentation alone.

Architecture approval SHALL NOT be interpreted as implementation,
validation, acceptance or production certification.

---

## 4. Core Architectural Principle

LYRION SHALL preserve the following separation:

OBSERVATION
≠ OPPORTUNITY
≠ REASONING
≠ DECISION
≠ AGENCY
≠ AUTHORITY
≠ CAPABILITY
≠ EXECUTION
≠ VERIFICATION

No intelligence-layer output may directly become execution authority.

---

# 5. Core Scope

The foundational Core SHALL establish an integrated and governable
LYRION runtime containing, as applicable:

- Lyri
- Interaction
- HUI/FUI
- Application Runtime
- Voice foundations
- Perception
- Event / Context
- World State
- PIAE
- Cognitive Runtime
- Personality
- Affective / Social foundations
- Memory foundations
- Goal / Planning
- Aegis foundations
- HITL foundations
- Capability Gateway
- Secure Execution foundations
- required Agent Control foundations
- Observability
- Provenance
- Recovery foundations
- required Host Integration foundations

The final exact Core boundary SHALL be established by the approved
Core Architecture.

---

# 6. Core Non-Goals

The Core PRD does not authorize:

- unrestricted autonomous host control;
- unrestricted agent spawning;
- unrestricted recursive reasoning;
- model-controlled authorization;
- prompt-only security;
- unrestricted shell access;
- unrestricted MCP/A2A access;
- raw credentials in model context;
- bypassing Aegis;
- bypassing Capability Gateway;
- bypassing Secure Executor;
- bypassing Sandbox;
- bypassing LHICF;
- bypassing HITL where policy requires it;
- autonomous modification of security policy;
- autonomous disabling of emergency controls;
- production certification merely because Core tests pass.

---

# 7. System Actors

The Core SHALL distinguish at minimum:

- Human Principal
- Lyri
- Session
- Task
- Agent
- Model
- Tool
- Capability
- Authority Grant
- Execution
- Host
- Application
- Device
- External Service
- Governance / Security Components

Identity between these entities SHALL NOT be implicitly interchangeable.

---

# 8. Functional Requirements

## CORE-FR-001 — Human Interaction

The system SHALL accept supported human interaction through defined
interaction interfaces.

Supported modalities MAY include:

- text
- voice
- frontend interaction
- approved realtime interaction

Interaction input SHALL enter the governed LYRION runtime.

**Verification:** interaction integration tests and E2E validation.

---

## CORE-FR-002 — Lyri Runtime

The system SHALL provide Lyri as the primary LYRION intelligence
interface.

Lyri SHALL operate within the system's identity, policy, authority
and execution boundaries.

Lyri SHALL NOT independently constitute an execution authority.

---

## CORE-FR-003 — Intent Interpretation

The system SHALL transform authenticated human intent into a governed
task representation before consequential execution.

Intent interpretation SHALL remain distinguishable from authorization.

---

## CORE-FR-004 — Task Representation

The system SHALL maintain a structured representation of the active
root task, relevant context and task lineage.

Tasks SHALL have identifiable lifecycle state.

---

## CORE-FR-005 — Context Management

The system SHALL provide controlled context propagation across
interaction, cognitive, agentic and execution components.

Context SHALL be scoped and SHALL NOT implicitly grant authority.

---

## CORE-FR-006 — World State

The system SHALL maintain a governed representation of relevant
world state.

World-state information SHALL distinguish observed state,
inferred state and proposed state where applicable.

---

## CORE-FR-007 — Cognitive Runtime

The system SHALL provide a controlled cognitive runtime for:

- reasoning
- planning
- goal decomposition
- model interaction
- decision support

Cognitive output SHALL remain non-authoritative until independently
processed by the applicable governance and execution boundaries.

---

## CORE-FR-008 — PIAE

PIAE SHALL operate as an intelligence/runtime component.

PIAE SHALL NOT become an independent privileged execution authority.

---

## CORE-FR-009 — Goal and Planning

The system SHALL support governed goal and plan representation.

Plans SHALL remain proposals until the required authority and
execution controls admit their actions.

---

## CORE-FR-010 — Personality

Personality behavior SHALL remain separate from:

- authorization
- capability grants
- security policy
- execution admission
- emergency control

---

## CORE-FR-011 — Voice

Voice interaction SHALL remain separate from authorization.

Voice identity SHALL NOT by itself grant privileged execution authority.

Voice processing SHALL enter the normal authenticated and governed
application/session boundary.

---

## CORE-FR-012 — Application Runtime

Application Runtime SHALL provide the defined orchestration,
application-session and realtime boundary.

It SHALL NOT duplicate or bypass authoritative security,
authorization or execution components.

---

## CORE-FR-013 — HUI/FUI

The Core frontend SHALL provide the established LYRION HUI/FUI
interaction model.

Frontend state SHALL NOT constitute authorization.

Frontend actions requiring consequential execution SHALL enter the
normal governed request path.

---

# 9. Agentic Core Requirements

## CORE-AG-001 — Agent Identity

Each agent SHALL have an identity distinct from:

- human principal
- Lyri
- session
- model
- provider
- tool

---

## CORE-AG-002 — Agent Lifecycle

Agent lifecycle SHALL be explicitly governed.

Lifecycle operations SHALL include, as required:

- creation
- initialization
- activation
- suspension
- resumption
- termination
- recovery

---

## CORE-AG-003 — Agent Registry

Agents SHALL be discoverable through a controlled registry.

Registry information SHALL NOT itself constitute execution authority.

---

## CORE-AG-004 — Agent Control Plane

The Agent Control Plane SHALL govern agent lifecycle and mechanics,
including applicable:

- registration
- discovery
- routing
- scheduling
- supervision
- state
- communication
- resource management
- recovery
- termination
- audit integration

ACP SHALL NOT become an independent security authority.

---

## CORE-AG-005 — Delegated Authority

Agent authority SHALL be:

- task-bound
- agent-bound
- capability-scoped
- target-bound where applicable
- time-bounded where applicable
- revocable
- policy-bound
- replay-resistant

Child authority SHALL NOT exceed valid parent authority.

---

## CORE-AG-006 — Authority Attenuation

Delegation SHALL support authority attenuation.

A delegated agent SHALL NOT enlarge its authority through reasoning,
prompting, tool output or self-declaration.

---

## CORE-AG-007 — Agent Communication

Inter-agent communication SHALL be authenticated, attributable,
authorized, integrity-protected, scoped and observable.

Inter-agent messages SHALL provide appropriate replay resistance and
impersonation resistance.

Cross-task, cross-session and cross-tenant message leakage SHALL be
prevented where applicable.

Messages SHALL NOT implicitly grant authority.

---

# 10. Security and Governance Requirements

## CORE-SEC-001 — No Model Authority

No model output SHALL directly constitute authorization.

---

## CORE-SEC-002 — No Memory Authority

Memory content SHALL NOT automatically constitute truth or authority.

---

## CORE-SEC-003 — No Frontend Authority

Frontend state SHALL NOT constitute authorization.

---

## CORE-SEC-004 — No Voice Authority

Voice identity SHALL NOT constitute privileged execution authority.

---

## CORE-SEC-005 — No Protocol Authority

MCP, A2A, APIs, plugins or connectors SHALL NOT bypass LYRION
authorization and execution boundaries.

---

## CORE-SEC-006 — Independent Governance

Security-critical authorization SHALL be enforced by trusted system
components independent of the model's instruction following.

---

## CORE-SEC-007 — Deny by Default

Unrecognized, unauthorized or insufficiently scoped operations SHALL
fail closed.

---

## CORE-SEC-008 — Aegis

Aegis SHALL remain an independent security, policy, trust and risk
authority.

Agents and models SHALL NOT override Aegis policy.

---

## CORE-SEC-009 — HITL

Human approval SHALL be required when policy, risk or capability
classification requires it.

HITL approval SHALL NOT become an unrestricted execution authority.

---

## CORE-SEC-010 — Emergency Control

Emergency controls SHALL remain independent from normal agent/model
authority.

Agents SHALL NOT disable or modify their own emergency controls.

---

# 11. Capability and Execution Requirements

## CORE-EXEC-001 — Capability Gateway

Consequential operations SHALL pass through the authoritative
Capability Gateway / execution-admission boundary.

---

## CORE-EXEC-002 — Secure Executor

Secure Executor SHALL execute already-authorized operations.

It SHALL NOT infer privilege from model output or agent intent.

---

## CORE-EXEC-003 — Sandbox

Risk-appropriate execution isolation SHALL be provided for agent
execution.

Sandboxing SHALL address applicable:

- process isolation
- filesystem isolation
- network isolation
- credential isolation
- resource fencing
- escape resistance

---

## CORE-EXEC-004 — LHICF

Host operations SHALL pass through the controlled LYRION Host
Integration & Control Fabric where applicable.

---

## CORE-EXEC-005 — No Alternate Privileged Path

No alternate privileged execution path SHALL be introduced outside
the approved security and execution chain.

---

## CORE-EXEC-006 — Verification

Consequential execution SHALL have independent verification
appropriate to its risk.

An agent/model claim of success SHALL NOT by itself establish
successful execution.

---

# 12. Memory Requirements

## CORE-MEM-001 — Scoped Memory

Memory SHALL be scoped according to applicable:

- principal
- tenant
- session
- task
- agent
- project
- sensitivity

---

## CORE-MEM-002 — Provenance

Memory objects SHALL maintain appropriate provenance.

---

## CORE-MEM-003 — Trust

Memory SHALL distinguish evidence, provenance, confidence and trust
where applicable.

---

## CORE-MEM-004 — Validation

Information SHALL NOT become durable trusted memory merely because it
was generated by a model.

---

## CORE-MEM-005 — Conflict Handling

The memory architecture SHALL support conflict detection and
appropriate promotion, supersession or expiration.

---

## CORE-MEM-006 — Memory Lifecycle

The memory architecture SHALL maintain appropriate controls for:

- integrity and versioning
- retention
- revocation
- deletion
- auditability

Memory lifecycle operations SHALL preserve applicable provenance and
scope controls.

---

## CORE-MEM-007 — Memory Data Integrity

Primary authoritative memory state SHALL use the consistency model
defined by the approved Data Architecture.

Secondary indexes and derived retrieval structures SHOULD be
reconstructible where feasible.

Backup, restore, migration and corruption-recovery behavior SHALL be
validated before applicable production acceptance.

---

## CORE-MEM-008 — RMA Separation

Recursive Memory Architecture SHALL remain distinct from Recursive
Language Model reasoning.

---

# 13. RLM Requirements

## CORE-RLM-001 — Bounded Recursion and Isolation

RLM recursion SHALL be externally bounded and SHALL execute only
within the governed isolation boundary defined by the approved
execution and sandbox architecture.

Applicable limits SHALL include, where relevant:

- recursion depth
- calls
- tools
- context
- time
- tokens
- compute
- memory
- cost
- retries
- egress
- artifacts

---

## CORE-RLM-002 — No Authority or Isolation Bypass

RLM SHALL NOT grant itself or obtain through recursive execution:


- capabilities
- credentials
- filesystem authority
- network authority
- process authority
- privileged execution
- policy modification authority

---

## CORE-RLM-003 — Output Validation

RLM output SHALL remain reasoning/evidence output until processed by
the applicable governance and execution boundaries.

---

# 14. Observability and Provenance

## CORE-OBS-001 — Auditability

Security-relevant and consequential actions SHALL generate appropriate
audit evidence.

---

## CORE-OBS-002 — Causal Provenance

The system SHALL support causal lineage across applicable:

Human
→ Task
→ Agent
→ Delegation
→ Capability
→ Tool
→ Execution
→ Host Action
→ Verification
→ Outcome

---

## CORE-OBS-003 — Tamper Evidence

Critical provenance and audit evidence SHALL provide appropriate
integrity protection.

---

## CORE-OBS-004 — No False Evidence

Local or reference-layer evidence SHALL NOT be represented as
production evidence without the required environment and acceptance
basis.

---

# 15. Recovery and Reliability

## CORE-REL-001 — Durable State

Required agent/task/execution state SHALL be persisted according to
the approved durability model.

---

## CORE-REL-002 — Authority Revalidation

Recovery SHALL revalidate:

- identity
- task
- policy
- authority
- capability
- resource constraints

before consequential execution resumes.

---

## CORE-REL-003 — Revocation

Expired or revoked authority SHALL NOT be restored merely because a
checkpoint contains it.

---

## CORE-REL-004 — External Effects

Consequential external effects SHALL use appropriate idempotency,
deduplication or compensation mechanisms.

---

## CORE-REL-005 — Failure Handling

Security and execution failures SHALL fail safely and produce
appropriate evidence.

---

# 16. Resource Governance

## CORE-RES-001 — Resource Budgets

Applicable resource budgets SHALL be enforced outside model
instructions.

Budgets MAY include:

- CPU
- memory
- storage
- network
- tokens
- tool calls
- execution time
- cost
- retries
- agent count
- swarm depth
- egress
- artifacts

---

## CORE-RES-002 — Runaway Prevention

The system SHALL prevent uncontrolled recursive or agentic resource
consumption.

---

# 17. Interoperability

## CORE-INT-001 — Controlled Adapters

MCP, A2A, APIs, plugins and connectors SHALL enter through controlled
adapter boundaries.

---

## CORE-INT-002 — Trust Establishment

External interoperability participants SHALL undergo applicable
identity/trust and policy processing.

---

## CORE-INT-003 — Execution Boundary

Interoperability mechanisms SHALL NOT bypass:

- Aegis
- Capability Gateway
- Secure Executor
- Sandbox
- HITL where required
- Verification

---

# 18. Host Integration

## CORE-HOST-001 — Controlled Host Boundary

Host access SHALL occur through approved LYRION host integration
boundaries.

---

## CORE-HOST-002 — Typed Operations

Host operations SHALL use typed/controlled operations where
applicable rather than treating arbitrary shell execution as the
Universal Computer architecture.

---

## CORE-HOST-003 — Host Verification

Host operations SHALL provide appropriate independent verification
and provenance.

---

# 19. Privacy and Data Protection

## CORE-PRIV-001

Sensitive information SHALL be subject to defined access,
processing, retention and deletion controls.

---

## CORE-PRIV-002

Secrets SHALL NOT be unnecessarily exposed to models, agents,
frontend components, logs or provenance records.

---

## CORE-PRIV-003

Cross-session, cross-agent and cross-scope data leakage SHALL be
prevented.

---

# 20. Supply Chain

## CORE-SC-001 — Evidence-Based Supply-Chain Admission

Dependencies, models, tools, agents, images, adapters, MCP servers,
A2A peers, connectors and other externally sourced components SHALL
undergo appropriate evidence-based admission before privileged use.

Admission evidence SHALL include, as applicable:

- provenance
- version
- integrity
- vulnerability state
- ownership
- license
- security review
- approval status

Privileged admission SHALL fail closed when required evidence is
missing or invalid.

---

## CORE-SC-002

Untrusted external components SHALL NOT receive privileged authority
merely because they are integrated.

---

## CORE-AG-008 — Swarm Expansion Boundary

Governed swarm execution SHALL be treated as an incremental Agentic
Expansion capability rather than a prerequisite for establishing the
foundational Core.

When swarm capability is introduced, it SHALL provide at minimum:

- agent identity
- lineage
- bounded depth
- bounded width
- capability attenuation
- resource budgets
- namespace isolation
- communication authorization
- cancellation
- emergency stop

Unlimited recursive agent spawning SHALL NOT be permitted.

Swarm capability SHALL remain subject to the same Aegis, delegated
authority, capability, execution, sandbox, provenance and verification
boundaries established for the Core.

---

# 21. Performance and Scalability

## CORE-PERF-001

Core performance requirements SHALL be measurable and established
for applicable critical paths.

---

## CORE-PERF-002

Security controls SHALL not be disabled merely to satisfy performance
targets.

---

## CORE-PERF-003

The Core SHALL support bounded scaling of tasks, agents, tools and
resources according to the approved architecture.

---

# 22. HUI/FUI Requirements

## CORE-UI-001

The Core frontend SHALL implement the approved LYRION HUI/FUI
interaction direction.

---

## CORE-UI-002

The interface SHALL clearly represent applicable:

- system state
- task state
- agent state
- execution state
- approval state
- security state
- errors
- verification state

---

## CORE-UI-003

UI presentation SHALL NOT be treated as authoritative security state.

---

# 23. Validation Requirements

## CORE-VAL-001

Every accepted Core component SHALL have traceable validation
evidence.

---

## CORE-VAL-002

Validation SHALL include, where applicable:

- unit testing
- integration testing
- end-to-end testing
- security testing
- adversarial testing
- failure/recovery testing
- performance/resource testing
- frontend/browser testing
- voice/realtime testing
- provenance testing

---

## CORE-VAL-003

Reference validation SHALL remain distinguishable from real
infrastructure validation.

---

## CORE-VAL-004

Passing local tests SHALL NOT constitute production certification.

---

# 24. Core Acceptance Gates

The Core SHALL progress through:

### Gate A — Requirements

Requirements reviewed and approved.

### Gate B — Architecture

Core architecture approved and traceable to requirements.

### Gate C — Implementation

Implementation performed only after applicable authorization.

### Gate D — Integration

Core subsystems integrated.

### Gate E — Security Validation

Security and adversarial controls validated.

### Gate F — System Validation

End-to-end behavior validated.

### Gate G — Core Baseline

Documented Core validation baseline established.

### Gate H — Expansion Authorization

Only after the Core baseline is accepted may additional modules be
incrementally authorized.

---

# 25. Core Implementation Staging

## Stage A — Complete Core

Build the approved Core boundary.

## Stage B — Core Integration

Integrate all Core subsystems.

## Stage C — Core Stabilization

Perform:

- unit tests
- integration tests
- E2E tests
- security tests
- adversarial tests
- failure/recovery tests
- performance/resource tests
- frontend/browser tests
- voice/realtime tests
- provenance tests

## Stage D — Core Validation

Establish the documented Core validation baseline.

## Stage E — Incremental Expansion

Implement additional enterprise and agentic modules incrementally.

Each expansion SHALL follow:

Design
→ Security Review
→ Implementation
→ Unit Validation
→ Integration Validation
→ Security Validation
→ System Validation
→ Documentation Update
→ Manifest Update
→ Project Memory Update
→ Baseline/Release
→ Next Phase

---

# 26. Requirements Traceability

Each requirement SHALL ultimately trace:

Requirement
→ Architecture Component
→ Contract
→ Implementation
→ Security Control
→ Test
→ Evidence
→ Documentation
→ Manifest

Unverifiable requirements SHALL remain OPEN, DEFERRED or BLOCKED.

---

# 27. Project Memory and Manifest Synchronization

The Manifest SHALL remain the authoritative project-state ledger.

Project Memory SHALL preserve:

- decisions
- rationale
- implementation context
- completed work
- validation results
- blockers
- deferred decisions
- architectural changes
- important historical context

Documentation, Manifest, Project Memory and implementation state
SHALL remain synchronized.

A module SHALL NOT be considered project-complete until its
implementation, validation and documentation states agree.

---

# 28. Requirement Evidence Classification

Every requirement claim SHALL identify the applicable evidence class:

- Existing Approved Architecture
- Existing Implementation
- Existing Validation Evidence
- New Phase-B Design
- Proposed Enhancement
- Research Reference
- Pending Validation
- Production Evidence
- Independent Evidence

Documentation SHALL NOT manufacture evidence.

---

# 29. Current Gate State

Existing TAOS Architecture:
**APPROVED**

Existing TAOS Security Target:
**APPROVED**

Existing Platform Blueprint:
**APPROVED TARGET**

Existing TAOS Manifest:
**AUTHORITATIVE CURRENT-STATE LEDGER**

Existing Implementation:
**PARTIAL / VALIDATED IN DEFINED SLICES**

Complete TAOS:
**NOT PROVEN**

G47 Certification:
**BLOCKED**

Phase-B Detailed Architecture Approval:
**PENDING**

Phase-B Implementation Authorization:
**NOT AUTHORIZED**

Core PRD:
**DRAFT — REQUIREMENTS BASELINE**

---

# 30. Approval Requirement

This document SHALL NOT be considered an approved requirements
baseline until:

1. Requirements completeness review is performed.
2. Requirements-to-existing-architecture traceability is completed.
3. Security requirements are reviewed against the Phase-B Security
   Architecture.
4. Requirements conflicts are resolved.
5. Core scope is confirmed by the Core Architecture.
6. Validation paths exist for acceptance-critical requirements.
7. Open decisions are recorded.
8. Manifest and Project Memory references are prepared.
9. Formal requirements approval is recorded.

Creation of this document does NOT authorize implementation.

---

# 31. Next Required Artifact

After Core PRD approval:

**Complete LYRION Core Architecture**

Then:

**Agentic Runtime Architecture**

followed by the remaining Phase-B architecture specifications.

---

## End of Document

# LYRION R097 — Database Credential Provisioning Contract Gap

**Document ID:** R097-DOC-GAP-DB-CREDENTIAL-PROVISIONING  
**Version:** 1.0.0  
**Status:** IDENTIFIED / IMPLEMENTATION BLOCKED  
**Scope:** R097 PostgreSQL persistence integration  
**Date:** 2026-09-28

## 1. Purpose

This record documents the currently identified architecture and implementation
contract gap concerning PostgreSQL credential provisioning for R097.

This record does not authorize implementation, credential creation, PostgreSQL
role modification, password modification, `pg_hba.conf` modification, or
production operation.

## 2. Evidence Basis

The R097 documentation set establishes:

- durable recovery-context persistence;
- PostgreSQL integration testing;
- environment-gated PostgreSQL integration through `LYRION_DATABASE_URL`;
- current authorization and execution-admission requirements;
- prohibition of restoring historical authorization as current authority;
- reuse of the existing governed authorization architecture.

The repository implementation currently contains:

`src/lyrion/core/settings.py`

with the application default:

`postgresql+asyncpg://localhost/lyrion`

The integration test configuration uses:

`LYRION_DATABASE_URL`

when PostgreSQL integration evidence is executed.

## 3. Identified Gap

The repository and reviewed R097 documentation do not currently establish
an explicit approved contract defining:

1. the authoritative credential provider;
2. the runtime credential injection mechanism;
3. the service identity used by the R097 persistence runtime;
4. credential scope and lifetime;
5. credential rotation and revocation;
6. credential exposure boundaries;
7. secret redaction requirements for database connection configuration;
8. ownership and operational responsibility for provisioning;
9. development/test versus production credential separation;
10. the approved evidence required to prove credential provisioning.

Therefore the database credential provisioning mechanism remains undefined.

## 4. Security Boundary

No credential mechanism shall be invented locally as an implementation
shortcut.

In particular, this gap record does NOT authorize:

- creation of a new PostgreSQL role;
- modification of `lyrion_app`;
- password reset;
- credential discovery or extraction;
- credential placement in source code;
- credential placement in committed `.env` files;
- modification of PostgreSQL authentication policy;
- bypass of Aegis;
- bypass of Capability Gateway;
- bypass of Secure Executor or other governed execution controls.

## 5. Required Contract Before Implementation

Before R097 PostgreSQL runtime credential remediation proceeds, an approved
credential-provisioning contract shall define at minimum:

### 5.1 Identity

- runtime service identity;
- database principal;
- ownership;
- least-privilege permissions;
- separation between developer, test, staging, and production identities.

### 5.2 Secret Management

- authoritative secret-management mechanism;
- secret retrieval boundary;
- runtime injection mechanism;
- secret lifetime;
- rotation;
- revocation;
- emergency replacement;
- auditability.

### 5.3 Application Boundary

The application shall receive only the minimum credential material required
to establish its approved database connection.

Credentials shall not be:

- persisted in model context;
- exposed to agents unnecessarily;
- logged;
- written into provenance records;
- emitted in telemetry;
- embedded in source code;
- committed to version control.

### 5.4 PostgreSQL Boundary

The approved contract shall define:

- database principal;
- authentication mechanism;
- connection target;
- TLS requirements where applicable;
- database authorization;
- role ownership;
- schema privileges;
- migration privileges;
- operational maintenance privileges.

### 5.5 Validation Evidence

The contract shall define evidence proving:

- authentication succeeds with the approved identity;
- unauthorized identity/access fails;
- least privilege is enforced;
- credentials are not exposed;
- revoked/expired credentials fail as expected;
- credential rotation works;
- integration tests execute against the intended PostgreSQL environment;
- evidence is reproducible and attributable.

## 6. Current State

Current classification:

**IDENTIFIED GAP — IMPLEMENTATION BLOCKED**

The absence of an explicit provisioning contract is not evidence that PostgreSQL
itself is incorrectly configured.

It is an architecture and operational-contract gap.

## 7. Required Next Governance Action

An approved Phase-B documentation/architecture decision shall establish the
credential-provisioning contract before implementation changes are authorized.

Only after that approval may the implementation proceed to:

1. provision or bind the approved runtime identity;
2. configure secure secret injection;
3. execute PostgreSQL integration validation;
4. capture evidence;
5. update R097 validation records;
6. update applicable manifests;
7. proceed through the established acceptance/certification gates.

## 8. Safety Classification

This document records a governance/architecture gap only.

No database, role, password, authentication configuration, source code,
runtime configuration, or credential was modified by creation of this record.

## 9. Non-Claims

This record does not claim:

- production readiness;
- production operation;
- production certification;
- successful PostgreSQL runtime authentication;
- approved credential provisioning;
- approval to modify PostgreSQL;
- approval to introduce a new secret-management system.


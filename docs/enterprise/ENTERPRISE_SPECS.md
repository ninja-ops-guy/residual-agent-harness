# Residual Command Station — Enterprise Specifications

**Version:** 1.0.0
**Date:** 2026-09-13
**Normative language:** RFC 2119
**Target:** residual-agent-harness v2.0.0+
**Audience:** Fortune 500, multinational, regulated industries
**Depends on:** PATH_TO_10_SPECS.md, all previous specs

---

## Overview

Eight specs covering what a global company requires beyond the
technical architecture: identity, compliance, multi-tenancy,
availability, supply chain, integration, governance, and
commercial viability.

The technical work is 12 weeks. The enterprise work is 78 weeks.
The ratio is 1:6.5. This is why enterprise software is hard.

---

## SPEC-ENT-001: Enterprise Identity and Access Management

### Purpose
Integrate with the identity infrastructure that global companies
already have. No new user accounts. No separate passwords. No
shadow IT.

### Requirements

**ENT1-R1.** Residual MUST support SAML 2.0 and OpenID Connect
(OIDC) for authentication. It MUST integrate with Okta, Azure AD
(Entra ID), Ping Identity, Auth0, and OneLogin without custom
configuration per provider.

**ENT1-R2.** Residual MUST support Role-Based Access Control (RBAC)
with fine-grained permissions. Roles MUST be definable at the
level of: task types, swarm participation, HITL approval authority,
receipt visibility, module installation, and policy modification.

**ENT1-R3.** Residual MUST support Attribute-Based Access Control
(ABAC). Permission decisions MUST be evaluable against user
attributes: department, region, clearance level, employment status,
and custom attributes from the IdP.

**ENT1-R4.** Residual MUST support Just-In-Time (JIT) access.
A user MAY request temporary elevation for a specific task or
time window. Elevation MUST: expire automatically, be observed,
produce a receipt, and require pre-authorization from a
designated approver.

**ENT1-R5.** Residual MUST support service accounts for bots,
CI/CD pipelines, and automated systems. Service accounts MUST:
have scoped permissions (never admin), support credential rotation,
emit observations for every action, and be distinguishable from
human accounts in receipts.

**ENT1-R6.** All authentication events MUST be observed and
receipted. Login, logout, token refresh, permission elevation,
and access denial MUST produce observations with: user identity,
timestamp, source IP, and authorization result.

**ENT1-R7.** Residual MUST support multi-factor authentication
(MFA) enforcement. MFA MAY be delegated to the IdP (preferred)
or enforced locally. Privileged actions (HITL approval, policy
modification, module installation) MUST require MFA regardless
of session age.

**ENT1-R8.** Session management MUST comply with enterprise
policies. Configurable: session timeout, idle timeout, concurrent
session limits, and IP-based restrictions. Sessions MUST be
revocable immediately on security event.

---

## SPEC-ENT-002: Compliance and Audit Framework

### Purpose
Every action Residual takes must be auditable against GDPR, SOX,
HIPAA, PCI-DSS, ISO 27001, SOC 2, and industry-specific regulations
— simultaneously and automatically.

### Requirements

**ENT2-R1.** Every receipt, observation, and HITL decision MUST
be taggable with compliance framework references. The tagging
MUST be configurable per deployment. Example: a receipt for a
database change might be tagged `["SOX-CC7.2", "GDPR-Art32",
"PCI-DSS-Req10"]`.

**ENT2-R2.** The observation log MUST support configurable
retention policies. Default: 7 years for SOX-relevant events,
3 years for operational events, 1 year for debug events.
Retention MUST be enforced automatically. Expired events MUST
be archived before deletion.

**ENT2-R3.** The observation log MUST support legal hold. When
legal hold is active for a scope (user, task, time range),
events in that scope MUST NOT be deleted or archived until
the hold is released. Legal hold MUST itself be observed and
receipted.

**ENT2-R4.** Residual MUST support data residency. Receipts,
observations, and station state MUST be stored in the region
where the task was executed. Cross-border data flow MUST require
explicit policy approval and MUST be observed.

**ENT2-R5.** Residual MUST support GDPR Article 17 (right to
erasure) via pseudonymization. When a user requests deletion:
- Their identity MUST be replaced with a salted hash in all
  observations and receipts
- The salt MUST be destroyed, making the hash irreversible
- The receipts themselves MUST be preserved (they are legal
  records)
- The pseudonymization MUST be observed and receipted

**ENT2-R6.** Residual MUST generate compliance reports on demand.
Report types MUST include:
- All tasks executed in a time range with receipts
- All HITL escalations and their resolutions
- All contract violations and their dispositions
- All access to sensitive data with user attribution
- All module installations and their signatures

**ENT2-R7.** Compliance reports MUST be cryptographically signed
by the Station. They MUST be exportable in PDF, JSON, and CSV.
They MUST be suitable for presentation to external auditors
without modification.

**ENT2-R8.** Residual MUST integrate with enterprise SIEM systems
(Splunk, Microsoft Sentinel, IBM QRadar). All observations MUST
be forwardable in real time via syslog or native API. The
forwarding MUST be reliable (at-least-once delivery) and
observed.

---

## SPEC-ENT-003: Multi-Tenant Architecture

### Purpose
One Residual deployment, many isolated tenants. Business units,
regions, and projects each get their own namespace with independent
state and policies.

### Requirements

**ENT3-R1.** Residual MUST support multi-tenancy with hard
isolation between tenants. Each tenant MUST have its own:
- GoalSpec registry
- Module registry
- Receipt chain
- Observation log
- HITL queue
- Quarantine policy set
- Brake configuration

**ENT3-R2.** Tenant isolation MUST be enforced at the data layer.
One tenant MUST NOT query, read, or modify another tenant's
receipts, observations, or state — even with administrative
privileges. Cross-tenant access MUST require explicit federation
agreement.

**ENT3-R3.** Compute resources (workers, engines, cluster nodes)
MAY be shared across tenants. Scheduling MUST be fair: no tenant
MAY starve another of compute. Resource quotas MUST be
configurable per tenant.

**ENT3-R4.** Residual MUST support cross-tenant delegation.
Tenant A MAY grant Tenant B permission to execute tasks that
affect Tenant A's infrastructure. The delegation MUST:
- Be scoped (specific task types, specific resources)
- Be time-limited
- Require HITL approval from Tenant A for each execution
- Produce receipts visible to both tenants

**ENT3-R5.** Each tenant MUST be able to define its own:
- Quarantine policies (beyond platform defaults)
- Brake thresholds (beyond platform safety floors)
- Verification requirements (beyond platform minimums)
- Module allowlist/denylist

**ENT3-R6.** Tenant creation and deletion MUST be administrative
operations requiring platform-level privileges. Tenant deletion
MUST: archive all receipts and observations, destroy all state,
and produce a final deletion receipt.

---

## SPEC-ENT-004: High Availability and Disaster Recovery

### Purpose
If Residual goes down, the company keeps operating. Zero lost
receipts. Automatic failover. Tested recovery.

### Requirements

**ENT4-R1.** Residual MUST support active-active deployment.
Multiple station instances across regions MUST operate
simultaneously. If one instance fails, another MUST take over
automatically.

**ENT4-R2.** The receipt chain MUST be replicated across
instances in real time. Replication MUST be: synchronous for
the primary region, asynchronous for secondary regions. A
receipt that exists in the primary region MUST exist in at
least one secondary region within 30 seconds.

**ENT4-R3.** If the primary station fails mid-run, a secondary
station MUST be able to resume from the last verified receipt.
The resume MUST: identify incomplete tasks, reassign them to
available workers, and continue execution without human
intervention.

**ENT4-R4.** Recovery Point Objective (RPO) MUST be zero for
receipts. No verified receipt may be lost. Recovery Time
Objective (RTO) MUST be less than 60 seconds for automatic
failover.

**ENT4-R5.** Residual MUST support encrypted backups. Backups
MUST include: receipt chain, observation log, station state,
tenant configurations, and module registry. Backups MUST be
taken at least daily. Backup encryption keys MUST be managed
separately from the station.

**ENT4-R6.** Backup restoration MUST be tested at least
quarterly. A restoration test MUST: restore from backup,
verify receipt chain integrity, verify observation log
completeness, and produce a restoration report.

**ENT4-R7.** Residual MUST support degraded mode. If the
cluster is unavailable, individual stations MUST continue
operating with local models. Receipts MUST be queued locally
and synchronized when connectivity returns.

**ENT4-R8.** All failover events, backup operations, and
restoration tests MUST be observed and receipted.

---

## SPEC-ENT-005: Supply Chain Security

### Purpose
Prove that Residual itself hasn't been compromised. Signed
releases, SBOM, third-party audit, vulnerability disclosure.

### Requirements

**ENT5-R1.** Every release of Residual MUST be cryptographically
signed. The signature MUST cover the release artifact (binary,
package, or container image). The signing key MUST be managed
with hardware protection (HSM or equivalent).

**ENT5-R2.** Residual MUST produce a Software Bill of Materials
(SBOM) for every release. The SBOM MUST list: every direct
dependency, every transitive dependency, every version, every
license. The SBOM MUST be generated automatically during the
build process.

**ENT5-R3.** The SBOM MUST be scanned for known vulnerabilities
before every release. Vulnerabilities rated HIGH or CRITICAL
MUST be fixed or explicitly accepted with justification before
release. The scan results MUST be published with the release.

**ENT5-R4.** Residual MUST undergo annual third-party security
audit by a recognized firm (NCC Group, Trail of Bits, Cure53,
or equivalent). The audit MUST cover: code review, penetration
testing, architecture review, and compliance verification.
Results MUST be published.

**ENT5-R5.** Residual MUST maintain a vulnerability disclosure
program. Security researchers MUST be able to report issues
responsibly. Reports MUST be acknowledged within 72 hours.
Critical vulnerabilities MUST be patched within 14 days.

**ENT5-R6.** All dependencies MUST be pinned to exact versions
with cryptographic hashes. No floating version ranges. Hashes
MUST be verified on install. A dependency update MUST require
explicit review and CI passing.

**ENT5-R7.** Third-party modules MUST run in isolated containers.
Containers MUST: have no network access to the host, have
filesystem access limited to explicit allowlists, run as
non-root, and be resource-constrained.

**ENT5-R8.** The build process MUST be reproducible. Given the
same source code and build environment, the build MUST produce
bit-identical output. Reproducibility MUST be verified in CI
for every release.

---

## SPEC-ENT-006: Enterprise Integration Hub

### Purpose
Fit into the company's existing tooling. Residual doesn't
replace ITSM, CI/CD, monitoring, or communication — it plugs
into them.

### Requirements

**ENT6-R1.** Residual MUST integrate with ITSM systems:
ServiceNow, Jira Service Management, BMC Helix. Integration
MUST support: task creation from tickets, receipt attachment
to tickets, status synchronization (ticket status reflects
task status), and HITL challenge delivery via ticket
assignment.

**ENT6-R2.** Residual MUST integrate with CI/CD systems:
Jenkins, GitLab CI, GitHub Actions, Azure DevOps, CircleCI.
Integration MUST support: task triggering from pipeline
stages, pipeline gating on Residual verification (pipeline
waits for IntegrationReceipt), and receipt publication as
pipeline artifacts.

**ENT6-R3.** Residual MUST integrate with monitoring systems:
Datadog, New Relic, Dynatrace, Prometheus. Integration MUST
support: metrics export (per SPEC-GAP-003), health check
endpoints, alert generation on brake trips and HITL
escalations, and distributed tracing context propagation.

**ENT6-R4.** Residual MUST integrate with communication
platforms: Slack, Microsoft Teams, Email. Integration MUST
support: HITL challenge notifications, receipt delivery on
approval, swarm status updates, and alert routing to
on-call channels.

**ENT6-R5.** Residual MUST integrate with ticketing systems:
Jira, Azure Boards, Linear. Integration MUST support:
requirement import (ticket → GoalSpec), task status sync,
receipt attachment as evidence, and automatic ticket
closure on task acceptance.

**ENT6-R6.** All integrations MUST be bidirectional where
meaningful. Residual MUST accept input from enterprise
systems (tickets trigger tasks) AND produce output for
enterprise systems (receipts attach to tickets). One-way
integrations are insufficient.

**ENT6-R7.** All integration activity MUST be observed and
receipted. Every API call to an external system MUST produce
an observation with: target system, endpoint, request hash,
response hash, and latency.

---

## SPEC-ENT-007: Change Management and Governance

### Purpose
Enable adoption through the company's existing governance
processes. Change advisory boards, architecture reviews,
security reviews, and procurement.

### Requirements

**ENT7-R1.** Residual MUST provide a pilot program framework.
The framework MUST define: evaluation criteria, pilot scope,
success metrics, duration (typically 30-90 days), rollback
plan, and graduation criteria to production.

**ENT7-R2.** Residual MUST provide an architecture review
package. The package MUST include: system diagrams, data flow
diagrams, security boundary maps, failure mode analysis,
scalability analysis, and integration points. The package
MUST be suitable for presentation to an architecture review
board without modification.

**ENT7-R3.** Residual MUST provide a security review package.
The package MUST include: threat model, attack surface
analysis, mitigation strategies, compliance mapping (per
SPEC-ENT-002), vulnerability scan results (per SPEC-ENT-005),
and penetration test results.

**ENT7-R4.** Residual MUST provide runbook templates for
common operational scenarios:
- Brake tripped: investigation and resolution
- HITL challenge: review and approval workflow
- Contract violation: containment and post-mortem
- Station failure: failover and recovery
- Module installation: validation and rollback

**ENT7-R5.** Residual MUST provide role-specific training
materials:
- Operators: task execution, HITL approval, brake response
- Administrators: configuration, module management, troubleshooting
- Developers: module development, engine adapter development
- Auditors: receipt verification, compliance reporting

**ENT7-R6.** All training materials MUST include hands-on
exercises. Video-only or document-only training is
insufficient. Exercises MUST run against a sandboxed
Residual instance.

---

## SPEC-ENT-008: Commercial and Legal Framework

### Purpose
Enable procurement. A global company buys from vendors, not
open-source projects. There must be contracts, SLAs, support,
and liability.

### Requirements

**ENT8-R1.** A commercial entity MUST exist behind Residual.
The entity MUST be able to: sign contracts, accept payment,
provide invoices, and be liable for breaches. The entity
MAY be a corporation, LLC, or foundation with commercial
support arm.

**ENT8-R2.** Residual MUST offer support tiers:
- **Standard:** business hours, 24-hour response, email only
- **Premium:** 24/7, 4-hour response, email + phone
- **Enterprise:** 24/7, 1-hour response for P1, dedicated
  support engineer, on-site option

**ENT8-R3.** Residual MUST offer professional services:
implementation assistance, custom module development, training
delivery, and integration development. Services MUST be
available as fixed-scope engagements or ongoing retainers.

**ENT8-R4.** Residual MUST provide indemnification for
intellectual property infringement. If a third party claims
that Residual infringes their patents, copyrights, or trade
secrets, the vendor MUST defend the customer and cover
damages.

**ENT8-R5.** Residual MUST carry insurance:
- Cyber liability insurance (minimum $5M coverage)
- Errors and omissions insurance (minimum $2M coverage)
- General liability insurance (minimum $1M coverage)
- Certificate of insurance MUST be available on request.

**ENT8-R6.** Residual MUST provide financial stability evidence.
This MUST include: funding history, revenue or burn rate,
runway projection, and customer count. The evidence MUST
support a reasonable belief that the vendor will exist in
3 years.

**ENT8-R7.** Residual MUST offer flexible licensing:
- Open source (core platform)
- Commercial (enterprise features: multi-tenancy, HA/DR,
  compliance reporting, premium support)
- Per-node, per-task, or flat-rate pricing
- Educational and non-profit discounts

**ENT8-R8.** Residual MUST provide a Data Processing Agreement
(DPA) for GDPR compliance. The DPA MUST cover: data controller
vs. processor roles, sub-processor list, data breach
notification timeline (72 hours), and audit rights.

---

## Implementation Timeline

| Spec | Effort | Dependencies |
|---|---|---|
| ENT-001: IAM | 8 weeks | None |
| ENT-002: Compliance | 10 weeks | ENT-001 |
| ENT-003: Multi-Tenancy | 8 weeks | ENT-001 |
| ENT-004: HA/DR | 10 weeks | ENT-003 |
| ENT-005: Supply Chain | 6 weeks (parallel) | None |
| ENT-006: Integration Hub | 12 weeks | ENT-001, ENT-002 |
| ENT-007: Governance | 6 weeks (parallel) | None |
| ENT-008: Commercial | 26 weeks (parallel) | None |
| **Total** | **~90 weeks** | |

**Critical path:** ENT-001 → ENT-002 → ENT-006. Everything
else can be built in parallel.

**The uncomfortable truth:** The technical architecture
(M2-M4, engine adapters, cluster) is 12 weeks. The enterprise
requirements are 78 weeks. The ratio is 1:6.5. This is not
a flaw in Residual — it's the reality of enterprise software.
Every platform that serves global companies has paid this cost.
The question is whether you pay it now or pay it later.

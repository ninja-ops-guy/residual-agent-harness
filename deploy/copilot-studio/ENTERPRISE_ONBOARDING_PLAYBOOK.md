# RESIDUAL × Microsoft Copilot Studio Enterprise Onboarding Playbook

**Status:** Enterprise onboarding runbook  
**Applies to:** RESIDUAL Engineering Agents solution for Microsoft Copilot Studio  
**Departments:** Firmware, Mechanical, Electromechanical, Automated Testing, Quality Assurance  
**Primary outcome:** A tenant-specific deployment that produces a verified `release_eligible=true` enterprise-readiness bundle.

---

## 1. Purpose

This playbook converts the remaining enterprise deployment work into auditable tasks.

The repository supplies the application-side controls:

- Entra delegated/OBO validation
- department-scoped RBAC
- encrypted mission/evidence persistence
- PostgreSQL multi-instance persistence
- local read-only engineering analysis
- isolated build/test execution
- exact-head HITL for consequential writes
- package/configuration drift tests
- hybrid-Entra acceptance harness
- enterprise-readiness evidence bundle

The tenant must supply and verify the Microsoft and infrastructure controls that cannot be manufactured by repository code:

- production Entra identities and groups
- Conditional Access / MFA / device controls
- Power Platform environment and data policies
- production cryptographic key custody
- enterprise ingress and runtime hosting
- managed solution export/import
- real delegated-token acceptance testing
- final release evidence and activation approval

A green PR or successful solution import is **not** sufficient by itself.

---

# 2. Roles and responsibility model

| Role | Primary responsibilities |
| --- | --- |
| RESIDUAL Platform Owner | API/runtime deployment, PostgreSQL, KMS/HSM integration, configuration, readiness bundle |
| Entra Administrator | App registrations, delegated scope, groups, Conditional Access, workload identity |
| Power Platform Administrator | Environments, DLP/data policies, solution import/export, pipelines, Agent Library |
| Security Engineering | Threat review, ingress/WAF, key custody, SIEM, Conditional Access validation |
| Department Engineering Owner | Department membership, agent knowledge, repository/resource approvals |
| Engineering Lead | Consequential-action approver, departmental operational authority |
| QA / Qualification Owner | Acceptance scenarios, evidence review, release qualification |
| Auditor | Read-only evidence validation, readiness bundle review |
| Change Manager / Release Owner | Production activation, rollback authorization, change record |

No single technical control should silently collapse these roles into one superuser.

---

# 3. Required source artifacts

Before onboarding starts, confirm the deployment package contains:

- `residual/integrations/copilot_studio/openapi.yaml`
- `deploy/copilot-studio/solution-manifest.json`
- `deploy/copilot-studio/environment.example.json`
- `deploy/copilot-studio/agents/*.json`
- `deploy/copilot-studio/agent-library-template.json`
- `deploy/copilot-studio/SECURITY.md`
- `docs/integrations/COPILOT_STUDIO_SECURITY_REVIEW_V1.md`
- `docs/integrations/COPILOT_STUDIO_ENTERPRISE_DEMO.md`
- `docs/integrations/COPILOT_STUDIO_OPERATIONS.md`

Record the exact Git commit used for onboarding.

**Evidence required**
- exact 40-character Git SHA
- source repository URL
- pull request / release reference
- timestamp of the selected release candidate

**Exit criterion**
- all deployment work below is performed against one exact source head

---

# 4. Phase 0 — Enterprise preflight

## ENT-000 — Create the onboarding change record

**Owner:** Change Manager  
**Tasks**
- [ ] Create change / implementation record.
- [ ] Record exact RESIDUAL Git SHA.
- [ ] Identify dev, test, and production Power Platform environments.
- [ ] Identify Entra tenant.
- [ ] Identify production hosting region(s).
- [ ] Identify approved PostgreSQL service.
- [ ] Identify approved KMS/HSM service.
- [ ] Identify rollback owner and incident owner.

**Evidence**
- change ticket / implementation record
- approved implementation window
- named accountable owners

**Exit**
- deployment cannot proceed without an accountable release owner

---

## ENT-001 — Confirm repository qualification

**Owner:** RESIDUAL Platform Owner + QA  
**Tasks**
- [ ] Confirm Copilot enterprise matrix passed on Python 3.11.
- [ ] Confirm passed on Python 3.12.
- [ ] Confirm passed on Python 3.13.
- [ ] Confirm PostgreSQL multi-instance tests passed.
- [ ] Confirm Factory runtime evidence passed.
- [ ] Confirm Factory OS execution evidence passed.
- [ ] Confirm clean-install qualification passed.
- [ ] Confirm Control Plane / Factory ownership / measured-evaluation gates passed.
- [ ] Record any external/advisory check that did not run and why.

**Important**
PR Agent or another AI reviewer is advisory. Provider quota failure must be recorded, not converted into a false successful review.

**Evidence**
- GitHub Actions run IDs
- exact-head check results
- list of intentionally unsatisfied gates

**Exit**
- all authoritative product/security checks green on the exact release head

---

# 5. Phase 1 — Microsoft Entra identity foundation

## ENT-100 — Register the RESIDUAL API application

**Owner:** Entra Administrator  
**Tasks**
- [ ] Create or identify the production RESIDUAL API app registration.
- [ ] Restrict deployment to the intended tenant.
- [ ] Record Application (client) ID.
- [ ] Record tenant ID.
- [ ] Expose delegated API scope `access_as_user`.
- [ ] Review API permissions and remove unused permissions.
- [ ] Confirm access tokens for the API use the expected audience.
- [ ] Confirm signing keys are discoverable through the tenant JWKS endpoint.

**Do not**
- put secrets in `environment.example.json`
- use a maker's personal credential as RESIDUAL authority
- accept body-provided tenant/user/group identity

**Evidence**
- tenant ID
- API client ID
- delegated scope definition
- screenshot/export of API permissions
- token claim sample with secrets/redacted values removed

**Exit**
- a delegated Entra token can be issued for the RESIDUAL API

---

## ENT-101 — Register/configure the Copilot custom-connector client

**Owner:** Entra Administrator + Power Platform Administrator  
**Tasks**
- [ ] Create or identify the application/client used by the Copilot Studio custom connector.
- [ ] Record connector client application ID.
- [ ] Configure delegated/OBO access to the RESIDUAL API.
- [ ] Add only required redirect URIs.
- [ ] Configure consent according to tenant policy.
- [ ] Add the connector client ID to RESIDUAL's allowed client-app configuration.
- [ ] Verify a token from any other client app is rejected.

**Evidence**
- connector application ID
- consent/permission configuration
- negative test for unauthorized client app

**Exit**
- only approved connector client applications can invoke the RESIDUAL Copilot API surface

---

# 6. Phase 2 — Department and role groups

Create **object-ID based** groups. Do not configure RESIDUAL with display names.

## ENT-200 — Department member groups

**Owner:** Entra Administrator + Department Owners  
**Tasks**
- [ ] Create/identify Firmware Engineering member group.
- [ ] Mechanical Engineering member group.
- [ ] Electromechanical Engineering member group.
- [ ] Automated Testing member group.
- [ ] Quality Assurance member group.
- [ ] Assign owners for each group.
- [ ] Define membership lifecycle.
- [ ] Define joiner/mover/leaver process.

**Environment variables**
- `RESIDUAL_FIRMWARE_GROUP_ID`
- `RESIDUAL_MECHANICAL_GROUP_ID`
- `RESIDUAL_ELECTROMECHANICAL_GROUP_ID`
- `RESIDUAL_AUTOMATED_TESTING_GROUP_ID`
- `RESIDUAL_QA_GROUP_ID`

---

## ENT-201 — Department reviewer groups

**Owner:** Entra Administrator + QA/Department Owners  
**Tasks**
- [ ] Firmware reviewer group.
- [ ] Mechanical reviewer group.
- [ ] Electromechanical reviewer group.
- [ ] Automated Testing reviewer group.
- [ ] QA reviewer group.
- [ ] Verify reviewer membership does not grant another department's reviewer scope.

**Environment variables**
- `RESIDUAL_FIRMWARE_REVIEWERS_GROUP_ID`
- `RESIDUAL_MECHANICAL_REVIEWERS_GROUP_ID`
- `RESIDUAL_ELECTROMECHANICAL_REVIEWERS_GROUP_ID`
- `RESIDUAL_AUTOMATED_TESTING_REVIEWERS_GROUP_ID`
- `RESIDUAL_QA_REVIEWERS_GROUP_ID`

**Exit**
- a Mechanical reviewer cannot read Firmware mission evidence solely by reviewer role

---

## ENT-202 — Shared lead and auditor roles

**Owner:** Entra Administrator + Security  
**Tasks**
- [ ] Create/identify Engineering Leads group.
- [ ] Create/identify Engineering Auditors group.
- [ ] Require privileged access-management process if available.
- [ ] Limit group owners.
- [ ] Review memberships before production.

**Environment variables**
- `RESIDUAL_ENGINEERING_LEADS_GROUP_ID`
- `RESIDUAL_ENGINEERING_AUDITORS_GROUP_ID`

**Expected semantics**
- Lead: can read/control authorized department missions.
- Auditor: can read authorized evidence; cannot execute/cancel.
- Reviewer: can read within reviewer department; cannot control.
- Former department member: loses mission visibility even if they owned the mission originally.

---

# 7. Phase 3 — Conditional Access, MFA, and device posture

## ENT-300 — Define Conditional Access policy

**Owner:** Entra Administrator + Security Engineering  
**Tasks**
- [ ] Scope the policy to the intended engineering population/application.
- [ ] Require MFA according to organizational policy.
- [ ] Require compliant device and/or Microsoft Entra hybrid joined device as approved by security.
- [ ] Define emergency/break-glass exclusions separately.
- [ ] Test in report-only mode first where appropriate.
- [ ] Validate positive and negative sign-in cases.
- [ ] Document service/workload identities separately from interactive users.

**Important**
RESIDUAL does not invent device-compliance attestation. Device trust is enforced upstream by Entra and recorded as environment evidence.

**Evidence**
- Conditional Access policy ID/export
- positive sign-in evidence
- denied noncompliant-device test
- denied/no-MFA test where applicable

**Exit**
- intended users can access from compliant corporate endpoints; unapproved access path is blocked

Microsoft reference:
https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-alt-admin-device-compliand-hybrid

---

# 8. Phase 4 — Power Platform environment governance

## ENT-400 — Prepare environments

**Owner:** Power Platform Administrator  
**Tasks**
- [ ] Create/identify Development environment.
- [ ] Test/UAT environment.
- [ ] Production environment.
- [ ] Enable Copilot Studio.
- [ ] Confirm required admin/maker roles.
- [ ] Create environment strategy for ALM/pipelines.
- [ ] Restrict who can create/edit/publish engineering agents.

**Evidence**
- environment IDs
- admin/maker access matrix
- ALM path

---

## ENT-401 — Configure data policies / DLP

**Owner:** Power Platform Administrator + Security  
**Tasks**
- [ ] Create or update the applicable Power Platform data policy.
- [ ] Require authenticated agent usage.
- [ ] Place approved Microsoft connectors and RESIDUAL connector in the intended data group.
- [ ] Block or restrict unapproved HTTP usage.
- [ ] Apply endpoint filtering where used.
- [ ] Restrict public website/document knowledge sources as required by policy.
- [ ] Restrict Direct Line/custom channels if they are not approved.
- [ ] Restrict event triggers unless explicitly approved.
- [ ] Confirm data cannot move between incompatible Business/Non-business connector groups.

**Evidence**
- DLP policy export/screenshots
- connector classification
- negative policy test

**Exit**
- agent cannot publish/run with an unapproved connector/channel/data combination

Microsoft reference:
https://learn.microsoft.com/en-us/microsoft-copilot-studio/admin-data-loss-prevention

---

# 9. Phase 5 — Production RESIDUAL infrastructure

## ENT-500 — Provision PostgreSQL

**Owner:** RESIDUAL Platform Owner / Database Team  
**Tasks**
- [ ] Provision managed PostgreSQL meeting enterprise availability requirements.
- [ ] Enable TLS.
- [ ] Restrict network access to RESIDUAL services.
- [ ] Create least-privilege database identity.
- [ ] Configure backup/restore.
- [ ] Configure monitoring.
- [ ] Configure high availability/failover as required.
- [ ] Set production DSN through secret management, not source control.
- [ ] Test concurrent multi-instance gateway/worker access.
- [ ] Test recovery after gateway restart.
- [ ] Test worker leasing after worker failure.

**Evidence**
- DB service identifier
- backup policy
- HA policy
- restore test record
- multi-instance test output

**Exit**
- no production instance depends on local SQLite for shared enterprise state

---

## ENT-501 — Configure KMS/HSM CryptoProvider

**Owner:** Security Engineering + RESIDUAL Platform Owner  
**Tasks**
- [ ] Select enterprise KMS/HSM.
- [ ] Create encryption key(s).
- [ ] Create signing/integrity key(s) if required.
- [ ] Bind service identity to least-privilege key use.
- [ ] Implement/configure production `CryptoProvider`.
- [ ] Verify plaintext mission/source/evidence does not appear in database storage.
- [ ] Document rotation process.
- [ ] Test key rotation.
- [ ] Test backup/restore compatibility with retained encrypted evidence.

**Do not**
- use `LocalDevCryptoProvider` in production

**Evidence**
- KMS key identifiers
- access policy
- rotation test
- encryption-at-rest verification

---

## ENT-502 — Configure enterprise ingress

**Owner:** Security / Platform Engineering  
**Tasks**
- [ ] Publish RESIDUAL API behind approved ingress/API gateway/WAF.
- [ ] TLS only.
- [ ] Configure request/body/time limits.
- [ ] Configure distributed rate limiting.
- [ ] Restrict origins/routes as appropriate.
- [ ] Forward redacted security telemetry to SIEM.
- [ ] Do not log Authorization headers, raw prompts, source code, credentials, or plaintext evidence.
- [ ] Exercise 401/403/409/429 monitoring.
- [ ] Validate upstream health/failover.

**Evidence**
- ingress configuration
- TLS validation
- WAF/API gateway test
- log redaction test
- SIEM event sample

---

# 10. Phase 6 — RESIDUAL deployment configuration

## ENT-600 — Populate environment configuration

**Owner:** RESIDUAL Platform Owner  
**Tasks**
- [ ] Populate real API base URL.
- [ ] Tenant ID.
- [ ] API client ID.
- [ ] Connector client app ID.
- [ ] Five member group IDs.
- [ ] Five reviewer group IDs.
- [ ] Leads group ID.
- [ ] Auditors group ID.
- [ ] Validate configuration with `EnterpriseCopilotDeployment`.
- [ ] Record the resulting deployment configuration hash.

**Evidence**
- redacted deployment configuration
- `deployment_config_hash`

**Exit**
- configuration parses and department catalog contains all five departments

---

## ENT-601 — Configure Graph overage resolution

**Owner:** Entra Administrator + Platform Owner  
**Tasks**
- [ ] Determine whether group claim overage can occur for target users.
- [ ] If required, provision a service/workload identity for Microsoft Graph group checks.
- [ ] Grant only required Graph permission.
- [ ] Configure `MicrosoftGraphGroupResolver`.
- [ ] Ensure the resolver queries only the deployment's configured group IDs.
- [ ] Confirm token-provided `_claim_sources` URLs are never followed.

**Evidence**
- Graph permission list
- positive overage test
- unrequested-group rejection test

---

# 11. Phase 7 — Engineering resources and execution profiles

## ENT-700 — Register Firmware source resources

**Owner:** Firmware Engineering Owner + Platform Owner  
**Tasks**
- [ ] Define approved `repository_id` aliases.
- [ ] Map each alias to a controlled local/enterprise Git repository.
- [ ] Define approved read-only context file list.
- [ ] Set file/total byte limits.
- [ ] Verify snapshot reads exact committed content, not dirty working tree.
- [ ] Verify cloud/provider-chat engine cannot receive source context.

**Evidence**
- repository resource catalog
- commit/snapshot test evidence
- negative cloud-disclosure test

---

## ENT-701 — Register approved build/test profiles

**Owner:** Firmware/Test Engineering + Security  
**Tasks**
- [ ] Define opaque `build_profile_id` values.
- [ ] Define exact argv arrays; no prompt-generated commands.
- [ ] Set timeout.
- [ ] CPU bound.
- [ ] memory bound.
- [ ] output bound.
- [ ] Review required toolchain binaries.
- [ ] Verify M4 namespace isolation is available.
- [ ] Verify no unsandboxed fallback.
- [ ] Verify network namespace is private/denied by construction.

**Evidence**
- profile hashes
- successful isolated build/test
- isolation-unavailable negative test

---

## ENT-702 — Register document/evidence bundles

**Owner:** Mechanical / Electromechanical / QA Owners  
**Tasks**
- [ ] Define approved immutable document/evidence bundle aliases.
- [ ] Limit document sizes and bundle total sizes.
- [ ] Define source classifications.
- [ ] Verify document content is treated as untrusted evidence, not instructions.
- [ ] Verify local review engine cannot execute tools.

**Evidence**
- bundle IDs/hashes
- prompt-injection negative test

---

# 12. Phase 8 — Copilot custom connector

## ENT-800 — Create/import custom connector

**Owner:** Power Platform Administrator  
**Tasks**
- [ ] Use `residual/integrations/copilot_studio/openapi.yaml`.
- [ ] Replace deployment placeholders through supported environment/configuration mechanisms.
- [ ] Configure Microsoft Entra delegated authentication/OBO.
- [ ] Configure connection reference.
- [ ] Point to enterprise RESIDUAL API origin.
- [ ] Test submit/status/evidence/cancel.
- [ ] Confirm no additional unreviewed operations are exposed.
- [ ] Confirm invalid department/template combinations fail closed.

**Evidence**
- custom connector definition
- connection reference ID
- successful API smoke run

**Exit**
- connector can call RESIDUAL using the signed-in user's delegated identity

---

# 13. Phase 9 — Build the five agents

Use the manifests in `deploy/copilot-studio/agents/`.

## ENT-900 — Firmware Engineering agent

- [ ] Import/create agent.
- [ ] Add approved native Microsoft knowledge sources.
- [ ] Add RESIDUAL actions:
  - `firmware-repository-analysis`
  - `firmware-sandbox-build`
  - `firmware-test-triage`
- [ ] Verify ordinary Q&A stays native.
- [ ] Verify bounded execution uses RESIDUAL.
- [ ] Verify no merge/deploy action exists.

## ENT-901 — Mechanical Engineering agent

- [ ] Add approved Mechanical knowledge.
- [ ] Add design-review/change-impact RESIDUAL actions.
- [ ] Verify released design state cannot be modified.

## ENT-902 — Electromechanical Engineering agent

- [ ] Add approved interface/integration knowledge.
- [ ] Add interface/integration review actions.
- [ ] Verify cross-domain evidence is department-scoped.

## ENT-903 — Automated Testing agent

- [ ] Add approved testing knowledge.
- [ ] Add test-plan review.
- [ ] Add isolated test execution.
- [ ] Verify only configured test/build profiles execute.

## ENT-904 — Quality Assurance agent

- [ ] Add approved quality/qualification knowledge.
- [ ] Add evidence-review/release-readiness actions.
- [ ] Verify QA does not modify implementation under review.

**Evidence for ENT-900..904**
- agent IDs
- solution component IDs
- configured knowledge sources
- configured RESIDUAL actions
- screenshots/exported configuration
- smoke-test transcript

---

# 14. Phase 10 — Power Platform solution / ALM

## ENT-1000 — Build custom solution

**Owner:** Power Platform Administrator  
**Tasks**
- [ ] Create/open `ResidualEngineeringAgents` custom solution.
- [ ] Add all five agents.
- [ ] Add custom connector.
- [ ] Add connection references.
- [ ] Add environment variables.
- [ ] Add required dependent components.
- [ ] Validate solution dependencies.
- [ ] Use development/test/prod ALM process.

Microsoft reference:
https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-solutions-overview

---

## ENT-1001 — Export managed production candidate

**Owner:** Power Platform Administrator + Release Owner  
**Tasks**
- [ ] Export managed solution ZIP from the approved environment.
- [ ] Record solution version.
- [ ] Calculate SHA-256.
- [ ] Store artifact in approved release repository.
- [ ] Import into test/UAT environment.
- [ ] Resolve required connection references.
- [ ] Reconfigure authentication after import if required.
- [ ] Publish agents in test only.

**Evidence**
- managed ZIP
- ZIP SHA-256
- import log
- solution version
- test environment ID

Microsoft reference:
https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-solutions-import-export

---

# 15. Phase 11 — Hybrid-Entra acceptance / trial by fire

Run the scenarios in `COPILOT_STUDIO_ENTERPRISE_DEMO.md`.

## ENT-1100 — Positive Firmware walkthrough

**Tasks**
- [ ] User signs in on corporate compliant/hybrid-joined endpoint.
- [ ] Opens Firmware Engineering agent.
- [ ] Requests repository analysis.
- [ ] Copilot selects RESIDUAL tool.
- [ ] Delegated identity reaches RESIDUAL.
- [ ] Mission is authorized.
- [ ] Worker executes.
- [ ] Evidence returns to Copilot.
- [ ] No source disclosure to cloud/provider-chat engine occurs.

---

## ENT-1101 — RBAC negative cases

- [ ] Mechanical user requests Firmware mission → denied.
- [ ] Firmware reviewer reads Firmware evidence → allowed.
- [ ] Mechanical reviewer reads Firmware evidence → denied.
- [ ] Reviewer cancellation → denied.
- [ ] Auditor read → allowed.
- [ ] Auditor cancellation → denied.
- [ ] Engineering Lead cancellation → allowed.
- [ ] Removed former owner → access denied/nondisclosing.

---

## ENT-1102 — Identity negative cases

- [ ] Wrong tenant → denied.
- [ ] Wrong audience → denied.
- [ ] Missing delegated scope → denied.
- [ ] Wrong connector client app → denied.
- [ ] Expired token → denied.
- [ ] HS256 token → denied.
- [ ] Unsigned/malformed token → denied.
- [ ] Group overage resolution works only through fixed resolver.

---

## ENT-1103 — Execution attack cases

- [ ] Prompt requests shell → authority unchanged.
- [ ] Prompt requests merge/deploy/secrets → denied/not exposed.
- [ ] Structured input includes path/URL/capability/role → rejected.
- [ ] Repository contains prompt injection → treated as data.
- [ ] Document contains prompt injection → treated as data.
- [ ] Unknown build profile → no command runs.
- [ ] Namespace isolation unavailable → fail closed.
- [ ] Worker lease expires → result cannot become authoritative.
- [ ] Cancellation races completion → completion rejected.
- [ ] Queue ciphertext tampered → claim rejected.
- [ ] Duplicate retry storm → one mission.
- [ ] Same request ID/different payload → 409.
- [ ] Mission ID enumeration → uniform not-found.

---

## ENT-1104 — HITL negative cases

- [ ] Create exact-head external-write challenge.
- [ ] Approve correct head → accepted once.
- [ ] Replay approval → rejected.
- [ ] Change evidence head → previous approval rejected.
- [ ] Wrong approver role → rejected.
- [ ] Missing host authenticator → fail closed.

**Exit for Phase 11**
- every acceptance scenario has a recorded pass/fail result
- all blocking scenarios pass

---

# 16. Phase 12 — Operational readiness

## ENT-1200 — Monitoring / SIEM

**Owner:** Security Operations  
**Tasks**
- [ ] Alert on abnormal 401/403.
- [ ] 409 replay/conflict spikes.
- [ ] 429 rate limiting.
- [ ] lease expiry.
- [ ] ciphertext verification failures.
- [ ] sandbox infrastructure failure.
- [ ] sustained queue depth.
- [ ] repeated worker failure.
- [ ] HITL replay/denial.
- [ ] PostgreSQL health/failover.
- [ ] KMS access failure.

**Evidence**
- SIEM dashboard/rules
- test alert

---

## ENT-1201 — Backup and recovery exercise

**Owner:** Platform / Database Team  
**Tasks**
- [ ] Back up encrypted DB.
- [ ] Restore to isolated recovery environment.
- [ ] Verify ownership records.
- [ ] Verify evidence decrypts with authorized key path.
- [ ] Confirm uncertain active leases are not blindly replayed.
- [ ] Record recovery time.
- [ ] Record recovery point.

---

## ENT-1202 — Incident response walkthrough

**Tasks**
- [ ] Connector credential compromise.
- [ ] KMS key compromise.
- [ ] Entra group misassignment.
- [ ] API ingress compromise.
- [ ] worker compromise.
- [ ] malicious knowledge/source content.
- [ ] database outage.
- [ ] Graph outage.
- [ ] JWKS refresh failure.

**Evidence**
- tabletop record
- escalation contacts
- rollback/disable procedure

---

# 17. Phase 13 — Build the enterprise-readiness bundle

## ENT-1300 — Collect exact-head qualification evidence

**Owner:** QA / Release Owner  
**Tasks**
- [ ] Record exact Git SHA.
- [ ] Copilot matrix run ID.
- [ ] Python 3.11 result.
- [ ] Python 3.12 result.
- [ ] Python 3.13 result.
- [ ] PostgreSQL qualification evidence.
- [ ] Factory runtime evidence.
- [ ] Factory OS evidence.
- [ ] clean-install qualification.
- [ ] Control Plane.
- [ ] ownership gate.
- [ ] Command Station.
- [ ] controller/provider contracts.
- [ ] browser/Pages proof if part of release.

---

## ENT-1301 — Bind release artifacts

**Tasks**
- [ ] Managed Power Platform solution ZIP SHA-256.
- [ ] Deployment configuration hash.
- [ ] Optional container/image digest(s).
- [ ] Infrastructure-as-code artifact hash(es) if applicable.
- [ ] acceptance scenario report hash.

---

## ENT-1302 — Generate readiness bundle

Use RESIDUAL's enterprise-readiness API.

The bundle must contain:
- exact Git SHA
- exact-head qualification records
- department policy
- deployment-config hash
- acceptance scenarios
- release artifact SHA-256s
- known limitations

**Exit**
- `verify_readiness_bundle(...)` succeeds

---

## ENT-1303 — Require release eligibility

Production activation requires:

```
release_eligible == true
```

That requires:
- all qualification records pass
- all blocking scenarios pass
- required release artifact hashes exist
- no blocking known limitations remain

If it is false, stop.

---

# 18. Phase 14 — Agent Library publishing

## ENT-1400 — Register custom template as Inactive

**Owner:** Power Platform / Copilot Agent Kit Administrator  
**Tasks**
- [ ] Confirm Copilot Agent Kit is installed/configured if Agent Library is used.
- [ ] Create custom template.
- [ ] Upload managed solution ZIP.
- [ ] Attach setup guide.
- [ ] Keep Publish Status = **Inactive**.
- [ ] Validate install into a clean test environment.
- [ ] Validate connection references.
- [ ] Validate environment variables.
- [ ] Re-run smoke/hybrid acceptance.

Microsoft references:
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/kit-agent-library-custom-templates
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/kit-agent-library-custom-agent-templates

---

## ENT-1401 — Activate template

**Preconditions**
- [ ] readiness bundle verifies
- [ ] `release_eligible=true`
- [ ] change approval granted
- [ ] test install successful
- [ ] rollback plan approved

**Task**
- [ ] Change Agent Library publish status from Inactive to Active.

**Evidence**
- template ID
- activation timestamp
- active managed-solution SHA-256
- release/change record

---

# 19. Phase 15 — Production activation

## ENT-1500 — Production import

- [ ] Import managed solution into production.
- [ ] Resolve production connection references.
- [ ] Populate production environment variables.
- [ ] Validate Entra authentication.
- [ ] Publish only approved agents.
- [ ] Verify DLP policy enforcement.
- [ ] Run bounded smoke tests.

---

## ENT-1501 — Final production acceptance

- [ ] One positive mission per department.
- [ ] One cross-department denial.
- [ ] Reviewer scope verification.
- [ ] Auditor read-only verification.
- [ ] Engineering Lead control verification.
- [ ] isolated test execution.
- [ ] evidence retrieval.
- [ ] SIEM/audit event.
- [ ] PostgreSQL health.
- [ ] KMS health.
- [ ] no secret/source leakage.

**Exit**
- release owner signs production acceptance

---

# 20. Rollback playbook

Rollback does not require weakening policy.

## RB-01 — Disable Agent Library template
- Set template Inactive to stop new installs.

## RB-02 — Unpublish affected agents
- Prevent new user interactions.

## RB-03 — Disable/restrict custom connector
- Block new mission submissions.

## RB-04 — Revoke client/service identity
- Use Entra if compromise is suspected.

## RB-05 — Freeze workers
- Stop new claims.
- Preserve encrypted queue/evidence.
- Do not automatically replay uncertain active work.

## RB-06 — Roll back managed solution
- Follow Power Platform solution/version rollback policy.

## RB-07 — Preserve evidence
- Keep audit/evidence under retention/legal-hold requirements.

## RB-08 — Requalify before restore
- New exact head/configuration must produce a fresh readiness bundle.

---

# 21. Offboarding / access lifecycle

## ENT-1600 — User offboarding

**Tasks**
- [ ] Remove member/reviewer/lead/auditor group assignments as appropriate.
- [ ] Verify removed department member loses mission access.
- [ ] Revoke sessions according to identity policy.
- [ ] Preserve evidence according to retention policy.

## ENT-1601 — Department changes

A mover between departments must not inherit the previous department's evidence authority unless separately assigned a reviewer/lead/auditor role.

---

# 22. Final go-live checklist

Do not activate production until every required item below is checked.

## Identity
- [ ] Tenant/API/connector IDs populated
- [ ] delegated `access_as_user`
- [ ] RS256/JWKS validation
- [ ] real group object IDs
- [ ] Graph overage tested if needed

## Access
- [ ] five member groups
- [ ] five reviewer groups
- [ ] leads group
- [ ] auditor group
- [ ] cross-department negatives pass

## Endpoint
- [ ] Conditional Access
- [ ] MFA
- [ ] compliant/hybrid device policy
- [ ] ingress TLS/WAF/rate limits
- [ ] redacted SIEM logging

## Runtime
- [ ] production PostgreSQL
- [ ] backup/restore
- [ ] KMS/HSM CryptoProvider
- [ ] resource catalogs
- [ ] build/test profiles
- [ ] sandbox isolation

## Power Platform
- [ ] DLP policy
- [ ] custom connector
- [ ] five agents
- [ ] connection references
- [ ] environment variables
- [ ] managed solution ZIP
- [ ] test import

## Qualification
- [ ] exact-head code matrix
- [ ] PostgreSQL multi-instance
- [ ] hybrid-Entra walkthrough
- [ ] attack scenarios
- [ ] HITL scenarios
- [ ] operational recovery test

## Release
- [ ] managed ZIP SHA-256
- [ ] deployment-config hash
- [ ] readiness bundle verifies
- [ ] `release_eligible=true`
- [ ] change approval
- [ ] Agent Library activation / production publish

---

# 23. Definition of enterprise onboarding complete

Enterprise onboarding is complete only when:

1. Microsoft-native identity, device, DLP, environment, solution, and Agent Library controls are configured in the real tenant.
2. RESIDUAL independently validates identity and authority and executes only bounded capabilities.
3. Production persistence and cryptographic custody use enterprise services.
4. The real managed solution and deployment configuration have been acceptance tested.
5. Negative/adversarial scenarios pass.
6. The exact release head and all release artifacts are cryptographically bound into the readiness bundle.
7. `release_eligible=true`.
8. Production activation is approved through the organization's change process.

Anything less is a development/test deployment or enterprise pilot—not a fully onboarded production deployment.

# Copilot Studio Firmware v1 — Security Review

Status: implementation security review, pre-production  
PR: #290  
Scope: Microsoft Copilot Studio -> Entra delegated token -> RESIDUAL Firmware profile -> Factory ExecutionPlan boundary

## Security objective

A Copilot Studio agent may request a bounded RESIDUAL mission, but neither the
conversation, request body, connector configuration, nor a downstream worker may
grant authority beyond the authenticated user's verified department profile and
the server-owned mission template.

The v1 surface intentionally has no production write, PR merge, policy
modification, verifier bypass, qualification bypass, secret-read, arbitrary host
shell, or arbitrary network capability.

## Trust boundary

Trusted for authority:
- RESIDUAL's configured OIDC verifier and key provider;
- verified Entra claims after signature/issuer/audience/time validation;
- deployment-configured tenant, delegated scope, optional connector client-app
  allowlist, and department group object IDs;
- server-owned DepartmentProfile and MissionTemplate registry;
- RESIDUAL Factory plan hashing and the MissionBinding hash;
- the configured durable MissionStore.

Not trusted for authority:
- user prompt text;
- Copilot-generated text;
- request-body identity/role/department fields;
- arbitrary structured inputs;
- knowledge-source or tool output;
- backend-returned template/risk metadata;
- friendly Entra group display names in production;
- token-provided group-overage endpoints.

## Findings and disposition

### SR-01 — JWT algorithm confusion

Risk: the generic RESIDUAL OIDC utility supports HS256 and RS256. A Copilot
integration must not accidentally accept a symmetric-token configuration for
Microsoft Entra.

Disposition: **fixed**. CopilotIdentityVerifier rejects every JWT header whose
`alg` is not exactly `RS256` before the generic verifier runs. The generic
OIDC verifier still performs signature, issuer, audience, and time validation.
Regression coverage explicitly constructs an otherwise-valid HS256 token and
requires rejection.

### SR-02 — Confused deputy / body-supplied identity

Risk: a caller could place tenant, group, department, role, or administrator
fields in the connector body and attempt to have RESIDUAL trust them.

Disposition: **fixed**. MissionRequest accepts exactly four fields:
`request_id`, `template_id`, `objective`, and `inputs`. Identity is created
only by CopilotIdentityVerifier from verified claims. Extra body identity fields
fail the request.

### SR-03 — Prompt or structured-input capability escalation

Risk: prompt injection could request production deployment, merge, secret
retrieval, host shell, or another prohibited operation.

Disposition: **fixed at the gateway boundary**. Capabilities come only from the
server-owned MissionTemplate. Prompt text and inputs are never interpreted as
authority. Tests send explicit requests for `pr.merge`, `production.write`,
`secrets.read`, arbitrary shell, and administrator role and verify the bound
capability set remains unchanged.

### SR-04 — Department authorization and Entra group semantics

Risk: Entra access-token `groups` values are group object IDs, not stable
friendly names. Group overage can also move group membership outside the token.

Disposition: **fixed/configurable**. DepartmentProfile accepts deployment-specific
group object IDs. The friendly `Engineering-Firmware` value is a local fixture
only. Group-overage resolution receives only the already-verified tenant ID and
object ID; it is not passed the token-provided endpoint, preventing a resolver
from accidentally following an attacker-controlled URL.

Production requirement: configure the Firmware Entra group object ID and use a
host-owned Microsoft Graph resolver when group overage must be supported.

### SR-05 — Cross-user evidence access

Risk: a valid Firmware user could enumerate another Firmware user's mission
evidence or cancel another mission.

Disposition: **fixed, stricter than the future role model**. v1 binds ownership
to `tenant_id + object_id + mission_id`. Unauthorized callers receive the same
not-found result used for an absent mission. Group membership is re-evaluated on
status, evidence, and cancellation, so removing the user from the department
revokes access. v1 does not yet expose a Firmware-reviewer override.

### SR-06 — Replay / idempotency race

Risk: repeated connector retries, process restarts, or two gateway instances
could execute the same request twice or reuse one request ID for different work.

Disposition: **fixed at the gateway/store boundary**. A canonical request hash is
bound to `tenant + object + request_id`. Mission IDs are deterministic from the
verified identity, request hash, template, department, and Factory plan hash.
MissionStore atomically claims that idempotency key. Reusing the key with a
different canonical payload fails closed. Backends are required to be idempotent
by mission ID.

Crash recovery is tested for the window where the durable idempotency claim
commits but the backend acknowledgement is lost: the exact deterministic mission
is safely re-submitted.

### SR-07 — Process restart loses authorization ownership

Risk: an in-memory ownership map would make evidence authorization and replay
semantics depend on one Python process lifetime.

Disposition: **fixed**. SQLiteMissionStore provides the reference durable
implementation. It persists hashes and authorization metadata only, not bearer
tokens, provider credentials, prompts, evidence bodies, or tool output.

On POSIX, the store refuses symlink traversal and requires a private regular file
owned by the service with no group/other permission bits.

### SR-08 — Error and audit leakage

Risk: token contents, claim values, prompt text, backend error strings, or
evidence could be returned to Copilot or copied to telemetry.

Disposition: **fixed for the framework-neutral API adapter**. Expected access
errors expose stable codes and bounded descriptions. Unexpected ContractError
responses use a generic 500 message. The optional audit callback receives only
method, bounded path, status, stable error code, and exception type; it never
receives authorization headers, payloads, claim values, evidence bodies, or raw
backend exception text. Regression tests verify redaction.

### SR-09 — Connector client identity

Risk: audience validation proves the token is for the RESIDUAL API, but a tenant
may also want to restrict which Entra client application can invoke this Copilot
surface.

Disposition: **implemented as a deployment control**. CopilotIdentityVerifier can
require an allowlisted `azp`/`appid`. Production Copilot packaging should set
this to the expected custom-connector/client application ID.

### SR-10 — Consequential external writes / HITL

Risk: a future template might turn a Copilot request into a repository, ticket,
configuration, deployment, or production write without exact-head human
authorization.

Disposition for v1: **removed from the attack surface**. The exposed Firmware
templates are analysis, sandbox build/test, patch proposal, and draft-PR
*proposal* only. No external-write endpoint or capability exists in the v1 API.
`production.write` and `pr.merge` are explicitly denied.

Production expansion requirement: any future external-write capability must be
added as a separately reviewed template and routed through RESIDUAL HITL with
approval bound to the exact mission/plan/evidence head. Copilot's own confirmation
UI is additive and is not sufficient authorization for RESIDUAL.

## Automated security/contract coverage

The dedicated Copilot CI lane runs on Python 3.11, 3.12, and 3.13 and covers:
- valid delegated mission submission;
- RS256 algorithm pinning;
- issuer/audience/expiry/scope/tenant failures;
- department denial;
- optional client-app allowlist;
- group-overage fail-closed behavior and verified-ID resolver;
- body identity injection;
- prompt and structured-input authority escalation;
- exact capability binding;
- request size bounds;
- deterministic idempotency and conflict behavior;
- cross-user evidence denial;
- department-removal revocation;
- owner-scoped cancellation;
- durable restart behavior;
- lost-backend-acknowledgement recovery;
- audit redaction;
- SQLite file privacy and symlink rejection.

## Production blockers still open

These are not hidden behind a "security complete" label:

1. **HTTP hosting layer.** The framework-neutral adapter expects a parsed body.
   The production host must enforce TLS, content type, a raw HTTP body limit,
   request/read timeouts, rate limits, and safe reverse-proxy behavior before
   calling CopilotAPI.
2. **Real Entra configuration.** Configure tenant-specific issuer/JWKS,
   RESIDUAL API audience, `access_as_user`, expected connector client app ID,
   and real Firmware group object ID. JWKS retrieval/rotation is a host
   responsibility of the existing OIDC key-provider boundary.
3. **Production Factory backend.** InMemoryMissionBackend is test/development
   only. Production needs a durable backend that consumes the already-compiled
   ExecutionPlan and preserves MissionBinding, evidence, cancellation, and
   mission-ID idempotency.
4. **Group overage resolver.** If required, implement it with a fixed Microsoft
   Graph endpoint and the verified tenant/object IDs. Never follow a URL from
   `_claim_sources`.
5. **Enterprise rate/load qualification.** Run concurrent submissions, polling,
   cancellation races, backend restart, store contention, and resource-exhaustion
   tests against the hosted endpoint.
6. **Future reviewer roles.** v1 is owner-only. Cross-user reviewer/auditor
   evidence access must be explicit RBAC, not a relaxation of owner checks.
7. **Future writes.** No external write may be added until the RESIDUAL HITL
   exact-head approval path and stale-approval tests are present.
8. **Conditional Access/device compliance.** Hybrid Entra join and compliant
   device enforcement stay upstream in Microsoft Entra. RESIDUAL must not claim
   device attestation unless a verified device claim is explicitly integrated.

## Current review conclusion

The implemented v1 gateway is deliberately constrained to bounded analysis and
sandbox/proposal missions. The security-sensitive identity, authorization,
capability, replay, ownership, and redaction controls are represented in code and
tests. Production deployment remains gated on the blockers above and on an
exact-head green CI result; this document is not an authorization to merge or
deploy.


## C4 read-only execution bridge

The first production-shaped execution path is intentionally limited to
`firmware-repository-analysis`.

Admission and execution are separated by `EncryptedMissionQueueBackend`.
The Copilot/HTTP process persists an encrypted, integrity-bound mission but does
not execute repository code. A trusted `FirmwareRepositoryAnalysisWorker`
claims only the analysis template through an exact lease.

Repository access is resolved through `RepositoryCatalog`: the caller supplies
only an opaque `repository_id`; the deployment owns the resolved local Git
repository and exact context-file list. The worker reads those files from a
frozen `HEAD^{commit}`, not the mutable working tree, and records direct
SHA-256 file hashes plus a snapshot hash.

Repository contents are passed to the selected RESIDUAL execution engine as
explicitly untrusted data. The worker exposes no shell, file-write, arbitrary
network, merge, deployment, secret, policy, or qualification tool surface.
Any engine result containing tool calls is rejected. Provider-native approval or
policy metadata is rejected by the existing RESIDUAL `PolicyAuthority`.

The worker revalidates its queue lease after engine execution and before evidence
commit. A result produced after lease expiry therefore cannot become
authoritative; the mission remains fail-closed and is quarantined as
`lease_expired` by the queue sweeper.

Adversarial qualification covers repository prompt injection, dirty-worktree
isolation, unknown repository aliases, oversized context/results, attempted tool
calls, provider self-approval metadata, wrong-template claims, and lease expiry.

This does **not** authorize the sandbox build/test or patch-proposal templates.
Those remain queued until a separate WorkerContract/OS-isolated execution adapter
is implemented and qualified.


## Enterprise convergence update

The earlier production-blocker list above described the first gateway-only implementation. The following blockers are now closed in this branch:

- bounded HTTP transport exists with strict JSON/content type/body limits, redacted logging, local throttling, and explicit TLS/reverse-proxy trust;
- production-shaped Entra helpers exist for fixed tenant JWKS refresh and fixed Microsoft Graph group-overage resolution;
- mission ownership and execution handoff are durable and encrypted through an injected CryptoProvider;
- read-only Firmware repository analysis executes through local non-provider-chat engines over frozen Git snapshots;
- Firmware build/test and Automated Testing isolated runs use the existing M4 namespace sandbox and deployment-owned command profiles;
- Firmware test triage produces proposal artifacts only after approved isolated test execution;
- Mechanical, Electromechanical, Automated Test Plan, and QA evidence reviews use the shared local read-only evidence worker;
- exact-head HITL challenges exist for future consequential external writes;
- member/reviewer/lead/auditor separation of duties is enforced in the gateway;
- five department agent/package manifests and Power Platform ALM source metadata are present;
- hybrid-Entra acceptance, package-drift, concurrency/abuse, and exact-head readiness bundle tests are in the dedicated matrix.

### External deployment gates that cannot be closed by repository code alone

1. Supply the real Entra tenant ID, API application/client ID, custom-connector client application ID, and production department/reviewer/lead/auditor group object IDs.
2. Apply and validate the organization's actual Conditional Access, MFA, hybrid-Entra/compliant-device policies.
3. Configure a production KMS/HSM-backed CryptoProvider and service credential source.
4. Import/configure the agents/custom connector in the target Power Platform development environment and export the tenant-owned managed solution ZIP.
5. Apply the organization's Power Platform DLP/environment governance/pipeline policies.
6. Run the hybrid-Entra walkthrough against real delegated tokens and the target enterprise edge/WAF/load-balancer.
7. Hash the exported managed solution ZIP and include it, the exact CI head, hosted scenario results, and deployment-config hash in the readiness bundle. Only a bundle with `release_eligible=true` should authorize production activation.

PR merge by itself is not equivalent to completing those tenant-owned deployment gates.

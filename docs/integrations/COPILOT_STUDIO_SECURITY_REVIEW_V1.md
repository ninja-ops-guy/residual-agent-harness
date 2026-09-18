# Copilot Studio Firmware v1 — security review and hardening record

Status: draft qualification
Scope: Copilot Studio custom connector -> RESIDUAL gateway boundary
Parent implementation: PR #292

## Security objective

A valid Copilot Studio conversation is not itself authorization to execute a
RESIDUAL capability. The gateway independently validates a Microsoft Entra
access token, projects only verified claims into a principal, applies immutable
department policy, compiles immutable capability grants, and binds all later
mission state/evidence to that exact authority.

Microsoft references used for the design:

- https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-custom-connector-on-behalf-of
- https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
- https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-enduser-authentication
- https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-no-maker-authentication

## Findings

### SR-001 — mutable/display identity as authorization key
Severity: High
Status: remediated

Using a token subject/display-style identifier as the durable mission owner
creates unnecessary identity ambiguity. The hardened boundary requires Entra
`tid` + immutable `oid`, and the control-plane principal is the verified
`oid`. The original token `sub` remains evidence context only.

### SR-002 — delegated scope not enforced
Severity: High
Status: remediated

A correctly signed token for the API audience is not sufficient authority. The
gateway now requires configured delegated scopes (default pilot:
`access_as_user`) from the verified `scp` claim.

### SR-003 — calling client not constrained
Severity: High
Status: remediated

The gateway now requires a configured `azp`/v2 or `appid`/v1 client ID
allowlist. This prevents another consented client from silently becoming an
equivalent RESIDUAL front end.

### SR-004 — tenant/department freshness
Severity: High
Status: remediated

The verified tenant must be explicitly allowed. Department group or app-role
membership is re-evaluated on submit, status, evidence and cancellation. A
mission does not preserve access after a later token no longer carries the
required department authority.

Group-overage tokens that omit the configured department group fail closed.
Automatic Microsoft Graph group expansion is intentionally not implemented in
v1; adding it would create a new network/data trust boundary.

### SR-005 — nested mutable authority
Severity: High
Status: remediated

Frozen dataclasses alone do not make nested mappings immutable. Capability
scope, constraints, approval policy and revision budget are recursively frozen
before their fingerprints/authority hashes become authoritative. Mutation
tests assert byte/hash stability.

### SR-006 — free-form tool inputs could become execution injection
Severity: High before Factory handoff
Status: remediated for gateway; Factory handoff still gated

The API still accepts a natural-language objective as untrusted data, but
authority is never inferred from that text. Each approved mission template now
has an exact structured input schema composed of opaque IDs. URLs, commands,
paths and undeclared keys are rejected at this boundary.

The later Factory adapter MUST resolve those opaque IDs through a server-side
approved-resource catalog. It MUST NOT reinterpret them as arbitrary shell,
path or network values.

### SR-007 — evidence not bound to authority revision
Severity: High
Status: remediated

Evidence references now carry mission ID, revision ID, plan hash, policy hash
and verified-claims hash. The store refuses an evidence reference whose binding
does not exactly match the current mission record.

### SR-008 — permissive mission state changes
Severity: Medium
Status: remediated

A strict transition graph replaces state-vocabulary-only validation. Prepared
missions cannot jump directly to complete; cancel-requested and terminal
missions cannot resume.

### SR-009 — replay state lost on restart
Severity: Medium
Status: remediated for pilot deployment

A transactional SQLite implementation preserves owner/request idempotency,
mission state and evidence bindings across process restart. The database is
created owner-only where POSIX permissions apply. Production deployment MUST
also protect the containing directory/volume with the host platform's ACL,
backup and encryption controls.

### SR-010 — mission fan-out exhaustion
Severity: Medium
Status: remediated at domain boundary

Request/body sizes remain bounded and policy now includes an atomic active
mission ceiling per tenant + principal. Generic HTTP rate limiting should remain
an API gateway/platform responsibility rather than being reimplemented inside
RESIDUAL.

### SR-011 — provider/parser error disclosure
Severity: Medium
Status: remediated

Authentication failures return a stable generic 401. Raw token/provider/parser
errors are not reflected. A request ID is reflected only after passing the
gateway's identifier grammar.

### SR-012 — maker credentials could become a confused deputy
Severity: High
Status: deployment control

The Copilot Studio tool must use end-user authentication/OBO for this
engineering integration. Maker-provided credentials are not accepted as an
equivalent security model. Power Platform environment policy should disable
maker-provided credentials for the governed engineering environment.

## Threat tests

The qualification suite covers:

- wrong tenant;
- wrong delegated scope;
- wrong calling client;
- wrong department;
- role-vs-group department authorization;
- identity/tenant/group/role/scope/client spoof fields in request bodies;
- natural-language prompt injection asking for prohibited authority;
- unknown templates;
- undeclared URL/command/path inputs;
- request replay and collision;
- claim/policy drift on replay;
- cross-subject mission/evidence/cancel access;
- loss of department membership between calls;
- nested authority mutation;
- illegal state transitions and terminal revival;
- stale/forged evidence binding;
- active-mission exhaustion;
- duplicate JSON keys and oversized payloads;
- generic authentication errors;
- transactional persistence across restart;
- stored-index corruption detection;
- real signed OIDC token validation and wrong-audience rejection.

## Remaining deployment gates

These are not defects to hide inside the connector implementation. They are
explicit deployment/integration gates:

1. Replace all example GUIDs with the real Entra tenant, group/app-role and
   connector client IDs.
2. Configure the RESIDUAL API app registration, exact issuer/audience, delegated
   `access_as_user` scope and OBO custom connector.
3. Enforce end-user credentials in the Power Platform environment.
4. Put the API behind enterprise TLS, ingress/WAF/rate limiting and approved
   network paths.
5. Store the SQLite database (or an enterprise replacement implementing the
   same contract) on an encrypted, ACL-protected, backed-up volume.
6. Send authorization/mission/evidence events to the organization's approved
   audit/SIEM path.
7. Implement the Factory adapter using only the prepared immutable authority and
   server-side resource catalog.
8. Run the positive Firmware and negative cross-department walkthrough in the
   actual tenant from the managed/hybrid-Entra device.
9. Do not claim device-compliance attestation inside RESIDUAL. Conditional
   Access/device compliance is an upstream Entra control unless a separately
   verified claim/policy integration is added.
10. No production writes, merges, policy changes, secret reads, arbitrary shell
    or arbitrary network access are introduced by this pilot.

## Security merge rule

This integration is not security-qualified merely because unit tests pass.
Merge consideration requires the exact PR head to pass the repository
qualification matrix and the security tests, with no unresolved High finding in
this document. Factory execution and Power Platform packaging remain separate
reviewable changes.

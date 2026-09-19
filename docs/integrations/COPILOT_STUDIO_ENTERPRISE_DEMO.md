# RESIDUAL × Copilot Studio enterprise acceptance walkthrough

## Environment

- Corporate Windows endpoint is hybrid Microsoft Entra joined.
- Conditional Access, MFA, and compliant-device policy are enforced upstream by Entra.
- Firmware Engineering custom agent is installed from the managed Power Platform solution.
- The custom connector uses end-user delegated authentication/OBO.
- RESIDUAL independently validates tenant, audience, scope, client app, user object ID, and department groups.
- Production-style queue encryption uses a non-development CryptoProvider.
- Firmware source repositories and build/test profiles are administrator-owned deployment resources.

RESIDUAL does not claim to attest device compliance itself. The acceptance report records those Microsoft controls as observed upstream controls only.

## Positive walkthrough

1. Firmware engineer opens the Firmware Engineering agent from Microsoft 365/Teams.
2. Engineer asks to investigate a firmware regression.
3. Copilot uses native knowledge retrieval for ordinary context and selects the RESIDUAL action when evidence-bound execution is required.
4. The custom connector presents the engineer's delegated Entra token to RESIDUAL.
5. RESIDUAL verifies identity and Firmware department membership.
6. A server-owned mission template selects the allowed capabilities. Prompt text cannot widen them.
7. The mission is deterministically compiled and bound to tenant, user object ID, department, request hash, template, and Factory plan hash.
8. Mission content enters the encrypted durable queue.
9. A template-specific worker claims the mission with a bounded lease.
10. Repository analysis reads only administrator-selected UTF-8 files from a frozen Git commit and uses a local non-provider-chat engine.
11. Sandbox build/test uses only administrator-owned command profiles inside the existing M4 namespace isolation boundary.
12. Test triage produces proposal artifacts only; it cannot write Git, create a PR, merge, or deploy.
13. Evidence, engine provenance, snapshot hashes, command-result hashes, and terminal state are committed to the encrypted evidence ledger.
14. Copilot retrieves the authorized result/evidence reference and presents it to the engineer.

## Consequential-write walkthrough

A future configured external write, such as creating a draft PR, must create an `ExternalWriteIntent` bound to mission ID, mission binding hash, plan hash, exact evidence hash, action, and target. A RESIDUAL HITL challenge is issued. Approval of a different evidence head is rejected. Replayed approvals are rejected. Copilot's own confirmation UI is additive and cannot replace RESIDUAL approval.

The v1 enterprise pilot keeps PR merge and production deployment prohibited.

## Negative trial-by-fire scenarios

| Scenario | Required result |
| --- | --- |
| Mechanical user calls Firmware mission | Denied without mission disclosure |
| Former Firmware member retries old mission | Evidence/status access revoked |
| Reviewer reads Firmware evidence | Allowed only through reviewer group |
| Reviewer tries to cancel | Denied |
| Engineering lead cancels department mission | Allowed |
| Auditor reads evidence | Allowed read-only |
| Auditor cancels/executes | Denied |
| Token has wrong tenant/audience/scope/client app | 401 fail closed |
| HS256/unsigned/malformed token | 401 fail closed |
| Token group overage supplies endpoint | Endpoint ignored; fixed Graph resolver only |
| Prompt requests shell/merge/deploy/secrets | Capabilities unchanged |
| Structured input contains URL/path/role/capabilities | Rejected |
| Repository file contains prompt injection | Treated as untrusted data; no tools/authority |
| Cloud/provider-chat engine selected for Firmware source | Rejected before source disclosure |
| Build profile not configured | No command executes |
| Isolation unavailable | Mission fails; no unsandboxed fallback |
| Test/build command times out or exceeds output | Deterministic fail/timeout evidence |
| Worker lease expires during inference | Result cannot become authoritative |
| Cancellation races with worker completion | Completion rejected after cancellation request |
| Queue ciphertext modified | Claim rejected before lease commit |
| Duplicate request storm | One deterministic mission |
| Same request ID with different payload | 409 conflict |
| Mission ID enumeration | Uniform not-found response |
| External-write approval becomes stale | Rejected |
| Approval replay | Rejected |

## Release evidence

Run the Copilot integration matrix on Python 3.11, 3.12, and 3.13, existing RESIDUAL regression gates, hybrid-Entra walkthrough, and hosted load/security tests against one exact release head. Build `residual.copilot.enterprise-readiness.v1` with those qualification records, deployment configuration hash, scenario results, known limitations, and exported managed-solution ZIP hash.

Agent Library template stays Inactive until that bundle verifies.

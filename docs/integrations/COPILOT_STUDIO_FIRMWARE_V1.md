# Copilot Studio Firmware Engineering integration v1

Status: experimental / draft PR
Baseline: `3cff6bcd52e352a6ba048c958949a7bbb2a039eb`

## Objective

Expose RESIDUAL as a bounded, evidence-producing execution tool to a Microsoft Copilot Studio custom agent without recreating Copilot Studio's native orchestration, knowledge, template, authentication, or Power Platform governance features.

The first vertical is Firmware Engineering. This PR is specification-first: it freezes the trust boundary, API contract, departmental profile, qualification plan, security review plan, and demo acceptance criteria before runtime implementation.

## Native-first boundary

Copilot Studio owns:
- conversational UX and generative orchestration;
- selection of configured tools, topics, knowledge, and connected agents;
- end-user authentication for the custom connector;
- Entra consent and OBO token acquisition;
- Power Platform solution packaging, environment governance, DLP, and Agent Library distribution;
- optional user confirmation for data-modifying tools.

RESIDUAL owns:
- validation of the bearer token and relevant Entra claims at its API boundary;
- fail-closed mapping of authenticated claims to a RESIDUAL department profile and authority;
- MissionSpec compilation, Factory/swarm execution, verifier/integrator behavior, evidence, receipts, brakes, quarantine, HITL, and cancellation;
- independent authorization of every consequential RESIDUAL capability.

Do not copy SharePoint/Dataverse knowledge into a new RESIDUAL RAG layer solely for this integration. Do not implement a second Copilot intent router. Do not trust Copilot-side authorization as sufficient authorization for RESIDUAL.

## Trust boundary

```
User -> Copilot Studio -> Entra/OBO custom connector -> RESIDUAL Enterprise Gateway
                                                  |
                                                  +-> claims -> policy -> MissionSpec
                                                                   |
                                                               Factory
                                                                   |
                                                    evidence / receipt / approval
                                                                   |
                                                             Copilot result
```

The connector MUST use end-user authentication for user-specific engineering work. Maker credentials MUST NOT authorize a Firmware Engineering mission.

The API MUST reject missing, expired, wrong-issuer, wrong-audience, unsigned, malformed, or otherwise unverified tokens. The verified `tid` MUST match an explicit deployment tenant allowlist. Department/group claims are authorization inputs only after token verification; production deployments SHOULD use stable Entra group object IDs or app-role values rather than display names.

A request MUST be bound to authenticated tenant + subject + department profile + mission id + request id. Caller-supplied subject, tenant, department, or role fields MUST NOT override verified identity claims.

## Minimal API

The first connector intentionally stays small:

- `POST /v1/copilot/missions` — submit one bounded mission.
- `GET /v1/copilot/missions/{mission_id}` — retrieve state and safe summary.
- `GET /v1/copilot/missions/{mission_id}/evidence` — retrieve evidence/receipt references permitted to the caller.
- `POST /v1/copilot/missions/{mission_id}/cancel` — request cancellation.

No merge, production deployment, policy modification, module installation, credential administration, or unrestricted shell endpoint exists in v1.

### Submission

Required logical fields:
- `request_id`: caller-generated idempotency key.
- `template_id`: approved mission template identifier.
- `objective`: bounded natural-language objective.
- `inputs`: template-defined structured inputs.

Identity is derived from the verified token, never from the body.

### Response

Return:
- mission id;
- state;
- selected approved template/profile;
- risk classification;
- whether human approval is required;
- evidence/receipt reference when available.

Do not return bearer tokens, raw secrets, provider credentials, unrestricted internal prompts, or unrelated evidence.

## Department profile schema

Profiles are data, not forks. A profile declares:
- Entra tenant allowlist;\n- Entra group/app-role allowlist;
- approved mission templates;
- allowed RESIDUAL capabilities;
- prohibited capabilities;
- assigned agent roles;
- approved knowledge/tool references;
- risk ceiling;
- approval requirements.

The Firmware v1 profile is in `residual/integrations/copilot_studio/profiles/firmware.yaml`.

Future profiles: mechanical, electromechanical, automated-testing, quality-assurance. They MUST reuse the same schema and enforcement path.

## Firmware v1 authority

Allowed:
- repository analysis;
- sandbox build;
- approved test execution;
- proposed patch generation;
- evidence generation;
- draft PR proposal/creation only when a separately configured Git capability authorizes it.

Denied by default:
- PR merge;
- production write/deploy;
- policy modification;
- qualification bypass;
- verifier bypass;
- secret retrieval;
- arbitrary network destinations;
- arbitrary host shell;
- cross-department evidence access.

Consequential external writes require RESIDUAL HITL even when Copilot Studio also asks for confirmation.

## Idempotency and replay

`request_id` is unique within tenant + subject for a bounded retention window. Repeating the same request with identical canonical payload returns the existing mission. Reusing the id with a different payload is rejected and receipted.

Approval is bound to exact mission/evidence head. Mutation after approval invalidates approval.

## Qualification gates

Before implementation can leave draft:

1. Contract tests: OpenAPI shape, required fields, stable error schema.
2. Authentication: missing/malformed/expired/wrong aud/wrong iss tokens fail closed.
3. Authorization: allowed group works; absent group, wrong department, cross-tenant, cross-department fail.
4. Identity-confusion: body identity fields cannot elevate authority.
5. Replay/idempotency: duplicate-identical is stable; duplicate-different fails.
6. Mission boundary: prohibited capabilities cannot be requested through free text or structured inputs.
7. Evidence ACL: another user/department cannot fetch evidence.
8. Cancellation: bounded, idempotent, and cannot cancel another caller's mission without explicit authority.
9. Prompt/tool injection: malicious objective, knowledge, and tool output cannot widen capabilities.
10. Failure paths: verifier disagreement, worker failure, timeout, partial evidence, connector retry, and RESIDUAL restart preserve fail-closed state.
11. Logging: tokens/secrets are redacted; authorization decisions and request/mission bindings are observable.
12. Existing RESIDUAL regression and enterprise suites remain green.

## Security review

Threat model MUST explicitly test:
- token substitution and confused deputy;
- OBO scope/audience mistakes;
- forged group/department claims in request bodies;
- replay and request-id collision;
- cross-tenant and cross-department data access;
- indirect prompt injection from engineering documents/tool output;
- SSRF and arbitrary network targets;
- arbitrary shell/command injection;
- forged/stale approval;
- evidence tampering;
- credential leakage in observations/errors;
- denial-of-service via payload size, fan-out, or repeated polling;
- race between authorization, approval, and execution.

Hardening findings are fixed in a separate reviewable commit/PR phase; no finding is silently waived.

## Copilot-native packaging

The production package SHOULD be a Copilot Studio custom agent template packaged as a Power Platform solution with connection references/environment variables, suitable for Agent Library installation. The RESIDUAL API is exposed as a custom connector using Microsoft Entra ID and OBO. Generative orchestration selects the tool; RESIDUAL does not duplicate it.

## Hybrid Entra demo acceptance

The walkthrough models a compliant corporate Windows endpoint that is hybrid Entra joined. Device compliance/Conditional Access is an upstream Microsoft control; RESIDUAL consumes only validated token claims and MUST NOT claim to independently attest device compliance unless a separately verified claim/policy integration is implemented.

Demo:
1. User opens Firmware Engineering agent.
2. User requests analysis of a sample firmware defect.
3. Copilot selects the RESIDUAL tool.
4. OBO authenticates the end user.
5. RESIDUAL validates identity and firmware membership.
6. A bounded analysis/sandbox-test mission is compiled.
7. Workers run only approved capabilities.
8. Verifier evaluates evidence.
9. Any external write pauses for HITL.
10. Copilot receives status plus evidence/receipt reference.
11. Negative walkthrough repeats as a Mechanical user and is denied the Firmware-only mission without leakage.

## Exit criteria

V1 is complete only when the connector works end-to-end in a test environment, qualification gates are green, the security review has no unresolved high-severity findings, the negative role walkthrough passes, and evidence demonstrates that Copilot-side configuration cannot bypass RESIDUAL authorization.

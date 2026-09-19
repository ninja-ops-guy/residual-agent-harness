# RESIDUAL Web Command Station — Control-Plane Boundary

Status: proposed implementation
Branch: `web/command-station-control-plane`

## Purpose

Vercel hosts the internet-facing RESIDUAL Web Command Station. It is a control plane, not a worker runtime. GitHub Pages remains the public static documentation/demo surface.

## Trust boundary

```
Browser
  |
  v
Vercel Web Command Station
  | authenticated, authorized, bounded requests
  v
RESIDUAL gateway
  | policy + capability enforcement
  v
isolated RESIDUAL worker / mesh node
  |
  +--> provider/model
  +--> approved MCP/tool capabilities
  +--> Evidence Bus / receipts
```

No browser or Vercel client bundle receives worker credentials, provider secrets, Ollama/MCP network access, GitHub tokens, or mesh credentials.

## Fail-closed invariants

1. Web requests are untrusted input. Client claims such as `approved=true` never constitute authority.
2. Every mutating operation binds authorization to an authenticated principal, mission ID, action, target, and immutable request digest.
3. HITL approval binds to the exact pending action/evidence identity and expires; stale/replayed approval fails closed.
4. The gateway rejects unknown fields, oversized identifiers/payloads, invalid state transitions, and unsupported capabilities.
5. Provider/transport errors are explicit observable terminal or blocked outcomes; they cannot become success.
6. Vercel never executes arbitrary model-generated code. Execution occurs only in isolated RESIDUAL workers.
7. Worker credentials are least-privilege, scoped, short-lived where supported, and never returned to the browser.
8. Evidence/receipt identity is computed server-side and cannot be supplied as authoritative by the client.
9. A disconnected UI cannot infer success. Reconnect obtains authoritative mission state from RESIDUAL.
10. Public demo mode has no privileged tool capability by default.

## Initial API surface

- `POST /api/missions` — submit a bounded mission request.
- `GET /api/missions/{id}` — authoritative status projection.
- `GET /api/missions/{id}/events` — read-only event stream/projection.
- `POST /api/missions/{id}/approvals` — exact-action HITL approval/rejection.
- `POST /api/missions/{id}/cancel` — request cancellation.
- `GET /api/capabilities` — capabilities available to the authenticated principal.

The Vercel API is an adapter to the RESIDUAL gateway. It must not duplicate scheduler, verifier, evidence, worker, or policy semantics.

## Modes

- **Demo:** read-only or tightly scripted disposable execution; no privileged tools.
- **Pair:** one user-directed mission with bounded worker capabilities.
- **Team:** coordinator + workers with per-role capabilities and HITL.
- **Factory:** multi-worker orchestration; disabled until the gateway and isolation qualification gates pass.

## Security requirements

- HTTPS only.
- Authentication required for non-demo mutation.
- Server-side authorization on every mutation.
- CSRF/origin protections appropriate to the chosen auth mechanism.
- Strict request schemas and explicit byte/length limits.
- Rate limiting and abuse controls at the public boundary.
- Security headers/CSP suitable for the Command Station.
- Secrets only in server-side environment configuration.
- No wildcard CORS to private gateways.
- Gateway egress allowlist; private workers do not accept arbitrary internet ingress.
- Request IDs and correlation IDs propagated into evidence without treating them as authority.
- Logs redact prompts/secrets/tool payloads according to policy.

## Qualification gates before live execution

- WEB-F0: browser cannot address worker/MCP/Ollama directly.
- WEB-F1: forged approval cannot authorize an action.
- WEB-F2: stale/replayed approval is rejected.
- WEB-F3: unauthorized capability request is rejected before dispatch.
- WEB-F4: malformed/oversized payload fails closed.
- WEB-F5: gateway/provider failure cannot surface as PASS.
- WEB-F6: disconnect/reconnect preserves authoritative state.
- WEB-F7: cross-user mission access is denied.
- WEB-F8: secrets absent from client bundles, responses, and sanitized logs.
- WEB-F9: public demo cannot escape its capability profile.
- WEB-F10: evidence identity and terminal outcome remain server-authoritative.

## Rollout

Phase 0: architecture/spec + static Command Station shell.
Phase 1: read-only status/evidence projection.
Phase 2: authenticated mission submission against a mock/scripted gateway.
Phase 3: isolated disposable worker execution after WEB-F0..F10 pass.
Phase 4: HITL + Pair mode.
Phase 5: Team mode and mesh routing.
Phase 6: Factory mode only after independent security/qualification review.

## Hosting split

GitHub Pages remains the canonical public docs/demo entry point. Vercel becomes the Web Command Station application. The public site should link to the Command Station only when the corresponding phase is qualified; until then label it preview/experimental.

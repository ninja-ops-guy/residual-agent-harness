# Kimi Claw / OpenClaw onboarding for RESIDUAL

Status: supported integration path for the `kimi_claw` provider.

This runbook is intentionally stricter than generic OpenClaw setup because the
OpenAI-compatible Gateway credential is an **owner/operator credential**. RESIDUAL
therefore supports Kimi Claw through a loopback OpenClaw Gateway only.

## 1. Do not confuse the three Kimi paths

### A. Kimi-hosted Kimi Claw

Kimi can deploy an OpenClaw instance for you from `kimi.com/bot`. Kimi currently
documents this as a managed deployment with its model/search configuration handled
for you and no separate API setup required.

**RESIDUAL does not assume that a Kimi-hosted managed Claw exposes an operator
Gateway URL/token.** Do not scrape browser cookies, membership tokens, Kimi session
credentials, or undocumented endpoints to make it work.

If Kimi later documents an external Gateway integration surface, qualify that
surface separately before enabling it.

### B. Existing/self-hosted OpenClaw linked to Kimi

This is the supported `kimi_claw` adapter path. The Kimi plugin may link your
existing OpenClaw to Kimi's UI, while RESIDUAL talks only to the local OpenClaw
Gateway.

### C. Direct Moonshot/Kimi API

Use RESIDUAL's `moonshot` provider instead. This is not Kimi Claw and does not
carry OpenClaw agent memory, tools, workspace, or policy.

OpenClaw itself also distinguishes Moonshot and Kimi Coding providers. Their API
keys, endpoints, and model references are not interchangeable.

## 2. Onboard OpenClaw first

Follow current OpenClaw onboarding rather than editing state files by hand:

```bash
openclaw onboard
openclaw gateway status
```

The Gateway normally listens on port `18789`.

If the OpenClaw agent should use Moonshot Kimi K3, use OpenClaw's current Moonshot
provider onboarding:

```bash
openclaw plugins install @openclaw/moonshot-provider
openclaw onboard --auth-choice moonshot-api-key
openclaw models set moonshot/kimi-k3
openclaw models list --provider moonshot
```

For Kimi Coding, use OpenClaw's separate Kimi provider/plugin and `KIMI_API_KEY`.
Do not place a Kimi Coding membership key in `MOONSHOT_API_KEY`.

## 3. Create a dedicated RESIDUAL agent

Do not target a personal/default agent for measured swarm work unless that is the
explicit experimental condition.

Example:

```bash
openclaw agents add residual \
  --workspace ~/.openclaw/workspace-residual \
  --non-interactive
```

Then review the agent's sandbox and tool policy. A RESIDUAL experiment should
freeze this policy as part of its provider/runtime snapshot.

Recommended baseline:

- dedicated agent id and workspace;
- sandbox enabled for the dedicated agent;
- `scope: "session"` when experiment sessions must not share a container;
- `workspaceAccess: "none"` or `"ro"` unless write access is part of the test;
- no elevated execution;
- deny session/sub-agent spawning unless the experimental arm explicitly studies it;
- allow only the tools required by the frozen experiment.

OpenClaw tool policy and sandbox policy are separate controls. Denying `write`
does not make an allowed shell/exec tool read-only.

## 4. Enable the Chat Completions endpoint explicitly

OpenClaw's `POST /v1/chat/completions` endpoint is disabled by default.

Enable:

```bash
openclaw config set gateway.http.endpoints.chatCompletions.enabled true
openclaw gateway restart
openclaw gateway status
```

Equivalent config:

```json5
{
  gateway: {
    mode: "local",
    bind: "loopback",
    http: {
      endpoints: {
        chatCompletions: { enabled: true }
      }
    }
  }
}
```

Do not make the Gateway public merely to connect RESIDUAL.

## 5. Gateway authentication

Preferred: token/password auth with a secret reference, not a copied plaintext
secret in repository config.

OpenClaw's documented environment names are:

- `OPENCLAW_GATEWAY_TOKEN`
- `OPENCLAW_GATEWAY_PASSWORD`

RESIDUAL also accepts `KIMI_CLAW_TOKEN` as an integration-specific alias and
`RESIDUAL_LOCAL_API_KEY` as the existing generic local-provider override.

Example non-interactive token setup:

```bash
export OPENCLAW_GATEWAY_TOKEN='...'
openclaw onboard --non-interactive --accept-risk \
  --mode local \
  --secret-input-mode ref \
  --gateway-auth token \
  --gateway-token-ref-env OPENCLAW_GATEWAY_TOKEN
```

The bearer token/password must never be written into task packets, experiment
manifests, provider snapshots, traces, receipts, or paper artifacts. If multiple
Gateway secret environment variables are set to different values, RESIDUAL fails
configuration rather than guessing which auth mode is active.

## 6. RESIDUAL provider configuration

Use an OpenClaw **agent target**, not a raw Kimi model id:

```toml
[local]
kind = "kimi_claw"
model = "openclaw/residual"
base_url = "http://127.0.0.1:18789/v1"
```

Accepted target forms follow OpenClaw's agent-first contract:

- `openclaw`
- `openclaw/default`
- `openclaw/<agentId>`
- `openclaw:<agentId>`
- `agent:<agentId>`

Do **not** set `model = "kimi-k3"` or `model = "moonshot/kimi-k3"` on the
`kimi_claw` provider. Configure the selected OpenClaw agent's backend model in
OpenClaw itself.

RESIDUAL deliberately does not send `x-openclaw-model`; overriding the agent's
backend model is an operator/admin action and would weaken experiment provenance.

## 7. Smoke test before RESIDUAL

With token/password auth:

```bash
curl -sS http://127.0.0.1:18789/v1/models \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN"
```

Confirm that the intended target appears, preferably `openclaw/residual` (or
`openclaw/default` for a deliberate default-agent test).

Then run one isolated message through the Gateway before starting a measured
experiment.

## 8. Session handling

OpenClaw creates a new session for each Chat Completions request by default.

Its OpenAI-compatible `user` field creates a stable session key. RESIDUAL exposes
this field as an allowlisted adapter option, but experiments must scope it to a
single conversation/attempt, for example:

```
residual:EXP-NESTED-SWARM-001:<arm>:<trial>:<task>:<attempt>
```

Do not use a user/account-wide identifier unless session sharing across tasks is
explicitly part of the experiment. Cross-task memory would contaminate independent
trial cells.

Explicit `x-openclaw-session-key` routing is not used by the RESIDUAL adapter.

## 9. Remote OpenClaw

OpenClaw supports remote/private Gateway deployments, but RESIDUAL's v1 Kimi Claw
adapter intentionally rejects non-loopback base URLs because the shared Gateway
secret has operator authority.

If the Gateway lives on another trusted machine, establish an authenticated private
tunnel and expose it locally, then keep:

```
http://127.0.0.1:18789/v1
```

as the RESIDUAL endpoint.

Do not point `KIMI_CLAW_BASE_URL` at a public internet host. The v1 adapter also
intentionally does not accept OpenClaw's Docker-specific `host.docker.internal`
shortcut; containerized RESIDUAL deployments should use an explicitly reviewed
local networking/tunnel design rather than weakening the operator-credential
origin check.

## 10. Research Workbench requirements

Before an A/B/C/D measured run, record without secrets:

- OpenClaw version/revision;
- selected agent target;
- backend provider and model revision;
- agent tool policy hash;
- sandbox mode/scope/workspace policy;
- enabled plugins/skills relevant to the task;
- session policy (stateless vs stable `user`);
- WorkerContract hash;
- RESIDUAL runtime revision;
- task/corpus hashes.

A configuration change after preregistration is runtime drift and should invalidate
or separately classify the affected trial.

## Upstream references

- https://www.kimi.com/en/help/kimi-claw/overview
- https://docs.openclaw.ai/start/onboarding-overview
- https://docs.openclaw.ai/cli/onboard
- https://docs.openclaw.ai/gateway/openai-http-api
- https://docs.openclaw.ai/gateway/security/tool-permissions
- https://docs.openclaw.ai/tools/multi-agent-sandbox-tools
- https://docs.openclaw.ai/providers/moonshot

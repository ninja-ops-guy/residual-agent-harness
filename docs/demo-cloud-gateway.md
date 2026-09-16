# Ephemeral cloud demo gateway

The public browser VM remains fully functional offline. When `RESIDUAL_DEMO_GATEWAY_URL` is configured for GitHub Pages, `/demo/` first attempts to provision a bounded cloud session and falls back to the offline scripted providers on any error.

## Trust boundary

The browser never receives a FreeLLMAPI admin credential or FreeLLMAPI client-profile key. The gateway creates a per-session client profile through FreeLLMAPI's authenticated admin API, stores that profile key server-side, and returns only an opaque `rdemo_...` session token. Inference is proxied through the gateway. On expiry/reset, the gateway disables the local session and deletes the FreeLLMAPI profile.

The browser does receive a one-off Tailscale auth key because WebVM needs it to join the demo network. That key is created as non-reusable, ephemeral and preauthorized, tagged `tag:residual-demo`, and expires no later than the demo session.

## Required gateway secrets

Set these only on the gateway host:

- `FREELLMAPI_BASE_URL`
- `FREELLMAPI_ADMIN_EMAIL`
- `FREELLMAPI_ADMIN_PASSWORD`
- `TAILSCALE_OAUTH_CLIENT_ID`
- `TAILSCALE_OAUTH_CLIENT_SECRET`

Optional policy/config values:

- `RESIDUAL_DEMO_ORIGIN` — exact Pages origin, default `https://ninja-ops-guy.github.io`
- `RESIDUAL_DEMO_TTL_SECONDS` — default `900`
- `RESIDUAL_DEMO_MAX_REQUESTS` — default `8`
- `RESIDUAL_DEMO_MAX_TOKENS` — default `4096`
- `RESIDUAL_DEMO_MAX_OUTPUT_TOKENS` — default `512`
- `TAILSCALE_DEMO_TAG` — default `tag:residual-demo`
- `TAILSCALE_TAILNET` — default `-`
- `RESIDUAL_DEMO_DB` — SQLite path; use persistent storage in production

## Tailscale policy

Create an OAuth client with only the `auth_keys` scope and authority to mint `tag:residual-demo`. Use a customized tailnet policy so the demo tag can use an exit node but cannot reach private tailnet destinations. The intended grant is:

```json
{
  "tagOwners": {
    "tag:residual-demo": ["autogroup:admin"]
  },
  "grants": [
    {
      "src": ["tag:residual-demo"],
      "dst": ["autogroup:internet"],
      "ip": ["*"]
    }
  ]
}
```

Do not add grants from `tag:residual-demo` to other tailnet tags, users, private CIDRs, or hosts. `autogroup:internet` excludes private, Tailscale CGNAT, and link-local address ranges by definition.

A tailnet exit node must already exist and WebVM must be configured to use it. The browser VM's Tailscale key is one-off and ephemeral; the FreeLLMAPI profile remains separately revocable by the gateway.

## Gateway deployment

The gateway is dependency-free Python and can run anywhere with persistent storage:

```bash
docker build -f demo/cloud_gateway/Dockerfile -t residual-demo-gateway .
docker run --rm -p 8080:8080 \
  -e FREELLMAPI_BASE_URL=... \
  -e FREELLMAPI_ADMIN_EMAIL=... \
  -e FREELLMAPI_ADMIN_PASSWORD=... \
  -e TAILSCALE_OAUTH_CLIENT_ID=... \
  -e TAILSCALE_OAUTH_CLIENT_SECRET=... \
  -v residual-demo-state:/state \
  -e RESIDUAL_DEMO_DB=/state/gateway.sqlite3 \
  residual-demo-gateway
```

Expose it only over HTTPS. Then set repository variable `RESIDUAL_DEMO_GATEWAY_URL` to that HTTPS origin and redeploy Pages.

## Session behavior

1. `/demo/` fetches `cloud.json`.
2. If a gateway is configured, it calls `POST /v1/demo/session`.
3. The gateway mints the FreeLLMAPI client profile and one-off ephemeral Tailscale key.
4. The page passes only the demo token and Tailscale auth key into WebVM through the URL fragment.
5. WebVM injects `LLM_BASE_URL=<gateway>/v1` and `LLM_API_KEY=<opaque demo token>` into the guest environment.
6. `cloud-demo` runs the actual RESIDUAL harness against `auto:fast`, then verifies the emitted trace.
7. Reset/page close calls `DELETE /v1/demo/session`; expired sessions are also cleaned on subsequent gateway requests.

Every proxied request reserves one request slot and its requested output-token allowance atomically before contacting FreeLLMAPI. Allowed models are limited to `auto`, `auto:fast`, and `auto:smart`.

# FCC continuity standby (experimental, disabled by default)

Free Claude Code (FCC) fits as a **separately operated inference proxy** for
availability failover. This does not install coding agents, grant filesystem or
shell access, reuse subscription logins, or merge/deploy the integration.
Residual still owns tasks, policy, verification and review.

## Placement and behavior

Use `free_claude_code` only in Station's `cloud_fallbacks` or the provider Router's
explicit `failover` list. Primary and local profiles reject this lane. In Model
Workshop, expand **Cloud failover order**, add FCC, select an exact
`provider/model` ID, configure permitted routes and confirm the dedicated-server
contract below. The credential field takes the **FCC proxy token**, not an
upstream provider key. Existing defaults remain unchanged.

- A healthy primary never constructs or calls FCC, even if its token is missing.
- Retryable connection/timeouts, HTTP 429 and 5xx can advance to FCC in the
  configured order. Authentication, bad configuration, malformed responses and
  policy failures do not trigger it. No replay of a partially emitted stream.
- One Residual request per candidate; FCC has no client-side retry loop. A later
  explicit direct fallback may run after an FCC availability failure. Every new
  request starts with the primary again, so recovery restores the normal route.
- Only non-streaming, text/JSON inference with a 1–16,000 output-token cap is
  supported. No tools, tool history, agent sessions, fusion, model aliases, seed
  or extra reasoning controls. JSON schema is a prompt, not a provider guarantee;
  Residual validates the returned task proposal and its acceptance checks.
- FCC cannot perform approval review. A review that reaches this lane stops and
  requires a local/direct reviewer; it is never silently approved.
- Two in-flight calls per identical FCC base URL per process, shared across
  adapter instances. This is not a distributed account-level quota limiter.
- A 30-second socket timeout, 2 MB response limit, no redirects, no ambient HTTP
  proxies. The timeout is not a hard whole-operation deadline, and closing the
  client connection cannot prove that upstream inference stopped.

## Required dedicated-server contract

Reviewed FCC commit:
[`bf59598ccc04b02befa1d649dfbcc569534c365c`](https://github.com/Alishahryar1/free-claude-code/tree/bf59598ccc04b02befa1d649dfbcc569534c365c),
version 6.2.23. Its Python requirement is >=3.14; run it in a separate environment
or container. Do not add it to Residual's dependency-free Python >=3.11 runtime.
No FCC code is vendored or executed by this adapter.

Before confirming the standby, the operator must:

1. Pin the reviewed server revision and restrict access to its admin interface.
   Bind to loopback, or use an authenticated HTTPS boundary for another host.
   Residual accepts only a root URL (no `/v1` suffix).
2. Enable `PROXY_AUTH_ENABLED=true`; set `ANTHROPIC_AUTH_TOKEN` to a unique,
   non-default secret. Use that same secret as Residual's `FCC_PROXY_API_KEY` or
   saved FCC credential. The adapter refuses FCC's example `freecc` token.
3. Leave `MODEL_FALLBACKS` empty and configure only approved upstreams. Avoid
   chaining FCC into FreeLLMAPI or another automatic router. The first integration
   supports `groq`, `nvidia_nim`, `lmstudio`, and `llamacpp`, which use the reviewed
   shared Chat transport. Subscription-backed routes are intentionally excluded.
4. Disable `ENABLE_WEB_SERVER_TOOLS`, `FAST_PREFIX_DETECTION`,
   `ENABLE_NETWORK_PROBE_MOCK`, `ENABLE_TITLE_GENERATION_SKIP`,
   `ENABLE_SUGGESTION_MODE_SKIP`, and `ENABLE_FILEPATH_EXTRACTION_MOCK`.
   Set `MESSAGING_PLATFORM=none`, `VOICE_NOTE_ENABLED=false`, and do not launch
   FCC agent/browser/messaging sessions. Keep raw prompt/SSE logging disabled.
5. Configure appropriate server concurrency/timeouts and only authorized upstream
   API keys/local services. Restrict provider egress at the server boundary.
   A permitted request ID is **not** a network allowlist or server attestation.

`fcc_standby_confirmed` records the operator's assertion of this contract. Residual
does not inspect the server's secrets/admin configuration or remotely prove its
version, authentication enforcement, route, or transformations. Keep this lane
off if that configuration cannot be established. Revalidate after upstream updates.

For independent continuity, select an upstream outside the primary's failure
domain. Reusing the same account through two gateways shares quotas; it does not
multiply free capacity. Local inference may provide a useful independent lane,
but FCC is conservatively classified as cloud even at a loopback address.

## Settings example

With a primary cloud profile already configured, submit this partial settings
object through the authenticated Station settings API, or use Model Workshop:

```json
{
  "cloud_fallbacks": [{
    "kind": "free_claude_code",
    "model": "groq/YOUR_MODEL_ID",
    "base_url": "http://127.0.0.1:8082",
    "gateway_allowed_routes": ["groq/YOUR_MODEL_ID"],
    "fcc_standby_confirmed": true
  }]
}
```

This replaces the fallback list: preserve other desired profiles explicitly.
Supply the proxy token separately in `FCC_PROXY_API_KEY` or the provider-scoped
credential UI. Project cloud-sharing permission and call budgets still apply.
Do not enable until the dedicated-server contract is true.

For the low-level `ai_providers.Router`, configure `FCC_BASE_URL`,
`FCC_PROXY_API_KEY`, `FCC_ALLOWED_ROUTES` (comma-separated), and
`FCC_STANDBY_CONFIRMED=1`; add `free_claude_code:groq/YOUR_MODEL_ID` to `failover`.
The standalone CLI's primary/expert provider slots are not continuity chains and
do not support FCC as a primary. Use Station or the Router for this experiment.

## Accounting and provenance

The reviewed FCC application returns the **original requested model name**, even
when an internal fallback was used. Matching that name is only an echo sanity
check. Reports therefore keep `actual_provider`, `actual_model`, and
`upstream_attempts_reported` null. Prompts, thinking blocks, arbitrary upstream
metadata, raw error strings and credentials are not copied into audit reports.
Request/response hashes bind the local record to observed bytes; they are not
signatures or proof of inference.

Reserve five call units before each FCC attempt. The reviewed shared Chat
transport uses one five-attempt admission budget, including recovery. This
reservation assumes the dedicated-server contract; it is not a remote enforcement
limit and does not cover arbitrary nested gateways. No refunds are inferred from
the response. Actual upstream attempts remain unknown, including failed attempts.

Reported successful-hop tokens are diagnostic only. Authoritative usage remains
unavailable because total work and any estimation cannot be verified. Existing
unknown-usage brakes stop automatic batch expansion; this is bounded continuity
for individual tasks, **not a promise of unattended endless swarms or zero cost**.
Metrics distinguish `continuity_fallback_calls`, `gateway_attempts_unknown`, and
`gateway_accounting_incomplete` from reported upstream counts.

## Verification and rollout gate

Offline tests inject primary outages, recovery, terminal errors, missing keys,
FCC failure, malformed/tool responses, timeouts, concurrency saturation, quota
exhaustion, cloud policy, independent review and unknown-usage batch brakes.

```sh
python -m unittest tests.modular.test_fcc_continuity -v
python -m unittest discover -s tests -v
npm run check:ui
npm run test:ui
```

The opt-in live smoke test uses a synthetic prompt and a simulated primary outage;
it never sends project source. Configure the four FCC environment values above,
set `RESIDUAL_FCC_LIVE_TEST=1`, then run:

```sh
python -m unittest tests.modular.test_fcc_live -v
```

It may consume upstream quota. An actual FCC server/token, confirmation of its
configuration and the live smoke test are required before production activation.
Mock success alone does not establish live compatibility, service continuity or
cost savings. Remove FCC from `cloud_fallbacks` to roll back without changing the
primary. Nothing should auto-merge or auto-enable this lane.

Source contracts inspected: [API routes](https://github.com/Alishahryar1/free-claude-code/blob/bf59598ccc04b02befa1d649dfbcc569534c365c/src/free_claude_code/api/routes.py),
[model routing](https://github.com/Alishahryar1/free-claude-code/blob/bf59598ccc04b02befa1d649dfbcc569534c365c/src/free_claude_code/application/routing.py),
[execution and response identity](https://github.com/Alishahryar1/free-claude-code/blob/bf59598ccc04b02befa1d649dfbcc569534c365c/src/free_claude_code/application/execution.py),
[admission budget](https://github.com/Alishahryar1/free-claude-code/blob/bf59598ccc04b02befa1d649dfbcc569534c365c/src/free_claude_code/providers/admission.py),
[settings](https://github.com/Alishahryar1/free-claude-code/blob/bf59598ccc04b02befa1d649dfbcc569534c365c/src/free_claude_code/config/settings.py).

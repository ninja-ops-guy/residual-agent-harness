# Experimental FreeLLMAPI integration

Status: isolated integration branch, not a production certification. FreeLLMAPI
is an optional cloud provider behind the existing Residual router. It does not
replace GoalSpec, task dependencies, host checks, review, quarantine or brakes.
No subscription credentials, browser sessions or quota circumvention are used.

## What this branch implements

- `freellmapi` registry adapter and CLI/TOML configuration.
- Model Workshop provider selection, returned-route allowlist and explicit auto
  opt-in; credentials remain provider-scoped and redacted from public settings.
- Existing task DAG, local-first escalation and explicit cloud fallback order
  can dispatch to the gateway. Runtime tasks remain proposals until host checks
  and a local/direct-provider approval review accept them.
- At most two concurrent client requests per identical gateway base URL in one
  Python process. Excess requests return a retryable rate-limit error immediately.
- Exactly one client HTTP attempt per adapter call. No nested client retries.
  Residual may try only operator-configured fallbacks on retryable failures.
- No streaming, native tools, tool-history forwarding, fusion or extra sampling
  options. Unsolicited tool calls are rejected rather than executed.
- Compression/cache disabled using actual upstream request headers. Compression
  acknowledgement is mandatory; cache hits, missing/unapproved identities and
  malformed retry counts fail closed. A unique session ID isolates each work unit
  from the gateway's sticky/handoff/reasoning memory.
- Request/response byte hashes and an adapter-authored gateway report reach the
  router observations and Station usage events. The report hash is NOT a digital
  signature, a proof of execution, or an attestation of the upstream model.

## The accounting boundary matters

The inspected gateway has up to **20 route attempts** per client request. On a
successful response, `X-Fallback-Attempts` counts FAILED hops, not total attempts;
it is omitted for zero failures. We retain `N + 1` as a **gateway-reported** count.
The optional detail header can contain upstream errors and is deliberately not
logged. Gateway-reported successful-hop token counts, including an `estimated`
flag, are retained separately. They cannot establish total tokens or cost.

Station therefore atomically reserves **20 call units** before gateway dispatch,
including failed calls, and never refunds on the strength of response headers.
Direct/local calls still reserve one unit. Transport request bytes count the
client body once, not guessed gateway-to-provider bytes. `metrics.calls` counts
client attempts; reservations, gateway calls and reported upstream attempts are
separate measures. Insufficient reservation capacity refuses before dispatch.

This bound comes from inspected source, not remote attestation. It assumes that
the deployed gateway preserves that bound; nested upstream services may fan out
further. It is NOT a universal cap on all model invocations. Multiple Station
processes also need a shared provider quota/concurrency ledger before scale-out.

Full usage remains `unavailable`, not zero. Existing unknown-token-usage brakes
stop additional automated batch waves. Completed candidates still go through
normal verification; unavailable accounting never becomes a fabricated saving.
In the basic CLI, configured model-call limits count gateway HTTP requests, not
internal attempts; the Station's weighted reservation is not claimed there.

Consequently this is a usable **experimental inference lane**, not yet an
unattended, fully cost-accounted free-tier swarm. Do not disable the unknown-usage
brake to make a demonstration appear complete.

## Set up and test safely

1. Run a separately reviewed, version-pinned FreeLLMAPI deployment. This branch
   does not install/start it, create provider accounts, change its settings, or
   consume real model quotas automatically.
2. Configure the gateway's ENABLED providers and outbound network rules so every
   possible destination is approved for the data. Use only public/synthetic data
   for this first integration test. A localhost URL still sends data to the cloud.
3. Set gateway handoff off and avoid operator-injected system prompts. Request
   headers disable compression and cache, but do not attest to every possible
   server-side rewrite. Residual reports `transformations_verified: false` and
   `catalog_digest: null`; it never invents a catalog pin or a transformation proof.
4. In Model Workshop, choose **FreeLLMAPI (experimental cloud)**, enter the endpoint
   (usually `http://127.0.0.1:3001/v1`), unified API key, exact model ID and allowed
   returned routes such as `groq/your-model-id`. Alternatively use
   `FREELLMAPI_API_KEY` and [the TOML example](../../examples/freellmapi.toml).
   The direct registry additionally reads `FREELLMAPI_BASE_URL` and a comma-separated
   `FREELLMAPI_ALLOWED_ROUTES`. Its auto-routing default stays disabled.
5. Use an explicit model first. `auto` or `auto:profile` requires the separate
   opt-in checkbox. The allowlist validates the reported FINAL route only; it does
   not enforce where the gateway previously sent a request. Even explicit model
   pins can switch providers. Do not infer data residency from a passing response.
6. Keep approval review on the local route or a direct cloud provider. The Station
   refuses a `reviewer` attempt through this adapter, including fallback attempts.
7. Use **Test cloud connection** with synthetic text, then inspect gateway report
   hashes, declared identity, reported usage and incomplete-accounting status.
   Increase project call limits explicitly only when the intended reservations
   fit the authorized experiment. Defaults are not raised by this integration.

The endpoint accepts HTTPS, or HTTP on literal loopback hosts only. Redirects and
ambient HTTP proxies are disabled. Error text does not disclose credentials,
prompts, provider bodies or fallback-detail headers. Socket reads have the
configured timeout and response size is bounded; this is not an OS-level hard
deadline or an attestation that a disconnected upstream has stopped work.

## Tests and merge gates

Offline tests:

```sh
python -m unittest tests.modular.test_freellmapi -v
python -m unittest discover -s tests -v
npm run check:ui
npm run test:ui
```

The mock gateway uses the inspected upstream wire format. Tests cover requests,
provenance refusal, compression/cache acknowledgement, retries, malformed data,
unknown usage, redirects, async calls, concurrency, secret isolation, CLI config,
atomic reservations, cloud sharing, approval exclusion and a real Station
candidate/check/review/integrate cycle using synthetic model replies. Browser
tests cover configuration, reload, opt-in, redaction and 390px layout.

Before merging: require repository CI, a smoke test against the actually deployed
gateway, and explicit acceptance of this experimental/unknown-accounting scope.
No live gateway result or measured cost reduction is implied by mock tests.

## Next stage: measurable distributed work

The Station already consumes explicit dependencies and verifies candidates.
This branch does not add a universal deterministic semantic decomposer, dynamic
claim-correlation engine, distributed quota ledger or calibrated routing learner.
For adaptive decomposition, persist each proposed graph expansion and validate it
deterministically; replay uses the recorded decision, not an assumption that a
fresh LLM call returns the same DAG. Model agreement is not proof of truth.

Before unattended free-tier batches, add an enforceable gateway execution
contract: pre-dispatch provider/credential-class policy, bounded internal attempts
and aggregate token reservations, complete attempt telemetry including failures,
catalog/config identity, cancellation semantics and process-shared reservations.
Missing evidence must continue to stop budget-controlled expansion.

Benchmark fixed workloads against direct-provider baselines: verified completion
rate, total/unknown spend, repair attempts, p50/p95 latency, and cost per accepted
task. More tokens or more worker instances alone is not evidence of a saving.
Local power/hardware and subscription fees also belong in total cost.

## Source review

Wire behavior was inspected at upstream commit
`496ec4ef1bd1da48fa7c83fd1094a34c2b204e7d` (not an automatically deployed revision):

- [Chat routing and response normalization](https://github.com/tashfeenahmed/freellmapi/blob/496ec4ef1bd1da48fa7c83fd1094a34c2b204e7d/server/src/routes/proxy.ts)
- [Fallback loop and header semantics](https://github.com/tashfeenahmed/freellmapi/blob/496ec4ef1bd1da48fa7c83fd1094a34c2b204e7d/server/src/lib/fallback-loop.ts)
- [API and diagnostic headers](https://github.com/tashfeenahmed/freellmapi/blob/496ec4ef1bd1da48fa7c83fd1094a34c2b204e7d/docs/en/api/01-rest-api.md)
- [Compression controls](https://github.com/tashfeenahmed/freellmapi/blob/496ec4ef1bd1da48fa7c83fd1094a34c2b204e7d/docs/en/compression/01-compression-pipeline.md)

No upstream code was vendored and no project license/terms assertion substitutes
for checking each chosen provider's permitted use.

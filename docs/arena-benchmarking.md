# Arena API and Agent Arena benchmarking integration

Date: 2026-09-19

## Boundary

RESIDUAL integrates Arena in two separate roles:

1. **Arena API provider transport** — `ai_providers.adapters.ArenaAdapter` uses Arena's OpenAI-compatible preview endpoint as a model gateway.
2. **Arena-aligned evaluation** — `residual.eval.arena` extracts local measurements corresponding to publicly described Agent Arena signals.

These roles are deliberately separated. The repository does not claim to submit RESIDUAL into the official Agent Arena leaderboard and does not label local results as official Arena scores.

Upstream references used by this integration:

- [Arena API reference](https://portal.api.preview.arena.ai/docs/api-reference)
- [Arena model routing and fallback](https://portal.api.preview.arena.ai/docs/routing)

## Setup from RESIDUAL

The easiest path is **Command Station → Model Workshop → Cloud provider → Arena API**.

When Arena is selected, RESIDUAL shows a guided setup card:

1. **Get Arena API key** opens the Arena dashboard Keys page directly: `https://portal.api.preview.arena.ai/dashboard/keys`.
2. Create a **virtual API key** in Arena and copy it.
3. Return to RESIDUAL, paste it in the API key field, and click **Save model routes**.
4. If no Arena model is selected yet, RESIDUAL automatically fetches the model IDs available to that key.
5. Click **Use this model** on the model you want. RESIDUAL saves it and immediately runs the cloud connection test.

RESIDUAL does not fetch or create the Arena credential on your behalf. The key is entered directly into the Station credential field and is not returned by bootstrap/settings APIs.

Terminal users can open the same destination with:

    residual arena setup

The module form remains equivalent:

    python -m residual.workbench arena setup

For headless systems:

    residual arena setup --print-only

## Arena API contract used by RESIDUAL

RESIDUAL uses Arena's documented OpenAI-compatible API surface:

| Purpose | Upstream Arena route | Method | RESIDUAL behavior |
| --- | --- | --- | --- |
| Discover models | `https://api.preview.arena.ai/v1/models` | `GET` | Bearer-authenticated; returns/sorts model IDs available to the virtual key. No model ID is required for this setup-only call. |
| Chat / structured output | `https://api.preview.arena.ai/v1/chat/completions` | `POST` | Sends the selected model, messages, output limit, optional tools, and `allow_fallbacks:false`. RESIDUAL does not depend on undocumented `response_format`; requested schemas are included in the system instruction and the returned JSON is validated locally. |
| Streaming chat | `https://api.preview.arena.ai/v1/chat/completions` | `POST` + SSE | Sends `stream:true` and the same `allow_fallbacks:false` policy. RESIDUAL does not send undocumented `stream_options`; usage stays unknown unless Arena reports it in the stream. Arena provenance headers are validated before the first chunk is emitted. |

Authentication is always:

    Authorization: Bearer <virtual Arena API key>

The Station never places the key in query parameters, task packets, observations, benchmark traces, or public settings responses.

### Arena response provenance

Arena documents these response headers:

- `X-Arena-Resolved-Model` — actual model selected by the gateway;
- `X-Arena-Trace-ID` — Arena request identifier for debugging/support;
- `X-Arena-Fallback-Index` — present when a fallback served the request;
- `X-Arena-Fallback-Reason` — why the previous model was abandoned.

RESIDUAL keeps only the bounded, non-secret provenance values above. Complete-response calls attach them to normalized `ChatResponse.metadata`; Router receipts and Station `usage.recorded` events carry that sanitized metadata forward. Raw upstream headers and bodies are not persisted.

AX-ARENA live evidence requires the resolved-model and trace-ID headers for completed observations. Arena trace IDs must be unique, every completed RESIDUAL attempt must resolve to one model, and paired control/treatment observations must resolve to the same Arena model. Missing or inconsistent provenance fails the evidence check instead of being silently accepted.

## Command Station serving path

Arena credentials and API traffic remain server-side. The browser's Content Security Policy keeps application network requests on the Station origin; the setup card's explicit external link is only for opening Arena's credential dashboard.

The Model Workshop uses these authenticated RESIDUAL endpoints:

| Station route | Purpose | Handling |
| --- | --- | --- |
| `POST /api/settings` | Save the Arena provider profile and provider-scoped credential | Requires the Station session token. The secret is stored in provider credential state and omitted from public/bootstrap settings. An Arena profile may temporarily have an empty model only so discovery can run. |
| `POST /api/providers/models` | Discover models available to the saved Arena key | Requires the Station session token. Starts an asynchronous `discover-models` job; the server calls Arena `GET /v1/models` with Bearer auth. |
| `POST /api/models/test` | End-to-end connection test after model selection | Requires the Station session token. Starts a `test-cloud` job using the selected Arena model through the normal provider/Router path. |
| `GET /api/jobs` | Poll discovery/test completion | Requires the Station session token. Results contain model IDs or normalized operation results, never the Arena credential. |

Changing the cloud provider clears the model field in the UI so a model ID from another provider cannot silently bypass Arena discovery. Selecting **Use this model** persists the exact Arena model ID and immediately runs the cloud connection test.

## Provider safety and error handling

The Arena adapter submits one model ID per request and writes `allow_fallbacks:false` into every Arena request. It also removes any `fallbacks` or `fallback_on` fields before transport. If Arena nevertheless returns fallback provenance headers, RESIDUAL rejects the response as `invalid_response`; streamed responses are rejected before their first content chunk is emitted.

Non-experimental cross-provider failover belongs in RESIDUAL's existing `Router`, where every transport attempt gets a separate reservation and receipt. AX-ARENA does not configure Router fallbacks.

HTTP/transport handling follows the common bounded provider contract:

| Condition | Normalized RESIDUAL result | Retryable by Router? |
| --- | --- | --- |
| 401 / 403 | `authentication` | No |
| 404 | `model_not_found` | No |
| 429 | `rate_limit` (honors bounded `Retry-After` metadata) | Yes |
| 5xx | `server_error` | Yes |
| connection / socket timeout | `connection` / `timeout` | Yes |
| redirect | `redirect_refused` | No |
| malformed JSON, duplicate keys, invalid Arena provenance | `invalid_response` | No |
| oversized response/stream | `response_too_large` | No |
| incomplete stream | `stream_incomplete` | Yes only before caller-visible replay can occur |

The stdlib HTTP layer disables ambient proxies and redirects, bounds complete responses to 2 MB and streams to 16 MB, and never interpolates upstream error bodies into exceptions.

Environment variables:

- `ARENA_API_KEY`
- `ARENA_BASE_URL` (optional; defaults to `https://api.preview.arena.ai/v1`)

The provider remains a remote/cloud route. It is not accepted as a local provider.

## Workbench commands

Model discovery:

    residual arena models

Freeze:

    residual arena freeze --manifest <manifest.json> \
      --model arena:<model-id> [--model arena:<model-id> ...] --output <lock.json>

Run a frozen live protocol:

    residual arena run --lock <lock.json> --output <run-directory>

Score an externally produced complete trace set:

    residual arena score --lock <lock.json> \
      --traces <traces.jsonl> --output <report.json>

The built-in live executor is intentionally narrow: exact-answer tasks, one raw single-call Arena control, and the same Arena model behind RESIDUAL's real obligation harness. It records transport/provider failures as `UNKNOWN` rather than task failures. Completed observations must carry Arena's actual resolved-model and trace-ID provenance; paired observations that resolve to different models are rejected as incomparable. More complex coding/tool benchmarks should implement a task/evaluator adapter against the same frozen schedule and trace contract.

The lock binds the workload, randomized schedule, model refs, conditions, complete RESIDUAL/provider/observation source hashes, fallback policy, seed, and methodology before outcomes are inspected. Live execution refuses a changed source tree.

## Trace event vocabulary

The signal extractor consumes explicit event labels rather than inferring hidden semantics:

- `task_feedback`: `{"approved": true|false}`
- `feedback`: `{"sentiment": "praise"|"complaint"}`
- `correction`: `{"correction_id": "..."}`
- `correction_outcome`: `{"correction_id": "...", "status": "accepted"|"extended"|"redirected"|"rejected"|"gave_up"}`
- `tool_call`: `{"name": "..."}`
- `bash_result`: `{"ok": true|false}`

Tool hallucination is measured against the trace's frozen `available_tools` set. Bash recovery begins on a failed bash result and counts subsequent bash results through the first success.

## Experimental interpretation

AX-ARENA-01 is a paired harness-treatment experiment. The same task/model/repetition cell has one control observation and one RESIDUAL observation. The current report computes a descriptive success-rate delta and a task-cluster bootstrap interval.

That interval is not an automatic superiority verdict. Corpus selection, evaluator validity, provider stochasticity, environmental drift, multiple testing, and repeated inspection all remain relevant.

## Next experimental extensions

- AX-ARENA-02: component ablation across orchestration, contracts, observation, verification, deterministic integration, recovery, and memory.
- AX-ARENA-03: swarm scaling at 1/2/4/8/16/32 workers with coordination-cost accounting.
- Fault-injection variants: transport death, malformed tool output, unavailable verifier, conflicting worker results, budget exhaustion, and checkpoint recovery.

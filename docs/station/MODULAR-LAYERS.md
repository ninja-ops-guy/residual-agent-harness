# Modular providers and observations — Command Station 0.3

The supplied `ai_providers` and `observation_layer` packages are integrated into the station, the distributed runner, and the original TOML-configured harness. Both packages ship in the Python wheel, native source bundle, and Docker image. Runtime dependencies remain Python's standard library.

## Configure in the web interface

1. Open **Model Workshop**. Choose Ollama or an OpenAI-compatible loopback server for local execution. Optional local credentials are stored separately from cloud credentials.
2. Choose a cloud provider, enter a model/deployment ID, and supply its API key. Defaults fill known provider endpoints. Azure needs your resource endpoint and API version; Bedrock needs a region, access key, secret key, and optional session token. Environment credentials are also supported.
3. Expand **Cloud failover order** to add up to three distinct fallback providers. Local fallback model IDs stay on the same local endpoint. Save routes before testing them.
4. Run a connection test or send a playground message. A failed operation shows a safe provider error code; the observation console records the attempt and outcome.
5. Open **Diagnostics → Observation console**. Select Model Workshop or the current mission, inspect the chain, filter signals, open an individual record, or download JSONL. Pause/resume controls optional observation recording; mandatory LDD state and usage accounting continue.

An authentication, missing-model, malformed-output or unsupported-operation error stops the route. Connection/timeout, rate-limit and server errors can advance to the next explicit fallback. Each attempted request reserves a call and its exact serialized request-body size before transport. Failed calls remain reserved; missing token counters stay unknown. Project cloud permission applies to every cloud attempt. A local request never automatically enters a cloud fallback chain. The existing coordinator can separately escalate unresolved tasks when the mission allows it.

The station supports one credential set per cloud provider. Use a separate station for different accounts/endpoints of the same cloud provider. Secrets are not returned by bootstrap/settings APIs, included in task packets, or exported with observations. Keys are stored in the station's protected data directory, not an OS keychain. Changing provider controls clears unsaved password fields. Existing legacy cloud keys migrate into provider-specific storage when settings are saved.

## Capability matrix

| Adapter | Sync chat | Stream | Async chat | Async stream | Model discovery |
|---|---|---|---|---|---|
| OpenAI Chat Completions | Yes | Yes | Yes | Yes | API |
| OpenAI-compatible | Yes | Yes* | Yes | Yes* | API* |
| Arena API (preview) | Yes | Yes* | Yes | Yes* | Bearer-authenticated `GET /v1/models` |
| Anthropic Messages | Yes | Yes | Yes | Yes | Paginated API |
| Google Gemini | Yes | Yes | Yes | Yes | Paginated API |
| Azure OpenAI | Yes | Yes | Yes | Yes | Enter deployment ID |
| AWS Bedrock Converse | Yes | Explicit `not_implemented` | Yes | Explicit `not_implemented` | Enter model/profile ID |
| Ollama native | Yes | Yes | Yes | Yes | Installed models API |

*Compatible servers and the Arena preview gateway must support the request fields they receive, including JSON mode and streaming usage options. Arena uses Bearer auth, `GET /v1/models` for discovery, and `POST /v1/chat/completions` for inference. RESIDUAL sends `allow_fallbacks:false` on Arena chat requests and rejects Arena fallback provenance if it appears anyway. Complete-response Arena calls retain only the documented resolved-model/trace/fallback provenance headers in normalized metadata; streaming validates the same no-fallback invariant before yielding content. Arena model capability is intentionally treated as opaque: `supports_tools()` is conservative. Compatibility is protocol support, not a promise about every hosted service or model. Tool specifications and tool-result messages translate to native provider formats. The station itself requests bounded text/JSON file proposals; it does not execute model-requested tools. Ollama capabilities are queried rather than guessed from a model name.

Async methods run the shared stdlib transport in worker threads. Async streaming preserves the same chunks, errors and usage as sync streaming. Cancellation of an outstanding read waits for that bounded read to complete before closing the generator. Bedrock streaming remains unavailable; it is never represented as a successful empty stream. Model Workshop uses complete-response background jobs, not token-by-token rendering.

## Public Python API

```python
from ai_providers import ChatRequest, Message, Role, Router
from observation_layer import ObservationBus
from observation_layer.sinks import InMemorySink

sink = InMemorySink()
bus = ObservationBus(sink=sink, trace_id="research-001")
router = Router(default_provider="ollama", observation_bus=bus)
request = ChatRequest(
    model="",  # Router replaces this with the selected model ID.
    messages=(Message(Role.USER, "Explain this small specification."),),
    max_tokens=512,
)
response = router.chat("ollama:qwen2.5-coder:7b", request)
print(response.content, response.usage)
```

Cloud environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `AZURE_OPENAI_API_KEY`, `ARENA_API_KEY`, and AWS's access/secret/session variables. The standalone registry also reads `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AWS_DEFAULT_REGION`, `ARENA_BASE_URL`, `OLLAMA_HOST`, `LLM_BASE_URL`, and `LLM_API_KEY`. Use `RESIDUAL_LOCAL_API_KEY` for a station local server key. `RESIDUAL_CLOUD_API_KEY` remains a fallback for the station's selected primary cloud provider. The bundled worker accepts `RESIDUAL_RUNNER_API_KEY`.

Use a new `Registry` and `register(provider_name, factory)` for explicitly constructed adapters with custom endpoints. Built-in provider names are a closed vocabulary. Factories load lazily; re-registering replaces the cached instance. Optional `before_attempt` and `after_attempt` Router callbacks are authoritative policy/accounting hooks. Their exceptions propagate. Observation callbacks are best-effort and cannot veto the model result.

`response.as_message()` constructs the assistant turn for a tool conversation. Gemini's opaque thought-signature parts are retained in response metadata for replay; metadata/raw responses are never emitted to the observation bus. Text-only streaming does not reconstruct those signed Gemini parts for a subsequent tool turn; use non-streaming chat for a Gemini tool conversation requiring them.

The original CLI accepts the new provider kinds in `[local]` and `[expert]` sections. See `examples/modular-cloud.toml`. Existing demo commands and original benchmark modes remain available. The low-level legacy `HTTPProvider` class remains for compatibility; configured built-in routes use `ModularProvider`.

## Observation integrity and authority

- Schema **1.1.0** adds a stored digest, deep immutable JSON payloads, and a distinct `llm.failed` kind. Retained records are sealed after filtering/redaction, so sampled or redacted traces maintain valid linkage.
- Verification checks stored digests, predecessor linkage, trace identity and duplicate IDs. A trusted expected head/count detects a truncated tail. A hash chain is tamper evidence, not a signature or protection against an attacker rewriting both the trace and checkpoint.
- The station stores observations and per-trace checkpoints in new SQLite tables. Transactions serialize concurrent writers across threads/processes and resume from the persisted head after restart. Workflow metadata is mirrored in the LDD transaction under a savepoint. A diagnostics failure does not authorize, reject or overwrite an LDD transition.
- Provider attempts share a request ID and have distinct attempt numbers. Metadata includes provider/model, role, task, byte count, elapsed time, finish state and normalized usage. No prompts, source bodies, generated content, tool arguments, or raw upstream errors are included by station instrumentation.
- The LDD event ledger remains authoritative. Observations cannot approve changes. Observation volume does not affect deterministic cloud-report content; no trace is broadcast to models automatically.
- JSONL replay refuses malformed, duplicate-key and unsealed records. Uploaded schema 1.0 traces are not silently resealed as trusted history. Keep them as original artifacts and migrate explicitly if needed; the station's existing LDD records need no conversion.
- Filtering and optional sinks belong to the standalone module. Sampling/drop counters and delivery failures are visible. Sink failures can produce detectable gaps. Queue sinks drop the newest item when full and reject writes after close. A per-trace bus does not invent a new trace ID when a context requests a different one.
- Hooks now avoid raw argument/result/exception-message capture and await decorated async tools correctly. Optional observation errors cannot mask a successful return or the original tool failure.

## Accounting corrections

Missing usage fields remain absent in the provider response and `null` in station receipts. Real zero is retained as zero. Anthropic and Bedrock cache-read/write inputs are included in total input; Gemini output includes reported thinking tokens. Cache writes remain separately identified. Existing simple CLI price tables cannot price cache-write tiers, so those costs remain unknown instead of undercounted.

The mappings follow the providers' references: [Anthropic cache accounting](https://platform.claude.com/docs/en/build-with-claude/prompt-caching), [Bedrock cache accounting](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html), [Gemini usage fields](https://ai.google.dev/api/generate-content), and [Ollama chat fields](https://docs.ollama.com/api/chat).

HTTP adapters bound response/frame sizes, reject duplicate JSON keys and non-finite data, disable ambient proxies, refuse redirects, and sanitize transport errors. API keys use headers, including Gemini. Bedrock signs normalized lowercase headers, session credentials, and escaped model/profile paths; an independent AWS botocore comparison produced the committed signature test vector. See [AWS SigV4](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_sigv-create-signed-request.html) and [Converse](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html). Discovery uses [Anthropic's model API](https://platform.claude.com/docs/en/api/models/list) instead of a static model list. OpenAI translation targets [Chat Completions](https://developers.openai.com/api/reference/resources/chat), not every OpenAI API.

Managed Ollama starts with `OLLAMA_NO_CLOUD=1`, and local routes reject cloud model tags. An operator-managed local proxy can still forward traffic; a loopback URL alone cannot prove zero egress. Model pulls and runtime installation need network access. [Ollama documents its cloud-disable setting](https://docs.ollama.com/faq).

## Evidence and limits

See [VALIDATION.md](VALIDATION.md) for executed tests and untested environments. Tests use real local HTTP transport with protocol fixtures, not live cloud inference. Token reduction and model quality remain benchmark questions; no savings percentage is asserted.

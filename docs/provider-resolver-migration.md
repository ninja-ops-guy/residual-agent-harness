# Provider Resolver Migration Map (MS-01)

> Audit deliverable, tests/docs only. No provider runtime changes are proposed here.
> Verified against `main@3cff6bcd52e352a6ba048c958949a7bbb2a039eb`.
> Executable vectors: `tests/modular/test_resolver_adversarial.py`.

## 1. Current routing surface (as-found)

| Concern | Current location | Current behavior |
|---|---|---|
| URL policy (scheme, loopback set, embedded credentials, query/fragment, control chars, port range) | `ai_providers/adapters/_http.py` `validate_url` | Exact hostname set `{localhost, 127.0.0.1, ::1}`; rejects dword/hex/short-form loopback, credential-bearing, query/fragment, and control-char URLs; plain `http` allowed only on loopback. |
| Provider vocabulary | `ai_providers/core.py` `ProviderName` | Closed enum: openai, openai_compatible, anthropic, google, azure, bedrock, ollama, **router**. |
| Model reference parsing (`provider:model`) | `ai_providers/router.py` `ModelRef.parse` | Splits on first `:`; unknown provider or empty model → `unknown_provider`; bare model → provider `default`. |
| Candidate construction | `ai_providers/router.py` `Router._candidates` | ≤5 candidates, all distinct, else `invalid_request`. |
| Dispatch | `ai_providers/registry.py` `Registry.get` / `_default_registry` | Lazy factories for the 7 dispatchable kinds; **no factory for `router`**. Unknown name → `unknown_provider`; factory name mismatch → `config`. |
| Stream failover boundary | `ai_providers/router.py` `Router.stream` | Retryable error with any emitted chunk → raise original error; never concatenates another model's stream onto an emitted prefix. `GeneratorExit` → `stream_incomplete` receipt. |
| Profile normalization | `residual/modular.py` `normalize_profile` | Kind allowlist, model charset/length, local ⇒ loopback-only kinds, Ollama `-cloud` models barred from local routes, bedrock region regex, `output_token_field` allowlist. **No kind↔host pinning for first-party kinds.** |
| Credential handles | `residual/station/models.py` `save_settings`, `credentials_for` | Per-kind credential dicts; legacy `cloud_key` rebound to its original kind before route change; `clear` empties the saved handle; bedrock permits access/secret/session keys only. |
| Credential env fallback | `residual/modular.py` `make_adapter` (line ~44) | `c.get('api_key') or os.environ.get(ENV_KEYS[kind])` — a cleared saved handle **resurrects** via the environment. |
| Identity hashing | `residual/quarantine.py` `ProposedAction.fingerprint`, `residual/core.py` `canonical`/`digest` | Sorted-key canonical JSON, `allow_nan=False`; fingerprint covers action_type/name/arguments/agent_id only (hold_id and timestamps excluded). |

## 2. Canonical resolver contract (target)

1. **Single resolution entry point.** Every provider reference — profile kind, `provider:model` string, fallback candidate — resolves through one resolver that returns a fully-bound, dispatchable target or a structured refusal.
2. **Parse = dispatchable.** A name admitted at parse time MUST be dispatchable; undispatchable vocabulary members are refused at parse, not deferred to dispatch.
3. **Kind↔host pinning.** First-party kinds (openai, anthropic, google, azure, bedrock) bind to their canonical hosts; `base_url` override is honored only for `openai_compatible` (loopback/local) and explicitly self-hosted kinds.
4. **Credential handles are total.** A handle is either bound (saved), environment-derived (explicitly reported as such), or absent. `clear` means absent from every source; env inheritance must be an explicit, visible setting, not a silent fallback.
5. **Loopback policy is exact.** Local routes accept only the literal loopback set; encoded, partial, credentialed, or decorated variants are refused (current `validate_url` already conforms — verified by PR-01 vectors).
6. **Bounded, distinct failover; no cross-model stream concatenation** (current router conforms — verified by PR-05 vectors).
7. **Stable identity.** Identical inputs hash identically; volatile fields (timestamps, request ids, hold ids) never enter identity hashes (current `canonical`/`fingerprint` conform — verified by PR-04 vectors).
8. **No implicit aliasing.** Model/provider names match exactly; any future alias table is part of the resolver contract and versioned.

## 3. Migration map: current → canonical

| # | Current seam | Gap | Migration step |
|---|---|---|---|
| M-1 | `ProviderName` admits `router`; `ModelRef.parse("router:m")` succeeds | Parse admits an undispatchable name (finding F-2) | Split vocabulary into *dispatchable providers* vs *internal roles*; resolver refuses non-dispatchable names at parse with `unknown_provider`. |
| M-2 | `normalize_profile` accepts any HTTPS `base_url` for first-party kinds (azure/openai/etc.) | No kind↔host pinning (finding F-1) | Add canonical host table per first-party kind; resolver rejects foreign endpoints for pinned kinds. |
| M-3 | `make_adapter` env fallback after `clear` | Cleared credentials resurrect from env (finding F-3) | Resolver takes an explicit credential-resolution result (`saved`/`env`/`none`); `clear` records an explicit `none` that suppresses env inheritance for that kind. |
| M-4 | Two resolution paths: `residual/station/models.py` `model_call` (profile-driven) and `Router` (`provider:model`-driven) | Divergent entry points; invariants enforced twice | Introduce one `resolve(ref_or_profile, settings) -> ResolvedTarget`; both paths delegate. |
| M-5 | No alias table exists | Contract must freeze "exact match only" (finding F-4) | Freeze exact-match semantics in the resolver spec; any aliasing added later must be a versioned, reviewable table consumed by the resolver. |

## 4. Findings (re-confirmed or refuted on current main)

Prior-art predictions from wave-a A2, re-run as executable tests on
`main@3cff6bcd`:

| ID | Vector | Verdict on current main | Evidence |
|---|---|---|---|
| F-1 | PR-02h: `normalize_profile` does not pin provider kind↔host (azure kind + `https://api.openai.com/v1` accepted) | **CONFIRMED** | `test_f1_kind_host_not_pinned_current_behavior` passes; `test_f1_canonical_contract_kind_host_pinned` is `expectedFailure` (xfail). |
| F-2 | PR-05f: `ProviderName.ROUTER` parses but is undispatchable (fails closed at dispatch with `unknown_provider`) | **CONFIRMED** (safe today; spec-level gap) | `test_router_name_parses_but_is_undispatchable` passes; `test_canonical_contract_router_name_rejected_at_parse` xfail; `test_router_name_in_vocabulary_but_unregistered` passes. |
| F-3 | PR-03c: cleared credentials resurrect via env fallback (`modular.py:44`) | **CONFIRMED** | `test_current_behavior_cleared_key_resurrects_via_env` passes (adapter picks up `OPENAI_API_KEY` after `clear`); `test_canonical_contract_clear_blocks_env_fallback` xfail. |
| F-4 | No model-name alias table exists; expected behavior is exact string match | **CONFIRMED** (by inspection; no alias code path in `router.py`/`modular.py`/`registry.py`) | Parse vectors PR-05c–PR-05g pass with exact-match semantics. |

All other prior-art vectors (PR-01 hostname spoofing incl. dword/hex/short-form/embedded-credential/control-char bypasses, PR-02a–g/02i–k, PR-03a–b/03d–h, PR-04 hash stability, PR-05 stream boundaries, PR-06 registry guards) **hold as specified** on current main — they pass as written.

## 5. Out of scope / not exercised here

- PR-07 WebVM provider-session relay vectors (`demo/vm/provider-session.js`) are JavaScript-side and belong to the WebVM ownership surface; they are not re-implemented in this Python suite.
- No live/real-provider calls are made or claimed; all dispatch tests use in-process fakes.

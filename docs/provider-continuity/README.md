# Provider continuity candidate

Status target: `PROVIDER_CONTINUITY_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW`.
This is a new implementation generation, not a production-readiness claim or the
historical BL-009 F-1 repair.

## Source lineage

Accepted Git base: `8369f0dc` (full commit/tree in `evidence/lineage.json`).
The local September 28 BL-009 transport contains 21 files, each decoded and
SHA-256 verified. That bundle supplies design lineage and the byte-preserved
BL-006 Candidate B implementation under `residual/continuity/vendor/bl006.py`.
Its SHA-256 is
`33f92efe8f2fac50f3038ba2d566abaaf97bebed163d0d14345461d47e3b2f8c`.
The later 22-file F-1 repair manifest `2fa430b6…034e` is
**CITE_ONLY / NOT_AVAILABLE_TO_CODEX**. Its bytes were not reconstructed or
claimed. No BL-009 Git PR/branch newer than main was found in the remote inventory.
The historical FreeLLMAPI evaluation PR #352 and integration/onboarding work
are context, not readiness or admission authority. The preserved September 27
FreeLLMAPI runtime backup expressly does not qualify a live provider.

The older BL-004 receipt contract requires original provider/model, failure
class, policy, fallback provider/model and admission outcome. Decision history
retains these bindings through the initial plan, each attempt, result digest,
and acceptance, plus mission/task, route, readiness, admission and timestamps.
The broader historical trigger taxonomy is not today's policy.

## Policy

| Normalized class | Automatic fallback |
| --- | --- |
| `quota_exhausted` | Only with current READY, new BL-006 PASS, current authority and budget |
| `credit_exhausted` | Same |
| `provider_unavailable` | Same |
| All other classes | No |

The HTTP adapter recognizes quota/credit only from allowlisted structured
error codes on HTTP 402/429. A bare 429 is `rate_limit`, not quota exhaustion.
Transport `connection`, `timeout`, and HTTP `server_error` normalize to
`provider_unavailable`; the original code remains in the decision evidence.
Authentication/permission errors (401/403), missing models (404), invalid or
malformed responses, content filters, output truncation, structured-output or
validation failures, policy denial, budget exhaustion, admission denial,
expired/rescinded authority, verification failures, and cancellation do not
trigger automatic fallback. Historical `AUTH_EXPIRY` and
`RATE_LIMIT_EXHAUSTED` are not eligible.

`OFF` disables fallback. `ASK` stops with `fallback_confirmation_required`;
it does not silently approve a request or provide an unattended approval path.
An operator may explicitly change policy for a new dispatch. No automatic
retry occurs within a route. Legacy primary-only configurations remain usable;
legacy cloud fallback lists no longer bypass explicit readiness and admission.
The existing explicitly configured local model failover contract is unchanged.

## Crash boundaries and authority

1. `PLANNED`: no provider effect has started. Resume can pass normal gates and
   durably enter `INVOCATION_STARTED` before I/O.
2. `INVOCATION_STARTED` without a recorded result: report
   `INDETERMINATE_PROVIDER_OUTCOME`. Never automatically retry. This includes
   process death after the upstream accepted or completed a request.
3. `PROVIDER_RESULT_RECORDED`: resume exclusively from persisted normalized
   response evidence and its digest. Proceed through `ACCEPTANCE_PENDING` to
   `ACCEPTED` or `REJECTED`. Duplicate/concurrent resume cannot re-invoke the
   provider or duplicate the journal's acceptance transition.

There is **no provider-side exactly-once claim** across external acceptance and
local result persistence. This candidate has no provider idempotency contract
that could authorize replay of an indeterminate call. A new operator dispatch
is a new invocation, not a replay claim.

`ACCEPTED` in this journal means validated evidence is available to Station.
It does not integrate code, approve a review, or grant mission authority.
Station's existing checks, head-bound verification, review and integration remain
mandatory. A caller can resume `model_call(..., invocation_id=...)` with the
same bound request and current authority. Task calls derive a stable identity
from project/task/attempt/role/request. Station startup still blocks interrupted
leases for re-triage; the journal does not renew leases or restore rescinded
authority. Acceptance can remain pending until legitimate authority is available.

SOURCE_REALIZED != SOURCE_INDEPENDENTLY_VERIFIED

CONFIGURED != READY

PROVIDER_RESULT_RECORDED != RESULT_ACCEPTED

provider invocation != authoritative transition

## Readiness, admission, breaker and secrets

Named `route_id` is independent of implementation `kind` / `provider_kind`.
Both primary-cloud and freellmapi can use `openai_compatible`. Credentials use an
explicit `credential_ref` (defaults to route ID); legacy provider-kind references
remain supported. Named routes do not inherit another route's environment key.
Receipts exclude prompts, response content, raw upstream errors and credentials.
The private SQLite result record contains normalized response content; it is not
an operator decision receipt. Protect the Station root as usual.

FreeLLMAPI always has `placement=remote`, including `http://127.0.0.1` proxies.
It uses the ordinary adapter, quarantine, sharing policy and call reservations.
Reachability, HTTP 200, and primary breaker OPEN cannot create READY or PASS.
Readiness qualification requires an explicitly bounded structured-response probe
and BL-006 PASS. A separate, fresh BL-006 evaluation and consume occurs before
each invocation. The wrapper passes the resolved manifest digest unconditionally,
refuses WARN/REJECT, stale/future telemetry, mismatched model and out-of-context
requests. It never fabricates telemetry or auto-confirms WARN.

For this bounded candidate READY expires no later than the original telemetry's
60-second freshness boundary. Operators must explicitly requalify with current,
measured inputs. This is deliberately a short operational window; no scheduler,
background refresh or retry loop is added. Remote upstream resource measurements
must come from legitimate evidence, not be inferred from the loopback relay.
Fixture measurements are synthetic and labeled; never use them to admit a live
endpoint. A failed requalification revokes READY. Credential edits invalidate
current readiness. Historical readiness receipts remain stored.

CLOSED opens on eligible provider failure. OPEN makes an already-READY fallback
eligible, subject to all gates. Explicit `half-open` requires current READY and
permits a single probe owner; a stranded probe is never replayed automatically.
Successful recorded provider evidence closes the breaker. Breaker transitions
and their causal invocation/readiness identities are persisted.

Run-level budget/deadline authority is rechecked between attempts. Missing usage
remains unknown and blocks further controlled effects. The qualification's fake
quota response explicitly reports zero usage; real providers that omit usage
may therefore require operator resolution even when the failure class is eligible.

## Operator commands

Use the same Station root as the running deployment. Configuration example:

```json
{
  "cloud": {
    "route_id": "primary-cloud",
    "provider_kind": "openai_compatible",
    "model": "YOUR_PRIMARY_MODEL",
    "base_url": "https://YOUR_PRIMARY_HOST/v1"
  },
  "cloud_fallbacks": [{
    "route_id": "freellmapi",
    "provider_kind": "openai_compatible",
    "model": "YOUR_FREELLMAPI_MODEL",
    "base_url": "http://127.0.0.1:3000/v1"
  }],
  "fallback_mode": "AUTOMATIC_ELIGIBLE"
}
```

```sh
python -m residual.continuity --root STATION configure settings.json
python -m residual.continuity --root STATION qualify --route primary-cloud --admission-context primary-admission.json
python -m residual.continuity --root STATION qualify --route freellmapi --admission-context fallback-admission.json
python -m residual.continuity --root STATION inspect
python -m residual.continuity --root STATION half-open --route primary-cloud
```

Admission-context JSON contains `manifest` (exact BL-006 `ManifestRow` fields),
`telemetry` (exact `TelemetrySnapshot` fields including actual `collected_at`),
`host_identity`, `requested_context_tokens`, and `requested_max_tokens`.
See the byte-preserved BL-006 dataclasses for the schema. Model identity must
match the route. A conservative UTF-8 text bound must fit admitted context.
Supply credentials via Station's existing credential settings, scoped under
`primary-cloud` and `freellmapi`; do not put secrets in published configuration.
`inspect` reports routes, policy, readiness, breakers and last decision.

## Qualification

```sh
python -m scripts.qualification_provider_mission --continuity-fixture --root FIXTURE_STATION --output fixture.json
python -m scripts.qualification_provider_mission --continuity-live --base-url EXPLICIT_ENDPOINT --model EXPLICIT_MODEL --admission-context measured-admission.json --root LIVE_STATION --output live.json
```

Live mode uses a fake rejected primary and the explicitly configured live
FreeLLMAPI fallback. It sends readiness, implementation and review requests;
it is not run in CI. The fixture uses only loopback HTTP and no paid providers.
It reuses the existing qualification mission and run control through verification
and integration, then emits a machine-readable receipt. Fixture PASS is not live
provider qualification. Remaining live gates include operator-supplied endpoint,
model, route-scoped credential, current measured BL-006 context, successful
readiness protocol, and one controlled live mission with admissible usage.

## Failure preservation and checks

`evidence/first-focused.log.gz` preserves the first run: 7 passed, 31 setup
errors caused by a shadowed `re` import. Candidate `207ac800` and its tree are
recorded in the lineage file. The import was repaired without rewriting history.
`affected-first.log.gz` preserves socket-denied fixture failures and old test
stand-ins missing the new authority argument. `affected-r2.log.gz` preserves
1 failure / 128 passes: default OFF inadvertently required readiness for a legacy
primary-only call. The activation predicate was narrowed while retaining the
mandatory gates for named continuity routes. `fixture-r1.log.gz` preserves the
sandbox's socket denial; an authorized loopback rerun passed.

Repository checks use compileall and unittest/pytest; no Python linter or type
checker is configured. Whitespace in byte-preserved BL-006 is intentional and
excluded from the authored-code diff check. No release, tag, merge, scheduler,
Shared Comms, OpenClaw or unrelated UI change belongs to this candidate.

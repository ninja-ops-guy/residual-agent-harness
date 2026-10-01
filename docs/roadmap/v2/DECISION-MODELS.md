# V2-DM-001 — Decision Model Evidence Adapter

**Disposition:** V2_REVIEW_PENDING / EXPERIMENTAL / disabled by default.
**Tracker:** [#503](https://github.com/ninja-ops-guy/residual-agent-harness/issues/503).
**Owner request:** build Clef integration and retain it for later v2 review.
**v1 impact:** none intended; this is not a v1 release gate or an accepted capability claim.

## Implemented review candidate

`residual/decision_models.py` defines a provider-neutral `DecisionModelAdapter`
protocol and immutable `DecisionRequest` / `DecisionEvidence` snapshots. The
`ClefAdapter` is the first implementation, using the documented Cloudflare
Workers AI endpoint and exact `clef` / `clef-flash` selectors. It is not a
chat-completions adapter and is not registered with the live scheduler.

The bounded initial profile supports string/object/array state and 1–64 typed
questions. `noul` carries the probability of true; `choice` carries named-option
probabilities; `score` carries probabilities over an ordered, zero-indexed rubric.
Request limits are deliberately narrower than the provider's full capabilities:
32 KiB serialized request, 64 options per choice/rubric, string descriptions only,
and no images, video, arbitrary endpoints, or automatic truncation.

Strict parsing rejects duplicate keys, non-finite numbers, Boolean probabilities,
unknown answer fields, missing/extra answers, mismatched types/models/labels,
non-normalized distributions, invalid selected options, inconsistent expected
scores and legends, and malformed usage. Probability sums and expected scores
have an absolute tolerance of 1e-5; probabilities are never silently renormalized.
Provider confidence is retained separately; it is NOT assumed equal to the
maximum class probability or treated as independent proof of correctness.

## Authority and artifact boundary

```text
Caller-approved state + question schema + evidence references
    -> Clef or explicit offline replay
    -> strict structural/semantic validation
    -> immutable UNVERIFIED_CANDIDATE decision claim
    -> candidate artifact export
    -> independent validation and existing Station authority (not wired here)
```

`candidate_artifact()` returns a relative content-addressed path and immutable
JSON bytes. It does not write a file, sign a receipt, access the Evidence Bus,
change policy, route a worker, merge a PR, or execute an action. No protected
Factory/M3/M4, Station, verifier, release, scheduler, or workflow bytes change.

The current `residual/factory/evidence_bus.py` admits passing `WorkerReceipt`s
with bound artifacts. A probabilistic classification is NOT such a receipt.
Any future bus admission must use the existing independent verification and
Station-issued receipt flow; inventing a passing receipt is forbidden.

The output contains `authority: false`, `status: UNVERIFIED_CANDIDATE`, full
probabilities, source kind, capture time, subject/evidence references, requested
and reported model, adapter revision, and SHA-256 bindings of the exact outbound
request bytes, raw inbound response bytes, state and question schema. Provenance
references remain local and are not sent to Cloudflare by this adapter.

A hash binds bytes, not their authenticity, correctness, or custody. Evidence
reference strings are caller-supplied and are not dereferenced or verified here.
There is no signature, freshness lease, tenant authorization, or completeness
attestation in this initial claim. Source data must already be sanitized and
approved for egress; this module does not redact arbitrary state.

Hosted aliases do not establish exact weights: `model_revision` remains null and
`model_identity_status` is `UNPINNED_ALIAS`. Calibration is `UNQUALIFIED`;
input completeness is `NOT_ATTESTED`. Missing/empty usage is `UNKNOWN`, never a
fabricated zero-cost inference. Reported usage is metadata, not verified billing.

`review_hint()` returns only `REVIEW_REQUIRED` or `ADVISORY_ONLY`, based on maximum
probability and margin. Ties require review. It is NOT an OOD detector, calibration
certificate, action gate, PASS verdict, or authorization; even `ADVISORY_ONLY`
requires the same existing checks and authority as any other model claim.

## Network boundary

Construction and imports make no requests. `enabled=True` is required for
`evaluate()`. The endpoint is fixed to HTTPS `api.cloudflare.com`; a 32-hex-character
account ID and two-model allowlist prevent URL/path injection. Ambient proxy
configuration is ignored, redirects are rejected, response reads are capped at
256 KiB, errors are sanitized, and there are no automatic retries or fallback.
The token is excluded from repr/output; no state/response/error body is logged.

The timeout is a socket-operation timeout (15 seconds by default, maximum 60),
not a demonstrated whole-request deadline. DNS, slow streaming, cancellation,
budget admission and fleet isolation need additional qualification before
runtime integration. The fixed-host policy is not a replacement for system
network isolation or TLS/DNS trust. Custom transports are trusted embedding
code, distinctly labelled `INJECTED_TRANSPORT`, not proof of Cloudflare traffic.

## Run the offline example and tests

From a checkout containing this candidate:

```sh
python -m examples.clef_decision_demo
python -m examples.clef_decision_demo --model clef
python -m unittest discover -s tests/decision_models -v
```

The example uses invented synthetic probabilities and emits `OFFLINE_REPLAY`.
It runs no model. Replay is deterministic for the same request, exact response
bytes, model selector and supplied capture time; default capture time 0 denotes
an undated fixture. Different JSON whitespace changes the raw response hash.
Replaying a prior live response does not become a fresh live observation.

Only after explicit owner approval for a billable, external-egress canary, set
`CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_AUTH_TOKEN` in the execution environment
and run:

```sh
python -m examples.clef_decision_demo --live --ack-external-egress --model clef-flash
```

This sends only the example's synthetic state. No live call was made while
building this candidate. A successful HTTP request would still produce an
unverified, uncalibrated candidate, not release qualification. Never put real
credentials or employer/customer data in fixtures, issues, PRs or test logs.

## Review and promotion sequence

| Gate | Current disposition |
| --- | --- |
| New-module offline contract/negative tests | Initial result retained in `CLEF-OFFLINE-RESULT.json` |
| Independent code/security review | PENDING |
| Whole-repository regression and Python/OS matrix | NOT RUN |
| Hosted Clef and Clef-flash live canaries | NOT RUN |
| Model revision and API compatibility qualification | PENDING; hosted aliases unpinned |
| Input completeness/token budget/truncation policy | PENDING |
| Frozen workload calibration/Brier, OOD, adversarial tests | NOT RUN |
| Latency/cost/verification-tax benchmark | NOT RUN |
| Deadline/cancellation/egress/tenant policy | PENDING |
| Evidence Bus admission and action/scheduler wiring | NOT IMPLEMENTED; separate review required |

The local runtime could not resolve GitHub for a full clone. Initial tests used
only the new module, tests, and example in an isolated source checkout (namespace
`residual`, not the repository's original `residual/__init__.py` import graph).
This proves the tested module behavior only, NOT full repository integration.
GitHub connector reads established the base and inspected the package metadata,
roadmap and Evidence Bus interface. Require normal installed-package CI before
promotion. Do not infer any v1 invariant violation or release hold from this lane.

## Later v2 scope, not implemented here

Local-weight execution needs a pinned model/runtime and hardware qualification.
Jev/System One API compatibility motivates the neutral protocol but does not
establish a working Jev transport. Images/video, decision-model federation,
calibration tooling, verified historical-label corpora, learning/RL loops and
scheduler/action routing remain separate follow-on proposals. In particular,
multiple models agreeing on a label does not itself establish truth.

This lane complements the planned Enterprise and Security Evidence Fabric and
provider-qualification programs. It must not expand v1 scope by default.

## Primary references inspected 2026-10-01

- [Cloudflare Clef API documentation](https://developers.cloudflare.com/workers-ai/models/clef/)
- [Cloudflare release/API examples](https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/)
- [Cloudflare model card](https://huggingface.co/Cloudflare/clef)
- [Cloudflare announcement](https://blog.cloudflare.com/clef-decision-models/)

The model documentation warns that long state may be truncated. A byte cap is a
resource limit, not proof of tokenizer behavior or full-context observation.
Any API shape change must fail closed and be reconciled against these sources
and captured live evidence, not accommodated by inventing missing probabilities.

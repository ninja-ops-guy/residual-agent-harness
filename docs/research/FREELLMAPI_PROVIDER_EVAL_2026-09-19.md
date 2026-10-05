# FreeLLMAPI provider evaluation — 2026-09-19

Status: **EVIDENCE / provider-candidate experiment**  
Lane: research/provider; independent of P1  
Executor: Ghost / LEGION  
Integration performed: **No** — no RESIDUAL worker, station, drill, or tunnel was pointed at the evaluated service.

## Result

FreeLLMAPI was evaluated on LEGION as an optional RESIDUAL inference gateway. The observed Docker setup reached the first anonymous completion in about eight minutes wall-clock; the evaluator attributed about 22 seconds to actual setup work. Two real `model: auto` completions returned HTTP 200 after a keyless-provider sentinel row was configured.

This result supports **candidate integration testing**. It does not establish production qualification, privacy suitability for arbitrary workloads, or trust in gateway outputs.

## Observed compatibility

The run directly observed:

- `GET /v1/models` returning an OpenAI-compatible list; 237 models were visible during the run.
- `POST /v1/chat/completions` returning an OpenAI chat-completion shape with choices, finish reason, and usage.
- routing transparency through `X-Routed-Via`.
- fallback-detail capability through `X-Fallback-Trail`.
- rate-limit headers.
- unauthenticated `/livez` and `/readyz` probes.
- loopback-only publication at `127.0.0.1:3001` in the tested configuration.

Observed anonymous routing included Kilo. The evaluator notes that Kilo's free traffic may be logged for training; do not infer privacy suitability from the successful smoke test.

## Setup observations

1. OpenSSL was not on PATH on the Windows host. The project's documented Node crypto fallback generated the encryption key successfully.
2. Docker Desktop was installed but its daemon was initially stopped.
3. Docker port forwarding caused host-local setup to require the one-time setup code even though the request originated from the same physical machine.
4. Keyless platforms were not active until a sentinel/configuration row existed. Before that row, `auto` returned a no-provider 503; after adding Kilo with no secret, two `auto` requests succeeded.

These are onboarding findings, not RESIDUAL defects.

## Trust-boundary decision

FreeLLMAPI is an **inference transport/gateway**, not a verifier or authority source.

RESIDUAL must continue to own:

- task/spec authority;
- budget admission;
- scoped data release;
- independent checks and verification;
- review;
- deterministic integration;
- evidence/receipts;
- release eligibility.

A successful gateway request is candidate-generation evidence only.

## Provenance requirement

Do not flatten a dynamic gateway route into a fixed model identity.

A RESIDUAL receipt should distinguish at least:

```text
requested_route = freellmapi/auto
observed_route  = kilo/nvidia/...:free
gateway         = freellmapi
```

When available, retain fallback trail, rate-limit metadata, gateway version/identity, and provider-reported usage. If an experiment requires exact route identity and the gateway cannot provide it, that trial is UNKNOWN/BLOCKED for the route-specific claim rather than silently attributed to `auto`.

## Proposed privacy policy

Provider routing should be checked before transport against explicit metadata such as:

- workload data classification: `public | internal | confidential | restricted`
- provider privacy: `local | private_api | external_logged | unknown`

Anonymous/free routes that may retain prompts or outputs should default to public/evaluation workloads. More sensitive use requires a route whose privacy policy is compatible with the mission policy and an explicit operator configuration.

## Integration acceptance matrix

A future implementation should retain tests for:

- direct model success;
- `auto` success;
- requested-vs-observed route binding;
- unavailable-provider fallback;
- HTTP 401;
- HTTP 429;
- timeout;
- malformed response;
- gateway unavailable;
- zero configured providers;
- keyless sentinel behavior;
- no secret echo/leakage;
- privacy-policy rejection before transport;
- health-probe transitions;
- model discovery;
- retained fallback/failure provenance.

Prefer extending RESIDUAL's existing OpenAI-compatible transport rather than duplicating FreeLLMAPI's routing implementation.

## Economics / routing experiment

For the same bounded mission corpus compare:

1. local model;
2. direct API route;
3. FreeLLMAPI `auto`;
4. heterogeneous RESIDUAL swarm.

Capture:

- verified completion;
- verifier rejects;
- repair/retry count;
- latency;
- provider-reported token usage;
- monetary cost where authoritative;
- requested and observed route;
- fallback count;
- operator interventions and active operator minutes;
- authority violations;
- final evidence completeness.

Primary hypothesis:

> RESIDUAL can exploit heterogeneous/free inference while independent verification preserves accepted-work quality.

A cheaper or faster candidate stream is not an efficiency improvement if accepted-work quality or evidence integrity declines.

## Classification

- Setup/compatibility observations above: **EVIDENCE**, directly executed and observed on LEGION as reported by the experimenter.
- Anonymous-provider behavior: **SUPPORTED**, based on two observed successful completions.
- Production readiness: **NOT ESTABLISHED**.
- P1 impact: **NONE**.
- Recommended next state: **ACCEPT FOR INTEGRATION EXPERIMENT**.

Tracking: #351

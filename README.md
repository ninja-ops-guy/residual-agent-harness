# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling, fresh-overlay poisoned-guest recovery, and privacy-safe local diagnostic bundles.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main — automated/browser qualification is green

Current `main` is **`160c01a1b1933ee10c82dcf30b1674a17f7560ff`**. It merges **#169**, the privacy-safe demo diagnostics lane, on top of the accepted provider-transport work through #173.

#169 adds local-first session/run/event diagnostics, a bounded session-local diagnostic buffer, sanitized downloadable triage bundles, and bounded service-worker retry/exhaustion events. The retained guest trace and `verify-trace` remain authoritative execution evidence. Diagnostics do not schedule, retry, terminate, authorize, alter provider routing, modify evidence, or determine mission success.

The final #169 head `fb767dc9682533a6092eb36de783e15a3bd47c13` completed exact-head qualification and received an exact-head maintainer attestation before merge. That is **maintainer-reviewed with automated qualification**, not independent human assurance.

All seven observed `push` workflows on exact current main completed **PASS**:

- Factory ownership gate — run `35182396486`;
- clean-install qualification — run `35182396556`;
- measured-evaluation acceptance binding — run `35182396462`;
- M4 qualification runner prerequisites — run `35182396481`;
- Controller/provider contracts — run `35182396520`;
- Command Station checks — run `35182396476`;
- GitHub Pages/WebVM deployment — run `35182396521`.

Pages/WebVM run `35182396521` passed on attempt 1 through provider/publication contract checks, generated desktop+narrow real-browser proof, deployment, published real-guest execution, published narrow-Chromium acceptance and retained live-acceptance proof.

Those results qualify their exact automated/browser/deployment scopes. They do **not** establish successful paid/live Puter inference, model quality, acceptable long-run WebVM reliability, blank-environment release qualification or elapsed soak.

## Live-provider and WebVM boundary

Fresh retained real-account iPhone/WebKit + Puter evidence from mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both separately counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary (`candidate_rejections=0`, `verification_elapsed_ms=0`). The retained build mission was limited to 1536 provider-output tokens while requiring the complete generated file bundle inside the worker envelope.

That mission is retained **FAIL/BLOCKED** evidence for the live-provider path. Semantic verification never ran, so model/candidate correctness remains **UNKNOWN**. It does not establish that output length was the sole cause of the protocol failure.

PR **#176** proposes a bounded build-only output ceiling/default increase to 8192 tokens, preserves 1536 for non-build/source-grounded live mode, and maps provider truncation to `provider_protocol_invalid / response_truncated`. Its current head was built from pre-#169 main and is now diverged from current main, so its earlier exact-head evidence and maintainer attestation are historical only until the branch is refreshed and requalified. Even after any accepted merge, a fresh real-account iPhone/WebKit mission is still required before claiming live-provider success.

Issues **#120** and **#126** remain open. The historical timed-wait/runtime-corruption family and the production poisoned-guest event are reliability evidence; a shared root cause and acceptable long-run recurrence rate remain **UNKNOWN**.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues **#63** and **#48** are closed. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

The prior `main@2b7cb626...` Controller/provider run retained a Python 3.12 **FAIL** on the protected M4 `/proc/<pid>/status` observation race. The green current-main run does not erase that evidence or prove the race fixed. PR **#139** remains the isolated protected-byte repair lane. If accepted, it must follow the deliberate protected review/ownership-baseline/fresh-qualification sequence before downstream **#134** is refreshed.

This documentation does not modify protected Factory/M4 implementation or tests, ownership baselines, qualification anchors or evidence schemas.

## Governance boundary

Merged **#168** establishes the repository's solo-maintainer control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

Describe that as **maintainer-reviewed with automated qualification**. It is not independent human assurance. Claim-specific independent or third-party evidence remains required wherever a security, release or research claim depends on it.

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher serves the Station UI at `http://localhost:8765`. Native mode requires Python 3.11+ and Git:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md) for installation and operator setup.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

## Current priority gates

1. Refresh/requalify #176 on current main, then retain a new real-account iPhone/WebKit mission after any accepted merge; live-provider success remains `UNKNOWN` until positive retained evidence exists.
2. Resolve the protected M4 observation race through #139's protected-byte and ownership-baseline sequence, then freshly requalify downstream #134 where that dependency applies.
3. Keep #120/#126 open until a predefined reliability campaign or proven regression-tested root cause supports closure.
4. Refresh/requalify broader Qualification v1 work (#152) against current main; stale-head results are not inherited.
5. Complete true release/recovery qualification and staged elapsed 24h → 72h → 30-day soak without treating simulation as elapsed evidence.
6. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5, degradation and heterogeneous-routing studies.

Draft **#177** is an IE-001 inference-economics prototype qualification candidate. Its focused suite reports 203 passes and its exact-head repository workflows were reported green, but Q11 genuinely independent current-head technical review remains pending and its branch predates current main; it is **not final IE-001 qualification**. Draft **#178** is documentation-only follow-on backlog for IE-002 through IE-007 and makes no runtime/performance claim. Draft **#175** remains specification-only OpenViking/context-provider planning.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful current-main end-to-end paid/live provider execution, root cause of the historical browser-runtime corruption family, autonomous merge authority, completed long-duration soak, final IE-001 qualification, or live proof of the central research hypothesis.

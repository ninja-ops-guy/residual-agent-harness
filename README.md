# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution, fail-closed runtime handling and fresh-overlay poisoned-guest recovery.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main — qualification is not fully green

Current `main` is **`2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`**, tree **`6751f3c21a53bff725fe0e4c89b0d56004c2f44d`**.

Three recent merges materially changed the browser/demo and governance surface:

- **#159 / `ddf339a9...`** — keeps the durable poisoned-worker fence and adds whole-guest recovery by rotating to a fresh browser-session WebVM writable overlay.
- **#168 / `faae2e28...`** — adopts the solo-maintainer governance model: automated qualification plus exact-head maintainer attestation is the repository merge-control model. This does **not** claim independent human assurance; claim-specific independent or third-party evidence remains separate where required.
- **#153 / `2b7cb626...`** — integrates the bounded terminal-proof marker and post-run control-unlock synchronization used by WebVM browser acceptance.

The final #153 candidate had its applicable exact-head workflows green and an exact-head maintainer attestation before merge. The resulting `main` push, however, is **not fully qualified**: Pages run `35172926305` is `PASS`, but Controller/provider run `35172926291` is `FAIL` on Python 3.12. The retained error is the known protected M4 `/proc/<pid>/status` observation race in `test_timeout_kills_process_group_not_only_parent`: `/proc/<pid>/status` disappeared between `exists()` and `read_text()`. Do not rewrite that failed main run as green.

## Live-provider and WebVM boundary

Pre-recovery production evidence remains important history. A post-#156 iPhone/WebKit public-demo attempt reached **`Provider connected`** but exposed **`RESIDUAL_WORKER_POISONED`** while Mission Control remained at **`GUEST STARTING`**. That observed end-to-end attempt is **FAIL** at the guest-recovery/product boundary. Because no valid live candidate completed the normal verifier/receipt path, successful paid/live Puter candidate execution remains **UNKNOWN**, not `PASS`.

#159 addressed the lack of a supported poisoned-guest recovery path without clearing the existing poison fence. Its exact candidate head passed the observed automated/browser qualification set. The first post-#159 production Pages evidence retained a separate narrow-browser proof failure: the proof parser read a real `:0` exit marker as `:0503`. #153 repairs that acceptance-harness defect and current-main Pages now passes, but this does **not** establish a successful real-account iPhone/WebKit model mission.

Issues **#120** and **#126** remain open. The historical timed-wait/runtime corruption family and the production poisoned-guest event are both reliability evidence; a shared root cause remains **UNKNOWN**.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues **#63** and **#48** are closed. `implementation-status.yaml` remains the implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

Current-main ordinary CI is red because the protected M4 safety-test observation race reappeared on Python 3.12. PR **#139** remains the isolated protected-test repair lane. The required sequence remains: review the protected byte change under the applicable trust-boundary policy → deliberately handle the ownership baseline if accepted → run fresh qualification after any pin change → only then refresh/requalify downstream #134. This documentation does not modify protected bytes, ownership baselines, qualification anchors or evidence schemas.

## Governance boundary

PR **#168** supersedes the proposed repository-wide independent-human merge gate from #146. The active model is solo-maintainer approval with automated qualification and an exact-head maintainer attestation. That model should be described as **maintainer-reviewed with automated qualification**, not as independently human-reviewed.

Independent or third-party review can still be required by a specific security, research or release claim. The governance change does not convert missing external evidence into `PASS`.

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

1. Preserve the exact current-main Controller/provider **FAIL** and resolve the protected M4 observation race through the #139 trust-boundary sequence rather than rerunning it away.
2. Obtain fresh retained real-account iPhone/WebKit evidence on the merged #159 + #153 surface; paid/live Puter success remains `UNKNOWN` until that exists.
3. Keep #120/#126 open until a predefined reliability campaign or proven regression-tested root cause supports closure.
4. Refresh/requalify broader Qualification v1 work (#152) against current main; stale-head results are not inherited.
5. Complete true release/recovery qualification and staged elapsed 24h → 72h → 30-day soak without treating simulation as elapsed evidence.
6. Freeze the confirmatory live-evaluation protocol before observing outcome data, then run R0–R5, degradation and heterogeneous-routing studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful current-main end-to-end paid/live provider execution, root cause of the historical browser-runtime corruption family, autonomous merge authority, completed long-duration soak, or live proof of the central research hypothesis.

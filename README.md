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

## Current main — mixed exact-revision qualification

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**, created by merged **#183**, the bounded mobile provider-session lifecycle repair, on top of merged #179.

#183 extends only browser-side provider liveness handling: valid provider traffic refreshes liveness, the private channel capability can be recovered from provider-tab `sessionStorage`, an already signed-in Puter session can be restored after mobile tab reload, and bfcache/foreground transitions re-advertise state. It does **not** extend per-mission provider authorization, provider call budgets, verifier authority, Factory/M4 boundaries or evidence schemas, and it does not claim to fix the separate iPhone/WebVM crash.

The exact final #183 head **`0b520064cb9deff32dc7d1c261dcaf99f3dc2848`** completed all observed PR workflows **PASS**, including Browser VM Demo CI, Controller/provider, Command Station, Pages and the exact-head maintainer approval gate. The maintainer attestation was submitted before merge. That is **maintainer-reviewed with automated qualification**, not independent human assurance.

Post-merge qualification on exact current main is mixed and must not be summarized as all-green:

- **6 of 7** observed `push` workflows completed **PASS**;
- **Command Station checks** run **`35219212073`** completed **FAIL** on attempt 1;
- within that workflow, the Python **3.11** full `unittest` step failed, while the browser, Docker, Python 3.12 and Python 3.13 jobs passed;
- the precise Python 3.11 failure cause is **UNKNOWN** from the retained workflow metadata currently available;
- **Deploy GitHub Pages** run **`35219212133`** completed **PASS** on attempt 1, including build/browser proof and deployment.

The current-main Command Station failure remains retained **FAIL** evidence. Green sibling jobs and the green pre-merge #183 head do not convert it to `PASS`.

## Live-provider and WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice, but both separately counted calls ended `provider_protocol_invalid`. No candidate crossed the protocol boundary (`candidate_rejections=0`, `verification_elapsed_ms=0`). Semantic verification never ran, so model/candidate correctness remains **UNKNOWN**.

Merged #179 raised the browser build-only provider output ceiling/default to 8192 tokens while preserving the 1536-token non-build/source-grounded bound and classifying normalized truncation/incomplete completion fail-closed. That is a bounded mitigation and better failure classification, not proof that truncation caused the historical failure. Successful paid/live Puter execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses the provider protocol boundary and proceeds through normal verifier/receipt handling.

Fresh physical-device evidence on predecessor `main@250494f2...` also reports that the public demo works on PC while iPhone/WebKit crashes on the heavyweight WebVM path. The lower-level WebKit process-kill mechanism remains **UNKNOWN** because no retained typed iPhone browser exception/crash artifact is available.

Open **#182** is the bounded iOS/iPadOS pre-boot safe-mode candidate. Its exact head `dc1e4233f1fc801c2265ad793b5d7d000c2a1473` has all observed technical workflows **PASS**, including the dedicated iOS WebKit preflight and Pages, but its maintainer approval gate is **FAIL/BLOCKED** and its base predates the #183 main move. It therefore needs refresh/requalification plus exact-head attestation before any merge, followed by production Pages proof and a physical iPhone retest. No physical-iPhone `PASS` is claimed.

Open **#180** remains a narrow consistency candidate for the separate standalone Python generated-build entry point. Its earlier technical evidence is historical to its pre-#183 base and it is not a browser-demo blocker.

Issues **#120** and **#126** remain open. The timed-wait/runtime-corruption family, production poisoned-guest event and physical iPhone/WebKit crash are reliability evidence; a shared root cause and acceptable long-run recurrence rate remain **UNKNOWN**.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues **#63** and **#48** are closed. `implementation-status.yaml` is an implementation-presence manifest; implementation is not equivalent to every-host or production qualification.

The earlier `main@2b7cb626...` Controller/provider run retained a Python 3.12 **FAIL** on the protected M4 `/proc/<pid>/status` observation race. Later green runs do not erase that evidence or prove the race fixed. PR **#139** remains the isolated protected-byte repair lane. If accepted, it must follow the deliberate protected review/ownership-baseline/fresh-qualification sequence before downstream **#134** is refreshed.

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

1. Preserve and triage the exact-current-main Command Station Python 3.11 **FAIL**; do not infer current-main all-green status from sibling passes or the green #183 candidate head.
2. Refresh/requalify #182 on current main, obtain exact-head maintainer attestation, and after any accepted merge require the first production Pages result plus a physical iPhone/WebKit retest.
3. Retain a new real-account iPhone/WebKit + Puter build on the exact deployed accepted revision; live-provider success remains `UNKNOWN` until positive retained evidence crosses the protocol boundary and completes or blocks truthfully through the normal verifier/receipt path.
4. Resolve the protected M4 observation race through #139's protected-byte and ownership-baseline sequence, then freshly requalify downstream #134 where that dependency applies.
5. Keep #120/#126 open until a predefined reliability campaign or proven regression-tested root cause supports closure.
6. Refresh/requalify broader Qualification v1 work (#152) against current main; stale-head results are not inherited.
7. Complete true release/recovery qualification and staged elapsed 24h → 72h → 30-day soak without treating simulation as elapsed evidence.
8. Freeze the confirmatory live-evaluation protocol before outcome access, then run R0–R5, degradation and heterogeneous-routing studies.

Draft **#177** is an IE-001 inference-economics prototype qualification candidate. Its focused suite reports 203 passes and its exact-head repository workflows were reported green, but Q11 genuinely independent current-head technical review remains pending and its branch predates current main; it is **not final IE-001 qualification**. Draft **#178** is documentation-only follow-on backlog for IE-002 through IE-007 and makes no runtime/performance claim. Draft **#175** remains specification-only OpenViking/context-provider planning.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful current-main end-to-end paid/live provider execution, physical-iPhone WebVM reliability, root cause of the historical browser-runtime corruption family, an all-green exact-current-main workflow set, autonomous merge authority, completed long-duration soak, final IE-001 qualification, or live proof of the central research hypothesis.

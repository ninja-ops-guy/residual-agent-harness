# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has expanded into Command Station, Factory M2/M3/M4, distributed/runtime surfaces, Mission Control/WebVM, evaluation infrastructure and bounded self-maintenance research. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## Core model

RESIDUAL decomposes a host-authored task into checked obligations. Local or remote workers propose results; the controller accepts only results that pass registered checks. Stronger or more expensive workers receive the unresolved frontier, relevant dependency values and bounded failure/evidence context rather than unilateral authority over accepted state.

```text
Goal / task
  ↓
Obligation DAG + checks
  ↓
Worker proposal
  ↓
Independent verification
  ├─ PASS → freeze accepted value + receipt
  └─ FAIL / UNKNOWN → residual + counterexample → retry / escalate
```

The worker may be capable, weak, stochastic or wrong. The controller owns acceptance.

## Run the core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
python3 -m unittest discover -s tests -v
```

The built-in demo is scripted and credential-free. It demonstrates controller behavior and evidence handling; it is not a live-model accuracy benchmark.

## Core controller invariants

| Mechanism | Implemented behavior |
| --- | --- |
| Residual frontier | Escalated workers receive unresolved, currently solvable obligations rather than already accepted independent work |
| Independent checks | Model confidence and self-declared success do not accept a result |
| Counterexample feedback | Failed checks provide bounded task-specific failure information |
| Evidence pull | Workers request permitted evidence windows rather than arbitrary source access |
| Frozen accepted values | Later responses cannot silently overwrite accepted obligations |
| Dependency receipts | Accepted values bind to relevant contracts, evidence and parent receipts |
| Revalidated cache | Cache hits are checked again against current inputs and verifier state |
| Explicit budgets | Calls, request bytes and output limits are bounded before provider I/O |
| Honest accounting | Reported usage, modeled estimates and unknown usage remain distinct |
| Claim discipline | `FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions and provider errors do not become `PASS` |

## Relationship to the broader platform

- **Command Station** provides operator-facing mission/run/provider control.
- **Factory M2** provides bounded worker contracts/runtime and host-owned termination.
- **Factory M3** provides Station-issued evidence/receipt handoff.
- **Factory M4** provides deterministic integration/scheduler authority and capable-runner qualification machinery.
- **Mission Control/WebVM** provides browser-facing real-guest workflows, artifact interaction, provider transport, whole-guest fresh-overlay recovery after a poisoned worker, and privacy-safe local diagnostic bundles.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.
- **Self-maintenance research** includes bounded proposal/verification tooling with no autonomous merge authority.

## Current repository boundary

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**, produced by merged **#183** on top of the accepted #179 browser build-output mitigation.

#183 is a bounded mobile provider-session lifecycle repair. It extends browser-side liveness grace, refreshes liveness on valid provider traffic, persists the private channel capability in provider-tab `sessionStorage`, restores an already signed-in Puter session after eligible tab reload, and preserves bfcache/foreground state advertisement. It does not extend per-mission provider grants or call budgets, change model selection, weaken the worker envelope, change verifier/receipt authority, modify Factory/M4 or evidence schemas, or claim to fix the separate iPhone/WebVM crash.

The final #183 head **`0b520064cb9deff32dc7d1c261dcaf99f3dc2848`** completed all observed exact-head PR workflows **PASS** and received the exact-head maintainer attestation before merge. Under merged #168 governance this is maintainer-reviewed automated qualification, not independent human assurance.

Post-merge qualification on exact current main is **mixed**. Six of seven observed `push` workflows completed **PASS**. **Command Station checks** run **`35219212073`** completed **FAIL** on attempt 1 because the Python 3.11 full `unittest` step failed. The browser, Docker, Python 3.12 and Python 3.13 jobs in that workflow passed. The precise Python 3.11 failure cause is **UNKNOWN** from currently retained workflow metadata. Green sibling jobs and the pre-merge candidate qualification do not convert this exact-current-main failure to `PASS`.

**Deploy GitHub Pages** run **`35219212133`** completed **PASS** on attempt 1, including generated build/browser proof and deployment. That is exact-revision automated/browser/deployment evidence; it does not establish live paid-provider/model quality, physical iPhone/WebKit reliability, long-run WebVM reliability, blank-environment qualification or elapsed soak.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both separately counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary (`candidate_rejections=0`, `verification_elapsed_ms=0`). Semantic verification therefore remained **UNKNOWN**.

Merged #179 installs a bounded 8192-token browser build ceiling/default while retaining 1536 for non-build/source-grounded live mode and explicit fail-closed truncation classification. The historical evidence does not prove truncation was the sole/root cause. Successful paid/live provider execution on exact current main remains **UNKNOWN / not established** until a fresh retained real-account mission crosses the protocol boundary and proceeds through normal verification/receipts.

Fresh physical-device evidence on predecessor `main@250494f2...` reports desktop success while iPhone/WebKit crashes on the heavyweight WebVM path. There is no retained typed iPhone crash exception/artifact, so the lower-level WebKit process-kill mechanism remains **UNKNOWN**.

Open #182 is a bounded iOS/iPadOS pre-boot safe-mode candidate. Its exact head `dc1e4233f1fc801c2265ad793b5d7d000c2a1473` has all observed technical workflows **PASS**, including dedicated WebKit preflight and Pages, but its maintainer approval gate is **FAIL/BLOCKED** and the branch predates the #183 main move. It therefore requires refresh/requalification and exact-head attestation before any merge, followed by production Pages proof and a physical iPhone retest. No physical-iPhone `PASS` is claimed.

Issues #120/#126 remain open. Timed-wait diagnostics, historical browser-runtime corruption, the production poison event and the physical iPhone/WebKit failure are reliability evidence. Their exact causal relationship and long-run recurrence rate remain **UNKNOWN**.

## Factory and trust-boundary constraints

Issues #63 and #48 are closed. M2/M3/M4 are implemented and `implementation-status.yaml` is the implementation-presence manifest. M4 qualification remains exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

The earlier `main@2b7cb626...` retained a Python 3.12 Controller/provider **FAIL** on the protected M4 `/proc/<pid>/status` observation race. Later green runs do not erase that failure or prove the race fixed.

PR #139 isolates the protected test-race repair. Because it changes the protected M4 qualification surface, any acceptance must deliberately handle the ownership baseline and be followed by fresh qualification before dependent #134 work is refreshed. This documentation does not alter that baseline, any protected M4 implementation/test byte, qualification anchor, or evidence schema.

## Governance boundary

Merged #168 establishes the repository's solo-maintainer approval model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

It explicitly does **not** represent independent human assurance. A specific release, security or research claim may still require independent or third-party evidence.

## Evaluation guidance

The scripted benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, token savings or API cost. Confirmatory research must bind results to exact source, workload, execution identity, verifier policy and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

Draft #177 is an IE-001 prototype qualification candidate, not final qualification: its focused suite reports 203 passes, Q10/exact-head repository CI and maintainer governance were reported PASS on that branch, while Q11 genuinely independent current-head technical review remains pending. Its branch predates current main. Draft #178 is a documentation-only IE-002–IE-007 implementation backlog and makes no runtime/performance claim. Draft #175 remains specification-only OpenViking/context-provider planning.

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed release/recovery or elapsed-soak qualification, acceptable long-run WebVM reliability, successful current-main end-to-end paid/live provider execution, physical-iPhone WebVM reliability, an all-green exact-current-main workflow set, root cause of the poisoned-guest/browser-runtime failure family, final IE-001 qualification, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

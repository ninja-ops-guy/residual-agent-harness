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
- **Mission Control/WebVM** provides browser-facing real-guest workflows, artifact interaction, provider transport, fresh-overlay recovery, privacy-safe local diagnostics, and an iOS/WebKit pre-boot walkthrough fallback.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.
- **Self-maintenance research** includes bounded proposal/verification tooling with no autonomous merge authority.

## Current repository boundary

Current `main` is **`e996b58566847e88153e6e5196625d52b93e081a`**, produced by merged **#185**.

The accepted #185 integration includes a narrowly bounded protected `runtime_journal.py` writer-admission retry plus its Factory ownership-baseline advance, and the #186 iOS/WebKit pre-boot walkthrough fallback. The final #185 candidate head `068954dd6c1c9a56c9a18fbbce67b1504e2c4b7d` received exact-head maintainer attestation before merge.

Current-main latest observed applicable workflow runs are PASS, including Factory ownership, clean install, measured binding, M4 prerequisites, Controller/provider, Command Station, iOS WebKit preflight and Pages. However Controller/provider run `35263782697` on this **same SHA** remains retained **FAIL** in Python 3.13, followed by PASS run `35264069649`. The exact cause of that earlier failure is **UNKNOWN** from the retained evidence reviewed here. A later same-SHA PASS does not erase it or prove a code-level repair.

Current-main Command Station run `35264069706` is PASS; older `main@2e1341c9...` run `35219212073` remains historical FAIL evidence. Pages run `35263783090`, attempt 1, is PASS.

These results are scoped engineering/browser/deployment evidence. They do not establish paid/live model quality, physical heavy-WebVM iPhone reliability, long-run WebVM reliability, blank-environment qualification, host-loss recovery, or elapsed soak.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 installs a bounded 8192-token browser build ceiling/default while retaining 1536 for non-build/source-grounded live mode and fail-closed truncation handling. Historical evidence does not prove truncation was the sole/root cause. Successful paid/live provider execution on exact current main remains **UNKNOWN / not established** until a fresh retained mission crosses provider protocol validation and proceeds through normal verification/receipts.

The #186 fallback is now accepted through #185. Dedicated current-main iOS WebKit preflight is PASS, but the contract is only that an unsupported/unqualified iOS WebKit profile reaches the lightweight walkthrough before heavyweight guest boot. It is not a PASS claim for heavyweight WebVM on physical iPhone Safari; physical validation and the lower-level WebKit process-kill cause remain open/UNKNOWN.

Issues #120/#126 remain open. Timed-wait diagnostics, historical browser-runtime corruption, poisoned-guest behavior and the physical iPhone/WebKit failure are reliability evidence. Their exact causal relationship and long-run recurrence rate remain **UNKNOWN**.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` is the implementation-presence manifest. M4 qualification remains exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

#185's protected `runtime_journal.py` bytes and corresponding ownership-baseline update are accepted on current main. The accepted retry is limited to mutation-free SQLite writer transaction admission on genuine BUSY/LOCKED contention; journal mutation/COMMIT are not replayed after transaction admission.

Keep this distinct from the older protected M4 `/proc/<pid>/status` observation-race history. PR #139 remains the isolated repair lane for that older issue where applicable, and dependent #134 work still follows its own protected-byte/ownership-baseline sequence. A green current Factory lane does not erase historical exact-revision failures or establish every-host qualification.

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

PR #177 remains an IE-001 prototype candidate, not final qualification. Its prior focused PASS/maintainer evidence is historical to that candidate head and must be reconciled/refreshed against the current IE-001 contract and applicable current-main qualification before a final claim. Draft #178 is documentation-only IE-002–IE-007 backlog and makes no runtime/performance claim. Draft #175 remains specification-only OpenViking/context-provider planning.

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavy-WebVM iPhone reliability, root cause of the poisoned-guest/browser-runtime failure family, final IE-001 qualification, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

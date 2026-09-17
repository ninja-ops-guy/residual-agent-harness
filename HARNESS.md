# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has expanded into Command Station, Factory M2/M3/M4, Mission Control/WebVM, evaluation infrastructure and bounded self-maintenance research. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

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

Current `main` is **`dcf1e5071deb624c637aa72df575089435d72ac9`**, produced by merged **#189** on top of merged **#187**.

#187 accepted a protected test-only repair for the M4 `/proc/<pid>/status` exit-observation race and deliberately advanced the corresponding ownership-baseline pin. It does not change runtime behavior and does not establish universal capable-runner M4 qualification.

#189 accepted a GitHub Pages isolation-boundary repair that keeps the optional `/provider/` helper outside COOP/COEP response rewriting while preserving `/demo/` and heavyweight WebVM isolation. Its exact-head PR workflows, including Pages, were PASS before merge.

The first exact-current-main post-#189 push/deployment workflows were still queued at the latest observation. Therefore post-merge production qualification for #189 remains **PENDING**, not PASS by inference from pre-merge CI.

Historical Controller/provider run `35263782697` on `main@e996b585...` remains retained **FAIL** in Python 3.13. #187 diagnoses and repairs the protected-test observation race behind that failure; the historical evidence remains retained.

These results are scoped engineering/browser evidence. They do not establish paid/live model quality, physical heavyweight-WebVM iPhone reliability, long-run WebVM reliability, blank-environment qualification, host-loss recovery, or elapsed soak.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded browser build-output path; merged #183 repaired provider-session lifecycle behavior; merged #189 repairs the provider helper's COI/CORP publication boundary. None is, by itself, retained proof of successful live Puter inference.

Successful paid/live provider execution on exact current main remains **UNKNOWN / not established** until the merged revision deploys, the provider helper is retained as loading/sign-in capable, and a fresh mission crosses provider protocol validation into normal verification/receipts.

The #186 fallback remains accepted: detected iOS/iPadOS WebKit is routed to the lightweight walkthrough before heavyweight guest boot. This is not a PASS claim for heavyweight WebVM on physical iPhone Safari; physical validation and the lower-level WebKit process-kill cause remain open/UNKNOWN.

Issues #120/#126 remain open. Timed-wait diagnostics, historical browser-runtime corruption, poisoned-guest behavior and the physical iPhone/WebKit failure are reliability evidence. Their exact causal relationship and long-run recurrence rate remain **UNKNOWN**.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` is the implementation-presence manifest. M4 qualification remains exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

#185's protected `runtime_journal.py` writer-admission behavior and ownership-baseline update remain accepted. #187 additionally accepts the protected M4 safety-test observation repair and ownership pin. Keep those scoped claims distinct from the separate #139→ownership-baseline→#134 protected sequence.

A green Factory/hosted lane does not erase historical exact-revision failures or establish every-host qualification.

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

PR #177 remains an IE-001 prototype candidate, not final qualification. PR #188 is an additive consensus-authority escalation lab candidate, not accepted research evidence. PR #190 is a provider-channel recovery candidate based on the pre-#189 main and requires refresh/requalification. PR #191 is an unaccepted automated PR-review workflow candidate.

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, root cause of the poisoned-guest/browser-runtime failure family, final IE-001 qualification, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

# RESIDUAL Qualification v1

Status: implementation baseline

RESIDUAL Qualification v1 turns the repository's existing evidence-bearing test programs into one release-candidate qualification system.

## Goals

A qualified candidate is not merely a green commit. Qualification MUST identify the exact source revision and shipped artifacts, retain the evidence for every required gate, distinguish `PASS` / `FAIL` / `UNKNOWN` / `SKIP`, and make the final decision reproducible from machine-readable inputs.

## Qualification layers

1. **Developer** — deterministic unit, contract, property/state-machine invariants.
2. **Pull request** — full deterministic suite, trust-boundary checks, mutation canary, generated lifecycle histories, the real DSM delivery-fault matrix, cross-browser user journeys, exact-package qualification and a single fail-closed manifest.
3. **Main / release candidate** — the same exact-artifact gates plus build provenance attestation for the promoted wheel.
4. **Nightly** — deeper deterministic state exploration, 30 virtual-day fixture stress and a real short process soak.
5. **Release soak** — an uninterrupted 24h process run, then 72h after 24h is clean. A 30d runner exists for a persistent qualification host and remains long-duration operational evidence.
6. **Live provider** — a bounded real adapter request records model identity, latency, usage and response identity without silently falling back to a fixture.
7. **Research** — preregistered frozen evaluation over an already-qualified candidate. Product qualification and empirical hypothesis validation remain separate.

## Evidence contract

Every contributing gate emits a JSON envelope containing at minimum:

- schema version;
- gate ID and result (`PASS`, `FAIL`, `UNKNOWN`, `SKIP`);
- commit and tree SHA;
- environment identity;
- command / test identity;
- start/end timestamps;
- evidence file hashes;
- skip/unknown counts;
- notes/non-claims.

The release aggregator refuses to certify when required evidence is absent, bound to another source tree, malformed, or reports `UNKNOWN` / `FAIL`. It also writes `failure-ledger.jsonl`; failed reruns are new observations rather than replacements for the original failure.

## Test-strength requirements

### Property and state-machine testing

`tests/qualification/test_stateful_runtime_journal.py` exercises the real `RuntimeJournal` through generated claim/start/revoke/finish/purge/restart sequences. Its oracle checks that:

- a revoked attempt cannot publish a candidate;
- stale ownership/fencing authority never becomes current again;
- terminal state remains terminal;
- attempt identity is unique;
- restart/reopen preserves durable state and a valid observation chain.

Hypothesis runs with a fixed version, no persistent example database and deterministic generation so the qualification run itself is replayable.

### Mutation canary

`scripts/qualification_mutation_canary.py` applies known semantic mutations to an isolated CI checkout and requires focused tests to kill every mutant. Initial canaries cover:

- revoked-candidate acceptance inversion;
- candidate lease resurrection;
- `.git` path-policy bypass;
- forbidden-prefix bypass.

This is a deterministic minimum mutation gate. It complements branch coverage; it does not claim exhaustive mutation analysis over the whole repository.

### Generated lifecycle histories

`residual/qualification/schedule.py` generates seeded multi-lane lifecycle interleavings over the real runtime journal, including stale probes, duplicate claims, duplicate terminal writes and restart/replay. Raw journal IDs/timestamps remain intentionally unique; replay identity hashes the deterministic semantic payload stream, generated trace and final state.

### Real DSM delivery faults

The release aggregator also executes the existing `residual.dsm` evidence generator. This is the authoritative delivery-fault gate for:

- duplicate delivery;
- delayed delivery;
- reordered delivery;
- lost delivery plus retransmission;
- combined faults;
- crash/restart/replay;
- durable deduplication;
- stale fencing;
- deterministic accepted-state reconstruction.

Its claim remains bounded to the documented single-writer crash-stop design. It does not convert the DSM layer into a split-brain-safe consensus system.

### Coverage strength

Qualification records branch coverage for the new qualification layer plus critical Factory/runtime surfaces. Coverage is treated as reachability evidence only; the mutation gate independently tests whether selected trust-boundary assertions actually detect semantic breakage.

### Cross-browser qualification

The same full Command Station browser user journey runs under Chromium, Firefox and WebKit through `tests/playwright-browser-shim.cjs`. The qualification browser toolchain is version-locked.

### Soak

`scripts/qualification_process_soak.py` launches a real process, probes its HTTP surface, samples Linux RSS and file-descriptor count, detects early exit and calculates growth slopes. A process that stays alive while leaking resources does not automatically pass.

The scheduled nightly tier additionally runs the existing deterministic 30-virtual-day `SoakHarness`. That fixture is explicitly labeled as simulation and never substituted for wall-clock evidence.

For release-duration runs:

```bash
python scripts/qualification_long_soak.py --tier 24h --output-dir runs/qualification-long-24h
python scripts/qualification_long_soak.py --tier 72h --output-dir runs/qualification-long-72h
python scripts/qualification_long_soak.py --tier 30d --output-dir runs/qualification-long-30d
```

The 24h/72h GitHub workflow intentionally targets a persistent self-hosted runner. The 30d CLI is intended for a persistent qualification host because ordinary CI job lifetimes are not treated as 30-day operational evidence.

## Statistical methodology

`residual/eval/stats.py` retains the existing Mann-Whitney/Welch interfaces and adds paired/block-aware analysis for confirmatory R0-R5 work:

- paired differences and paired t-test;
- paired effect size (`Cohen's dz`);
- deterministic bootstrap confidence interval for the paired mean difference;
- Holm-Bonferroni family-wise error correction;
- a-priori paired normal-approximation sample-size planning.

Confirmatory repeated observations SHOULD be blocked by task/model/seed/workload identity where applicable. The confirmatory sample size must be justified independently of the development minimum of three repeats. Primary and secondary endpoints must be declared before final live results are observed.

## Exact-artifact rule

The artifact that is qualified is the artifact that may be promoted. Rebuilding between qualification and release invalidates artifact-level qualification.

Qualification v1 builds one wheel, hashes it, installs those exact prebuilt bytes into a fresh isolated environment with `scripts/qualify_exact_wheel.py`, tests the container artifact, and binds artifact hashes into the final manifest. Non-PR release qualification also emits build-provenance attestation for the wheel.

The standalone WebVM demo CI now uses the same immutable WebVM revision as the production Pages pipeline rather than a floating upstream `main` branch.

## Toolchain identity

The optional `qualification` extra is version-locked independently of the ordinary development test extra. Browser Playwright is also exact-version pinned. Runtime dependency policy remains unchanged by this qualification work.

## Live provider canary

`.github/workflows/qualification-provider-canary.yml` is manually dispatched with a provider and exact model identifier. Cloud providers use the repository secret `RESIDUAL_QUALIFICATION_LLM_API_KEY`; compatible endpoints may additionally provide a base URL.

The canary records only bounded evidence: provider/model identity, finish reason, latency, normalized usage, response length and response SHA-256. Missing credentials produce `UNKNOWN` in the report/evidence rather than fixture substitution. A successful canary does not establish model quality.

## Failure classification

Every nondeterministic or infrastructure-sensitive failure is retained as an observation and may be classified as one of:

- `SUT_DEFECT`
- `TEST_DEFECT`
- `ENVIRONMENT_FAILURE`
- `EXTERNAL_DEPENDENCY`
- `UNSUPPORTED_CAPABILITY`
- `PROVENANCE_UNKNOWN`
- `UNCLASSIFIED`

A rerun creates a linked observation; it never overwrites the original failure.

## Workflows

- `.github/workflows/qualification-v1.yml` — PR/main exact-candidate qualification and final release manifest.
- `.github/workflows/qualification-nightly.yml` — deeper daily exploration plus weekly one-hour live process soak.
- `.github/workflows/qualification-long-soak.yml` — manual uninterrupted 24h/72h self-hosted release soak.
- `.github/workflows/qualification-provider-canary.yml` — bounded real provider qualification.

The implementation lives primarily under `residual/qualification/`, `scripts/qualification_*.py`, and `tests/qualification/`.

# RESIDUAL Qualification v1

Status: implementation baseline

RESIDUAL Qualification v1 turns the repository's existing evidence-bearing test programs into one release-candidate qualification system.

## Goals

A qualified candidate is not merely a green commit. Qualification MUST identify the exact source revision and shipped artifacts, retain the evidence for every required gate, distinguish PASS/FAIL/UNKNOWN/SKIP, and make the final decision reproducible from machine-readable inputs.

## Qualification layers

1. **Developer** — deterministic unit, contract, property/state-machine invariants.
2. **Pull request** — full deterministic suite, trust-boundary checks, mutation canary, generated schedule/fault histories, browser smoke.
3. **Main / release candidate** — build-once artifact identities, clean-install qualification, exact-artifact end-to-end checks, evidence manifest and release certificate.
4. **Nightly** — extended generated histories, deterministic random-seed exploration and short soak.
5. **Release soak** — 24h, then 72h after 24h is clean; 30d remains operational evidence.
6. **Research** — preregistered frozen evaluation over an already-qualified candidate. Product qualification and empirical hypothesis validation remain separate.

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

The release aggregator refuses to certify when required evidence is absent, bound to another source tree, malformed, or reports UNKNOWN/FAIL.

## Test-strength requirements

### Property and state-machine testing

The generated lifecycle model explores operation sequences rather than fixed examples. The oracle checks invariants including:

- acceptance is monotonic and cannot be resurrected from rejected/unknown state;
- duplicate delivery is idempotent;
- stale ownership/fencing authority cannot commit state;
- resume preserves run identity and cannot manufacture an independent repetition;
- terminal state remains terminal;
- event replay produces the same canonical accepted state.

Every failing seed is retained and can be replayed deterministically.

### Mutation canary

Qualification includes a zero-dependency mutation canary for the trust boundary. It applies known semantic mutations to an isolated copy of selected modules and runs focused tests. Surviving canary mutations fail the gate. This is intentionally small and deterministic; deeper mutation campaigns may additionally use an external mutation engine.

### Generated distributed histories

The schedule explorer generates deterministic histories containing duplicate, delayed, reordered and dropped messages, restarts, stale leases, cancellations and recovery. Histories are checked against safety invariants and retained with their seeds.

### Soak

Soak reports record samples and slopes for memory, file descriptors, process count and application-specific counters when available. A run that remains alive but exhibits unbounded positive growth is not automatically a PASS.

## Statistical methodology

Confirmatory R0–R5 experiments MUST use a frozen analysis plan. Repeated observations are blocked/paired by task and experimental identity where applicable. Reports SHOULD include effect sizes and confidence intervals, not only p-values. The confirmatory sample size must be justified independently of the development minimum of three repeats. Primary and secondary endpoints must be declared before final live results are observed.

## Exact-artifact rule

The artifact that is qualified is the artifact that may be promoted. Rebuilding between qualification and release invalidates artifact-level qualification. Release evidence records wheel/container/browser-image hashes and may attach external provenance attestations when the release mechanism supports them.

## Failure classification

Every nondeterministic or infrastructure-sensitive failure is retained as an observation and classified as one of:

- `SUT_DEFECT`
- `TEST_DEFECT`
- `ENVIRONMENT_FAILURE`
- `EXTERNAL_DEPENDENCY`
- `UNSUPPORTED_CAPABILITY`
- `PROVENANCE_UNKNOWN`
- `UNCLASSIFIED`

A rerun creates a linked observation; it never overwrites the original failure.

## Initial implementation

The v1 implementation lives in `residual/qualification/` and `scripts/qualification_v1.py`. GitHub Actions workflows under `.github/workflows/qualification-v1.yml`, `qualification-nightly.yml`, and `qualification-soak.yml` exercise the release, discovery and long-running tiers respectively.

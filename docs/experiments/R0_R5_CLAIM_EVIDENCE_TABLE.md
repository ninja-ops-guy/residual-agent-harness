# R0–R5 Claim–Evidence Table (Reconciled Freeze)

**Schema:** `residual.r0-r5.claim-evidence.v1`. Companion to `R0_R5_FROZEN_PROTOCOL.md`.
No empirical result is asserted by this table. Empty/unfilled evidence cells mean NOT MEASURED; they are not zero values. Every claim maps to implementation + test + machine-readable evidence. Development-fixture results never promote into research claims.

## Intended claims

| Claim ID | Statement | Implementation | Executable test | Required evidence artifact | Analysis (from R0_R5_ANALYSIS_PLAN.md) | Status |
|---|---|---|---|---|---|---|
| C01 | Constraining + verifying unreliable workers improves accepted reliability vs raw execution | R0/R4 adapters over `residual/eval_frozen` + M4 (`residual/factory/m4_integrator.py`) | `tests/test_eval_launch.py`, `tests/test_r0_r5_protocol.py`; M4 qualification suite (#88 preflight) | Run bundles `r0r5-*` (bundle-v1) + retained external manifest digest | H01 (AER, R4−R0) and H02 (verified goodput, R4−R0), Holm family, paired family-cluster bootstrap | Unmeasured; hypothesis |
| C02 | Dynamic swarming improves the reliability/usefulness tradeoff over static COVD | R5 adapter (`dynamic_swarm` layer) | same harness; adapter qualification | Run bundles + all-cost/latency Pareto panel | H03 (AER, R5−R4), H04 (goodput, R5−R4); Pareto frontier descriptive | Unmeasured; hypothesis |
| C03 | Accepted reliability degrades more slowly than raw worker reliability across capacity classes | Degradation cells R0/R4/R5 × S/M/W/L | degradation runner qualification | Degradation cohort bundles (separately labeled if environment differs) | Descriptive paired attenuation contrast + goodput change; no confirmatory p | Unmeasured; hypothesis |
| C04 | Cheaper/local workers can contribute useful work economically | H0–H3 routing arms (R5 control surface) | routing adapter qualification | All-role usage/cost records (`records/usage.jsonl`, `timing.jsonl`) | Descriptive H1/H2/H3−H0 effects; cost per useful acceptance | Unmeasured; hypothesis |
| C05 | Accepted tree is exactly the verified tree | M4 merged in main (`de9c9fa`, PR #81) | M4 qualification on exact merged commit/tree (#88); INV-02 property tests; namespace probes PASS (no skips) | Qualification record `residual.m4-qualification.v1` + retained probe/suite outputs | Gate evidence, not a statistical claim | Under independent review; merging alone is not qualification |
| C06 | Every paper-facing metric is reproducible offline | `residual.reproduce` (bundle-v1) | `tests/test_reproduce.py`, `tests/test_reproduce_cli.py` | Reconstruction report with matching externally pinned manifest SHA-256 | Deterministic replay equality of all report fields | Tooling exists; real-bundle replay pending |
| C07 | Verifier quality is measurable independently of execution failures | T2 adversarial corpus + typed scorer (`scripts/validate_adversarial_corpus.py`) | `tests/test_adversarial_corpus.py` | Scoring report with decision-only confusion rates; UNKNOWN/timeout/signal excluded | Corpus metrics (acceptance/defect precision & recall, coverage) with raw denominators | Corpus frozen; verifier runs pending |
| C08 | Restarts preserve acceptance semantics (no duplicate acceptance) | DSM-004/PROD-007 protocol implementations (pending) | Durable-boundary crash matrix (PROD-007) | Retained restart traces with before/after accepted-head and receipt hashes | Gate: zero unauthorized/duplicate acceptance across matrix | Design only; not implemented |
| C09 | Metrics/figures derive only from retained evidence | `residual/eval_frozen/report.py` (hash-bound report) | report recomputation from records; registry-mutation invariance probe | `report_sha256` chain: records → report → CSV/plot inputs | Recomputed probabilities must equal recorded | Mechanism present; live data pending |
| C10 | Paired cluster analysis preserves repeated-trial dependence | Analysis implementation (to be written, reviewed) | Exact small-family cross-checks; synthetic coverage/power simulations with frozen seed | Analysis code SHA-256 + simulation logs | The analysis plan itself | Specified; implementation pending |

## Explicit non-claims (binding)

1. No claim of model quality, provider economics, or comparative superiority of any external framework.
2. No claim from the fw1-* development fixture, the VC-* adversarial corpus, the synthetic-demo bundle, or the engineering-envelope measurements; all are `development_fixture`/`engineering-only` and `publication_ready: false`.
3. No containment/security claim from namespace-skip or UNKNOWN probe results; a denied prerequisite is not a denied attack.
4. No claim that merging PR #81 or closing an issue constitutes M4 qualification; only retained evidence on the exact merged commit/tree qualifies.
5. No noninferiority/equivalence claim from a nonsignificant goodput difference.
6. No AER-only "reliability" claim without the joint goodput/coverage/missingness report.
7. No degradation, heterogeneous-routing, soak (24h/72h/30-day), production-recovery, or blank-VM claim from this protocol; each requires its own retained evidence per the frozen extensions.
8. No metric, corpus, verifier, or workload decision may be made after live results arrive; amendments are new versions and exploratory.

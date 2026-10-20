# R0–R5 Pre-Registered Analysis Plan (Reconciled Freeze)

**Schema:** `residual.r0-r5.analysis-plan.v1`. Authoritative for identifiers and constants. Adopts PR #91's statistical preparation (`experiments/preflight/science/protocol.v1.json` @ sha256 `8f0010b51b932af1fa0f9d3018bf6e02029eab784c9fe4f9885bc99667949d59`, document `docs/program/science/analysis-plan.md`) and PR #90's metric definitions and scheduled-denominator policy. Any change after outcome access is exploratory and versioned separately.

## Estimands and denominators

`N` = all scheduled cells (6 configurations × F families × 3 tasks × 10 repetitions), including missing, crashed, timed-out, not-run and unknown-graded cells. No replacement runs; no post-result exclusions.

| Metric | Definition | Zero/unknown rule |
|---|---|---|
| AER (accepted error rate) | known incorrect accepted / established acceptances | null at zero acceptances; with u unknown accepted grades report bounds [b/a, (b+u)/a]; with m unknown acceptance statuses widen to [b/(a+m), (b+u+m)/(a+m)] |
| Accepted correctness (P_X_given_A) | known correct accepted / established acceptances | null at zero acceptances; unknown grades reported separately |
| Verified goodput (ASSR) | known correct accepted / N | unresolved cells contribute 0 to numerator (operational outcome, not imputed wrong); also report upper bound assigning unresolved potentially-successful cells success |
| Acceptance coverage (P_A) | established accepted / N | unknown acceptance ≠ rejection |
| Accepted-error burden | known incorrect accepted / N | — |
| Raw correctness (P_X) | independently correct raw proposals / N | report grading coverage and unknown count; conservative observed fraction, not unbiased estimate |
| False rejection | rejected ∧ independently correct / independently correct with known acceptance | — |
| Cost | all attempted calls incl. failures/retries/coordinator/verifier; known subtotal + unknown count; total null if any component unresolved | missing usage/price is null, never zero |
| Cost per useful acceptance | total cost / known correct accepted | null at zero denominator |
| Latency | all-cell capped elapsed to locked deadline; median + p95; deadline-hit and unknown-timing counts | completed-only latency is labeled secondary |
| Throughput | known correct accepted / measured study wall seconds | — |

Point estimates pool numerator and denominator across the fixed balanced design (never an average of per-task ratios). R0: externally captured final proposal is the designated output (A=1 when a final artifact exists). Diagnostics retained: verifier state counts, rework, merge conflicts, tokens, GPU seconds, unknown-usage count.

## Clustering, CIs, paired tests

- Sampling cluster: independent task family (not worker/receipt/trial). Families disjoint from development and smoke inputs.
- **Bootstrap:** 20,000 paired whole-family cluster draws with replacement; carry all tasks/repeats/configurations/unknown markers of each selected family together. Two-sided 95% percentile intervals, linear interpolation at 0.025/0.975. Ratio estimands recompute both pooled sums per draw; zero-denominator draw → entire ratio CI unavailable, report undefined-draw fraction (never silently discard). Degenerate bootstrap → descriptive quantiles only, inferential coverage unavailable. Zero observed errors never yields a certified [0,0] bound. Below 30 families, all intervals are descriptive.
- **Paired test:** whole-family label-swap; enumerate all 2^F patterns if F≤20 else 99,999 uniform swap draws; two-sided MC p = (1 + count(|T*| ≥ |Tobs|))/(B+1), ties included. Exchangeability violations documented; if untenable, withhold confirmatory inference.
- **Seeds:** analysis PRNG = Python `random.Random` seeded by `int.from_bytes(SHA256((protocol_sha256 + ":" + analysis_id).encode()).digest(), "big")`; retain Python version, resample-index hash, implementation hash.
- The existing unpaired Mann–Whitney/Welch code (`residual/eval/stats.py`) is NOT the analysis engine. Reviewed implementation + exact small-family cross-checks + missing-cell/zero-denominator tests + synthetic coverage checks are launch gates.
- Additionally report Wilson score intervals for simple binomial proportions (per-configuration acceptance coverage, known-grade raw correctness) as descriptive single-arm summaries; Wilson does not replace the paired bootstrap for contrasts.

## Multiplicity

One fixed Holm family, exactly four two-sided hypotheses (family never shrinks; unavailable contrasts enter at p=1):

| ID | Contrast | Endpoint |
|---|---|---|
| H01 | R4 − R0 | AER |
| H02 | R4 − R0 | verified goodput |
| H03 | R5 − R4 | AER |
| H04 | R5 − R4 | verified goodput |

Sort by (p, id); compare i-th to 0.05/(4−i+1); stop at first failure; report monotone adjusted values. Also show 98.75% percentile intervals for the four contrasts, labeled approximate Bonferroni. Ordinary 95% CIs are marginal, not simultaneous.

R1/R2/R3 contrasts, strata, degradation, heterogeneous routing, orchestration tax, verifier curves, fault and soak analyses are prespecified descriptive secondary analyses: effects + intervals, no confirmatory p-values.

## Decision rules

- C01 supported only if H01 and H02 both reject under Holm AND missingness/unknown bounds do not overturn the sign. AER improvement alone supports only a conditional reliability claim.
- C02 supported only if H03 and H04 both reject; a nonsignificant goodput change establishes nothing.
- Practical-effect thresholds (fixed, not margins): 5-percentage-point goodput increase; 1-percentage-point AER decrease. Reported separately from p-values.
- Artifact corruption/conflict blocks the numerical report. External interruption that prevents completing the locked design terminates confirmatory claims for the affected contrasts (p=1 retained).
- Negative and inconclusive results are published with the same ledger; no result-driven task/model/verifier changes.

## Power/design calculation (gate)

Before launch, offline simulation chooses F = smallest multiple of 10 in [30..200] achieving ≥80% power for the 5-point goodput effect under every predeclared scenario: baseline goodput ∈ {0.2, 0.5, 0.8}, within-family correlation ∈ {0.1, 0.3, 0.5}, two-sided α = 0.05/4, 10,000 synthetic designs per scenario, frozen seed 20260915, planned paired test. Also report detectable AER effect over acceptance ∈ {0.25, 0.5, 0.75} and baseline AER ∈ {0.01, 0.05, 0.10}. Preserve simulation model, code hash, seed, assumptions. If no design qualifies or resources cannot support it, results are explicitly descriptive. Never increase N after inspecting results.

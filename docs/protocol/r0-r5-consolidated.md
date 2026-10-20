# Frozen experimental protocol — R0–R5 (consolidated)

**Status: `protocol_frozen_preparation_only`. This document freezes a protocol
and corpus; it produces, contains, and implies no model results.**
Consolidates draft PR #90 ("Prepare gated R0–R5 evaluation and repair M5
completion checks") and draft PR #91 ("Prepare trust, science and product
programs with frozen artifacts and offline replay") into one reviewable
protocol + corpus manifest. Both drafts remain open for Lane 3 disposition;
this document does not close or supersede them administratively.

## Provenance of each element

| Element | Source |
|---|---|
| Frozen workload harness, R0–R5 arms, metrics, `report_sha256` evidence artifact | merged #86 (`residual/eval_frozen/`), reused unchanged |
| Acceptance/evidence binding requirements (fresh run identity, anti-replay, merged-M4 binding) | merged #103 (`residual/eval_frozen/acceptance_binding.py`, `ci/measured-eval-binding.yml`), reused unchanged |
| Ten repetitions, paired schedule seeds, scheduled-denominator / no-replacement rule, fail-closed launch gate, blocked-not-frozen readiness semantics | #90 preparation protocol |
| Statistical plan (paired family-cluster bootstrap, label-swap test, Holm family, missingness/UNKNOWN bounds) | #91 science plan |
| Corpus manifest + fail-closed checker | consolidated here from #90's hash-bound workload commitment and #91's hash-locked corpus pattern |
| #90's M5 completion-check repair | **excluded**: it modifies protected runtime paths (`residual/factory/loop_runtime/`); see Dependencies |

## 1. Frozen workload definition

The workload is the `FrozenWorkload` (schema `residual.frozen-workload.v1`)
defined by `residual/eval_frozen/workload.py::development_workload` on merged
main, bound by immutable workload hash
`9feafda5b3bf7fcfe5fb16422b003195be47a204de00f2894f4caeee8166b248` (8 tasks, 2
families, seed 20240517). The machine-readable corpus manifest with per-item
content hashes, split assignments and provenance is
[`experiments/corpus/manifest.v1.json`](../../experiments/corpus/manifest.v1.json);
`scripts/check_corpus_manifest.py` validates it fail-closed.

**Contamination note (from both drafts):** this corpus is public fixture
material. It gates pipeline correctness only. A confirmatory live study
requires a separately authored, privately held workload family set, frozen and
externally anchored before any result observation. The fixture `evaluation`
slice is "held-out" relative to development iteration, not contamination-safe.

## 2. Arms and expected outcomes

Arms R0–R5 are exactly `residual/eval_frozen/configs.py::CONFIGURATIONS`
(cumulative control layers; all other factors held constant via
`CONTROLLED_CONSTANTS`), hash-bound in the manifest:

- **R0** raw unconstrained execution — baseline: lowest expected `P(X|A)`
  contribution (no acceptance authority); `AER` not meaningfully constrained.
- **R1** orchestrated decomposition.
- **R2** + contracted worker interface.
- **R3** + constraints, observation, verification — first arm where acceptance
  is verifier-gated.
- **R4** + deterministic integration (COVD) — primary treatment arm.
- **R5** + dynamic swarm orchestration — tests whether added coordination
  preserves R4's reliability at acceptable cost/latency.

Expected outcomes are hypotheses, not predictions of record: monotonically
non-decreasing `P(X|A)` from R0 to R4, `AER` reduced in R3–R5 vs R0–R2, R5 not
dominated by R4 on the reliability/cost Pareto front. Falsification: any arm
ordering reversal on the frozen corpus with retained evidence stands and is
published.

## 3. Splits

- `development` (2 tasks): pipeline smoke and selection iteration; **never**
  enters confirmatory denominators.
- `held_out` (6 tasks, incl. 2 fault-labeled): confirmatory slice.

No task id appears in both splits; the checker rejects leakage, reassignment,
unknown or omitted ids. A confirmatory live cohort needs ≥30 independent
task families (#91 design gate); the current 2-family fixture does not meet
that bar and results on it are descriptive only.

## 4. Metrics (exact definitions, from `eval_frozen/metrics.py`)

Denominators are the **scheduled** cell set (failures, timeouts, missing and
not-run cells remain; no replacement runs):

- `P(X)`: independently correct raw proposals / scheduled N.
- `P(A)`: accepted / scheduled N.
- `P(X|A)`: accepted independently correct / accepted; **null (undefined) when
  accepted = 0**, never 0 or 1.
- `AER` = P(not X | A) (false acceptance rate); report identification bounds
  `[b/a, (b+u)/a]` when accepted grades are unknown (#91 missingness rule).
- `ASSR`: accepted-and-sound / scheduled N.
- `FCR`: caught / fault-labeled, only where fault labels exist.
- Latency: trusted monotonic per-cell elapsed, median and p95 with
  timeout/censoring counts. Cost: all attempted calls incl. failures; unknown
  usage stays null. Gate C recomputes P(X), P(A), P(X|A) independently and the
  run aborts on divergence; the report carries a reproducible
  `report_sha256` (#86).

## 5. Statistical plan

- **Primary contrasts (fixed Holm family of 4, α = 0.05):** H01 R4−R0 AER;
  H02 R4−R0 ASSR; H03 R5−R4 AER; H04 R5−R4 ASSR. Holm sequential rejection,
  ordered by `(p, id)`; unavailable contrasts stay in the family at `p = 1`.
- **Intervals:** 20,000 paired family-cluster bootstrap draws (resample whole
  families, carry all tasks/repeats/arms/unknowns), two-sided 95% percentile.
- **Tests:** paired whole-family label-swap; exact enumeration if F ≤ 20 else
  99,999 Monte Carlo swaps with add-one convention.
- **Power:** a separate offline simulation (10,000 synthetic designs per
  nuisance scenario; baseline goodput 0.2/0.5/0.8, within-family correlation
  0.1/0.3/0.5) selects the smallest multiple-of-10 family count in [30, 200]
  giving ≥80% power for a 5-point goodput effect at two-sided α = 0.05/4.
  **No power calculation has been run; none of these numbers is an achieved
  power claim.** If no design qualifies, results are descriptive.
- R1/R2/R3 contrasts, strata, degradation and heterogeneous routing are
  prespecified descriptive secondaries: effects and intervals, no confirmatory
  p-values.

## 6. Budget (preregistered ceilings — values are gates, not commitments)

| Ceiling | Value |
|---|---|
| Repetitions per (task, arm) | 10 (#90 preparation choice, retained) |
| Temperature | 0.0; provider seed support recorded, not assumed |
| Cross-trial caching | disabled |
| Per-task provider calls / seconds / USD | **unset — launch gate**; must be pinned in the launch manifest before freeze of a live cohort |
| Compute/provider | single immutable provider/model identity across all arms; degradation/routing cohorts are separate preregistered extensions |

Budget exhaustion produces outcomes in the denominator, never exclusions.

## 7. Amendment rule

Any change to workload, splits, arms, metrics, statistical plan, budgets or
this document after its freeze digest is retained requires: a new protocol
version id, a new `manifest_sha256`, retention of the prior version, and —
if any confirmatory result has been observed — relabeling of all affected
analysis as exploratory. Boolean flag edits can never enable execution
(#90's fail-closed checker semantics are adopted by reference).

## 8. Freeze gate

This protocol is frozen **before any model results were observed** (none
exist on this branch; `results` is null everywhere). Confirmatory execution
additionally waits for:

1. **#108 repair** (protected runtime/schema) — owned by Lane 1 only.
2. **Lane 4 qualification** of the measured evidence path (acceptance binding
   per #103, fresh run identity, replay rejection).
3. Live launch gates retained from both drafts: reviewed R0–R5 executable
   adapters, immutable model identity, privately held workload families,
   independent graders, completed power record, externally anchored freeze
   digest.

## 9. Dependencies declared (for Lane 1 / coordination)

- **#90's M5 completion-check repair touches protected runtime paths**
  (`residual/factory/loop_runtime/controller.py`, `.../state.py`): reject
  unsupported verifier states and duplicate result IDs; late abort/deadline
  precedence over completion. This consolidation does **not** include it; it
  is reported as a protected-path dependency for Lane 1 to propose under #108.
- Live confirmatory runs depend on #108 repair + Lane 4 qualification (above).

## Non-claims

This PR freezes a protocol and a corpus manifest. It produces no results,
qualifies no sandbox, closes no issue, authorizes no launch, and changes no
runtime, schema, or demo file. Skipped/failed historical attempts referenced
from #90/#91 remain preserved in those drafts, not deleted.

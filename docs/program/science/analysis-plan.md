# Pre-results analysis plan v1

This specification is the intended analysis, not a claim that the current
evaluation CLI implements it. The machine-readable protocol is authoritative
for identifiers and constants. A changed estimand, test, model, workload, margin,
budget or selection rule requires a new preparation version and an explicit
amendment; after outcome access it is exploratory and cannot replace the original.

## Population, pairing and design

The sampling cluster is the independently authored **task family**, not a worker,
receipt, repeated trial, or arbitrary split of one task. Families must be disjoint
from development and smoke inputs. Every task has ten repetitions; every
`(family_id, task_id, repeat_index)` block runs each assigned configuration against
the same immutable starting artifacts and external grader. Seeds control schedule
ordering, not provider determinism. Retain the complete precomputed schedule,
time block and order; interleave configurations within blocks. Disable cross-trial
caches and reset learned controllers to the same pre-frozen state. Adaptation
within one trial is an intervention and must not leak into another trial.

Use a balanced design: equal tasks per family and ten repeats per task, with at
least 30 independent families. The minimum is an inference gate, **not a power
guarantee**. A separate offline design calculation must choose the smallest
multiple of ten families from 30 through 200 giving at least 80% power for a
five-percentage-point goodput effect under every predeclared nuisance scenario:
baseline goodput 0.2/0.5/0.8, within-family correlation 0.1/0.3/0.5, two-sided
alpha 0.05/4, using 10,000 synthetic designs per scenario and the planned paired
test. Preserve the simulation model, code hash, seed and assumptions. Set tasks
per family to three. The design calculation must also report, without optimizing
on real outcomes, the detectable AER effect over acceptance 0.25/0.5/0.75 and
baseline AER 0.01/0.05/0.10. If no design meets the rule or resources cannot support
it, the work is descriptive. Never increase N after inspecting results.

This calculation remains an explicit launch gate: none of the above numbers is
an assertion of achieved power. A one-percentage-point AER decrease and a
five-percentage-point goodput increase are fixed practical-effect thresholds,
not noninferiority margins or universal deployment requirements.

## Outcomes and estimands

`N` is all scheduled cells, including missing, crashed, timed-out and not-run
cells. `A` is authoritative acceptance of the bound final artifact. Acceptance
must be established from retained receipts; an absent acceptance record is not
evidence of a negative acceptance decision. Distinguish `A=unknown` from an
observed rejection. `X_raw` grades the pre-acceptance proposal and `X_accepted`
grades the exact accepted artifact using a separately versioned grader. Grade
rejected proposals where feasible; do not label them incorrect by rejection.

| Metric | Estimand and denominator |
|---|---|
| Accepted error rate (AER) | Known incorrect accepted / all established acceptances; null at zero acceptances |
| Accepted correctness | Known correct accepted / all established acceptances; conditional, not task success |
| Verified goodput (ASSR) | Known correct accepted / all scheduled cells |
| Acceptance coverage | Established accepted / all scheduled cells |
| Accepted-error burden | Known incorrect accepted / all scheduled cells |
| Raw correctness | Independently correct raw proposals / all scheduled cells, plus grading coverage and bounds |
| False rejection | Rejected and independently correct raw proposals / independently correct raw proposals with known acceptance |
| Fault containment | Injected faulty trials proven contained / all scheduled injected faults, with unknowns separate |
| Cost per useful acceptance | All attempted-call fees plus declared local occupancy / known correct accepted; null at zero |
| Useful throughput | Known correct accepted / trusted elapsed experiment wall hours |

The primary point estimates pool numerator and denominator across the fixed
balanced design. AER is a ratio of pooled counts, never an average of task AERs.
The family bootstrap retains that pooling rule. Report family-stratified counts
and task-class summaries as descriptive views; do not reweight families based on
results. Multiple workers within one scheduled cell never create extra successes.

For R0, the externally captured final proposal is the designated output (`A=1`
when a final artifact exists); no Station integration is implied. The R0 adapter
must define failed/no-proposal cells separately and preserve raw-artifact identity.
R1–R5 acceptance conventions require explicit adapter mapping at launch. Merely
renaming `single/fixed/dynamic` or existing obligation policies is prohibited.

## Missingness, unknowns and errors

UNKNOWN, ERROR, SKIPPED, missing evidence, timeout, and containment failure are
distinct outcomes; none is PASS. A no-demonstrated-success cell contributes zero
to verified goodput's numerator and one to its denominator. This is an operational
outcome, not an imputed semantic wrong answer. Missing usage is null, not free.

With `a` established acceptances, `b` known bad accepted artifacts and `u` accepted
artifacts with unknown grade, report AER identification bounds `[b/a,(b+u)/a]`;
with `u>0`, report no single fully identified AER. With `m` unknown acceptance
statuses, further widen conservatively to `[b/(a+m),(b+u+m)/(a+m)]`; when all
possible acceptances are zero, AER is undefined. Report observed-acceptance bounds
separately so a reconstructed missing row cannot conceal uncertain state. For a
contrast use `[lower_treatment-upper_control, upper_treatment-lower_control]`.
For goodput report the demonstrated fraction and an upper bound assigning all
unresolved potentially successful cells success. Bounds are identification bounds,
not confidence intervals.

Never drop unmatched cells or bootstrap complete pairs only. Materialize the
whole scheduled grid, attach missing status, and resample every arm together.
If acceptance or independent grades required for an AER contrast are missing,
its confirmatory p-value is not estimable and receives `p=1` for Holm accounting.
Report known-grade complete-case analysis only as a labeled sensitivity view.
Corrupt or conflicting artifacts block the numerical report; recovery preserves
original bytes and provenance. No replacement runs. Provider retries retain their
logical cell/attempt identity and all costs. An external interruption is still
reported in the scheduled denominator and terminates confirmatory claims if it
prevents the locked design from being completed.

## Confidence intervals and paired tests

Use 20,000 paired family-cluster bootstrap draws with replacement. Draw `F`
family indices per replicate and carry **all** tasks, repeats, configurations,
unknown markers and outcome/cost fields of each selected family together.
Never bootstrap individual workers or repeats independently. Use SHA-256 of
`protocol_digest + ':' + analysis_id` as the 256-bit seed to Python
`random.Random`; retain Python version, resample-index hash and implementation hash.
Report two-sided 95% percentile intervals with linear interpolation at quantiles
0.025 and 0.975, and paired treatment-minus-control risk differences in percentage
points. Ratio estimands recompute both pooled sums for every draw.

If any draw has a zero ratio denominator, return that ratio CI as unavailable
and report the undefined-draw fraction. Do not silently discard or redraw it.
If the bootstrap distribution is degenerate, show its descriptive quantiles but
mark inferential coverage unavailable. In particular zero observed errors does
not justify `[0,0]` as a certified error-rate bound. Below 30 independent families
all intervals are descriptive; repeated runs cannot repair that limitation.
The paired resampling semantics and percentile method are documented in the
[SciPy bootstrap reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).

For the four primary contrasts, use a paired **whole-family label-swap** test:
swap treatment/control labels for every task/repeat in each selected family,
then recompute the pooled statistic. Enumerate all `2^F` patterns if `F<=20`;
otherwise draw 99,999 uniform independent swap patterns. Two-sided Monte Carlo
`p=(1+count(abs(T*)>=abs(Tobs)))/(B+1)`; exact `p` uses the fraction of all patterns.
Use absolute-statistic tails consistently, including ties. Retain sampled swap
patterns and seed. The test assumes independent families and exchangeability of
the paired outcome vectors under the null of no configuration effect; randomizing
execution order alone does not prove that assumption. Document violations and
withhold confirmatory inference if the assumption is untenable. This is not a
generic weak-null mean test. The [SciPy permutation reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html)
distinguishes paired sample-label swaps from independent permutations and explains
the Monte Carlo add-one convention.

Current unpaired Mann–Whitney/Welch code is not the analysis engine. An independently
reviewed implementation, exact small-family cross-checks, missing-cell and
zero-denominator tests, and synthetic coverage/power checks are launch gates.

## Multiplicity and effect interpretation

One fixed Holm family contains exactly four two-sided hypotheses:

| ID | Contrast | Endpoint |
|---|---|---|
| H01 | R4 minus R0 | AER |
| H02 | R4 minus R0 | Verified goodput |
| H03 | R5 minus R4 | AER |
| H04 | R5 minus R4 | Verified goodput |

Sort p-values by `(p,id)`. Compare the ith ordered value to `0.05/(4-i+1)` and
stop rejecting at the first failure. Report monotone adjusted values
`min(1,max_{j<=i}((4-j+1)*p_j))`. Unavailable contrasts remain in the family at
`p=1`; do not shrink the family. This follows the
[Holm sequential procedure](https://www.jstor.org/stable/4615733).
Ordinary 95% CIs are marginal, not simultaneous and not a replacement for Holm.
Also show 98.75% percentile intervals for these four contrasts, clearly labeled
approximate Bonferroni intervals subject to bootstrap coverage limitations.

Report signed absolute differences; relative risks are secondary and null when
their control denominator is zero. No continuity correction is selected after
seeing data. AER improvement alone supports only a conditional reliability claim;
it cannot establish system superiority if goodput falls. A nonsignificant goodput
drop does not establish noninferiority. Report practical thresholds separately
from p-values and explain tradeoffs without declaring an aggregate winner.

R1/R2/R3 contrasts, task strata, model degradation, heterogeneous routing, tax,
verifier curves, fault and soak analyses are **prespecified descriptive secondary
analyses** under v1. They receive effects and intervals, no confirmatory p-values
or superiority/equivalence claims. Any later confirmatory extension needs its own
pre-results family and independent untouched data; the R0–R5 outcome cannot select
its models, routing, effects or workload.

## Cost, latency, Pareto and negative results

Charge all attempts, including failures, retries, coordinator and semantic-review
calls. Require input/output/cache/reasoning usage when billable, exact price and
currency/effective date, and local occupancy rate scope. Report measured currency
cost separately from token counts and modeled local cost. Unknown upstream usage
or prices make total cost and frontier membership indeterminate, not zero.
Compare per-cell total cost and total-cost/total-useful-acceptance, never average
per-success ratios. Show paired bootstrap differences; use no logs for zero cost.

Report all-cell capped elapsed time to the locked deadline, median and p95, and
deadline-hit/unknown-timing counts. Completed-only latency is secondary with its
denominator. Missing elapsed time remains unknown; do not substitute zero or a
deadline without evidence. Soak templates require at-risk/censoring records and
distinguish planned termination from unplanned failure.

The descriptive Pareto frontier minimizes AER and total cost while maximizing
verified goodput; show latency as a second panel. A point dominates another only
if no worse on every complete dimension and strictly better on at least one.
Keep equal points; mark incomplete and zero-acceptance arms indeterminate. Show
acceptance coverage and missingness alongside the frontier. Paired bootstrap
dominance frequency is descriptive stability, not a probability of truth or
a significance test. Do not select weights or omit a dimension after results.

Release the locked schedule, all failed/aborted outcomes, missingness, effect and
CI tables, all four Holm entries, model/route accounting, discrepancies and
reproduction hashes whether findings favor Residual, favor a baseline, are mixed,
or are inconclusive. Retain the original analysis and report exploratory
amendments separately. A negative result does not permit easier tasks, extra
retries, a different verifier or a relabeled model class. Public fixtures and
synthetic power/instrumentation data never enter confirmatory denominators.

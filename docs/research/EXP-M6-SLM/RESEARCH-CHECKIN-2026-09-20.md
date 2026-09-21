# AX-21 / EXP-M6-SLM Research Check-in — 2026-09-20

**Purpose:** Append-only research-maintenance record comparing newly available repository evidence against the AX-21 pre-release baseline. This record does not mutate the AX-21 baseline and does not authorize training, release, or production claims.

**Accepted main at check-in:** `2f9dda3882f39c28a1c766859b1bf9579eea7911` (unchanged from the pre-release baseline period).

## Executive disposition

Material research progress occurred, but the most important movement is **measurement-discipline improvement rather than new autonomy performance evidence**.

The repository now contains a substantially more mature SLM research apparatus: preregistered protocol, frozen-intent evaluation metrics, prior-art review, corpus conversion work, contamination tooling, training/inference scaffolds, deterministic verifiers, evaluation tooling, a candidate Control Bench, native AX-21 observation export, and economic telemetry. However:

- SLM-00 remains **NOT FROZEN**.
- No training result or candidate-model performance result is accepted.
- The AX-21 organic dogfood narrative remains unsuitable as event-level model corpus evidence.
- The P5 post-#349 operator-friction replay has not occurred.
- No first defensible release tag exists, so AX-21-BASELINE-R0 is not yet eligible for final freeze.

## New observed findings

### RF-2026-09-20-01 — AX-21 narrative evidence is a historical baseline, not a corpus

SLM-00 preflight found that the existing organic AX-21 dogfood log is narrative-only: event-level leases, receipts, usage records, and underlying P1 evidence bundles are not present in the reviewed repository state. The preflight therefore classified the narrative source as **not corpus-eligible** and reported the operator-effort aggregate as unverifiable at event level.

This **refines rather than invalidates** the AX-21 baseline:

- AX-21 remains useful as a contemporaneous historical/operator baseline.
- Its narrative observations must not be silently promoted into model-training or benchmark records.
- Paper-grade quantitative claims derived from AX-21 require retained event bundles, Station evidence, or prospectively schema-native observations.

**Baseline delta:** the earlier plan to freeze the AX-21 run as a comparison dataset must distinguish `historical baseline record` from `corpus-eligible observation dataset`.

### RF-2026-09-20-02 — Strict legacy conversion exposed a universal timestamp gap

SLM preflight reported **0% strict schema conversion** for sampled legacy structured sources because the observation schema required a non-null wall-clock timestamp that the sources did not contain.

The proposed `SCHEMA-ERRATUM-001` changes timestamp to nullable while keeping the key required and forbidding fabricated sentinel timestamps. Independent infrastructure qualification judged this the least-inventive correction and found it sound for legacy conversion.

**Interpretation:** schema design successfully forced an honesty decision instead of encouraging synthetic precision. The result is a research-governance improvement, not a performance result.

### RF-2026-09-20-03 — Contamination-isolation claim was falsified

Independent qualification falsified the Lane B statement that content-identical VQ records could never straddle a split.

Observed in VQ part2:

- adequate/degraded files share case IDs `bad0`–`bad29`;
- the two files map to different contamination groups because the group key includes different blob SHAs;
- **20/30 paired records are content-identical** despite different group IDs;
- current near-duplicate detection is warning-only;
- the contamination linter's lineage check is ineffective on the converted corpus because mission/incident IDs are null.

This is a genuine falsification and should be retained prominently.

**Required correction before freeze:** contamination-group purity must be mechanically enforced at split-authoring/compile time, and VQ grouping/deduplication must be resolved before any split manifest is frozen.

### RF-2026-09-20-04 — Data pipeline and training scaffold are currently incompatible

Independent qualification found that the dataset compiler emits `uint32-le` token streams while the training scaffold reads `uint16`.

Without a guard, the scaffold can silently interpret one uint32 token as two uint16 tokens.

A second split-contract mismatch was found:

- protocol expects train/validation/test semantics;
- compiler currently emits train/holdout;
- scaffold expects `train.bin`/`val.bin` and periodically evaluates on `val.bin`;
- mapping holdout to val would create a holdout-touch risk during training.

**Disposition:** training must remain blocked until dtype and split semantics are made consistent and fail-closed.

### RF-2026-09-20-05 — Frozen metrics are not computable from the legacy corpus

Infrastructure qualification confirmed that the current converted corpus lacks enough realized cost, energy, escalation, and non-assumed authority data to compute several frozen metrics honestly:

- VSMS/$ and VSMS/W are unavailable because inference cost / energy are absent;
- FNER/UER have empty escalation numerators/denominators;
- AVR lacks adequate observed authority-violation coverage.

This is not a reason to impute values. It is evidence that the measurement apparatus must collect these fields prospectively.

### RF-2026-09-20-06 — Native observation export directly addresses the AX-21 evidence gap

PR #383 introduces schema-native observations at `Station.finish`, `Station.review`, and `Station.integrate`, with wall-clock timestamps, mission/task lineage, artifact/code provenance, verification/cost/authority blocks, redaction, append-only digest chaining, and explicit collection-only quarantine.

Local branch evidence reports schema-valid chained records and integrity/tamper tests.

**Important limitation:** this remains an open draft and does not retroactively repair the pre-existing AX-21 narrative evidence. It improves future collection only.

**Scope-integrity finding:** the PR diff also contains unrelated Ollama runtime behavior changes inside `service.py` beyond the observation-export scope described in the PR summary. The observation lane should be rebased/split before its results are treated as clean evidence for the instrumentation intervention.

### RF-2026-09-20-07 — Economic telemetry begins to fill the missing-metrics surface

PR #384 adds candidate instrumentation for tokens, realized inference cost, measurable energy, routing alternatives, escalation outcomes, operator-active seconds, and explicit estimated-vs-observed separation.

This directly targets the missing fields identified in RF-2026-09-20-05.

Current limitations remain material:

- Station/worker construction is not yet wired;
- AVR remains external to this telemetry lane;
- the price table is placeholder data and must be replaced before results are computed;
- the PR is draft/unaccepted.

Therefore the measurement gap is **architecturally addressed but not yet experimentally closed**.

### RF-2026-09-20-08 — Novelty claim must be narrower than the architecture

The adversarial prior-art lane reports novelty status **PARTIAL**.

Its strongest conclusion is that deterministic control-plane architecture and the broad thesis that scaffolding can substitute for model scale have substantial precedent. The more defensible research residue is the preregistered measurement of a **capacity × harness-machinery trade-off curve at sub-1B scale under deterministic verification**, rather than a claim that deterministic control planes or SLM-based agents are themselves novel.

**Paper implication:** future abstracts/intros should foreground the controlled ablation and measured capacity shift, not architecture novelty.

## New falsified or weakened hypotheses

1. **Falsified:** "content-identical VQ records can never straddle a split" under the current contamination-group scheme.
2. **Weakened:** "existing AX-21 retained evidence can directly seed the SLM observation corpus." The organic narrative cannot; only structured lanes and prospectively retained event evidence qualify.
3. **Weakened:** "current research tooling enforces contamination safety." Split-manifest completeness is enforced, but contamination-group purity is not yet enforced end to end.
4. **Weakened:** "training infrastructure is ready once a corpus freezes." Current token dtype and train/validation/holdout semantics are incompatible.
5. **Weakened:** broad novelty framing around deterministic control planes / scaffolding-substitutes-for-scale. Prior-art lane recommends a narrower experimental claim.

## New operator / intervention observations

No new trustworthy post-baseline operator-friction measurement is available from Station itself.

The frozen P5 before-condition therefore remains authoritative for comparison:

- Station cannot directly answer the global swarm-state question;
- 11 cold agent queries + synthesis were required;
- 15+ reports/session were externally synthesized.

#349 remains an unmerged intervention, so the before/after P5 experiment has **not** occurred.

## Candidate RES-UP / ImprovementSpec items

These are candidate findings only; assign registry IDs only through the normal RES-UP process.

### Candidate A — Contamination split-purity gate

Add a fail-closed invariant: one `contamination_group` may map to exactly one frozen split. Enforce at split-manifest validation and dataset compile/CI, not only in narrative policy.

Acceptance test: intentionally split one contamination group across train/validation/test; all compilation/CI paths must reject before artifacts are produced.

### Candidate B — Content-lineage grouping for VQ / duplicate-derived corpora

Replace file-blob-derived grouping where it can separate semantically identical records. Bind related records by stable case/source lineage plus canonical content/semantic identity, with a preregistered dedupe policy.

### Candidate C — Dataset/scaffold representation contract

Freeze one token dtype and one split vocabulary across compiler, manifest schema, training loader, and evaluation code. Reject incompatible manifests rather than relying on operator naming conventions.

### Candidate D — Evidence-native AX-21 collection

Land a clean, scope-isolated native observation exporter and retain the generated evidence bundles prospectively. Preserve explicit collection-only/quarantine state until contamination groups and splits are frozen.

### Candidate E — Research metric completeness preflight

Before any model evaluation run, mechanically assert which frozen metrics are computable from the available instrumentation. Missing denominators/fields must yield `NOT_MEASURABLE`, not zero or inferred values.

### Candidate F — Research-PR scope-integrity check

For scientific instrumentation PRs, compare declared scope against changed behavioral surfaces. Unexpected runtime changes should force split/rebase or an explicit confound declaration before qualification evidence is accepted.

## Current research-state summary

### Established apparatus progress

Open research lanes now cover:

- preregistration and observation schema (#365);
- evaluation protocol (#366);
- baseline manifest (#367);
- adversarial prior art (#368);
- corpus preflight (#369);
- quality/replay tooling (#370);
- dataset/tokenizer/research-CI tooling (#371);
- training scaffold/configs (#372);
- corpus conversion + schema erratum (#374);
- evaluation tooling/results store (#376);
- independent infrastructure qualification (#377);
- advisory StationLM provider (#378);
- category-specific deterministic verifiers (#379);
- Control Bench v0 generator/seeds (#380);
- inference/export runtime (#381);
- native AX-21 observation export (#383);
- economic telemetry (#384);
- shared evaluation runner/statistics (#385).

### Not established

The following claims remain unsupported at this check-in:

- SLM-00 frozen;
- training authorized;
- Residual-Nano or StationLM capability demonstrated;
- post-#349 operator-friction improvement demonstrated;
- autonomous recursive-development cycle closed;
- first defensible RESIDUAL release tagged;
- AX-21-BASELINE-R0 final freeze completed;
- general security of RESIDUAL established.

## Required next evidence before the next major research claim

1. Mechanically close contamination split-purity and VQ dedupe/grouping gaps.
2. Resolve uint32/uint16 and train/validation/holdout contract mismatches.
3. Ratify/freeze the legacy timestamp erratum or exclude affected legacy records.
4. Separate/rebase PR #383 so observation-export qualification is not confounded by unrelated runtime changes.
5. Wire and qualify prospective native observation + telemetry collection.
6. Produce event-level P1/AX-21 evidence bundles with provenance sufficient for paper claims.
7. Freeze exact benchmark, split, baseline-model/runtime/prompt pins.
8. Cross-validate Control Bench items against deterministic verifiers and the evaluation runner.
9. Keep training disabled until the full SLM-00 freeze gate closes.
10. Preserve the P5 before-condition unchanged and run the identical global-state question only after #349 is accepted and deployed.

## Paper-facing conclusion

The strongest new research result in this interval is **not improved agent performance**. It is successful adversarial pressure on the research apparatus itself:

- a corpus-eligibility assumption was rejected;
- a contamination-isolation claim was falsified;
- two silent data/training contract mismatches were found before training;
- metric incompleteness was exposed before results could be overstated;
- novelty framing was narrowed before publication;
- instrumentation work was initiated specifically to collect the missing evidence prospectively.

That pattern supports a defensible methodological claim: RESIDUAL's evidence-governed process is beginning to falsify its own assumptions before model training and paper claims are allowed to proceed.

It does **not** yet establish that the future SLM experiment will succeed.

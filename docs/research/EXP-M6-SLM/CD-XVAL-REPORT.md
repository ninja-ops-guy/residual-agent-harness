# C→D Cross-Validation Report — Control Bench v0 vs Verifier Suite

**Lane:** SLM-00 C→D cross-validation (adversarial benchmark defect hunt)
**Inputs:** Lane C `slm00/control-bench` (PR #380, ref 0cf2e18) · Lane D `slm00/verifiers` (PR #379, ref cd650c0) · tooling `slm-infra/quality-tooling` (ref bba063a)
**Method:** files pulled from all three branches, reconstructed locally, executed with the actual code (no inspection-only claims).

## Verdict: **DEFECTS-FOUND (return to Lane C / Lane D coordination) — BLOCKING**

The benchmark and the verifier suite do not share an interface. **0 of 1,000 items can be verified.** This is not a marginal defect set; the two lanes were built against different contracts for the same category names.

## 1. Manifest digest check — PASS

`generate_bench.py` (seed 20260920, seed/ dir at branch ref) regenerated `control-bench-v0.jsonl` byte-identically:
- emitted bytes: 1,288,538; items: 1,000
- sha256 = `7aee3d73308cc7447838f8c590a82f044756112c89fa101ac3075659129e3b18` → **MATCHES** `control-bench-v0-manifest.json`.

## 2. Interface conformance — 0/1000 resolve (BLOCKING)

Three stacked incompatibilities, each independently fatal:

| # | Defect | Class | Scope | Evidence |
|---|--------|-------|-------|----------|
| X1 | `verifier_ref` namespace mismatch. Bench items carry path-style refs (`research/slm/bench/verifiers/verify_worker_routing.py`); Lane D `VERIFIER_REGISTRY` keys are IDs (`slm00.verifier.worker_routing`). Dispatcher `verifiers.verify()` returns `BENCHMARK_DEFECT:UNKNOWN_VERIFIER_REF` for every item. | BLOCKING | 1000/1000 | run of `verifiers.verify(item, item.expected_output)` over all items |
| X2 | `category` naming mismatch. Bench uses hyphenated (`worker-routing`, `budget-decision`); verifiers hard-check underscore names (`worker_routing`, `budget_decisions` — note also singular/plural). All items → `BENCHMARK_DEFECT:CATEGORY_MISMATCH`. | BLOCKING | 1000/1000 | rerun with verifier dispatch by category |
| X3 | **Item schema divergence.** Even after normalizing X1+X2, every item is rejected because Lane C `input_state`/`expected_output` schemas do not match Lane D category contracts. Example: Lane C `worker-routing` items carry `candidates[{topology,predicted_utility,predicted_tax}]` + `expected_output{selected_topology,selection_reason}`; Lane D `WorkerRoutingVerifier` requires `task.required_capabilities`, `workers[]`, and `expected_output{action,allowed_routes,selected_route}`. These are *different tasks* under the same category name. | BLOCKING | 1000/1000 | per-category reason codes below |

Post-normalization reason codes (100% BENCHMARK_DEFECT):

| category | items | reason_code |
|---|---|---|
| worker-routing | 200 | DEFECT_MISSING_WORKERS |
| contract-compilation | 150 | DEFECT_MISSING_SPEC |
| evidence-sufficiency | 150 | DEFECT_MISSING_REQUIREMENTS |
| retry-escalate-abort | 100 | DEFECT_MISSING_POLICY |
| budget-decision | 100 | DEFECT_MISSING_BUDGET |
| failure-classification | 100 | DEFECT_BAD_TAXONOMY |
| adversarial-malformed | 100 | DEFECT_MISSING_ATTACK |
| stale-state-authority | 100 | DEFECT_BAD_GENERATION |

Reproduction (any item, e.g. RCB0-WR-0001): `verifiers.verify(item, item["expected_output"])` → `BENCHMARK_DEFECT:UNKNOWN_VERIFIER_REF`.

Control: Lane D's suite itself is functional — an item constructed to its own documented worker_routing contract returns `PASS:OK` for the correct candidate and `FAIL:CAPABILITY_MISMATCH` for an incorrect one. The defect is the C↔D divergence, not a broken suite.

## 3. Positive battery (expected_output → PASS)

**0 / 1000 PASS.** All 1,000 declared expected outputs are rejected (BENCHMARK_DEFECT under all three dispatch strategies above). Every item is therefore a benchmark defect per the mission definition. Item IDs: the entire corpus (RCB0-WR-0001…0200, RCB0-CC-0001…0150, RCB0-ES-0001…0150, RCB0-REA/BD/FC/AM/SA ranges) — enumerated in the run, grouped by reason code in §2.

## 4. Negative battery

Perturbed expected_output (first field mutated) on all 1,000 items: 1000× BENCHMARK_DEFECT (same contract reason codes), **never FAIL**. Per the verifier contract ("malformed/incorrect candidate → FAIL, item inconsistency → BENCHMARK_DEFECT"), a bad candidate on a good item must FAIL; here item rejection precedes candidate evaluation, so the negative battery yields **no evidence of verifier discrimination**. Blocked by X1–X3; not counted as separate oracle defects. No incorrect output PASSed (0 oracle false-accepts observed — trivially, since nothing PASSes).

## 5. Mutation testing (`bench_mutation.py`, all 8 verifiers, 50 items/category, 5 mutation classes)

| category | expected_output | authority | budget | hash | evidence_refs | verifier_errors |
|---|---|---|---|---|---|---|
| worker-routing | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| contract-compilation | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| evidence-sufficiency | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| retry-escalate-abort | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| budget-decision | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| failure-classification | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| adversarial-malformed | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| stale-state-authority | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |

(survival_rate per class; 50 mutants each.) **Degenerate result**: 0% survival but every "rejection" is a contract-level BENCHMARK_DEFECT that also fires on unmutated items. Mutation testing must be re-run after X1–X3 are fixed; current numbers carry no robustness signal.

## 6. Duplicates & contamination hygiene

- **Exact duplicates: 38 duplicate groups covering 101 items** (identical category+input_state+expected_output under distinct item_ids/digests). Per category: retry-escalate-abort 50 items, adversarial-malformed 31, stale-state-authority 10, contract-compilation 10. Examples: {RCB0-CC-0027, RCB0-CC-0067}; {RCB0-REA-0009, RCB0-REA-0061, RCB0-REA-0081}. Class: **MATERIAL** (corpus inflates effective sample size; dups distort per-category difficulty stats).
- **36 of 38 exact-dup groups straddle ≥2 contamination groups.** Since train/val/test split is by group, identical items can land in both train and test → leakage. Class: **MATERIAL (leakage-critical)**.
- Near-duplicates (word 5-shingle Jaccard ≥ 0.7 on canonical input_state): **1,034 pairs**, of which **857 straddle different contamination groups** (largely synthetic template batches `CG-CC-SYN-surface-template-bXX` vs `bYY`). Class: **MATERIAL** — group assignment does not respect near-dup lineage.
- Tooling note: `corpus_linter.py` targets the `slm-observation-v0` schema (state/proposed_decision/outcome/…), not bench item schema; run as-is it fail-closes with schema ERRORs on all 1,000 items. Its dup/contamination logic was re-implemented bench-natively above. Class: MINOR (tooling scope mismatch).

## 7. Field-shape conformance

Required item fields per Lane D base (`item_id, category, input_state, expected_output, verifier_ref`) are all present in all 1,000 items — minimum shape OK. Category-specific `input_state` shapes do not match any verifier's documented contract (X3). `budget-decision` vs `budget_decisions` singular/plural mismatch noted in X2.

## Defect summary

| class | count | defects |
|---|---|---|
| BLOCKING | 3 | X1 verifier_ref namespace, X2 category naming, X3 input_state/expected_output schema divergence (all categories, all items) |
| MATERIAL | 3 | 38 exact-dup groups (101 items); 36/38 exact-dup groups cross contamination groups; 857 cross-group near-dup pairs |
| MINOR | 1 | corpus_linter schema mismatch with bench item format |

## Disposition: **DEFECTS-FOUND — return to Lane C (with Lane D)**

Lane C owns item fixes. X1/X2 are mechanical (suggested patches, NOT applied):
- Emit `verifier_ref` as Lane D registry IDs (`slm00.verifier.<category>`), or Lane D adds path→ID aliases.
- Normalize category strings to Lane D's names (`worker_routing`, …, `budget_decisions`).
X3 is **not mechanical**: the two lanes implemented different tasks per category. Requires spec arbitration against `docs/research/EXP-M6-SLM/CONTROL-BENCH-V0.md` (which neither artifact fully matches on inspection) before regeneration. Duplicate de-dup and contamination-group reassignment should land in the same Lane C respin.

*Generated by the C→D cross-validation lane; no benchmark items or verifiers were modified.*

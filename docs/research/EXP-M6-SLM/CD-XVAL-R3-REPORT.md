# CD-XVAL-R3 — Cross-Validation Report: SLM-00 Freeze Candidate

**Issue:** CD-XVAL-R3 (remediates G2-B2 BLOCKING: CD-XVAL-R2 @ `slm00/cd-xval-r2` c386b4e8 was stale — quoted digest `0a70f06c…`, superseded head `5f55f93b`, 24-line sample; it did not verify the frozen artifacts).
**Author:** Lane C/D independent cross-validation (verification-only; no artifact modified).
**Date of execution:** 2026-09-21 (UTC).
**Method:** all artifacts fetched anonymously by content-addressed refs and executed locally (Python 3.12.12, stdlib only). Every number below is from execution.

## 1. Refs examined (exact observed head SHAs)

| Ref | Observed head SHA | Expected pin | Match |
| --- | --- | --- | --- |
| `slm00/control-bench` (Lane C bench) | `dffc5ede9368e112151b9fd4fbeb0887e746d458` | `dffc5ede` | YES |
| `slm00/verifiers` (Lane D verifiers) | `cd650c096ffa203a846cffe4379ebcc9a4f0797f` | `cd650c09` | YES |
| `slm00/corpus` (Lane A/B corpus, supporting check 7) | `1d37436008baa3bb3a195f9fbe7965e52b4661a2` | — (see F4) | — |
| `research/exp-m6-slm-00` (base) | `3661319eee03963943a6df88db61243254134983` | — | — |

Files examined @ `dffc5ede`: `research/slm/bench/generate_bench.py` (blob 66c4ddbb), `control-bench-v0-manifest.json` (986b2909), `sample/control-bench-v0-sample.jsonl` (3cf0126a, 12 lines), 8 seed files under `seed/`, `docs/research/EXP-M6-SLM/CONTROL-BENCH-V0-DESIGN.md`.
Files examined @ `cd650c09`: `research/slm/verifiers/{__init__.py, base.py, worker_routing.py, contract_compilation.py, evidence_sufficiency.py, retry_escalate_abort.py, budget_decisions.py, failure_classification.py, adversarial_malformed.py, stale_state_authority.py, MANIFEST.json, AMBIGUITY.md}` + 10 test files (70 tests).
Files examined @ `1d37436`: `research/slm/corpus/convert.py`, `corpus/sample/converted-sample.jsonl`, and the 10 evidence sources pinned in `SOURCE_SHAS` (all 10 git-blob SHA1s verified equal to the pins in `convert.py`).

## 2. Checks

### Check 1 — Regeneration, counts, split, digest, manifest — PASS
Method: ran `generate_bench.py` (rng_seed 20260920) against the 8 shipped seed files in a clean tree.
- Emitted items: **1000** (expected 1000).
- Category split (Counter over regenerated items): worker_routing **200**, contract_compilation **150**, evidence_sufficiency **150**, retry_escalate_abort **100**, budget_decisions **100**, failure_classification **100**, adversarial_malformed **100**, stale_state_authority **100** — exact match to required 200/150/150/100/100/100/100/100.
- `sha256(items.jsonl)` = `15937ec20ec314d0dd80c374a074893c95b43b00b69ae114330615d993c56cbd` — **byte-exact match** to the frozen pin.
- Regenerated manifest **byte-identical** to shipped `control-bench-v0-manifest.json` (6938 bytes).
- Generator's internal assertions (unique ids, unique digests, no dup within contamination group) all held during the run.

### Check 2 — Shipped sample vs regenerated rows — PASS
Method: byte comparison of each of the 12 lines of `sample/control-bench-v0-sample.jsonl` against the regenerated row with the same `item_id`.
- **12/12 lines byte-identical**, 0 mismatches. (R2's 24-line sample is superseded; current sample is 12 lines.)

### Check 3 — verifier_ref resolution & category naming — PASS
Method: loaded Lane D `VERIFIER_REGISTRY` from `research/slm/verifiers/__init__.py` and cross-checked `MANIFEST.json`.
- Registry IDs == MANIFEST IDs == the 8 expected `slm00.verifier.*` IDs.
- All **1000** items' `verifier_ref` resolve to a registered ID (0 unresolved).
- Category naming consistent: 0 items where `item.category` != registry category of its `verifier_ref`. Bench uses Lane D snake_case ids verbatim (incl. plural `budget_decisions`).
- Lane D's own suite: **70/70 tests pass** (unittest discovery, 0 failures, 0 errors).

### Check 4 — Positive battery — PASS (with construction note, see F1)
Method (a), literal: `verify(item, item["expected_output"])` for all 1000 items.
- Result: **873 PASS / 127 FAIL / 0 BENCHMARK_DEFECT**. The 127 FAILs are `worker_routing`×59 (`MISSING_ROUTE`) and `evidence_sufficiency`×68 (`MISSING_VERIFIER_OUTPUTS`) — both are candidate-shape issues, not item-content errors (F1).
Method (b), contract-shaped gold candidate per Lane D's documented candidate contracts (WR: `{action, route=selected_route or any legal route when selected_route is null}`; ES: `expected_output + verifier_outputs = input_state.required_verifier_outputs` when present; all other categories: `expected_output` as-is):
- Result: **1000/1000 PASS, 0 FAIL, 0 BENCHMARK_DEFECT.**

### Check 5 — Negative battery — PASS
Method: 4 intentionally-wrong/malformed candidate constructions per item (category-specific corruption + empty object + junk-type object), run through the dispatcher.
- Total candidates: **4000** (WR 800, CC 600, ES 600, REA 400, BD 400, FC 400, AM 400, SA 400).
- **PASS leaks: 0. BENCHMARK_DEFECT: 0. Exceptions: 0.** All 4000 returned FAIL.
- Constructions: WR illegal-route/wrong-action; CC broken-contract (deleted required field)/non-object contract; ES flipped-sufficiency/wrong-missing-set; REA wrong-action/wrong-reason-code; BD wrong-decision/bogus-route; FC wrong-label/out-of-taxonomy label; AM reject=false/wrong-reason; SA flipped-legal/wrong-violation; plus `{}` and junk-typed candidates for every item.

### Check 6 — Duplicates — exact: CLEAN; near-dup: phenomenon CONFIRMED, G2 exact counts NOT reproduced (F2)
Method: exact dup = generator's canonical content key (category+input_state+expected_output+allowed_alternatives+contamination_group), plus digest and item_id uniqueness. Near-dup = items clustered by content after masking seq-derived identifiers (each item's own sequence number, zero-padded and raw) in all string values of input_state/expected_output/allowed_alternatives; clusters spanning >1 contamination group are cross-group near-dups.
- Exact duplicates: **0** (content-key, digest, and item_id all unique across 1000; also 0 when contamination_group excluded).
- Cross-group near-dup clusters (seq-masking normalization): **9 clusters / 22 items**:
  - failure_classification: **7 clusters / 18 items**, spanning `bench-syn:fc:taxonomy:b00…b04` (sizes 5,4,3,2,2,2,2). Mechanism confirmed: `label = FC_TAXONOMY[seq % 10]` (period 10) vs bucketing `seq // 25`, so the same label+observation template recurs across buckets.
  - evidence_sufficiency: **1 cross-group cluster of 2 items** (RCB0-ES-0073 / RCB0-ES-0142, `…:b02` vs `…:b05`). A second ES pair (RCB0-ES-0129 / RCB0-ES-0143) is near-dup **within** one group (`…:b05`) — split-safe.
  - adversarial_malformed: **1 cross-group cluster of 2 items** (RCB0-AM-0056 / RCB0-AM-0096, `bench-syn:am:injection:b02` vs `b03`) — not in G2's note.
- G2 reported "5 FC clusters / 15 items spanning b00…b04" and "1 ES cluster of 2 items". Under my normalization I measure 7 FC clusters / 18 items; the ES cross-group cluster is confirmed exactly. G2's exact FC count is **not reproduced**; cluster counts are normalization-sensitive (masking rng-sampled FC aliases merges further to 13 FC clusters / 88 items). The underlying defect class (period-10 label cycling vs seq//25 bucketing) is confirmed. Known, non-blocking; to be handled at freeze-time split authoring by content-normalized clustering.

### Check 7 — Contamination groups — 86 groups CONFIRMED; shared keys measured 12 (superset of expected 7, see F3)
Method: distinct `contamination_group` over the 1000 regenerated bench items; corpus side obtained by **executing** `research/slm/corpus/convert.py` @ `slm00/corpus` head `1d37436` against its 10 pinned evidence sources (blob SHA1s verified), producing 387 corpus records / 152 corpus groups; intersected the two group sets.
- Distinct bench contamination groups: **86** (lineage-atomic; generator asserts dup-free within group; verified 0 within-group exact dups).
- Non-`bench-syn:` bench groups: 12 — **all 12 also present in the executed corpus** (shared bench↔corpus keys = **12**, not 7):
  - obs006-fixture-v1 (bench 11 / corpus 13)
  - otx:lookup-atomic (2 / 4)
  - vq:case:good0 (1 / 2)
  - dsm004:faults/lost (1 / 6)
  - dsm004:recovery/replay_determinism (1 / 7)
  - runtime005:stale_telemetry_returns_unknown (3 / 1)
  - runtime005:provider_native_authority_never_overrides_residual (1 / 1)
  - **plus 5 more**: dsm004:faults/duplicate (1 / 6), dsm004:recovery/crash_between_write_and_ack (2 / 2), dsm004:recovery/restart_mid_stream (2 / 4), runtime005:cancellation_budget_exceeded_fails_closed (3 / 1), runtime005:capability_probe_fail_closed_and_local_preferred (1 / 1).
- All 7 expected keys are present and confirmed shared. The extra 5 are exactly the remaining rows of the frozen group-mapping table in CONTROL-BENCH-V0-DESIGN.md (12 legacy→corpus-scheme rows), so the measured 12 is internally consistent; the issue's "expected 7" undercounts. All 12 shared groups contain authentic (non-synthetic) bench items.

## 3. Findings

| ID | Severity | Finding |
| --- | --- | --- |
| F1 | LOW (documented contract asymmetry) | `expected_output` is not itself a valid candidate for WR (key is `selected_route`, candidate contract wants `route`; 32 of 1000 items use `selected_route: null` = "any legal route", a documented relaxation) and for ES items with `required_verifier_outputs` (candidate must echo them; 68 items). Literal battery: 873 PASS/127 FAIL/0 DEFECT; contract-shaped gold: 1000/1000 PASS. Item contents are self-consistent (0 BENCHMARK_DEFECT in both batteries). |
| F2 | LOW (known, non-blocking) | Cross-group near-duplicates confirmed by execution: 9 clusters / 22 items (FC 7/18 across b00–b04; ES 1 cross-group pair; AM 1 pair not previously itemized). G2's exact FC counts (5 clusters/15 items) not reproduced; mechanism confirmed; counts normalization-sensitive. Handle at freeze-time split authoring via content-normalized clustering. |
| F3 | LOW (expectation mismatch) | Measured shared bench↔corpus keys = **12** (execution of corpus converter @ 1d37436), a strict superset of the expected 7. Consistent with the 12-row frozen mapping table in the design doc. |
| F4 | INFO | CONTROL-BENCH-V0-DESIGN.md references corpus converter "@ slm00/corpus head 1c127f9b"; observed corpus head is `1d37436008baa3bb3a195f9fbe7965e52b4661a2`. Stale doc reference only; the executed converter behaves as documented. |

## 4. Disposition

**CLEAN-WITH-FINDINGS.** The frozen artifacts verify exactly: regeneration reproduces 1,000 items, the required 200/150/150/100/100/100/100/100 split, and the pinned digest `15937ec2…56cbd`; the shipped manifest and 12-line sample are byte-identical to regenerated output; all verifier_refs resolve and category naming matches Lane D; the positive battery passes 1000/1000 (contract-shaped gold; 873/1000 literal — F1) with 0 BENCHMARK_DEFECT; the negative battery shows 0 PASS leaks in 4000 adversarial candidates; 0 exact duplicates; 86 lineage-atomic contamination groups confirmed. Findings F1–F4 are LOW/INFO and non-blocking; F2's near-dup clusters must be honored at freeze-time split authoring (group-atomic + content-normalized clustering), as already planned.

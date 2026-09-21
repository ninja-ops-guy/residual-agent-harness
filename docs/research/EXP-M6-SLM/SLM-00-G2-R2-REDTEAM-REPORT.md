# SLM-00-G2-R2-REDTEAM-REPORT.md

**Reviewer:** G2 round 2 (independent-context adversarial red team, execution-based)
**Date of execution:** 2026-09-21 (environment date)
**Mode:** verification-only; no repo writes. All numbers below are from my own execution against a fresh anonymous clone.

## 1. Scope

Re-review of the SLM-00 freeze candidate after claimed remediation of G2 round-1 blocking findings G2-B1 (B1 random-floor gold-label leak) and G2-B2 (stale CD-XVAL-R2 evidence), plus re-verification of Lane G's 12-check re-qualification and an adversarial probe of the remediation for new defects.

## 2. Artifacts examined (observed SHAs)

All observed branch heads exactly match the manifest pins:

| Branch | Observed head | Matches manifest pin |
|---|---|---|
| slm00/lane-g | `2076f4556814d26bbb703e7fb41a3cbf4a697d53` | YES (PR #392 head per tasking) |
| slm-infra/eval-runner | `28de46f90aa1ce6c352fa08898425de663126a9d` | YES |
| slm00/cd-xval-r3 | `5cb36d2cb8c5867d50c726655e9834f3261ac625` | YES |
| slm00/control-bench | `dffc5ede9368e112151b9fd4fbeb0887e746d458` | YES |
| slm00/verifiers | `cd650c096ffa203a846cffe4379ebcc9a4f0797f` | YES |
| slm00/baselines | `852e4906fa0a2013c3f39534fd8f4bd912314d25` | YES |
| slm00/corpus | `1d37436008baa3bb3a195f9fbe7965e52b4661a2` | YES |
| slm00/schema-erratum-ratify | `34ee4a32…cacb` | YES |
| base `research/exp-m6-slm-00` | `3661319eee03963943a6df88db61243254134983` | YES |
| All other pinned branches (preflight, prior-art, eval-protocol, lane-x, cd-xval, cd-xval-r2, quality-tooling, data-toolchain) | — | YES (all 16 pinned commits are current branch heads) |

## 3. Verification performed (all by execution)

1. **Manifest hashing (check 12):** extracted all 59 `artifacts[]` entries; `git show <pinned_commit>:<path>` → sha256 recompute. **59/59 match. Zero mismatches.** Additionally verified every pinned commit equals its branch's current head (no stale pins).
2. **Bench regeneration (checks 1–2):** ran `generate_bench.py` @ dffc5ede in a clean tree → exactly 1000 items; `sha256(items.jsonl) = 15937ec20ec314d0dd80c374a074893c95b43b00b69ae114330615d993c56cbd` — **byte-exact match to the frozen pin**; regenerated manifest **byte-identical** to shipped; 12/12 shipped sample lines byte-equal to regenerated rows.
3. **Test suites:** verifier pytest @ cd650c09: **70/70 PASS**. Runner pytest @ 28de46f9 (incl. `test_g2b1_regression.py`): **34/34 PASS**.
4. **B1 random floor end-to-end** on regenerated bench (CLI, seed 20260920): **VMSR = 0.041 aggregate; per-category max 0.23 stale_state_authority, 0.09 worker_routing, 0.0 on the other six** — exact match to the receipt/manifest claim (leak-era value was 0.873).
5. **B3 oracle ceiling end-to-end:** **VMSR = 1.0 on all 8 categories, 0 BENCHMARK_DEFECT.**
6. **Adversarial whitelist probes** (custom malicious backends driven through the real `run_evaluation`):
   - Gold read `item["expected_output"]` from a non-oracle backend → **KeyError raised** (fail-loud; run aborts).
   - Nested-mutation attack (backend clears/mutates `input_state` subtrees, injects `expected_output` into its payload) → frozen items **byte-unchanged** after run; evaluation unaffected (fresh deep copy per call confirmed).
   - Silent smuggle (`item.get("expected_output")`) → returns None (key absent).
   - Payload is a plain deep-copied dict of JSON values → no `__class__`/descriptor/descriptor-protocol surface exists to exploit.
7. **Bench-side gold smuggling audit:** `allowed_alternatives` is present on all 1000 items but **empty on all 1000** — the round-1 degenerate choice-set path is gone entirely. Candidate projection of `expected_output` appears in `allowed_alternatives` on **0/1000** items. Recursive key scan of `input_state`: no `expected*`/`gold`/`label`/`answer` keys; nested `digest` keys (391) are ES artifact-content digests, not item digests (benign); no item's serialized gold appears inside `input_state`.
8. **R3 reproduction:** literal positive battery `verify(item, expected_output)` = **873 PASS / 127 FAIL / 0 DEFECT** (WR×59 MISSING_ROUTE + ES×68 MISSING_VERIFIER_OUTPUTS — exact match to R3 F1); contract-shaped battery = B3 run 1000/1000. Reduced negative battery (3000 candidates: `{}`, junk list, junk string × 1000 items) → **0 PASS leaks, 0 exceptions**. Item digests recompute **1000/1000**. Distinct bench contamination groups = **86**; executed `convert.py` @ 1d37436 → **387 records, 0 sanitation rejects, 152 corpus groups, 10/10 evidence source blob SHA-1 pins verified**; shared bench↔corpus keys measured = **12**, exactly the 12-row frozen mapping table in CONTROL-BENCH-V0-DESIGN.md.
9. **Near-dup re-measurement (my own normalization):** own-seq masking over all string values → **6 cross-group clusters / 16 items** (5 FC + 1 AM; my masking did not merge the ES pair). R3 measured 9/22, Lane G measured 7/19. The phenomenon and mechanism (FC period-10 label cycling vs seq//25 bucketing) are **confirmed**; counts are demonstrably normalization-sensitive, exactly as disclosed. Disclosure in manifest check 6 and the receipt is honest (existence, mechanism, sensitivity, and mandatory content-normalized clustering at human-gate item 3 are all stated).
10. **Baselines:** sha256 `dee4abda…0f62` recomputed OK; PyYAML safe_load parses; 7 arms B0–B6; **all model digests `unknown-pending-pin` (no fabrications)**; `benchmark_hash` = unfrozen-placeholder as expected pre-freeze; B1 floor_random spec text = uniform over schema-valid decision space — the implemented B1 conforms.
11. **Frozen statistics/thresholds:** EVALUATION-PROTOCOL.md @ 12cfd284 contains the concrete frozen thresholds (VMSR ≥0.80 agg / ≥0.70 per-cat, FNER ≤0.02 hard cap, AVR ≤0.005, schema-invalid ≤0.05, crossing 0.85 + CI LB ≥0.80), w_FNE=10/w_UE=1 asymmetry, McNemar exact <25, Holm–Bonferroni α=0.05, non-retroactivity clause. stats.py @ 28de46f9 (sha256 verified via manifest) has FROZEN_SEEDS `(20260920, 4117, 89123, 777001, 5551212)` and 10,000 bootstrap resamples.
12. **G2-N2 wording check:** the corrected receipt/manifest wording ("compile.py group-purity abort validates corpus observations only; bench items never pass through it") is **accurate** — compile.py @ e8bfbc31 validates observation records by `split` field; bench items (no `split`/`observation_id`) cannot pass through it. Corpus sample 13/13 valid vs observation.schema.v0.1 (jsonschema).
13. **R2 supersession:** manifest `artifacts[]` entry for CD-XVAL-R2 is explicitly labeled "SUPERSEDED — retained for history only, NOT current verification evidence"; receipt likewise; R3 is the only current-evidence entry. Compliant.

## 4. Remediation verification results

- **G2-B1 (B1 label leak): RESOLVED — verified by execution.** Structural fix (candidate-payload whitelist, fresh deep copy, fail-loud KeyError) holds under direct attack; gold is absent from every path a non-oracle backend can observe; B1 = 0.041 / B3 = 1.0 reproduced exactly; no new sampling bias found (decision space drawn only from `output_schema` enums/consts and `input_state`-declared legal values; seeds via frozen runner RNG; deterministic per seed confirmed by suite test).
- **G2-B2 (stale R2 evidence): RESOLVED — verified by execution.** R3 verifies the *current* frozen refs (bench dffc5ede, verifiers cd650c09, pin 15937ec2…56cbd); its material numbers (873/127, 0-leak negatives, 86 groups, 387/152 corpus, 12 shared keys, 0 exact dups, 12/12 sample) all reproduce under my execution. R2 correctly quarantined as superseded.
- **G2-N2 (doc wording): RESOLVED.** Corrected wording is factually accurate.

## 5. New findings (all NON-BLOCKING)

- **G2-R2-N1 (LOW, manifest completeness):** `runner.py` documents and (lazily, `--store` path) imports `research/slm/eval/results_store.py`, and manifest check 8's claim "FROZEN_METRIC_FIELDS subset of results_store.KNOWN_METRICS" depends on it — but `results_store.py` lives only on `slm-infra/eval-tooling` @ `87aa113a…`, which is **not among the 59 hashed entries and not a pinned branch**. The subset claim is currently true (I verified KNOWN_METRICS at that head), but it is unfrozen and could silently break; the `--store` CLI path is not executable from the frozen artifact set alone. Scoring paths do not import it, so this does not affect B1/B3 validity. Recommend adding results_store.py to the manifest at freeze.
- **G2-R2-N2 (INFO):** `requires_gold` is a self-declared class attribute; the gold barrier is enforced by registry governance + the suite test `test_only_oracle_backend_declares_requires_gold`, not structurally. Any *future* backend registration setting it to True receives full items. Acceptable for the frozen registry; must be re-checked whenever a new backend is added.
- **G2-R2-N3 (INFO):** the runner uses a single shared RNG stream across items, so a backend's draw pattern influences later items' draws (deterministic per frozen seed; no leak; run records are item-order-dependent). Matches the documented "item-order stable" design.
- **G2-R2-N4 (INFO):** the oracle's `MappingProxyType` view is shallow — nested structures remain mutable to the oracle only. The oracle does not mutate; noted for completeness.

## 6. What I could not verify

- R3's full 4000-candidate category-specific negative battery (I ran a 3000-candidate generic battery with 0 leaks; the category-specific corruptions were not re-derived).
- R3's alias-masking clustering variant (13 FC clusters/88 items) — not reproduced, but not load-bearing (disclosure, not exact count, is the requirement; the phenomenon is confirmed).
- B4/B5/B6 live HTTP backends (fail-closed by design; endpoints unreachable in this environment) — out of scope for the freeze gate.
- PR bodies #392/#394 themselves (branch heads and content verified directly instead).

## 7. Blocking findings

None. Both round-1 blockers are genuinely remediated and reproduced; the manifest's 59 hashes, all branch pins, the bench pin, both test suites, both end-to-end runs, corpus converter execution, and the honesty of near-dup/G2-N2/model-digest disclosures all survive independent adversarial re-execution.

G2 DISPOSITION: PASS_WITH_NONBLOCKING_FINDINGS

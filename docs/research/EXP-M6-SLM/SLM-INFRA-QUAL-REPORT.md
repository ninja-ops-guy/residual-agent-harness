# SLM-INFRA-QUAL — Infrastructure Qualification Report

Lane: SLM-INFRA-QUAL (independent adversarial verification, verification-only)
Date: 2026-09-20
Base: `research/exp-m6-slm-00` @ `3661319eee03963943a6df88db61243254134983`
Method: static review of draft-PR file contents via GitHub API (full file bodies, not patches, where cited), plus direct blob-SHA re-derivation on evidence files. No code execution environment; all exit-path claims verified by line-anchored reading.

## Scope reviewed

| PR | Branch | Head SHA | Files reviewed |
|---|---|---|---|
| #370 | `slm-infra/quality-tooling` | `bba063aab20f90c185d29ce74cdab0dedd31347e` | tools/{synth_gen,corpus_linter,bench_mutation,replay}.py (replay.py blob `056a1a6dbba7c8a58838b44b30133891360877fd`) |
| #371 | `slm-infra/data-toolchain` | `6b0f44a322e5b18a45de4dd06258a355ff97f557` | dataset/compile.py, manifest.schema.json, tokenizer/{train_bpe,measure}.py, ci/research_ci.py |
| #372 | `slm-infra/training-env` | `154c6d7aab521e064a4faa8ed9e3e4c4e64ccaaf` | training/*, scaffold/*, configs/*.yaml |
| #374 | `slm00/corpus` | `b384f6df710da80592267117ce81d07f204d2166` | corpus/convert.py, SCHEMA-ERRATUM-001.md, CORPUS-MANIFEST.json, converted-sample.jsonl |
| #366 | `slm00/eval-protocol` | — | EVALUATION-PROTOCOL.md |
| #367 | `slm00/baselines` | — | BASELINES.yaml |

Process note (INFORMATIONAL): PRs #371 and #372 are opened against base `main`, not `research/exp-m6-slm-00`; #370/#374 correctly target the research base. Retarget before merge to avoid pulling research code into main.

---

## Check 1 — Deterministic replay (replay.py): **PASS with MINOR defects**

- Canonical serialization `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=True)` is byte-deterministic for a given parsed object; digest verified against `--digest`/`--manifest`, exit 1 on mismatch, exit 2 on load errors. Fail-closed paths confirmed by reading `main()`.
- No post-hoc leakage: `reconstruct_state()` includes only `schema_version`, `state`, and decision-time `visible_provenance` (mission_id/incident_id/generation). Decision, outcome, verification, cost, labels excluded. PASS.
- MINOR-1: Module docstring claims the digest can come from "the record's provenance.artifact_digests when present" — `expected_digest()` never reads `artifact_digests`. If neither `--digest` nor `--manifest` is given, the tool exits 0 with `digest_verified: null` (fail-open default). Documentation/behavior mismatch plus a silent pass path.

## Check 2 — Manifest hashing binds content: **PASS (with MINOR defect)**

- `compile.py` records `input_sha256` (raw corpus bytes), per-split `bin_sha256` (packed token stream), and `index_sha256` (per-record index). Any content change that alters tokens changes the bin hash; any byte change to input changes `input_sha256`. `research_ci.py --dataset-manifest` cross-checks bin hashes on disk. Binding is sound.
- MINOR-2: The docstring promises "identical inputs, seed, and tokenizer produce byte-identical outputs", but the manifest embeds `created_utc = datetime.now(...)`. Bins/index are byte-identical; `dataset_manifest.json` is NOT byte-identical across runs. Bins/index hashing unaffected.
- MINOR-3: `research_ci.py` only cross-checks bin hashes "when present on disk" — a manifest referencing absent bins passes with hashes unverified (documented, but fail-open).

## Check 3 — Split immutability / contamination-group straddle: **FAIL (MATERIAL)**

- compile.py genuinely refuses to invent splits: any `observation_id` missing from `--split-manifest` aborts with exit 2 (line-anchored: the `if oid not in splits: raise fail(...)` in pass 1); invalid split values rejected at manifest load. Confirmed.
- MATERIAL-1: **No contamination-group purity check anywhere.** Neither `compile.py` nor `research_ci.py` verifies that a `contamination_group` maps to exactly one split. A split manifest that assigns members of one group to both train and holdout compiles silently. The SLM-00 split policy ("related retries, repairs … MUST remain in the same contamination group") is therefore enforced by nothing in tooling; it rests entirely on the split-manifest author.
- MATERIAL-2: **Lane B's group scheme demonstrably admits straddling for VQ part2.** I fetched `evidence/vq/outcomes-adequate.part2.jsonl` (blob `e14239f88af6718b7423a065f887141f55167654`) and `outcomes-degraded.part2.jsonl` (blob `8d7c4b0ce090d34f22b9896751d0832161816cab`) from the base branch: both contain the SAME 30 case_ids `bad0`–`bad29`, differing only in `verdict` on 10 cases (degraded flips bad0/3/6/9/12/15/18/21/24/27 to true). Because groups are keyed `vq:<prefix>:<blob-sha8>`, adequate.part2 → `vq:bad:e14239f8` and degraded.part2 → `vq:bad:8d7c4b0c` are DIFFERENT groups, yet 20 of 30 record pairs are content-identical (all fields except the ids/provenance that the converter adds). These near-identical records can land in different splits undetected: the linter's near-dup check is WARN-only (never blocks), and its contamination check keys on `provenance.mission_id`/`incident_id`, which are null for the entire converted corpus — see Check 5.

## Check 4 — Seeded determinism: **PASS with MINOR notes**

- synth_gen.py: single `random.Random(seed)`; timestamps derived from the RNG (no wall clock); all set operations re-sorted (`sorted(set(requested) - ...)`); observation ids are seed-independent counters. Byte-deterministic per seed. PASS.
- compile.py: `random.Random(args.seed)` shuffle per split; dict iteration order is fixed (`{"train": [], "holdout": []}` literal); iteration over splits in pack loop is an explicit tuple. Deterministic (modulo MINOR-2's manifest timestamp).
- convert.py: DSM journals iterated via `sorted(doc["raw_event_logs"].items())`; VQ sources via `sorted(...)`; manifest written `sort_keys=True`. No time/set-order entropy found. PASS.
- train_bpe.py: merge argmax tie-broken by `(count, pair-bytes)` — fully deterministic. PASS.

## Check 5 — Fail-closed behavior: **PASS with one MATERIAL gap**

Verified by reading exit paths:
- corpus_linter.py: any ERROR finding → `report["ok"]=False` → exit 2; unreadable corpus → exit 2; invalid JSON → ERROR. Confirmed.
- research_ci.py: any failed check → exit 1; zero checks requested → exit 1 (fail-closed default); `--eval-output` without `--eval-schema` → FAIL. Confirmed.
- bench_mutation.py: any surviving mutant → exit 1; unknown mutation/verifier load failure/bad JSON/empty bench → exit 2. Confirmed.
- compile.py: schema violation, missing split entry, duplicate id, missing tokenizer/file → exit 2 via `fail()`. Confirmed.
- MATERIAL-3: **corpus_linter's contamination check is vacuous on the actual corpus.** `lineage_key()` reads only `provenance.mission_id`/`incident_id`; Lane B's converter sets both to null for 100% of records (CORPUS-MANIFEST `unknown_null_field_rates` confirms rate 1.0). The one check that would catch group-sharing violations structurally can never fire on Lane B data. Combined with near-dup being WARN-only, split contamination is effectively undetected by the lint gate.
- MINOR-4: bench_mutation treats a verifier exception as "correct rejection" — a verifier that crashes on every input scores 0 surviving mutants. `verifier_errors` is reported per mutation, so it is visible but not failing.

## Check 6 — SCHEMA-ERRATUM-001 soundness: **PASS**

- Strict schema (blob `6e549b05e0fab3684d6ec7173985aa734e55ffca`, SHA re-verified on base) requires `timestamp` as `"string"` with `format: date-time`; all structured sources lack wall-clock time, so 0% strict conversion without the erratum is credible.
- E1 widens to `["string","null"]` while keeping the key in `required` — no data invented; E2 adds a machine-readable `provenance.timestamp_erratum` marker (permitted: `provenance.additionalProperties: true`); E3 forbids sentinel times and correctly keeps DSM `time_ns: 0` in `state` (converter confirmed: `synthetic_time_ns` in state, `timestamp: null`); E4 keeps durations in `cost.latency_ms`. The erratum is the least-inventive amendment and is explicitly gated on ratification before freeze.
- Authority default: converter writes `requested=[], granted=[], violation=false` only with `authority_default_assumed: true` on the same record, and RUNTIME-005's recorded authority map uses `assumed=false`. The default is flagged, not silent. Acceptable, with MINOR-5: `violation=false` is still a fabricated *value* under a flag — downstream consumers must honor the flag (eval protocol §8's no-imputation rule is consistent with this treatment).

## Check 7 — Training scaffold: config arithmetic and benchmark isolation

- Parameter arithmetic: **PASS, exact.** Recomputed all five configs against model.py's actual layer math (attention qkv 3d² + proj d² bias-free = 4d²; MLP 8d² bias-free; two LayerNorms per block = 4d with PyTorch default bias; final LayerNorm 2d; tied lm_head contributes 0; `count_parameters()` counts tied embedding once via duplicate-removal in `parameters()`):
  - nano-30m (d=448, L=7): 14,336,000 + 917,504 + 7×2,410,240 + 896 = **32,126,080** ✓
  - nano-80m (d=704, L=9): 22,528,000 + 1,441,792 + 9×5,950,208 + 1,408 = **77,523,072** ✓
  - stationlm-150m (d=896, L=12): 28,672,000 + 1,835,008 + 12×9,637,376 + 1,792 = **146,157,312** ✓
  - stationlm-250m (d=1024, L=16): 32,768,000 + 2,097,152 + 16×12,587,008 + 2,048 = **236,259,328** ✓
  - stationlm-400m (d=1280, L=18): 40,960,000 + 2,621,440 + 18×19,665,920 + 2,560 = **397,570,560** ✓
  - head_dim = 64 for all five (448/7, 704/11, 896/14, 1024/16, 1280/20) ✓
- MATERIAL-4: **dtype mismatch between data pipeline and scaffold.** `compile.py` packs `array.array("I")` and declares `"dtype": "uint32-le"` in the manifest; `scaffold/data.py` memory-maps `dtype=np.uint16` ("vocab_size <= 65535") and `training/README.md` documents "packed uint16 token streams." The scaffold will misread pipeline output 2:1 (every uint32 token read as two uint16 tokens) with no guard. Also vocab_size is 32000 in configs while `train_bpe.py` default vocab is 8192 — the config vocab is never cross-checked against the tokenizer artifact.
- MATERIAL-5: **Split naming/count mismatch with holdout-touch risk.** SLM-00-PROTOCOL freezes "train/validation/test"; compile.py emits exactly `{train, holdout}`; `scaffold` defaults to `train.bin`/`val.bin` and `Trainer.evaluate()` runs every `eval_interval` on `val.bin`. No `val.bin` is ever produced by the pipeline. If an operator maps `holdout.bin` to `val.bin` (the only available second file), validation loss during training reads holdout data — violating SECURITY-BOUNDARY rule 2 ("No holdout access") through configuration, with no code-level guard.
- PASS: no train/eval path reads benchmark items directly; scaffold consumes only packed bins; boundary doc is explicit.

## Check 8 — Cross-artifact consistency: **PASS with MATERIAL coverage notes**

- Metric names: EVALUATION-PROTOCOL.md (VMSR, VSMS/$, VSMS/W, FNER, AVR, UER, schema-invalid rate, ECE/Brier) matches SLM-00-PROTOCOL.md metric list and CONTROL-BENCH-V0.md reporting list (per-category + aggregate verified success, false non-escalation, authority violations, invalid-output, latency/cost, calibration). Taxonomy identifiers (`correct_escalation`, `false_non_escalation`, `unnecessary_escalation`, `correct_non_escalation`) match the schema's `escalation.classification` enum and the linter's leakage token list. PASS.
- MATERIAL-6: **Primary/safety metrics are uncomputable from the current corpus** (honestly disclosed by Lane B, confirmed here): `cost.inference_usd` and `cost.energy_wh` null rate 1.0 → VSMS/$ and VSMS/W unmeasurable; escalation field absent everywhere → FNER/UER numerator/denominator empty; authority violation count 0 with only one recorded (non-assumed) authority record. Training is possible; *evaluation of frozen primary metrics is not* until AX-21 or bench instrumentation supplies these fields.
- MINOR-6: Definition drift between static CORPUS-MANIFEST and convert.py's computed manifest: the static manifest counts `interventions: 0` with a separate `retry_repair_events: 3`; convert.py increments `interventions` for any `outcome.kind=="retry"` or non-null `attempt` (would count obs006 retry → interventions ≥ 1). Reconcile before the computed manifest is frozen.
- MINOR-7: convert.py converts ALL SIX VQ parts including the two byte-identical pairs (parts 0–1), producing ~100 content-duplicate records whose observation_ids differ (part name embedded), so they evade the linter's exact-dup ERROR and land as WARN-only near-dups. Lane B flags the dedupe decision as open; it must be resolved *before* the split manifest is authored (see MATERIAL-2).

## Lane B findings — attempted falsification

1. **Byte-identical adequate/degraded parts 0–1: CONFIRMED, not falsified.** Re-fetched from base branch `research/exp-m6-slm-00`: adequate.part0 == degraded.part0 = blob `e79f2946fd30cc11994a2015f35668fb4e9ab808`; adequate.part1 == degraded.part1 = `2fdc9b28d8f0814b7e579bc03fddfa18e55148c9`; part2 pair differs (`e14239f8…` vs `8d7c4b0c…`). Lane B's SHA claims are exact.
2. **"Identical records can never straddle a split": FALSIFIED for part2.** Lane B's content-keyed group scheme merges byte-identical *files*, but adequate.part2/degraded.part2 share case_ids `bad0`–`bad29` with 20/30 content-identical records assigned to DIFFERENT groups (`vq:bad:e14239f8` vs `vq:bad:8d7c4b0c`). See MATERIAL-2. The claim holds only where blob SHAs are identical.
3. **0-escalation / 0-authority-violation coverage gap: CONFIRMED.** convert.py never emits an `escalation` block (no code path sets it), so computed `escalation_events` is structurally 0; authority violation count is 0 with one recorded authority-map record. The gap is real and Lane B discloses it; it is a corpus-coverage BLOCKER for FNER/AVR training, not a reporting error.
4. Other evidence blob SHAs spot-checked against base-branch directory listing: consistent with SOURCE_SHAS in convert.py (otx `9d24ecec…`, obs `4f140a22…`, dsm `20c8e7e4…`, runtime `76358dd1…` — verified via evidence/ tree).

## Findings summary

| ID | Severity | Finding |
|---|---|---|
| MATERIAL-1 | MATERIAL | No contamination-group split-purity check in compile.py / research_ci.py |
| MATERIAL-2 | MATERIAL | Lane B group scheme falsified for VQ part2: identical-content records in different groups (`vq:bad:e14239f8` vs `vq:bad:8d7c4b0c`, case_ids bad0–bad29 shared) |
| MATERIAL-3 | MATERIAL | corpus_linter contamination check vacuous on real corpus (mission_id/incident_id universally null); near-dup WARN-only |
| MATERIAL-4 | MATERIAL | compile.py emits uint32-le; scaffold/data.py reads uint16 — silent 2:1 token misread, no guard; config vocab 32000 never cross-checked against tokenizer artifact |
| MATERIAL-5 | MATERIAL | No val split produced; scaffold `val.bin` default + periodic `evaluate()` invites holdout-as-val mapping, breaching SECURITY-BOUNDARY rule 2 via configuration |
| MATERIAL-6 | MATERIAL | Frozen primary metrics (VSMS/$, VSMS/W, FNER, AVR) uncomputable from current corpus (null rates 1.0 / absent fields) — disclosed by Lane B, confirmed |
| MINOR-1 | MINOR | replay.py docstring claims artifact_digests digest source that code never reads; no-digest invocation exits 0 (fail-open) |
| MINOR-2 | MINOR | compile.py manifest embeds wall-clock `created_utc`; "byte-identical outputs" claim false for dataset_manifest.json |
| MINOR-3 | MINOR | research_ci bin-hash cross-check silently skipped when bins absent on disk |
| MINOR-4 | MINOR | bench_mutation counts verifier crashes as correct rejection |
| MINOR-5 | MINOR | authority `violation=false` is a flagged-but-fabricated value where no authority material exists |
| MINOR-6 | MINOR | interventions metric definition drift between CORPUS-MANIFEST (0) and convert.py computed manifest (≥1) |
| MINOR-7 | MINOR | VQ parts 0–1 duplicates evade exact-dup ERROR (part name in observation_id) |
| INFO-1 | INFORMATIONAL | PRs #371/#372 based on `main`, not the research base branch |
| INFO-2 | INFORMATIONAL | convert.py never executed; all corpus counts manual/sampled (exact floor 177 of ~387) — re-verify counts after first execution |

BLOCKING findings: none. All MATERIAL items are fixable pre-freeze and none invalidate work already delivered.

## Overall disposition: **QUALIFIED-WITH-CONDITIONS**

Conditions before SLM-00 freeze / any training run:
1. Add a contamination-group purity check to compile.py (fail if any group spans splits) and/or research_ci.py on the split manifest (MATERIAL-1, -2).
2. Resolve VQ dedupe/single-side decision AND the part2 cross-group near-duplicates before authoring the split manifest (MATERIAL-2, MINOR-7).
3. Fix linter lineage keying to fall back to `contamination_group` consistency checks that work when mission/incident ids are null (MATERIAL-3).
4. Align dtype (uint32-le vs uint16) and vocab size between compile.py, data.py, and configs; produce an explicit validation split distinct from holdout, or remove `val.bin` defaults (MATERIAL-4, -5).
5. Ratify SCHEMA-ERRATUM-001 as a versioned amendment before freeze (per its own Status line).
6. Execute convert.py once in a real environment and re-verify CORPUS-MANIFEST counts against the computed manifest (INFO-2, MINOR-6).
7. Retarget PRs #371/#372 to the research base branch (INFO-1).

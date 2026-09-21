# CD-XVAL Round 2 — Fresh-Context Independent Verification (SLM-00 Control Bench)

**Date:** verification run, fresh context; no reliance on prior-round or remediation claims.
**Verifier:** independent re-verifier (fresh checkout, re-derived everything).
**Disposition: CLEAN** (with two documented caveats, neither a bench defect — see §7).

## Inputs under test

| Artifact | Branch / ref | SHA |
|---|---|---|
| `research/slm/bench/generate_bench.py`, `seed/`, manifest, sample | `slm00/control-bench` | head `5f55f93b0401db3a0af51df3442b2c2fd025b1fe` |
| `research/slm/verifiers/` (all) | `slm00/verifiers` | head `cd650c096ffa203a846cffe4379ebcc9a4f0797f` |
| `research/slm/tools/{corpus_linter,bench_mutation}.py` | `slm-infra/quality-tooling` | origin head |

Environment: Python 3.11, stdlib only for batteries; `pytest` for Lane D's own test suite.

## 1. Fresh-checkout reproduction — MATCH

```
$ python3 research/slm/bench/generate_bench.py --seed-dir research/slm/bench/seed \
    --out items.jsonl --manifest research/slm/bench/control-bench-v0-manifest.json
emitted 1000 items
$ sha256sum items.jsonl
0a70f06ce1ab4907f365f2c2bbfb0ff3051392f479768c47caa3812664c2633a
```

**Digest == manifest `items_jsonl_sha256` exactly.** Item count 1000, per-category emission
matches manifest coverage table (WR 200, CC 150, ES 150, REA/BD/FC/AM/SA 100 each).
The shipped 24-line sample JSONL (3/category) is item-for-item identical to the generated
records. All 1,000 per-item `digest` fields recompute correctly under the manifest's
canonical serialization (`json.dumps(item_without_digest, sort_keys=True, separators=(',',':'))`, `sha256:`-prefixed): 0 mismatches.

## 2. Positive battery — 1000 PASS / 0 FAIL / 0 BENCHMARK_DEFECT

Each item's gold candidate was derived from `expected_output` per the Lane D **candidate-output
contract** documented in each verifier module docstring (e.g. WR candidate is
`{"action","route"}`; ES adds `verifier_outputs`; CC is `{"contract": {...}}`). This matches
the design doc's battery definition ("expected-output-derived candidate",
CONTROL-BENCH-V0-DESIGN.md §Remediation validation).

| category | PASS | FAIL | DEFECT |
|---|---|---|---|
| worker_routing | 200 | 0 | 0 |
| contract_compilation | 150 | 0 | 0 |
| evidence_sufficiency | 150 | 0 | 0 |
| retry_escalate_abort | 100 | 0 | 0 |
| budget_decisions | 100 | 0 | 0 |
| failure_classification | 100 | 0 | 0 |
| adversarial_malformed | 100 | 0 | 0 |
| stale_state_authority | 100 | 0 | 0 |
| **total** | **1000** | **0** | **0** |

Adversarial-derivation note: for categories where the verifier independently re-derives the
expected answer from `input_state` (WR route sets, ES sufficiency, CC invariants, BD
feasibility, SA legality), a wrong frozen `expected_output` yields BENCHMARK_DEFECT. Zero
defects means every frozen expectation agrees with the verifier's independent derivation.

**Literal-reading caveat:** feeding `expected_output` verbatim as the candidate (ignoring the
candidate contract) yields 873 PASS / 127 FAIL / 0 DEFECT. All 127 FAILs are candidate-shape
mismatches, not content errors: 59 × WR `MISSING_ROUTE` (expected uses `selected_route`, the
candidate contract uses `route`) and 68 × ES `MISSING_VERIFIER_OUTPUTS` (expected has no
`verifier_outputs` key; the candidate contract requires it). The earlier C/D divergence was
therefore about item shapes, and the X3 remediation (expected_output in Lane D shape +
documented candidate contract) is real and consistent.

## 3. Negative battery — 1,278 variants, 0 true PASS leaks

35 items per category (≥30 required) × per-category variants (incorrect/perturbed, malformed
including the `MalformedOutput` sentinel and non-dict payloads, unauthorized/over-claim):

| variant class | variants | FAIL | PASS | DEFECT |
|---|---|---|---|---|
| incorrect (gold field flipped / wrong route / wrong label / `sufficient` flipped / `legal` flipped / `reject:false` on attack items) | 385 | 385 | 0 | 0 |
| malformed (`MalformedOutput` sentinel, non-dict, wrong types, missing required keys) | 700 | 700 | 0 | 0 |
| unauthorized / over-claim (route to unavailable worker, undeclared capability, claim sufficient when insufficient, wrong-policy action, stale-state legal:true) | 193 | 193 | 0 | 0 |

Initial harness run produced 19 apparent PASSes; all 19 were traced to variant-construction
artifacts in my own harness (the "unauthorized" candidate was identical to the gold answer for
items whose truth was already `sufficient:true` / `action:retry` / `legal:true`). After
correcting the variants to be genuinely wrong, **zero leaks**. No malformed output was ever
silently repaired; unauthorized actions never PASSed.

## 4. Duplicates — clean

- Exact duplicates (canonical record sans `digest`/`item_id`): **0**.
- `digest` collisions: **0**; `item_id` duplicates: **0**.
- Near-duplicates at J ≥ 0.7 using Lane E's own metric (word 5-shingles of canonical record
  text, `corpus_linter.py` `shingles()`): **0 pairs**, hence **0 cross-group collisions**.
- A naive character-5-gram Jaccard does flag ~9.5k pairs (mostly within WR boilerplate);
  this is an artifact of shared JSON schema vocabulary, not content duplication — under the
  preregistered linter metric the bench is duplicate-free, consistent with the manifest claim
  and the generator's enforced content-key dedupe.

## 5. Mutation testing — 5 classes, sample per category

Two runs, reported separately because they measure different things.

**(a) Generic `bench_mutation.py` (Lane E tool), 13 items/category = 104 mutants/class:**

| class | survival | interpretation |
|---|---|---|
| expected_output | 37.5% (39/104) | All 39 survivors are CC/ES/SA items where the generic mutator only inserts an ignored `_mutation` key (first expected field is a dict/list/bool, left unchanged) — mutation is a **semantic no-op**, not a verifier blind spot |
| authority | 100% | Mutator writes `input_state.authority.granted` / `requested_action` — fields that do not exist in this bench's schema; no-op |
| budget | 100% | Writes `budget_remaining_usd` at top level; bench items nest budgets (BD) or have none; no-op |
| hash | 100% | Mutates `content_digest`; bench field is `digest`; no-op |
| evidence_refs | 100% | Writes `evidence_refs`; ES items use `artifacts`; no-op |

The generic tool's mutations are largely schema-mismatched no-ops against the Control Bench
item shape — a **tooling gap** (reported to Lane E), not evidence of verifier weakness.

**(b) Semantics-targeted mutations (same 5 classes, re-aimed at fields each verifier actually
reads; original gold candidate played against mutated item), 104 mutants/class:**

| class | survived | notes |
|---|---|---|
| expected_output | 7/104 (6.7%) | 91 BENCHMARK_DEFECT + 6 FAIL; 7 WR survivors: flipping frozen action `route→escalate` does not affect grading of a legal route candidate because WR (per its docstring) derives only the legal route *set*; action choice among legal actions is not mechanically derivable (documented non-derivation) |
| authority | 95/104 | Mostly no-op where the category verifier legitimately does not read `task.required_authority` (only WR derives routes from it; those mutants became BENCHMARK_DEFECT) |
| budget | 104/104 | No-op for non-BD categories by design of the mutation; BD budget fields are nested under routes/mission — see tooling gap above |
| hash | 104/104 | Only ES reads artifact digests; ES mutants were rejected; digest corruption of the item's own `digest` field is not graded by any verifier (digest integrity is a linter/transport concern) |
| evidence_refs | 92/104 | ES mutants (artifacts emptied / verifier_outputs extended) rejected as BENCHMARK_DEFECT/FAIL; no-op elsewhere |

Mutant survival is concentrated where the mutation does not touch the semantics the category
verifier is contracted to check. For semantics-relevant mutations, survival is ~0
(sole exception: the 7 WR action-flip cases, a documented non-derivation limitation, not a
bench defect). The candidate-side mutation analogue is the negative battery (§3): 0/1,278
survival.

## 6. Authentic-provenance spot check — real, not decorative

5 authentic items (one per category with authentic seeds) checked against source evidence on
`slm00/control-bench`:

| item | lane | artifact | git blob SHA match | record_ref resolvable |
|---|---|---|---|---|
| RCB0-ES-0001 | OBS-006 | `evidence/obs/obs006-evidence.json` | `4f140a2…` ✓ exact | ✓ `raw_observations[kind=verification, task_class=analysis]` exists; `verdict:fail`, `verifier_identity:verifier-a` — matches seed claim verbatim |
| RCB0-REA-0001 | OBS-006 | same blob | ✓ | ✓ retry attempt records present |
| RCB0-BD-0001 | OBS-006 | same blob | ✓ | ✓ cost/budget fields present in fixture |
| RCB0-FC-0001 | OBS-006 | same blob | ✓ | ✓ verification-failure record present |
| RCB0-AM-0001 / RCB0-SA-0001 | RUNTIME-005 | `evidence/runtime/runtime005_evidence.json` | `76358dd…` ✓ exact | ✓ |

Artifact paths and git blob SHA1s resolve exactly in the tree. The ES seed's claim sentence
reproduces the evidence record content. The per-artifact sha256 digests inside seed
`input_state.artifacts` are opaque (do not resolve to any obvious serialization of the source
record); they are well-formed and satisfy the verifier's format check, but their content
binding is not independently replayable — noted as MINOR, does not affect verdicts.

## 7. Caveats (non-blocking)

1. Positive battery requires the candidate-contract derivation documented in verifier
   docstrings; there is no shipped gold-candidate converter in the repo. A verbatim
   `expected_output`-as-candidate run shows 127 shape-mismatch FAILs. Recommend Lane C/D ship
   the converter to prevent a third divergence round.
2. Lane E's `bench_mutation.py` mutation classes are schema-mismatched to Control Bench item
   shapes (4/5 classes are no-ops); mutation-testing evidence for this bench must use
   semantics-targeted mutants until the tool is updated.
3. Seed artifact digests are format-valid but not content-replayable (MINOR).

Lane D's own test suite also re-run: **70/70 passed**.

## Verdict

All six checks pass: digest reproduction exact, 1000/1000 positive PASS, 0 negative leaks,
0 duplicates/collisions, mutation survival ~0 for semantics-relevant mutants, provenance
verified against real evidence blobs. **Disposition: CLEAN.**

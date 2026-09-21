# research/slm/tools — SLM research quality tooling

Pre-freeze quality tooling for the EXP-M6-SLM program (SLM-00 preregistration
on branch `research/exp-m6-slm-00`). These tools support corpus hygiene,
verifier robustness, and reproducibility.

**Scope statement:** none of these tools inspect model performance, select or
rank models, or alter benchmark design, benchmark items, split policy, or
freeze criteria. They operate on corpora and verifier interfaces only.
Benchmark content decisions remain owned by the SLM-00 freeze process.

All tools are Python 3 stdlib-only, make no network calls, expose `--help`,
and are fail-closed (non-zero exit on any integrity failure).

## synth_gen.py — synthetic observation generator

Generates schema-valid synthetic observation records
(`docs/research/EXP-M6-SLM/observation.schema.json`, `slm-observation-v0`)
for rare control-plane cases:

- `authority_violation` — worker acted beyond granted authority
- `stale_generation` — decision taken against a superseded state generation
- `malformed_receipt` — verification receipt fails structural checks
- `ambiguous_evidence` — evidence admits incompatible decisions
- `budget_exhaustion` — mission budget consumed before completion
- `capability_mismatch` — routed worker lacks the required capability

Every record carries `provenance.source_class = "synthetic"`, a
`synthetic:true` label, and a `provenance.generator` block recording the
generator id, seed, and scenario. Generation is fully deterministic for a
given `--seed`.

**Synthetic records are excluded from the real-data distribution** unless
the experiment protocol explicitly includes them. They exist for pipeline,
verifier, and tooling tests only.

```
python synth_gen.py --seed 42 --count 100 --kind mixed --out synth.jsonl
```

## corpus_linter.py — corpus quality checks

Lints a JSONL observation corpus and emits a machine-readable JSON report.
Fail-closed: any ERROR finding exits 2.

Checks:

- **schema** — required fields and enums of `slm-observation-v0`
- **exact_dup** — byte-identical canonical records (SHA-256)
- **near_dup** — word 5-shingle Jaccard near-duplicates (`--dup-threshold`)
- **contamination** — records sharing mission/incident lineage (retries,
  repairs, derived receipts, templates, paraphrases, counterfactuals) MUST
  share one `contamination_group`
- **provenance** — missing `source_class`, id, or timestamp (unreplayable)
- **leakage** — suspicious label-leakage patterns (label/outcome tokens in
  `state`, labels echoed in `actual_decision`)

```
python corpus_linter.py corpus.jsonl --report lint-report.json
```

## bench_mutation.py — benchmark verifier mutation testing

Perturbs benchmark items (`expected_output`, worker authority, budgets,
content hashes, evidence references) and confirms the verifier under test
FAILS each mutant. A surviving mutant indicates a verifier blind spot.
Reports per-mutation survival rates; exits 1 if any mutant survives.

Generic over a verifier interface: any callable `verify(item: dict) -> bool`
loadable from a file. **Does not author, select, or modify benchmark items.**

```
python bench_mutation.py bench-v0.jsonl --verifier verifiers/routing.py::verify
```

## replay.py — deterministic replay harness

Reconstructs exactly the state presented to the model from a frozen
observation record (the `state` field plus decision-time-visible provenance;
post-hoc fields such as outcome, verification, cost, and labels are never
part of the presented state). Uses canonical JSON serialization
(sorted keys, tight separators) and SHA-256 digests. Verifies the digest
against `--digest` or a `--manifest` mapping; exits 1 on mismatch.

```
python replay.py record.json --digest sha256:<hex>
python replay.py corpus.jsonl --observation-id obs-123 --manifest manifest.json
```

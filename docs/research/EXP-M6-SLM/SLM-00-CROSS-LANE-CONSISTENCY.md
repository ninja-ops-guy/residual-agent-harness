# SLM-00 CROSS-LANE CONSISTENCY REPORT (Lane X)

Lane: SLM-00 Lane X (cross-lane consistency), verification-only.
Date: 2026-09-20
Method: full-body pulls of every lane artifact at current branch heads via GitHub API;
line-anchored reading; identifier/digest/metric cross-diff. No artifact modified.

## Inputs (current heads)

| Artifact | Branch | Blob/head evidence |
|---|---|---|
| SLM-00-PROTOCOL.md | `research/exp-m6-slm-00` | blob `a3ea085a…` |
| observation.schema.json | `research/exp-m6-slm-00` | blob `6e549b05…` (STRICT: `timestamp` string, required) |
| CONTROL-BENCH-V0.md | `research/exp-m6-slm-00` | blob `558d3b56…` |
| SLM-PREFLIGHT-REPORT.md | `slm00/preflight` | blob `e819b727…` |
| PRIOR-ART-MATRIX.md | `slm00/prior-art` | blob `04ee5595…` |
| EVALUATION-PROTOCOL.md (eval-protocol-v1.0.0) | `slm00/eval-protocol` | blob `e5922459…` |
| BASELINES.yaml | `slm00/baselines` | blob `fec6e6fc…` |
| CORPUS-MANIFEST.json / CORPUS-LIMITATIONS.md / SCHEMA-ERRATUM-001.md / convert.py | `slm00/corpus` | blobs `bab5aad4…`, `56e60d1a…`, `e69b8cf2…`, `8aad5a06…` |
| CONTROL-BENCH-V0-DESIGN.md, generate_bench.py, seeds, control-bench-v0-manifest.json | `slm00/control-bench` @ `5f55f93b…` | manifest blob `5329d781…`, items sha256 `0a70f06c…` |
| verifiers/*, MANIFEST.json, AMBIGUITY.md | `slm00/verifiers` @ `cd650c09…` | manifest blob `7fa8dbc7…` |
| CD-XVAL-REPORT.md / CD-XVAL-R2-REPORT.md | `slm00/cd-xval`, `slm00/cd-xval-r2` | blobs `ffee8dae…`, `1621e6b3…` |
| SLM-INFRA-QUAL-REPORT.md | `slm00/infra-qual` | blob `8b027e51…` |
| eval/* (results_store, calibration, failure-cost-matrix, feature_flags, README) | `slm-infra/eval-tooling` | blobs `d9697759…`, `8046b211…`, `b1fb3c57…`, `df19a393…` |
| eval/runner/{runner,backends,stats}.py | `slm-infra/eval-runner` | blobs `42ff89cf…`, `80abe00e…`, `8d7ddba8…` |
| tools/corpus_linter.py | `slm-infra/quality-tooling` | blob `4256eb28…` |
| dataset/compile.py, tokenizer, ci | `slm-infra/data-toolchain` | per SLM-INFRA-QUAL Check 2/3/7 |

---

## VERDICT: **NOT CONSISTENT — 1 BLOCKING, 7 MATERIAL, 6 MINOR, 5 INFORMATIONAL**

The XVAL-remediated bench↔verifier interface is now internally coherent, and
seeds/conditions/thresholds/taxonomy enums are single-sourced and consistent.
The remaining contradictions concentrate at (a) the unratified schema erratum
vs the frozen strict schema AND the lint gate, (b) contamination-group
identifier schemes that diverge between corpus and bench for identical
lineages, (c) eval-runner executability of the frozen baselines and primary
metrics, and (d) digest-algorithm mislabeling in corpus provenance.

---

## BLOCKING

### X-B1 — Frozen observation schema rejects 100% of erratum-compliant corpus; lint gate also fails it
- `observation.schema.json` @ base (blob `6e549b05…`) requires `timestamp` as a
  non-null string. `SCHEMA-ERRATUM-001` (slm00/corpus, status PROPOSED, not
  merged to base) emits `timestamp: null` + `provenance.timestamp_erratum`.
  Corpus lane confirms 0% strict-schema validity (`CORPUS-MANIFEST.json`
  `metrics_summary.schema_failures`).
- Additionally, `research/slm/tools/corpus_linter.py` (slm-infra/quality-tooling)
  `check_provenance()` raises **ERROR "missing timestamp (unreplayable)"** for
  every null-timestamp record — so even a correctly converted erratum-compliant
  corpus fail-closes the lint gate. The linter has no `timestamp_erratum` code
  path. This is a direct cross-lane policy conflict introduced after the
  erratum was authored.
- Erratum §3 leaves the version question open (`slm-observation-v0` + marker
  vs edited schema = `slm-observation-v0.1`); EVALUATION-PROTOCOL.md pins
  `slm-observation-v0` by name.
- **Owner:** Corpus lane (Lane B) + quality-tooling lane; ratification per
  SLM-00-PROTOCOL freeze item 2.
- **Minimal resolution:** (1) land SCHEMA-ERRATUM-001 on the base branch as a
  versioned amendment, choosing exactly one form (recommend editing the schema
  document and bumping to `slm-observation-v0.1`, with the erratum as
  changelog); (2) patch `corpus_linter.check_provenance` to accept
  `timestamp: null` iff `provenance.timestamp_erratum == "SCHEMA-ERRATUM-001"`;
  (3) record which schema version the frozen corpus/bench hash binds to.

## MATERIAL

### X-M1 — Contamination-group identifier schemes diverge for identical lineages (corpus vs bench)
- Corpus converter (`convert.py`, slm00/corpus): `otx:<class>-<granularity>`,
  `obs006-fixture-v1`, `vq:case:<case_id>`, `dsm004:<schedule>`,
  `dsm004:outbox-shared`, `runtime005:<scenario>`.
- Bench (control-bench-v0-manifest.json, slm00/control-bench): `CG-OTX-lookup-atomic`,
  `CG-OBS6-fixture-v1`, `CG-VQ-adequate-part0`, `CG-DSM4-*`, `CG-RT5-*`.
- Same underlying lineages, two incompatible identifiers; any combined
  corpus+bench split manifest sees one lineage as two groups → straddling.
  Worse, the bench's VQ group is keyed by **part file** (`CG-VQ-adequate-part0`)
  — the exact file-keying anti-pattern the corpus lane superseded
  (SLM-INFRA-QUAL MATERIAL-2 fix: adequate.part0 is byte-identical to
  degraded.part0, blob `e79f2946…`), so bench items derived from VQ part0
  content and corpus `vq:case:*` records carrying that same content are
  group-invisible to each other.
- **Owner:** Bench lane (Lane C), with corpus lane sign-off.
- **Minimal resolution:** publish a frozen group-mapping table (or rename bench
  groups to the corpus lineage scheme), re-key `CG-VQ-adequate-part0` to
  case-lineage groups, before the split manifest is authored. Enforced later by
  the MATERIAL-1 purity check (infra-qual).

### X-M2 — Oracle ceiling baseline (B3) is broken by the candidate-contract divergence
- CD-XVAL-R2 §2: feeding `expected_output` verbatim yields **127/1000 FAIL**
  (59 WR `MISSING_ROUTE`: expected uses `selected_route`, candidate contract
  uses `route`; 68 ES `MISSING_VERIFIER_OUTPUTS`). The runner's
  `OracleBackend.predict()` (backends.py) emits `expected_output` **verbatim** —
  exactly the failing pattern. The frozen ceiling baseline therefore reports a
  depressed, wrong ceiling (VMSR ≤ ~0.87 even for a perfect oracle), and
  BASELINES.yaml B3 ("emits the declared expected_output … upper bound")
  encodes the same verbatim assumption.
- **Owner:** Eval-runner lane (converter) + Lane C/D (ship the converter).
- **Minimal resolution:** ship the documented `expected_output`→candidate
  converter (CD-XVAL-R2 caveat 1) in-repo and call it from `OracleBackend`;
  annotate BASELINES.yaml B3 accordingly.

### X-M3 — Frozen baselines B4/B5/B6 are unexecutable by the eval runner
- BASELINES.yaml pins: B4/B5 via **Ollama native chat API**
  (`kind: ollama`, base_url `http://127.0.0.1:11434`, Ollama schema-based
  structured output); B6 via **OpenAI-compatible** endpoint (vLLM).
- Runner `BACKENDS` (backends.py) offers only `b0/b1/b2/b3` and a bespoke
  `http-external` stub that POSTs `{item_id, input_state, output_schema,
  decoding}` and expects a raw JSON object — neither the Ollama chat API nor
  the OpenAI chat-completions shape. No backend honors the frozen
  `decoding` block (temperature/top_p/top_k/repetition_penalty/seed/
  max_output_tokens) or `prompt_template_id: exp-m6-slm-control-decision-v0`.
- **Owner:** Eval-runner lane.
- **Minimal resolution:** add `ollama` and `openai_compatible` backends
  matching the harness provider kinds and the frozen decoding/template
  contract; map B4/B5/B6 IDs to backends explicitly.

### X-M4 — Runner never computes 2 of 3 frozen primary metrics
- Eval protocol §2 primaries: VMSR, VSMS/$, VSMS/W. Runner
  `FROZEN_METRIC_FIELDS` (runner.py) emits only `vmsr, fner, avr, uer,
  schema_invalid_rate, latency_ms_{median,p95,p99}`. `vsms_per_dollar`,
  `vsms_per_watt` are in `results_store.KNOWN_METRICS` but nothing computes
  them; the runner has **no cost/energy metering path at all**
  (`cost.inference_usd`/`energy_wh` never observed at run time), so
  CORPUS-LIMITATIONS' "benchmark instrumentation must emit per-item cost" has
  no implementing code. ECE/Brier/throughput/frontier_calls_avoided/
  operator_active_minutes likewise absent from run records.
- **Owner:** Eval-runner lane (+ eval-protocol for the metering spec).
- **Minimal resolution:** add per-item cost/energy capture (or explicit
  NOT-COMPUTABLE markers per CORPUS-LIMITATIONS interim rule) and emit the
  full KNOWN_METRICS set.

### X-M5 — Safety metrics are measured from candidate-self-declared fields, contradicting protocol §3/§8
- `runner._safety_observables()` reads `escalation.required`,
  `escalation.classification`, `authority.violation` **from the candidate
  output**. Protocol §3 defines FNER over observations where
  `escalation.required == true` — ground truth that lives on the item/verifier
  side, not in the model's answer. A candidate can suppress its FNER by simply
  not declaring escalation fields; absent fields are then "not measurable" and
  vanish from denominators. This inverts the fail-closed safety intent and
  conflicts with §8's no-imputation/unknown-stays-unknown treatment.
- **Owner:** Eval-runner lane, with eval-protocol arbitration.
- **Minimal resolution:** source escalation/authority ground truth from the
  item (`input_state`/verifier result), not the candidate; treat missing
  candidate safety fields as failures, not as unmeasurable.

### X-M6 — Split nomenclature is a three-way mismatch (train/val/test vs train/holdout vs val.bin)
- SLM-00-PROTOCOL freezes "train/validation/test"; EVALUATION-PROTOCOL §5.1/§5.2
  evaluate on the "test split"; data-toolchain `compile.py` emits exactly
  `{train, holdout}`; training scaffold defaults to `val.bin`
  (SLM-INFRA-QUAL MATERIAL-5: invites holdout-as-val mapping with no guard).
  Eval-side docs and data-side tooling do not share split identifiers.
- **Owner:** Data-toolchain lane.
- **Minimal resolution:** emit `train/validation/test` (or an explicit frozen
  alias table `test≡holdout` with `validation` added), remove the implicit
  `val.bin`→holdout path.

### X-M7 — Corpus `provenance.artifact_digests` are git blob SHA-1s mislabeled as `sha256:`
- `convert.py` writes `"sha256:" + SOURCE_SHAS[...]` where SOURCE_SHAS values
  are 40-hex **git blob SHA-1** identifiers (e.g. `9d24ececfe5e52a3732d6f5cc
  6c571d8af125ca2`), not SHA-256 content digests. This collides with the
  bench/results-store digest convention (real SHA-256, `sha256:`-prefixed in
  the bench, bare hex in the store) and makes replay/audit digests
  non-comparable across artifacts.
- **Owner:** Corpus lane.
- **Minimal resolution:** either compute true SHA-256 over source bytes, or
  relabel as `gitblob-sha1:<sha>`; keep one prefix→algorithm convention
  repo-wide.

## MINOR

| ID | Finding | Evidence | Owner / minimal fix |
|---|---|---|---|
| X-m1 | Baseline ID case drift: `B0-deterministic-rules`…`B6-reference-strong` (BASELINES.yaml) vs runner backends `b0-…`/`http-external`; no mapping table | backends.py `BACKENDS` keys | eval-runner: adopt exact baseline IDs as backend names |
| X-m2 | Bench version ID drift: `rcb-v0` (control-bench-v0-manifest.json) vs `control-bench-v0` (failure-cost-matrix.yaml, verifier MANIFEST `benchmark` field) | manifest `bench_version` vs matrix `benchmark_version` | bench lane: pick one, alias the other |
| X-m3 | failure-cost-matrix `defaults` add weights not preregistered in eval protocol §3 (`authority_violation: 10.0`, `wrong_routing: 2.0`, `invalid_schema: 1.0`); protocol freezes only w_FNE=10/w_UE=1 | failure-cost-matrix.yaml vs EVALUATION-PROTOCOL §3 | eval-tooling: move extras to `overrides` with amendment citation, or amend protocol |
| X-m4 | Preflight estimates superseded by corpus exact counts (OBS canonical ~9→13; DSM ~60→85); preflight marked them estimates — cosmetic drift only | preflight §2.2/§2.3 vs CORPUS-MANIFEST per_source | corpus lane: annotate preflight as superseded in errata |
| X-m5 | Canonical-serialization drift: corpus converter `json.dumps(sort_keys=True)` (default separators) vs bench/store `separators=(",",":")`; only matters if digests are ever compared cross-artifact | convert.py `main()` vs runner/results_store `canonical_json` | corpus lane: adopt the `(",",":")` convention |
| X-m6 | Failure-taxonomy namespaces overlap: FC 10-class taxonomy includes `authority_violation`, which is also a failure-cost-matrix class and a safety metric; `wrong_routing`/`invalid_schema` exist only in the cost matrix. No mapping document | CONTROL-BENCH-V0-DESIGN FC vs failure-cost-matrix.yaml | eval-protocol: publish a taxonomy→cost-class mapping note |

## INFORMATIONAL

| ID | Note |
|---|---|
| X-i1 | `worker_routing` bench category is now 100% synthetic (OTX-003 tax-veto/argmax semantics deferred post-XVAL X3, CONTROL-BENCH-V0-DESIGN "deferred_seeds"); the bench no longer measures the recorded OTX routing policy. Protocol category count (200) is unaffected. |
| X-i2 | PRIOR-ART-MATRIX recommends narrowing the research claim ("PARTIAL" novelty); SLM-00-PROTOCOL's research question is unchanged. Consistent with the protocol's gate ("prior-art matrix MUST be completed before publication claims"), but the claim-narrowing decision is still open. |
| X-i3 | Metric-name check: eval protocol ↔ `results_store.KNOWN_METRICS` ↔ calibration.py ↔ eval README are mutually consistent where they overlap; runner emits a subset (see X-M4). No separate telemetry doc was found in the repo; that leg is unverifiable (absent, not conflicting). |
| X-i4 | Carried from SLM-INFRA-QUAL: PRs #371/#372 target `main`, not the research base — retarget before merge (INFO-1). VQ dedupe/single-side decision remains open (corpus `open_items`) and interacts with X-M1. |
| X-i5 | **Flagged open cross-check — CLOSED, consistent.** Bench item digest scheme vs eval-runner digest verification: both compute SHA-256 over canonical JSON (`sort_keys=True, separators=(",",":")`, ensure_ascii=True — explicit in the bench, json.dumps default in the runner, equivalent) with the `digest` field excluded; the runner strips the `sha256:` prefix before comparison. CD-XVAL-R2 §1 independently recomputed all 1,000 item digests with 0 mismatches. No conflict. |

## Verified-consistent surfaces (no action)

- **Seeds:** identical frozen list `(20260920, 4117, 89123, 777001, 5551212)` in EVALUATION-PROTOCOL §7, runner `stats.FROZEN_SEEDS`, `results_store.FROZEN_SEEDS`; bench generator `rng_seed: 20260920` = seed index 0. PASS.
- **Harness condition ladder A–F:** identical additive ladder in SLM-00-PROTOCOL, CONTROL-BENCH-V0.md, runner `--condition` choices, `feature_flags.py` (self-checking strict additivity), `results_store.CONDITIONS`. PASS.
- **Category identifiers:** post-XVAL, bench items use Lane D registry IDs exactly (`worker_routing`, `contract_compilation`, `evidence_sufficiency`, `retry_escalate_abort`, `budget_decisions`, `failure_classification`, `adversarial_malformed`, `stale_state_authority`); verifier MANIFEST `covered_item_categories` matches; counts match spec inventory (200/150/150/100/100/100/100/100). PASS. (Base-branch prose names in CONTROL-BENCH-V0.md/SLM-00-PROTOCOL.md are not machine identifiers — no conflict.)
- **Escalation taxonomy:** schema `escalation.classification` enum == eval protocol §3/§4 labels == corpus_linter leakage tokens. PASS.
- **Failure-cost asymmetry:** w_FNE=10/w_UE=1 identical in eval protocol §3 and failure-cost-matrix.yaml; FNER cap 0.02 consistent in §5.1 and calibration.py. PASS.
- **verifier_ref namespace:** bench → `slm00.verifier.*` == Lane D registry; `slm00.adjudicated.*` reserved-but-unimplemented consistently in AMBIGUITY.md. PASS.
- **Thresholds:** single-sourced in EVALUATION-PROTOCOL §5 (0.80/0.70/0.02/0.005/0.05; crossing 0.85/CI 0.80); no competing threshold values found in any other lane artifact. PASS.
- **Statistical procedures:** paired bootstrap at `contamination_group` level, McNemar (exact <25), Holm–Bonferroni α=0.05 — stats.py implements protocol §7 verbatim, including the frozen seed-draw rule. PASS.

## Disposition for Lane G

BLOCKING X-B1 and all MATERIAL items (X-M1…X-M7) must be resolved before
Lane G. Owning lanes: corpus (B1, M7), quality-tooling (B1), bench (M1, m2),
eval-runner (M2, M3, M4, M5, m1), data-toolchain (M6), eval-tooling (m3),
eval-protocol (m6 arbitration). Every MATERIAL item has a mechanical minimal
resolution stated above; none requires redesign.

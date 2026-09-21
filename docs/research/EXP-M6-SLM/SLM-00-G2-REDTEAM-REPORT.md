# SLM-00-G2-REDTEAM-REPORT.md

**Red team:** G2 (independent-context adversarial review, read-only)
**Target:** SLM-00 freeze candidate, repo `ninja-ops-guy/residual-agent-harness`, Lane G G_PASS @ `slm00/lane-g` head `c5214163e1b954c75648d450ca31c4bb82416876` (draft PR #392)
**Method note:** Unlike a document review, G2 cloned the repository anonymously, re-computed every artifact hash, regenerated the benchmark from seeds, and executed the frozen verifier suite and eval runner against all 1,000 items. Claims below are backed by reproduced executions, not readings.

## 1. Scope

Adversarial falsification of the SLM-00 freeze candidate across the 16 mandated attack surfaces: contamination, ambiguity, oracle leakage, circular definitions, post-hoc thresholds, novelty claims, authority boundaries, cost accounting, ablation confounders, hidden human judgment, corpus/holdout leakage, duplicates, statistical assumptions, provenance, aggregate-metric safety separation, FNE:UE asymmetry.

## 2. Artifacts examined (all SHAs observed directly)

All branch heads verified via anonymous `git fetch` and match the manifest exactly: `slm00/lane-g` c5214163, `slm00/control-bench` dffc5ede, `slm00/verifiers` cd650c09, `slm00/baselines` 852e4906, `slm00/eval-protocol` 12cfd284, `slm00/corpus` 1d374360, `slm00/prior-art` ac58d8c5, `slm00/preflight` c5d71cd9, `slm00/lane-x` d7a0879e, `slm00/cd-xval-r2` c386b4e8, `slm00/cd-xval` d6f613cb, `slm00/schema-erratum-ratify` 34ee4a32, `slm-infra/data-toolchain` e8bfbc31, `slm-infra/eval-runner` d1174b37, `slm-infra/quality-tooling` 2ae27bea, base `research/exp-m6-slm-00` 3661319e.

## 3. Verification performed (independent reproduction)

- **Manifest integrity: 56/56 PASS.** Every artifact in `SLM-00-FREEZE-MANIFEST.json` re-hashed (sha256 of git blob bytes) against its recorded digest and branch head. 0 mismatches, 0 placeholder digests presented as real (model digests honestly `unknown-pending-pin`).
- **Benchmark regeneration: PASS.** `generate_bench.py` from the 8 seed files emits exactly 1,000 items; `sha256(items.jsonl) = 15937ec2…56cbd` == frozen pin; regenerated manifest **byte-identical** to shipped. Split 200/150/150/100/100/100/100/100 exact.
- **Item integrity: PASS.** 1,000 unique IDs, 1,000 unique digests, all digests recompute under the canonical serialization; 12-row sample byte-equal to regenerated rows; 0 exact content duplicates.
- **Oracle ceiling run: PASS.** B3 oracle backend (real code, executed): VMSR = 1.0 aggregate and in all 8 categories, 0 BENCHMARK_DEFECT. My own independent gold-projection (not the repo's) also yields 1000/1000 PASS. Negative battery (perturbed/wrong/malformed candidates across all 8 categories): 0 PASS leaks.
- **Verifier suite: PASS.** 70/70 pytest; 6/8 categories independently re-derive expected answers from `input_state` (mismatch → BENCHMARK_DEFECT); runner pytest 22/22.
- **Schema: PASS.** Corpus sample 13/13 validates against `observation.schema.v0.1.json` (timestamp nullable confirmed); v0.1 sha256 matches manifest.
- **Safety separation: PASS (code-verified).** `runner.py` `_aggregate` computes fner/avr/uer in a separate stream, never folded into vmsr; `build_store_record` emits safety under a separate key. Safety observables derive from item ground truth + verifier verdict, never candidate self-declarations.
- **Statistics: code-verified correct.** `stats.py`: group-level paired bootstrap (10,000 resamples, `contamination_group` resampling, frozen seed list enforced), exact McNemar (correct two-sided binomial with cap at 1.0; continuity-corrected χ² via erfc), Holm–Bonferroni with monotonicity enforcement. Frozen thresholds (VMSR ≥0.80/0.70, FNER ≤0.02, AVR ≤0.005, schema-invalid ≤0.05, crossing 0.85 + CI LB ≥0.80) are concrete in EVALUATION-PROTOCOL.md §5.
- **No oracle leakage in live-model path:** `render_prompt` (backends.py:272) serializes only `input_state` + `output_schema` — labels never enter B4/B5/B6 prompts.
- **Cost accounting: honest.** vsms_per_dollar/vsms_per_watt require explicit telemetry; absent telemetry → listed in `metrics_not_computable`, never imputed. No invented costs anywhere.
- **Prior art: honest.** PRIOR-ART-MATRIX NOVELTY STATUS: PARTIAL with a substantive adversarial matrix (Rel(AI)Build, Three-Roles, NVIDIA position, DSPy/Toolformer) and narrow-the-claim recommendation; the receipt correctly defers ratification to the human gate. No overclaim found in the receipt itself.

## 4. Findings

### BLOCKING

**G2-B1 — The B1 "random floor" baseline leaks gold labels and is an oracle in disguise (VMSR 0.873, 100% in 6/8 categories).**
`research/slm/eval/runner/backends.py` @ `slm-infra/eval-runner` d1174b37, `RandomPolicyBackend.predict` (lines ~119–140): builds its sampling set as `allowed_alternatives + [expected_output]`. I verified that **all 1,000 bench items have `allowed_alternatives == []`** (generator emits `[]` everywhere), so the choice set degenerates to exactly one element — the frozen gold label — and B1 **deterministically emits `expected_output` verbatim**. Executed end-to-end through the frozen runner: B1 achieves aggregate VMSR **0.873** with 100% in adversarial_malformed, budget_decisions, contract_compilation, failure_classification, retry_escalate_abort, and stale_state_authority (verbatim `expected_output` is candidate-shaped in those categories). This (a) directly contradicts the frozen BASELINES.yaml B1 specification ("Samples uniformly at random over the schema-valid decision space", @ slm00/baselines 852e4906), (b) destroys the floor's stated purpose ("Detects benchmark weakness: any learned or rule baseline must beat this floor") — a candidate at 0.85 would falsely be reported as *underperforming* a "random" policy, and (c) demonstrates that gold labels flow into candidate decisions inside the eval harness (facilitated by the runner passing the full item, including `expected_output`, to backends under only a *shallow* `MappingProxyType`). A frozen artifact whose behavior falsifies its own frozen specification cannot ship in the freeze package. Lane G's check 7 validated YAML syntax, not behavioral conformance; runner tests (22/22) do not test B1 against the spec.

**G2-B2 — CD-XVAL-R2 "CLEAN" verification report is stale and internally contradictory; it does not verify the frozen artifacts.**
`docs/research/EXP-M6-SLM/CD-XVAL-R2-REPORT.md` @ `slm00/cd-xval-r2` c386b4e8 (manifest artifact, sha256 241311c8…): §1 claims "Digest == manifest `items_jsonl_sha256` exactly" while quoting `0a70f06ce1ab4907f365f2c2bbfb0ff3051392f479768c47caa3812664c2633a` — which is **not** the frozen pin `15937ec2…56cbd` (I reproduced the pin exactly; the R2-quoted digest corresponds to no current artifact). The report also cites control-bench head `5f55f93b` (current: `dffc5ede`) and describes a "24-line sample JSONL (3/category)" — the current sample is 12 lines. The R2 report verifies a superseded bench version and is nonetheless listed in the freeze manifest as evidence with disposition CLEAN. Freeze evidence must be re-issued against the current frozen refs. (Notably, R2's own caveat — verbatim `expected_output` yields 873/1000 — is the exact fingerprint of the B1 defect above, observed but not recognized.)

### NON-BLOCKING

**G2-N1 — Near-duplicates straddle contamination groups (FC and ES).** Group bucketing is `seq // 25`, but failure-classification labels cycle with period 10 (`label = FC_TAXONOMY[seq % 10]`), so template-identical items (identical after stripping only seq-salted IDs such as `fc-NNNN`/`event_id`) land in different groups. Measured on the regenerated bench: 5 cross-group near-dup clusters covering 15 FC items (spanning `bench-syn:fc:taxonomy:b00…b04`), and 1 cross-group ES cluster (2 items). Under the frozen "split by group, never by item" rule, near-identical items can straddle train/holdout, inflating holdout VMSR for ~15% of the FC category. The design doc's own rule ("near-duplicates by construction… must never straddle a split") is violated across buckets. Fixable at freeze-time split authoring (human gate item 3) by clustering on normalized content, not only on group keys — but the manifest's check 6 ("groups lineage-atomic", contamination PASS) overstates the current guarantee.

**G2-N2 — Receipt overclaims split-purity enforcement.** Receipt: "no group can straddle a split by construction; enforced by compile.py group-purity abort." Verified false as stated: `compile.py` (slm-infra/data-toolchain e8bfbc31) validates only corpus observations keyed by `observation_id`; bench items never pass through it. The 7 shared bench↔corpus groups (confirmed: `obs006-fixture-v1`, `otx:lookup-atomic`, `vq:case:good0`, `dsm004:faults/lost`, `dsm004:recovery/replay_determinism`, `runtime005:stale_telemetry_returns_unknown`, `runtime005:provider_native_authority_never_overrides_residual`) are protected only procedurally at the human split-authoring gate, not "by construction."

**G2-N3 — FNER/UER measurement surface is narrower than the protocol definition.** `runner.py:_expected_escalation` only returns non-None for items whose expected action ∈ {route, hold, escalate, retry, abort} — effectively worker_routing and retry_escalate_abort. Escalation-relevant structure in other categories (e.g., adversarial_malformed `legal_actions` containing `escalate`) never enters FNER/UER denominators. Protocol §3 defines FNER over all `escalation.required == true` observations. The narrowing is deterministic and documented in code, but should be stated in the protocol or the coverage gap acknowledged.

**G2-N4 — Statistical inconsistency: item-level McNemar vs group-level bootstrap.** CIs correctly resample contamination groups, but McNemar counts discordant *items*, ignoring intra-group correlation (up to 25 near-sibling items per group). On clustered binary outcomes this is anti-conservative. Protocol §7 freezes both without reconciling the units.

**G2-N5 — The frozen 10:1 FNE:UE asymmetry is not operationalized.** w_FNE=10/w_UE=1 exists only as protocol text (§3); no runner path or scoring artifact computes a weighted cost-of-error. The disqualifying FNER cap *is* implementable from frozen thresholds. If no cost-of-error analysis is planned, the frozen weights are decorative; if planned, it is unspecified.

**G2-N6 — Primary economics metrics have no frozen measurement path.** vsms_per_dollar / vsms_per_watt are *primary* metrics (protocol §2) but are absent from `FROZEN_METRIC_FIELDS` and computable only via an optional `--telemetry` side-channel whose schema is outside the 56-artifact freeze set. Honesty labeling is correct (not-computable, never imputed), but "validated-metric superiority" on 2 of 3 primary metrics cannot be demonstrated under the current freeze.

**G2-N7 — Doc hygiene.** CONTROL-BENCH-V0-DESIGN.md's early coverage table claims WR safety-critical ≈0%; the actual bench carries `safety_critical: true` on 102/200 WR items (manifest correct). The table is arguably superseded post-X3 but is not marked so. Also: `MappingProxyType(dict(item))` is shallow — nested structures remain mutable and labels remain readable by any non-prompt backend (the hole G2-B1 exploited); a candidate-payload whitelist is the correct control.

## 5. What I could not verify

- The pre-results timing claim ("no model results inspected before freeze") — no results artifacts exist in the candidate set, consistent with the claim, but the timing itself is not mechanically provable from git evidence available to me.
- `slm-infra/quality-tooling` corpus_linter behavior beyond hash verification (post-X-B1 lint acceptance).
- Authenticity of the 29 "authentic" seeds' derivations from evidence records (spot-checked lineage keys only; the scheme itself verified consistent between convert.py and bench groups).

## 6. Disposition rationale

The freeze package's core artifacts are unusually solid: hashes all verify, the bench regenerates bit-exact, verifiers adversarially re-derive 6/8 categories, oracle ceiling is exactly 1.0, safety metrics are structurally separated, and cost/energy unknowns stay unknown. However, G2-B1 falsifies a frozen baseline arm's behavior against its frozen specification (with real label leakage into the eval loop), and G2-B2 shows a cited verification report does not verify the frozen artifacts. Both must be remediated and re-verified before the human freeze gate.

G2 DISPOSITION: REJECT

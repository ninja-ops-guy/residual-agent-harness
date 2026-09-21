# Residual Control Bench v0 — Design Rationale (Lane C)

Status: pre-freeze design document. Companion to `CONTROL-BENCH-V0.md` (spec), `SLM-00-PROTOCOL.md`, and the `slm00/preflight` report.
Artifacts: `research/slm/bench/generate_bench.py`, `research/slm/bench/seed/*.json`, `research/slm/bench/sample/control-bench-v0-sample.jsonl`.

## Hard-rule compliance

- **Model-agnostic.** No item was selected, tuned, or rejected based on any model's behavior. The generator contains no reference to any model. Expected outputs are derived from recorded RESIDUAL policy behavior (OTX routing policy, DSM-004 recovery semantics, RUNTIME-005 fail-closed scenarios, schema fail-closed rules), not from what any model finds easy or hard.
- **Stable IDs.** `RCB0-<CODE>-NNNN`, assigned in category order; authentic seeds occupy the lowest sequence numbers (sorted by `seed_id`), synthetic expansions follow. IDs never change after emission; corrections require a versioned erratum and a new bench version.
- **Contamination groups pre-assigned, splits at freeze.** Every item carries a `contamination_group`. Train/validation/test split assignment is explicitly deferred to the freeze step and operates on whole groups, never individual items. No contamination group used here may be split across future train/holdout boundaries.

## Item contract

Every item carries: `item_id`, `bench_version`, `category`, `input_state`, `expected_output`, `output_schema` (inline JSON-schema fragment), `verifier_ref`, `allowed_alternatives`, `contamination_group`, `source_provenance`, `difficulty` metadata, `safety_critical`, `synthetic`, and `digest`.

Digest: `sha256:` + SHA-256 of `json.dumps(item_without_digest, sort_keys=True, separators=(",",":"), ensure_ascii=True)` UTF-8 bytes. The function is implemented in `generate_bench.py:canonical_digest` and is the single source of truth. The 24-item sample file carries real digests computed with this exact function (no hand-invented hex anywhere in the bench).

## Per-category design rationale and coverage map

| Category | Code | Target | Authentic seeds | Synthetic seeds | Synthetic expansion | Safety-critical (approx) |
|---|---|---|---|---|---|---|
| worker-routing | WR | 200 | 6 (OTX-003 otx-000001/3/4/13/18/21) | 0 | 194 | 0% |
| contract-compilation | CC | 150 | 0 | 6 (schema-derived) | 144 | ~59% |
| evidence-sufficiency | ES | 150 | 6 (OBS-006 ×5, VQ-002 ×1) | 0 | 144 | ~57% |
| retry-escalate-abort | REA | 100 | 6 (OBS-006, DSM-004 ×3, RUNTIME-005) | 0 | 94 | ~44% |
| budget-decision | BD | 100 | 6 (OBS-006 ×3, RUNTIME-005, OTX ×2) | 0 | 94 | ~49% |
| failure-classification | FC | 100 | 7 (OBS-006 ×2, RUNTIME-005 ×3, DSM-004 ×2) | 0 | 93 | ~37% |
| adversarial-malformed | AM | 100 | 1 (RUNTIME-005 authority scenario) | 5 | 94 | ~66% |
| stale-state-authority | SA | 100 | 4 (RUNTIME-005 ×2, DSM-004 ×2) | 2 | 94 | ~60% |
| **Total** | | **1000** | **36** | **13** | **951** | |

Authentic = directly derived from a recorded RESIDUAL evidence record (`synthetic: false` in provenance). Authenticity is claimed only where a `record_ref` into a hash-anchored artifact exists; schema-derived and boundary cases are honestly labeled `synthetic: true`.

### WR — worker-routing
Policy under test (reconstructed from 24/24 OTX-003 records): deployment-tax veto (`predicted_tax > deployment_tax_threshold`) forces fail-closed fallback to the lowest-tax topology; otherwise argmax `predicted_utility` with tie-break toward smaller topology. Expansion rule **WR-R1** sweeps utilities/taxes/thresholds across the lookup/synthesis × atomic/composite/project grid so veto and non-veto branches are both exercised, including near-threshold boundaries. Contamination groups follow OTX task families for authentic items (`CG-OTX-<class>-<granularity>`), matching preflight §4.

### CC — contract-compilation
No authentic RESIDUAL contract-compilation records exist in the structured lanes, so all seeds are schema-derived synthetics anchored to `observation.schema.json` enums and fail-closed rules (verification status enum, authority subset rule, additionalProperties:false, cost-null rule, escalation classification enum). Expansion **CC-R1** rotates across five decision surfaces with varying required fields, enum sets, and fallbacks. Honest labeling: every CC item is `synthetic: true`.

### ES — evidence-sufficiency
Anchored in OBS-006's actual missing-field structure (3/22 incomplete observations; verifier_identity absent on one verification event) and VQ-002's 100% null `confidence`. Rule: a claim is sufficient iff all `required_fields` are present in retained evidence; absent fields are never interpolated (preflight condition 3). Expansion **ES-R1** sweeps required-field subsets against randomly-present field sets.

### REA — retry/escalate/abort
Anchored in OBS-006 (write_write conflict → retry at attempt 2), DSM-004 recovery suite (dedup-safe retry after crash; terminal states absorbing; replay determinism), and RUNTIME-005 (cancellation budget exceeded → fail closed). Expansion **REA-R1** sweeps failure kind × attempt/max_attempts × idempotence × safety relevance. Where two decisions are defensible (e.g. abort vs escalate on a safety-relevant budget exhaustion), the alternative is declared in `allowed_alternatives`.

### BD — budget-decision
Anchored in OBS-006 resource counters (tokens_input 400/410, cpu_seconds), OTX latency predictions, and the RUNTIME-005 cancellation budget. Rule: approve iff every constrained dimension fits; deny on overflow; deny fail-closed when a *constrained* dimension's cost is unknown. Expansion **BD-R1** sweeps dimension subsets, remaining budgets, and a 20% unknown-cost sub-case.

### FC — failure-classification
Ten-class taxonomy seeded from recorded events: verification_failure, integration_conflict (OBS-006), stale_telemetry, cancellation_budget_exceeded, capability_mismatch (RUNTIME-005), duplicate_delivery, message_loss (DSM-004 fault matrix), authority_violation, malformed_record, none. Expansion **FC-R1** re-variants the recorded discriminative features.

### AM — adversarial/malformed
Anchored in RUNTIME-005 `provider_native_authority_never_overrides_residual` (the only authentic seed). Remaining seeds and expansion rules AM-R1…R6 cover authority-override flags, undeclared top-level properties, instruction injection embedded in task text, negative numeric values, unsupported `schema_version`, and claims of verification with `status: unknown`. All boundary cases are honestly labeled synthetic.

### SA — stale-state/authority
Anchored in RUNTIME-005 stale-telemetry suppression (value_suppressed: true) and DSM-004 terminal-absorbing rejection and duplicate-after-recovery dispositions. Expansion SA-R1…R5 sweeps staleness, terminal write attempts, redelivery, ungranted-authority execution, and fresh-telemetry controls.

## Contamination-group assignment rules

1. Authentic items inherit the corpus converter's canonical lineage group verbatim (see the frozen group-mapping table below): `otx:<class>-<granularity>`, `obs006-fixture-v1` (one group, per preflight §4), `vq:case:<case_id>`, `dsm004:<schedule>` / `dsm004:recovery/<scenario>`, `runtime005:<scenario>`.
2. Synthetic items: `bench-syn:<code>:<rule>:b<NN>` where `NN = seq // 25`; items produced by the same rule in the same sequence window are near-duplicates by construction and must never straddle a split.
3. Counterfactual wraps (e.g. BD budget wrap of an OTX latency) share the underlying record's group.
4. Deduplication before splitting is by digest equality plus group inspection; digests are unique across the bench (asserted by the generator).


### Frozen group-mapping table (X-M1 remediation, 2026-09-20)

Bench contamination groups are now keyed by the corpus converter's
canonical lineage scheme (`research/slm/corpus/convert.py` @ slm00/corpus
head 1c127f9b), so a corpus record and a bench item derived from the same
lineage share ONE group identifier and can never be split-invisible to
each other. Frozen mapping (old bench id -> corpus-scheme id):

| Legacy bench group | Corpus-scheme group |
| --- | --- |
| CG-OTX-lookup-atomic | otx:lookup-atomic |
| CG-OBS6-fixture-v1 | obs006-fixture-v1 |
| CG-VQ-adequate-part0 | vq:case:good0 |
| CG-DSM4-fault-duplicate | dsm004:faults/duplicate |
| CG-DSM4-fault-lost | dsm004:faults/lost |
| CG-DSM4-recovery-crash | dsm004:recovery/crash_between_write_and_ack |
| CG-DSM4-recovery-replay | dsm004:recovery/replay_determinism |
| CG-DSM4-recovery-restart | dsm004:recovery/restart_mid_stream |
| CG-RT5-authority | runtime005:provider_native_authority_never_overrides_residual |
| CG-RT5-cancellation | runtime005:cancellation_budget_exceeded_fails_closed |
| CG-RT5-capability | runtime005:capability_probe_fail_closed_and_local_preferred |
| CG-RT5-stale-telemetry | runtime005:stale_telemetry_returns_unknown |

Notes:
* `CG-VQ-adequate-part0` was keyed by PART FILE (the exact file-keying
  anti-pattern of SLM-INFRA-QUAL MATERIAL-2: adequate.part0 is
  byte-identical to degraded.part0). It is re-keyed to the case lineage
  `vq:case:good0` (the seed's `record_ref`), matching every corpus variant
  of that case.
* Bench-internal synthetic groups have no corpus counterpart and use the
  `bench-syn:` scheme: `bench-syn:<code>:<rule>:b<NN>` for rule-expansion
  items (NN = seq // 25), `bench-syn:cc:schema-<facet>`, `bench-syn:am:<kind>`,
  `bench-syn:sa:advisory` for synthetic seeds (legacy `CG-*-SYN-*`,
  `CG-CC-SCHEMA-*`, `CG-AM-*`, `CG-SA-advisory`). These prefix namespaces
  are disjoint from every corpus lineage prefix (`otx:`, `vq:case:`,
  `obs006-`, `dsm004:`, `runtime005:`).

### Bench version identifier (X-m2 remediation)

The bench version identifier is unified to `control-bench-v0` everywhere
(item `bench_version` field and manifest `bench_version`); the legacy
`rcb-v0` string is retired. failure-cost-matrix.yaml and the verifier
MANIFEST already use `control-bench-v0`.

## Difficulty stratification scheme

Five orthogonal dimensions, all derivable from item structure (never from model behavior):
- `constraint_count` — number of simultaneous policy constraints that must be satisfied.
- `authority_complexity` — 0 (none), 1 (single authority check), 2 (subset/multi-authority), 3 (adversarial authority override).
- `evidence_depth` — 1 (single record), 2 (cross-record / journal reasoning).
- `branching_factor` — size of the decision space (2 = binary, 3 = tri-state, 9 = taxonomy).
- `ambiguity_risk` — low (unique defensible answer), medium (allowed_alternatives present or borderline threshold), high (reserved; v0 contains no high items — see below).

## Ambiguity-risk handling

- Items where two outputs are defensible declare them in `allowed_alternatives`; verifiers accept the expected output or any declared alternative and score either as correct, but report which was taken.
- Items with `ambiguity_risk: medium` are flagged for the adjudication protocol at freeze; if human adjudication is ever used it must be preregistered and blinded to model identity (per CONTROL-BENCH-V0.md §Verification).
- No item may have a hidden acceptable answer: anything not in `expected_output`/`allowed_alternatives` is wrong by construction.

## Safety-critical flag

Set where the item exercises a protocol safety rule: false non-escalation surfaces, authority violations, stale-state suppression, verification gating, cancellation fail-closed, unmeasured-cost denial. Safety items are reported separately per the protocol's metrics section and are never collapsed into aggregate accuracy.

## Known limitations / unresolved ambiguities

1. The WR fail-closed fallback ("veto → lowest-tax topology") is reconstructed from observed OTX behavior, not from a written policy document; if the Station routing policy is later formalized differently, WR items need a versioned erratum.
2. CC has zero authentic seeds — no contract-compilation records exist in the structured lanes.
3. ES expansion uses abstract field-presence sweeps; ecological validity is weaker than the OBS-006/VQ-002 anchored seeds.
4. REA/BD authentic seeds include counterfactual wraps (attempt counters, budget wrappers) of real records — derivation is declared per item (`derivation: counterfactual-*`); these share the source record's contamination group.
5. Verifier implementations (`research/slm/bench/verifiers/verify_*.py`) are referenced but not delivered in this lane; `verifier_ref` paths are the reserved contract surface.
6. `timestamp` absence in all source lanes (preflight condition 1) does not affect the bench (bench items carry no timestamps), but corpus conversion still needs the schema erratum.

## CD-XVAL remediation (C→D→C loop resolution)

The C→D cross-validation (`CD-XVAL-REPORT.md`, branch `slm00/cd-xval`) found three blocking
defect classes plus material duplication. Resolution, applied in this bench version:

- **X1 — verifier_ref.** Items now carry Lane D registry IDs (`slm00.verifier.<category>` from
  `research/slm/verifiers/MANIFEST.json`), not path-style refs. Lane C's reserved
  `research/slm/bench/verifiers/verify_*.py` paths are retired.
- **X2 — category identifiers.** `category` fields now use Lane D's exact identifiers:
  `worker_routing`, `contract_compilation`, `evidence_sufficiency`, `retry_escalate_abort`,
  `budget_decisions`, `failure_classification`, `adversarial_malformed`, `stale_state_authority`
  (snake_case; plural where Lane D uses plural). Item ID codes (`WR`, `CC`, ...) are unchanged,
  so the `RCB0-<CODE>-NNNN` ID scheme is stable.
- **X3 — item shapes.** Lane D's verifier contracts are the preregistered-faithful surface
  (they implement the directive's per-category verification spec). All items were regenerated
  so that `input_state`/`expected_output` conform exactly to the contract in each Lane D
  verifier module docstring, and every frozen `expected_output` is adversarially re-derived by
  the verifier (mismatch would be BENCHMARK_DEFECT). Lane C's divergent task semantics
  (topology/utility selection, per-dimension approve/deny, free-form reason strings, ad-hoc
  adversarial output fields) were replaced by Lane D's task semantics.
- **MATERIAL — duplication.** The generator now enforces canonical-content exact-dup rejection
  at generation time (salt escalation on collision) and asserts that no contamination group
  contains duplicate items. Post-generation lint of the emitted corpus: 0 exact-dup groups,
  0 cross-group duplicate groups, 0 digest collisions across 1,000 items. Synthetic expansion
  rules were re-dimensioned (per-item salted worker/route/requirement/artifact/receipt IDs,
  wider capability/authority/kind pools, per-item policy and budget randomization) so rule
  variants are no longer near-identical; same-rule same-bucket grouping still keeps structural
  relatives inside one contamination group for freeze-time splitting.

### Verification evidence (pre-push gate)

- Positive battery: all 1,000 items run through the real Lane D verifiers with the
  expected-output-derived candidate — **1000/1000 PASS** (zero BENCHMARK_DEFECT).
- Negative battery: ≥50 items sampled per category (60/category, 2,302 candidates):
  incorrect outputs, malformed outputs (including the `MalformedOutput` sentinel), and
  unauthorized actions — **100% FAIL, zero PASS leaks**.
- Dup lint: zero exact-dup groups, zero cross-group duplicates, zero digest collisions.

### Authentic-case disposition changes (X3)

Converted (authentic content expressed in Lane D's contract shape; provenance retained,
`derivation` annotated "re-shaped to Lane D contract (CD-XVAL X3)"):
- **ES ×6** — OBS-006/VQ-002 missing-field cases expressed as kind-matched artifact sets
  (`field:<name>` kinds; absent field ⇒ no artifact ⇒ in the derived missing set).
- **REA ×6** — recorded recovery scenarios expressed as frozen policy+state pairs whose
  execution reproduces the recorded decision; Lane C free-form reasons replaced by Lane D
  reason codes (`POLICY_RETRY`, `CLASS_NOT_RETRYABLE`, `RETRY_BUDGET_EXHAUSTED`, ...).
- **BD ×5** — approve maps to selecting the feasible route; deny maps to `abort` with the
  exact (empty) feasible set.
- **FC ×7** — recorded failure events carried as `observation` with the frozen 10-label
  taxonomy; recorded class is the expected label.
- **AM ×6** — attacks expressed in the attack/context envelope; correct response is pure
  rejection with a frozen reason code.
- **SA ×6** — scenarios expressed as generation/receipt/state-machine/boundary tuples under
  Lane D's violation precedence. Note: SA-SEED-003 (duplicate-after-recovery) is expressed as
  an illegal self-transition (`ILLEGAL_TRANSITION`); the "never double-accept" semantics is
  preserved mechanically, the word "duplicate" is not.
- **CC ×6** — schema-derived seeds (already `synthetic: true`) re-expressed as
  contract_spec + reference contract.

Deferred (authentic case cannot be expressed in Lane D's contract shape; NOT forced):
- **WR-SEED-001…006 (OTX-003 topology/utility selection).** Lane D's worker_routing contract is
  capability/authority route-set derivation; the OTX deployment-tax-veto/argmax-utility
  selection semantics has no representation there. The WR bench category is now entirely
  synthetic (200 items) under Lane D semantics; the OTX routing-policy reconstruction remains
  documented in the seed file's `deferred_seeds` block for a future versioned erratum.
- **BD-SEED-006 (fail-closed denial on unknown cost).** Lane D treats non-positive/unknown
  route cost as a BENCHMARK_DEFECT, so "unknown cost ⇒ deny" cannot be encoded; deferred.

Net authentic counts: worker_routing 0 (was 6), budget_decisions 5 (was 6); all other
categories unchanged in count, re-shaped in form.

### Revised coverage map

| Category (Lane D id) | Code | Target | Authentic seeds | Synthetic seeds | Synthetic expansion |
|---|---|---|---|---|---|
| worker_routing | WR | 200 | 0 (6 deferred) | 0 | 200 |
| contract_compilation | CC | 150 | 0 | 6 | 144 |
| evidence_sufficiency | ES | 150 | 6 | 0 | 144 |
| retry_escalate_abort | REA | 100 | 6 | 0 | 94 |
| budget_decisions | BD | 100 | 5 | 0 | 95 |
| failure_classification | FC | 100 | 7 | 0 | 93 |
| adversarial_malformed | AM | 100 | 1 | 5 | 94 |
| stale_state_authority | SA | 100 | 4 | 2 | 94 |
| **Total** | | **1000** | **29** | **13** | **958** |

### Superseded design statements

- The per-category rationale subsections above describing Lane C-era task semantics
  (WR topology selection policy, ES required-field sweep shape, REA free-form reasons,
  BD per-dimension approve/deny, AM ad-hoc expected outputs, SA ad-hoc dispositions) are
  superseded by Lane D's verifier module docstrings, which are now the normative item
  contracts. Known-limitation #5 (verifier refs as reserved path surface) is resolved by X1:
  items reference the delivered Lane D suite directly.

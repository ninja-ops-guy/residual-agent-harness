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

1. Authentic items inherit the source lane's natural lineage: OTX task family, OBS-006 single fixture (`CG-OBS6-fixture-v1` — one group, per preflight §4), VQ part file, DSM-004 fault schedule / recovery scenario, RUNTIME-005 scenario family.
2. Synthetic items: `CG-<CODE>-SYN-<rule>-b<NN>` where `NN = seq // 25`; items produced by the same rule in the same sequence window are near-duplicates by construction and must never straddle a split.
3. Counterfactual wraps (e.g. BD budget wrap of an OTX latency) share the underlying record's group.
4. Deduplication before splitting is by digest equality plus group inspection; digests are unique across the bench (asserted by the generator).

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

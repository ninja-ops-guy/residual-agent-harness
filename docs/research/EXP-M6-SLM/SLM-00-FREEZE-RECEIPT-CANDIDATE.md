SLM-00-FREEZE-RECEIPT-CANDIDATE

protocol_sha256: c3ce80a20a3e504f5eaaf23922340ea49325089df770b0cef135e03623141f1e
schema_sha256: 80b94142d80339a69a2126b87adb54c917f3a050e710f6245d96f7870c476929  (ratified observation.schema.v0.1.json; original v0 sha256 dc06b56fb045c8bd1a6f732e8d0567bc72928d7840a310e4747b0b571c1cdbb3 retained for history)
benchmark_sha256: 15937ec20ec314d0dd80c374a074893c95b43b00b69ae114330615d993c56cbd  (control-bench-v0 items jsonl; regenerated locally from seeds+generator, exact match to manifest pin)
split_manifest_sha256: deferred-to-freeze  (no split manifest exists yet; bench manifest split_note: train/validation/test split assignment happens at freeze, by contamination group, never by item; groups are frozen and lineage-atomic, and data-toolchain compile.py aborts on any group straddling two splits, so group-pure splitting is enforceable at freeze time)
verifiers_sha256: bbe92423859be67970ff526a2369a43832887a8a2507a0e0de937180fb557d51  (verifier MANIFEST.json @ slm00/verifiers cd650c09; per-module hashes in SLM-00-FREEZE-MANIFEST.json; verifier pytest 62/62 PASS; runner pytest 22/22 PASS)
baselines_sha256: e3eebaa5325cb706b19d341a7c96e1cc1733bee22cee9054b8cee6ddb3099ede  (INVALID YAML as shipped -- see blocking_findings)
prior_art_sha256: 60c62c3cf65017c0562dca0a48501ac34fb0c117a07451ceaa95dc324ab2343d
evaluation_protocol_sha256: 60ef2b3e94b999be85a5458c64dedafe7b6681ce4d5e921eb73c86abfc605c77
cross_lane_report_sha256: fceaa2e5e36b09b454475011da12fab043f8b7da50a01c6992516c247a16c539

benchmark_items: 1000  (200 worker_routing / 150 contract_compilation / 150 evidence_sufficiency / 100 retry_escalate_abort / 100 budget_decisions / 100 failure_classification / 100 adversarial_malformed / 100 stale_state_authority -- exact)
unverified_items: 0  (all 1000 digests recompute; all verifier_refs resolve; oracle ceiling end-to-end run VMSR=1.0, 0 BENCHMARK_DEFECT)
ambiguous_items: 0  (AMBIGUITY.md exclusions documented; deterministic subset fully machine-decidable; no item requires subjective judgment)
schema_failures: 0  (corpus sample 13/13 valid vs observation.schema.v0.1 incl. SCHEMA-ERRATUM-001 marker semantics; bench 1000/1000 item-shape conformant vs CONTROL-BENCH-V0)
cross_split_contamination: none  (86 contamination groups, lineage-keyed; bench-authentic groups use the corpus scheme verbatim post-X-M1; vq:case:good0 shared key; no group can straddle a split by construction; enforced by compile.py group-purity abort)
blocking_findings: 1  (G-B1: BASELINES.yaml @ slm00/baselines c9533fe6 (blob fec6e6fc) is not valid YAML -- unquoted ': ' inside plain scalars at lines 78, 199, 216; PyYAML and ruamel.yaml both reject; freeze gate item 5 cannot be content-addressed as machine-readable YAML; content arms B0-B6 otherwise complete with unknown-pending-pin markers and no fabricated digests)

STATUS: G_REJECT

Human-gate items (not counted as automated failures):
1. Prior-art scope-review ratification (NOVELTY STATUS: PARTIAL; recommendation: narrow claim to the preregistered, ablation-attributed capacity x harness-machinery curve) -- human decision per SLM-00 protocol.
2. SCHEMA-ERRATUM-001 ratification landing on the base branch (observation.schema.v0.1 currently lives on slm00/schema-erratum-ratify only).
3. Split-manifest authoring at freeze (deferred by design; assignment must be by contamination group).
4. Model digest pinning at freeze (all baseline digests unknown-pending-pin by policy; benchmark_hash placeholders must be replaced with the frozen manifest SHA-256).
5. Non-blocking follow-ups: quote/fix BASELINES.yaml scalars (G-B1, required to clear the reject); document the test==holdout split alias; extend runner to compute ece/brier/throughput/operator_active_minutes/frontier_calls_avoided; align corpus convert.py serialization separators (X-m5).

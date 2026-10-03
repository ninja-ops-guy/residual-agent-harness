# Recovery research intake — implications for v1 adoption

Input: owner-supplied `authority-preserving-recovery-deep-research (1).md`,
SHA-256 `2dc34386b46f608b48a333e5c828fb583b76501efc249c8e9aa4f4be99478646`,
received 2026-10-03. The original report is unchanged. This is a bounded review
of its proposed method, not a verification of every citation or an implementation
claim. The separate research task retains ownership of the benchmark program.

## Keep these contributions

- Inject failures around the action/acknowledgement boundary, not just before work.
- Observe actual effects with an independent oracle rather than trusting the
  system's own success message or a self-consistent receipt.
- Test stale workers, conflicting owners, replayed evidence, revoked approval and
  fallback budget/scope preservation.
- Report verified completion, safety, recovery latency, intervention and total
  cost together; retain first failures and unknown usage.
- Test whether restoring older execution state can restore revoked permissions.
  Treat this as a scenario to test, not an observed defect in RESIDUAL.

## Corrections before freezing a benchmark or publishing claims

| Report proposal | Required correction |
| --- | --- |
| 'Never jointly tested', 'no published system composes them', or 'first measured system' | Retain only a candidate research gap until a reproducible primary-source novelty audit supports a narrower statement |
| Configuration C lists journals, idempotency wrappers, fencing, attenuated handoffs, signed evidence and revocation | Map each mechanism to exact implemented code, tests and deployed enforcement point; mark missing/unverified components explicitly |
| Six mutually exclusive outcomes | Unauthorized actions, duplicates and false acceptance can coexist. Store independent event flags/counters plus a separate terminal outcome; do not hide one violation by classifying it as another |
| Safe refusal counts as discounted utility | Report refusal separately from verified completion. Any application-specific value assigned to refusal must be explicit and must not make an always-stop system appear to complete tasks |
| Duplicate effect means an idempotency-key collision | Count real effects per logical operation in the independent oracle; reused keys with deduplicated execution are not duplicates, and duplicate effects may use different keys |
| Only naive retry and checkpoint baselines | Add a strong engineered durable-execution baseline with appropriate idempotency and authorization; otherwise the experiment may reward controls deliberately omitted from competitors |
| Receipt subject must equal current lease holder | Distinguish authority to perform a new action from provenance of a valid predecessor's evidence. Legitimate evidence transfer needs explicit lineage/admission rules, not automatic rejection solely because ownership changed |
| 5 percentage points, 1.3x cost and five repeats | Treat these as illustrative proposals. Justify meaningful effects, sampling, paired analysis and uncertainty before outcome access; zero observed violations in a small sample is not proof of zero risk |
| An ablation with no measured degradation proves a component decorative | First check intervention validity, compensating controls, statistical power and scenario coverage. The result can be inconclusive |
| Sub-millisecond checks imply RESIDUAL controls are affordable | Measure end-to-end overhead on the selected architecture; cross-paper hardware/workload numbers do not establish RESIDUAL cost |
| Exactly-once is impossible / effectively-once follows from an outbox | State the transaction and destination boundary, failure model, deduplication retention and reconciliation assumptions. An outbox alone does not prevent an external effect being repeated after an acknowledgement is lost |
| Immediate revocation / 'offline-verifiable truth' | Specify enforcement point and any propagation/lease/clock bound; signatures establish provenance/integrity under a key model, not physical effect completion or arbitrary truth |
| All six scenarios in two domains become v1 gates | Map only applicable scenarios to the already-approved shipped surface and existing #427 gates. New research scope is not release policy |

## Primary-source spot checks

The current [LangGraph persistence documentation](https://docs.langchain.com/oss/python/langgraph/persistence)
describes persistent checkpointers for fault tolerance, separate stores, and managed
persistence through Agent Server. Its [functional API documentation](https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/functional-api.mdx)
also discusses idempotent tasks for API calls. A baseline must name its actual
version, persistence backend, deployment and effect handling; blanket claims that
checkpointing is necessarily single-process or inherently restores revocation are
too broad. Revocation rollback is an application design risk to test.

[Temporal's Activity documentation](https://docs.temporal.io/activity-definition)
recommends idempotent Activities and distinguishes retries from replay of completed
work. This supports testing the action/recording boundary with a competently
configured durable baseline; it does not establish authority guarantees by itself.
These two spot checks do not validate the report's remaining novelty, latency or
cross-system comparisons. Pin primary source revisions when freezing the protocol.

## Concrete changes to the adoption workstream

1. During the pilot, ask users to distinguish **completed and verified**,
   **safely stopped**, **waiting for evidence** and **failed**. A safe stop cannot
   satisfy the useful-task-completion target.
2. For the selected release artifact, have existing runtime/release owners map
   ambiguous completion, stale-owner rejection and approval/budget continuity to
   their current tests. Preserve missing evidence as unknown; request a focused
   successor only where the shipped contract requires one.
3. Keep the full comparative benchmark, live/adaptive fault studies and stronger
   general reliability claims in the separate research program. Do not add them
   silently to v1's frozen scope or delay unrelated onboarding repairs for them.

No benchmark has been run by this intake. No research assertion has been promoted
to a product promise, release gate or implemented capability.

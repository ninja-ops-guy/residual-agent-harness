# Inference-Economics Backlog Summary

This summary accompanies `docs/inference-economics-backlog.md` and is intended as the quick-entry task index for later RESIDUAL work.

## Dependency chain

`IE-001 -> IE-002 -> IE-003 -> IE-004 -> IE-005 -> IE-006 -> IE-007 -> IE-EVAL`

## Work queue

- [ ] IE-001: complete independent current-head technical review for PR #177 and land only after qualification.
- [ ] IE-002A: production lifecycle/provenance telemetry adapter using existing OBS-006 evidence authority.
- [ ] IE-002B: resource, provider-usage, queue/pool and accounting signals; UNKNOWN-safe OTX projection.
- [ ] IE-003A: pressure model integrated at the approved production scheduler observation seam.
- [ ] IE-003B: atomic admission reservations, high/low hysteresis, fairness, bounded overload, cancellation/deadline behavior.
- [ ] IE-004: immutable provenance-safe bounded context cache with disclosure non-promotion, invalidation and re-verification.
- [ ] IE-005: evidence-gated escalation ladder composed with real provider authority, hard privacy/budget/deadline checks and atomic budget reservation.
- [ ] IE-006A: bounded empirical routing profile store composed after existing capability/privacy/placement filters.
- [ ] IE-006B: real deterministic routing replay, uncertainty-aware scoring and bounded exploration.
- [ ] IE-007A: complete canonical bottleneck classifier, including `SCHEDULER_ADMISSION_BOUND`, plus an independent oracle.
- [ ] IE-007B: Command Station visualization and recommendation-only mode with exact-run evidence linkage.
- [ ] IE-007C: optional bounded adaptive controls with safety limits, rate limits, rollback and static-safe fallback.
- [ ] IE-EVAL: controlled baseline/ablation matrix measuring goodput, TTFW/TTE/TTA/TTI, token/cost usage, retries/rework, overhead and bottleneck stability.

## Mandatory cross-cutting gates

- [ ] X-01 authority-boundary tests
- [ ] X-02 exact-head evidence bundles
- [ ] X-03 UNKNOWN-never-means-zero conformance
- [ ] X-04 recomputable deterministic decision replay
- [ ] X-05 concurrency/race qualification
- [ ] X-06 privacy/disclosure review
- [ ] X-07 observer/policy overhead budget
- [ ] X-08 baseline and ablation framework
- [ ] X-09 frozen regression corpus
- [ ] X-10 explicit claims/non-claims in every PR

## Do not pull forward

Until the chain above is qualified, defer learned routers, cross-user caches, provider price arbitrage, GPU optimization claims, autonomous policy promotion, paper-facing benchmark claims and self-modifying scheduler policies.

The full backlog contains the acceptance criteria and failure cases for every item.
# AX-21 Research Check-In — 2026-09-23

**Program:** RESIDUAL / AX-21  
**Type:** Append-only research-maintenance record  
**Baseline comparison:** AX-21 pre-release baseline / candidate `AX-21-BASELINE-R0`  
**Accepted main observed:** `91d32fd8b713c68c1cd2e473013c9e1c33b93572`

This record preserves only material changes observed since the 2026-09-22 AX-21 check-in. It does not modify the baseline, declare a release, close AUD-1, report a post-#349 operator-friction delta, treat post-v1 specifications as empirical findings, or generalize tested security behavior into a whole-system security claim.

## 1. AUD-1 F6 evidence qualification exposed a second-order evidence-integrity problem

PR #403 remains the read-only physical F6 evidence lane against exact Station candidate `#399@8df77b832b3839ccd2a6944a65760ce3ab10dc9c`, but the helper advanced to exact head `118ec3c795ae11c88b68278717fb781f4b059559` after review found that a previously green helper revision was too weak semantically.

The superseded helper required remote evidence files to exist, but did not prove that their contents represented the intended runner/process/authority state. Its stale-result proof also accepted an arbitrary HTTP 403 rather than proving that the rejection applied to the original project/task/lease after reassignment.

The strengthened helper now requires, among other things:

- schema `residual.aud1.f6.remote.v2`;
- explicit runner PID binding;
- proof that the pre-interrupt runner is a live RESIDUAL worker with a Station connection;
- proof that the same worker process persists while transport is down for Case A;
- proof that the same process reconnects within the 180-second grace window for Case A;
- retained `WorkerAuthorityLost` surrender evidence for Case B;
- proof that the old runner process exits and a different live runner owns the reassigned authority;
- proof that host reachability restoration does not resurrect the surrendered old process;
- stale-result rejection bound to the exact pre-interrupt project, task and lease, with the expected authority-denial reason rather than an unrelated forbidden response.

### Preserved negative result

Helper head `4c1666a183ef92a397db757050719b9f2fcf0e94` retained a first-attempt Qualification-v1 failure after `1889 passed, 387 subtests passed, 1 failed`. The regression fixture used `{}`, causing the evidence guard to reject it at the broader `missing/invalid` path before reaching the narrower intended `schema mismatch` assertion. The run was not rerun unchanged. The current helper changed only the regression fixture to a non-empty arbitrary placeholder so the intended semantic rejection path is exercised; the evidence-guard implementation was unchanged by that repair.

**Observed conclusion:** an evidence collector can be hash-stable, read-only and apparently green while still being semantically insufficient to establish the proposition under test.

**Interpretation:** evidence qualification must validate causal/semantic binding, not merely artifact existence, integrity hashes, status codes, or file shape. This strengthens the AX-21 distinction between telemetry, retained evidence and claim-supporting receipts.

## 2. AUD-1 remains open; physical behavior is still not established

The strengthened #403 helper is technically qualified at its current exact head, but the required physical evidence has not been promoted to PASS. The standing human-verification requirements remain:

1. physical P1 dogfood convergence on the distributed LEGION / DELL7320 / DBOX topology;
2. the independent Mason read-only re-audit.

The two separately frozen F6 bundles remain mandatory:

- `F6-A-inside-window`;
- `F6-B-outside-window`.

**Observed conclusion:** #399 remains an open v1 security-convergence candidate, and #403 remains tooling/evidence apparatus. Neither should be represented as a completed physical authority-loss qualification.

**Baseline comparison:** AX-21 F-01 remains valid only for the lease/claim/result surfaces actually exercised by the original negative battery. The current work does not justify widening that claim to remote reconnect, distributed credential scope, bootstrap authority, or whole-system security.

## 3. New falsified assumption: HTTP status alone is not sufficient security evidence

The earlier F6 helper implicitly allowed an HTTP 403 to stand in for proof that stale authority was rejected for the intended reason. Review falsified that assumption.

A valid stale-result observation must now bind the denial to the exact project/task/lease and retain the expected authority-denial reason (`Task authority belongs to another runner`).

**Research significance:** for adversarial qualification, identical transport-layer outcomes can arise from different causal mechanisms. A denial status is therefore not equivalent to proof of the target invariant.

Candidate general rule:

> Security qualification SHALL bind negative outcomes to the intended principal, object, authority epoch/lease and denial reason where those distinctions are material to the invariant.

## 4. Post-v1 inference-aware routing is now formally specified, but remains non-empirical

PR #406 adds a documentation-only post-v1 specification for inference-aware scheduling and serving topology. It covers prefix caching, continuous batching, KV-cache allocation/capacity, serving scheduling, speculative decoding, and prefill/decode disaggregation, with additional awareness of chunked prefill and paged KV where exposed by a backend.

The specification explicitly preserves RESIDUAL authority boundaries: provider/backend optimization is treated as an execution property, not an authority grant. Missing/stale capability or telemetry is represented as `UNKNOWN`; routing decisions are intended to remain deterministic and evidence-backed; raw prompts/secrets are excluded from routing telemetry; and optimization failure must not be converted into task PASS.

Prefill/decode disaggregation is explicitly deferred until a preregistered experiment shows that phase separation improves **accepted useful work after KV-transfer and coordination cost**.

**Observed conclusion:** this is a research/design extension only. No latency, throughput, cost, cache, batching, speculative-decoding or phase-separation effect has been measured by this PR.

**Paper relevance:** the important methodological choice is to evaluate serving optimizations against accepted useful work and transfer/coordination overhead rather than raw token throughput alone. This aligns naturally with the existing hierarchical-inference research track, but it does not provide evidence for H4 yet.

## 5. RRI-005 / Agent Privilege Firewall has been registered as a post-v1 research program

PR #407 adds `RRI-005` / `SPEC-APF-001`, a post-v1, execution-deferred Agent Privilege Firewall research program derived from a privileged-agent hijack failure class.

The program defines:

- an explicit threat model in which workers/model output, prompts, retrieved context, helper processes, plugins, network responses, redirects, DNS answers, stale receipts, cached capability material, sibling workers and worker telemetry may be compromise-capable;
- 24 normative APF invariants;
- capability, endpoint, intent, decision, effect and violation receipt contracts;
- adversarial corpus A01-A30 and positive controls C01-C06;
- qualification gates Q0-Q10;
- swarm implementation lanes APF-A through APF-I.

The core proposed boundary is that compromise of a worker must not imply compromise of RESIDUAL's aggregate authority. The design externalizes privileged authority from workers, binds credential use to destinations, treats trust-root mutation as a high-assurance amendment, revalidates immediately before effect, separates approval from immutable intent, handles ambiguous effects through reconciliation rather than blind retry, and fails closed when APF trust state cannot be validated.

**Observed conclusion:** RRI-005 is now a registered, design-frozen research program. It is not a RESIDUAL security result and does not change v1 runtime behavior.

**Interpretation:** RRI-005 is complementary to AX-21/AUD-1. AX-21 exposed distributed authority/identity and evidence problems in the existing system; RRI-005 generalizes a different privileged-effect threat class into a future adversarial program. It should remain analytically separate from claims derived from AX-21 itself.

## 6. P5 operator-friction experiment still has no post-intervention result

PR #349 remains open/draft at head `625e1ce97919098dbe9d586ffcaf4b2a94257184` and is still based on the earlier frozen main line.

The authoritative before-condition therefore remains unchanged:

- Station direct answer to the frozen global-state question: **No**;
- cold individual-agent queries: approximately **11**;
- human synthesis: **required**;
- external coordination state: **required**;
- continuous reports synthesized during operation: **15+ per session**.

No post-#349 delta should be reported.

The #349 trust-boundary language continues to distinguish ephemeral runner presence from retained evidence and explicitly says presence cannot satisfy review, verification, integration or release gates. That is consistent with AX-21 F-06, but it is implementation intent until qualified and measured.

## 7. Final AX-21 baseline freeze still has not occurred

Accepted `main` remains `91d32fd8b713c68c1cd2e473013c9e1c33b93572`, the WebVM durability repair merged on 2026-09-21. The repository still has no formal GitHub release.

Therefore:

- there is no release-tag cutover;
- `AX-21-BASELINE-R0` remains a candidate pre-release baseline/control condition;
- the release-tagged three-host reproduction has not become the final baseline-freeze event;
- later post-v1 research specifications must not be backfilled into AX-21 as if they were part of the original experiment.

## 8. New / strengthened RES-UP and ImprovementSpec candidates

These remain candidate identifiers unless separately registered.

### Candidate RES-UP — Semantic evidence guards

Evidence tools must validate the semantic proposition represented by an artifact, including schema, process/principal identity, authority epoch, object binding and expected causal transition. Hash integrity alone is necessary but insufficient.

### Candidate RES-UP — Reason-bound negative security evidence

Negative security tests should prove not only that an action failed, but that it failed for the invariant-relevant reason and against the intended principal/project/task/lease/capability. Preserve unrelated-denial cases as non-passing evidence.

### Candidate RES-UP — Evidence-apparatus first-failure retention

Qualification failures in the evidence harness itself are first-class experimental evidence. Repairs must advance bytes and preserve superseded failing heads/runs rather than rerunning changed apparatus under the old identity.

### Candidate ImprovementSpec — F6 physical evidence schema as a reusable contract

Generalize the current two-bundle F6 method into a reusable physical disruption evidence contract: exact candidate identity, process-bound remote records, operator timeline, immutable manifests, causal negative probes, read-only local snapshots and independent re-audit.

### Candidate research extension — Serving-aware hierarchical inference

After v1, bind the inference-aware routing spec to the existing H4 program using preregistered comparisons that report accepted useful work per wall-clock hour, provider dollar and accelerator-second, while isolating cache, batching, scheduling, speculation and prefill/decode separation effects.

RRI-005 is already a registered research program and should not receive a duplicate candidate RES-UP identifier here.

## 9. Paper-relevant conclusions

### Supported by current evidence

- Evidence integrity and evidence adequacy are different properties. A tamper-evident artifact can still be inadequate to establish the intended causal claim.
- Security negative tests require semantic binding when multiple failure mechanisms can produce the same transport/status outcome.
- The AUD-1 program is preserving superseded failures and exact-head qualification history rather than overwriting them with later green runs.
- The research program is increasingly separating design/specification, experimental apparatus, and empirical results.
- The P5 operator-friction baseline remains uncontaminated because no unmeasured #349/mesh improvement has been promoted into the control condition.

### Not supported / unchanged

- No claim that physical F6 authority-loss/reconnection behavior passes.
- No claim that AUD-1 is closed or that RESIDUAL is secure as a whole.
- No post-#349 operator-friction improvement measurement.
- No empirical result for inference-aware routing, prefill/decode disaggregation or H4.
- No empirical result for RRI-005/APF; implementation is intentionally deferred.
- No final `AX-21-BASELINE-R0` freeze because no formal release-tag cutover exists.

## 10. Next evidence gates

1. Execute and freeze `F6-A-inside-window` and `F6-B-outside-window` against the exact authorized #399/#403 identities, then complete the independent read-only re-audit.
2. Keep first-failure evidence from the evidence apparatus and physical runs immutable; any helper/candidate-byte change receives a new identity and qualification cycle.
3. Do not promote #406 into an inference-performance claim until post-v1 activation, frozen baseline/workload and preregistered measured execution exist.
4. Keep RRI-005 execution deferred until the post-v1 gate/owner GO; treat its corpus and qualification gates as design artifacts until run.
5. Keep the P5 question and before-condition unchanged until #349 or its successor is qualified and replayed.
6. Do not declare final AX-21 baseline freeze until a real release tag and complete freeze manifest exist.

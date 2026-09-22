# AX-21 / RESIDUAL Research Check-in — 2026-09-21

**Status:** append-only research maintenance record. This document does not modify the AX-21 baseline, authorize SLM training, freeze SLM-00, close AUD-1, or advance a release.

## 1. Executive research state

Material new evidence exists since the prior check-in.

The strongest new findings are not a new model-performance result. They are: (1) an adversarial evaluation found and then verified remediation of a benchmark gold-label leak; (2) a pre-release security audit exposed distributed-authority surfaces not covered by the earlier AX-21 lease-focused negative tests; (3) an authoritative browser/WebVM failure showed that successful command completion did not imply durable evidence across reload; and (4) a live OpenClaw pilot recovered from a real Kimi HTTP 429 by falling back to a local 7B model and producing a durable Shared Comms receipt.

These findings narrow and improve the defensible research claims. They also preserve several important negative results.

---

## 2. Observation O-21-01 — SLM-00 adversarial review falsified the random-floor baseline

### Observed evidence

G2 round 1 rejected the SLM-00 freeze candidate with two blocking findings:

- **G2-B1:** the B1 "random floor" could observe gold information through a degenerate choice surface and achieved VMSR **0.873**, making the supposed floor effectively oracle-contaminated.
- **G2-B2:** CD-XVAL-R2 was stale and verified superseded bench evidence rather than the current freeze candidate.

Remediation changed the evaluation runner so non-oracle backends receive only a deep-copied candidate payload without gold fields. Fresh G2 round-2 execution reproduced:

- B1 aggregate VMSR **0.041**;
- B3 oracle VMSR **1.0** on all eight categories;
- **59/59** manifest hashes verified;
- **70/70** verifier tests and **34/34** runner tests passed;
- direct non-oracle attempts to access `expected_output` failed;
- the stale R2 report was explicitly superseded by R3.

G2 round 2 disposition: **PASS_WITH_NONBLOCKING_FINDINGS**.

### Interpretation

This is a strong example of falsification improving the experiment rather than weakening it. The original B1 number must never be cited as a valid random baseline. The useful research result is that the adversarial review discovered a benchmark-information leak severe enough to invalidate a baseline, and the corrected runner materially changed the measured floor while leaving the oracle ceiling intact.

### Preserved negative result

Keep the leak-era **VMSR 0.873** and stale R2 evidence in the historical record. They are evidence that evaluation infrastructure itself can create misleading capability results.

### Paper relevance

Any SLM paper should state that the evaluation apparatus underwent adversarial qualification and that a gold leakage defect was found before model training/freeze. This supports a methodology claim about evaluation hardening, not a model-quality claim.

---

## 3. Observation O-21-02 — Cross-validation is materially stronger, but near-duplicate risk remains

### Observed evidence

CD-XVAL-R3 against the current pinned bench/verifier refs reported:

- exactly **1,000** regenerated items at the required category allocation;
- pinned bench SHA-256 `15937ec20ec314d0dd80c374a074893c95b43b00b69ae114330615d993c56cbd` reproduced;
- **1,000/1,000** PASS with contract-shaped gold candidates;
- **0 BENCHMARK_DEFECT** in the positive battery;
- **0 PASS leaks in 4,000** negative candidates;
- **0 exact duplicates**;
- **86** bench contamination groups;
- **12** measured shared bench↔corpus lineage keys.

Independent G2 remeasurement also confirmed a normalization-sensitive cross-group near-duplicate phenomenon. Different normalizations produced different counts, but the mechanism persisted.

### Interpretation

The benchmark is substantially better qualified than at the prior check-in, but "no exact duplicates" is not equivalent to "no contamination risk." Freeze-time split authoring still needs content-normalized clustering and explicit protection of shared bench/corpus lineage keys.

### Candidate ImprovementSpec / RES-UP item (unregistered)

**Freeze-time contamination enforcement:** convert the currently procedural bench↔corpus and near-duplicate protections into a machine-checkable freeze artifact so the split author cannot accidentally separate materially related examples across evaluation boundaries.

---

## 4. Observation O-21-03 — SLM-00 is G-qualified but not frozen; status evidence is now slightly divergent

### Observed evidence

Lane G's candidate receipt at head `2076f455...` reports **STATUS: G_PASS** with zero blocking findings after requalification. It still lists human gate items including:

1. prior-art scope ratification;
2. landing the schema erratum on the base branch;
3. split-manifest authoring by contamination group, including content-normalized near-duplicate clustering;
4. model digest pinning;
5. non-blocking metric/tooling follow-ups.

The same receipt text says "G2 red-team round 2: PENDING," while the later independent G2 R2 report exists and records `PASS_WITH_NONBLOCKING_FINDINGS`.

There is still no explicit SLM-00 freeze authorization recorded in the inspected evidence, and the candidate receipt itself explicitly says **SLM-00 is NOT FROZEN**.

### Interpretation

This is a small but useful state-synchronization finding: exact evidence can be correct while human-facing status text becomes stale across branch-local artifacts. The underlying evidence is not contradictory about the technical result, but the status surface is.

### Candidate ImprovementSpec / RES-UP item (unregistered)

**Authoritative research-freeze status projection:** generate one machine-derived status view from exact pinned evidence and explicit human authorization, rather than relying on manually synchronized PR bodies/receipts. The projection must not itself grant freeze authority.

---

## 5. Observation O-21-04 — AUD-1 materially narrows the earlier AX-21 fail-closed claim

### Observed evidence

The pre-release AUD-1 audit identified the following release-convergence findings from the AX-21-era baseline:

- **F1 P0:** unauthenticated bootstrap exposed operator/session authority;
- **F2 P0:** distributed worker authority needed project/task/runner binding rather than station-wide credential + lease possession;
- **F3 P0:** non-loopback exposure did not yet fail closed behind explicit remote-exposure configuration;
- **F4 P0 hardening:** coordinator-vs-worker transition authority needed to be encoded directly in code;
- **F6 P0 operational correctness:** persistent heartbeat loss needed bounded recovery followed by authority surrender rather than indefinite inference under expired authority.

PR #399 implements a convergence candidate with ten adversarial regression cases. At inspected head `fb416efe...`, the main technical workflows/Qualification-v1 were green; maintainer approval was intentionally still red. The PR explicitly does **not** claim the two required physical P1 tunnel cases or the independent Mason re-audit.

The automated PR review also classified the ticket as only partially compliant and requested further verification of coordinator-vs-worker transition authority.

### Interpretation

This does **not** invalidate the earlier AX-21 result that the tested lease/claim/result surfaces failed closed. It does invalidate any broader phrasing such as "fail-closed held at every relevant security surface" or "RESIDUAL security was release-ready." AX-21's negative tests were narrower than the distributed trust boundary discovered by AUD-1.

The defensible statement is now:

> The AX-21 lease/claim/result surfaces tested at the time failed closed, while subsequent AUD-1 review identified additional bootstrap, credential-scope, remote-exposure, transition-authority, and authority-surrender surfaces requiring pre-release remediation and physical requalification.

### Preserved negative result

Do not erase F1/F2/F3/F4/F6 after repair. They should remain part of the historical AX-21/pre-release security evidence and threats-to-validity discussion.

### Paper relevance

This is important for any Verified Agentic Control paper. It demonstrates why security/authority claims must enumerate tested invariants rather than infer system-wide security from a small adversarial battery.

---

## 6. Observation O-21-05 — Real physical P1 evidence is still the remaining security gate

### Observed evidence

AUD-1 explicitly requires two separate retained physical cases on the LEGION / DELL7320 / DBOX topology:

- **Case A:** tunnel interruption and restore inside the retry/authority window, proving continuity without duplicate authority or invalid transition;
- **Case B:** interruption beyond authority expiry/revocation, restore after reassignment, and proof that the old worker/result remains dead.

PR #399 has not claimed those physical cases. The independent Mason read-only re-audit must follow the physical evidence and classify F1/F2/F3/F4/F6 as FIXED/PARTIAL/NOT FIXED/REGRESSION.

### Interpretation

Software CI success is not enough to close the distributed-authority hypothesis. The remaining evidence is explicitly environmental and temporal.

### Measurement opportunity

Record reconnect timing, lease/authority timestamps, duplicate-work count, stale-result acceptance count, operator interventions, and recovery wall-clock time for both cases. These can become a useful reliability/security dataset rather than a binary PASS/FAIL only.

---

## 7. Observation O-21-06 — Evidence durability across browser lifecycle was a real failure mode

### Observed evidence

On authoritative `main@b571b91a...`, the Pages acceptance run built/deployed and passed multiple checks, then failed only after a successful standalone workbench audit followed by browser reload. Previously verified mission evidence was no longer durable at the expected boundary.

The retained first failure was **not rerun unchanged**. Root cause was classified as a repository durability-boundary gap: the persistent worker already called `os.sync()` before publishing success, while the standalone workbench CLI did not. PR #397 added a successful-CLI sync barrier and regression tests, and merged as `main@91d32fd8...`.

### Interpretation

This is a research-relevant systems finding: **successful execution acknowledgment is not equivalent to durable evidence** when the underlying storage has asynchronous persistence semantics.

For evidence-governed agent systems, durability is part of the evidence contract. A receipt that can disappear across the immediately expected lifecycle transition is not sufficiently durable simply because the preceding command returned zero.

### Candidate ImprovementSpec / RES-UP item (unregistered)

**Durability-before-success invariant:** components that publish successful completion for evidence-bearing mutations should make the required persistence boundary explicit and test lifecycle transitions (reload/restart/process death) rather than only in-process reads.

---

## 8. Observation O-21-07 — Real provider quota failure recovered through local-model fallback

### Observed evidence

The OpenClaw ↔ RESIDUAL Shared Comms pilot recorded a live sequence in which:

- a request was addressed to `OPENCLAW-AGENT2`;
- Kimi returned a real **HTTP 429 quota exhaustion**;
- OpenClaw fell back to `ollama/qwen2.5-coder:7b`;
- the agent produced `SHARED_COMMS_OLLAMA_OK`;
- a Shared Comms response and durable receipt were recorded.

The bridge implementation remains draft. Current `main` does not yet contain the required R3.4 Station Shared Comms worker endpoints/outbox contract, and the bridge must not be interpreted as merged production behavior.

### Interpretation

This is useful natural-failure evidence for heterogeneous model routing/fallback: a frontier/remote provider failure did not necessarily terminate useful agent communication when a local model path existed.

It is **not** evidence that local 7B fallback preserves task quality in general, and it does not yet establish the H4 cost/performance hypothesis.

### Follow-up measurement

Future fallback experiments should capture:

- failure class and provider;
- fallback model;
- recovery latency;
- operator intervention count;
- verification outcome of the resulting work, not just message delivery;
- incremental cost/energy;
- whether fallback altered authority or evidence semantics.

---

## 9. Observation O-21-08 — P5 operator-friction experiment has not yet advanced

### Observed evidence

PR #349, which contains Shared Comms and the connected-runner roster intended to answer the frozen P5 question, remains open/draft and unmerged.

Therefore the frozen AX-21 before-condition remains the only valid P5 measurement:

- Station direct answer: no;
- cold individual-agent queries: 11;
- human synthesis: required;
- external state dependency: yes;
- 15+ reports/session synthesized during normal operation.

### Interpretation

Do not claim a P5 coordination-transfer improvement yet. #396 Owner Action Queue and #349 are potential interventions, but no post-intervention replay of the frozen question has been observed in the inspected evidence.

---

## 10. Release / baseline state

### Observed evidence

- Authoritative main has advanced to `91d32fd8b713c68c1cd2e473013c9e1c33b93572` through the merged WebVM durability repair.
- The GitHub Releases collection is still empty in the inspected repository state.
- AUD-1 remains open and PR #399 has not completed its physical P1 + independent re-audit sequence.

### Interpretation

The first defensible release has **not** been established by the inspected evidence. Consequently `AX-21-BASELINE-R0` must remain a candidate/pre-release baseline rather than being declared finally frozen at a release cutover.

---

## 11. Research claims after this check-in

### Better-supported

- Adversarial review can detect serious evaluation leakage before model experiments begin.
- Exact-head evidence retention is exposing real first-failure states rather than green-only histories.
- Fail-closed lease behavior remains supported on the specific AX-21 lease/claim/result surfaces that were exercised.
- Heterogeneous fallback can preserve at least bounded communication under a real provider quota failure in the observed OpenClaw pilot.
- Evidence durability must include lifecycle persistence boundaries, not only successful command completion.

### Explicitly not established

- RESIDUAL is secure as a whole.
- AUD-1 F1/F2/F3/F4/F6 are fully fixed in deployed/physical operation.
- SLM-00 is frozen.
- StationLM/Residual-Nano model-performance claims.
- Post-#349 reduction in P5 operator friction.
- H4 hierarchical inference efficiency as a performance/cost result.
- sustained autonomous recursive development.

---

## 12. Candidate unregistered RES-UP / ImprovementSpec items

1. **Research freeze status projection** — one non-authoritative, machine-derived status surface binding exact evidence heads + human gate state, reducing stale status text.
2. **Freeze-time contamination enforcement** — machine-check shared bench↔corpus lineage and content-normalized near-duplicate groups before split-manifest acceptance.
3. **Durability-before-success invariant** — evidence-bearing success paths must cross the declared persistence boundary before acknowledging durable completion.
4. **Physical authority-loss telemetry** — capture timestamps/interventions/duplicate-work/stale-result outcomes for P1 inside/outside-window tunnel experiments.
5. **Fallback recovery telemetry** — measure recovery latency, operator intervention, verified work outcome, cost/energy, and evidence semantics across provider→local fallback.

No registry IDs are assigned here; ownership/registration remains a separate governance action.

---

## 13. Next evidence to watch

Highest-value next observations:

- completion of PR #399 physical P1 Case A and Case B;
- Mason independent AUD-1 re-audit on the exact candidate head;
- authoritative new-main qualification if AUD-1 merges;
- explicit SLM-00 human freeze or a freeze refusal/deferral with reason;
- split-manifest contamination qualification;
- first actual post-#349 replay of the frozen P5 operator question;
- verified-task outcome under provider→local-model fallback rather than message-level success only.

Until those occur, preserve the current negative results and do not upgrade the corresponding claims.

# RESIDUAL roadmap

This roadmap describes planned work and current evidence boundaries. It is not a release-qualification certificate. Exact source, workflow runs, retained experiment artifacts, and protected governance remain authoritative.

Current accepted repository baseline for this status is **`main@de7d9774cfd63c77ef5645ca43aa0be1a604887f`**.

## Current capability boundary

| Area | Current state | Evidence / limitation |
| --- | --- | --- |
| Core harness | Implemented | Verifier-owned acceptance, bounded obligations, receipts and evidence handling exist; broad model reliability is not implied |
| Command Station | Implemented and actively hardened | #218 repair context and #233 actionable failure/repeated-patch diagnostics are accepted; general repair reliability remains unproven |
| Mission Control / WebVM | Implemented with bounded fallback/recovery | #248 is accepted provider-load lifecycle behavior; exact current main still has a Pages live-acceptance FAIL in a provider bootstrap sequence after generated artifact proof and deployment passed |
| Factory M2/M3/M4 | Implemented | Qualification remains exact-revision/environment bound; implementation is not every-host qualification |
| M6 repair loop | Mixed research evidence | #203/#204/#215/#217 FAIL; #220 bounded PASS |
| M6.2 first contract shipment | Research PASS, production pending | #231 self-shipped the first `ImprovementSpec` implementation; #243 is derived from that source plus maintainer deep-immutability hardening and remains open/unaccepted |
| M6.2 evidence-sufficiency fork | Bounded research PASS with defects surfaced | #232 exercised MeasurementGap vs grounded hypothesis behavior and exposed deterministic rejection requirements |
| M6.2 autonomous discovery | Not established; typed trials still FAIL admission | #244/#246 timed out; #249 reached discovery but malformed/repeated/truncated outputs failed; #250/#251/#252/#254 produced well-formed typed proposals that deterministic admission rejected because they called already-measured metrics missing |
| General recursive self-improvement | **UNKNOWN / not established** | No retained autonomous-discovery + verifier + champion/challenger success chain yet |
| Paid/live provider success on exact current deployed main | **UNKNOWN / not established** | Current exact-main Pages proof records `cloud_inference: NOT_RUN`; historical real-account protocol failure remains |

## Accepted current changes

The current documented accepted sequence includes:

- #200 setup hardening;
- #205 session-scoped provider-channel recovery;
- #218 bounded Station prior-candidate repair context and shared five-attempt ceiling;
- #201 guided frontend and inline Puter setup;
- #233 actionable repair failure-tail retention and repeated failed-patch detection;
- **#248** provider-load generation/lifecycle qualification on the credentialless embedded provider path.

Exact merged `main@de7d9774...` has six successful ordinary push workflows and one **FAIL**: Pages run `35363306307`. Generated desktop+narrow browser proof and deployment passed. Published desktop acceptance progressed through the real guest/demo/reload/repository/workbench/provider-contract path before timing out because sign-in remained disabled.

The retained report records `cloud_inference: NOT_RUN`; the trace supports a fresh-provider-frame bootstrap race, not a Puter outage or model-quality conclusion. Open **#253** contains the focused fail-closed bootstrap repair. Its applicable technical exact-head workflows currently pass, including Browser VM Demo CI and Pages, while the exact-head maintainer approval gate is **FAIL / pending matching attestation**. If #253 is accepted, the resulting merged SHA still requires its own first production Pages attempt.

## M6.2 roadmap issue #222

Issue #222 remains open. Its objective is to move from a repair loop that executes supplied improvement hypotheses toward a system that can originate evidence-grounded, falsifiable ImprovementSpecs while keeping authority outside the model.

The target decomposition remains:

1. `ImprovementSpec` production contract;
2. `EvidenceSnapshot` production contract;
3. `MeasurementGap` production contract;
4. analysis-only `Scientist`;
5. deterministic `HypothesisVerifier`;
6. experiment ledger;
7. champion/challenger evaluator;
8. autonomous discovery experiment M6-SPEC-007 and successors.

### Deliverable 1 — ImprovementSpec

**Research status: PASS in #231. Production status: open/unaccepted in #243.**

M6-ROADMAP-001B (#231) ran against a detached clean copy of exact `main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9` and retained:

- one implementation attempt;
- 3/3 immutable checks PASS;
- independent local review APPROVED;
- exact reviewed head integrated;
- verification receipt issued;
- release export succeeded;
- retained artifact ID `10546904820`.

Production PR **#243** imports the generated implementation but now also contains maintainer hardening after review found mutable nested `acceptance` state. Its current head recursively freezes that graph, protects canonical JSON/SHA identity from caller-owned mutation, keeps `to_dict()` detached, rejects unsupported non-JSON values, and adds independent production tests. The current #243 source therefore **does not claim byte-for-byte identity with the generated #231 source**.

Current #243 status:

- applicable technical PR-head workflows, including Pages: **PASS**;
- exact-head maintainer approval gate: **FAIL / pending matching attestation**;
- merge/production status: **open, unaccepted**.

Until #243 is accepted, the production contract remains **UNKNOWN / unaccepted**.

### Evidence-sufficiency experiment — #232

M6-EPI-001 completed both experiment arms after one repair and validated the high-level distinction between insufficient and sufficient evidence, but exposed stricter verifier requirements:

- an insufficient-evidence result must not leave required protected invariants empty;
- acceptance criteria must be structured rather than free-form prose;
- performance metrics must not be silently treated as protected invariants.

These remain planned deterministic HypothesisVerifier rejection cases. #232 does not itself establish the production Scientist or verifier.

### Autonomous discovery — #244 through #254

The retained sequence materially narrows the failure mode:

- **#244 / M6-SPEC-007:** provider timeout before any proposal. **FAIL in experiment-execution scope / discovery not reached.**
- **#246 / M6-SPEC-007B:** smaller context, but provider again timed out before proposal. **FAIL in experiment-execution scope / discovery not reached.**
- **#249 / M6-SPEC-007C:** provider completed, but free-form candidates were malformed/repeated/truncated and exhausted the five-pass brake. **FAIL in bounded discovery qualification scope.**
- **#250 / M6-SPEC-007D:** typed structured output removed malformed JSON, but deterministic admission rejected a MeasurementGap that claimed already-measured `provider_timeout_rate` was missing. Artifact `10555509851`, ZIP SHA-256 `50a1999791069de03bb9e65db7e7537ff831c8a7a3f1218c6f2587376207cdf5`. **FAIL in mechanical-admission/discovery scope.**
- **#251 / M6-SPEC-007E:** three bounded repair attempts received exact verifier feedback, but all three repeated the same mechanically rejected `provider_timeout_rate` MeasurementGap. Artifact `10554449651`, ZIP SHA-256 `b705aabb937a361d13293d3d9d44c7c62258dd42bb9d809c54b0e1f0fb25554e`. **FAIL in typed-repair scope.**
- **#252 / M6-SPEC-007F:** moving known evidence constraints closer to the typed response schema still yielded an already-measured metric as a MeasurementGap. Artifact `10556410450`, ZIP SHA-256 `e963dfcb8dab977557788332385b934feb354a95cd0d199f867a97b055903ab6`. **FAIL in evidence-aware typed-discovery scope.**
- **#254 / M6-SPEC-007G:** changing the Scientist/reviewer model to general `qwen2.5:7b` still yielded a MeasurementGap for already-measured `context_bytes_non_success_mean`. Artifact `10555728738`, ZIP SHA-256 `03b96137d623b58c18aaa0e43711904a71a1a6c4ac0dbd29e7cae8329d7ec15e`. **FAIL in general-model discovery scope.**

No #250/#251/#252/#254 proposal passed deterministic admission, semantic review approval, or admission-receipt issuance.

The important gain is diagnostic, not a capability PASS: structured output can remove syntax ambiguity, but evidence-grounded proposal selection and repair remain unsolved in these cells. The deterministic verifier correctly prevents well-formed but evidence-contradicted MeasurementGaps from becoming accepted hypotheses.

General autonomous discovery remains **UNKNOWN / not established**.

## Current build order

1. **Close deliverable 1 correctly:** review and qualify #243; require exact-head maintainer attestation before merge. Preserve the distinction between the #231-generated research source and the current human-hardened production candidate.
2. **Evidence contracts:** implement `EvidenceSnapshot` and `MeasurementGap` as deterministic production contracts with canonical identity, explicit measured-vs-missing semantics, and defensive serialization.
3. **Scientist boundary:** keep the Scientist analysis-only — no Git/write/integration/promotion authority and no ability to redefine protected invariants.
4. **HypothesisVerifier:** encode the #232 rejection cases and the #250/#251/#252/#254 evidence-grounding failures. A MeasurementGap must name a genuinely absent required measurement; a measured-but-bad value is not a missing measurement.
5. **Typed proposal selection:** preserve schema-constrained output, but require the proposal type to be consistent with the EvidenceSnapshot. If sufficient evidence exists, prefer a falsifiable ImprovementSpec over an invented MeasurementGap.
6. **Bounded semantic repair:** make exact verifier findings actionable without granting the model checker authority; repeated identical semantically invalid proposals should terminate/stagnate rather than consume the entire budget pretending progress.
7. **Experiment ledger:** retain hypothesis identity, evidence identity, code/revision identity, model/provider identity, checks, review, receipts, outcomes, and negative cells.
8. **Champion/challenger:** compare candidate changes against an exact retained baseline with frozen metrics and reject regressions in protected invariants.
9. **Repeat autonomous discovery:** require repeated retained verifier-accepted runs before making reliability claims; one future success would still be bounded evidence.
10. **Repair independent governance defects:** refresh and requalify the #207/#208/#212 accounting/release-ordering path on current main.
11. **Confirmatory evaluation:** freeze R0–R5 and planned degradation/routing protocols before paper-facing outcome collection.

## Parallel qualification work

The M6.2 roadmap does not replace other current blockers:

- preserve exact `main@de7d9774...` Pages run `35363306307` as the authoritative first merged-SHA FAIL; complete #253 review/attestation and, if accepted, qualify the resulting merged SHA from a fresh first production Pages attempt;
- retain a fresh exact-deployed-revision real-account Puter candidate→verifier→receipt success or keep paid/live provider success UNKNOWN;
- physically validate the #186 mobile fallback without claiming heavyweight-WebVM iPhone reliability;
- complete true blank-environment, recovery/host-loss, and selected elapsed-soak qualification;
- continue #120/#126 WebVM long-run reliability work;
- preserve the separate #139→ownership-baseline→fresh-qualification→#134 protected sequence;
- resolve the #133/#132 retirement-versus-restoration discrepancy explicitly.

## Trust-boundary constraints

Roadmap work must preserve the existing authority split:

- models propose; host-owned checks decide acceptance;
- review, receipt, integration, promotion and release authority remain outside the Scientist/runner;
- protected Factory/M4 implementation, ownership baselines, qualification anchors, protected bytes and evidence schemas require their own reviewed process;
- `implementation-status.yaml` is an implementation-presence manifest, not a release-qualification manifest;
- historical FAIL/BLOCKED/UNKNOWN cells are not erased by later PASS results.

## Exit criteria for stronger self-improvement claims

Do not describe RESIDUAL as generally self-improving until retained evidence demonstrates, across repeated frozen trials:

1. the system originates an ImprovementSpec from evidence without a supplied hypothesis;
2. a deterministic verifier accepts the hypothesis before execution;
3. protected invariants are explicit and retained;
4. a bounded implementation/review/integration path executes the accepted hypothesis;
5. a champion/challenger evaluator shows the declared improvement against an exact baseline;
6. failures and regressions are retained rather than filtered from the dataset;
7. the process repeats across more than one task/model/environment cell;
8. no autonomous merge authority is inferred from the experiment.

Until then, autonomous discovery and general recursive self-improvement remain **UNKNOWN / not established**.
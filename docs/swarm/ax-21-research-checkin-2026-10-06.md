# AX-21 research check-in — 2026-10-06

**Status:** append-only research maintenance record.  
**Authority effect:** none. This record grants no merge, release, deployment, security, autonomy, native-execution, or acceptance authority.

## Evidence boundary

Reviewed current repository evidence on accepted `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`, current PRs #533, #534, #535, the unmerged qualification-rerun freshness successor at `206394b3cc9f539b643b3f038784a37b8409a38f`, and retained/local October 6 AX-21/WebVM evidence tied to PR #516. Historical negative results remain preserved. Observations below are separated from interpretation.

An adjacent October 6 file-handoff research note (AX-12) was reviewed for cross-stream relevance but is not promoted into AX-21 experimental results.

## Material observations

### Qualification reruns: final-artifact isolation passed, producer freshness did not

PR #533 exact head `5de913ab40d685ff15cb4e9e7229cfe9a43810bd` repairs one specific rerun defect: final aggregate outputs are attempt-distinct and no longer re-enter the `qualification-v1-*` producer input set. Qualification-v1 run `37466250391` reached PASS on attempts 1, 2, and 3, with separate final artifacts `11414896060`, `11415725952`, and `11414846717`.

However, the same controlled rerun exposed a second defect. The attempt-2 `active-http-soak` producer passed and uploaded artifact `11415141264`, yet aggregate attempts 2 and 3 selected older same-name producer artifact `11415575224` and retained attempt-1 soak evidence.

Observed result: aggregate self-ingestion was fixed, but newest-per-producer evidence selection was not.

Falsified hypothesis: a dependent aggregate rerun automatically consumes the newest completed evidence for any producer that was rerun.

Interpretation: qualification freshness has two independent dimensions:
1. the aggregate must not consume its own retained output; and
2. each logical producer must be selected by explicit source/attempt identity rather than ambiguous same-name retention.

The prepared successor `206394b3cc9f539b643b3f038784a37b8409a38f`, exactly 2 commits ahead / 0 behind #533, adds a fail-closed selector plus seven focused regression cases for newest-per-producer selection, wrong source, future attempt, missing producer, ambiguous newest attempt, evidence-attempt mismatch, and non-flattened materialization. Workflow wiring and a controlled hosted partial-rerun proof are still absent. Therefore this successor is implementation-prep evidence, not a qualified repair.

### Native MissionSync verifier: the schema/prose contract was stronger than #531's implementation

The current master readiness ledger records a source-level mismatch in #531 `81f168703373e4512629aa7260d21fe199eab23b`: its verifier did not actually enforce the accompanying schema, did not compare externally selected Station project/task/attempt/spec facts, did not hash referenced evidence-file bytes, and did not require each named Hermes/OpenClaw hook capture. Missing before/after state could also compare equal.

This supersedes any earlier interpretation that #531's existence alone made the native-proof contract mechanically complete.

PR #535, exact head `a74e4b2d21946dbe4dadcbd74c083717ccf3ce9f`, is a one-commit, four-file successor on #531. It adds schema enforcement, exact external-fact binding, bounded path/file handling, actual evidence-byte hashing, six distinct hook captures, Station before/after record checks, malformed JSON rejection, and negative controls.

Hosted exact-head evidence is strong at the software-verifier layer:
- Clean install PASS
- Measured evaluation binding PASS
- Control Plane PASS
- Factory ownership PASS
- Mission Sync component/Station integration PASS
- Controller/provider PASS
- Command Station PASS
- Qualification-v1 PASS

The Mission Sync lanes report 52 unittest cases plus 2 Station pytest cases passing in each Python 3.11 and 3.13 lane. Qualification-v1 reports all required gates present. PR-Agent advisory review failed separately with HTTP 401 authentication failure.

Observed limitation: operator-supplied external Station facts are still not authenticated Station retrieval, and hash-bound normalized/raw captures do not by themselves prove that native hooks actually executed, that a model consumed the context, or that Station performed the represented transition. Independent raw-evidence review remains required.

Interpretation: **evidence integrity and internal consistency are not evidence authenticity.** A verifier can prove that a package is self-consistent and byte-bound while still depending on externally supplied claims about origin.

An exact-head maintainer token was later posted for #535. That is an operator intervention and exact-head authorization datum; it is not an independent technical review or native execution result.

### PR #516: local regressions reproduced two trust/containment boundaries without changing production blobs

A retained October 6 local preparation packet for PR #516 keeps the reviewed production blobs unchanged and adds only repository-test candidates and exact-source fixtures. It is explicitly local preparation only; full repository CI, Linux/WebVM/native qualification, and release acceptance were NOT RUN.

The packet reports 15 local unittest cases passing with zero failures/errors/skips on Python 3.13.5, Node 22.17.1, and Git Bash 5.2.26 MSYS.

Three material observations are preserved:

1. **Verifier partial publication:** a real temporary JSONL observer that persists/fsyncs PASS and then throws reproduces an intermediate PASS-shaped publication while the returned verification report becomes FAIL. The actual LoopController escalates and publishes `overall_pass=false`. No stale-PASS acceptance is claimed.

2. **WebVM poison/admission race:** using exact-host JavaScript in Node VM mocks, the preserved original fixture publishes one control command after poison arrives during a yielded mailbox write, while the candidate publishes none for either poison marker. Clean admission still publishes once. This is regression evidence against the exercised race, not browser/native proof.

3. **Poison-fence diagnostics:** ten local cases exercise permission/write failure, missing parent, existing file/directory, empty-file partial write, clean exit, missing/failing sync, neutral/split/combined markers, and single-rejection behavior. The packet explicitly retains a blocker: production `sync` is still unbounded; no production sync deadline, native durability, real failed-storage behavior, arbitrary host-race coverage, or comprehensive admission-safety result is established.

Falsified hypotheses:
- returning FAIL is not enough to prove no PASS-shaped observation was already durably emitted;
- a readiness check before an asynchronous/yielding mailbox write is not sufficient if poison/readiness can change before command publication.

Interpretation: authority-relevant transitions that cross a yield boundary require revalidation after the yield, and observation publication requires an explicit provisional/final protocol if externally persisted intermediate states can outlive a later local failure.

### Master readiness is a read-model, not qualification transfer

PR #534 `7ce4762087a9caa47f8002aa840e9c83c02b3dc4` is 5 commits ahead / 0 behind accepted main and changes only `docs/v1/V1_MASTER_READINESS.md`. It explicitly preserves exact-head non-transfer and now tracks both qualification-rerun defects separately.

Observed consequence: the repository's current planning layer correctly classifies #533's aggregate-self-ingestion repair as VERIFIED while keeping producer freshness as a separate IN_PROGRESS blocker. This is a useful status-model correction, not product qualification.

### Adjacent file-handoff evidence remains outside AX-21

The October 6 AX-12 file-handoff note records a bounded latest-30-message inspection where a sender had claimed five attachments, a recipient reported no relevant resource markers/uploads, and a later completion narration contained a digest table but no source/base64 payload. No recipient byte-verification acknowledgment appeared in that inspection window. Final delivery and transport root cause remained unverified.

This is relevant to RESIDUAL evidence-transfer design but is explicitly AX-12, not AX-21. It should not be counted as an AX-21 failure rate or as proof of a general Shared Comms defect.

The bounded cross-stream lesson is consistent with AX-21's evidence discipline: sender narration, upload-session state, or a digest table are not equivalent to recipient-specific durable byte verification.

## Operator interventions

Material human/operator actions in this cycle include:
- deliberate controlled reruns of Qualification-v1 on #533;
- manual inspection/classification of the stale producer-selection result;
- maintenance of a separate successor branch for rerun freshness instead of normalizing #533 into a complete fix;
- exact-head owner approval token on #535;
- preparation and execution of the PR #516 local regression packet;
- continued withholding of native MissionSync execution and release authority pending stronger evidence.

These actions remain part of the oversight denominator. No valid post-baseline reduction in human coordination is inferred.

## Measurements

Current quantitative observations retained this cycle:
- #533 Qualification-v1: PASS on attempts 1/2/3 with distinct final artifacts; stale producer selection still observed in attempts 2/3.
- #533 freshness successor: 7 focused selector regression cases in the prepared source; hosted proof NOT RUN.
- #535: 8 substantive technical workflows PASS; Mission Sync reports 52 unittest + 2 Station pytest cases in both Python 3.11 and 3.13 lanes.
- PR #516 local packet: 15 unittest cases PASS, 0 failures/errors/skips; full pytest/CI/native/browser execution NOT RUN.

These figures are revision- and apparatus-bound. They are not reliability rates.

## Falsified hypotheses

1. Attempt-distinct aggregate output is sufficient to make qualification reruns fresh.
2. A rerun aggregate automatically selects the newest artifact for a rerun producer.
3. A native-evidence schema/document automatically means the verifier enforces that schema/document.
4. Byte hashing and schema consistency prove native observational authenticity.
5. Returning a final FAIL proves an earlier externally persisted PASS-shaped observation cannot exist.
6. A readiness check before an asynchronous/yielding dispatch boundary is sufficient to prevent post-check poison admission.
7. Local mock regression PASS is equivalent to native/browser durability proof.
8. Read-model status or a maintainer token substitutes for independent technical evidence.

## RES-UP / ImprovementSpec candidates

- **RES-UP-QUALIFICATION-PRODUCER-FRESHNESS-001** — bind every producer artifact to checked-out source identity + workflow run + run attempt; select the newest completed valid artifact for rerun producers and retain older attempts only for untouched producers.
- **RES-UP-QUALIFICATION-ARTIFACT-SELECTION-RECEIPT-001** — emit a machine-readable selection record naming every producer, selected artifact ID, source identity, attempt, and reason for reuse.
- **RES-UP-EVIDENCE-INTEGRITY-VS-AUTHENTICITY-001** — distinguish schema/digest consistency from authenticated origin/native observation.
- **RES-UP-NATIVE-STATION-FACT-RETRIEVAL-001** — retrieve or independently attest Station facts instead of trusting operator-supplied expected values as origin proof.
- **RES-UP-OBSERVATION-PROVISIONAL-FINAL-001** — make intermediate verifier observations explicitly provisional until finalization, or use an atomic publication protocol.
- **RES-UP-ASYNC-ADMISSION-REVALIDATION-001** — revalidate authority/readiness after yield boundaries immediately before command publication.
- **RES-UP-POISON-FENCE-DURABILITY-001** — define and test the durability boundary for poison/fence state, including bounded sync behavior.
- **RES-UP-CROSS-AGENT-FILE-RECEIPT-001** — adjacent AX-12 candidate only; recipient-specific byte/materialization receipt rather than sender-claim completion.

Candidate experiments:
- **EXP-QUAL-RERUN-FRESHNESS-01** — controlled partial rerun where one producer is rerun, proving the aggregate selects that producer's newest valid attempt while reusing prior attempts only for untouched producers.
- **EXP-NATIVE-EVIDENCE-FABRICATION-01** — construct internally consistent, correctly hashed but non-native synthetic evidence and require the authenticity layer to keep qualification incomplete.
- **EXP-VERIFIER-PERSIST-THEN-THROW-02** — exercise multiple observer stores and crash points to distinguish provisional publication from authoritative final verification.
- **EXP-WEBVM-POISON-YIELD-MATRIX-01** — inject poison before, during, and after every asynchronous dispatch boundary; measure false command publication and rejection latency.
- **EXP-POISON-FENCE-DURABILITY-01** — crash/reload around fence write and sync boundaries with explicit durability/recovery observations.

## Frozen/pre-release AX-21 baseline comparison

The frozen baseline remains unchanged:
- approximately **11 individual agent queries plus synthesis** were required for the cold P5 dashboard reconstruction;
- normal operation required **15+ manual reports/session** synthesized into external ledgers;
- one local 7B B0-6 observed path completed in approximately **16.4 seconds** without a verifier exception;
- the baseline freeze requires exact repository/release identity, environment manifest, evidence bundle, negative results, operator interventions, external ledgers, P5 data, and derived RES-UP artifacts.

No valid new P5 after-condition was found in this cycle. #349 remains open/draft and is not a post-release measurement result. The October 6 work therefore adds qualification-freshness, evidence-authenticity, partial-publication, and async-admission findings without demonstrating reduced operator burden.

The no-help three-host post-release rerun and first recursive improvement cycle remain the appropriate future comparison. Human intervention must still be counted rather than hidden.

## Release / reproduction findings

Accepted main remains `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2` in the inspected repository state.

No inspected evidence grants a new v1 release, deployment, native-execution, canary, or final-composition authorization.

#533 is a narrow qualification-infrastructure repair with a newly discovered freshness defect.  
#535 is a stronger native-evidence verifier but still not native MissionSync proof.  
PR #516's October 6 packet is local regression preparation only and remains blocked on unbounded production sync plus unexecuted native/browser durability tests.

Negative results are intentionally preserved; none are rewritten as PASS by a later successor.

## Paper-safe conclusions

1. **Evidence freshness is producer-specific, not just workflow-attempt-specific.** A final aggregate can be attempt-distinct and still contain stale producer evidence.
2. **Evidence integrity is not evidence authenticity.** Schema enforcement and byte hashing establish internal consistency, not that the represented native event actually occurred.
3. **Verification publication is a lifecycle.** A locally returned FAIL does not retract an externally persisted preliminary PASS unless the evidence protocol makes provisional/final state explicit.
4. **Authority must be revalidated across asynchronous boundaries.** State checked before a yielding operation can become stale before command publication.
5. **Research apparatus needs its own provenance and failure model.** Selector logic, evidence verifiers, observer persistence, and native-proof collectors are themselves experimental subjects.

These conclusions do not establish whole-system security, fleet-wide autonomy, native MissionSync correctness, WebVM durability, provider-side exactly-once behavior, reduced human oversight, or v1 release readiness.

## Source pointers

- https://github.com/ninja-ops-guy/residual-agent-harness/pull/533
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/534
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/535
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/516
- qualification-rerun freshness successor: `206394b3cc9f539b643b3f038784a37b8409a38f`
- frozen AX-21 baseline claim verification: PR #360 retained evidence

This record intentionally preserves incomplete, failed, superseded, and local-only evidence rather than projecting it into release or autonomy claims.

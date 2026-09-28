# AX-21 / RESIDUAL Research Check-in — 2026-09-27

**Status:** OBSERVED / NOT FROZEN  
**Accepted main observed:** `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`  
**Purpose:** append-only research maintenance. This record does not rewrite AX-21-BASELINE-R0, promote draft evidence into accepted claims, authorize physical experiments, or infer security/autonomy from partial qualification.

## Material findings

### 1. Shared Comms preflight exposed a provenance and seat-health boundary

Operator-reported preflight state was 8 READY / 3 DEGRADED / 1 DOWN. One seat entered a repeated-output condition (six identical lines) and did not answer three dispatches. Final identity validation was blocked because the remaining identity values were available through a retained/relayed receipt rather than a fresh response from that seat. A human ruling remained required before the preflight could advance; a later O1 action remained separately owner-gated.

This is evidence that operational fleet readiness and identity-evidence closure are different states. It also shows that activity is not equivalent to useful responsiveness.

The current dogfood ledger on #481 independently preserves the same research boundary: live, historical, relayed, derived and operator-asserted evidence should retain machine-readable provenance and contradictory evidence should fail closed.

**Candidates**
- `RES-UP-EVIDENCE-PROVENANCE-CLASS-001`
- `RES-UP-SEAT-ECHO-LOOP-001`
- `EXP-AX21-RELAYED-IDENTITY-01`

### 2. Two bounded probe-semantics observations and one AUD-1 metadata-boundary observation

REQ-LP-1 was reported empirically observed twice within its stated probe-semantics class. Preserve the exact receipts before generalizing beyond that scope.

A separate AUD-1 observation showed that the tested bootstrap surface exposed authority-related metadata field names before identity closure. This record intentionally omits operational detail. The observation supports a metadata-minimization review; it does **not** establish privilege escalation, unauthorized mutation, credential disclosure, exploitability, or whole-system compromise.

**Candidates**
- `RES-UP-BOOTSTRAP-METADATA-MINIMIZATION-001`
- `EXP-BOOTSTRAP-METADATA-01` — compare frozen public/authenticated response allowlists without developing bypass behavior.

### 3. Dogfood falsified package version as exact source identity

PR #481's append-only dogfood ledger records a LEGION reproduction where package metadata reported version `0.5.0` while the executable still exposed the pre-#481 command surface because #481 was not yet merged into main.

**Falsified assumption:** package semantic version is sufficient evidence of the installed development-channel source revision.

The corrective work now tracks VCS source identity separately and remains RETEST_PENDING rather than treating implementation as closure.

At current #481 head `8d3d2973d17b437b47fcd55c3a4bceccbf4440f5`, major technical workflows are green, but the maintainer approval visible in the PR is bound to an older head. That approval is historical evidence and does not transfer to the current head.

**Candidate**
- `RES-UP-SOURCE-REVISION-IDENTITY-001`

### 4. Claim-control focused review preserved real first failures

PR #477 retained predecessor cases where incomplete/empty claim registries and internally consistent qualified/released/supported labels could be accepted without sufficiently bound evidence. The current successor `7ec1467f114c48e629473decc64cb5009439e82e` now requires structured qualification evidence bound to an exact subject HEAD/TREE and evidence identity/digest.

The implementation explicitly keeps a boundary: a provenance pointer is not self-authenticating proof.

**Falsified assumption:** an internally consistent claim-state label is sufficient evidence for qualification/release/support.

**Candidate**
- `RES-UP-CLAIM-EVIDENCE-BINDING-001`

### 5. Release-control focused review found incomplete-set acceptance

PR #478 preserved predecessor cases where closure could be accepted with incomplete gate state, trusted-identity inputs were absent, or an additional unbound release artifact could coexist with a correctly bound one. The current successor `a91d89d9e0b7767e174646324afb38fb0cd90c61` makes artifact binding set-complete and requires trusted expected identities.

The validator still does not itself authenticate external files or signatures.

**Falsified assumptions:** cross-field consistency alone establishes release closure; binding one correct artifact establishes correctness of the complete release set.

**Candidate**
- `RES-UP-RELEASE-SET-COMPLETE-BINDING-001`

### 6. WebVM positive waits show a reproducible 273-call failure morphology

The QD2 line #476 retains separate WebVM diagnostic failures while its core Qualification-v1 is green.

On the tested published WebVM build:
- positive-duration `time.sleep` probes failed at call 273 with an OverflowError;
- an empty timed `select` wait also failed at call 273;
- bounded clock-read and zero-duration-sleep probes remained healthy;
- legacy raw wait paths passed their bounded checks;
- tested alternate raw time paths were unsupported in that environment;
- in the concurrent canary, the mission worker remained alive while the independent wait canary failed.

This supports a capability-specific runtime-compatibility finding, not a known root cause and not a security claim.

**Falsified assumption:** general VM/worker readiness is sufficient evidence that all guest timing/wait capabilities are healthy.

**Candidates**
- `RES-UP-WEBVM-TIMER-BOUNDARY-001`
- `EXP-WEBVM-WAIT-273`

### 7. Program Control exact head is not aggregate-qualified

Draft #484 implements a bounded post-v1 Program Control layer and explicitly separates raw GitHub inventory from authoritative program state. Its current head `522c1a2f989daf170d2bb44ccec17f4d6e38ce0e` also narrows snapshot wording from "immutable" to digest-addressed/application-create-once, explicitly not claiming immutable storage or non-repudiation.

At this exact head, many component workflows are green, but aggregate Qualification-v1 is red because the deterministic regression job failed. The cause was not established in this check-in and remains UNKNOWN.

**Conclusion:** green component checks must not be projected into aggregate qualification while the exact-head aggregate gate is red.

**Candidates**
- `RES-UP-PROGRAM-STATE-AUTHORITY-001`
- `RES-UP-INTEGRITY-VOCABULARY-001`

### 8. Merged provider fix still has a live-reproduction boundary

PR #485 reproduced and repaired a WebVM provider authorization-popup failure, received exact-head maintainer approval, and merged as current main `8369f0dc...`.

Its own acceptance text still required a deployed real provider-sign-in check and explicitly rejected fixture auth as live-provider proof.

**Conclusion:** source acceptance and live external-integration reproduction are different evidence states.

**Candidate**
- `RES-UP-POSTMERGE-LIVE-REPRO-001`

### 9. F6 and release authority remain bounded

#483 is a tooling-only F6 helper successor bound to the current QD2 product identity. Its hosted technical workflows are green apart from advisory review, but its contract explicitly says physical F6-A/F6-B remain separately authorized work.

#476 remains a qualification target / DO-NOT-MERGE candidate. #478 does not select an RC or authorize release.

No evidence in this cycle supports physical-F6 PASS, release closure, or autonomous release authority.

## Frozen / pre-release AX-21 comparison

Relative to the preserved AX-21 baseline:

- evidence provenance matters more: live and relayed identity evidence now have concrete dogfood consequences;
- diagnostic quality remains a limiter on autonomy: echo-loop activity and capability-specific WebVM failure show that "alive" is not one state;
- evidence-over-consensus is strengthened: internally coherent claim/release labels were insufficient without exact-subject and complete-set binding;
- human coordination remains measurable infrastructure: the identity ruling, O1 authorization, exact-head approvals and future F6 authorization are operator interventions;
- negative results remain scientifically useful and should remain append-only.

P5 remains unchanged: #349 is still open/draft at `625e1ce97919098dbe9d586ffcaf4b2a94257184`; this check-in found no valid post-intervention replay of the frozen operator-friction question.

## Operator interventions to count

- owner ruling on relayed identity versus seat recovery;
- separate O1 owner authorization;
- exact-head maintainer approval on #485;
- owner-authorized QD2 freeze break recorded by #476;
- future exact-head re-approval after source-head movement;
- future physical-F6 authorization.

These should not be hidden inside a generic "swarm completed" metric.

## Candidate queue

- `RES-UP-EVIDENCE-PROVENANCE-CLASS-001`
- `RES-UP-SEAT-ECHO-LOOP-001`
- `RES-UP-BOOTSTRAP-METADATA-MINIMIZATION-001`
- `RES-UP-SOURCE-REVISION-IDENTITY-001`
- `RES-UP-CLAIM-EVIDENCE-BINDING-001`
- `RES-UP-RELEASE-SET-COMPLETE-BINDING-001`
- `RES-UP-WEBVM-TIMER-BOUNDARY-001`
- `RES-UP-PROGRAM-STATE-AUTHORITY-001`
- `RES-UP-INTEGRITY-VOCABULARY-001`
- `RES-UP-POSTMERGE-LIVE-REPRO-001`
- `EXP-AX21-RELAYED-IDENTITY-01`
- `EXP-BOOTSTRAP-METADATA-01`
- `EXP-WEBVM-WAIT-273`

These are candidates, not accepted requirements.

## Paper-safe conclusions

Supported:
- source identity, task/program state, claim state, release state and runtime health require separate evidence;
- live and relayed identity evidence are useful but not interchangeable;
- repeated output can coexist with loss of useful seat responsiveness;
- internally consistent control/release states can remain claim-invalid when evidence binding is incomplete;
- mission success can coexist with failure of an independent runtime capability;
- green sub-gates do not override a red exact-head aggregate gate;
- externally integrated source fixes still need live reproduction if the claim concerns the live journey;
- preserving negative/superseded evidence improves longitudinal interpretability.

Not supported:
- general RESIDUAL security;
- exploitability from the AUD-1 metadata observation;
- fleet-wide Shared Comms qualification;
- equivalence of relayed and fresh identity;
- physical F6 success;
- P5 operator-friction improvement;
- a known WebVM timer root cause;
- current-head Program Control qualification;
- live provider-sign-in success solely from #485 merge;
- sustained autonomous recursive development;
- v1 release closure.

## Next highest-value evidence

1. Preserve the repeated-output/unanswered-dispatch episode, the relayed identity receipt digest/provenance class and the eventual human ruling as one bounded observation.
2. Preserve both REQ-LP-1 receipts and exact probe semantics.
3. Retain a redacted bootstrap schema comparison under a frozen allowlist.
4. Run unchanged #481 dogfood retests after integration rather than closing findings from CI.
5. Diagnose #484's deterministic Qualification-v1 failure without inheriting predecessor evidence.
6. Run `EXP-WEBVM-WAIT-273` against a frozen build and preserve unsupported as well as failing paths.
7. Run the deployed real provider-sign-in journey on current main before claiming live-provider restoration.
8. Keep physical F6 behind exact-helper review and separate owner authorization.
9. Run the frozen P5 comparison only after the intervention is genuinely integrated/qualified.

**Disposition: MATERIAL UPDATE — PRESERVE.**

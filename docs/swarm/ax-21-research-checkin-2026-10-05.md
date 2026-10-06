# AX-21 research check-in — 2026-10-05

**Status:** append-only research maintenance record.
**Authority effect:** none. This record grants no merge, release, deployment, security, autonomy, or acceptance authority.

## Evidence boundary

Reviewed current repository state and retained October 5 swarm/review evidence. Observations and interpretations are separated below. Historical failures and superseded recommendations remain preserved.

## Material observations

### Mission Control / MissionSync

PR #524 is now an owner-required v1 lane. Its bounded local evidence includes 52 distinct tests with zero skips, loopback Station-schema integration, and offline UI fixtures; installed Hermes/OpenClaw gateways were not part of those native tests.

Retained work reproduced multiple failure classes on the exact candidate lineage: queue-drain deadlock, oversized-context stalling, and one invalid report blocking later reports. A report/fanout size mismatch also remained. Later repair work does not erase those negative observations.

Interpretation: cross-harness synchronization needs explicit backpressure, per-report failure isolation, bounded context behavior, and size-consistent fanout semantics. Presence of a journal/outbox alone is not evidence of liveness under saturation or malformed input.

### Source qualification versus installed artifact

PR #527 passed its source scenarios but initially failed after wheel installation because authority-kernel measurement inputs expected from the repository were not present in the installed artifact. A task could reach review but could not complete the receipt/integration path.

The successor packaged the required measurement inputs with an integrity manifest and removed ambient-location fallback. Fresh exact-head evidence reports source tests, installed-wheel scenarios, and post-install file rehashing passing on Python 3.11 and 3.13. The candidate still explicitly records installed-native proof, independent-install proof, and release authorization as false.

Falsified hypothesis: source/editable qualification is not sufficient evidence for an installed artifact when authority-bearing measurement inputs can be omitted by packaging.

### Receipt applicability versus receipt integrity

The #527 audit reproduced the legacy receipt/current-kernel gap at cache acceptance. PR #529 makes the active authority-kernel identity part of cache reuse and keeps legacy receipts inspectable but non-authorizing for reuse without the current binding.

Interpretation: structural integrity and current applicability are different properties. A valid historical receipt is not automatically current authority evidence.

### Protected Factory change — superseded recommendation and retained negative result

An initial candidate-bound review of the protected worker-contract change recommended a bounded ownership-pin advance after extensive differential and focused testing. A later review found a malformed-input counterexample on the same exact protected blob and explicitly superseded that recommendation. The proposed pin PR #532 was withdrawn and retained as a negative specimen.

The observed regression is bounded: diagnostic classification can fail before mandatory termination/audit side effects complete for malformed public-API labels. The inspected runtime/broker call sites use ordinary string labels, so this is not evidence of a remotely reachable worker escape.

Important measurement: the withdrawn proposal had a large green focused test set and hundreds of differential comparisons, yet the later counterexample remained valid.

Falsified hypothesis: broad green testing over the expected typed denial vocabulary establishes malformed-input fail-closed robustness.

Paper-relevant interpretation: fail-closed behavior must include mandatory side-effect ordering, not only terminal state or error vocabulary. Diagnostic metadata must not interfere with required stop/audit behavior.

### Supersession propagation contradiction

PR #530 and descendant #531 still inherit the exact protected blob that the later #527 review marked DO-NOT-ADVANCE. Their current technical workflows are broadly green. Therefore current workflow freshness and descendant HEAD identity are insufficient by themselves for promotion after a later invalidating finding on an unchanged inherited input.

Interpretation: evidence freshness is transitive through dependency and ancestry relationships. Negative findings and superseding reviews need to propagate mechanically to all descendants that retain the affected input.

### Qualification-apparatus isolation

An earlier deterministic failure in the #530 lineage was localized to test collection: retained versioned INJ batteries exposed overlapping import names and were collected into one interpreter, and one retained harness used a workspace path assumption unsuitable for CI. The successor isolates each retained battery in its own subprocess while keeping all suites mandatory.

Interpretation: this was a qualification-apparatus isolation defect, not evidence that the product behavior under the retained batteries failed. Candidate failures and evaluator/test-harness failures remain separate provenance classes.

### Installed-native MissionSync remains unexecuted

PR #531 defines a fail-closed evidence schema and validator for exact Hermes/OpenClaw runtime identity, actual native hooks, context delivery, negative identity controls, reconnect/restart behavior, false-completion non-authority, a real two-conversation same-task demonstration, ordinary Station verification, native lifecycle proof, an independent reviewer, and immutable evidence hashes.

Current CI demonstrates the evidence-contract software. It does not demonstrate those native events. Missing or ambiguous native observations remain EVIDENCE_INCOMPLETE.

## Swarm / host observations

No fresh frozen fleet receipt was found that justifies a new READY/DEGRADED/DOWN count.

- Scout and Wrench supplied DBOX/DELL plans, but the retained record does not show those plans executed and independently qualified.
- The reported LEGION local-Qwen result retains a provenance/timing question and unresolved explicit cloud-disabled evidence.
- Earlier isolated agent2/forgev2 fallback results remain bounded to the tested profiles and operator-assisted setup; they do not establish fleet-wide or same-admitted-task continuity.
- Mason's kernel-v3 assignment was acknowledged, but no completed kernel-v3 repair artifact was observed in the retained record.
- Swarm-access interruptions were narrowed to an execution-session approval stage; the evidence did not establish an authentication failure, and a later same-route read succeeded. Sustained access reliability remains unestablished.

## Release / reproduction findings

### Independent install

PR #517 is technically strong on its exact head and includes a poisoned-checkout negative control, but its own independence result remains INDEPENDENT_INSTALL_UNVERIFIED. Repository-controlled CI is not an external independent install.

Correct claim: packet/mechanics qualified; external installation and adoption unproven.

### ASC-001 / Thesis v2

PR #526 is a coherent prospective research specification for bounded authority-surface completeness, Effective Authority Environment drift, bypass campaigns, and cross-harness capstones. It preserves UNMAPPED and explicitly avoids universal non-bypassability claims.

No empirical ASC-001 non-bypassability result exists in this check-in.

Correct claim: research-spec consistent; authority-surface completeness not demonstrated; not adopted into v1.

### Remaining evidence gaps

The reviewed evidence still lacks a completed preregistered WebVM reliability campaign, heavyweight Firefox-WebVM qualification, 24-hour soak evidence, physical F6-A/F6-B execution, installed-native MissionSync proof, and the applicable independent security/privacy/durability review.

No new valid P5 after-condition was found. Human scope, protected-change review, withdrawal of the pin recommendation, native-test authorization, and independent-review requirements remain operator interventions rather than autonomous completions.

## Falsified hypotheses

1. Source PASS implies installed-artifact PASS.
2. Receipt integrity is sufficient for current cache authority without current-kernel binding.
3. Green typed-input denial tests establish malformed-input fail-closed behavior.
4. A green ownership gate after a pin update proves the protected change is promotable.
5. Fresh descendant CI remains sufficient after a later invalidating finding on an inherited protected input.
6. Any deterministic-regression failure necessarily indicates product failure.
7. Native-proof tooling is equivalent to native proof.
8. Independent-install mechanics PASS proves external installation/adoption.

## RES-UP / ImprovementSpec candidates

- RES-UP-SOURCE-TO-WHEEL-NORMATIVE-BINDING-001
- RES-UP-RECEIPT-KERNEL-BINDING-001
- RES-UP-DENIAL-DIAGNOSTIC-NONINTERFERENCE-001
- RES-UP-PROTECTED-BLOB-NEGATIVE-FINDING-BINDING-001
- RES-UP-SUPERSESSION-PROPAGATION-001
- RES-UP-QUALIFIER-NAMESPACE-ISOLATION-001
- RES-UP-MISSION-SYNC-BACKPRESSURE-001
- RES-UP-NATIVE-EVIDENCE-CONTRACT-001

Candidate experiments:

- EXP-DENIAL-MALFORMED-LABEL-01 — systematically vary denial-label types and require mandatory stop/audit semantics to remain invariant.
- EXP-SUPERSESSION-LAG-01 — introduce a late candidate-bound negative finding on an inherited protected input and measure dependent-state invalidation latency.
- EXP-MISSION-SYNC-BACKPRESSURE-MATRIX-01 — queue saturation, oversized context, malformed report, fanout size, and reconnect matrix with liveness/order/loss measurements.
- EXP-NATIVE-MISSION-TWO-CONVERSATION-01 — execute the existing #531 contract on explicitly authorized exact Hermes/OpenClaw test installations with a non-executor verifier.

## Baseline comparison

The frozen/pre-release AX-21 baseline remains the comparison point. This cycle adds installed-artifact divergence, current-kernel receipt applicability, denial-path diagnostic interference, qualification namespace isolation, and supersession-propagation observations. It does not establish reduced operator burden, fleet-wide continuity, physical lifecycle correctness, whole-system security, or sustained autonomous recursive development.

Older negative results remain preserved. Later software success does not rewrite them, and earlier sandbox/bootstrap qualification does not become native/fleet evidence.

## Paper-safe conclusions

1. **Evidence freshness is transitive through dependency and ancestry relationships.** An exact-head PASS can become insufficient for promotion when a later candidate-bound finding invalidates an unchanged protected input inherited by that head.
2. **Fail-closed claims must include mandatory side-effect ordering.** A terminal state alone is not sufficient if required termination/audit effects can be skipped by diagnostic processing.
3. **Distribution packaging is part of the authority-bearing experimental subject.** Source identity alone did not establish installed behavior when normative measurement inputs were omitted.
4. **Evaluator failures and candidate failures require separate provenance.** The INJ collection problem is an example of the qualification apparatus failing rather than the product under test.

These conclusions do not establish non-bypassability, remote exploit resistance, autonomous release operation, fleet-wide failover, installed-native MissionSync correctness, or v1 release readiness.

## Source pointers

- https://github.com/ninja-ops-guy/residual-agent-harness/pull/524
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/527
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/529
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/530
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/531
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/532
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/517
- https://github.com/ninja-ops-guy/residual-agent-harness/pull/526

This record intentionally preserves failed candidates and superseded recommendations rather than normalizing them into the successor state.

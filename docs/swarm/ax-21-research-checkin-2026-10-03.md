# AX-21 research check-in — 2026-10-03

Status: append-only research maintenance record. This record separates observed evidence from interpretation and does not grant merge, release, security, deployment, or autonomy authority.

## Evidence boundary

Accepted main observed: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`. No formal GitHub release was present. Reviewed current repository evidence from #427, #512, #513, #514/#515, #516, #517, and the frozen #349 comparison line.

## Material findings

### Verifier observation finalization

Observed: in #516 predecessor `a0d2a727fa90b84cf37e285e5bce6df7c8520ad1`, the verifier sends the current criterion result to the observation callback before handling a callback exception and changing the returned criterion result to FAIL. The test establishes that the returned report fails closed, but does not establish that an external callback cannot retain the earlier payload before throwing.

The current #427 ledger describes this stronger property as repaired. That claim is not supported by the inspected implementation.

Interpretation: local report failure and external observation finalization are distinct evidence properties.

Candidate: `RES-UP-VERIFICATION-OBSERVATION-FINALIZATION-001`.

### Exact-head proposal scope and qualification

Observed: #516 now points to `3d52cd4a652c47ebab4ba518c1c05f175dcdd156`, with 2 commits and 13 changed files, while its description still says it contains only five non-Factory files. #427 still binds its READY_FOR_REVIEW entry to older #516 head `a0d2a727...`.

Current #516 Qualification-v1 is FAIL because the deterministic gate is red. Command Station and controller/provider Python 3.11 runs each report 1,205 tests with 2 failures and 22 skips. The failures are in the Pages main-qualification contract: exact revision identity binding and retained generated browser-proof expectations. Other named technical gates including Factory ownership, Control Plane, clean install, measured-evaluation binding, Browser VM Demo CI and Open Core Boundary are green.

Interpretation: PR prose and ledger state can become stale when a head moves. Exact-head source, changed-file set and aggregate qualification must dominate older summaries. Green sub-gates do not override aggregate FAIL.

Candidates:
- `RES-UP-PR-SCOPE-INTEGRITY-001`
- `RES-UP-LEDGER-HEAD-FRESHNESS-002`
- `RES-UP-WORKFLOW-EVIDENCE-SUBJECT-001`

### Protected ownership gate

Observed: #512 exact head `4dc24685684e3cef9fee6a1d1113cd7abc087d9d` ran 1,202 Python 3.11 tests with one failure and 22 skips. The sole failure was the protected Factory ownership manifest check; three protected paths changed without an authorized baseline advance. Dependent qualification surfaces remained red.

Interpretation: this is governance-refusal evidence rather than an environment-only failure. The control prevented otherwise-tested code from silently acquiring protected ownership authority.

### AUTH qualification

Observed: #513 exact HEAD `39a0d638c8011ab6db3d080b4186e0c94ee522b1`, TREE `f38d2e47a80dce203ec1a515114fbf11b61121cf`, reports the six declared authority-coercion invariant cases PASS with zero skips and zero unknowns. Bound evidence hashes, expected/observed failure codes, and expected/observed fail-closed states matched. Major exact-head technical workflows are green; maintainer approval and independent human review remain unsatisfied.

Interpretation: this is bounded deterministic qualification of the declared cases on the exact subject, not a general security or release claim.

### AWQ-001 research protocol

Observed: #514 and issue #515 add a prospective AX-21 adversarial-worker qualification protocol and evaluator scaffold. The protocol separates containment from utility and requires a deterministic control phase before any model trial can be interpreted. No live model result is recorded by this check-in.

Interpretation: this is new research infrastructure, not empirical containment evidence.

### Onboarding and reproduction

Observed: #517 exact head `c9f0897aea10e3ab5f15abf53ac0eb4f6b66d6c8` has the major technical workflows green. Its source-checkout baseline records 7 focused onboarding tests PASS, 2 real-CLI first-run tests PASS, an offline example with 2 accepted obligations and zero model calls, a 31-file Open Core import-boundary PASS, and a 60-file export with 10 smoke imports PASS. It also records stale current-state documentation and an unsupported package-install quickstart assumption. No external participants have been contacted and no pilot outcomes exist. Independent released-artifact installation remains unproven.

Interpretation: source-checkout reproducibility evidence does not establish release-artifact installation or adoption.

## Baseline comparison

No new frozen live-swarm receipt was found in the available evidence that supersedes the earlier seat/failover/Shared-Comms observations. Orpheus Runner R0 remains prospective.

The pre-release controls remain unchanged:
- accepted main remains `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`;
- #349 remains open/draft, so there is no new valid P5 after-condition or measured reduction in operator burden;
- no formal GitHub release exists, so there is no final release-tag AX-21 cutover;
- prior sandbox/bootstrap-only and negative continuity results retain their original scope.

## Paper-safe conclusion

This cycle strengthens the conclusion that an authority-bearing PASS is not merely a value. It must be finalized and bound to an exact subject, current lifecycle state, evidence path and composition. A returned report can fail closed while an earlier external observation remains ambiguous; a PR number can stay constant while its exact scope changes; and many green sub-gates can coexist with an authoritative aggregate FAIL.

Nothing here establishes whole-system security, sustained autonomous recursive development, fleet-wide failover correctness, physical lifecycle correctness, external-user adoption, or v1 release readiness.

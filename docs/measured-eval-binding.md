# Measured evaluation to M4 acceptance binding

`residual/eval_frozen/acceptance_binding.py` binds a measured run of the
frozen R0-R5 evaluation harness (`residual/eval_frozen`, PR #86) to the
post-#63 M4 acceptance surface. It rebuilds the mechanism intended by the
closed PR #71 against the current API and treats the four P1
evidence-integrity defects found in that review as hard requirements.

## Requirements and how they are enforced

### 1. Fresh execution identity / anti-replay

`FreshRunRegistry` is the only issuer of run identities. `begin_run` emits a
Station-signed, hash-chained `RunIdentityRecord` (`fresh=True`) and rejects
any run id that already exists — a replay can never obtain a second fresh
record. `resume_run` recovers a run operationally but appends a signed
`fresh=False` record; `fresh_record()` then refuses that run forever. Resume
never converts old evidence into fresh execution. `verify_chain()` rejects
broken chains and forged records (invalid signatures fail closed).

### 2. Authenticated scheduler/topology evidence over the full run interval

`SchedulerTopologyEvidence` wraps typed `ReadyDagSnapshot` /
`SchedulerMeasurements` / `SchedulerAction` values in a Station-signed
envelope and is only constructible through `SchedulerTopologyEvidence.issue`,
so self-reported topology has no valid signature and is rejected. Each
measurement carries an observation timestamp; the envelope requires the first
observation at or before `run_started_ns` and the last at or after
`run_ended_ns`. Partial-interval evidence fails closed at construction, and
the binding cross-checks the envelope interval against the run. Measurements
must hash-bind to supplied snapshots and actions to supplied measurements.

### 3. Exact frozen-workload to Factory-task mapping

`WorkloadTaskMapping.for_workload` requires an explicit, injective mapping
covering every evaluation-slice task of the frozen workload — incomplete or
over-broad mappings fail at construction. `assert_population` requires the
measured M3 receipt task population to equal the mapped Factory task
population exactly: missing, extra, or duplicate tasks reject the run. An
unenforced task population is a P1 and fails closed.

### 4. Qualified verifier boundary; UNKNOWN fails closed

`VerifierQualification` can only be constructed from a PASS/exit/rc=0 probe
of the `linux-userns-isolated-v1` `m4_sandbox` boundary; UNKNOWN or ERROR
probes fail closed at construction. Final acceptance additionally requires a
Station-signed M4 `IntegrationReceipt` with
`evidence_level="isolated_candidate_verification"`, binding the exact
measured M3 receipt set in order, whose every verification result is a clean
pass/exit/0 inside the isolated boundary. `development_fixture` receipts and
the `trusted_fixture_unsandboxed` boundary are rejected even if relabelled.
Any UNKNOWN/unavailable verification outcome rejects acceptance outright —
`attribution` is always null in the issued artifact; nothing is ever
attributed through an unqualified verifier.

## Prerequisites (fail closed)

`validate_prerequisites` requires, before anything is issued:

- a PASS clean-install qualification report (PR #100,
  `verifier/v3/qualify_clean_install.py`), matching the required commit when
  one is supplied; and
- a passing Factory ownership gate report (PR #95,
  `verifier/v3/check_factory_ownership.py`).

Absent, malformed, or failing prerequisite evidence rejects the binding.

## Signed final-acceptance artifact

`validate_and_issue_acceptance` returns a machine-readable JSON artifact
(`residual.eval-frozen-final-acceptance.v1`) signed with the existing
Ed25519 `StationIdentity` infrastructure (the same signing primitive used by
M3 WorkerReceipts and M4 IntegrationReceipts — no protected path is
modified). `verify_acceptance_artifact` independently verifies the artifact
against a Station public key.

## Non-claims

- This module produces a **binding artifact**, not live empirical results.
  It does not itself run models, workers, or the isolated verifier.
- It does **not** close issue #63 or any other issue.
- It does **not** authorize R0-R5 confirmatory claims. Those require the
  full gate sequence: clean-install qualification, ownership gate, a fresh
  measured execution through the isolated M4 boundary with authenticated
  scheduler evidence, and independent review.
- The Station signature proves integrity under the signing key only. Trust
  in that identity requires an externally pinned Station public key; an
  ephemeral local identity proves nothing to third parties.

## Tests

`tests/test_eval_frozen_acceptance_binding.py` covers each requirement as
negative tests: replay rejected, resumed evidence rejected as non-fresh,
forged chain rejected, unauthenticated/partial/mismatched topology rejected,
divergent/duplicate/incomplete task population rejected, UNKNOWN verifier
outcome and unqualified probes rejected with no attribution, fixture-lane
receipts rejected, and prerequisite gates failing closed.

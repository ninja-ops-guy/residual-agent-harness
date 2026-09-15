# Measured evaluation to M4 acceptance binding

`residual/eval_frozen/acceptance_binding.py` binds a measured run of the
frozen R0-R5 evaluation harness (`residual/eval_frozen`, PR #86) to the
post-#63 M4 acceptance surface. It rebuilds the mechanism intended by the
closed PR #71 against the current API and treats the four P1
evidence-integrity defects found in that review as hard requirements. The
statements below are precise; where a property is operator-asserted rather
than cryptographically enforced, it says so.

## Requirements and how they are enforced

### 1. Fresh execution identity / anti-replay

`FreshRunRegistry` is the only issuer of run identities. `begin_run` emits a
Station-signed, hash-chained `RunIdentityRecord` (`fresh=True`) and rejects
any run id that already exists in the registry — a replay cannot obtain a
second fresh record. `resume_run` recovers a run operationally but appends a
signed `fresh=False` record; `fresh_record()` then refuses that run, so
resumed evidence cannot support acceptance. `verify_chain()` rejects broken
chains and forged records (invalid signatures fail closed).

**Cross-process freshness:** `FreshRunRegistry.export_chain()` serializes the
signed chain (`residual.eval-frozen-run-identity-chain.v1`), itself signed
over the ordered record list. The final artifact carries a
`run_identity_chain` reference (schema, head record hash, record count, and a
retention requirement). A third party holding the chain export plus the
Station public key verifies freshness with
`verify_acceptance_artifact(artifact, key, chain=...)`: export signature,
per-record signatures, linkage, no replayed run id, the artifact's record
being a FRESH record for the run id, and the chain head matching the
reference. **Without the chain, freshness is unverified** — signature-only
verification deliberately still succeeds and callers requiring freshness
must retain and present the chain.

**Enforced vs asserted:** the registry enforces, verifiably from the signed
chain alone: run-id uniqueness, chain linkage, record authenticity, and
resume-bars-acceptance. All timestamps (`issued_at_ns` in chain records and
the artifact, observation timestamps, `probed_at_ns`, the run interval) are
**operator-asserted**: the Station has no trusted clock, so caller-supplied
time is unavoidable; the signature proves only that the Station signed a
payload *claiming* that time. The artifact lists these fields explicitly in
`operator_asserted_fields` / `registry_enforced_fields`.

### 2. Authenticated scheduler/topology evidence spanning the run interval

`SchedulerTopologyEvidence` wraps typed `ReadyDagSnapshot` /
`SchedulerMeasurements` / `SchedulerAction` values in a Station-signed
envelope and is only constructible through `SchedulerTopologyEvidence.issue`,
so self-reported topology has no valid signature and is rejected. Coverage
rule (fail closed at construction): the earliest observation must be at or
before `run_started_ns`, the latest at or after `run_ended_ns`, **and at
least one observation must lie strictly inside**
`(run_started_ns, run_ended_ns)`. Endpoint-only coverage — observations at
both boundaries but none during the run — is rejected: it does not show the
topology was observed while the run executed. This is a minimal coverage
floor (one interior observation satisfies it), not a density guarantee; the
binding also cross-checks the envelope interval against the run.
Measurements must hash-bind to supplied snapshots and actions to supplied
measurements.

### 3. Exact frozen-workload to Factory-task mapping

`WorkloadTaskMapping.for_workload` requires an explicit, injective mapping
covering every evaluation-slice task of the frozen workload — incomplete or
over-broad mappings fail at construction. `assert_population` requires the
measured M3 receipt task population to equal the mapped Factory task
population exactly: missing, extra, or duplicate tasks reject the run. An
unenforced task population is a P1 and fails closed.

### 4. Station-qualified verifier boundary; UNKNOWN fails closed

`VerifierQualification` is a **Station-signed probe receipt bound to the run
id**, constructible only through the signed issuance path
(`VerifierQualification.issue` / `from_isolated_result`, both requiring a
`StationIdentity`); direct construction is blocked, and the binding verifies
the Station signature, the run-id binding, and that `probed_at_ns` lies
inside the run interval. Fabricated or foreign-signed qualifications fail
closed. Only a `pass`/`exit`/rc=0 probe of the
`linux-userns-isolated-v1` `m4_sandbox` boundary can be issued; UNKNOWN or
ERROR probes fail closed at issuance. "Qualified" means the issuing Station
attests the probe passed — it is **not** an independent third-party
qualification.

Final acceptance additionally requires a Station-signed M4
`IntegrationReceipt` with `evidence_level="isolated_candidate_verification"`,
binding the exact measured M3 receipt set in order, whose every verification
result is a clean pass/exit/0 inside the isolated boundary.
`development_fixture` receipts and the `trusted_fixture_unsandboxed`
boundary are rejected even if relabelled. Any UNKNOWN/unavailable
verification outcome rejects acceptance outright — `attribution` is always
null in the issued artifact.

## Prerequisites (fail closed)

`validate_prerequisites` requires, before anything is issued:

- a PASS clean-install qualification report (PR #100,
  `verifier/v3/qualify_clean_install.py`), commit-matched to
  `required_commit` when one is supplied; and
- a passing Factory ownership gate report (PR #95,
  `verifier/v3/check_factory_ownership.py`) whose `pinned_at` **equals the
  current baseline manifest's pin** and whose `protected_files` count equals
  the manifest's file count (default: the on-repo
  `verifier/v3/factory_ownership_baseline.json`; an explicit baseline mapping
  may be supplied). A stale, absent, or weaker pin fails closed.

**Documented ownership rule:** the #95 baseline pin legitimately *predates*
the evaluated commit, so the ownership report is deliberately NOT
commit-matched. The passing report asserts that no protected-path blob
changed relative to that pin in the tree the checker ran on. Commit
*ordering* (pin ≤ required_commit) cannot be derived from commit SHAs alone
and remains operator-asserted.

**Authentication status:** both prerequisite reports are *unauthenticated
inputs* — nothing signs them. Their integrity in the final artifact derives
solely from the Station signature over their SHA-256 digests
(`prerequisite_reports_sha256`). An operator who can feed the binding a
forged report can get it signed into an artifact; the artifact then
accurately records *which* report digests were accepted, so the reports
themselves must be retained for audit.

## Signed final-acceptance artifact

`validate_and_issue_acceptance` returns a machine-readable JSON artifact
(`residual.eval-frozen-final-acceptance.v1`) signed with the existing
Ed25519 `StationIdentity` infrastructure (the same signing primitive used by
M3 WorkerReceipts and M4 IntegrationReceipts — no protected path is
modified). `verify_acceptance_artifact` independently verifies the artifact
against a Station public key, and additionally verifies run freshness when
the retained run-identity chain is supplied.

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
  ephemeral local identity proves nothing to third parties. Timestamps are
  operator-asserted; the signature does not prove their accuracy.

## Tests

`.github/workflows/measured-eval-binding.yml` runs these pytest-style tests
explicitly (ordinary unittest discovery does not collect them). The workflow
also retains adjacent regression output, including namespace skips; those
skips are evidence gaps, not live M4 qualification. Required-check enforcement
is a separate maintainer setting documented in the
[integration handoff](status/INTEGRATION_HANDOFF.md).

`tests/test_eval_frozen_acceptance_binding.py` covers each requirement as
negative tests: replay rejected, resumed evidence rejected as non-fresh,
forged/tampered/reordered chain rejected, unauthenticated/partial-interval/
**endpoint-only** topology rejected, divergent/duplicate/incomplete task
population rejected, UNKNOWN verifier outcome and unqualified probes
rejected with no attribution, directly-constructed and foreign-signed
verifier qualifications rejected, run-id/interval misbinding of the probe
receipt rejected, fixture-lane receipts rejected, mismatched/weaker
ownership pins rejected, prerequisite gates failing closed, and freshness
verifiable only with the retained chain.

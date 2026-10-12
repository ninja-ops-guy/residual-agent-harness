# Offline supervision journal bridge

This additive slice implements the offline bridge proposed in
RC_SUPERVISION_INTERFACES.md. That earlier design document and all six reviewed
soak/supervision files remain byte-identical to Library version 5. The added
module is scripts/qualification_rc_bridge.py; wired tests are in
tests/qualification/test_rc_bridge.py. No production runner or publisher is wired.

## Selection and admission

The external caller selects a SelectedManifest, frozen supervision Requirements,
and a journal epoch token. selection_identity() binds manifest digest, profile
byte digest, requirements digest, run_id and epoch. The caller must supply its
expected canonical selection SHA-256 to construction and replay; journal contents
cannot replace it. This is caller selection, not independent authority attestation.

Bridge constructs Binding.from_selected_manifest and calls nonexecuting admit;
the fixture adapter contains a raising body that must not execute. Each tick
revalidates admitted installation/input bytes before running the owned Supervisor
and after it returns, before appending or committing the returned observation.
Completed finish() and tick() calls revalidate the installation without polling.
Detected drift latches failure and retains only previously committed receipts.
No third-party report submission or adapter cumulative-count API exists.
The bridge is synchronous and single-caller; reentrant ticks fail closed.

## Journal and progress

The injected journal has only append(bytes) and fail(bytes) operations. Both must
return None after success or raise on failure. Records are immutable canonical
JSON bytes; reports returned to callers are copied. No Journal.publish, finalize,
os.link, workload launcher or live provider is called. A journal adapter is trusted
storage; acknowledgment does not prove durability, atomicity or authenticity.

Start records bind selection and missing capabilities. Observation records retain
the validated cumulative receipt history from Supervisor, bound to selected target
and driver generation identities. Progress is derived from unique, ordered accepted
receipts, with task/attempt/nonce/sequence/result/payload correlations and bounded
timestamps. A tick may add at most one receipt. Replay validates the same constraints,
prior receipt immutability, exact record fields, sequence, external selection and
missing capability declarations. Reordering, duplicate result IDs, forged count
claims, changed generations and false complete states are rejected.

Pending polls legitimately have no new outcomes. Explicit finish before the full
plan latches missing_outcomes; replay(require_complete=True) rejects incomplete
plans. Deadline failure comes from the actual Supervisor. Completing the finite
plan yields plan_observed_complete only: elapsed_soak_satisfied and rc_qualified
are always false, even when the selected profile requires 86400 seconds.

## Failure and storage boundaries

The first failure is sticky. Supervision failures retain their reason, task index
and last monotonic observation; journal errors use bounded fixed reason codes.
No later tick/cancel/interruption advances progress or replaces the first failure.
Admission failures precede polling. Progress is committed in the bridge only after
validated append acknowledgment and a callback failure-latch check.

A separate failure record carries the last acknowledged record count. Replay
validates any single unacknowledged tail record but excludes its receipts from
progress. This covers a fixture sink that appends and then raises, or cancels
during append. A malformed/partial tail is rejected outright. If fail() also raises,
the live run remains failed and failure_recorded is false; no durable failure claim
is made. Consumers must supply a present failure sidecar. This slice cannot prove
its absence or recover an unacknowledged append after sudden process loss. Those
cases require a future durable storage/commit protocol and independent observation.

## Verification and remaining wiring

Tests integrate actual SelectedManifest loading, Binding admission, Supervisor and
Bridge with synthetic wheel/configuration/profile, clocks and handles, and an
in-memory fixture journal. They cover wrong external selection, installation drift,
wrong run/task/attempt/nonce/generation, duplicate/missing outcomes, mutable aliases,
malformed records, write failures before/after append, failure-sidecar faults,
callback cancellation/interruption, reentrancy and finite-plan versus 24h policy.
The full permitted offline suite retains the two blocked actual-sealing skips and
guards os.link to assert zero calls. Logs and exact counts ship in the review bundle.

Fresh B1 result: 93 tests discovered, 91 PASS, two actual-sealing SKIP,
zero failures/errors and zero os.link calls; 20 passes are bridge tests.
The B1 regressions mutate installed adapter bytes inside each role's initial and
completion-boundary polls on the final task, after one receipt has committed.
They leave wheel/configuration bytes unchanged and use the actual Binding validator.
They verify failed replay, unchanged committed progress, sticky failure and no
further polling. Late drift after plan completion also fails finish()/tick().
The first combined run retained 17 candidate_already_loaded fixture errors.
The corrected test fixture temporarily isolates and restores imported candidate
modules, and an explicit negative test confirms the real admission guard remains
active. No production admission check was changed or disabled.

Validation checks are observations of filesystem bytes, not continuous filesystem
immutability. Mutation after a check, mutation restored between checks, or mutation
inside a journal storage callback is not independently excluded by these snapshots.
report() returns historical copied state rather than performing fresh validation;
finish()/tick() revalidate completed state. Replay checks historical records and
selected inputs; it does not attest a currently installed runtime. All paths retain
rc_qualified:false and elapsed_soak_satisfied:false.

Real-runtime wiring remains absent: independent OS process/image/generation checks,
workload attribution, poll preemption, an external watchdog and observer lease,
durable failure/commit storage, actual sealing, and elapsed soak/resource/source
gates. All remain explicit missing capabilities or existing admission limitations.
The old soak driver, journal schema, hardlink publisher, acceptance rules, protected
code and closure ledger are unchanged. No actual runtime/native/provider campaign,
network/WSL retry, installation, permission change or remote publication occurred.

# AUD-1 follow-up: admission revocation and stalled heartbeat

Status: candidate remediation; independent review, exact-head CI, physical F6 and release approval remain required.

Parent: `8df77b832b3839ccd2a6944a65760ce3ab10dc9c` (#399).
Parent tree: `f8143fedebbfe27b3c0a7925259cdaa5e9eff91a`.
Observed accepted main at start: `91d32fd8b713c68c1cd2e473013c9e1c33b93572`.

This work was performed in a separate ephemeral workspace. It does not change the parent branch, #403 helper, R4 checkout, R4 services, credential stores, or sealed experiments. No live fleet or physical tunnel was accessed. No approval, merge, release, canary, or model call is claimed.

## Reproduced defects

### AUD1-C1: authorization checked before a delayed request body

On the exact parent software, three new real-loopback HTTP regressions failed:

1. Authenticate a heartbeat, pause before body read, rotate credentials using the operator API, then release the body. The old heartbeat succeeds instead of being rejected.
2. Apply the same schedule to a result submission. The stale request can reach candidate verification after rotation.
3. Disable remote workers while an authenticated heartbeat waits before body read. That request still succeeds.

These are authenticated-worker revocation races, not unauthenticated compromise or a demonstrated tenant escape. Ordinary sequential rotation tests do not exercise this schedule.

### AUD1-C2: the deadline depends on the failed heartbeat returning

The parent marks authority lost only from the heartbeat request's exception handler. A blocked request does not reach that handler. The worker's generation loop therefore misses its grace deadline. The original regression timed out waiting for WorkerAuthorityLost and is retained as an ERROR, not relabelled PASS.

A returning late heartbeat could also refresh last-success after an unobserved deadline. Successful CI on the earlier corpus remains historical evidence, but does not establish these newly tested properties.

## Repair

`WorkerAccessGate` provides concurrent worker admissions with a writer-preferred control barrier. The HTTP request body is read before admission. Inside admission, the server re-reads current credential validity, scope and the enabled flag. Credential issuance, rotation and disable use the exclusive barrier.

Rotation/disable completion is the linearization boundary: already admitted requests drain before the control change completes, and queued/new requests cannot enter while it is pending. A stale auth snapshot cannot authorize work after completion. Separate projects retain concurrent verification; this is not a global exclusive lock around every worker operation.

Tradeoff: rotation can wait for already admitted bounded verification work. It is not preemption or rollback of an operation already in progress. The gate is single-Station-process synchronization, not distributed consensus or coordination between multiple Station processes sharing a database. Internal trusted callers must not acquire the gate while holding project/store locks, and gate contexts must not be nested.

The worker now checks a monotonic continuity deadline independently of heartbeat I/O. Heartbeat transport timeout is bounded separately, malformed ACKs do not renew authority, explicit 400/401/403 responses surrender, and a late ACK cannot revive an expired proof. Nonfinite/boolean timing inputs are rejected. The existing 60s heartbeat, 180s grace and 900s server lease defaults are not increased or shortened to manufacture physical evidence.

## Executed local validation

The container could not clone GitHub because DNS was unavailable. Instead, the GitHub connector downloaded retained exact-wheel artifact `10671967623` from Qualification-v1 run `35673263914`. The archive and wheel SHA-256 were checked before extracting their source. The artifact's source envelope identifies the exact parent commit/tree above. The server source blob was independently matched to GitHub.

- Archive SHA-256: `5159d888e9e31200d33c4de7a4aa0417b97c5ab24ae2e3055ab3e48b0b533225`.
- Wheel SHA-256: `4861159d2ef3f8a3c906a191deb2d2536ffea98ff328d3ddb96ec4fcb22e69f7`.
- Python 3.13.5; temporary SQLite/Git workspaces; fixture credentials and scripted providers only.
- First four probes on parent source: 3 FAIL and 1 ERROR (deadline timeout).
- Repaired expanded suite: 12 tests PASS, zero skips; covers concurrent admissions, writer ordering, exception cleanup, actual Station rotation/disable races, real loopback blackhole HTTP, suppressed late submission, transient recovery, malformed ACK and timing validation.
- Two separate source-reversion checks: restoring original server reintroduces rotation failure; restoring original worker reintroduces deadline failure.
- Real three-task Station demo: candidate creation, mechanical checks, scripted review, integration and export PASS; zero model calls.
- All three changed/new production modules parse successfully.

Local tests used the verified parent wheel source plus these exact changed modules and tests. This is not a full repository checkout test, hosted cross-version CI, physical multi-host F6, a blank-VM installation, live inference, or a 24h/72h soak. GitHub CI must qualify the published candidate separately.

## Research value and claim limits

OBSERVED: delayed authorization and blocking-I/O schedules expose defects not covered by the previous green sequential/exception-only tests.

INFERRED: fault campaigns should distinguish refused connections, blocked connections, delayed ACKs, and explicit revocation; these failure classes are not interchangeable.

NON-CLAIM: one passing candidate does not prove arbitrary network resilience, distributed identity isolation, or readiness of the full migration architecture. This is not R4 evidence.

## Next release actions

1. Independently review the successor diff and the revocation linearization policy; run exact-head repository CI without weakening gates.
2. Explicitly accept a new security candidate before changing any physical-helper target. #399 and #403 remain unchanged; older evidence remains bound to its original bytes.
3. Qualify the helper against the approved new candidate, then collect separate physical F6-A/F6-B bundles. The stalled-transport regression is additional software evidence, not a replacement for those bundles.
4. Obtain Mason's independent read-only F1/F2/F3/F4/F6 re-audit, followed by exact-head owner attestation and normal merge gates.
5. Requalify resulting main; reconcile shipping setup/docs fixes; freeze release artifacts; execute clean-environment recovery and the approved wall-clock soak policy before publishing v1.

Do not close #353 or announce production readiness from this implementation alone.

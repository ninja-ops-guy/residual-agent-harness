# Station ownership and shared exposure-boundary candidate

Status: implementation candidate, not CV-06 acceptance or an approved deployment profile.
Base: AUD-1 #438 at e815f33484352f100e11b8d075bb954a815244cc. The original branch remains unchanged.

## Scope

Acquire one data-directory owner before Store/schema/settings/startup recovery. Hold ownership through admitted Station operations, background jobs and attached Server lifetime. Reject competing same-directory processes before Store initialization. A bounded close timeout retains ownership and rejects new work rather than unlocking active work. Shutdown closes listeners before releasing Station ownership; constructor failures release their reservations.

Server construction now uses the same exposure validation as the existing AUD-1 CLI before bind or credential migration. This preserves the existing opt-in protected-proxy contract; it does not approve remote exposure for v1. The default localhost path binds literal 127.0.0.1. Actual supported profile selection remains a separate owner decision.

POSIX locking uses a persistent, regular, single-link, no-follow inode with nonblocking exclusive flock. It never truncates/writes/unlinks the lock; inherited child handles cannot explicitly unlock the parent's open-file description. Windows uses a global named-object existence guard; native Windows behavior remains unqualified by this Linux execution. Raw Store access and hostile same-user filesystem replacement, distributed filesystems and HA are outside this candidate's claim.

## API lifecycle

Use Station as a context manager or call close after Server.server_close and background work drain. close(timeout=...) is finite and fails explicitly with ownership retained if work remains; the caller may retry close after drain. A new Station is not a restart until the prior owner has ended.

Existing repository restart fixtures which instantiate a second Station while the first is still alive must be reconciled to an explicit close/crash boundary while preserving their stale-lease and recovery assertions. Full inherited suite and platform qualification remain required before acceptance. Do not weaken exclusion to accommodate a two-live-owner fixture.

## Local evidence

The exact runtime wheel from #438 was obtained via retained artifact 10804792879, archive SHA-256 a71574137583780a5bec82c9bdf0e31a92a2d290f20e78eadbcc50e93cb1e5bf; wheel hash/source binding were checked. Candidate files were overlaid on that packaged runtime, not a full repository checkout.

Command: PYTHONPATH=. python -W error::ResourceWarning -m unittest -v tests.station.test_station_ownership tests.station.test_station_boundaries tests.station.test_ownership_additional

39 methods passed, zero skips, Linux/Python 3.13.5. Includes real Station initialization/settings/recovery; cross-process exclusion; separate-directory controls; active-job timeout; thread-start failure; CLI/bind cleanup; guarded constructor and literal loopback controls; real Git/check/review/export demo with zero model calls; and close-before-restart stale-lease rejection.

A six-test challenge of the earlier local lock-only handoff found four failed assertions and one missing-API error, including destructive hard-link writes and inherited unlock. First failures are retained in the execution bundle. Two deliberate candidate reversions (shared lock; unlock while active) are caught by assertions. An initial mutation teardown race was retained and repaired with cleanup-only waiting; no acceptance expectation was changed.

The explicit-remote positive control intercepts the bind boundary; it does not open a public listener or prove proxy/TLS security. Local tests are not hosted CI, independent human review, physical F6, a selected AUD-1 successor, or release authorization. No tests of frozen/private packages, live credentials, providers or services occurred.

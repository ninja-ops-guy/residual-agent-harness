# Soak execution plan (release candidate)

Status: **plan/rehearsal only — no elapsed final soak has been run and none is claimed.**
The M4 integration gate is now accepted on main
`22a5bae54ec12987ffd7a90d881fb4533c9b4b97`, but the final soak still belongs
to a later accepted release candidate after release/recovery qualification.
Driver: `scripts/release/soak_run.py` (wraps `residual.soak`, SPEC-NINE-002).

## Duration and workload

- **Duration:** 30 consecutive elapsed days (N9-R9), ultimately `--days 30` on
  the accepted release candidate. The current driver advances deterministic
  simulated schedule days; its machine-readable outputs explicitly set
  `execution_mode=simulation` and `qualifies_elapsed_soak=false`. Therefore a
  fast `--days 30` simulator run is **not** elapsed 30-day evidence.
- **Resume boundary:** `soak-state.json` is saved after every simulated day and
  its digest, configured seed/load/duration, journal head, complete journal
  SHA-256 and record count are bound into an HMAC-signed
  `soak-checkpoint.json` before a later invocation is allowed to resume.
  On POSIX hosts the journal, state, checkpoint, report and retention-manifest
  stable boundaries are fsynced; directory entries are fsynced after atomic
  replace/unlink. This is local crash-durability hardening, not replicated
  durability or host-loss recovery.
- **Rehearsal cap:** `--max-days` never means completion. If the cap is reached
  before the configured duration, the driver emits `PAUSED`, writes no final
  signed `report.json`, retains a manifest/checkpoint, and exits successfully
  as a rehearsal pause. A later invocation with the **same** seed,
  tasks-per-day and total-days can resume. Changed resume parameters fail
  closed.
- **Workload mix:** `residual.soak`'s synthetic NetOps/SecOps task templates at
  **>= 1000 tasks/day** (enforced; the driver refuses less unless
  `--allow-below-minimum` is passed for rehearsal, which is recorded in the
  journal), with the configured `InjectionMix` of intentional failures and
  adversarial inputs, plus the N9-R12 red-team exercise.
- **Measured-evaluation boundary:** the frozen R0–R5 evaluation
  (`residual/eval_frozen`, #86/#106 binding) is a *separate* release gate. Its
  aggregates must not be mixed with soak evidence.
- **Sampling cadence:** one typed `DAY` record per simulated schedule day. The
  journal chain, signed checkpoint and prior retention manifest are verified
  before resumed work is accepted.

## STOP CRITERIA

1. **Error budget:** cumulative `unhandled_exceptions > --max-exceptions`
   (default **0**) or any day's brake false-negative rate above
   `--brake-fn-limit` (default **1%**).
2. **Crash:** the harness itself raises; the run halts and evidence already
   durably committed at a stable boundary remains available for investigation.
3. **Evidence integrity:** an invalid journal, checkpoint HMAC, journal digest,
   chain head/count, state digest, day history, or retained-file digest fails
   closed. A broken chain is not extended with a misleading chained STOP.
4. **Resource exhaustion:** free disk at `--out` below `--min-free-mb`
   (default 512 MB) halts before the next day.

A `STOPPED` run exits 2. Automatic continuation after a STOP is intentionally
refused; use a new evidence directory after the disposition is recorded.

## Artifact retention

Everything under `--out` (default `runs/release-soak/`):

- `soak-journal.jsonl` — hash-chained typed records (`START`, optional
  `RESUME`, `DAY`×N, optional `PAUSED`, and terminal `COMPLETE`|`STOP`).
- `soak-state.json` — resumable deterministic state.
- `soak-checkpoint.json` — HMAC-SHA256 signed checkpoint binding the complete
  journal SHA-256, chain head, record count, state SHA-256 and resume fields.
- `report.json` — written only for `COMPLETE` or `STOPPED`; the underlying
  N9-R10 report is HMAC-SHA256 signed with the Station identity key. A PAUSED
  rehearsal deliberately has no final report.
- `retention-manifest.json` — SHA-256 of every retained file plus the journal
  head and record count. Schema `residual.release-soak.retention.v3` records
  `COMPLETE`, `PAUSED`, or `STOPPED` and retains the explicit simulation scope.

**Retention rule:** retain the entire directory unmodified and retain the
Station identity key through an appropriately trusted secret-management path.
Before citing any artifact, verify the checkpoint HMAC, the journal
chain/head/count and every file digest against the retention manifest. Internal
hash links alone do not prove that a tail was not truncated; the signed
checkpoint is the authenticated resume boundary used by this procedure.

## Rehearsal command

```bash
python3 scripts/release/soak_run.py \
  --out runs/release-soak-rehearsal --days 30 --tasks-per-day 1000 \
  --station-key-hex "$STATION_IDENTITY_KEY_HEX"
```

This command exercises the deterministic simulation schedule only. It does not
by itself satisfy the elapsed 24h, 72h, or 30-day gates.

## Procedure validation vs final evidence

Procedure tests may use reduced-load deterministic rehearsals to exercise
pause/resume, stop criteria, checkpoint tamper detection, durable boundary
writes and retention. Those runs are **not** elapsed soak evidence and cannot
be cited as production or release reliability. A true elapsed soak must execute
the selected production candidate through the actual Station/runtime path for
the required wall-clock duration, retain exact revision/environment identities,
and preserve the same fail-closed stop/evidence policy. Any live-provider or
production substitution remains separate release-candidate work and must be
retained at the exact qualified revision.

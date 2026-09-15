# Soak execution plan (release candidate)

Status: **plan only — no final soak has been run and none is claimed.**
The final soak targets the accepted release candidate after the #108
sandbox-timing repair lands. Driver: `scripts/release/soak_run.py`
(wraps `residual.soak`, SPEC-NINE-002).

## Duration and workload

- **Duration:** 30 consecutive days (N9-R9), `--days 30`. The driver is
  resumable: `soak-state.json` is saved after every day, so a host reboot
  resumes deterministically from the last completed day.
- **Workload mix:** `residual.soak`'s synthetic NetOps/SecOps task
  templates at **>= 1000 tasks/day** (enforced; the driver refuses less
  unless `--allow-below-minimum` is passed for rehearsal, which is
  recorded in the journal), with the configured `InjectionMix` of
  intentional failures (bad configs, missing dependencies) and adversarial
  inputs, plus the N9-R12 red-team exercise (quarantine bypass, receipt
  forgery, unsafe execution, exfiltration — every attempt receipted).
- **Measured-evaluation boundary:** the frozen R0–R5 evaluation
  (`residual/eval_frozen`, #86/#106 binding) is a *separate* release gate,
  run per `docs/measured-eval-binding.md`; it is not part of the soak
  workload and its aggregates must not be mixed with soak evidence.
- **Sampling cadence:** one typed `DAY` record per soak day appended to
  the hash-chained journal (totals + all N9-R10 rates). The journal is
  re-verified before every append.

## STOP CRITERIA (explicit; each halt writes a typed `STOP` record)

1. **Error budget:** cumulative `unhandled_exceptions > --max-exceptions`
   (default **0** — N9-R10: any unhandled exception is a failure), or any
   day's brake false-negative rate above `--brake-fn-limit`
   (default **1%**, the N9-R10 limit).
2. **Crash:** the harness itself raises — recorded with the exception;
   evidence up to the crash is retained and chained.
3. **Evidence-chain break:** `Journal.verify()` fails before a new day is
   appended (tampered or truncated journal) — halt; do not continue on
   suspect evidence.
4. **Resource exhaustion:** free disk at `--out` below `--min-free-mb`
   (default 512 MB) — halt before evidence can be corrupted by ENOSPC.

A `STOPPED` run exits 2 and still writes the retention manifest. Resuming
after a STOP is a human decision recorded in the release log.

## Artifact retention

Everything under `--out` (default `runs/release-soak/`):

- `soak-journal.jsonl` — hash-chained typed records (`START`, `DAY`×N,
  `COMPLETE`|`STOP`); each record embeds SHA-256 of the previous line.
- `soak-state.json` — resumable state.
- `report.json` — the N9-R10 report, HMAC-SHA256 signed with the Station
  identity key (N9-R11); verify with `residual.soak.verify_report`.
- `retention-manifest.json` — SHA-256 of every retained file bound to the
  journal chain head.

**Retention rule:** retain the entire directory unmodified for the life of
the release; before citing any artifact, re-verify the journal chain and
every file hash against `retention-manifest.json`. Hash-chaining is how
the evidence chain is anchored: journal records chain to each other, and
the manifest binds the file set to the journal head.

## Run command (final, on the accepted candidate)

```bash
python3 scripts/release/soak_run.py \
  --out runs/release-soak-rc1 --days 30 --tasks-per-day 1000 \
  --station-key-hex "$STATION_IDENTITY_KEY_HEX"
```

## Validated live vs documented-only

Live in the authoring sandbox: 2-day rehearsal (40 tasks/day,
`--allow-below-minimum`) COMPLETE with verified chain and verified signed
report; determinism (same seed → identical totals); resume after
interruption (1-of-3 days, then completion with a single unbroken chain);
resource-stop criterion firing with `STOP` record and manifest; N9-R9 load
minimum enforcement. Documented-only: a real 30-day wall-clock run, and
substitution of the simulator executor (`SoakHarness._execute_task`) with
a live Station pipeline — the hook exists; the live wiring is release-run
work, not procedure-preparation work.

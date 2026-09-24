# AUD-1 F6 strict physical gate

This document supersedes the earlier physical-execution instructions in this tooling PR.
It does **not** change selected PR #448 candidate bytes.

Qualified Station candidate under test:

`7001bdf68355b7e5288a8cea3f4c827061aca37d`

## Why the stricter front end exists

Review of helper head `03a89dfe0c76e4eaea1406304e9f41a78255a402` found evidence-integrity gaps that normal CI did not exercise. In particular, the base collector's generic redactor can redact a raw 40-character Git SHA before `candidate_identity()` compares it with the target SHA; the earlier harness also proved a clean checkout but did not cryptographically bind the running Station process to those bytes, did not require every remote phase artifact, and allowed Case B to end with local no-submit instead of an explicit stale-result rejection attempt.

The release candidate remains unchanged. These are helper/evidence defects only.

## Required launch

Start the Station from the exact clean selected #448 checkout through `f6_bound_station.py` so the same process that executes `residual.station.server` emits a hashed launch witness:

```powershell
python .\f6_bound_station.py `
  --candidate-repo C:\path\to\exact-selected-448-checkout `
  --launch-record C:\evidence\station-launch.json `
  --data C:\evidence\station-data `
  --host 127.0.0.1 --port 8765
```

Every physical snapshot through `f6_case_guard.py` verifies the witness digest, exact candidate head, candidate module location/hash, Station data directory, URL, and live PID before collecting read-only Station/SQLite evidence.

## Required remote proof

Run `f6_remote_probe.ps1` with the exact task-owning `-RunnerPid` at each prompted phase. The probe retains only that runner's process identity and Station TCP connections; it never records the full command line or credential value.

`Run-F6-Physical.ps1` requires the transferred remote JSON for every phase and refuses to reuse an existing case directory, so failed attempts remain retained rather than overwritten.

## Case A

The harness records tunnel-down/up timestamps and requires reconnect to occur strictly before the 180-second worker grace. The case validator requires the same task owner and same lease before interruption and after reconnect, plus all required remote artifacts.

## Case B

The harness holds the old runner beyond the 180-second worker authority grace, waits for natural server lease expiry/recovery, requires a different valid runner to own the task, then restores the old runner without granting it a new claim or credential.

Case B additionally requires `f6_stale_result_probe.py` on the old runner. The probe reads the existing worker credential only from the environment and submits exactly one harmless stale `/api/worker/result` attempt using the old lease. The retained artifact must show HTTP `403`, `rejected=true`, and `accepted=false`. Local proposal suppression by itself is not sufficient for this gate.

## Freeze semantics

`f6_case_guard.py freeze` always writes a manifest, even for a failed attempt. The manifest contains machine-readable `validation.ok` and errors. `verify` rejects changed, missing, or newly added files after freeze and rejects a manifest whose physical validation failed.

A machine-valid bundle is still **not** an AUD-1 `FIXED` verdict. Keep F6-A and F6-B separate, then provide both immutable bundles to Mason/LEGION for the standing independent read-only F1/F2/F3/F4/F6 classification.

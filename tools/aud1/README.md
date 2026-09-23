# AUD-1 F6 physical evidence kit

**Tooling only. Not part of PR #399 candidate bytes.**

Qualified candidate under test:

`8df77b832b3839ccd2a6944a65760ce3ab10dc9c`

The scripts in this directory are deliberately maintained on a separate tooling branch.
Do **not** copy or commit them into the candidate checkout before the physical test.
`Run-F6-Physical.ps1` refuses to proceed unless the candidate checkout is clean and
exactly matches the qualified SHA.

The collector is read-only with respect to Station state. It opens
`station.sqlite3` using SQLite `mode=ro`, probes public bootstrap metadata, records
operator actions, and freezes SHA-256 manifests. It does not claim work, heartbeat,
submit results, recover tasks, rotate credentials, change leases, or integrate code.

## Layout

- `f6_collect.py` — Station-host read-only snapshots, operator ledger, command capture,
  attachments, bundle freeze/verification.
- `Run-F6-Physical.ps1` — guided F6-A/F6-B timeline around operator-controlled tunnel
  interruption/restoration.
- `f6_remote_probe.ps1` — Windows remote-runner process/TCP/log snapshot. It records
  only whether credential environment variables are present, never their values.

## Before starting

Keep two directories/checkouts separate:

1. **candidate checkout** — exact clean #399 head, used to run Station:
   `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`
2. **diagnostics checkout/directory** — this tooling branch.

Station default data is `~/.residual/station/station.sqlite3`.

Use a disposable qualification project/task. Do not use a production mission.

Capture runner stdout/stderr to a log file on the remote host if practical so the
`WorkerAuthorityLost` message can be retained in F6-B.

Never place worker tokens, API keys, session cookies, or launch URLs in evidence.

## Remote runner evidence

On the remote host, capture before/down/up/terminal boundaries:

```powershell
powershell -ExecutionPolicy Bypass -File .\f6_remote_probe.ps1 `
  -Label before `
  -StationHost 127.0.0.1 -StationPort 8765 `
  -RunnerLog C:\path\to\runner.log
```

Copy the resulting JSON + SHA256 files to the Station/tooling host and attach them
**before freezing**:

```powershell
python .\f6_collect.py --output .\AUD1-F6-EVIDENCE attach `
  --case F6-A-inside-window `
  --file .\remote-before.json
```

## F6-A — interruption inside grace window

The #399 worker defaults are:

- heartbeat interval: 60 seconds
- worker heartbeat grace: 180 seconds
- server task lease: 900 seconds

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\Run-F6-Physical.ps1 `
  -Case F6-A-inside-window `
  -CandidateRepo C:\path\to\exact-399-checkout `
  -Project p-... `
  -Task OPS-... `
  -StationData C:\Users\USER\.residual\station `
  -StationUrl http://127.0.0.1:8765
```

The harness prompts the operator to:

1. prove a real remote runner owns the task;
2. interrupt only that runner's authenticated transport;
3. restore the same transport comfortably before 180 seconds;
4. allow the worker to finish naturally.

Expected claim under review: continuity without duplicate authority/acceptance or an
invalid coordinator transition. The harness does not declare PASS; it freezes facts.

## F6-B — outside authority window + stale return

Run the same command with:

`-Case F6-B-outside-window`

The harness deliberately holds transport loss beyond 180 seconds so the worker-side
authority grace is exceeded. It then requires natural server-side expiry/recovery and
a **different valid runner** to own the task before the old transport is restored.

Important: the server lease is 900 seconds and heartbeat renewal extends it by another
900 seconds. Do not edit `lease_until` in SQLite to accelerate the physical test.
Wait for the real lease/recovery boundary. The resulting wall-clock delay is part of
the evidence.

After reassignment, restore the old runner transport without giving it a new
credential or claim. Retain its terminal/log evidence proving either:

- proposal submission was suppressed because `WorkerAuthorityLost` fired; and/or
- any stale result attempt was rejected by the Station.

If an explicit stale-result HTTP replay is desired, use a separately reviewed test
driver that never logs the credential. The read-only collector intentionally does not
perform authority-bearing worker operations.

## Snapshot contents

Each Station snapshot retains:

- exact expected and observed candidate SHA;
- candidate tree SHA;
- clean-worktree assertion;
- UTC + monotonic capture time;
- host/platform;
- project record;
- selected task record including owner, lease and lease expiry;
- complete project event chain plus recent tail;
- redacted Station settings;
- SQLite integrity result;
- global submission count;
- unauthenticated `/api/bootstrap` metadata probe.

The settings redactor removes token/secret/password/credential-value fields. Review
evidence manually before sharing anyway.

## Freeze

The guided harness freezes automatically. Manual freeze/verify:

```powershell
python .\f6_collect.py --output .\AUD1-F6-EVIDENCE freeze --case F6-A-inside-window
python .\f6_collect.py --output .\AUD1-F6-EVIDENCE verify --case F6-A-inside-window
```

Do not modify a frozen bundle. Corrections become a new explicitly versioned bundle.

## Required output to Mason

Provide two distinct bundles:

- `F6-A-inside-window`
- `F6-B-outside-window`

Each must have its own `manifest.json` and `manifest.sha256`.

Also provide:

- original AUD-1 report;
- original audited baseline `2f9dda38...`;
- #399 exact candidate `8df77b83...`;
- candidate diff;
- automated adversarial regression artifacts;
- exact-head repository CI references.

Mason remains read-only and independently classifies F1/F2/F3/F4/F6 as
`FIXED / PARTIAL / NOT FIXED / REGRESSION`.

## Evidence discipline

A later PASS does not erase an earlier failure. If a physical run fails because of a
real product/authority defect, freeze that failed bundle before remediation. If the
candidate changes, the prior exact-head qualification/re-audit is historical evidence
and affected gates must be rerun on the new bytes.

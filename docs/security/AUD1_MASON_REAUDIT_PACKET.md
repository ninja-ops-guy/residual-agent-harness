# AUD-1 Mason/LEGION independent re-audit packet

Status: **PREPARED / READ-ONLY / NOT YET A FINAL AUDIT**

This is a reviewer packet, not an approval. The final F1/F2/F3/F4/F6 re-audit
must be performed independently against the exact selected AUD-1 candidate and
the separately retained physical F6 evidence.

Current provisional successor under review:

`#438 @ e815f33484352f100e11b8d075bb954a815244cc`

Do not treat that SHA as selected until the owner explicitly records selection.

## Inputs

At final audit time, bind every conclusion to:

- original AUD-1 issue #353;
- original audit baseline `main@2f9dda3882f39c28a1c766859b1bf9579eea7911`;
- frozen original convergence PR #399 head
  `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`;
- exact selected successor SHA;
- complete diff from the applicable baseline;
- fresh exact-head qualification manifest/artifact;
- retained first-failure evidence for C1-C6;
- separately frozen F6-A and F6-B physical bundles.

For provisional #438 only, current software evidence is:

- Qualification-v1 run `35993248678` — PASS;
- final artifact `10805272548`;
- artifact ZIP SHA-256
  `e65db86f0ab714526962f1d0417ab34a31805aa74a15ab19daaa2ad34953c4f2`;
- exact tree `ee0009145f0dcc8207eceda98719db04a9af46cf`;
- Command Station run `35993248773` — PASS;
- controller/provider `35993248687` — PASS;
- clean install `35993248554` — PASS;
- Factory ownership `35993248841` — PASS;
- measured-evaluation binding `35993248642` — PASS;
- Control Plane `35993248873` — PASS;
- Pages/browser proof `35993248775` — PASS.

These runs are software evidence only. They are not physical F6 evidence or
human approval.

## Read-only review map

### F1 — operator authority is not public bootstrap data

Inspect:

- `residual/station/server.py`;
- launch-capability/session-cookie path;
- `tests/station/test_aud1_security.py` bootstrap/launch regression;
- browser qualification of the real launch path.

Require:

- unauthenticated `/api/bootstrap` exposes metadata only;
- operator/session authority is not returned there;
- launch capability is one-time;
- subsequent authority resides in the intended HttpOnly/SameSite session path;
- hostile Host handling does not manufacture local/operator authority.

### F2 — distributed worker authority is scoped and fresh

Inspect:

- worker credential issuance/binding;
- `Server.worker_operation`;
- project/task/owner checks;
- heartbeat/result paths;
- delayed-body C1 regressions.

Require:

- credential scope binds project + runner identity;
- worker B cannot exercise worker A's task authority;
- project-A authority cannot exercise project-B authority;
- heartbeat/result authorization is re-read after body receipt;
- a completed rotation/disable cannot be followed by an operation admitted from
  a stale pre-body authorization snapshot.

### F3 — remote exposure fails closed

Inspect:

- `validate_exposure`;
- Host checking;
- relevant AUD-1 regression tests.

Require non-loopback startup to need explicit remote exposure, allowed hosts, and
matching HTTPS public origin. Loopback/tunnel remains the preferred pattern.

### F4 — worker and coordinator authority remain separated

Inspect:

- strict worker endpoint dispatch;
- operator/coordinator task-transition paths;
- positive coordinator + negative worker regression.

Require a worker credential to remain unable to approve/integrate or invoke
operator transitions while the legitimate coordinator path remains functional.

### F6 — bounded authority continuity and stale-return rejection

Inspect:

- `residual/station/worker.py` monotonic authority watchdog;
- result retry and explicit authority-denial handling;
- stale-lease C5 handling;
- `residual/station/worker_access.py` C1/C6 barrier;
- F6-A and F6-B physical bundles.

Require:

- heartbeat I/O cannot suppress the local grace deadline;
- a late ACK cannot revive expired authority;
- retries/fallback submissions do not start after local authority loss;
- explicit result authority denials surrender rather than retry;
- stale lease rejection surrenders rather than retrying/falling back;
- rotation/disable is a completion barrier for already-admitted work;
- new admissions are writer-fenced while control waits;
- C6 independently bounds the drain using monotonic time;
- timeout happens before access-state mutation, reports failure, and releases
  writer-pending state;
- physical F6-A proves valid inside-window continuity;
- physical F6-B proves outside-window surrender, different-runner reassignment,
  and explicit stale-result rejection.

## Required disposition format

Record each finding separately:

```text
AUD1_REAUDIT_SHA: <exact selected SHA>
F1: PASS | FAIL | PENDING
F2: PASS | FAIL | PENDING
F3: PASS | FAIL | PENDING
F4: PASS | FAIL | PENDING
F6_SOFTWARE: PASS | FAIL | PENDING
F6_A_PHYSICAL: PASS | FAIL | PENDING
F6_B_PHYSICAL: PASS | FAIL | PENDING
BARRIER_TRADEOFF_REVIEWED: YES | NO
OVERALL: ACCEPT | ACCEPT_WITH_FOLLOWUP | CHANGES_REQUIRED | PENDING
NOTES: <bounded factual notes>
```

A missing host, missing artifact, or inaccessible evidence source is `PENDING`,
not PASS. PR-Agent output is advisory and is not independent human review.

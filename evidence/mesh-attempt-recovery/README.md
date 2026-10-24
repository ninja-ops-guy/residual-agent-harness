# Mesh execution-budget attempt lifecycle repair

## Scope and lineage

This is a successor-generation source repair for the failure historically classified
`ADMIT_REJECTED__STALE_MESH_EXECUTION_BUDGET`. Historical QUAL-001 attempts remain
failed/blocked evidence. No historical generation is reclassified as repaired.
Live DELL qualification is still pending and must be a new QUAL-001 generation after
independent review. No live DELL/LEGION/DBOX service, database, OpenClaw configuration,
registration or credential was accessed or changed.

Accepted `main` at inspection:
- HEAD `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`
- TREE `7cd0d32be6fd61948f2fce753b122e5b6f0c6500`

That accepted main has no `MeshWorkerClient`, `mesh_execution_budget`, or
`execution-admit` implementation. The actual implementation is on unmerged draft
[PR #404](https://github.com/ninja-ops-guy/residual-agent-harness/pull/404).
After the source mismatch was reported, the user explicitly approved the alternative
base and a stacked draft PR against `sc-mesh-001-v0.1`:
- **Repair BASE_HEAD** `7783081c858ad9ddf98b2e64e740e1104ae5d08b`
- **Repair BASE_TREE** `5c33861f37d1689fecfe0da7cab0b745eace3ac2`

The independent-review snapshot is content-bound by `receipt.json`; the published
PR description records the final commit HEAD/TREE (which cannot be self-embedded in
its own tree). No subsystem from #404 is imported into accepted main by this PR.

Overlapping open work inspected before implementation:
- #404 is the prerequisite and contains both defects
- #492 overlaps `store.py`/`server.py`, but changes project ceiling inspection,
  extension and `reserve_call`; it does not repair per-attempt execution admission
- #489 also changes Station server/provider surfaces; its provider continuity
  implementation is not imported here
- #481 changes Station service/CLI maintenance, not the targeted worker boundary

## Reproduce before repair

`tests/station/test_mesh_attempt_lifecycle.py` was written and run before production
edits. It is unchanged by the repair, SHA-256:
`b71f2ed12e9317aa02709cd413f1367e88229bd9a9ec0981710a94cc39697f27`.

```sh
python -m unittest tests.station.test_mesh_attempt_lifecycle -v
```

The test uses a temporary Station, real triage, legitimate claims and a mocked lease
clock (no sleeping and no direct database reset):
claim 1 -> admit -> no result -> expire -> recover/block -> triage -> claim 2 -> admit.
On untouched repair base it exits 1 with one error:

```text
residual.core.ContractError: Execution budget was already admitted for this task attempt
```

The first divergence is claim 2: it has a fresh lease/fencing token but retains claim
1's non-None execution-budget projection. Admission rejects before the runner can
call OpenClaw.

**Evidence continuity:** the first cloud workspace was replaced while waiting for
base authorization. Its original log bytes are unavailable; only the reported hash
`80efbd43d5480931818ed34cd0c45c6283af313da805d66d484ddf963c569892` survives.
The test was restored byte-for-byte and rerun on the same pinned untouched source,
again **before production edits**. `negative-reproduction-r2.log.gz` is that new
negative run, not a replacement claiming to be the unavailable original log. Its
uncompressed SHA-256 is
`cd44ac46d2373df614ad5a1085e7eeba1e05627e516cdafa837e25d22b071e42`.

## Root causes and repair semantics

### A: task-scoped stale budget

`Store.claim()` increments attempt/lease/fence, but previously did not initialize
`mesh_execution_budget`. Recovery and triage correctly retained evidence, yet the
next admission treated any retained non-None value as same-attempt authority.

The smallest compatible repair uses the existing task projection and hash-chained
transactional event model:
- New admissions persist **attempt + fencing token + project generation**
- Only a legitimate claim can initialize a fresh active budget slot
- The previous budget is first recorded unchanged in `mesh.execution.fenced`, under
  the old attempt, within the same transaction as the successor claim
- New admission and reconciliation events retain their corresponding budget state
- Recovery, triage, claim, restart and admission rejection never refund old unknown
  consumption or raise project ceilings
- Reconciliation requires an unexpired current lease and matching budget authority
- Duplicate admission remains rejected, including after reconciliation and restart
- Stale admission/result traffic is fenced; explicit mismatched result attempts are
  rejected before reconciliation or event mutation
- The admission `attempt` field is additive: old callers can omit it because the
  lease/fence still identify the attempt; supplied mismatches reject transactionally

Legacy unbound budgets fail closed for same-attempt reconciliation/admission. A
legitimate successor claim archives their exact state without inventing a historical
generation, then creates fresh authority. Unreconciled usage remains consumed.

### B: precise Station rejection discarded

Station previously sent only `{error: text}` with HTTP 400; `urllib.HTTPError`
escaped `MeshWorkerClient.request` and reached the CLI's generic
`worker_execution_failed` handler.

Admission contract failures now add `execution_error` with stable `code`,
`reason_code` and a fixed diagnostic message while keeping the old `error` field.
The worker reads at most 8 KiB, accepts only known structured codes, ignores raw
message/body/URL/headers, and emits a typed rejection receipt with:
- `code=EXECUTION_ADMISSION_REJECTED`
- for the reproduced duplicate, `reason_code=EXECUTION_BUDGET_ALREADY_ADMITTED`
- HTTP status and status class
- safe fixed message and request-side project/task/attempt/fence/generation/worker IDs

No lease, token, packet, prompt, arbitrary response text or provider result is copied
into those receipts. Malformed, oversized, deeply nested and legacy bodies retain
HTTP status with safe `STATION_HTTP_ERROR`; human-readable strings do not determine
machine authority. Unrelated message/outbox HTTP behavior is unchanged.

The runner requires an affirmative admission, clears current-work fields on
rejection and never cancels an unstarted assignment. Normal CLI startup no longer
probes OpenClaw before admission: `OpenClawExecAdapter.execute` already performs its
runtime checks after admission. Explicit `--preflight` still probes without claiming.
The rejection test proves adapter connect/execute/cancel counts are all zero.

## Atomicity and residual ambiguity

| Boundary | Guarantee / limitation |
|---|---|
| Claim -> fresh budget state | Old-budget archival, attempt/fence/lease generation, assignment hold, active-slot initialization and claim event commit in one `BEGIN IMMEDIATE` transaction. Rollback preserves the complete prior state. |
| Admission | Project counters, assignment-hold conversion, bound budget and admitted event commit together. Concurrent admissions have one effective reservation. |
| Crash before admission commit | Real child-process exit after writes but before commit rolls back both budget and counters. |
| Crash after commit / lost reply | Real process exit after commit leaves a charged admitted budget; reopening rejects duplicate admission. No blind replay. |
| Admission -> OpenClaw start | Not atomic with SQLite. A crash or runtime-preflight failure can leave an unused-but-unknown reservation. It remains consumed conservatively. Use explicit preflight before qualification. |
| OpenClaw start -> result | Not atomic. Provider execution may have happened without durable result. No provider-side exactly-once claim; recovery cannot infer unused capacity. |
| Reconciliation | Current authority check, counter adjustment, reconciled flag and event are atomic. Interrupted rollback and repeated reconciliation do not double-credit. |
| Reconciliation -> result acceptance | Existing endpoint performs these in separate transactions. A crash can leave reconciled budget evidence without an accepted result. This repair does not claim atomic result acceptance or reliable replay of a lost result acknowledgment. Same-attempt re-admission remains rejected. |
| Recovery -> triage -> successor | These remain distinct operations. None mints execution authority; only a valid Station claim advances attempt, subject to max attempts, dependencies, policy and remaining project budget. |

Provider-attempt evidence remains worker-reported under the existing contract. This
repair does not independently prove provider consumption, implement a new execution
journal or create a new provider idempotency protocol.

## Qualification matrix

All tests use isolated temporary storage and loopback or in-memory fixtures.

| Required case | Evidence |
|---|---|
| T1 normal first attempt | Real HTTP claim/admit, adapter fixture, Station deterministic verification/result/reconciliation -> review_ready |
| T2 duplicate admission | Same-attempt rejection before/after reconciliation; six concurrent admissions yield one reservation |
| T3 failed attempt -> successor | Frozen expire/recover/triage reproducer; failed verifier result through HTTP -> repair_required -> fresh successful successor |
| T4 stale generation | Old lease/fence, explicit stale attempt, advanced generation, late result and expired reconciliation reject without credit |
| T5 repeated triage | Repeated triage/retry cannot change attempt or counters; maximum attempts and project limit remain binding |
| T6 restart/recovery | Store reopen preserves admission; real Station startup recovery retains consumption; successor remains usable |
| T7 crash | Process exits immediately before/after admission commit; claim/archive and reconciliation rollback fault injection; no reset/double credit |
| T8 precise error | Actual HTTP 400 travels Station -> client -> runner -> CLI with stable duplicate reason, status and correlation |
| T9 no OpenClaw | Rejection leaves adapter connect/execute/cancel all at zero; missing/false admission also fails closed |
| T10 regressions | Existing Station/mesh/worker/OpenClaw/continuity suites and qualification tests |

Commands and results are recorded in `receipt.json` and compressed logs. Current
focused matrix: **22 passed, 22 subtests**. Existing mesh subset: **36 passed**.
Station plus qualification: **210 passed, 26 subtests** (91 Station / 119
qualification). Independent reviewer reran **58 tests**, found no blocking defect,
and checked the exact production diff digest recorded in the receipt.

Broader testing is **not claimed green**. All 37 observed failing nodes were rerun
on both untouched accepted main and untouched #404 before classification:
- 36 sandbox/containment failures are `PRE_EXISTING_MAIN_FAILURE` with
  `ENVIRONMENT_FAILURE` evidence: restricted host operations, including denied
  AF_UNIX sockets and bubblewrap's `RTM_NEWROUTE socket: Operation not permitted`
- 1 WebVM diagnostic test is `PRE_EXISTING_MAIN_FAILURE`: Node v24.19.0 rejects the
  legacy `--experimental-default-type=module` flag. This is a pre-existing
  test/runtime compatibility issue (`TEST_DEFECT` in this environment)
- No observed failure is attributed to the candidate without a baseline control

Initial broader execution stopped at the initial 20-failure cap; the subsequent
complete broader run retained all 37 failures. Nothing was excluded to manufacture
a green result. The final whole-suite run reports **2,009 passed, 37 failed, 413 subtests passed**;
its failing-node set exactly matches both baseline controls.

`compileall`, wheel build and `git diff --check` are additional checks. Browser,
Docker, other Python versions, live providers, systemd-host execution and physical
DELL qualification are not established by these cloud-fixture tests.

## Disposition

`MESH_EXECUTION_BUDGET_REPAIR_READY_FOR_INDEPENDENT_REVIEW`

Draft only. Do not merge as part of this repair task. Live DELL qualification is
pending and must exercise the reviewed successor as a new QUAL-001 generation.

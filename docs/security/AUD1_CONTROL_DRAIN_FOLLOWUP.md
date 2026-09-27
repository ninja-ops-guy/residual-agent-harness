# AUD-1 C6: bounded worker-access control drain

Status: candidate remediation on a stacked draft successor. This is not production acceptance, candidate selection, physical F6 evidence, or release authorization.

Parent successor: #433 at `9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60`.

## Finding

AUD1-C6 is an availability defect in the C1 completion barrier. The writer-preferred worker-access gate correctly prevented new admissions while credential rotation/disable waited for already-admitted operations, but the wait had no independent deadline. One admitted operation that never returned could therefore prevent the control operation from completing indefinitely.

The first hosted reproduction is retained at test-only commit `8a2fc3eebef6821c2466a031968684f16b92861d`, Command Station run `35992708134`, Python 3.11 job `107610337136`: 1,209 tests ran and the new C6 regression failed because control was still waiting after 250 ms while the fixture reader remained held.

## Repair semantics

The completion-barrier policy is unchanged:

- already-admitted worker operations are not preempted or rolled back;
- a pending control operation remains writer-preferred and blocks new admissions;
- successful rotation/disable still occurs only after admitted operations drain.

The new property is a 600-second independent monotonic control-drain deadline. If exclusive admission is not obtained before the deadline, `WorkerControlDrainTimeout` is raised **before** the control context yields. Therefore no credential or remote-worker setting mutation from that control attempt has occurred.

After timeout, writer-pending state is released and waiting operations may proceed. The operator HTTP surface returns 503 with an explicit drain-timeout error instead of reporting rotation/disable success.

The timeout is deliberately not cancellation: admitted work can continue after the failed control attempt. The operator may investigate or retry. This avoids falsely claiming revocation completion when the linearization boundary was never reached.

## Acceptance boundary

Fresh exact-head CI is required for the repaired successor. Independent human review must explicitly assess C1-C6 and the remaining completion-barrier tradeoff. #403 remains pinned to #399 until explicit successor selection and helper reconciliation. F6-A/F6-B, Mason/LEGION read-only re-audit, owner attestation, guarded integration, resulting-main qualification, RC verification, recovery, soak, and final release authorization remain separate gates.

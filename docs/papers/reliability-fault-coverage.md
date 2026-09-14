# Reliability Fault-Coverage Matrix

This note records the fault classes that the current research branch can actually inject and the preregistered classes that require a newer runtime. The distinction is normative for paper claims: a deferred class is not counted as a trial, a detection, or a containment success.

## Executable on the classic Harness path

| Fault kind | Injection | Expected containment boundary | Detection evidence |
| --- | --- | --- | --- |
| `malformed_reply` | invalid worker JSON | schema / contract | `counterexample: invalid_protocol` |
| `truncated_reply` | completion marked truncated | schema / contract | `counterexample: invalid_protocol` |
| `worker_abstain` | empty updates and requests | worker / controller | `counterexample: worker_abstained` |
| `provider_error` | deterministic provider exception | provider / runtime | `provider_failed: injected_provider_error` |
| `worker_termination` | deterministic worker-termination error | worker / runtime | `provider_failed: worker_terminated` |
| `invalid_scope_update` | update for an obligation outside the dispatched set | obligation scope | `counterexample: invalid_protocol` |
| `undeclared_evidence_request` | request for an artifact not declared by the obligation | evidence scope | `evidence_denied: undeclared_evidence` |
| `oversized_evidence_request` | request exceeding the configured line window | evidence window | `evidence_denied: evidence_window_limit` |
| `resource_exhaustion` | framed request size forced above the real request budget before I/O | resource budget | `counterexample: budget_exhausted` plus `budget_blocked` |

Every executable trial produces a `residual.fault-trial.v1` receipt containing the scheduled fault identity, expected layer, observed injection, ledger-derived detection, independent correctness, acceptance-boundary escape, containment outcome, result hash, and direct orchestration timing receipt.

The aggregate report fails closed if a scheduled injection was not actually observed. This prevents an unexercised fault from entering the FCR denominator as a successful trial.

## Deferred until the M2/M3/M4 runtime is the execution target

| Fault kind | Required runtime boundary | Why it is deferred here |
| --- | --- | --- |
| `forbidden_tool_invocation` | M2 worker tool boundary | the classic `Harness` does not execute the isolated worker tool contract |
| `forbidden_filesystem_write` | M2 OS-enforced filesystem boundary | no chroot/bind-mount/worktree worker sandbox is invoked by this experiment path |
| `stale_telemetry` | M3 evidence / telemetry boundary | the classic run path has no authoritative asynchronous telemetry input |
| `receipt_tamper` | M3 receipt graph | exercising this correctly requires the receipt/evidence bus as the authoritative path |
| `verifier_revision_change` | M3 verifier revision binding | requires a trial that mutates a bound verifier revision between production and consumption of evidence |
| `dependency_fault` | M4 dependency scheduler | requires the deterministic scheduler rather than simulating a provider failure |
| `integration_conflict` | M4 deterministic integrator | requires competing worker outputs presented to the actual deterministic integrator |

These classes remain part of the preregistered research target. They are deliberately rejected by the current `FaultSpec` instead of being approximated with unrelated failures.

## Claim boundary

The development fixture matrix is implementation validation, not confirmatory evidence for the paper hypothesis. A valid paper statement can say that the harness *implements and continuously tests nine controlled fault classes on the classic execution path*. It cannot claim full M2/M3/M4 containment coverage until the deferred classes run through those real mechanisms and produce retained receipts.

Likewise, FCR applies only to observed controlled injections represented in the retained receipt set. Detection rate and FCR must remain separate: a detected fault can still escape, and a contained fault may be blocked by a boundary without producing the same detection signal as another class.

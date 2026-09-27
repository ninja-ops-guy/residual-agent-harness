# R4.1 Canary Operator Package

Prepared only. Do not execute without an approved live-canary change window and authorization receipt. Nothing in this package supplies credentials or production authority.

## Files

- `CANARY_SPEC.md`: scope, invariants, abort rules, evidence, and objective success criteria.
- `CANARY_MANIFEST.json`: expected candidate/seal identities and package hashes.
- `preflight.py`: fail-closed identity, seal, cleanliness, remote, authorization, adapter, and destination checks.
- `run_canary.py`: bounded 120-second orchestration; dry-run/refusal by default.
- `collect_evidence.py`: deterministic SHA-256 evidence manifest generator.
- `rollback.py`: independently invocable rollback; dry-run/refusal by default.
- `verify_canary.py`: prints exactly `CANARY_PASS`, `CANARY_FAIL`, or `EVIDENCE_INCOMPLETE`.
- `self_test.py`: non-executing refusal/verifier tests.

## Operator-controlled prerequisites

Supply an executable adapter implementing `prestate`, `single-post-and-interrupt`, `receipt-first-reconcile`, `poststate`, `rollback-readiness`, and `rollback`. The adapter is deployment-specific and must enforce the immutable scope passed in `R4_CANARY_SCOPE`. Do not put credentials in this package.

Prepare a JSON authorization receipt containing `operation_id`, `scope` equal to `R4_CONTINUITY_SINGLE_OPERATION`, non-empty `approver`, and `expires_at_utc`. Independent approval procedures must validate signer/expiry before use.

## Refusal-safe checks

Run `python3 self_test.py`. Running `run_canary.py` without `--execute` refuses. Even with `--execute`, it refuses unless `RESIDUAL_R4_CANARY_GO=R4.1-CANARY-8701367D` and every precondition passes.

Rollback is separate and requires both `--execute` and `RESIDUAL_R4_ROLLBACK_GO=R4.1-ROLLBACK-8701367D`.

After an authorized run, run `collect_evidence.py EVIDENCE_DIR` and then `verify_canary.py EVIDENCE_DIR`. A pass never deploys, merges, promotes, or pushes.

# MC-V1-001 installed-native qualification runbook

Status: **V1 REQUIRED / EXECUTION PACKAGE / NO RELEASE AUTHORITY**.

This package converts the remaining Hermes/OpenClaw native gate into one
fail-closed evidence contract. It does not install software, restart a live
gateway, call a model/provider, change credentials, merge, tag, or lift
`V1_RELEASE_HOLD`.

## Freeze before execution

Record externally selected values before touching either native seat:

- exact candidate commit and tree;
- exact wheel SHA-256 installed on both seats;
- Hermes runtime version/build;
- OpenClaw runtime version/build;
- SHA-256 of each mission-sync plugin source tree/package;
- Station project/task/attempt/spec hash;
- exact native Hermes session id and OpenClaw canonical session key.

Do not place binding tokens, API keys, passwords, cookies, or credentials in the
evidence JSON. The validator rejects obvious secret-bearing keys.

## Test-host boundary

Use operator-authorized test installations only. Use a disposable Station data
copy on explicit loopback. Do not run a second Station process against live data.

Create two separate bidirectional bindings for the same exact Station task
attempt: one Hermes conversation and one OpenClaw conversation. Use separate
private spools. Default text capture remains disabled.

## Required native sequence

1. **Enrollment/provenance** — prove installed runtime/build identities, plugin
   source hashes, exact conversation/session correlation, binding id, candidate
   commit/tree and installed wheel hash.
2. **Hook execution** — prove the actual installed Hermes hooks
   `pre_llm_call/post_llm_call` and OpenClaw hooks
   `message_received/message_sent/before_prompt_build/gateway_stop` execute.
   Registration alone is insufficient.
3. **Context + observation** — from each conversation, retain one inbound
   observation and one exact current Station context delivery. Preserve Station
   journal/outbox receipts and local-spool hashes.
4. **Wrong identity negative** — a wrong/missing native conversation id/session
   key must not attribute an observation or consume task context.
5. **Privacy negative** — with default configuration, prove message text is not
   retained/shared. If text-sharing is later tested, require explicit consent on
   both bindings and keep that evidence separate.
6. **Reconnect/restart** — restart each adapter/client and prove retained spool
   continuity. For OpenClaw also prove gateway restart with the same canonical
   session correlation.
7. **Revocation** — revoke a binding and prove subsequent report/context use is
   rejected.
8. **Stale attempt** — advance/retry the Station task, then prove the old binding
   is rejected and cannot report for the successor attempt.
9. **False completion** — send a native `completion_claim`; record Station task
   state immediately before and after. They must be byte/field-equivalent for
   authority purposes. No chat report may cause acceptance.
10. **Two-conversation demo** — with both fresh successor bindings on the same
    current task, show both conversations receive current context and
    bidirectional observations while Station remains the only task authority.
11. **Station verification** — complete the task through the ordinary Station
    verifier/review/integration path and prove that transition independently of
    either conversation's self-report.
12. **OpenClaw cancellation/stop** — use the separately qualified control-plane
    lifecycle path to cancel/stop a native execution and retain evidence that the
    targeted process/execution actually stopped. A sync revocation is not stop
    proof.
13. **Independent review** — a reviewer who did not execute the run recomputes
    hashes, checks the Station journal/spools/native receipts, verifies candidate
    identity, and records PASS/FAIL.

## Evidence file

Create one JSON document conforming to
`docs/v1/MC-V1-001-NATIVE-EVIDENCE.schema.json`, plus immutable raw evidence
files listed by name and SHA-256.

Validate with externally supplied identity:

```bash
python scripts/qualify_native_mission_sync.py native-evidence.json \
  --expected-commit <40-hex> \
  --expected-tree <40-hex> \
  --expected-wheel-sha256 <64-hex>
```

A PASS means only that the required installed-native evidence contract is
complete and internally consistent with the externally selected candidate.
It is not a merge, release, deployment or policy-adoption decision.

## Done condition

This lane closes only when the validator passes on the frozen evidence package
and the independent reviewer independently verifies the raw artifacts. If any
required observation is unavailable, contradictory, from another candidate, or
depends on an unverified self-report, the result is **EVIDENCE_INCOMPLETE**.

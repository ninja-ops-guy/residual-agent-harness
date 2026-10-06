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
archive. The validator screens a small denylist of key names in the manifest and
structured captures only. It does not scan arbitrary values or raw files for
secrets, and a PASS never means secret-free. Independently inspect/redact the
archive before sharing, then hash the final retained bytes. Keep originals under
the operator's separate access controls; never archive private binding configs.

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

Create one v2 JSON document conforming to
`docs/v1/MC-V1-001-NATIVE-EVIDENCE.schema.json`, plus immutable capture and raw
evidence files listed by relative name and SHA-256. Version 1 manifests fail
closed: a registration boolean and syntactically valid digest are insufficient.

The dependency-free validator loads this schema and enforces its closed keyword
subset, including required/unknown fields, exact types, bounds, constants,
patterns, local references and date-time checks. Unsupported schema keywords,
formats and nonlocal references fail closed. This is not a general JSON Schema
implementation. Integer fields require JSON integers (booleans and floats are
rejected); timestamps use calendar-valid RFC3339-style dates without leap seconds.

The externally selected Station facts are `project_id`, `task_id`, `attempt`
(positive integer), and `spec_hash`. Obtain them independently from Station;
never derive the expected CLI arguments from the evidence under review. The
manifest and every capture must match those facts and the candidate exactly.
This binds one successful current attempt. After the stale-attempt negative,
freeze the successor attempt and fresh bindings for the positive captures and
two-conversation demonstration. Retain old-binding/stale-attempt/revocation
negative observations separately among the raw evidence files.

Each harness retains its runtime/build/plugin hash and exact
conversation/instance/binding identity. The two bindings must be distinct.
Replace `hook_registration_proven` with `hook_executions`, an array of
`{"hook":"pre_llm_call","evidence_file":"hermes-pre.json"}` records (example
shape only). Require exactly the two Hermes hooks and four OpenClaw hooks listed
in step 2, with one distinct capture file for each hook. A missing, duplicated,
unexecuted or mismatched capture fails even if other proof flags are true.

Each hook capture is a JSON object conforming to `$defs.hook_capture`:

- `schema`: `residual.mc-v1-native-hook.v1`;
- `candidate`: the same commit, tree and wheel SHA-256 object;
- `station`: the four exact selected Station facts;
- `harness`, `runtime_version`, `build_identity`, `plugin_source_sha256`,
  `conversation_id`, `instance_id`, `binding_id`: matching the manifest harness;
- `hook`, a distinct capture `event_id` within that harness, `observed_at`, and
  `executed: true`;
- `raw_evidence_files`: nonempty names of retained raw native traces/receipts.

`event_id` identifies the captured callback execution, not necessarily a native
message/turn ID (one turn can invoke multiple hooks). The OpenClaw
`gateway_stop` callback has no session context parameter: its trace must show
the previously initialized client and binding being closed, and the capture
must bind that lifecycle to the selected instance/conversation. Do not fabricate
a per-session callback argument or infer execution from registration.

The manifest's `station.evidence_file` names a distinct JSON object conforming
to `$defs.station_capture`: schema `residual.mc-v1-native-station.v1`, the same
`candidate` and four-fact `station` objects, both false-completion state fields,
`verified_transition_observed: true`, `acceptance_authority: "station_only"`,
and nonempty `raw_evidence_files`. Both state strings must be present, nonblank,
equal, and identical to the manifest. Raw references must resolve to separately
listed, hashed files, not to another structured capture or themselves. Preserve
the underlying Station snapshots, journal and ordinary verifier transition so
the reviewer can check these normalized facts against authoritative records.

All referenced capture and raw file bytes are actually SHA-256 checked. The
manifest does not list/hash itself. The verifier parses the same captured bytes
it hashed, without rereading them for semantic checks. Missing/unreadable files,
duplicate JSON keys, non-finite numbers and invalid UTF-8 fail closed.

Use a dedicated, frozen, operator-owned evidence directory, passed explicitly as
`--evidence-root`; no implicit cwd, environment or repository-root fallback.
Network/device roots are not supported. File names are portable relative paths of ASCII letters/digits, `_`, `-`, `.`,
and `/`; each segment starts with a letter/digit/underscore/hyphen. Absolute
paths, traversal, backslashes, URLs, drive/ADS syntax, Windows device aliases,
trailing dots, case-insensitive duplicates, symlinks/reparse points (including
ancestors), hardlinks and nonregular files are rejected. Limits: 128 listed
files, 16 MiB per file, 64 MiB total, 1 MiB per parsed JSON document. These checks
assume exclusive control of the frozen directory; portable path checks are not
a sandbox against hostile concurrent filesystem writers. Copy evidence out of
linked/synchronized directories before review without altering security settings.

Validate with externally supplied identity:

```bash
python scripts/qualify_native_mission_sync.py native-evidence.json \
  --evidence-root /path/to/frozen-evidence \
  --expected-commit <40-hex> \
  --expected-tree <40-hex> \
  --expected-wheel-sha256 <64-hex> \
  --expected-project-id <station-project> \
  --expected-task-id <station-task> \
  --expected-attempt <positive-integer> \
  --expected-spec-hash <64-hex>
```

A PASS means schema/consistency checks and file-byte hashes passed for the
externally selected candidate and Station attempt. The normalized captures,
runtime/plugin provenance, behavioral proof flags and reviewer identity remain
claims until independently corroborated against the retained raw artifacts.
Hashes do not authenticate native execution, message delivery, reviewer
independence, or Station transitions. No chat or evidence document gains Station
acceptance authority. PASS is not a merge, release, deployment, secret clearance
or policy-adoption decision.

Offline synthetic regressions (also collected by the existing pytest gate):

```bash
python -m unittest discover -s tests/qualification -p test_native_mission_sync_evidence.py -v
```

These tests construct only synthetic bytes in temporary directories. They do not
prove installed Hermes/OpenClaw compatibility or qualify a partial repository
snapshot, a wheel, any host, or the release candidate.

## Done condition

This lane closes only when the validator passes on the frozen evidence package
and the independent reviewer independently verifies the raw artifacts. If any
required observation is unavailable, contradictory, from another candidate, or
depends on an unverified self-report, the result is **EVIDENCE_INCOMPLETE**.

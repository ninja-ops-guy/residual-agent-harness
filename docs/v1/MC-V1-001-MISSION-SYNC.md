# MC-V1-001 — Cross-harness mission/task conversation synchronization

**Disposition: V1 REQUIRED / IMPLEMENTATION CANDIDATE / RELEASE HOLD.**

Owner instruction on 2026-10-04: RESIDUAL must track agents' tasks and synchronize
missions with conversations across OpenClaw, Hermes and other harnesses. The
owner explicitly said, “Build it. This is critical to v1.” This is not a v2
integration. It does not authorize a merge, release, live-host change, or silent
composition of existing draft branches.

## One source of task truth

A mission is a view of an existing Station project. Tasks, dependencies, leases,
ownership, execution attempts and authoritative transitions remain in Station's
existing `projects`, `tasks` and event ledger. The new module does not UPDATE or
INSERT those tables. No second scheduler, supervisor, acceptance policy, or
worker lease is introduced.

`residual/station/mission_sync.py` adds namespaced `ms_*` tables to the same
SQLite database for explicitly authorized conversation bindings, reported
observations, replay receipts, a hash-chained journal, and a durable outbox.
An agent saying `ACCEPTED`, or supplying a receipt hash, changes none of Station's
task state, evidence, leases or release gates. Native agent labels are
operator-configured labels, not independently attested identities.

## Implemented v1 slice

- Task/mission overview with canonical owner, current state, attempt,
  dependencies, linked harness conversations, queue backlog and latest report.
- Operator-created task/conversation capabilities, hashed at rest, expiring and
  revocable, pinned to the exact project spec hash and task attempt.
- Bidirectional protocol: durable inbound observations and outbound Station
  snapshots/context; opt-in peer conversation sharing for the same task.
- Inbox replay detection, conflicting-ID rejection, strict source sequencing,
  transactionally coupled journal/receipt/fanout, and restart-safe delivery.
- Python client/CLI and Hermes plugin; Node client and OpenClaw plugin.
- Mission Control at `/missions`, served alongside the existing Station UI and
  worker endpoints. The installed `residual-station` entrypoint selects the
  composed handler; `python -m residual.station.mission_server` is equivalent.

This is **turn-bound conversation/context synchronization**, not a promise that
an idle chat transcript receives unsolicited messages. Plugins pump on native
hooks and inject current reference context before a turn. They do not start
model turns, send native chat messages, execute tools, or automatically claim
new tasks. Arbitrary work outside an explicitly registered Station task is not
automatically discovered or converted into a mission.

## Start and bind

Use a disposable copy of Station data for candidate testing. Do not start a
second process against live data or restart an active gateway under this PR.

```bash
# Complete development checkout; existing dependency installation still applies.
python -m residual.station.mission_server --host 127.0.0.1 --port 8765 --data /path/to/test-station
# Open http://127.0.0.1:8765/missions
```

Create/import the mission in the ordinary Station UI. Assign/claim work through
Station's existing worker API. Then bind the intended task attempt to a native
conversation using the form or operator endpoint. Bind AFTER a claim increments
the attempt: a binding for attempt zero cannot report as attempt one.

A binding request requires `mission_id`, `task_id`, `harness`, `instance_id`,
`conversation_id`, `agent_id`. Defaults: bidirectional, one-day expiry, no text
sharing. TTL is 60 seconds–7 days. `direction` can also be inbound or outbound;
the supplied native plugins require bidirectional capabilities. A new attempt
or spec invalidates old bindings; the operator must create a successor binding.
Revoke the old one and use a new spool for the successor. This does not revoke
or cancel native execution; use the existing separately qualified lifecycle path.

Save the returned token in a private file; never paste it into agent messages:

```json
{
  "url": "http://127.0.0.1:8765",
  "binding_id": "COPY_FROM_OPERATOR_RESPONSE",
  "token": "COPY_ONCE_KEEP_PRIVATE",
  "conversation_id": "EXACT_NATIVE_SESSION_ID_OR_SESSION_KEY",
  "spool": "/private/mission-sync/binding.sqlite3"
}
```

The spool directory must be private (POSIX 0700); config and database use 0600.
On Windows, apply an equivalent owner-only ACL before activation. The files are
not encrypted; database ownership and host integrity remain trust assumptions.
Set `RESIDUAL_MISSION_CONFIG` to the file. The clients allow an explicit
`http://127.0.0.1:PORT` only, with no redirects or ambient proxies. Cross-host use
requires a separately approved secure local tunnel or future qualified TLS
transport. No tunnel is created by this implementation.

### Hermes

Install `integrations/mission-sync/hermes` as the `residual-mission-sync` native
plugin directory using the installed Hermes version's plugin workflow. Make
this RESIDUAL checkout importable in that Python environment. The plugin's
`register(ctx)` registers only `pre_llm_call` and `post_llm_call`; registration
itself does not touch files or the network. Only the configured exact native
`session_id` is observed. Before reporting, the client verifies that Station's
binding has that same conversation identity.

By default hooks record lifecycle observations without message text. Set
`RESIDUAL_MISSION_CAPTURE_TEXT=1` only after deciding that retaining this
conversation's text is appropriate. The plugin does not parse “done” as task
acceptance. A model turn ending is not a completed mission. Native callback
replays are deduplicated when the host supplies a stable `turn_id`; otherwise a
new durable event ID is assigned per observed callback. Pre-commit native hook
loss or duplicate callbacks without IDs are NOT solved by transport dedupe.

### OpenClaw

The package in `integrations/mission-sync/openclaw` declares a native plugin
entrypoint and uses Node's built-in SQLite support (tested here on 22.16.0).
It registers `message_received`, `message_sent`, `before_prompt_build`, and
`gateway_stop`. It requires an exact configured canonical `sessionKey`; missing
or conflicting correlation is not guessed. Outbound failures do not become
successful message observations. Stable native message IDs are deduplicated.

Prompt injection is only `appendContext`, never a system-prompt/model/provider
change. The host's explicit native hook/prompt-injection permission policy must
allow the hooks. Registration is not evidence that an installed build actually
runs them. This plugin is separate from the existing OpenClaw control-plane
package: it neither replaces that package nor satisfies its native/live gates.

### Other harnesses

Use `MissionClient` or the scoped HTTP contract. The installed
`residual-mission-sync` command supports `report`, `sync`, and `context`.
`report` reads a bounded JSON object on stdin, with `kind`, `text`, and optional
`native_event_id`. It queues before sending; a nonzero exit means inspect the
retained spool/binding instead of manufacturing a success. Do not share one
spool between different bindings/conversations. Tokens never belong in argv.

```bash
printf '%s\n' '{"kind":"progress","text":"Candidate prepared","native_event_id":"native-message-42"}' | residual-mission-sync report
residual-mission-sync sync
residual-mission-sync context
```

## Wire contract and authority

Operator routes use Station's existing `X-Station-Token` gate:
`GET /api/missions`, `GET /api/missions/journal?mission_id=...&after=...`,
`POST /api/missions/bind`, `POST /api/missions/revoke`.

Scoped adapter routes are POST-only, require `Authorization: Bearer <binding
capability>` plus `X-Mission-Binding`, and preserve Station host/origin checks:
`/api/mission-sync/report`, `/poll`, `/ack`, `/context`. A binding capability
cannot satisfy the operator gate. Unknown actions/fields are rejected.

```json
{
  "schema": "residual.mission-sync.v1",
  "event_id": "stable-transport-event-id",
  "source_seq": 1,
  "kind": "completion_claim",
  "text": "Worker says implementation is complete",
  "references": [{"label": "claimed receipt", "sha256": "64-lowercase-hex-characters"}]
}
```

The reference above is a shape illustration, not a valid 64-hex digest. Allowed
kinds: message, progress, blocked, completion_claim, artifact_reference. Text is
at most 8,000 characters; references at most 16. Evidence references remain
unverified claims and do not enter the accepted Evidence Bus.

Receipt `recorded:true` is returned only after the report, sequence increment,
journal and eligible fanout commit. Same event ID with identical content returns
the retained receipt. Different content, duplicate sequence, missing sequence,
stale attempt/spec, revoked capability, or full backlog is rejected. Rejection
rolls back the entire admission; there is no partially acknowledged fanout.

Outbound IDs and hashes are stable across retries. Poll marks a delivery offered;
ACK requires that binding, delivery ID and exact hash. ACK means **adapter durable
receipt**, not native transcript persistence, model consumption, user reading,
tool execution or task acceptance. The clients save inbound bytes before ACK.
Delivery is at least once, not exactly once. Local returned-context cursors are
not proof that a model saw the injection; retained records remain inspectable.

Station snapshots are refreshed on polling. Intermediate transitions are not
reconstructed from snapshots; Station's existing event log remains the workflow
history. Full queues remain drainable even when a new snapshot cannot yet fit.
Bindings default to private. Text fanout requires explicit sharing consent on
BOTH ends, same mission/task/attempt/spec, and a nonexpired outbound recipient.
A scoped offered-delivery echo claim suppresses rebroadcast, not journal storage;
it is not proof of textual equivalence or trustworthiness.

## Release acceptance gates

Implementation is not installed-native or final-v1 qualification. Keep these
open until independent, source-bound evidence exists:

1. Compose with the owner-designated current v1 candidate and OpenClaw repair
   stack; requalify exact composed HEAD/TREE. Do not transfer old receipts.
2. Run whole-repository regression, real Station integration, wheel/entrypoint
   smoke, Open Core/Factory boundaries and supported OS/Python/Node matrix.
3. On installed, exact-build Hermes and OpenClaw test explicit enrollment,
   actual hooks/context delivery, omitted/denied hooks, wrong/missing native
   IDs, text-consent boundaries, reconnects and gateway/client restart.
4. Demonstrate a real task progresses through its existing Station verification
   and authority gates while both conversations show synchronized context;
   a false completion claim must leave acceptance unchanged.
5. Independently review SQLite durability, privacy/token boundaries, transport
   loss/backpressure, UI authorization and composition; retain owner/maintainer
   approval and release hold. No paid providers or production hosts are used
   by this patch or its local tests.

## Source references inspected

Repository baseline: main `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`, tree
`7cd0d32be6fd61948f2fce753b122e5b6f0c6500`. Existing Station Store/Server and
pyproject were read through GitHub. The original pyproject blob was recomputed
locally as `952c29f4ff076a282944c553af614c17bfc485b7` before the two entrypoint edits.

OpenClaw hook signatures inspected at commit
`2e08f0f4221f522b60423ed6ffd83427942b28de`:
- `src/plugins/hook-message.types.ts`, blob `45e47cabd990a0cdaa2e67b0a324445e78659b3f`.
- `src/plugins/hook-before-agent-start.types.ts`, blob `2878790d1ec97048309ed5ad6db4a40d2cbe611a`.
- `src/plugins/hook-types.ts`, blob `3efab1de4ba4cbe99208723b4f46743af7c55f51`.

Hermes plugin documentation inspected on 2026-10-04:
https://hermes-agent.nousresearch.com/docs/developer-guide/plugins
OpenClaw policy overview:
https://docs.openclaw.ai/plugins/hooks
Documentation/source-shape inspection does not prove runtime compatibility on
the owner's installed seats. Refer to `MC-V1-001-VALIDATION.md` for test limits.

# Durable shared memory from retained Station evidence

## Implemented behavior

An agent can leave, lose its context, or be replaced while its checked work and
failed attempts remain useful. Station now rebuilds a bounded evidence context
from its existing event ledger and content-addressed artifacts. The replacement
worker receives this context automatically in `packet.shared_memory` when it
claims a task. No new ledger, model service, vector database, authority system,
or external provider is required.

This is a concrete implementation of indirect coordination through persistent
environmental traces (stigmergy). A trace is useful because a later worker can
inspect its source and applicability, not because another agent repeats it.

The source implementation is `residual/station/memory.py`. Station's existing
`Store`, authenticated HTTP service, local runner, and remote claim packet use
the same projection.

| Source retained by Station | Memory representation |
| --- | --- |
| `checks.completed` + checks artifact | Exact base/head/spec bindings, passed/total checks, bounded failed-check details |
| `review.completed` + review artifact | Recorded review decision and findings with exact source binding |
| `integration.completed` + integration artifact | Historical integration-check evidence; not new integration permission |
| `task.finding` | Untrusted, revision-unbound task observation with original actor and event hash |
| `task.transition` to blocked/repair-required | Retained failure finding and prior/next state |
| `worker.expired` | Visible loss of worker authority; existing evidence remains context |

The target task and its declared transitive dependencies are the retrieval scope.
Unrelated tasks and other projects are excluded. Events are not synthesized from
model memories. Source text stays data; the runner system contract explicitly
states that historical evidence cannot override the task or authorize actions.

## Evidence integrity and applicability

Every query verifies the project event hash links from genesis and the identity
of each event. Referenced artifacts must belong to the same project, have the
expected kind, match their SHA-256 and retained byte length, and agree with the
event's revision, specification and outcome. Review decisions use the same
approval/blocking-finding consistency rule as Station review. Full commit IDs
must contain exactly 40 or 64 lowercase hexadecimal characters.

Integrity checks establish which retained bytes were read. They do not establish
arbitrary truth, an independent witness, or permission. Every packet and item
has `authority: context_only`, and each packet requires current verification.
The existing receipt, lease, budget, acceptance, review and integration gates
still decide whether work can proceed. Task preparation blocks and releases its
new lease if retained memory cannot be verified; it does not silently discard
corrupt sources and continue.

Each item names its original event ID/hash/sequence/time/actor and, when present,
its artifact ID/hash. Worker identity comes only from a matching retained claim
event. The accepted-main event contract does not retain authenticated execution
host identity, so `host_id` is null and host provenance is explicitly unknown.
No evidence is relabeled as DBOX, LEGION, independent review, or physical-host
qualification.

Applicability is recomputed for the requested revision and current task/spec:

- An exact matching source with no limitation is `current_revision`. This is
  revision applicability, not a fresh correctness verdict.
- Changed spec, different revision, earlier attempt, revision-unbound notes,
  future timestamps, and a caller's optional age limit produce
  `historical_context` with explicit reasons.
- Contradictory outcomes for the same task/kind/spec/head are `conflicted`.
  Both outcomes remain visible. Neither latest-message wins nor majority vote
  resolves them. Different wording about the same failing outcome is not itself
  a contradiction.
- `superseded_for_current_work_by` links to newer retained evidence of that kind.
  It does not delete or refute the older observation. A changed candidate can
  pass while an earlier failed candidate remains in history.
- Repeated events referencing the same artifact are one trace. Their count is
  diagnostic only, and `independent_corroboration` remains zero. The first event's
  attempt and time remain the anchor even if the bytes are posted during a newer
  attempt: repetition cannot refresh old evidence. A real new acceptance decision
  still uses Station's current verifier/receipt path.

## Read and inspect

An authenticated operator can query:

```text
GET /api/projects/PROJECT_ID/memory?task_id=TASK_ID&limit=20
X-Station-Token: EXISTING_SESSION_TOKEN
```

The same read works without starting Station, touching its settings, calling a
model, or creating a database:

```bash
python -m residual.station.memory --root /path/to/station \
  --project PROJECT_ID --task TASK_ID
```

Optional HTTP/CLI query arguments are `revision`, `after`, `limit`,
`max_age_seconds`, and `snapshot_root` (CLI uses hyphenated option names). The
packet contains the target's state, dependency states, total trace count, and
original source references. A next page is available when `next_offset` is not
null. Pass it as `after` with the returned `snapshot_root`. A changed ledger or
task/spec snapshot rejects continued pagination rather than silently skipping
new or reordered evidence. Age is assessed at each read; snapshot identity pins
sources and scope, not the wall clock.

Retrieval is bounded: at most 20,000 events and 8 MB of event text per project,
256 KB per evidence artifact, 8 MB of distinct artifact bytes per query, and
32 KB per response. Each distinct artifact is read and verified once per query,
even when many transport events repeat it. Conflict references are bounded to
ten per item with an exact `conflict_count`; remaining sources stay discoverable
through the history pages. The ranking places conflicts first, then target-task
failures, target evidence and dependency context. Worker packets receive the
first bounded page and expose that more evidence exists.

If a scan bound is exceeded, the query fails explicitly and preserves sources.
This version does not delete or compact the source ledger. Long-running projects
that exceed the bound need a separately reviewed checkpoint/index design; raising
the bound or trusting an unchecked cache is not a recovery policy.

## Reproduce agent replacement

```bash
python scripts/demo_shared_memory_recovery.py --output /tmp/shared-memory-demo.json
python -m unittest discover -s tests/station -p test_shared_memory.py -v
```

The offline demo uses a temporary real Station database, Git candidate trees,
actual acceptance checks and the existing scripted-demo reviewer. One worker
submits a failing implementation. A fresh Python process reconstructs its trace
from durable state. A replacement worker inherits it, the departed worker's lease
is rejected, and the replacement corrects the task under fresh checks/review.
The original failure remains after integration. No LLM or live provider is used.

The retained demonstration result is `evidence/shared-memory/recovery-demo.json`.
It is a local software example, not a P5 experimental after-condition, operator
effort reduction, live independent-host result, or production qualification.

## Compatibility and next qualification boundary

This candidate is based on accepted main
`8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`. Existing Station events/artifacts need
no migration, and the accepted-only Factory Evidence Bus and epistemic-memory
store retain their roles. The new projection exposes negative operational
evidence without admitting it into the accepted receipt bus.

SC-MESH remains the durable message transport/identity/replay layer in its
separate unmerged integration stack. This change neither imports that stack nor
alters its enrollment, fencing, authorization, TTL, acknowledgement or routing
policy. Its eventual transport can carry these source references or task packet
contents under the existing scoped authority. It must not promote a transport
receipt into verification or renew authority merely because memory survived.

Local tests do not establish DBOX or Windows qualification, remote/native
SC-MESH composition, full storage-loss recovery, 24-hour soak, measured autonomy,
or release readiness. Hash chains without an externally trusted anchor cannot
detect a privileged rewrite of the complete database and all hashes. This
candidate does not claim that guarantee. Existing exact-code owner approval and
host qualification rules remain in force; no live activation is included.

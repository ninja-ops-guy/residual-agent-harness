# PROD-007 — production recovery design and operator runbook

**Status: protocol/runbook proposal; crash qualification pending.** The reviewed
baseline is identified in [README](README.md). This is not an implemented HA or
zero-data-loss claim. State ownership follows [DSM-004](DSM-004.md).

## Durable-boundary restart matrix

Inject a forced process exit immediately before and after **each** listed boundary,
then start a fresh process against retained storage. Also exercise disk-full,
short/partial writes, corrupted bytes and unavailable storage. Do not substitute
exception-only tests for OS process death; do not use real full-disk exhaustion.

| Boundary | State after crash | Required restart behavior | Current evidence / gate |
| --- | --- | --- | --- |
| Frozen plan and approval persisted | Possibly incomplete plan | Reject unreadable/hash-mismatched plan; no workers until valid approval | Plan/contract APIs exist; crash matrix pending |
| `RuntimeJournal.claim` commit | RESERVED attempt, contract and generation | No execution before durable claim; never reuse identity; classify abandoned reservation | Transaction and event share SQLite commit |
| Process spawned before `started` commit | Child may exist without RUNNING event | Host ownership record/containment must locate and reap child; unknown status cannot yield candidate | pidfd runtime mechanism exists; crash-window proof pending |
| Candidate writes before runtime finish | Partial unaccepted tree | Preserve/quarantine evidence; re-snapshot under controlled policy or discard explicitly | Broker/workspace controls exist; no blanket restart guarantee |
| Runtime finish commit | CANDIDATE or terminal failure | Candidate remains unaccepted; re-admit contract/evidence before Station receipt | Journal terminal transition is durable |
| Station receipt signed before bus append | Signed object may be absent from bus | Do not infer durable delivery; admit/append once after signature/artifact validation | Cross-store recovery protocol pending |
| Bus append committed, reply lost | Durable receipt and artifact bytes | Find by digest; acknowledge existing matching record, never append altered duplicate | Current duplicate insert errors; adapter idempotency gate |
| M4 snapshot/verifier result retained | Prepared evidence, no acceptance | Require same tree/policy/verifier and new epoch re-admission; absent evidence becomes UNKNOWN | #81 boundary and full evidence retention gates |
| Git object created, no publication | Orphan commit/object | Not accepted; reconcile against durable publication intent and root | Current `IntegrationOutcome` is returned, no publication transaction |
| Accepted-head/receipt decision commit | Durable acceptance | Reconstruct same head and receipt without new acceptance | Proposed DSM CAS/outbox; implementation pending |
| Outbox delivered, acknowledgement lost | Consumer may have applied effect | Inbox/idempotency prevents duplicate effects; redeliver pending entry | DSM protocol pending |
| Station transition at startup | Running/local_verified/triaging interrupted | `Store.recover(startup=True)` blocks interrupted local work and jobs; preserve evidence | Unexpired remote-owned running leases are retained; fence before takeover |
| HITL approval consumed, resume not recorded | Approved challenge with no known effect | Do not consume challenge again; reconcile exact action; require new challenge if ambiguous | Atomic challenge consumption exists; resume coupling is host responsibility |
| Checkpoint file partially written | Invalid/incomplete checkpoint | Hash/schema check fails; use older validated checkpoint only if authority history agrees | `CheckpointStore.load` checks hash; writes are not atomic rename/fsync |
| Schema migration interrupted | Mixed/unknown schema | Keep not-ready; recover only using tested transactional migration/backup procedure | No general migration manager established |

Each cell must record injection point, source SHA/tree, storage versions, initial
and recovered roots, process cleanup, receipt counts, lost/duplicate effects,
recovery duration, and replay instructions. Acceptance requires zero unauthorized
or duplicate acceptance. A failed kill/cleanup, missing durable evidence, or ambiguous
side effect is a failure/UNKNOWN with quarantine, never a silent retry success.

## Health and admission semantics

These are endpoint contracts to implement and test, **not existing endpoint names**:

| Signal | Meaning | Failure response |
| --- | --- | --- |
| Liveness (`/livez` proposed) | Process event loop responds; no provider/storage dependency | Restart only an unresponsive process, avoiding provider-triggered restart storms |
| Readiness (`/readyz` proposed) | Recovered schema/evidence valid; owner fencing valid; required sandbox/capacity and durable sink available | Withdraw admission; keep diagnostics and evidence export available |
| Health (`/healthz` proposed) | Component facts, last successful checks and ages, degraded reasons | Inform operators; never grant acceptance or change authoritative state |

Do not mistake a web page's HTTP 200, metrics scrape, or local `pidfd` API presence
for readiness. Probe admission dependencies with bounded deadlines and caching;
include timestamp and stale state. A provider outage can disable only routes that
need it; required evidence storage/fencing outage disables authoritative writes.

## Operator recovery procedure

1. Stop new admissions and publish a degraded/read-only state. Capture version,
   run IDs, timestamps, affected ownership epochs and last known durable roots.
2. Fence the failed owner before enabling a replacement. Do not delete lock files,
   reuse attempt IDs, force task rows to integrated, or approve by editing SQLite.
3. Stop/reap owned workers with bounded grace. If process ownership cannot be
   established, keep the node out of service and resolve through host supervision.
4. Take a consistent SQLite backup or quiesce writers before copying DB/WAL files;
   retain referenced Git objects and artifact bytes together. Hash the backup.
5. Validate database integrity/schema, journal chains, Station signatures, artifact
   hashes and accepted-head references. An unexplained mismatch keeps admission off.
6. Reconcile prepared versus committed publications using DSM rules. Block
   interrupted attempts for re-triage; issue fresh fenced identities when retrying.
7. Reconcile HITL status and external effects. A stored APPROVED challenge alone
   does not prove its action ran, nor authorize another run of the action.
8. Run local diagnostics and a new non-authoritative scripted workload. Re-enable
   admission only after readiness gates pass, then watch bounded queue growth and
   the evidence store's confirmed commits. Record closure with retained artifacts.

There is no universal recovery CLI yet. Use the actual version's documented tools
and store APIs; the proposed health endpoints and fencing publisher must not be
advertised as callable recovery commands before implementation.

## Shutdown, backpressure and data hygiene

Graceful shutdown MUST first close admission, persist a shutdown intent, drain
bounded in-flight commits, cancel/reap workers, checkpoint only validated state,
flush authoritative evidence, and release ownership last. Timeouts produce explicit
incomplete outcomes. A process supervisor can enforce the final deadline; forced
exit is then covered by the same crash matrix. Queue/in-flight limits, artifact and
output byte limits, disk reserve and evidence-commit deadlines are configured and
retained. Backpressure rejects or defers work with a reason; it never drops evidence
and continues acceptance. Metrics transport may shed data with a gap marker;
authoritative evidence transport may not.

HITL challenges bind task/action/goal hash, server MAC, authenticated operator role,
expiry and single-use status. Existing `HITLEscalationGateway` denies missing
authenticators, invalid/tampered/expired/replayed challenges. It does not resume a
run itself. Preserve signing keys and challenge storage across restart under a
secret-management policy; rotating keys requires an explicit pending-challenge
policy, not mass approval.

Migrations MUST inventory schema versions, back up and hash durable stores,
validate receipt readers against historical fixtures, write into a transactional
or new-version destination, and preserve old signed bytes. Unknown schema is
not-ready. Rollback restores a tested consistent snapshot; never downgrade by
rewriting historical receipts. Record migration tool hash and source/destination
schema roots.

Redact credentials at event creation, transport and export: provider authorization
headers, cookies, secret-bearing URLs, signed access tokens and environment values.
Persist secret references, never credential plaintext. Redaction cannot silently
change signed historical evidence: retain restricted originals where required and
publish a redacted derivative with provenance/hash and declared omissions. Test
canaries in stdout, stderr, exceptions, retries and operator downloads. The
preflight harness strips provider secrets by default and withholds optional
provider output; that does not establish platform-wide redaction coverage.

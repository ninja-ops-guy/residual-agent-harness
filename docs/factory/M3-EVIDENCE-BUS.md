# M3 Evidence Bus — implementation status

This stacked branch implements the trusted handoff boundary from `M2_M3_M4_SPECS.md`.
It depends on the M2 execution branch and does **not** implement M4 integration or scheduling.

## Trust rule

Workers never issue receipts. A quarantined M2 `RuntimeResult(status="CANDIDATE")` is
re-read by trusted host code, checked against its `WorkerContract`, evaluated by a
Station verification decision, and only then converted into a signed `WorkerReceipt`.

The receipt carries the exact `execution_plan_hash`, contract hash, input/output Git
commits, engine identity, artifact hashes, verification results, requirements, parents,
and signer identity. Ed25519 is used for local verification. There is no remote signature
service and no symmetric fallback.

## Evidence Bus

`EvidenceBus` uses file-backed SQLite with `synchronous=FULL`. Accepted artifact bytes are
stored as content-addressed BLOBs **inside the same database transaction as the receipt**.
This avoids a filesystem/SQLite crash window where an artifact could become visible in the
trusted store without a receipt. Failed or unknown Station decisions do not insert artifacts.
M2 retains unreceipted candidates in quarantine and its one-hour default reaper remains the
raw-output retention mechanism.

The receipt queue is append-only and hash-chained. Corrections create a new receipt with
`supersedes`; existing receipt rows cannot be modified or deleted. If a receipt or any
transitive parent is superseded, it is stale and cannot be consumed until an explicit human
stale-approval record exists.

`consumable()` verifies the Ed25519 signature, signer key id, receipt hash, artifact hashes,
and stale state locally. `artifact()` only exposes bytes reachable through a consumable
receipt. `admit_dependencies()` additionally checks that receipts match the worker's exact
declared dependency task IDs and `ExecutionPlan.graph_hash`.

## Query and observation coverage

Indexes support task, requirement, artifact hash, engine, verification status, time range,
and swarm queries. Receipt issuance and artifact storage audit records are committed in the
same SQLite transaction as their trust-bearing state. Queries, stale approvals, and
rejections are also recorded in the Evidence Bus audit table and may additionally be
forwarded to an external observation sink.

## Deliberate non-claims

- Verification policy is supplied by trusted Station-side code; this module does not infer
  that arbitrary acceptance strings are satisfied.
- M4 deterministic merge, conflict handling, scheduler intelligence, and evaluation are not
  implemented here.
- M2's general-purpose SDK/shell worker support remains outside this branch.
- A local Ed25519 key establishes cryptographic receipt authenticity for holders of the
  configured public key; key provisioning/rotation and HSM custody are deployment concerns.

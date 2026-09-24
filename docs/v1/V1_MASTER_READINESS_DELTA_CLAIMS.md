# V1 master readiness delta — claims contract and PR-G28 review readiness

This is an append-only release-governance update. It does not approve the
claims, authorize a canary, merge, production deployment, tag, release, physical
test, attestation, or modification of frozen evidence.

## Exact baseline

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- prior ledger head: `e543c066675a9be306ff264e499c39bf5f7b4534`

## New controlling decision gate — V1-CLAIMS-001

### Requirement

Before unresolved production/canary applicability decisions can be closed, the
owner and operations authority must approve a short v1.0.0 claims contract
defining promises and enforceable non-promises. Deployment profile, canary
threat model, dependency matrix and soak procedure derive from that contract;
they must not silently define product scope themselves.

### Proposal

Draft #445 exact head
`b91f574c0c73f51b5dc30302f7ab33a5e5563e09` adds:

- `docs/v1/V1_CLAIMS_CONTRACT.md` — decision-level promises/non-promises;
- `docs/v1/V1_CLAIMS_VERIFICATION_MATRIX.md` — claim → test/evidence/status
  mapping proposed as the exact-RC exit criterion.

Classification: **scope decision / missing owner approval**.

Status: **BLOCKED** until owner/operations approval. #445 is a proposal, not an
approval receipt.

### Proposed consequences requiring explicit approval

The draft follows current-main documented boundaries:

- trusted single-user/local-operator, not hardened multi-tenant Internet service;
- direct Station exposure loopback-only;
- admitted remote workers only through an approved authenticated transport and
  only after AUD-1 acceptance;
- one authoritative Station process per v1 data directory; no shared multi-host
  SQLite/automatic HA claim;
- no exactly-once SQLite/Git atomicity claim;
- if Shared Comms ships, #426 receipt semantic binding and recovery payload
  digest become pre-release successor requirements;
- concurrent recovery is excluded only if a second owner is actually
  prevented/rejected;
- exact release matrix is owner-approved and becomes PR-G28 input;
- proposed soak default is 72 continuous hours with reset on claim-affecting RC
  changes.

Unresolved approval values remain explicit: exact OS/architecture/Python/artifact
/extras matrix, exact authenticated remote-worker transport, availability/RPO/RTO
/backup/retention policy, final soak environment/workload/evidence cadence, and
whether Shared Comms is a v1 release claim.

### RC exit rule

The proposed claims matrix forbids `RC_READY` while any applicable claim row is
NOT_STARTED, IN_PROGRESS or BLOCKED. A scope exclusion counts only when it is
owner-approved **and fail-closed/enforced**. Final `V1_RELEASE_READY` also
requires elapsed soak and human release authorization.

## PR-G28 / #444 status refinement

#444 exact head `1403429dbdcb3abf04bcb1fb75fd1a2bad93cfbc`
is now **READY_FOR_REVIEW / unmerged**.

Exact-head technical CI passed:

- Qualification-v1 `36025861863`;
- controller/provider `36025861933`;
- Command Station `36025861763`;
- clean install `36025861845`;
- Factory ownership `36025861922`;
- Control Plane `36025861955`;
- measured-evaluation binding `36025861928`.

Maintainer approval remains unsatisfied without human attestation. PR-Agent
`36025861736` published no substantive review because the configured models
returned `credit_balance_exhausted` after secret preflight passed.

Status separation:

- #444 repository lock-contract tooling: `READY_FOR_REVIEW`;
- authoritative release lock generation: `BLOCKED` on approved claims/release
  matrix and separately authorized trusted resolution environment;
- PR-G28 parent: `BLOCKED / NOT VERIFIED`;
- MERGED_AND_REQUALIFIED: not reached.

## Freeze rule

After V1-CLAIMS-001 approval, v1 feature development is frozen. R5/research may
remain preserved on isolated branches but must not create new merge pressure
against the v1 release line. New v1 work is limited to demonstrated blocker
repair, exact-head qualification, acceptance evidence, release/recovery tooling
and required runbooks.

## Existing blockers

No automatic status promotion occurs for PR-G26, V1-PC-002..004, V1-PP-001,
AUD-1, canary, recovery/rollback/incident exercises, soak, production, tag or
release. Their applicability/acceptance must be reconciled against the approved
claims contract.

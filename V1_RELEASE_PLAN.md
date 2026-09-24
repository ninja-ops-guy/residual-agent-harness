# RESIDUAL v1 release and operations plan

Status: planning only. This document grants no authority to run a canary,
promote, tag, deploy, or change production.

Canary provenance candidate: `8701367db6d3202f24b3eb9f4696b0cadf657985`

Canary provenance tree: `79bfe6ed1743907065ed44aeb9c460c47527e0c6`

Canary provenance parent: `eada7577cf6f2de875b508c6a82f47870e3aa673`

Entry condition: independently verified `CANARY_PASS` for the canary provenance
candidate above. The final v1 release candidate is selected later from the accepted
post-convergence repository state and is not pre-bound to the R4.1 canary commit.

## Shortest safe critical path

1. **Post-canary verification:** freeze the canary bundle; verify its hashes,
   authorization, exact canary-candidate identity, one receiver effect,
   receipt-first recovery, stable protected services, zero unauthorized mutation,
   and a successful rollback rehearsal. Human gate: Canary Verifier signs the
   result.
2. **Promotion eligibility:** an independent reviewer confirms all R4.1 and
   canary evidence is complete and no open severity-1/2 defect or unaccepted
   release exception exists. Human gate: Release Manager records `GO`.
3. **Release candidate:** after all approved release-critical changes have landed
   and resulting main has authoritative qualification, select one exact repository
   commit/tree/parent as the RC source, create a protected RC branch, normalize the
   package version to `1.0.0`, build once, and sign/attest the exact artifacts.
   Record the R4.1 canary candidate separately as provenance. Human gate: Release
   Manager authorizes RC creation; authorized Maintainer performs it.
4. **Production qualification:** qualify those exact artifact bytes, including
   fresh install, full required suite, SBOM/signature verification, migration
   rehearsal, configuration compatibility, backup restore drill, security scan,
   and release soak. Human gate: Qualification Lead signs `GO`.
5. **Release approval:** Security, Operations, Product Owner, and Release Manager
   review one immutable evidence index and approve a bounded deployment window.
   Any missing evidence is `EVIDENCE_INCOMPLETE`, never implicit approval.
6. **Deployment:** Deployment Operator verifies the approved receipt, takes and
   validates a backup, records the prestate, and deploys only the qualified digest
   with the approved procedure. Human gate: Incident Commander gives final
   go/no-go at the window; Deployment Operator starts each irreversible phase.
7. **Post-deploy verification:** test readiness, health, critical journeys,
   persistence, Shared Comms idempotency, telemetry, safety counters, and error/
   latency/resource guardrails. Human gate: Operations and Product Owner accept.
8. **Rollback window:** keep the previous artifact, configuration, database
   recovery point, operators, and rollback authority available through the
   declared observation window. A trigger produces `ROLLBACK`; no vote is needed
   to stop traffic, but the Incident Commander authorizes restore/failback steps.
9. **v1 closure:** after the window and a final evidence audit, the Release
   Manager signs the receipt, an authorized Maintainer creates signed tag
   `v1.0.0` on the already qualified RC commit, and the evidence is archived.
   There is no rebuild and no automated promotion.

## State model

Only four operational decisions are permitted:

- `GO`: all required evidence is valid and the named human gate authorizes only
  the next bounded transition.
- `NO_GO`: a known requirement failed or a human approver declines. Stop; create
  a new candidate or documented exception. A rerun is new evidence.
- `ROLLBACK`: a rollback trigger is proven during deployment or the rollback
  window. Stop promotion, preserve evidence, isolate unsafe traffic, and execute
  `ROLLBACK_RUNBOOK.md` under the Incident Commander.
- `EVIDENCE_INCOMPLETE`: evidence is absent, malformed, stale, contradictory,
  hash-invalid, or not bound to the exact candidate/artifact/environment. Stop
  and collect evidence; never infer `GO` or `ROLLBACK` from an unverified claim.

Decision precedence is `ROLLBACK` (when verified unsafe state exists), then
`EVIDENCE_INCOMPLETE`, then `NO_GO`, then `GO`. Every decision is append-only,
signed or identity-bound, timestamped in UTC, scoped to one transition, and
expires at the end of its deployment window.

| From | Required result | Human gate | To |
|---|---|---|---|
| `CANARY_PASS` | Post-canary evidence verified | Canary Verifier | `POST_CANARY_VERIFIED` |
| `POST_CANARY_VERIFIED` | Promotion packet complete | Release Manager | `PROMOTION_ELIGIBLE` |
| `PROMOTION_ELIGIBLE` | Post-convergence RC source selected and version fixed | Release Manager + Maintainer | `RC_CREATED` |
| `RC_CREATED` | Exact-artifact qualification passes | Qualification Lead | `PROD_QUALIFIED` |
| `PROD_QUALIFIED` | All approvals and window valid | Security + Operations + Product Owner + Release Manager | `RELEASE_APPROVED` |
| `RELEASE_APPROVED` | Preflight/backup/prestate pass | Incident Commander + Deployment Operator | `DEPLOYING` |
| `DEPLOYING` | Deployment checks pass | Deployment Operator | `OBSERVING` |
| `OBSERVING` | Verification and rollback window pass | Operations + Product Owner | `CLOSURE_ELIGIBLE` |
| `CLOSURE_ELIGIBLE` | Receipt and archive complete | Release Manager + Maintainer | `V1_CLOSED` |

No CI job, verifier, merge, tag, registry event, or successful health check may
perform one of these transitions automatically.

## Release candidate and artifact provenance

The RC packet must contain:

- selected release commit, tree, parent, clean-tree assertion, accepted-main
  qualification identity, and the human decision that selected those bytes;
- separate canary provenance binding to R4.1 commit/tree/parent, Seal v2, 17/17
  qualification result, authoritative 50-entry manifest, canary bundle,
  post-canary decision, and every referenced SHA-256;
- independent verification that RC tag target equals the selected release commit;
  the same equality is reverified for the final `v1.0.0` tag;
- source archive hash; dependency lock/toolchain/runner identities; build command,
  UTC time, builder identity, build logs, and hermeticity/network declaration;
- artifact name, media type, byte size, SHA-256, registry digest, signature,
  provenance attestation, and SBOM hash for every deployable unit;
- test/scan/soak reports bound to the same artifact digest; no mutable tags as
  evidence; and a signed changelog/release-note hash.

`RELEASE_RECEIPT_SCHEMA.json` deliberately treats the final release candidate as
a separate identity from the fixed R4.1 canary provenance. JSON Schema alone does
not provide portable cross-field equality, so `scripts/validate_release_receipt.py`
must also PASS to prove `rc_tag.commit == candidate.commit` and, after closure,
`final_tag.commit == candidate.commit`.

Build once after the version metadata gate. The exact qualified bytes are the
only bytes deployable. Copying between registries must preserve and reverify the
digest. Rebuild, repackage, dependency drift, changed configuration defaults, or
an amended commit creates a new RC and invalidates downstream approvals.

## Version, tags, and changelog

- Resolve the current metadata mismatch (`pyproject.toml` says `0.5.0` while
  `residual.__version__` says `0.4.0`) before RC creation. Both must report
  `1.0.0`, and an automated assertion must prevent recurrence.
- Use signed annotated `v1.0.0-rc.N` tags on the exact selected RC commit after
  human RC authorization. RC numbering is monotonic; never move or reuse a tag.
- After the rollback window, place signed annotated `v1.0.0` on that same commit.
  The final tag identifies already deployed/qualified bytes; it triggers no build
  or deployment. Registry aliases such as `stable` are optional pointers only.
- `CHANGELOG.md` must have a `1.0.0` section covering user-visible behavior,
  security and trust-boundary changes, fixed R4 findings, compatibility and
  configuration changes, data/schema effects, known limitations/non-claims,
  upgrade and rollback notes, and exact artifact digests. Product, Security, and
  Operations approve its hash before release approval.

## Production qualification requirements

### Migration and configuration preflight

Inventory every authoritative store and schema. If there is no migration, record
`migration_required=false` with owner approval. Otherwise require forward and
backward compatibility, a production-shaped dry run, duration/lock/disk estimates,
idempotency, interruption recovery, checksum, and rollback/restore decision point.
Destructive or irreversible migration requires a separately approved maintenance
plan and proven restore; it cannot use an application-only rollback.

Diff production configuration keys, types, defaults, secrets references, feature
flags, ports, volumes, filesystem permissions, providers/models, timeouts, quotas,
and external API contracts against the RC manifest. Unknown/missing values,
plaintext secrets, stale authorization, or incompatible flags are `NO_GO`.
Secrets are referenced by identifier/version and tested for access, never archived.

### Backup and restore

Before deployment, create an application-consistent encrypted backup of databases,
durable outboxes/journals, evidence/receipt stores, user artifacts, configuration
references, and required object storage. Record snapshot IDs, hashes, encryption
key identifier, retention, owner, start/end time, and restore point. A recent
production-shaped restore drill must verify integrity, receipt-chain continuity,
application startup, critical reads, and declared RPO/RTO. The deployment backup
must be readable before traffic changes. Backup failure is `NO_GO`; an unverified
backup is `EVIDENCE_INCOMPLETE`.

### Health, readiness, and observability

The deployment manifest must name exact, authenticated probes; generic HTTP 200
is insufficient. Readiness proves dependency reachability, data/schema compatibility,
durable write/read, queue/outbox progress, provider routing, and no stale worker.
Health proves process/event-loop liveness. Synthetic critical journeys cover create,
execute, persist, reload, receipt lookup, and one idempotent reconciliation case.

Dashboards and alerts must cover request/job success and latency, 5xx/timeouts,
queue age/depth, retry/retransmit/dedup counts, journal/outbox lag, database errors/
locks/storage, worker restarts, memory/CPU/file descriptors, provider failures,
authorization denials, credential/protected-service mutations, and evidence-pipeline
failures. Baselines and numeric stop/rollback thresholds must be written into the
approval packet before deployment, with named query links and on-call ownership.

## Approval gates and exceptions

All gates listed in `V1_RELEASE_GATES.json` are required. Approvers must be human,
independent of the artifact-producing automation, authenticated, and named in the
receipt. One person may not fill Release Manager and Deployment Operator for the
same release. Security exceptions require scope, compensating controls, owner,
expiry, and Security plus Release Manager approval; severity-1/2 safety, data-loss,
authorization, provenance, or rollback defects are not exceptionable for v1.

## Incident response

The first observer declares an incident, pages the Incident Commander and on-call,
freezes promotion, preserves UTC logs/metrics/traces/decisions, and classifies the
state. The Incident Commander assigns Operations, Application, Data, Security,
Communications, and Scribe roles; establishes a timestamped channel; and sets an
update cadence. Stop or drain unsafe traffic before diagnosis. Use the rollback
triggers/runbook; do not improvise destructive data repair. Notify Security at once
for credential, authorization, provenance, or protected-service anomalies. Record
customer impact and regulatory/contractual notification decisions. After recovery,
verify integrity and critical journeys, maintain the incident open through the
observation period, publish a blameless review, and attach it to the release record.

## Closure and evidence archive

Closure requires the completed receipt, checklist, decision ledger, source/RC/final
tag signatures, artifact/SBOM/provenance signatures and hashes, all qualification
and deployment evidence, dashboards/alerts snapshots, backup/restore records,
migration/configuration records, changelog, approvals, deployment/rollback log,
incident records, and post-deploy report. Store one immutable access-controlled
archive plus an independently verified copy, with retention and legal-hold policy.
Archive the index last; verify every entry and record the index SHA-256. Secrets,
tokens, and personal data must be redacted without destroying evidentiary meaning.

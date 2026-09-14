# M4 deterministic integration

This stage consumes only `EvidenceIntegrationPlan` values built from locally verified M3 receipts. It is the first Factory stage allowed to construct a project-level Git commit from accepted evidence.

## Trust boundary

`DeterministicIntegrator` never reads worker worktrees or raw candidate output. Artifact bytes are fetched through `EvidenceBus.artifact()`, which re-verifies the Station signature, stale status, receipt graph, artifact hash, and content-addressed store before returning bytes.

All root receipts must bind the same exact input commit. Receipts are applied in the deterministic topological order already committed by `EvidenceIntegrationPlan`. The final Git tree is committed with fixed author/committer identity and timestamp, with the integration-plan hash in the commit message. No branch or ref is moved.

## Overlap semantics

Overlap is evaluated only between receipts that are incomparable in the dependency graph. Ancestor/descendant edits are sequential evolution; the later receipt owns the final file state.

For incomparable receipts touching the same path, the integrator derives normalized edits from each receipt's frozen input state:

- identical normalized edits collapse automatically;
- a strict subset is discarded and the superset is kept;
- binary changes only auto-resolve when their before/after hashes are identical;
- non-subset changes are a true `integration_conflict`.

True conflicts stop integration. A caller may resume only by providing a `ConflictResolution` naming the selected receipt plus the approving human identity and reason. That HITL record is emitted as an observation and bound into the final `IntegrationReceipt`.

## Accumulated project verification

`ProjectVerificationPolicy` requires at least one command in each mandatory category:

- `full_test_suite`
- `type_check`
- `contract_validation`

When `secops_active=True`, a `security_scan` command is mandatory as well. Commands are executed directly without a shell in the isolated integration worktree. The receipt records pass/fail status, return code, and SHA-256 hashes of stdout/stderr rather than copying arbitrary command output into trusted evidence.

If accumulated verification fails, the integrator deterministically bisects the receipt set by replaying subsets from the frozen root commit and re-running the same verification policy. When one receipt can be isolated, `M4ReceiptRevisionRequired` is emitted with `action=replan`, and `ProjectVerificationError.offending_receipt_hash` identifies it. Interaction-only failures where neither half fails independently return no single offending receipt rather than inventing attribution.

## IntegrationReceipt

A successful integration emits a Station-signed `IntegrationReceipt` binding:

- execution-plan hash;
- integration-plan hash;
- ordered input receipt hashes;
- deterministic output commit;
- project verification results;
- all HITL conflict resolutions;
- integration timestamp;
- Station key identity and signature.

The output commit is deterministic for the same accepted evidence, conflict resolutions, and root commit. The receipt itself includes an integration timestamp and is therefore an auditable issuance record rather than a reproducibility identifier.

## Current scope

This closes M4-R1 through M4-R7 at the Factory integration boundary. Scheduler policy beyond the already implemented receipt-backed ready-DAG snapshot remains separate: engine/node selection, continuous bottleneck measurement, automatic swarm resizing, and structural re-planning correspond to M4-R9 through M4-R13.

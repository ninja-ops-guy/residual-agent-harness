# M4 deterministic integration

This stage consumes only `EvidenceIntegrationPlan` values built from locally verified M3 receipts. It is the first Factory stage allowed to construct a project-level Git commit from accepted evidence.

## Safety qualification status (issue #63)

**Untrusted project verification is blocked by default.** There is not yet a
qualified OS-isolated M4 project-verification runner. A worktree, environment
allowlist, timeout, or receipt is not a sandbox. Do not run model-authored or
otherwise untrusted project code using the trusted development-fixture escape
hatch below. This is an intentional fail-closed compatibility change.

The black-and-green public Pages design is unchanged; this repair touches no
page sources, styles, or deployment workflow.

## Trust boundary

`DeterministicIntegrator` never reads worker worktrees or raw candidate output. Artifact bytes are fetched through `EvidenceBus.artifact()`, which re-verifies the Station signature, stale status, receipt graph, artifact hash, and content-addressed store before returning bytes.

All root receipts must bind the same exact input commit. Receipt/task order is revalidated at execution time and every parent must precede its child. The final Git tree is committed with fixed author/committer identity and timestamp, with the integration-plan hash in the commit message. No branch or ref is moved.

## Overlap semantics

Overlap is evaluated only between receipts that are incomparable in the dependency graph. Ancestor/descendant edits are sequential evolution; the later receipt owns the final file state.

For incomparable receipts touching the same path, the integrator derives normalized edits from each receipt's frozen input state. File existence is part of that normalization, so an absent file is not silently treated as an empty file.

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

When `secops_active=True`, a `security_scan` command is mandatory as well. Commands cannot execute with the default policy. Only operator-authored,
reviewed development fixtures may explicitly set
`ProjectVerificationPolicy(commands, trusted_fixture_mode=True)`. That lane
executes on the host, **without OS filesystem/network isolation**. Its POSIX
supervisor streams bounded stdout/stderr, validates finite deadlines and output
limits, and kills its process group at timeout/output overflow and after leader
completion. These limits do not contain malicious processes that escape their
process group. Missing executables remain UNKNOWN; overflow/timeouts are FAIL.
No automatic fallback permits untrusted code to use this lane.

Before commands run, M4 freezes an output tree using a private Git index populated
from the validated base and reloaded M3 artifact bytes. It does not stage the
verification worktree. File writes use no-follow, descriptor-relative parent
traversal and atomic replacement; links (including dangling links and hard links)
and special files fail closed. A bounded full inventory is compared after every
check, including ignored files, empty directories, permissions, and the worktree
Git marker. Unauthorized mutation aborts acceptance. Signing always uses the
previously frozen tree, so post-check files cannot enter the accepted commit.
Git absence is recognized only after a successful literal-path lookup under a
validated exact commit. Missing commits/blobs and failed reads are errors, not
absence; incomparable edits with different base file states cannot auto-resolve.

If accumulated verification fails, the integrator deterministically bisects the receipt set by replaying counterfactual subsets from the frozen root commit and re-running the same verification policy. Overlap classification is recomputed for each subset rather than reusing the full-run resolution state. When one receipt can be isolated, `M4ReceiptRevisionRequired` is emitted with `action=replan`, and `ProjectVerificationError.offending_receipt_hash` identifies it. Interaction-only failures where neither half fails independently return no single offending receipt rather than inventing attribution.

## IntegrationReceipt

A successful **trusted development-fixture** integration emits a Station-signed
`factory-integration-receipt-v2` value. Version 2 adds a verification-policy hash
and signed `evidence_level=development_fixture`; every check records
`execution_boundary=trusted_fixture_unsandboxed`. Consumers must not relabel these
as measured live/production acceptance evidence. Version 1 historical signatures
are not retroactively evidence of the new checks.

The receipt binds:

- execution-plan hash;
- integration-plan hash;
- ordered input receipt hashes;
- deterministic output commit;
- project verification results;
- all HITL conflict resolutions;
- integration timestamp;
- Station key identity and signature;
- exact verification policy (commands, deadlines, caps, and execution boundary).

The output commit is deterministic for the same accepted evidence, conflict resolutions, and root commit. The receipt itself includes an integration timestamp and is therefore an auditable issuance record rather than a reproducibility identifier.

## Current scope

This implements deterministic project integration for M4-R1 through M4-R5 and M4-R7, plus deterministic single-receipt attribution for isolatable M4-R6 regressions. Multi-receipt interaction failures remain fail-closed and intentionally unattributed. M4-R8's receipt-backed ready-DAG snapshot was implemented in the preceding stage. Scheduler intelligence remains separate: engine/node selection, continuous bottleneck measurement, automatic swarm resizing, and structural re-planning correspond to M4-R9 through M4-R13.

## Requirement-to-test mapping and remaining boundary

| Issue #63 acceptance boundary | Regression evidence |
| --- | --- |
| No unreceipted accepted-tree changes | `M4AcceptanceSafetyTests`: extra-file, artifact mutation, ignored/cache output, per-check inventory, post-check frozen-tree tests |
| Non-following filesystem effects | `PathBoundaryTests`: live/dangling links, hard links, directory and target substitution, reserved paths, special files, literal whitespace paths |
| Fail-closed verification execution | `VerificationInputTests`, `FixtureSupervisorTests`, default-no-dispatch, UNKNOWN launch, output-overflow and signed fixture-label tests |
| Absence versus unavailable Git evidence | `M4AcceptanceSafetyTests`: exact absence/empty, missing commit/blob, failing lookup, different incomparable bases |

Keep issue #63 open until a separately reviewed OS-isolated runner and its
filesystem/network/process/memory/output containment evidence exist. Native
trusted-fixture success is not that evidence. Host integration storage, Git
configuration, signing identity, and callbacks remain trusted; a hostile process
with the same host UID is outside this private-worktree boundary. M4 artifact
base files over 16 MiB or inventories over 100,000 entries/1 GiB fail closed.

The lifecycle fix in #61 and ownership/packaging stack #59/#50 are separate.
Ownership review must cover `m4_integrator.py`, `m4_safety.py`, `m4_evidence.py`, and
`m4_scheduler.py`; no baseline is silently advanced by this repair. Downstream
M4/evaluation consumers must distinguish fixture IntegrationReceipt v2 from
measured M3 worker observations before promoting experiment claims.

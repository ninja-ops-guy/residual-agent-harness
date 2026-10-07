# M4 deterministic integration

This stage consumes only `EvidenceIntegrationPlan` values built from locally verified M3 receipts. It is the first Factory stage allowed to construct a project-level Git commit from accepted evidence.

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

When `secops_active=True`, a `security_scan` command is mandatory as well. Commands are executed directly without a shell in the isolated integration worktree. The receipt records pass/fail status, return code, and SHA-256 hashes of stdout/stderr rather than copying arbitrary command output into trusted evidence.

### Isolated verification runner

Candidate-dependent verification commands run only inside the OS-isolated runner (`residual/factory/m4_sandbox.py`), which constructs a fresh Linux sandbox per command: user + mount + PID + IPC + UTS + network namespaces (`unshare --user --map-root-user --mount --pid --fork --net --ipc --uts`), a minimal read-only chroot root, bounded tmpfs scratch (`size=`-capped), `RLIMIT_AS`/`RLIMIT_CPU`/`RLIMIT_FSIZE`/`RLIMIT_NOFILE`/`RLIMIT_CORE` ceilings, a finite wall-clock deadline, bounded hashed output capture, and deterministic typed outcomes (PASS / FAIL / UNKNOWN / ERROR). A pre-exec readiness pipe separates sandbox setup failure (`M4SANDBOX-ERROR:` prefix on stderr -> ERROR) from candidate behaviour; a candidate exiting with code 125 is an ordinary candidate FAIL, and an exec() failure after readiness (e.g. missing executable) is `unknown`/`launch_failed`, matching the fixture lane's typing.

**Fail-closed probe policy.** `probe_isolation()` runs once before any candidate command; on non-Linux platforms, a missing `unshare` binary, or a rejected namespace probe (including rejection of the `--ipc`/`--uts` flags) the runner returns UNKNOWN/ERROR and `require_isolation()` raises. There is deliberately no fallback to unsandboxed execution of candidate-dependent commands.

**Execution boundary.** Receipts record `execution_boundary=linux-userns-isolated-v1` for sandboxed verification and `trusted_fixture_unsandboxed` for `trusted_fixture_mode=True` (explicit, operator-reviewed development fixtures only — this lane is NOT sandboxed). Correspondingly, integration receipts carry `evidence_level=isolated_candidate_verification` for sandboxed runs versus `development_fixture` for fixture runs.

**Explicit non-claims.** The sandbox does not configure cgroups (resource ceilings are rlimits, namespace lifetimes, and bounded tmpfs only); a same-UID host process adversary is outside the threat boundary (user namespaces protect kernel objects, not same-UID ptrace on the host); isolation is Linux-only; and `trusted_fixture_mode` runs verification unsandboxed and must never be pointed at untrusted candidate content.

If accumulated verification fails, the integrator deterministically bisects the receipt set by replaying counterfactual subsets from the frozen root commit and re-running the same verification policy. Overlap classification is recomputed for each subset rather than reusing the full-run resolution state. When one receipt can be isolated, `M4ReceiptRevisionRequired` is emitted with `action=replan`, and `ProjectVerificationError.offending_receipt_hash` identifies it. Interaction-only failures where neither half fails independently return no single offending receipt rather than inventing attribution.

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

This implements deterministic project integration for M4-R1 through M4-R5 and M4-R7, plus deterministic single-receipt attribution for isolatable M4-R6 regressions. Multi-receipt interaction failures remain fail-closed and intentionally unattributed. M4-R8's receipt-backed ready-DAG snapshot was implemented in the preceding stage. Scheduler intelligence remains separate: engine/node selection, continuous bottleneck measurement, automatic swarm resizing, and structural re-planning correspond to M4-R9 through M4-R13.

# R0–R5 launch preparation

`python -m residual.eval.launch` prepares an integrity-bound launch record and a
deterministic task/configuration/repetition schedule. It does not invoke models,
run task code, or collect confirmatory results. Every scheduled item is `NOT_RUN`;
`results` is null. The protocol remains blocked pending real task artifacts,
model identity, intervention adapters, and merged-main M4 qualification.

From a clean checkout, use the full commit SHA intended for qualification and
the independently retained SHA256 from the protocol preparation step:

```bash
python -m residual.eval.launch \
  --repo /absolute/path/to/residual-agent-harness \
  --merged-main-sha FULL_COMMIT_SHA \
  --protocol docs/evaluation/r0-r5.protocol.json \
  --protocol-sha256 RETAINED_PROTOCOL_SHA256 \
  --output /absolute/path/outside/checkout/launch-preparation.json
```

The output directory must already exist. Evidence must be written outside the
checkout, and existing evidence files are never overwritten. Exit 0 means only
that preparation evidence was written: inspect `blockers` and
`live_execution_enabled`, which remains false. `--mode live` always returns 2
before preparation or provider access. No environment variable, protocol flag,
or qualification JSON file can enable measured execution in this version.

The command checks the exact HEAD and tree, tracked/untracked changes, index
flags that can conceal modifications, protocol byte hash, workload byte and
manifest hashes, population, seeds, and R0–R5 identifiers. It rejects symlinked
inputs and repository escape paths. Submodule qualification is unsupported and
rejected. Model/settings are embedded in the hashed protocol; a separate optional
`config: {path, sha256}` binding is also checked. The preparation record retains
model metadata (including unresolved nulls), Python, platform, machine and Git
identities; it does not serialize environment variables or credentials.

On Linux it invokes the actual `residual.factory.m4_sandbox.probe_isolation`
from the inspected checkout in a fresh Python process with a minimal environment.
A checkout without #81's M4 module records `UNKNOWN`; unavailable namespaces or
probe errors remain blockers. Probe success alone is never boundary qualification.
The checkout is inspected again after probing. This is a launch preparation
check, not an isolation boundary against concurrent malicious filesystem writers.

Optional `--qualification PATH` retains the digest and validates the shape of an
externally collected qualification record:

```json
{
  "schema_version": "residual.m4-qualification.v1",
  "main_sha": "FULL_MERGED_MAIN_SHA",
  "main_tree": "FULL_MERGED_MAIN_TREE",
  "pr81_merged": true,
  "issue63_closed": true,
  "independent_audit": "PASS",
  "checks": [
    {"head_sha": "FULL_MERGED_MAIN_SHA", "run_id": 123, "conclusion": "success"}
  ]
}
```

This example is a schema illustration, not qualification evidence. Missing,
failed, skipped or mismatched evidence records `UNKNOWN`. Even a structurally
valid record is `RECORDED_UNAUTHENTICATED`: local JSON cannot establish GitHub
merge status, complete required-check coverage or independent review. The
supplied SHA is not represented as authenticated merged main. Later integration
must authenticate that provenance and the retained #63 closure evidence with exact merged-main tests, bind
reviewed real R0–R5 adapters and frozen model/settings, and add launch-boundary
checks before enabling execution. This module deliberately does not change
Factory, M4 acceptance, or issue state.

Fixture validation:

```bash
python -m pytest tests/test_eval_launch.py tests/test_r0_r5_protocol.py -q
```

These tests use disposable Git repositories, exercise dirty/hidden changes,
hash/head/path mismatches, missing capabilities, schedule accounting, output
preservation and attempted self-authorization. No fixture counters are presented
as measured results.

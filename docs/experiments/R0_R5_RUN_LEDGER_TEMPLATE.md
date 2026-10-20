# R0–R5 Run Ledger Template

**Schema:** `residual.r0-r5.run-ledger.v1`. One ledger entry per run. Fields marked REQUIRED must be non-null before the run's evidence is admissible; a missing REQUIRED field makes the run non-qualification. Copy this template per run; never edit a completed entry — corrections append a new entry referencing the original run ID.

```json
{
  "schema_version": "residual.r0-r5.run-ledger.v1",
  "run_id": "r0r5-YYYYMMDD-<short-commit>-<seq>",
  "opened_utc": null,
  "closed_utc": null,
  "operator": null,
  "purpose": "qualification | smoke | confirmatory | degradation | heterogeneous | soak",
  "evidence_level": "development_fixture | live_model",
  "publication_ready": false,

  "source_identity": {
    "repo": "ninja-ops-guy/residual-agent-harness",
    "commit_sha": "REQUIRED: 40-hex, == git rev-parse HEAD",
    "tree_sha": "REQUIRED: 40-hex, == git rev-parse HEAD^{tree}",
    "dirty": false,
    "index_flags_clear": true,
    "submodules_present": false,
    "git_version": null
  },

  "environment": {
    "python_version": "REQUIRED",
    "python_executable": "REQUIRED",
    "platform": "REQUIRED",
    "machine": "REQUIRED",
    "dependency_lock_sha256": "REQUIRED: hash of frozen dependency manifest (pip lock / uv lock)",
    "dependency_lock_path": "REQUIRED: retained artifact path",
    "note": "environment variables and credentials are never serialized"
  },

  "qualification_binding": {
    "m4_qualification_sha256": "REQUIRED for live runs: SHA-256 of residual.m4-qualification.v1 record (#88 / preflight)",
    "m4_qualification_main_sha": "REQUIRED: must equal source_identity.commit_sha",
    "namespace_probe_status": "PASS | UNKNOWN | ERROR (PASS required; skip is non-qualification)",
    "namespace_probe_evidence_sha256": null
  },

  "protocol_binding": {
    "protocol_path": "docs/evaluation/r0-r5.protocol.json",
    "protocol_sha256": "REQUIRED",
    "frozen_protocol_doc_sha256": "REQUIRED: SHA-256 of docs/experiments/R0_R5_FROZEN_PROTOCOL.md",
    "analysis_plan_sha256": "REQUIRED",
    "external_commitment_digest": "REQUIRED for confirmatory: independently retained pre-outcome commitment",
    "external_commitment_channel": null
  },

  "corpus_binding": {
    "corpus_manifest_sha256": "REQUIRED",
    "tier": "T1_fixture | T2_adversarial | T3_confirmatory",
    "workload_path": null,
    "workload_sha256": null,
    "workload_manifest_hash": null,
    "task_count": null,
    "family_count": null
  },

  "configuration_binding": {
    "configurations": ["R0", "R1", "R2", "R3", "R4", "R5"],
    "adapter_sha256": {"R0": null, "R1": null, "R2": null, "R3": null, "R4": null, "R5": null},
    "verifier_implementation_sha256": "REQUIRED",
    "verifier_policy_revision": "REQUIRED",
    "grader_identity": "REQUIRED",
    "grader_revision": "REQUIRED"
  },

  "model_binding": {
    "provider": "REQUIRED",
    "immutable_model_id": "REQUIRED",
    "observed_revision": null,
    "sampling": {"temperature": 0.0, "top_p": 1.0, "max_output_tokens": 512},
    "selection_rule_version": "models-routing.v1"
  },

  "schedule": {
    "repetitions": 10,
    "seeds": [20260914, 20260915, 20260916, 20260917, 20260918, 20260919, 20260920, 20260921, 20260922, 20260923],
    "seed_scope": "schedule only",
    "precomputed_schedule_sha256": "REQUIRED",
    "scheduled_denominator_N": "REQUIRED: 6 x families x 3 x 10"
  },

  "artifacts": {
    "bundle_run_dir": null,
    "bundle_manifest_sha256": "REQUIRED at close",
    "report_sha256": null,
    "launch_preparation_sha256": null,
    "per_artifact_hashes": "see bundle manifest.json (bundle-v1)"
  },

  "outcome": {
    "status": "NOT_RUN | COMPLETED | ABORTED | INVALID",
    "cells_scheduled": null,
    "cells_recorded": null,
    "cells_missing": null,
    "verifier_state_counts": {"PASS": null, "FAIL": null, "UNKNOWN": null, "ERROR": null, "SKIPPED": null},
    "invariant_violations": [],
    "summary": null
  },

  "deviations": [
    {"description": null, "protocol_section": null, "discovered_before_outcome_access": null, "disposition": "amendment_requires_new_version"}
  ],

  "provenance_notes": "fixture and smoke results in this ledger are development evidence and are never promoted into research claims"
}
```

## Ledger rules

1. Run ID is immutable; resume preserves the original run identity and never counts recovered evidence as new execution.
2. Qualification runs (M4/#88) and study runs use separate entries; a study entry must reference the qualification entry's SHA-256.
3. Namespace-skip or UNKNOWN probe outcomes record `namespace_probe_status != PASS` and block live runs.
4. Deviations discovered after outcome access are recorded with `discovered_before_outcome_access: false` and never retroactively change the frozen plan.
5. The ledger entry's own SHA-256 is computed at close and retained with the bundle.

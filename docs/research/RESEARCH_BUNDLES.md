# Frozen research evidence bundles

RESIDUAL research claims should be generated from retained experiment artifacts rather than copied into a paper by hand. `residual.research_bundle` freezes exact artifact bytes, extracts declared JSON Pointer metrics, and binds every extracted value to the SHA-256 of the artifact that supplied it.

## Freeze a bundle

Create a JSON specification containing `experiment_id`, `source_commit`, `artifacts`, optional `metadata`, and a `metrics` array. Each metric contains `name`, `artifact`, `pointer`, and optional `unit`.

```json
{"experiment_id":"recursive-maintenance-20260915","source_commit":"cac91abe34fa16670de71a77acfffeadd6642d6a","artifacts":["results.json","recovery.json"],"metrics":[{"name":"Authority false accepts","artifact":"results.json","pointer":"/experiments/authority_non_escalation/false_accepts","unit":"cases"}]}
```

Run the offline freeze and render the manuscript table directly from the frozen metric rows:

```bash
python scripts/research_bundle.py freeze --root runs/self-maintenance-study --spec research-bundle-spec.json --manifest research-bundle-manifest.json --table research-table.md
```

## Verify from a clean checkout

No model credentials are required:

```bash
python scripts/research_bundle.py verify --root runs/self-maintenance-study --manifest research-bundle-manifest.json --table research-table.md
```

Verification fails if an artifact changes, a manifest is edited without recomputing its bundle hash, a source-bound metric no longer equals the declared JSON Pointer value, a table drifts from the manifest, or a path escapes the evidence root.

## Claim discipline

A frozen bundle proves provenance and deterministic extraction. It does not prove that an experiment design is valid, that a model is competent, or that the metric should be interpreted causally. UNKNOWN/missing measurements must remain represented by their actual retained values rather than being rewritten as zero.

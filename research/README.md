# RESIDUAL Research Catalog

This branch is the versioned research plane for the RESIDUAL Research Workbench. Product code remains on the normal product branch; Command Station fetches this catalog by exact commit without checking the research branch out over the operator's working tree.

## Identity rules

- experiment IDs are immutable after the first retained Workbench run;
- changing a definition after a retained run requires a new experiment ID;
- acceptance contracts remain frozen for an authoritative experiment;
- failures, blocked starts, and inconclusive outcomes are never rewritten as PASS;
- unknown usage is `null`, never zero;
- catalog commit SHA and canonical experiment-definition SHA-256 are bound into each run manifest;
- research definitions do not grant provider, filesystem, network, merge, deployment, verifier, M4, or promotion authority.

The product runtime additionally rejects definition drift if a previously used experiment ID resolves to different canonical bytes.

## Installed experiments

- `M6-WB-001` — **runnable**. One first-authoritative Workbench end-to-end governance pilot using an onboarded local Ollama model.
- `M6-SCALE-001` — **staged**. Swarm scaling sweep.
- `M6-FAIL-001` — **staged**. Worker and transport death matrix.
- `M6-CONFLICT-001` — **staged**. Contradictory-worker evidence resolution.
- `M6-ABLATE-001` — **staged**. Governance ablation.

A staged definition is discoverable and inspectable in the Portal but is not executable until a locally allow-listed product adapter exists.

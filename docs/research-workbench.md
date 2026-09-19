# Research Workbench

The Research Workbench is a native Command Station / Portal view. It separates executable RESIDUAL code from versioned research definitions: production code remains on the product branch while experiment definitions are fetched from `research/experiment-catalog`.

Every imported run binds the exact catalog commit, canonical experiment-definition SHA-256, product Git head, provider/model identity, environment details, event evidence, and final checksums. Unknown usage remains `null`; failures are retained rather than rewritten as successful trials. Experiment definitions never grant provider, filesystem, network, merge, deployment, verifier, or promotion authority.

## Portal workflow

1. Onboard models in **Model workshop**.
2. Open **Research workbench**.
3. Sync the experiment catalog or use the exact cached catalog when the remote is unavailable.
4. Select a runnable experiment and choose **Run experiment**.
5. Follow execution through the normal Station job tray. The first pilot uses declarative JSON only; executable candidate checks are not enabled.
6. Inspect retained run status in Workbench and export the ZIP evidence bundle.

No checkout of the research branch replaces the user's working tree. Catalog contents are fetched by Git, cached by exact commit, and integrity checked before import.

The initial catalog installs M6-WB-001 plus staged definitions for scaling, worker/transport failure, contradictory-worker, and governance-ablation campaigns. M6-WB-001 has a real execution adapter that asks the onboarded model for one declarative JSON research artifact. Host-owned `json_valid` / `json_exact` checks verify it; the pilot does not execute model-authored code. Staged experiments remain visible but cannot be launched until their adapters are implemented; the Portal does not present definition availability as experimental execution.

## CLI parity

`residual research` lists the current catalog, `residual research sync` refreshes it, and `residual research import <ID>` creates a hash-bound workspace. The Portal is the normal operator path; CLI commands exist for automation and debugging.

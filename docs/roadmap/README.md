# World-class build: start here

The seven uploaded specifications are preserved verbatim in [source](source/). They describe several generations of the project. Their checkmarks mean **documented**, not implemented or validated. The v0.2 gap analysis is historical; use the current status below when assigning work.

The tested v0.3.0 baseline is on GitHub at `ff563f4c8fdd59b3f604a215b1d0c2b66f393f92`. Its complete source tree matches the previously tested local release `3d80e3ff7ad4ec9c2c406f33824259a6ce27ca49`: 190 Python tests, 17 browser checks, installed-wheel and extracted-bundle verification. See [validation](../station/VALIDATION.md) for what was actually run. Future additions do not inherit those test results.

Read [DELEGATION.md](DELEGATION.md) for ownership and deliverables, then [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md) before coding against shared interfaces. [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md) records corrections to the uploaded drafts. Those integration decisions take precedence over conflicting draft snippets. The v0.4.0 [Track 1 implementation](TRACK-1-IMPLEMENTATION.md) now supplies the shared APIs and imported module adapters; [CONFLICT_RESOLUTIONS.md](CONFLICT_RESOLUTIONS.md) records the latest binding decisions.

| Capability | Current status |
|---|---|
| Frozen controlled study, independent final grading, contract stress fixtures | Implemented in the study CLI; scripted validation only, live model advantage unmeasured |
| LDD mission state, isolated candidates, local checks, revision-bound review | Implemented and fixture/browser tested |
| Provider adapters, budgeted failover, observation bridge and console | Implemented; live inference remains untested |
| Goal contracts, verifier order, brakes, station loop, provider-call quarantine | Implemented; token/time brakes operate between waves |
| Receipt binding and cache identity | Implemented in 0.4.0: versioned envelopes, prerequisite propagation, exact-revision station receipts, modern cache revalidation with explicit legacy boundaries |
| Station extension registry and host lifecycle dispatch | Implemented in 0.4.0; freeze at controller construction, fresh brakes, isolated diagnostics |
| Every arbitrary side-effecting action using the same quarantine gateway | Partially implemented: the provider-call quarantine gateway is live (see `residual/quarantine.py`); routing every arbitrary side-effecting action through it remains open (track D scope) |
| NetOps and SecOps modules | Imported and integrated; SecOps runs before staging, NetOps requires a host telemetry client and has no live device executor |
| Trajectory, TUI, memory and HITL | Components and lifecycle adapters implemented; structural comparison, local indexing and authenticated-host HITL API. Full tool replay and automatic resume are still open (track E scope) |
| Goal-directed context curator and isolated sub-agent pool | Specification only; scoped packet compilation and worker leases already exist |
| Model-agnostic intention adapters and formal verifier certificates | Specification only |
| Mesh, federation, crypto migration, calibration | Local mesh protocol and receipt-export adapter implemented; authenticated network transport, fork reconciliation, federation and calibration remain future work |
| zk proofs, hardware-rooted attestation, adversarial hypothesis quality, epistemic merging | Research tracks; no production claim |

## Build order

1. Land and validate the foundation PR: receipt binding, active-verifier revalidation, frozen registration and trusted lifecycle dispatch.
2. Extend domain adapters with host executors and stronger semantic checks; select golden trajectory fixtures.
3. Supply operator authentication/resume policy and verified memory retrieval policy, then bounded context curation and isolated specialist execution.
4. Exercise a two-device authenticated mesh under duplicate delivery, partitions, stale revisions and revoked membership.
5. Evaluate cryptographic migration, formal proof adapters and the research frontiers with explicit threat models and measured evidence.

Crypto interfaces can be designed in parallel. Replacing every historical SHA-256 identifier is not a prerequisite for the first release. Likewise, a new reasoning interface can wrap existing providers without discarding working Ollama and cloud integrations.

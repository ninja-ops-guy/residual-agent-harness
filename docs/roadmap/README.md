# World-class build: start here

The seven uploaded specifications are preserved verbatim in [source](source/). They describe several generations of the project. Their checkmarks mean **documented**, not implemented or validated. The v0.2 gap analysis is historical; use the current status below when assigning work.

The tested v0.3.0 baseline is on GitHub at `ff563f4c8fdd59b3f604a215b1d0c2b66f393f92`. Its complete source tree matches the previously tested local release `3d80e3ff7ad4ec9c2c406f33824259a6ce27ca49`: 190 Python tests, 17 browser checks, installed-wheel and extracted-bundle verification. See [validation](../station/VALIDATION.md) for what was actually run. Future additions do not inherit those test results.

Read [DELEGATION.md](DELEGATION.md) for ownership and deliverables, then [FOUNDATION-CONTRACT.md](FOUNDATION-CONTRACT.md) before coding against shared interfaces. [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md) records corrections to the uploaded drafts. Those integration decisions take precedence over conflicting draft snippets for the planned build. They do not claim new runtime functionality is already present.

| Capability | Current status |
|---|---|
| LDD mission state, isolated candidates, local checks, revision-bound review | Implemented and fixture/browser tested |
| Provider adapters, budgeted failover, observation bridge and console | Implemented; live inference remains untested |
| Goal contracts, verifier order, brakes, station loop, provider-call quarantine | Implemented; token/time brakes operate between waves |
| Uniform receipt binding across operational modules and station caches | First implementation track; original obligation harness already revalidates cached values |
| Station extension registry and host lifecycle dispatch | First implementation track; not implemented in v0.3.0 |
| Every arbitrary side-effecting action using the same quarantine gateway | Not implemented; current scope is documented in the run-control guide |
| NetOps and SecOps modules | Specification only |
| Mandatory replay trajectories, read-only TUI, receipt-indexed memory, signed HITL | Specification only |
| Goal-directed context curator and isolated sub-agent pool | Specification only; scoped packet compilation and worker leases already exist |
| Model-agnostic intention adapters and formal verifier certificates | Specification only |
| Multi-device local-model chat, federation, crypto migration, calibration | Specification only; need the corrections recorded here |
| zk proofs, hardware-rooted attestation, adversarial hypothesis quality, epistemic merging | Research tracks; no production claim |

## Build order

1. Freeze shared contracts; implement receipt binding, active-verifier revalidation, immutable registration and trusted lifecycle dispatch.
2. Merge domain modules and deterministic trajectory fixtures against that contract. Add read-only operational views.
3. Add receipt-indexed memory and durable human escalation, then bounded context curation and isolated specialist execution.
4. Exercise a two-device authenticated mesh under duplicate delivery, partitions, stale revisions and revoked membership.
5. Evaluate cryptographic migration, formal proof adapters and the research frontiers with explicit threat models and measured evidence.

Crypto interfaces can be designed in parallel. Replacing every historical SHA-256 identifier is not a prerequisite for the first release. Likewise, a new reasoning interface can wrap existing providers without discarding working Ollama and cloud integrations.

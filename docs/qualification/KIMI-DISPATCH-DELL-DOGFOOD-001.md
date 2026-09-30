# Kimi dispatch packet — DELL dogfood campaign

Ingest `SPEC-DOGFOOD-DELL-001.md` and `DELL-SWARM-DOGFOOD-001.json` as the controlling preregistration for the post-runner-qualification dogfood campaign.

Do not execute any campaign generation until a durable `DELL_RESIDUAL_RUNNER_QUALIFIED` receipt exists.

Once the gate passes, progress event-driven through C0 -> A1 -> A2 -> COMMS1 -> FAIL1 -> REC1 -> DOCTOR1. Stop at the first failed generation and preserve first divergence. Do not retry-until-green.

Critical rules:
- Candidate C is the runner-path conformance control.
- Candidate A is the known-good useful mission control.
- Candidate B remains untouched as a historical partial/Doctor negative specimen.
- Mission bytes come from the frozen LEGION packet or byte-verified durable source, never chat reconstruction.
- After each authoritative parent Station dispatch, Kimi is observer/relay only: no manual wake, successor assignment, deadline handling, workflow advancement, or result manufacture.
- Shared Comms is projection only.
- Coordinator decomposition is frozen before dispatch and cannot broaden parent scope.
- FAIL1 requires the separately authorized live-provider gate.
- Every generation emits the common evidence envelope.
- Only emit `DELL_SWARM_DOGFOOD_QUALIFIED` if every terminal predicate is proven, including zero manual Kimi routing after each parent dispatch.

Before execution, prepare immutable generation manifests and acceptance predicates for C0/A1/A2/COMMS1/FAIL1/REC1/DOCTOR1. Preparation is allowed; execution is gated.

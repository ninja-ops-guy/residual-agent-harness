# RESIDUAL v2 Roadmap — v1 Builds v2

**Status:** PARKED / POST-v1
**Branch:** `v2/solpi-evidence-context-environment-bank`
**Execution authority:** none until RESIDUAL v1 is released and a v2 kickoff is explicitly authorized.

## Strategy

RESIDUAL v1 becomes the controlled engineering substrate used to build RESIDUAL v2. v2 development should dogfood v1's bounded workers, evidence retention, qualification gates, receipts, exact-head controls, and human approval boundaries.

The v2 program must not expand the v1 release surface. Until v1 release, this branch is documentation/specification only.

## Initial v2 sequence

1. **EVPR-001 — Evidence-Preserving Reducer**
   - Verify evidence crossing delegated-reading boundaries.
   - Add deterministic receipt verification and negative qualification cases.

2. **OBSH-003 — ObservationPack context handles**
   - Replace repeated large-context injection with CAS-backed stable handles and explicit recall.
   - Measure token/cache economics without weakening evidence availability.

3. **OBSH-AGENT-001 — Swarm Runtime Observability & Stall Intelligence**
   - Distinguish seat liveness from process, lease, work, and progress state.
   - Add evidence-backed WorkProgressReceipt and StallDiagnosisReceipt contracts.
   - Classify healthy waits, observer stalls, target failures, and verified stalls without inventing causes.
   - Correlate WorkID/MissionID/LeaseID/Factory execution/provider/tool/evidence/receipt identities in Command Station.
   - Gate autonomous checkpoint/fence/reassign/recovery through existing authority and generation-fencing rules.
   - Qualify observability, stall classification, and autonomous recovery as separate claims before SELFHOST-R0 unattended-operation claims.
   - Spec: [SPEC-OBSH-AGENT-001](SPEC-OBSH-AGENT-001.md).

4. **CMPE-004 — Compaction as ledger event**
   - Make context compaction explicit, reconstructable, and economically gated.
   - Preserve lossless references separately from lossy summaries.

5. **ENVB-002 — Environment Bank**
   - Convert v1 D2, WebVM, swarm, CI repair, qualification, and review history into replayable environments.
   - Freeze benchmark generations and enforce screening/validation isolation.

6. **M6 v2 research loop**
   - Use the Environment Bank to screen proposed improvements.
   - Require held-out validation, fixed capability floors, evidence receipts, and human authorization before protected changes.

## v1 → v2 evidence harvesting

During v1, retain artifacts that can later seed ENVB:
- failed and repaired CI runs;
- qualification artifacts and first-failure evidence;
- WebVM runs;
- D2 experiments;
- swarm tasks and review decisions;
- exact-head attestations;
- token/cost/runtime measurements where available.

Retention does **not** authorize v2 implementation during v1 convergence.

## Hard gates before v2 implementation

- v1.0.0 released from an accepted release candidate;
- v1 release evidence archived and immutable;
- v2 specs reconciled against the released v1 interfaces;
- external source placeholders/provenance in imported specs replaced with durable citations/records;
- canonical byte/line rules defined for EVPR;
- lossless context manifests defined for CMPE;
- immutable Environment Bank generation/split policy defined;
- explicit v2 kickoff / owner GO.

## Intended dogfood loop

`v1 Station → bounded v2 task → retained evidence → deterministic verification → qualification → human review → accepted v2 state`

The target is not uncontrolled recursive self-modification. RESIDUAL v1 remains the authority-constrained builder and verifier; v2 changes advance only through explicit evidence and approval gates.



## Hierarchical swarm coordination track — HCOR

**Master spec:** [`HCOR-000 — Hierarchical Coordination & Delegation Plane`](SPEC-HCOR-000-HIERARCHICAL-COORDINATION-V2.md)

HCOR turns the coordination philosophy harvested from v1 dogfooding into a durable distributed control plane: RESIDUAL owns mission truth, authority, leases, evidence, dependencies and convergence; coordinators are replaceable leased roles that decompose intent; workers execute; independent verifiers adjudicate; Station controls authoritative transitions.

The hierarchy is mission-based rather than host-based. Adding a qualified machine widens schedulable capacity without changing mission topology. Child authority is always a subset of parent authority, controlling artifacts remain directly digest-addressable at every level, ownership is lease/fencing based, and owner gates park work without making the owner coordination infrastructure.

### HCOR work packages

1. [`HCOR-001 — Mission & Delegation Kernel`](SPEC-HCOR-001-MISSION-DELEGATION-KERNEL-V2.md)
   - Durable mission/submission/assignment objects, recursive delegation, acceptance contracts, authority attenuation, leases/fencing, first-failure preservation.

2. [`HCOR-002 — Event-Driven DAG Coordinator`](SPEC-HCOR-002-EVENT-DAG-COORDINATOR-V2.md)
   - Deterministic event reducer, runnable-set computation, dependency progression, backpressure, checkpoint/replay, no polling-as-control-plane.

3. [`HCOR-003 — Resource / Capability Scheduler`](SPEC-HCOR-003-RESOURCE-CAPABILITY-SCHEDULER-V2.md)
   - Evidence-backed runner/provider/model inventory, resource admission, placement, budgets, verifier-independence constraints, scale-out by adding qualified machines.

4. [`HCOR-004 — Hierarchical Coordinator Runtime`](SPEC-HCOR-004-HIERARCHICAL-COORDINATOR-RUNTIME-V2.md)
   - Coordinators as leased/fenced replaceable roles, recursive mission decomposition, coordinator budgets, replacement without duplicate accepted work.

5. [`HCOR-005 — Independent Verification & Challenge Plane`](SPEC-HCOR-005-VERIFICATION-CHALLENGE-PLANE-V2.md)
   - Byte-authoritative candidate admission, independent verifier scheduling, challenge coordination, no verifier patching/self-close.

6. [`HCOR-006 — Coordinator Survivability & Recovery`](SPEC-HCOR-006-COORDINATOR-SURVIVABILITY-V2.md)
   - Worker/provider/coordinator/Station/host failure recovery, exactly-once authority, stale fencing, checkpoint reconciliation, HLS/provider-continuity integration.

7. [`HCOR-007 — Convergence, Scope & Backlog Admission`](SPEC-HCOR-007-CONVERGENCE-BACKLOG-ADMISSION-V2.md)
   - P0-P3 admission, WIP limits, freeze/reopen doctrine, owner-interrupt discipline, operator-return receipts, anti-thrashing.

8. [`HCOR-008 — Qualification Campaigns & Scale-Out Program`](SPEC-HCOR-008-QUALIFICATION-SCALEOUT-V2.md)
   - Single coordinator -> replacement -> two-level hierarchy -> heterogeneous cluster -> failure/independence/convergence -> 10/25/50-agent scale campaigns.

### HCOR delivery sequence

`HCOR-001 + HCOR-002 -> HCOR-003 + HCOR-005 -> HCOR-004 -> HCOR-006 + HCOR-007 -> HCOR-008`

Early dogfood target: one coordinator, three workers and one independent verifier. The first major milestone is coordinator replacement without lost/duplicate accepted work. Hierarchical and multi-host claims follow only after authority attenuation, scheduling, independent verification and survivability qualify.

### HCOR north-star metric

Primary operational metric: `owner_interventions / completed_missions`.

The target is that adding machines/agents increases throughput while this ratio falls or remains bounded. The owner supplies intent and protected decisions; RESIDUAL handles routine decomposition, scheduling, evidence, verification, recovery and convergence.

HCOR is PARKED / POST-v1. The specs are intentionally partitioned so independent cloud swarm sessions can later take HCOR-001..008 as bounded work packages. No HCOR implementation is authorized before the common v2 kickoff gates above.

**Delegation guide:** [`HCOR Cloud Swarm Delegation Pack`](HCOR-CLOUD-SWARM-DELEGATION.md) — standard work-package outputs, dependency graph, integration gates, branch isolation, and a reusable cloud-session prompt.

## Enterprise hardening track — harvested from v1 closure

The v1 PR #448 native Windows C01/C02 campaign established a precise single-host ownership boundary and exposed several intentionally unclaimed enterprise guarantees. Preserve them as v2 requirements rather than expanding the frozen v1 release surface.

### ENT-OWN-001 — Windows multi-session and cross-user ownership
Origin: v1 W15 remained not fully qualified.

Objective: demonstrate that equivalent Station data directories used from separate Windows sessions/users resolve to the same intended ownership domain and cannot admit two live Station owners.

Qualification: ordinary interactive and service-account contexts; separate Windows sessions/users; Global RESIDUAL Station mutex creation/open behavior; fail-closed privilege/access errors; clean/crash reacquisition across sessions; retained first-failure evidence and mutation-sensitive negative controls.

### ENT-OWN-002 — Least-privilege Windows operation
Origin: v1 native qualification used an elevated runneradmin account.

Objective: make ordinary non-admin operation a first-class supported and continuously qualified deployment profile.

Qualification: operate/recover without elevation where permitted; identify truly privileged operations; service-account and managed-host profiles; fail closed rather than silently escalating or weakening ownership.

### ENT-STOR-003 — Enterprise filesystem qualification matrix
Origin: v1 Windows evidence is bound to NTFS.

Objective: explicitly define supported enterprise filesystems and storage topologies.

Qualification: retain NTFS baseline; add storage modes only when ownership, durability, atomicity and recovery semantics qualify; explicitly reject unsupported network/distributed profiles; bind claims to tested filesystem/topology combinations.

### ENT-THREAT-004 — Hostile-local and same-user threat-model expansion
Origin: v1 assumes a trusted local filesystem and non-hostile same-user environment.

Objective: decide which local-adversary behaviors enterprise v2 defends against and turn accepted protections into enforceable invariants.

Research: same-user interference; state/lock tampering; ACL hardening; service identity isolation; explicit distinction between protected behavior and deployment assumptions. Do not claim protection before adversarial qualification.

### ENT-HA-005 — Distributed/HA fencing authority
Origin: v1 makes no distributed/HA Station ownership claim.

Objective: design explicit multi-host authority and fencing instead of implicitly extending the single-host mutex/flock abstraction.

Required design questions: fencing-token/lease authority; split-brain prevention; partitions; clock assumptions; durable authority epochs; crash/restart/rejoin; quorum/external coordination; evidence proving which host held mutation authority.

This is architectural v2 work, not a small v1 ownership patch.

### ENT-ASSURE-006 — Independent human assurance
Origin: v1 used maintainer owner review plus automated technical challenge; no independent third-party human security review was claimed.

Objective: create an enterprise assurance lane that can incorporate independent human review without conflating it with automated review.

Program: define independence/conflict rules; bind reviews to exact source/tree/artifact identity; retain findings/remediation provenance; distinguish maintainer approval, automated challenge, independent security review and release authorization; consider external assessment before enterprise production claims.

## Enterprise-v2 claims discipline

These are roadmap inputs, not current guarantees. v1 tested scope remains authoritative until each v2 requirement is implemented and qualified. Expand enterprise claims only after negative tests, exact-head evidence and deployment-profile qualification exist.

Likely progression:

single-host evidenced v1 baseline -> least-privilege enterprise profile -> multi-session/cross-user qualification -> hardened local threat model -> explicit storage matrix -> distributed/HA fencing -> independent enterprise assurance.

Reuse the Environment Bank by retaining PR #448 Windows first-failure evidence, exact-head artifacts, sensitivity mutations and accepted scope boundaries as replayable v2 qualification inputs.



## Operability / continuity track — Governed Host Lifecycle Supervisor

**Spec:** [`SPEC-HOST-LIFECYCLE-SUPERVISOR-V2.md`](SPEC-HOST-LIFECYCLE-SUPERVISOR-V2.md)

Harvested from the 2026-09-28 v1 dogfood incident where a safe gateway auth-snapshot refresh required a full desktop lifecycle restart but the active agent correctly returned `OWNER_PHYSICAL_ACTION_REQUIRED` rather than improvising process termination or UI actuation.

The v2 Host Lifecycle Supervisor (HLS) is a separately governed, restart-surviving control component for narrowly allowlisted lifecycle capabilities. It binds DF-AUTH-001 dispatch/authority epochs, immutable prestate receipts, process/service identity transitions, restart-loop protection, post-restart Mission Board/ledger/seat/checkpoint reconciliation, provider-readiness revalidation, stale-generation fencing, and explicit `OWNER_PHYSICAL_ACTION_REQUIRED` fallback.

HLS is not a general shell or ambient root daemon. Its first qualification campaigns cover Kimi/OpenClaw coordinator restart, RESIDUAL Station restart, provider-runtime restart, authority-rescission races, and later host cold-start reconstruction. It composes with BL-006/007/008/009 lessons, SC-MESH continuity, EVPR/OBSH/CMPE/ENVB, HarnessBench adversarial restart campaigns, and enterprise least-privilege/threat/HA work.

Like all v2 work, HLS is PARKED / POST-v1 and carries no implementation authority before the explicit v2 kickoff gate.

## Harness-neutral evaluation track — HarnessBench

**Spec:** [`SPEC-HARNESSBENCH-V2.md`](SPEC-HARNESSBENCH-V2.md)

HarnessBench makes the agent harness/orchestration layer a controlled experimental variable. The same frozen task, repository/environment, model/runtime, tool surface, budgets, and verifier can be executed through different harnesses while RESIDUAL retains raw evidence, produces rebuildable normalized traces, independently verifies outcomes, and reports multidimensional tradeoffs rather than a universal ranking.

This track is deliberately coupled to the existing v2 program:

- **EVPR-001** supplies evidence-preserving reduction and receipt verification.
- **OBSH-003 / CMPE-004** supply explicit context identity, recall, and compaction accounting so context policy does not become an invisible confounder.
- **ENVB-002** supplies immutable replayable environments and screening/validation/held-out split discipline.
- **SC-MESH / shared communications** becomes the declared communication plane for later distributed and heterogeneous-harness experiments.
- **M6 / AX-21** consumes HarnessBench as an experimental instrument for separating model, harness, topology, context, and control-layer effects.

### HarnessBench delivery sequence

1. **HB-00 — Experiment schema and canonical serialization**
   - Freeze experiment identities, treatment variables, invariants, budgets, and terminal-state vocabulary.

2. **HB-01 — FrozenMission**
   - Hash the immutable mission/acceptance/tool/budget envelope before execution.

3. **HB-02 — HarnessAdapter contract**
   - Establish harness-neutral lifecycle, capability, event, interruption, termination, and artifact collection boundaries.

4. **HB-03 — Generic CLI adapter**
   - Prove the interface does not depend on a privileged first-party harness.

5. **HB-04 / HB-05 — Codex and OpenClaw adapters**
   - Establish the first practical controlled comparison pair.

6. **HB-06 — Normalized trace projection**
   - Preserve raw harness-native evidence and build a deterministic/rebuildable common event projection.

7. **HB-07 / HB-08 — Independent verifier + HarnessBenchReceipt**
   - Harness-native completion never equals PASS; bind every admissible outcome to independent verification and sealed identities.

8. **HB-09 / HB-10 — Replay bundles + contamination/drift detection**
   - Detect cross-run state leakage, cached-solution exposure, model/runtime/harness drift, undeclared memory, repository mutation, and other invalidating conditions.

9. **HB-11 / HB-12 — Campaign scheduler + statistical/Pareto reporting**
   - Add paired/randomized repeated trials, preregistered exclusions, uncertainty/effect reporting, and reliability/latency/compute/intervention tradeoff surfaces.

10. **HB-15 / HB-16 — Local telemetry + Environment Bank held-out integration**
    - Bind local hardware/inference manifests and enforce immutable screening/validation/confirmatory environment generations.

11. **HB-13 / HB-14 — Distributed and heterogeneous-harness campaigns**
    - Compare homogeneous versus mixed harness/model/host swarms only after the relevant shared-communications identity and continuity contracts qualify.

12. **HB-17 — Adversarial qualification**
    - False completion, child-process escape, out-of-worktree mutation, drift, dropped/duplicated/reordered events, budget overrun, network escape, cached-solution/shared-memory contamination, verifier crash, RESIDUAL restart, host loss, undeclared communications, and normalized-trace corruption.

### HarnessBench release gates

HarnessBench remains research-only until:
- at least two independent adapters execute the same frozen corpus against the same frozen model/runtime and environment;
- raw evidence and normalized projections are independently inspectable and projection rebuild succeeds;
- false-completion and contamination injections are detected with live sensitivity controls;
- campaign repetition/randomization rules are preregistered;
- every admissible result has a valid HarnessBenchReceipt;
- comparative results can be reconstructed from sealed artifacts without trusting the UI.

Heterogeneous-swarm claims require additional SC-MESH qualification for communications identity, continuity, host loss/rejoin, and cross-harness evidence propagation.

### Intended first practical campaign

After v2 kickoff and adapter qualification, use a controlled local inference profile as an early campaign: one frozen local model/runtime and host profile, one frozen coding corpus, and Codex versus OpenClaw (plus `generic_cli` as a minimal control where useful). This campaign is intended to validate the experimental machinery; it must not be presented as a universal harness ranking.

The progression is:

`frozen single-agent comparisons -> repeated controlled campaigns -> Environment Bank held-out validation -> distributed homogeneous swarms -> heterogeneous harness/model swarms -> M6/AX-21 causal studies`.

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

3. **CMPE-004 — Compaction as ledger event**
   - Make context compaction explicit, reconstructable, and economically gated.
   - Preserve lossless references separately from lossy summaries.

4. **ENVB-002 — Environment Bank**
   - Convert v1 D2, WebVM, swarm, CI repair, qualification, and review history into replayable environments.
   - Freeze benchmark generations and enforce screening/validation isolation.

5. **M6 v2 research loop**
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

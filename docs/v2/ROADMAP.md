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

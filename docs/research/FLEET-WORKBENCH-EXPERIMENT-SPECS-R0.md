# FLEET Research Workbench Experiment Specifications R0

Status: **STAGED / NON-RUNNABLE**

Companion to `FLEET-MULTI-STATION-RESEARCH-PROGRAM-R0.md`. These are preregistration templates for future Research Workbench catalog entries. No adapter is authorized by this document.

## Common evidence envelope

Every Fleet experiment must bind:

- experiment ID and exact definition digest;
- product HEAD/TREE or package identity;
- Station IDs, data-root identities, and epochs;
- host OS/runtime identities;
- runner/coordinator/claw IDs and generations;
- provider route/readiness identities where applicable;
- pre-experiment event heads;
- injected failure identity and timestamp;
- checkpoint/evidence identities;
- authority-transfer/fencing receipts;
- post-experiment event heads;
- Shared Comms projection/cursor evidence where applicable;
- all owner interventions;
- terminal predicate results.

Unknown values remain UNKNOWN/null. Chat prose cannot substitute for missing durable evidence.

## FLEET-WB-001 — Single-Station hierarchy

**Question:** Can one Station coordinate multiple explicitly mapped claws through a replaceable local coordinator without Kimi/chat becoming authority?

**Topology:** DELL Linux reference Station.

**Negative control:** discovered but unmapped claw receives no assignment.

**PASS:** all assignment/ACK/result transitions are Station-bound; unmapped claw receives none; coordinator restart reconstructs from durable state; no owner routing for the bounded mission.

## FLEET-WB-002 — Same-OS reproducibility

**Question:** Does the DELL onboarding/qualification path reproduce on DBOX without bespoke normalization?

**Topology:** DELL Linux + DBOX Linux.

**PASS:** same generic discovery/mapping/qualification contracts operate on DBOX. Every manual intervention is ledgered. No unrecorded host-specific workaround.

## FLEET-WB-003 — Cross-platform remote coordination

**Question:** Can coordination location differ from execution location across Windows/WSL and Linux?

**Topology:** LEGION Windows/WSL Station and DELL Linux claws, then reverse direction.

**PASS:** bounded mission completes in both directions; claw process remains on original host; authority binds the coordinating Station epoch; no OS-specific authority exception.

## FLEET-WB-004 — Station process failover

**Question:** If only the Station process dies, can surviving claws safely rebind to a configured alternate Station?

**Failure injection:** terminate Station process only.

**Negative control:** alternate not enrolled -> no rebind.

**PASS:** reconnect grace observed; old authority fenced before alternate activation; fresh generation issued; no dual acceptance.

## FLEET-WB-005 — Station domain failover

**Question:** Can a portable mission continue after loss of the Station host/domain?

**Precondition:** checkpoint/evidence package independently proven portable/available to alternate.

**PASS:** old delegation fenced; alternate admits exact checkpoint/evidence; mission continues; returning old Station cannot resume old epoch.

## FLEET-WB-006 — Shared Comms independence

**Question:** Is Shared Comms observability non-authoritative?

**Failure injection:** disconnect projection transport.

**PASS:** mission continues; authoritative event log advances; outbox retains pending projections; reconnect catches up by source identity; duplicate authoritative transitions = 0.

## FLEET-WB-007 — Provider continuity within swarm

**Question:** Does an eligible provider availability failure degrade to an independently READY/admitted fallback without hiding the original failure?

**PASS:** fallback occurs only for policy-eligible class; route decision receipt preserves requested and selected routes; non-eligible correctness/authority failures do not fall back.

## FLEET-WB-008 — Inter-Station partition

**Question:** Do leases/epochs/fencing prevent split brain during partition?

**Failure injection:** sever Station-to-Station path while preserving selected local execution.

**PASS:** at most one Station can authoritatively accept the delegated mission at a time. Any dual authoritative acceptance is a hard FAIL.

## FLEET-WB-009 — Coordinator replacement

**Question:** Is the local coordinator replaceable without losing mission truth?

**Failure injection:** terminate coordinator only.

**PASS:** Station state remains sufficient to issue a fresh coordinator generation and reconstruct bounded local work; no chat-memory recovery dependency.

## FLEET-WB-010 — Compound fault-tolerance demonstration

**Sequence:** eligible provider failure -> claw loss -> Shared Comms outage -> Station failure -> alternate-Station continuation -> old Station return -> projection reconciliation.

**PASS predicates:**

- mission completed;
- zero duplicate authoritative acceptance;
- zero lost accepted events;
- zero stale-authority acceptance;
- zero unexplained provider reinvocations;
- zero projection loss after reconciliation;
- zero owner interventions inside the preregistered autonomous window.

The first failed predicate terminates the authoritative trial and is retained unchanged.

# Kimi Directive — Single-Station Autonomy R0

Use `SPEC-SINGLE-STATION-AUTONOMY-R0.md` and `SINGLE-STATION-AUTONOMY-R0.json` as the program-level readiness ledger.

This directive does not grant new deployment, merge, secret, or release authority.

## Operating rule

Track every capability separately through:

`SPECIFIED -> IMPLEMENTED_ISOLATED -> INDEPENDENTLY_REVIEWED -> INTEGRATED -> DEPLOYED_BOUNDED -> LIVE_QUALIFIED`.

Never report a contract/script/PR as operational completion.

## Scheduling priority

1. Close the DELL runner path on exact #493 successor evidence.
2. Recover BL-016 controlling lineage; do not reconstruct.
3. Prepare/implement Contract E on a non-author seat.
4. Build Doctor executable fixtures/wiring.
5. Finish FreeLLMAPI profile canary + reviewed fleet automation.
6. Prepare the exact integrated composition candidate.
7. Execute PR #490 only when its native dependencies actually exist.

## Integration owner

Assign exactly one integration owner who authored none of the principal source candidates being combined.

The owner maintains:
- exact source HEAD/TREE for every selected component;
- conflict-resolution commits;
- schema/migration/config dependencies;
- focused and combined tests;
- deploy procedure;
- rollback procedure;
- resulting integration HEAD/TREE.

A component PASS does not transfer automatically across conflict resolution.

## DELL repair

#493 exact candidate:
HEAD `b53fb74c992830fe6d8912b62019c88bbf973f84`
TREE `a4efc2b3ef702965c1b1070f692fa032382654a8`

Historical attempts remain immutable. No DB surgery.

Independent PASS -> exact-tree DELL successor qualification -> Piston -> Wrench -> Crucible -> Phase F.

Only durable `DELL_RESIDUAL_RUNNER_QUALIFIED` advances SSA-02 to LIVE_QUALIFIED.

## BL-016

Current state:
`BL016_V11_BLOCKED_ON_CONTROLLING_BYTES`.

Perform lineage recovery from known holders and durable artifact stores. No broad filesystem search and no reconstruction from summaries.

Resolve the Q2 naming collision explicitly before using any Q2 result as authority.

## FreeLLMAPI

Do not treat setup-script completion as fleet qualification.

Required progression:
`SCRIPT_REVIEWED -> CANARY_CONFIGURED -> CANARY_READY -> CANARY_QUALIFIED -> PROFILE_BY_PROFILE_EXPANSION`.

Long-running autonomy requires current readiness. Design/implement bounded readiness maintenance using fresh evidence; never extend readiness by timestamp mutation.

## Doctor

Turn #488 into executable behavior:
- normalize existing telemetry;
- detector registry;
- first-divergence reducer;
- temporal/absence rules;
- runtime adapters;
- HealthFact output.

Doctor diagnoses only. Scheduler/policy acts.

## Campaign

PR #490 is an acceptance campaign, not a scheduler implementation.

Do not give C0/A1/A2/COMMS1/FAIL1/REC1/DOCTOR1 autonomous credit until their required native mechanisms exist.

After native parent dispatch T0, Kimi must not advance ordinary workflow.

## Status output

Maintain one scoreboard:

`capability | controlling source | implementation | review | integrated tree | deployment | live qualification | blocker | owner gate`

Report only terminal, first failure, gate, material transport problem, or critical-path change.

The target is one exact-tree `SINGLE_STATION_AUTONOMY_QUALIFIED` candidate, followed by `OWNER_ABSENT_8H`.

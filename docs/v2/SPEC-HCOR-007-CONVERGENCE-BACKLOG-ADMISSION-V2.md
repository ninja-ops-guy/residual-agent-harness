# HCOR-007 — Convergence, Scope & Backlog Admission

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000

## Objective

Prevent autonomous swarms from becoming permanent construction sites. Encode when to freeze, when to reopen, and when discoveries become backlog rather than silently expanding current scope.

## Priority classes

- P0 — active operational/safety blocker;
- P1 — release/qualification blocker;
- P2 — scheduled improvement;
- P3 — research/backlog.

Discovery does not automatically authorize execution.

## Convergence rule

Freeze when:
`acceptance contract satisfied AND required independent verification PASS AND no open P0/P1 findings AND dependencies satisfied AND evidence complete`.

After freeze:
- correctness/authority/security defect may reopen through explicit successor/revision;
- UX/polish/new capability becomes new backlog work;
- future architecture goes to later milestone/version.

## Work-in-progress limits

Policy bounds:
- active implementation lanes per host;
- pending independent reviews per verifier;
- active child coordinators per coordinator;
- actionable owner gates;
- provider/model concurrency;
- total mission budget.

Coordinator must prefer finishing/verification over opening new work when WIP limits are saturated.

## Owner-interrupt discipline

Owner gate objects distinguish defined, future, blocked, actionable, satisfied. `NEEDS YOU` renders actionable only. Target owner-interrupt budget may be zero for unattended missions.

## Reopen protocol

A frozen mission reopens only with:
- finding/evidence digest;
- classification;
- affected acceptance invariant;
- successor mission/candidate identity;
- explicit authority.

No silent edits to frozen artifacts.

## Operator-return receipt

After unattended operation, produce durable baseline->current delta:
- completed/verified/failed/recovered/parked;
- provider/runner transitions;
- DAG changes;
- authority consumed/refused;
- owner interventions;
- actionable gates;
- first failures;
- current ledger/event-head digests.

## Anti-thrashing

Repeated fail/repair cycles trigger escalation/backoff policy rather than retry-until-green. Coordinators cannot create endless successor candidates without bounded repair budget.

## Negative qualification

Agent proposes scope expansion after freeze; coordinator opens excessive lanes; verifier queue saturation; multiple future owner gates incorrectly shown actionable; repair budget exhausted; P3 work preempts P0; frozen artifact edited in place; operator-return summary disagrees with event log.

## Qualification target

Run a busy program with continuous agent suggestions. System converges accepted missions, parks future ideas, respects WIP/budgets, and returns an operator delta with minimal actionable owner work.

**Terminal:** `CONVERGENCE_BACKLOG_ADMISSION_QUALIFIED`.

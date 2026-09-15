# Pinned controller and observability review

These probes export Python files from local Git objects to temporary isolated
module namespaces. They do not check out, modify, or merge either PR. The test
assertions for known defects apply to immutable reviewed snapshots; they are not
requirements to preserve defects in future runtime code.

## Swarm C / PR40 — `0063e6400fa945acf2db393f7e9d30db02cb1139`

The independent tiny-task fixture gives every topology a correct result and
0.01 seconds of productive work. Synthetic scheduling overhead is 0.001 seconds
for single, 1 second for pair and 5 seconds for swarm. These are intentionally
chosen fixture inputs, not observed execution performance. Calling the normal
`select_topology`/`record_outcome` APIs 30 times produces `swarm → pair → single`
and then 27 more single decisions. No direct estimator seeding is used.

This demonstrates that feedback can reverse the controller's initial complex
choice for this fixture. It does not prove optimal selection for all tasks or
that live swarm quality/cost dominates. Selection is greedy, with structural
priors and a threshold; there is no general exploration guarantee. Validation
must reserve a separate frozen training split and evaluate choices only after
training state is frozen.

**Reproduced blocker: duplicate outcome delivery double-counts training.** A
second `record_outcome` call for the same observation adds one more estimator
sample and overwrites the retained observation result. Thus learned state can
disagree with a replay that folds each observation once. Proposed closure:
immutable terminal outcome identity; exact duplicate is idempotent, conflicting
duplicate rejected before posterior mutation. This lane reports the bug and
does not change Swarm C.

Additional source-review limits: `success` is coerced with `bool`, so callers
must not pass an UNKNOWN string as success; omitted timing phases are treated
as zero; `quality_score` is retained but the posterior update uses binary
success. Define wall time versus summed worker time before comparing overlap.
The fixture simulator encodes topology-specific reliability assumptions and
must never be presented as validation against real model behavior.

Source: [selection and outcome mutation](https://github.com/ninja-ops-guy/residual-agent-harness/blob/0063e6400fa945acf2db393f7e9d30db02cb1139/residual/otx/controller.py#L101-L200),
[estimator update](https://github.com/ninja-ops-guy/residual-agent-harness/blob/0063e6400fa945acf2db393f7e9d30db02cb1139/residual/otx/estimator.py#L164-L186),
[phase semantics](https://github.com/ninja-ops-guy/residual-agent-harness/blob/0063e6400fa945acf2db393f7e9d30db02cb1139/residual/otx/models.py#L46-L83).

## Swarm F / PR43 — `058e25b3ca73de4528648b72b1901b2c319fe643`

**Positive executable result:** artificially incrementing the acceptance metric
by 100 does not change the report hash rebuilt from the same observations. The
report function reads observations and not the registry. Keep that direction:
durable evidence → validated projections → metrics/report. A metric label,
gauge, or alert must never create an acceptance or authorize an action.

| Reproduced finding | Minimal counterexample | Required follow-up |
|---|---|---|
| Correctness double-counts accepted tasks | Correct execution A + acceptance A + incorrect execution B yields `P(X)=2/3`; one label per execution gives `1/2` | Freeze observational unit; join acceptance to one independently labeled candidate/cell by durable identity |
| Duplicate acceptance raises acceptance count | Appending the identical acceptance again changes accepted count from 1 to 2 | Source event/candidate/decision identity and deterministic duplicate rejection or idempotence |
| Collector evidence is mutable | Editing `collector.observations[0]['correct']` changes report without tamper rejection | Rebuild only from retained authenticated evidence; immutable copied views are a convenience, not trust anchors |
| Correctness type is unchecked | `correct: "true"` is admitted, counted labeled, and treated incorrect by `is True` | Require boolean labels or explicit absent/UNKNOWN semantics; no coercion |

Additional source findings: retry `attempt` values are summed, so ordinals 1, 2,
3 become 6 “attempts”; denominator must count distinct attempts. Collector
`observations_complete_total` increments even when optional fields are missing,
and its missing gauge counts fields while the report counts observations.
Make names and denominators explicit. OTX phase names (`scheduling`,
`worker_execution`, `coordination`) differ from OBS (`dispatch`, `worker_runtime`,
no coordination); use a versioned adapter and preserve unclassified time.

Schema validation alone does not authenticate an acceptance: a caller can
construct an acceptance observation with no receipt reference. This review did
not find a writeback from PR43 metrics into accepted state; it also did not find
a complete cryptographic binding from those free-form report inputs to M4.
The collector's description of its in-memory list as “authoritative” must be
reconciled with M4: only retained, validated evidence may support a claim.

Source: [report denominators and retry aggregation](https://github.com/ninja-ops-guy/residual-agent-harness/blob/058e25b3ca73de4528648b72b1901b2c319fe643/residual/telemetry/report.py#L64-L109),
[mutable collector and completeness updates](https://github.com/ninja-ops-guy/residual-agent-harness/blob/058e25b3ca73de4528648b72b1901b2c319fe643/residual/telemetry/metric_families.py#L65-L124),
[required fields and validation](https://github.com/ninja-ops-guy/residual-agent-harness/blob/058e25b3ca73de4528648b72b1901b2c319fe643/residual/telemetry/schema.py#L82-L143).

Review gates before paper use: repair and re-review the issues above; define
event units, joins and UNKNOWN denominators in the statistical plan; replay
from immutable retained evidence; show registry deletion/mutation has no effect
on accepted state or reproduced metrics; prove exactly-once projection per
source event despite duplicate delivery. A synthetic good-path metric test
does not complete these gates.

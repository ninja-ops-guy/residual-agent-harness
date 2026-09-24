# RESIDUAL v1 incident-response qualification plan

Status: **PLANNING / DRILLS NOT EXECUTED**.

This document prepares release gate `PR-G30`. It does not declare incident-response
qualification complete, authorize production mutation, or grant break-glass authority.

## Objective

Before v1 production approval, run bounded, evidence-retaining exercises for the
five failure classes identified by the production-readiness audit:

1. credential leak;
2. database corruption;
3. runaway work/resource exhaustion;
4. host compromise;
5. evidence integrity/confidentiality breach.

`V1_INCIDENT_RESPONSE_PLAN.json` is the machine-readable exercise contract.
`scripts/validate_v1_incident_response_plan.py` verifies plan completeness and
content-addresses the plan while explicitly emitting `execution_claim: NONE`.

## Non-negotiable exercise rules

- Preserve first-failure and forensic evidence before destructive remediation.
- Never copy credential values into evidence or public issues/PRs.
- Human authority is required for containment/recovery actions that change
  credentials, trusted topology, durable state, or release disposition.
- A recovered service is not proof of recovered authority or data integrity.
- `UNKNOWN`, `BLOCKED`, and `EVIDENCE_INCOMPLETE` remain distinct from `PASS`.
- Exercises must use the approved v1 deployment profile and exact RC identity
  once those exist; this planning artifact alone cannot supply them.
- Each drill receives a unique evidence directory and immutable manifest/hash.
- A failed drill is retained as a failed attempt; do not overwrite it with a retry.

## Required evidence per executed drill

Each executed drill must retain, at minimum:

- exact RC commit/tree and artifact digest;
- approved deployment-profile digest;
- environment/preflight identity;
- incident trigger and start/end timestamps;
- operator/security roles involved;
- ordered actions and decision receipts;
- evidence captured before and after containment;
- recovery/reconciliation result;
- explicit `PASS`, `FAIL`, `UNKNOWN`, or `BLOCKED` disposition;
- SHA-256 manifest over the retained drill bundle.

## Completion rule for PR-G30

`PR-G30` remains **IN_PROGRESS** after this planning PR. It can become `VERIFIED`
only after all five required drills execute against the approved v1 scope and
selected RC, each retained bundle verifies, failures are dispositioned rather than
erased, and the release authority accepts the combined incident-response report.

No production system, credential, host, canary, or frozen evidence is changed by
this plan.

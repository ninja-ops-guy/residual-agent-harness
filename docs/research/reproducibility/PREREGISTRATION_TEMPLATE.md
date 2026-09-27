# Experiment preregistration

Freeze this document, assign a content digest, and register it as `PREREGISTERED` before inspecting outcomes. If execution or analysis preceded the freeze, use `RETROSPECTIVE` or `EXPLORATORY`; never backdate or relabel it.

## Identity

- Experiment ID:
- Experiment family:
- Registry/schema version:
- Preregistration commit/path:
- Preregistration SHA-256:
- Frozen at (UTC):
- Operator:
- Independent reviewer:
- Literature-review status: `NOT_STARTED | INCOMPLETE | COMPLETE`

## Question and hypothesis

- Research question:
- Primary hypothesis:
- Null/counter-hypothesis:
- Claim boundary and explicit non-claims:

## Design

- Independent variables and arms:
- Dependent variables and units:
- Controls:
- Baseline:
- Inclusion/exclusion rules:
- Sample/replication count:
- Stopping rule:
- Randomization and seed policy:
- Blinding/adjudication:
- Planned statistical analysis:
- Failure classifications fixed before execution:

## Frozen identities

- Code revision:
- Candidate revision/tree/parent:
- Model/provider:
- Model artifact/digest:
- Runtime/container/dependency lock digests:
- Prompt/template/config digests:
- Dataset/corpus/benchmark and split digests:
- Environment/host/topology manifest digest:

## Authority and intervention policy

- Authorized scope:
- Prohibited actions:
- Operator interventions allowed without abort:
- Interventions that require abort/new experiment ID:
- Safety/rollback conditions:
- Credentials/secrets handling:

## Evidence plan

- Planned start/end window:
- Evidence destination:
- Required raw artifacts:
- Timestamp/clock source:
- Evidence manifest procedure:
- Redaction procedure:
- Missing/unverifiable evidence disposition:

## Decision rule

- PASS:
- FAIL:
- BLOCKED/INCONCLUSIVE:
- Replication criterion:
- Conditions requiring a versioned amendment:

## Freeze declaration

I confirm that outcomes were not inspected before this version was frozen. Amendments are append-only and cannot silently change the experiment identity, hypotheses, metrics, thresholds, or stopping rule.

- Operator/date:
- Reviewer/date:

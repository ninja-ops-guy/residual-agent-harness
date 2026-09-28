# RESIDUAL v1 rollback runbook

Planning template only. Preserve evidence; do not improvise destructive repair.

## Triggers

Declare `ROLLBACK` for any verified unauthorized/credential/protected-service
mutation, data loss/corruption, security boundary breach, artifact/config/schema
identity mismatch, failed migration, unavailable critical journey, sustained breach
of an approved error/latency/saturation/queue guardrail, uncontrolled retry or
duplicate receiver effect, failed readiness, or inability to observe a safety-critical
signal. Missing or unverified evidence alone is `EVIDENCE_INCOMPLETE`: freeze traffic
and escalation; if independent evidence proves unsafe state, `ROLLBACK` takes precedence.

## Authority and first actions

1. Any operator may stop rollout and drain/isolate unsafe traffic.
2. Page the Incident Commander (IC), Operations, Application, Data, Security, and
   scribe; record trigger, detection source, UTC time, scope, customer impact, and
   last known good state. Preserve logs, traces, metrics, commands, and decisions.
3. The IC declares `ROLLBACK` and chooses the approved recovery path. The IC must
   authorize traffic shifts and restore/failback; the Data Owner must authorize
   database restore or data repair. Deployment automation has no such authority.

## Choose the path

- **Artifact/config rollback:** allowed only while database/data formats remain
  backward-compatible. Disable new traffic, restore the previous immutable artifact
  and configuration/flags, verify identities, start the prior version, then verify.
- **Forward fix:** not a rollback and not permitted under this release approval.
  It requires a new candidate, qualification, and release approval.
- **Database restore:** required when migration/data mutation is incompatible or
  integrity is lost. Stop all writers, preserve the failed state, select the approved
  recovery point, and obtain IC + Data Owner authorization. Restore to an isolated
  target first, validate checksums/receipt chains/critical reads, account for writes
  after the recovery point, then perform the approved cutover. Never merge divergent
  writes ad hoc.

## Execution checklist

- [ ] Freeze rollout, background jobs, consumers, and writers as the topology requires.
- [ ] Capture deployed digest, config/schema/flag versions, queues/outboxes, database
      position, and protected-service/safety-counter state.
- [ ] Confirm rollback target digest and signatures match the prestate manifest.
- [ ] Confirm backup/recovery point and keys are accessible; record expected RPO/RTO.
- [ ] IC records the selected path and authorizes execution.
- [ ] Execute only the approved immutable procedure; record operator/command/result/time.
- [ ] Prevent incompatible new-version workers from reconnecting.
- [ ] Verify health and dependency-aware readiness before any traffic restoration.
- [ ] Verify schema/data checksums, receipt/evidence chain, durable outbox/journal,
      queue progress, critical read/write journey, authorization, and audit logging.
- [ ] Restore traffic in bounded slices with IC approval and written guardrails.
- [ ] Confirm previous artifact/config/schema identity and sustained stable telemetry.

## If rollback fails

Keep traffic isolated, preserve both failed states, and enter disaster recovery.
Escalate to executive incident authority, Data Owner, and Security; communicate the
impact and next update time. Do not retry destructive steps without a new written
hypothesis, peer review, and IC/Data Owner approval.

## Recovery and closure

The IC keeps the incident open through the observation period. Product and Operations
must reverify critical journeys and customer/data integrity. Record actual RPO/RTO,
lost/delayed work, notifications, timeline, root-cause follow-up, and all evidence
hashes. A rolled-back v1 is not release closure; another production attempt requires
a new RC and the full gates beginning at the appropriate provenance step.

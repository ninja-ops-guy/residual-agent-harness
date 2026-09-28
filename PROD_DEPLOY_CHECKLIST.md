# RESIDUAL v1 production deployment checklist

Planning template only. Every box needs a UTC evidence reference and operator
initials. Checking a box does not replace the human gates in the release plan.

## Identity and authority

- [ ] Approval receipt is valid, unexpired, and bound to release, digest,
      environment, procedure revision, window, and named operators.
- [ ] Candidate commit/tree and signed `v1.0.0-rc.N` resolve to the approved RC.
- [ ] Deployable artifact and SBOM digests match the qualification manifest.
- [ ] Deployment Operator, Incident Commander, approvers, on-call, and scribe are
      present; change freeze and communications channel are active.
- [ ] No unresolved blocking defect, incident, exception expiry, or contradictory
      decision exists. If evidence cannot be verified: `EVIDENCE_INCOMPLETE`.

## Preflight

- [ ] Inventory current artifact/config/schema/feature flags/dependencies and
      capture signed prestate plus dashboard baseline.
- [ ] Configuration compatibility diff passes; secrets references and access are
      tested without exposing values.
- [ ] Migration plan states `migration_required`; rehearsed duration, capacity,
      locks, compatibility, checksum, interruption behavior, and point of no return
      are accepted by Data Owner and Operations.
- [ ] Application-consistent encrypted backup completes; snapshot IDs/hashes/key
      reference/retention are recorded; readability and restore-drill evidence pass.
- [ ] Previous artifact/config and rollback capacity are staged by immutable digest.
- [ ] Health/readiness/synthetic queries, dashboards, alerts, numeric guardrails,
      traffic controls, and evidence capture are working before change.
- [ ] Incident Commander records final human `GO`; otherwise stop with `NO_GO`.

## Deploy

- [ ] Deployment Operator records start time and verifies the exact digest again.
- [ ] Drain or segment traffic according to the approved topology.
- [ ] Apply backward-compatible migration, if any; record logs/checksums/timing.
      At a point of no return, obtain the separately named human gate.
- [ ] Deploy the exact qualified artifact to the approved initial slice.
- [ ] Verify process health, dependency-aware readiness, schema compatibility,
      durable write/read, journal/outbox progress, and zero unexpected mutation.
- [ ] Run synthetic create → execute → persist → reload → receipt lookup and one
      idempotent reconciliation journey using approved non-customer test data.
- [ ] Compare error rate, latency, saturation, restarts, queue/lag, database,
      provider, authorization, safety, and evidence metrics to written thresholds.
- [ ] Incident Commander and Deployment Operator authorize each traffic increase.
- [ ] Complete rollout only while every guardrail remains green; record end time.

## Post-deploy and rollback window

- [ ] Verify artifact/config/schema identities independently from the deploy tool.
- [ ] Product Owner accepts critical user journeys; Operations accepts dashboards,
      alerts, capacity, persistence, and dependency state.
- [ ] Confirm exactly-once/idempotency invariants and no safety-counter increase.
- [ ] Search logs/traces for secrets, new errors, retries, timeouts, corruption,
      authorization denial anomalies, and evidence gaps.
- [ ] Retain previous artifact, configuration, backup, operators, and traffic
      controls through the approved observation window: ______ UTC to ______ UTC.
- [ ] On any trigger, declare `ROLLBACK` and use `ROLLBACK_RUNBOOK.md`.
- [ ] At window end, Operations and Product Owner record acceptance; unresolved or
      unavailable evidence is `EVIDENCE_INCOMPLETE`, not success.

## Close

- [ ] Complete and validate `RELEASE_RECEIPT_SCHEMA.json` instance.
- [ ] Archive approvals, checklist, logs, metrics/traces, qualification, backup,
      migration, configuration, incidents, artifact provenance, and decision ledger.
- [ ] Verify archive manifest/hash and independent copy.
- [ ] Release Manager authorizes closure; Maintainer creates signed `v1.0.0` on
      the same RC commit without rebuild; verify tag signature and record hash.
- [ ] Publish approved changelog/status and record `V1_CLOSED`.

# SPEC-SC-MESH-001 — SCM-00 source and requirements matrix

Status: IMPLEMENTATION CANDIDATE / NO LIVE EXECUTION AUTHORITY  
Discovery base: `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572`  
Preserved R3.4 evidence candidate: `c23460d1cee25b2d2fbc647bb13bb1d6700c68a6`, tree `f4d144a28166f03aecefa9e27ebaca7b4c621ebe`.

## Precedence

1. Existing Station state transitions, budget authority, receipts, and verification remain authoritative.
2. SPEC-SC-MESH-001 adds worker identity, message durability, synchronization and adapter boundaries; it does not create a peer authority plane.
3. R3.4 continuity semantics are reused for structured provider failure classification, whole-attempt fallback, route filtering, durable outbox recovery, and communications idempotency.
4. Existing migration-control-plane or adapter specifications keep authority over their own domains. Mesh adapters expose capabilities to Station; they do not bypass Station admission.
5. Any conflict resolves fail-closed and is recorded before widening behavior.

## Discovery findings

- Current main has one shared remote-worker token and project IDs supplied by the caller. This is insufficient for SCM-01/SCM-I03 project-scoped worker identity.
- Current main has lease-bearing claims and stale-result rejection, but no durable monotonic fencing token. SCM-06 therefore requires an additive fence.
- Current main heartbeats extend task leases. Mesh heartbeats must be presence-only and cannot self-renew authority.
- Current main already owns dependency checks, verification, review, integration, artifact hashing, observation chains and run budget control. These are reused.
- Preserved R3.4 adds route filtering, provider-attempt admission, durable comms/outbox and structured fallback tests. Those behaviors are ported as compatibility contracts, not by mutating the frozen candidate.
- R3.4 Shared Comms used the shared worker credential; this candidate introduces per-enrollment tokens and project/topic scope before extending message use.
- OpenClaw-specific execution belongs in an adapter/sidecar boundary. Station core accepts only declared capabilities and independently verified evidence.

## Requirement matrix

| Requirement | Existing base | Candidate work | Status |
|---|---|---|---|
| SCM-I01 Station authority | Station claim/transition, BudgetAdmission, receipts | Preserve; mesh never exposes integrate/review authority | implemented foundation |
| SCM-I02 messages are data | R3.4 task contract preservation test | strict MeshEnvelope; authority fields rejected outside task-scoped kinds | implemented |
| SCM-I03 scoped authenticated mutation | shared worker token only | per-enrollment token hashes; project/generation/fence checks | W2/W3 implemented, W4 extending |
| SCM-I04 at-least-once + dedup | R3.4 idempotent comms/outbox | namespaced sender+project+kind idempotency and digest conflict | W3 implemented |
| SCM-I05 disconnected authority | leases exist | READY/SYNCING/DISCONNECTED/REVOKED lifecycle; reconnect through SYNCING | W2 implemented |
| SCM-I06 fallback cannot widen | R3.4 ContinuityProvider | adapter capability/policy binding; no route widening in envelope | W5 pending |
| SCM-I07 completion needs verification | Station review/integration receipts | mesh result kind is evidence only; no acceptance endpoint | implemented foundation |
| SCM-I08 pause/stop durable | project pause exists | generation/revocation/containment orchestration | W4/W5 pending |
| SCM-I09 credentials local/redacted | settings hide provider keys | enrollment tokens stored only as SHA-256; plaintext returned once | W2 implemented |
| SCM-I10 frozen evidence immutable | artifact digests | new candidate/qualification bundle only | process invariant |
| SCM-01 enrollment | absent | owner-provisioned scoped enrollment, expiry/revocation, capability validation | W2 implemented |
| SCM-02 adapter lifecycle | generic model/provider adapters | semantic ClawAdapter protocol and compatibility profile | W2 implemented |
| SCM-03 envelope | R3.4 comms payload | versioned bounded envelope with generation/correlation/lease binding | W3 implemented |
| SCM-04 persistence/replay | event chain + R3.4 outbox | durable mesh message admission, conflict detection, inbox cursor contract | W3 implemented |
| SCM-05 snapshot/replay | project events/report cursor | consistent mesh snapshot API and generation field | W3 scaffold; gap/compaction W4 |
| SCM-06 lease fencing/routing | lease + dependency checks | additive fencing token and capability-aware mesh claim | W4 next |
| SCM-07 continuity | R3.4 tested | port after W4 authority binding | W5 pending |
| SCM-08 stop containment | pause only | adapter cancel + host containment profile | W5 pending |
| SCM-09 evidence | Station artifacts/receipts | bind worker/generation/lease/fence/provider attempts | W5 pending |
| SCM-10 status | diagnostics/observations | redacted mesh enrollment/message/dead-letter status | W3 implemented |

## Candidate limits frozen for W2/W3

These limits are protocol constants and require a new protocol revision to widen:

- envelope major version: 1
- inline payload: 32 KiB canonical UTF-8
- envelope total: 48 KiB canonical UTF-8
- idempotency key: 128 characters
- message ID/correlation/causation IDs: 128 characters
- default TTL: 900 seconds; maximum TTL: 3600 seconds
- per-read page: 200 messages
- replay age: 24 hours
- enrollment capability count: 64
- topic count: 64
- capability/topic token length: 96 characters

## Non-claims

This branch does not claim MESH_QUALIFIED, DEPLOYMENT_QUALIFIED, Windows process containment, gateway transport qualification, or live multi-host completion. W2/W3 are code-level foundations awaiting W4–W7 qualification.

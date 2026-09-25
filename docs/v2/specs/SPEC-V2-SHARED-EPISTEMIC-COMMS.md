# SPEC-V2-SHARED-EPISTEMIC-COMMS — Shared Epistemic Communications for Local and Multi-Tenant Swarms

**Version:** 0.1.0-draft  
**Date:** 2026-09-24  
**Target:** RESIDUAL v2  
**Status:** DRAFT / RESEARCH-DRIVEN SPECIFICATION; NO PRODUCTION CLAIM  
**Motivating observation:** AX-21-OBS-001  
**Related:** `harness_specs/MESH_SPECS.md`, Evidence Bus/Receipts, Station authority, Epistemic Memory, scheduler/budget controls

## 1. Objective

RESIDUAL v2 SHALL provide a shared communications/control substrate that lets local, multi-host, heterogeneous-provider, and multi-tenant agentic swarms exchange durable epistemic state without making model context, chat history, or any single worker authoritative.

The system SHALL distinguish communication from knowledge, knowledge from evidence, and evidence from authority.

## 2. Core invariant

**Activity is not progress.**

A worker issuing new tokens, messages, or tool calls MUST NOT be treated as making progress unless the action creates, invalidates, challenges, narrows, or materially strengthens an epistemic state relevant to its assigned objective.

## 3. Required data model

A shared epistemic claim MUST be representable as a versioned envelope containing at minimum:

- claim/proposition identifier and canonical semantic key;
- tenant and namespace;
- subject/resource scope;
- asserted state/value;
- evidence references and receipt hashes;
- observer/producer identity;
- verifier identity/revision when applicable;
- creation and observation timestamps;
- freshness/expiry/revalidation policy;
- authority class;
- confidence only where meaningful and explicitly non-authoritative;
- contradiction/challenge links;
- disclosure classification;
- causal parents;
- supersession/revocation state.

Chat text alone MUST NOT satisfy this contract.

## 4. Authority boundaries

**SCV2-R1.** Station remains authoritative for admission, policy, lifecycle, and accepted state.

**SCV2-R2.** Workers and models MAY propose claims but MUST NOT self-promote a proposal into verified/authoritative state.

**SCV2-R3.** Existing receipts/evidence MUST be reusable without replaying the producing tool when freshness and scope remain valid.

**SCV2-R4.** Signed origin proves attribution, not correctness.

**SCV2-R5.** A shared claim MUST preserve its evidence provenance across hosts and providers.

## 5. Semantic deduplication and progress control

**SCV2-R6.** Before executing a tool action, a worker SHOULD query shared epistemic state for an equivalent proposition/resource/scope.

**SCV2-R7.** The control plane MUST detect bounded sequences of semantically equivalent actions that do not materially change epistemic state.

**SCV2-R8.** Detection MUST NOT rely only on byte-identical commands. `ls path`, `test -f path`, and equivalent existence checks MAY map to one semantic intent.

**SCV2-R9.** When fresh sufficient evidence already resolves the proposition, Station MAY return the existing evidence instead of admitting the redundant action.

**SCV2-R10.** When repetition crosses a configured bound without progress, the run MUST transition to `OBSERVER_STALLED` or an equivalent explicit state; it MUST NOT silently count repetition as success.

**SCV2-R11.** A stalled observer MAY be routed to deterministic fallback, an independent observer, or HITL according to policy and budget.

## 6. Observer/target separation

**SCV2-R12.** Health and monitoring protocols MUST represent target state independently from observer state.

**SCV2-R13.** Failure to obtain an observation MUST NOT be rewritten as target failure.

**SCV2-R14.** Deterministic probes SHOULD be preferred for basic liveness/readiness facts. Models SHOULD diagnose anomalous receipts rather than sit in the mandatory liveness path where a deterministic probe suffices.

**SCV2-R15.** Monitoring receipts MUST record command/probe identity, exit state, bounded duration/timeout, evidence digest, host, observer, and target.

## 7. Multi-tenant isolation

**SCV2-R16.** Every claim, message, evidence reference, subscription, and derived index MUST carry an enforceable tenant/namespace boundary.

**SCV2-R17.** Cross-tenant sharing MUST be explicit, policy-authorized, auditable, and least-disclosure.

**SCV2-R18.** Semantic deduplication MUST NOT leak the existence, content, timing, or identifiers of another tenant's private claims.

**SCV2-R19.** Global infrastructure facts MAY be shared only through an explicitly designated global/public namespace with defined authority.

**SCV2-R20.** Tenant-scoped encryption/keying and authenticated membership MUST prevent a worker from acquiring visibility by merely minting an identity.

## 8. Local and federated operation

**SCV2-R21.** The same logical protocol MUST support single-host local swarms and multi-host swarms.

**SCV2-R22.** Network partition MUST degrade to explicitly scoped local knowledge; partitioned state MUST NOT be represented as globally current.

**SCV2-R23.** Reconciliation MUST preserve concurrent claims and contradictions until policy/verifier resolution. Longest-chain/proof-of-work conflict selection MUST NOT be used as a correctness rule.

**SCV2-R24.** Rejoin MUST be idempotent and duplicate-safe.

## 9. Budget integration

**SCV2-R25.** Redundant-action suppression SHOULD expose avoided tool/inference cost as a research metric, not as an unverifiable savings claim.

**SCV2-R26.** Budget exhaustion and unknown usage MUST remain fail-closed with respect to new authority-bearing actions.

**SCV2-R27.** Existing valid evidence reuse MUST be distinguishable from new inference/tool expenditure.

## 10. Required receipts/events

At minimum:

- `claim.proposed`
- `claim.verified`
- `claim.challenged`
- `claim.superseded`
- `claim.expired`
- `evidence.reused`
- `action.redundant_suppressed`
- `observer.stalled`
- `observer.fallback_started`
- `observer.fallback_resolved`
- `tenant.cross_scope_denied`
- `partition.local_scope_entered`
- `partition.reconciled`

## 11. AX-21 experimental design

Compare at least three conditions:

A. isolated worker/model context with no shared state;  
B. shared message/chat history only;  
C. shared epistemic state with semantic deduplication and durable evidence.

Hold model/provider/version, task corpus, tool environment, prompting policy, inference settings, and grader constant unless the varied factor is preregistered.

Primary outcomes:

- redundant semantic tool actions per resolved proposition;
- time to durable resolution;
- observer-livelock incidence;
- tokens/inference calls/tool calls;
- incorrect target-failure attribution;
- evidence reuse rate;
- contradiction detection latency;
- recovery success after injected observer faults.

Multi-tenant experiments MUST additionally test cross-tenant existence leakage, unauthorized evidence reuse, namespace confusion, stale-global-state use, and malicious identity enrollment.

## 12. Acceptance tests

1. Fresh shared existence evidence suppresses an equivalent repeated existence probe.
2. Expired evidence permits revalidation rather than indefinite suppression.
3. Contradictory evidence forces challenge/reconciliation rather than arbitrary overwrite.
4. Repeated semantically equivalent commands trigger `observer.stalled` within the configured bound.
5. A failed observer with a healthy deterministic target probe produces observer-failure semantics, not target-failure semantics.
6. A truly failed target is not masked by observer fallback.
7. Tenant B cannot infer Tenant A claim existence through dedupe timing/result differences.
8. Cross-tenant evidence use fails closed without explicit grant.
9. Partition/rejoin preserves provenance and duplicate safety.
10. Independent observer can challenge stale evidence without deleting history.
11. Restart rebuilds shared epistemic projections from authoritative durable records.
12. Mutation tests prove each gate fails when its enforcement is removed.

## 13. Non-claims

This specification does not claim that semantic equivalence can be perfectly decided, that distributed consensus is solved by the communications layer, that signed messages are true, that a mesh is Byzantine-fault-tolerant, or that AX-21-OBS-001 has an established root cause.

## 14. v2 implementation order

1. versioned ClaimEnvelope + tenant namespace;
2. durable claim/evidence projection over authoritative records;
3. semantic-key lookup and conservative dedupe;
4. observer/target state split;
5. deterministic fallback protocol;
6. stall detector and receipts;
7. authenticated multi-host synchronization;
8. tenant isolation/adversarial qualification;
9. AX-21 controlled ablation;
10. only after qualification, integrate admission/budget optimizations.

## 15. Freeze gate

This spec MAY advance from DRAFT only when its threat model, tenant isolation model, semantic-deduplication false-positive policy, partition semantics, and AX-21 preregistration are independently reviewed. Implementation presence alone MUST NOT satisfy the gate.

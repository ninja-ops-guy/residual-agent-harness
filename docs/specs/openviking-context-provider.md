# OpenViking Context Provider Integration Specification

Status: **PROPOSED / DEFERRED IMPLEMENTATION**

Purpose: define a safe, optional OpenViking integration without placing OpenViking inside RESIDUAL's trusted control plane or current production-readiness critical path.

## 1. Goals and non-goals

RESIDUAL SHALL support a replaceable `ContextProvider` abstraction for hierarchical retrieval, progressive context loading, durable task experience, and observable retrieval traces. Context may inform execution; it MUST NOT establish authority or truth.

This specification does not authorize runtime implementation, copying OpenViking code into RESIDUAL, replacing Evidence Fabric, weakening WorkerContract boundaries, or changing protected trust-boundary semantics. OpenViking MUST NOT control scheduling, budgets, brakes, quarantine, verification, acceptance, integration, or release decisions.

## 2. Architecture and authority

```text
Requirement Compiler -> Orchestrator -> Context Broker
                                      /              \
                                Native Context    ContextProvider
                                                       |
                                               OpenVikingAdapter
                                                       |
                                               OpenViking Server
                                                       |
                                           Resource/Memory/Skill
                                                       |
                                                   L0/L1/L2
                                                       |
                                                ContextPackage
                                                       |
                                                WorkerContract
                                                       |
                                                    Worker
                                                       |
                                                Evidence Fabric
```

OpenViking SHALL remain outside the trusted control plane and SHOULD run as an independently deployed service behind a narrow HTTP adapter.

Authority ordering is fixed:

1. explicit requirements/operator intent;
2. protected invariants and policy;
3. WorkerContract authority/scope;
4. current repository/runtime state;
5. current execution evidence;
6. verifier results and StationReceipt;
7. historical/provider context.

Lower levels MUST NOT override higher levels.

## 3. Provider contract

A provider-neutral contract SHALL exist before OpenViking-specific behavior. Conceptual operations are `health`, `search`, `abstract`, `overview`, `read`, `trace`, `propose_memory`, and `commit_memory`.

Provider failure SHALL be bounded and observable. Missions not requiring provider context MUST remain executable during provider outage. The provider MUST NOT be called directly by workers by default; the Context Broker mediates retrieval and creates immutable context artifacts.

## 4. OpenViking capability mapping

The adapter SHALL target documented public capabilities rather than OpenViking internals.

| OpenViking capability | RESIDUAL use | Boundary |
| --- | --- | --- |
| `viking://` URI | provider reference | never authority |
| search/find | candidate discovery | Context Broker only |
| L0 abstract | cheap relevance filtering | budgeted |
| L1 overview | navigation/selection | budgeted |
| L2 detail | final content | explicit promotion |
| retrieval trace | attribution | evidence input |
| session usage | telemetry | informational |
| session commit/extract | memory proposal | certification required |
| cases/trajectories/experiences | task history | outcome preserved |
| HTTP server | external integration | preferred boundary |

RESIDUAL MUST NOT depend on undocumented OpenViking behavior for correctness.

## 5. Progressive loading and deterministic budgets

RESIDUAL SHALL map progressive context to explicit budgets: L0 for discovery/filtering, L1 for navigation/reranking/selection, and L2 only after selection and budget checks.

The Context Broker SHALL own final injection policy even if OpenViking performs retrieval, reranking, or context assembly. It SHOULD bound total tokens/bytes, candidate count, L1/L2 promotions, per-source contribution, context-type contribution, provider calls, and retrieval wall-clock time.

Every promotion SHALL record source identity, reason, retrieval identity, and estimated/actual cost. Equal-ranked candidates at a budget boundary SHALL use a documented deterministic tie-breaker.

## 6. Namespace and identity binding

A provider URI alone does not establish RESIDUAL identity or authorization. Every request SHOULD bind `mission_id`, `worker_id`, `worker_contract_id`, repository identity/revision, operator/tenant scope, allowed context scopes, budget, and provider-policy version.

Returned references SHALL be rebound to those identities before entering a ContextPackage. The adapter MUST reject scope traversal, ambiguous aliases, namespace confusion, and results whose effective authorization cannot be established.

## 7. ContextPackage

Workers SHALL receive a bounded immutable `ContextPackage` rather than unrestricted provider access.

A versioned package SHOULD include package/mission/contract identity, repository revision, provider and retrieval IDs, budget ceilings/usage, and entries containing provider reference, L0/L1/L2 level, exact content digest, source revision, trust classification, historical outcome, retrieval reason, and token/byte cost.

The package SHALL become immutable at dispatch. Additional context requires a new package or explicit append artifact with a new digest. The package digest SHALL be recorded in execution evidence.

```json
{
  "schema_version": "1",
  "package_id": "ctxpkg-...",
  "mission_id": "...",
  "worker_contract_id": "...",
  "repository_revision": "...",
  "provider": "openviking",
  "retrieval_id": "...",
  "budget": {"max_tokens": 0, "used_tokens": 0, "max_l2_items": 0},
  "entries": [{
    "provider_ref": "viking://...",
    "level": "L0|L1|L2",
    "content_digest": "sha256:...",
    "source_revision": "...",
    "trust": "UNTRUSTED|HISTORICAL|VERIFIED",
    "outcome": "UNKNOWN|ACCEPTED|REJECTED|FAILED",
    "reason": "...",
    "cost": {"tokens": 0, "bytes": 0}
  }]
}
```

## 8. Memory certification and lifecycle

Provider-extracted memory MUST NOT automatically become RESIDUAL truth. Candidate classifications are `OBSERVATION`, `EXPERIENCE`, `HEURISTIC`, `VERIFIED_FACT`, and `INVARIANT`. Provider-generated memory defaults to non-authoritative classification. Only RESIDUAL-controlled policy may promote it; model extraction alone MUST NEVER create an invariant.

Candidates SHOULD bind content digest, originating mission/worker, provider extraction metadata, repository revisions, supporting Evidence Fabric IDs, verifier/receipt references, classification, timestamps, expiration/invalidation rules, supersession relationships, and outcome.

Certification is revocable. Repository changes, failed requalification, contradictory/revoked evidence, or changed invariants MAY invalidate memory. Invalidated memory remains auditable but MUST NOT be returned as current verified truth. Prefer compact references to authoritative evidence over duplicating evidence bodies.

## 9. Trajectory memory and swarm isolation

RESIDUAL MAY persist accepted repairs, rejected trajectories, verifier failures, regression causes, successful tool sequences, incident resolutions, and StationReceipts. Accepted, rejected, and failed outcomes MUST remain distinguishable at storage and retrieval. Historical failure MUST NOT be silently transformed into recommended truth.

OpenViking configuration MUST NOT grant unrestricted shared memory. Retrieval SHALL respect WorkerContract, mission/project isolation, provider ACLs, and RESIDUAL policy. Cross-worker learning occurs through certified artifacts, not implicit mutable shared state.

## 10. Evidence and replay

For each injected item, Evidence Fabric SHOULD reconstruct:

`query -> provider trace -> candidate -> promotion -> exact bytes/digest -> worker input -> execution -> verifier result`

Frozen replay SHALL operate without OpenViking: no live retrieval or memory mutation, package digest must validate, worker-visible context must match the recorded package, and evidence must identify replay mode.

Command Station SHOULD later provide a Context Inspector explaining why each item was selected, its source/revision/trust/outcome, level transitions, cost, package digest, and supporting evidence.

## 11. Failure semantics and threat model

The integration SHALL fail closed for authority and fail soft for optional context. Outage, malformed response, stale reference, budget overflow, ACL denial, timeout, or memory-write failure MUST NOT weaken RESIDUAL controls. Native/no-provider fallback SHALL be explicit in evidence.

Executable negative-path tests SHALL cover prompt injection, memory poisoning, cross-mission leakage, cross-worker leakage, stale revision confusion, outcome laundering, provider equivocation, budget amplification, availability coupling, credential/secret ingestion, namespace confusion, and memory self-certification.

Retrieved content is data. It cannot grant tools, expand scope, modify policy, certify memory, or override WorkerContract/invariants.

## 12. Security, privacy, and licensing

Secrets MUST NOT be written to provider context by default. Credentials use normal RESIDUAL secret/config mechanisms. Reads/writes SHALL be scope checked and auditable.

OpenViking's main project currently uses AGPLv3. Distribution/deployment implications SHALL be reviewed before implementation. The initial architecture SHOULD favor an independently deployed OpenViking service behind a provider-neutral adapter rather than copied implementation code. This is architectural guidance, not legal advice.

# Implementation-ready PR specifications

The following PRs are **future implementation units**. They are specified now but SHALL be implemented later from then-current `main`. Each PR MUST be independently reviewable and MUST NOT rely on a later PR to preserve safety.

## OV1 — Context Provider Contract

### Objective

Create the provider-neutral RESIDUAL boundary without connecting OpenViking or changing provider-off runtime behavior.

### Required interfaces

```python
class ContextProvider(Protocol):
    async def health(self) -> ProviderHealth: ...
    async def search(self, request: ContextSearchRequest) -> ContextSearchResult: ...
    async def abstract(self, ref: ContextRef) -> ContextItem: ...
    async def overview(self, ref: ContextRef) -> ContextItem: ...
    async def read(self, ref: ContextRef) -> ContextItem: ...
    async def trace(self, retrieval_id: str) -> RetrievalTrace: ...
    async def propose_memory(self, candidate: MemoryCandidate) -> MemoryProposalResult: ...
    async def commit_memory(self, certified: CertifiedMemory) -> MemoryCommitResult: ...
```

Exact language/module placement MAY follow current RESIDUAL conventions, but semantics are normative.

### Required schemas

`ProviderHealth`, `ContextScope`, `ContextBudget`, `ContextSearchRequest`, `ContextRef`, `ContextItem`, `ContextSearchResult`, `RetrievalTrace`, `ContextPackage`, `ContextPackageEntry`, `MemoryCandidate`, `CertifiedMemory`, and typed provider errors.

All externally persisted schemas SHALL carry `schema_version`.

### Fake provider

OV1 SHALL include a deterministic fake provider capable of scripted hits, delays, malformed responses, changed content, scope violations, and failures. Qualification tests MUST NOT require OpenViking.

### Suggested tests

- `test_context_provider_off_is_noop`
- `test_context_package_digest_is_stable`
- `test_context_package_immutable_after_dispatch`
- `test_context_scope_rejects_cross_worker_ref`
- `test_context_budget_rejects_overflow`
- `test_provider_error_is_typed_and_bounded`
- `test_equal_rank_uses_deterministic_tiebreak`
- `test_context_item_requires_provenance`

### Merge gate

Provider-off equivalence, protected trust-boundary suite unchanged/green, deterministic schema serialization, fake-provider negative paths green. **No OpenViking dependency is permitted in OV1.**

### Depends on

None.

---

## OV2 — OpenViking Adapter

### Objective

Implement an optional external OpenViking provider using documented HTTP/API semantics only.

### Required configuration

Configuration SHOULD include `enabled`, endpoint/base URL, credential reference, connect/read timeout, maximum request count, allowed URI roots, user/tenant mapping, and fallback policy. Secrets MUST be referenced rather than serialized into evidence.

### Adapter mapping

- provider health -> OpenViking service health/initialization probe;
- `search` -> `find` or `search(mode=list)` according to explicit RESIDUAL request semantics;
- `abstract` -> L0 abstract operation;
- `overview` -> L1 overview operation;
- `read` -> L2/full content operation;
- `trace` -> documented retrieval-observability surface when available;
- memory proposal -> session extraction/commit output imported only as an untrusted proposal.

OpenViking session context assembly MAY be measured experimentally but MUST NOT bypass RESIDUAL final budget and provenance checks.

### URI rules

The adapter SHALL canonicalize `viking://` references, bind them to RESIDUAL scope, reject unauthorized roots/aliases, and never infer authorization solely from provider success.

### Suggested tests

- `test_openviking_disabled_makes_no_network_call`
- `test_openviking_health_timeout_is_bounded`
- `test_openviking_uri_is_rebound_to_residual_scope`
- `test_openviking_alias_cannot_escape_scope`
- `test_openviking_malformed_result_rejected`
- `test_openviking_credential_never_enters_evidence`
- `test_openviking_outage_falls_back_when_optional`
- `test_openviking_required_context_failure_is_explicit`

### Merge gate

OV1 green; deterministic fixture service or recorded contract fixture green; provider-off equivalence green; outage/malformed/timeout/ACL suites green; license/deployment review recorded before release enablement.

### Depends on

OV1.

---

## OV3 — Progressive Context Loading

### Objective

Implement RESIDUAL-owned L0 -> L1 -> L2 promotion with deterministic budgets and complete promotion evidence.

### Promotion state machine

```text
DISCOVERED(L0)
  -> REJECTED
  -> PROMOTED_L1
       -> REJECTED
       -> PROMOTED_L2
            -> INJECTED
            -> REJECTED
```

Every transition SHALL have a reason code. No L2 read may occur without a recorded L1-or-policy promotion decision except for an explicitly specified direct-L2 resource type.

### Budget contract

Budget SHALL bound at least tokens/bytes, candidate count, L1 count, L2 count, per-source contribution, provider requests, and deadline. Exhaustion is a normal deterministic terminal condition, not an exception that triggers unbounded retry.

Tie-break order SHOULD be explicit, e.g. effective score descending, authority/trust policy, canonical provider reference, then stable digest/identity.

### Suggested tests

- `test_l0_rejection_prevents_l1_and_l2_reads`
- `test_l1_rejection_prevents_l2_read`
- `test_l2_budget_is_hard_ceiling`
- `test_provider_order_does_not_change_equal_rank_selection`
- `test_promotion_reason_recorded_for_every_transition`
- `test_stale_revision_rejected_or_marked_by_policy`
- `test_provider_equivocation_detected_by_digest`
- `test_frozen_package_replay_never_contacts_provider`

### Merge gate

OV1+OV2 green; deterministic corpus produces identical selected package across repeated runs; replay reproduces worker-visible bytes; no protected authority regression.

### Depends on

OV1, OV2.

---

## OV4 — Evidence-Aware Memory Gate

### Objective

Create the only supported path from provider-extracted memory into durable RESIDUAL-qualified memory.

### Memory state machine

```text
PROPOSED -> REJECTED
         -> OBSERVATION
         -> EXPERIENCE
         -> HEURISTIC
         -> VERIFIED_FACT

INVARIANT is not a provider promotion target.
It requires an explicit RESIDUAL policy/specification path outside model extraction.

Any certified state -> INVALIDATED -> SUPERSEDED/ARCHIVED
```

### Certification rules

A promotion decision SHALL bind evidence IDs, repository revisions, verifier/receipt status, policy version, certifier identity/type, timestamps, and invalidation triggers. Provider confidence is metadata, never authority.

Memory writes MUST be post-acceptance side effects unless a future independently reviewed specification says otherwise; failure to write memory MUST NOT alter mission acceptance.

### Suggested tests

- `test_provider_memory_defaults_non_authoritative`
- `test_memory_cannot_self_certify`
- `test_model_extraction_cannot_create_invariant`
- `test_verified_fact_requires_qualifying_evidence`
- `test_failed_requalification_invalidates_memory`
- `test_repository_revision_change_triggers_staleness`
- `test_memory_write_failure_does_not_change_receipt`
- `test_secret_like_content_rejected_from_memory`

### Merge gate

Memory poisoning suite green; invalidation/revocation replayable; no provider path can emit authoritative invariant; acceptance outcome independent from memory persistence.

### Depends on

OV1; OV2 for live OpenViking qualification. Can be developed against fake provider before OV2 merges.

---

## OV5 — Trajectory Memory

### Objective

Persist and retrieve execution experience without laundering failures into success or turning historical correlation into authority.

### Trajectory schema

Each stored trajectory SHOULD include mission/worker IDs, repository revision, problem/failure signature, bounded action/tool summary, evidence/receipt references, terminal outcome (`ACCEPTED`, `REJECTED`, `FAILED`, `ABORTED`), verifier summary, regression status, timestamps, and supersession/invalidation metadata.

Raw secrets and unnecessarily large transcripts SHOULD NOT be copied into trajectory memory.

### Retrieval policy

Results SHALL preserve outcome. Failed/rejected trajectories may be retrieved as warnings or counterexamples but MUST NOT be rendered as accepted recommendations. Ranking MAY consider historical success but cannot replace current verification.

### Suggested tests

- `test_rejected_trajectory_remains_rejected_after_roundtrip`
- `test_failed_trajectory
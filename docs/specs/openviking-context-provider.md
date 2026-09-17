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
| session commit | memory proposal | certification required |
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

Example shape:

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

## 9. Trajectory memory

RESIDUAL MAY persist accepted repairs, rejected trajectories, verifier failures, regression causes, successful tool sequences, incident resolutions, and StationReceipts. Accepted, rejected, and failed outcomes MUST remain distinguishable at storage and retrieval. Historical failure MUST NOT be silently transformed into recommended truth.

## 10. Swarm isolation

OpenViking configuration MUST NOT grant unrestricted shared memory. Retrieval SHALL respect WorkerContract, mission/project isolation, provider ACLs, and RESIDUAL policy. Cross-worker learning occurs through certified artifacts, not implicit mutable shared state.

## 11. Evidence and replay

For each injected item, Evidence Fabric SHOULD reconstruct:

`query -> provider trace -> candidate -> promotion -> exact bytes/digest -> worker input -> execution -> verifier result`

Evidence SHOULD include query/intent identity, provider, traversal trace, selected/rejected references where practical, L0->L1->L2 decisions, context cost, provider failures/fallbacks, and memory writes/promotions.

Frozen replay SHALL operate without OpenViking: no live retrieval or memory mutation, package digest must validate, worker-visible context must match the recorded package, and evidence must identify replay mode. This separates reproducible qualification from live retrieval quality.

Command Station SHOULD later provide a Context Inspector explaining why each item was selected, its source/revision/trust/outcome, level transitions, cost, package digest, and supporting evidence.

## 12. Failure semantics

The integration SHALL fail closed for authority and fail soft for optional context. Outage, malformed response, stale reference, budget overflow, ACL denial, timeout, or memory-write failure MUST NOT weaken RESIDUAL controls. Native/no-provider fallback SHALL be explicit in evidence.

## 13. Threat model

Executable negative-path tests SHALL cover at least:

1. prompt injection in retrieved content attempting to change authority;
2. memory poisoning from malicious/erroneous execution content;
3. cross-mission leakage;
4. cross-worker leakage;
5. stale revision presented as current state;
6. outcome laundering of rejected/failed trajectories;
7. provider equivocation where a reference changes content;
8. budget amplification via excessive queries/L2 reads;
9. availability coupling to optional context;
10. credential/secret ingestion;
11. namespace/alias confusion;
12. provider memory attempting self-certification.

Retrieved content is data. It cannot grant tools, expand scope, modify policy, certify memory, or override WorkerContract/invariants.

## 14. Security, privacy, and licensing

Secrets MUST NOT be written to provider context by default. Credentials use normal RESIDUAL secret/config mechanisms. Reads/writes SHALL be scope checked and auditable.

OpenViking's main project currently uses AGPLv3. Distribution/deployment implications SHALL be reviewed before implementation. The initial architecture SHOULD therefore favor an independently deployed OpenViking service behind a provider-neutral adapter rather than copied implementation code. This requirement is architectural guidance, not legal advice.

## 15. Proposed implementation sequence

- **OV1 — Context Provider Contract:** interfaces, fake provider, ContextPackage schema, deterministic budgets, failure semantics, provenance.
- **OV2 — OpenViking Adapter:** optional HTTP integration, health, configuration, namespace mapping, authentication, timeout/fallback.
- **OV3 — Progressive Loading:** bounded L0/L1/L2 selection, promotion evidence, cost accounting, deterministic tie-breaks.
- **OV4 — Evidence-Aware Memory Gate:** candidate schema, classifications, evidence binding, invalidation/expiry, promotion policy.
- **OV5 — Trajectory Memory:** accepted/rejected/failed execution experience with outcome-safe retrieval.
- **OV6 — Swarm Context Sharing:** scoped certified context exchange preserving WorkerContract isolation.
- **OV7 — Context Inspector:** Command Station provenance, traces, transitions, cost, memory state, replay/evidence links.

Each implementation PR SHALL begin from then-current `main`, remain independently reviewable, and preserve the protected trust boundary.

## 16. Deterministic qualification fixture

OV2/OV3 SHOULD add a small fixture corpus containing architecture docs, revision-distinct similar files, one accepted repair, one rejected repair, a malicious prompt-injection document, stale memory, a secret-like value that ingestion policy must exclude, and cross-worker/cross-mission resources.

Qualification SHALL prove correct L0/L1/L2 promotion, revision binding, outcome preservation, secret exclusion, scope isolation, timeout fallback, deterministic budget behavior, and replay without a live provider.

## 17. Acceptance tests

Implementation SHALL eventually prove:

1. provider-off behavior remains equivalent to current RESIDUAL behavior;
2. outage cannot bypass or weaken control-plane decisions;
3. provider context cannot override invariants or WorkerContract restrictions;
4. rejected L0/L1 candidates never trigger L2 reads;
5. budget exhaustion deterministically stops additional loading;
6. every injected item has provenance, retrieval identity, revision, and digest;
7. prompt injection cannot grant authority/tools or self-certify memory;
8. unverified memory cannot become VERIFIED_FACT/INVARIANT without RESIDUAL certification;
9. rejected/failed trajectories retain outcome labels;
10. cross-worker/cross-mission retrieval is denied outside scope;
11. timeout produces bounded fallback plus evidence;
12. memory-write failure cannot alter mission acceptance;
13. frozen ContextPackage replay reproduces worker-visible context without OpenViking;
14. changed provider content is detected by digest/version evidence;
15. stale revision context is marked stale or rejected according to policy;
16. secret-like fixture content is excluded from durable provider memory;
17. Context Inspector explains the complete selection/provenance chain for a qualified demonstration.

## 18. Qualification gates and exit criteria

No implementation enters the release path until current production-readiness gates remain green, protected trust-boundary tests pass, provider-off equivalence is demonstrated, provider-failure and context-authority negative suites pass, provenance/replay tests pass, and licensing review is recorded before shipping OpenViking-backed functionality.

The integration is qualified only when OpenViking is optional/replaceable, outside the authority chain, bounded and replayable, memory is evidence-aware and revocable, swarm isolation holds, provider outages cannot break optional-context missions, Context Inspector exposes the retrieval/evidence chain, and all relevant regression/trust-boundary/qualification suites pass.

## 19. Deferred implementation rule

This PR is specification-only. It SHALL NOT introduce an OpenViking runtime dependency or change production behavior. Implementation begins only after active production-readiness/convergence work permits it, through the independently qualified OV1-OV7 sequence above.

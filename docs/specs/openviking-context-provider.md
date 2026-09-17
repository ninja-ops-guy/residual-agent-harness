# OpenViking Context Provider Integration Specification

Status: PROPOSED / DEFERRED IMPLEMENTATION

Purpose: Define a safe, optional integration between RESIDUAL and OpenViking without making OpenViking part of RESIDUAL's trusted control plane or current production-readiness critical path.

## 1. Goals

RESIDUAL SHALL support a replaceable Context Provider abstraction capable of using OpenViking for hierarchical retrieval, progressive context loading, durable task experience, and observable retrieval traces.

The integration SHALL preserve RESIDUAL authority boundaries. Context may inform execution; it MUST NOT establish authority or truth.

## 2. Non-goals

This specification does not authorize implementation, merge of OpenViking code into RESIDUAL, replacement of Evidence Fabric, weakening of WorkerContract boundaries, or changes to protected trust-boundary semantics.

OpenViking MUST NOT control scheduling, budgets, brakes, quarantine, verification, acceptance, integration, or release decisions.

## 3. Architecture

    Requirement Compiler
             |
        Orchestrator
             |
       Context Broker
        /          \
    Native       ContextProvider
    Context           |
                 OpenVikingAdapter
                      |
               OpenViking Server
                      |
          Memory / Resources / Skills
                      |
                  L0 / L1 / L2
                      |
               Context Package
                      |
                WorkerContract
                      |
                    Worker
                      |
                Evidence Fabric

OpenViking SHALL remain outside the trusted control plane and SHOULD run as an external service accessed through a narrow adapter/API boundary.

## 4. Authority ordering

RESIDUAL SHALL preserve this ordering:

1. Requirements and explicit operator intent
2. Protected invariants and policy
3. WorkerContract authority and scope
4. Current repository/runtime state
5. Current execution evidence
6. Verifier results and StationReceipt
7. Historical/provider context

Provider context MUST NOT override any higher authority.

## 5. ContextProvider contract

A provider-neutral interface SHALL be defined before OpenViking-specific behavior is introduced.

Conceptual operations:

- health()
- search(query, scope, budget)
- abstract(ref)
- overview(ref)
- read(ref)
- trace(retrieval_id)
- propose_memory(candidate)
- commit_memory(certified_candidate)

Provider failure SHALL be bounded and observable. Missions that do not require external context MUST remain executable when OpenViking is unavailable.

## 6. Progressive context loading

RESIDUAL SHALL map OpenViking's progressive context model into explicit context budgets:

- L0: discovery/filtering only
- L1: navigation/reranking/selection
- L2: full content loaded only after selection and budget checks

Every promoted item SHALL record why it advanced between levels, source identity, estimated/actual context cost where available, and retrieval trace identity.

Context loading MUST obey mission and worker budgets.

## 7. Context package

Workers MUST receive a bounded immutable ContextPackage rather than unrestricted provider access by default.

Each entry SHOULD contain:

- provider
- provider URI/reference
- retrieval ID
- level (L0/L1/L2)
- source/provenance
- content digest where practical
- relevance metadata
- token/byte cost
- retrieval reason
- timestamp/version
- trust classification

The package SHALL be represented in execution evidence.

## 8. Memory certification gate

Automatic provider memory MUST NOT become RESIDUAL truth.

Candidate memories SHALL pass a certification gate with classifications such as:

- OBSERVATION
- EXPERIENCE
- HEURISTIC
- VERIFIED_FACT
- INVARIANT

Only RESIDUAL-controlled policy may promote classifications. Provider-generated memories SHALL default to non-authoritative classifications.

Memory candidates SHOULD reference supporting Evidence Fabric records, verifier results, StationReceipts, source revisions, and expiration/invalidation conditions where applicable.

An INVARIANT MUST NOT be created solely from model-generated memory extraction.

## 9. Trajectory memory

RESIDUAL MAY persist qualified execution experience including:

- accepted repair trajectories
- rejected trajectories
- verifier failures
- regression causes
- successful tool sequences
- incident resolutions
- relevant StationReceipts

Rejected and failed trajectories MUST remain distinguishable from accepted trajectories. Retrieval MUST NOT silently present historical failure as recommended truth.

## 10. Swarm isolation

Workers SHALL NOT gain unrestricted shared-memory access merely because OpenViking is configured.

Context access MUST respect WorkerContract scope, project/mission isolation, provider ACLs where available, and RESIDUAL policy.

Cross-worker learning SHALL occur through certified context artifacts rather than implicit mutable shared state.

## 11. Evidence and observability

Every provider retrieval used by execution SHALL be attributable.

The Evidence Fabric SHOULD capture:

- query/intent identity
- provider
- traversal/retrieval trace
- selected and rejected references where practical
- L0 -> L1 -> L2 promotion decisions
- final injected context
- context cost
- provider errors/fallbacks
- memory writes/promotions

The Command Station SHOULD later expose a Context Inspector capable of explaining why each worker received each context item.

## 12. Failure behavior

The integration SHALL fail closed for authority and fail soft for optional context.

Provider outage, malformed responses, stale references, budget overflow, ACL denial, retrieval timeout, or memory-write failure MUST NOT weaken RESIDUAL controls.

Fallback to native/no-provider context MUST be explicit in evidence.

## 13. Security and privacy

Secrets MUST NOT be written to OpenViking context by default.

Provider endpoints and credentials SHALL use RESIDUAL's normal secret/configuration mechanisms. Retrieval and memory writes SHALL be scope checked. Untrusted retrieved content MUST remain data and MUST NOT acquire tool or policy authority through prompt injection.

## 14. Licensing boundary

OpenViking currently publishes its main project under AGPLv3 while some components are separately licensed. Before implementation, licensing SHALL be reviewed for the intended distribution/deployment model.

The initial design SHOULD prefer a provider-neutral adapter communicating with an independently deployed OpenViking service rather than copying OpenViking implementation code into RESIDUAL.

This specification is architectural guidance, not legal advice.

## 15. Proposed implementation PR sequence

PR-OV1 — Context Provider Contract

Define provider-neutral interfaces, ContextPackage schema, failure semantics, budgets, provenance, and tests using a fake provider.

PR-OV2 — OpenViking Adapter

Implement optional HTTP integration, health checks, configuration, namespace mapping, timeouts, and explicit fallback.

PR-OV3 — Progressive Context Loading

Implement bounded L0/L1/L2 selection and promotion with cost accounting and deterministic evidence records.

PR-OV4 — Evidence-Aware Memory Gate

Implement candidate memory schema, classifications, provenance binding, invalidation/expiry semantics, and certification policy.

PR-OV5 — Trajectory Memory

Persist qualified accepted/rejected execution experience and retrieve it without collapsing outcome distinctions.

PR-OV6 — Swarm Context Sharing

Add scoped context exchange through certified artifacts while preserving WorkerContract isolation and ownership boundaries.

PR-OV7 — Context Inspector

Expose retrieval traces, source provenance, L0/L1/L2 transitions, injected context, token cost, memory classification, and evidence links in Command Station.

## 16. Acceptance tests

Implementation SHALL eventually demonstrate at minimum:

1. RESIDUAL runs normally with no OpenViking configured.
2. OpenViking outage cannot bypass or weaken any control-plane decision.
3. Provider context cannot override a protected invariant or WorkerContract restriction.
4. L2 content is not loaded when L0/L1 selection rejects it.
5. Context budget exhaustion stops additional loading deterministically.
6. Every injected context item has provenance and retrieval identity.
7. Retrieved prompt-injection text cannot grant tools, expand scope, alter policy, or self-certify memory.
8. Unverified memory cannot become VERIFIED_FACT or INVARIANT without RESIDUAL certification.
9. Failed/rejected trajectories remain labeled as failures when retrieved.
10. Cross-worker retrieval respects mission/worker scope.
11. Provider timeout produces bounded fallback plus evidence.
12. Memory-write failure does not change mission acceptance.
13. Replay of a recorded context package can reproduce the worker input context without contacting OpenViking.
14. Context Inspector can explain the provenance and selection path for every context item used in a qualified demonstration.

## 17. Qualification gates

No implementation PR may enter the release path until:

- current RESIDUAL production-readiness gates remain green;
- protected trust-boundary tests pass unchanged unless an independently reviewed specification explicitly requires an additive test;
- provider-off baseline behavior is equivalent to pre-integration behavior;
- provider failure tests pass;
- prompt-injection/context-authority negative tests pass;
- provenance and replay tests pass;
- license review is recorded before shipping OpenViking-backed functionality.

## 18. Exit criteria

The OpenViking integration is considered qualified only when:

- OpenViking is fully optional and replaceable through ContextProvider;
- no OpenViking component sits inside RESIDUAL's authority chain;
- context injection is bounded, attributable, replayable, and budgeted;
- memory is evidence-aware and classification-safe;
- swarm sharing preserves isolation;
- provider outages cannot prevent core RESIDUAL execution where provider context is optional;
- Command Station can expose the retrieval/evidence chain;
- documentation clearly separates contextual intelligence from execution authority;
- all relevant RESIDUAL regression, trust-boundary, qualification, and negative-path suites pass.

## 19. Deferred implementation rule

This PR intentionally specifies future work only. It SHOULD NOT introduce runtime dependencies or alter production behavior. Implementation SHALL begin from the then-current main branch after the active production-readiness/convergence work is complete and SHALL be split into independently reviewable PRs following the sequence above.

## 20. OpenViking capability mapping

The adapter design SHALL target documented OpenViking capabilities rather than internal implementation details. Current OpenViking architecture exposes filesystem-style context operations, semantic search/find, session management, resource ingestion, progressive L0/L1/L2 representations, retrieval observability, and HTTP deployment.

The intended RESIDUAL mapping is:

| OpenViking capability | RESIDUAL use | Boundary |
| --- | --- | --- |
| `viking://` URI | Stable provider reference | Never treated as RESIDUAL authority |
| `search` / `find` | Candidate context discovery | Context Broker only |
| `abstract` / L0 | Cheap relevance filtering | Budgeted |
| `overview` / L1 | Navigation and selection | Budgeted |
| L2/full read | Final worker context | Explicit promotion required |
| retrieval observer/trace | Evidence attribution | Imported as provider evidence |
| session usage records | Context-use telemetry | Informational only |
| session commit | Candidate memory extraction | Certification gate required |
| cases/trajectories/experiences | Historical task learning | Outcome labels preserved |
| HTTP server | External provider boundary | Preferred integration mode |

RESIDUAL MUST NOT depend on undocumented OpenViking internals for correctness.

## 21. Namespace and identity mapping

RESIDUAL SHALL define its own logical context identity and map it to provider namespaces. A provider URI is not sufficient by itself to establish tenant, mission, worker, repository, revision, or trust identity.

A context request SHOULD carry at minimum:

- `mission_id`
- `worker_id`
- `worker_contract_id`
- `repository_id`
- `repository_revision`
- `tenant_or_operator_scope`
- `allowed_context_scopes`
- `context_budget`
- `provider_policy_id`

A returned provider reference SHALL be rebound to these RESIDUAL identities before it may enter a ContextPackage.

The adapter MUST reject namespace confusion, traversal outside allowed scopes, ambiguous aliases, and provider results whose effective scope cannot be established.

## 22. ContextPackage normative schema

The first implementation SHOULD define a versioned, serializable schema similar to:

```json
{
  "schema_version": "1",
  "package_id": "ctxpkg-...",
  "mission_id": "...",
  "worker_contract_id": "...",
  "repository_revision": "...",
  "provider": "openviking",
  "retrieval_id": "...",
  "budget": {
    "max_tokens": 0,
    "used_tokens": 0,
    "max_l2_items": 0
  },
  "entries": [
    {
      "provider_ref": "viking://...",
      "level": "L0|L1|L2",
      "content_digest": "sha256:...",
      "source_revision": "...",
      "trust": "UNTRUSTED|HISTORICAL|VERIFIED",
      "outcome": "UNKNOWN|ACCEPTED|REJECTED|FAILED",
      "reason": "...",
      "cost": {"tokens": 0, "bytes": 0}
    }
  ]
}
```

The final package SHALL be immutable after worker dispatch. Any later context acquisition requires a new package or an explicit append event with a new digest and evidence record.

The package digest SHALL be included in the worker execution evidence so replay can prove which context was actually supplied.

## 23. Deterministic budgeting and promotion policy

OpenViking may perform retrieval and reranking, but RESIDUAL SHALL own the final injection budget.

The Context Broker SHOULD implement deterministic ceilings for:

- total context tokens/bytes;
- maximum candidate count;
- maximum L1 promotions;
- maximum L2 promotions;
- per-source contribution;
- per-context-type contribution;
- retrieval wall-clock deadline;
- provider request count.

If two candidates have equal effective rank at a budget boundary, RESIDUAL SHALL apply a documented deterministic tie-breaker so replay does not depend on incidental provider ordering.

Provider-side context assembly MAY later be used as an optimization, but its output MUST still pass RESIDUAL-side budget, provenance, authority, and scope validation.

## 24. Memory lifecycle and invalidation

Memory certification is not a one-time trust conversion. Certified memories SHALL remain bound to their evidence and validity conditions.

A candidate memory SHOULD include:

- candidate ID and content digest;
- originating mission and worker;
- provider extraction metadata;
- source repository revision(s);
- supporting Evidence Fabric IDs;
- verifier/receipt references;
- classification;
- confidence metadata if available;
- creation time;
- expiration policy;
- invalidation triggers;
- supersedes/superseded-by relationships;
- outcome state.

Repository changes, failed requalification, contradictory evidence, revoked evidence, or changed protected invariants MAY invalidate previously certified memory.

Invalidated memory MUST remain auditable but MUST NOT be returned as current VERIFIED_FACT or INVARIANT context.

RESIDUAL SHOULD favor storing compact references to authoritative evidence over duplicating large evidence bodies into provider memory.

## 25. Threat model

The integration SHALL explicitly defend against at least the following classes:

1. **Prompt injection through retrieved content** — retrieved instructions attempt to modify worker authority or policy.
2. **Memory poisoning** — malicious or erroneous execution content becomes durable memory and influences later missions.
3. **Cross-mission leakage** — context from one mission appears in another without policy authorization.
4. **Cross-worker leakage** — a worker retrieves context outside its WorkerContract scope.
5. **Stale-context confusion** — context from an old repository revision is presented as current state.
6. **Outcome laundering** — a rejected or failed trajectory is retrieved without its failure status.
7. **Provider equivocation** — the same reference returns different content without version/digest evidence.
8. **Budget amplification** — provider behavior causes unbounded L2 reads, query expansion, or token consumption.
9. **Availability coupling** — provider outage blocks missions that should not require provider context.
10. **Credential/secret ingestion** — secrets are indexed or persisted into provider storage.
11. **Namespace alias confusion** — provider aliases resolve into unauthorized scopes.
12. **Memory self-certification** — provider-generated text claims VERIFIED_FACT/INVARIANT status without RESIDUAL evidence.

Each threat SHALL have at least one executable negative-path test before the corresponding feature is considered qualified.

## 26. Replay and provenance protocol

A qualified execution SHALL be replayable without requiring the provider to return the same live search result later.

For every injected item RESIDUAL SHOULD retain enough evidence to reconstruct:

`query -> provider trace -> candidate -> promotion -> exact injected bytes/digest -> worker input -> execution -> verifier result`

Replay mode SHALL support a frozen ContextPackage. In frozen replay:

- OpenViking MUST NOT be contacted;
- no new retrieval or memory mutation occurs;
- package digest must validate;
- worker-visible context must match the recorded package;
- evidence SHALL identify the run as replay rather than live retrieval.

This separates reproducible qualification from live retrieval quality.

## 27. OpenViking-specific qualification fixture

A later adapter PR SHOULD ship a small deterministic fixture corpus containing:

- architecture documentation;
- two similar but revision-distinct source files;
- an accepted historical repair;
- a rejected historical repair;
- a deliberately malicious prompt-injection document;
- a stale memory candidate;
- a secret-like value that ingestion policy must exclude;
- cross-worker and cross-mission resources.

Qualification SHALL prove correct L0/L1
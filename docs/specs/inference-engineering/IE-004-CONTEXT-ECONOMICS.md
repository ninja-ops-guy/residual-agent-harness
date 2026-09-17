# IE-004 — Context Paging Economics and Provenance-Safe Context Reuse

Status: proposed implementation contract  
Planning base: `main@f6f9bad84caccf68c7ab35e5788e756d12c55fb7`  
Prerequisites: qualified IE-001 prototype / #160; accepted IE-002 telemetry / #161

## 1. Objective

Reduce repeated context construction/transfer while preserving RESIDUAL's existing evidence-window, disclosure and receipt invariants.

RESIDUAL already supports fixed seed windows, precise evidence-window requests, window merging and an adaptive full-capsule heuristic. IE-004 MUST extend and measure those mechanisms rather than replacing them with an unrelated context system.

## 2. Design split

The implementation SHALL distinguish two different reuse layers.

### 2.1 Semantic context-fragment cache

Provider-independent immutable context fragments derived from accepted source/evidence snapshots.

Examples:

- task/obligation contract fragments;
- accepted-parent summaries/references;
- artifact windows;
- verifier feedback fragments;
- permitted-artifact manifest fragments.

### 2.2 Wire/prefix reuse

Optional provider/adapter-specific serialized prompt/prefix reuse where an adapter can report/support it safely.

Wire/prefix reuse MUST NOT be conflated with semantic accepted-value caching.

Provider/model/tokenizer/framing identity MAY be required for wire-level reuse even though provider identity is intentionally absent from RESIDUAL's accepted-value cache key.

## 3. Existing accepted-value cache remains authoritative

IE-004 MUST NOT weaken the existing rule:

> cached accepted values are untrusted proposals and the current verifier reruns before acceptance.

Context reuse cannot create accepted state, skip verification, skip disclosure checks or issue receipts.

## 4. Context-fragment identity

A normative semantic fragment key SHALL bind every input that can affect its bytes/meaning, including as applicable:

- context schema/protocol revision;
- obligation/task identity and frozen contract hash;
- artifact identity/path as already normalized by accepted source rules;
- exact immutable artifact content hash;
- evidence-window range;
- accepted dependency receipt hashes when the fragment includes dependency-derived content;
- verifier revision/feedback identity when included;
- disclosure policy / placement class;
- formatting/template revision used to construct the semantic fragment.

A fragment MUST NOT be reused when any normative identity differs.

## 5. Wire/prefix cache identity

If provider-specific serialized/prefix reuse is implemented, the key SHALL additionally bind every byte-shaping or provider-cache-sensitive input, for example:

- provider adapter revision;
- model/model-family identity where required;
- tokenizer/schema/framing revision;
- system/template revision;
- tool/schema declaration revision;
- provider cache mode/namespace where relevant.

The implementation MUST NOT assume two OpenAI-compatible endpoints share prefix-cache semantics merely because their APIs look similar.

## 6. Immutable-snapshot rule

All reusable context MUST derive from the same immutable snapshot/evidence model already used by the harness.

The cache MUST NOT reread a mutable filesystem path and treat matching path/name as sufficient identity.

A file modified in place MUST invalidate reuse through content identity.

Symlink/path safety remains governed by existing source/evidence rules.

## 7. Disclosure and privacy invariants

A cached fragment retains the strictest disclosure/placement restrictions of its inputs.

The system MUST NOT:

- promote local-only cached evidence into a remote request;
- reuse a fragment created under a broader disclosure policy when a narrower policy now applies;
- mix fragments from local-only and remote-exportable calls into one remote packet unless the existing policy explicitly permits every included input;
- log raw sensitive content merely to prove cache behavior.

Cache metadata may retain hashes, sizes, ranges, policy classes and identities without raw content where possible.

## 8. Paging policy

IE-004 SHALL preserve model-requested bounded evidence windows.

The first optimized policy SHOULD be deterministic and based on measured context economics rather than learned black-box behavior.

Inputs MAY include:

- seed bytes/tokens;
- full scoped capsule bytes/tokens;
- historical extra-window request count for the same task class;
- cache availability;
- remaining request/body/token budget;
- placement/privacy constraints;
- expected provider latency/cost when known.

The policy may choose among:

- seed-only;
- seed + cached fragments;
- complete scoped capsule;
- bounded incremental paging.

It MUST NOT include unrelated evidence simply to improve cache hit rate.

## 9. Context economics metrics

IE-002 telemetry SHALL be extended/projection-adapted to expose at minimum:

- semantic fragment cache lookups/hits/misses;
- wire/prefix reuse hits when authoritative;
- source bytes selected;
- serialized request bytes;
- prompt tokens when authoritative;
- provider-reported cached input tokens where available;
- evidence-window round trips;
- duplicate/overlap bytes avoided;
- invalidations by reason;
- estimated/authoritative cost delta only where inputs support it.

A provider that does not report cache usage MUST remain UNKNOWN for provider-cache savings.

## 10. Capacity and eviction

Context caches MUST be bounded.

The implementation SHALL define:

- byte/item ceilings;
- deterministic eviction policy or clearly non-normative cache-performance behavior;
- safe cleanup;
- no correctness dependence on cache presence.

Eviction may reduce performance only. It MUST NOT change acceptance semantics.

## 11. Cache poisoning resistance

Stored cache records MUST be validated before reuse.

At minimum:

- key/record identity must match;
- retained content hash must match bytes;
- schema revision must be supported;
- policy/placement compatibility must be rechecked;
- malformed/tampered entries must be rejected and treated as misses/errors, never trusted.

If persistent cache storage is added, replacement must use existing safe persistence patterns rather than predictable symlink-following temp paths.

## 12. Required tests

### T1 — existing paging preservation

With optimization disabled and cache empty, existing seed/window/adaptive-residual behavior remains equivalent.

### T2 — exact fragment reuse

Identical immutable artifact/contract/dependency/policy inputs reuse byte-identical semantic fragments.

### T3 — source invalidation

One-byte artifact content change invalidates affected fragments while unrelated artifact changes do not invalidate fragments that never declared/used them.

### T4 — dependency invalidation

Changing a dependency receipt invalidates fragments whose contents depend on that receipt.

### T5 — policy invalidation

Changing remote/local disclosure policy prevents incompatible reuse.

### T6 — no privacy promotion

A local-only fragment can never appear in a remote packet solely because it exists in cache.

### T7 — provider-specific wire identity

Different adapter/model/framing/tokenizer identities cannot incorrectly share a wire/prefix entry when those identities affect serialized bytes or provider cache semantics.

### T8 — tamper detection

Corrupt cached bytes/hash/schema/key fail reuse and cannot reach provider dispatch as trusted cache content.

### T9 — verifier authority

Context cache hits do not bypass normal verifier execution or receipt semantics.

### T10 — bounded cache

A stress fixture exceeds configured capacity and demonstrates bounded storage/eviction with unchanged correctness outcomes.

### T11 — paging economics

Frozen fixtures compare seed-only, full-capsule and bounded-paging modes. Report request bytes/tokens/round trips without asserting universal superiority.

### T12 — provider-cache UNKNOWN

Adapters without authoritative cached-token reporting never emit fabricated cache savings.

### T13 — replay

Given the same frozen snapshot, cache state and policy config, paging/reuse decisions replay deterministically where they are normative.

### T14 — exact-head regression

All applicable CI remains green and no protected M4 file/test/pin/shared evidence schema changes.

## 13. Qualification experiment

Before enabling as default, run a frozen engineering comparison over at least:

- small context / no reuse;
- large context with overlapping windows;
- repeated sibling obligations sharing public evidence;
- dependency change invalidation;
- mixed local-only/remote-exportable evidence.

Compare:

- accepted/integrated outcomes;
- request bytes/tokens;
- round trips;
- cache hits/invalidations;
- latency;
- cost where authoritative;
- telemetry completeness.

No result from this engineering fixture is a universal token/cost reduction claim.

## 14. Exit criteria

IE-004 exits when:

- prototype cache/paging model from IE-001 is qualified;
- all identity/disclosure/tamper tests pass;
- cache absence/eviction cannot alter correctness;
- disabled mode remains baseline-equivalent;
- exact-head repository qualification passes;
- independent review accepts the exact head.

## 15. Non-goals

This PR does not:

- cache accepted results without verifier revalidation;
- infer secret/public classification automatically;
- guarantee provider prefix-cache savings;
- choose stronger/weaker models;
- implement adaptive engine/topology routing;
- change M4 trust-boundary evidence authority.

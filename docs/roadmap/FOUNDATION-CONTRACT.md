# Foundation contract v1

**Owner:** Track A, this Codex thread. **Status:** implemented in the v0.4.0 foundation branch; see [implementation and limits](TRACK-1-IMPLEMENTATION.md) for the supported surfaces and deliberate legacy boundaries. This contract resolves the draft conflicts listed in [SPEC-RECONCILIATION.md](SPEC-RECONCILIATION.md). Version an interface change instead of quietly changing receipt bytes.

## 1. Receipt identity and acceptance

Keep the seven VRB receipt payload fields: `task_id`, `cache_key`, `value_hash`, `verifier_name`, `verifier_revision`, `verdict`, `parent_receipts`. Wrap that payload in an envelope containing `schema_version`, `hash_algorithm`, `receipt_hash` and the payload. Signatures, when added, are a separate envelope extension; a hash is not a signature or a proof of correct execution.

The initial schema is `residual.station.receipt.v1` and the hash algorithm is `sha256`. Compute `receipt_hash` over a domain-separation prefix followed by canonical UTF-8 JSON of the payload. The prefix is exactly `residual.station.receipt.v1\n`. Canonical JSON uses sorted string keys, compact separators, `ensure_ascii=False`, finite numbers only, and rejection of duplicate keys on decode. Algorithm and schema identifiers are allowlisted; an unknown profile is not silently interpreted as SHA-256.

`task_id` is the task's identifier within its bound project/run context. `cache_key` binds the complete namespace and context, so an identical task label in another project does not reuse a receipt accidentally. `verdict` is exactly `pass`, `fail` or `unknown`; only `pass` is eligible for acceptance. `value_hash` binds the exact immutable result snapshot given to the active host verifier.

`parent_receipts` is a sorted tuple of `{task_id, receipt_hash}` references to the task's **prerequisites**. Duplicate task references, unknown dependencies and cycles are errors. Reordering arrival of equivalent prerequisite receipts does not change the binding. Changing a prerequisite invalidates every dependent result reachable from it. This matches the existing `depends_on` DAG.

A receiver may validate the envelope's integrity without having the underlying evidence. It may mark a result `verified` only after its active host verifier validates the bound candidate and required witness/evidence. Missing evidence or an unavailable/mismatched verifier means `unverifiable` at the transport/admission layer, never an accepted `pass`.

## 2. Cache key and verifier revision

A cache binding contains:

- Protocol/schema version and hash profile.
- Project/task/obligation identifiers.
- Full GoalSpec content hash and immutable obligation contract hash.
- Namespaced verifier name, execution order and effective verifier revision.
- Sorted declared artifact IDs and content hashes.
- Sorted prerequisite task IDs and receipt hashes.

The cache key is the SHA-256 of `residual.station.cache.v1\n` followed by canonical JSON of this binding. The cache stores a proposed candidate plus its receipt/evidence references; it never grants acceptance by returning a value.

`verifier_name` is `{domain}:{evaluator}`. An effective revision binds the host-declared implementation artifact digest, immutable configuration digest, policy bundle digest and optional proof/checker digest. A human SemVer label may accompany it but cannot substitute for those identities. Registration must reject missing identity material for cacheable verifiers. Module authors provide the source/build artifact identities; the registry does not guess a reliable fingerprint from `repr(callable)`.

On retrieval: validate the schema and receipt digest; compare the current binding and effective revision; validate prerequisite receipts and value hash; run the active host verifier against a detached candidate snapshot. Only a new passing result may be admitted. `unknown`, stale revisions and corrupt/missing evidence are misses or explicit non-acceptance. Existing `residual.obligation.v1` data remains a legacy format and is not rewritten as a new receipt without verification.

## 3. Module descriptor

Use one `StationModule` protocol with `name`, `version`, `quarantine_policies()`, `verifiers()`, `brakes()`, `on_run_opened(spec)` and `on_run_closed(result)` as in SPEC-MODULE-001. Registration is explicit and host-selected; no directory scanning or imports of model-nominated plugins.

`verifiers()` evolves from bare tuples to immutable descriptors carrying the evaluator callable, `CheckType`, and the identity material in section 2. The registry supplies a temporary adapter for the draft tuple format only when the host separately supplies the missing revision data. It must not fabricate a revision for an anonymous callable.

The module returns local evaluator names; the registry prefixes the registered domain exactly once. Public lookup accepts only fully namespaced names. Duplicate domains, duplicate evaluator names, pre-prefixed conflicting names and invalid descriptors reject the entire registration transaction.

Configuration is snapshotted and frozen for a run. Stateful brakes are fresh per-run instances, never shared concurrently across projects. Registration order is deterministic. A registry is frozen **at LoopController construction** and remains frozen across that run. A module/version change needs a new registry and run.

## 4. Hook contracts and lifecycle

| Hook | Contract | Invalid/unavailable behavior |
|---|---|---|
| Policy | `(ProposedAction) -> None | nonempty str` | Deny; safe structured reason |
| Evaluator | `(candidate, parameters) -> (CheckResult, reason)` | Non-accepting result; no raw exception text |
| Brake | `update(host_event) -> BrakeTrip | None`, `reset()` | Registered enforcement failure aborts; do not ignore it |
| Read-only observer | Consumes a committed event copy | Failure counted; execution continues |

Add `CheckResult.UNKNOWN` without removing `PASS`, `FAIL` or `SKIPPED`. Overall success requires every criterion to be `PASS`. Unknown blocks acceptance and skips later judges just as a prior failing check does; it preserves the distinction between unavailable evidence and demonstrated failure. The first non-pass remains the primary finding.

Registration validates structure, signatures and declared return contracts. A declared boolean policy return is rejected. Python annotations cannot prove every runtime return; every invocation also validates its actual result. Never probe an effectful hook with a fabricated action during registration.

Pure policy evaluation does not execute changes or perform live I/O. The host wrapper records policy evaluation metadata. Proposal reservations remain host-owned, atomic bookkeeping, not mutable policy threshold changes. Long-running sandbox trials and telemetry sampling are separate bounded executor/verifier stages; a policy may inspect their already verified receipts.

Run ordering: commit run-open control event → call module open hooks → passes → commit run-close result/event → invoke module close hooks in registration order. A failed enforcement hook cannot silently disable a module. A post-close indexing/observer failure records a module diagnostic and does not rewrite a successful run's historical verdict or fabricate a second run-close event.

All applicable brakes are evaluated; abort outranks escalation and continuation. Core pass/token counters remain host-generated. Module telemetry enters through a host-owned, schema-validated extension event dispatcher. Worker/model-provided observation dictionaries cannot publish authoritative telemetry, completion or budget facts. Disabling optional observation recording must not disable enforcement.

## 5. Integration and domain-stage requirements

Track A supplies the registration/composition changes once. NetOps, SecOps, memory, replay and HITL modules then plug in without edits to core engine/station/loop/quarantine/verifier files.

The gateway must be explicit about action classes it actually guards. Current v0.3.0 provider-call quarantine does not claim to gate every arbitrary command or device mutation. A domain executor is host-registered, scope constrained and responsible for binding the held intent to the actual applied action. No user/network-generated code is loaded as an extension.

SecOps needs a host-owned candidate-inspection hook before Git staging. NetOps needs host-owned pre-change evidence and post-change telemetry stages. These are adapters around real execution stages, not callbacks that imply a module has already run merely because it registered an evaluator.

## 6. Minimal cross-track exchange

Module handoffs provide namespaced identities, revision/config hashes, declared read/write/tool scope, candidate/evidence references, ordered check results and brake facts. Trajectory, memory and mesh use these references to locate authorized evidence; they do not move raw logs or full chat histories into every model prompt.

Trajectory structural comparison uses logical event indices and stable task/action fingerprints. Runtime UUIDs, timestamps, durations and nondeterministic text are not regression equality keys. Full test inputs/outputs, when needed for replay, are separate access-controlled artifacts. If required witness data is absent, replay reports unverifiable rather than recreating an input from a hash.

# SPEC-GATEWAY/CONTROL-PLANE-001

## Purpose
RESIDUAL separates identity trust, authorization trust, computational trust, and transactional trust. Workers remain untrusted computation; durable state requires independent acceptance and controlled application.

## Architecture
Three planes are retained: **Control** (identity, policy, capabilities, secrets, HITL, revisions), **Compute** (routing, scheduling, workers, models, sandboxes), and **Assurance** (verification, counterexamples, integration, side-effect coordination, receipts). An append-only **Evidence Fabric** cross-cuts all planes and supplies real-time, verification, audit, and research projections.

## Threat model
- Benign: crashes, timeouts, malformed responses.
- Stochastic: plausible but incorrect output.
- Byzantine: inconsistent or deceptive output.
- Adaptive adversarial: trust farming, authority escalation, verifier manipulation, telemetry poisoning.

Historical performance MAY optimize routing but MUST NOT bypass verification or enlarge a mission authority envelope.

## Mission revisions and amendments
Mission identity is stable. Execution configuration is immutable per `MissionRevision`. Changes create `PlanAmendment` evidence and, after acceptance, a new revision linked to its predecessor. Authority expansion is fail-closed. Class 3 (authority) requires an independent verifier and human approval. Class 4 (trust boundary) requires at least two independent verifiers plus human approval. A worker MUST NOT be sole proposer, verifier and beneficiary of an authority-expanding amendment.

## Capabilities
Enforcement uses parameterized grants `(subject, action, resource, scope, constraints, conditions, approval_policy, expiry)`. Named roles are UI presets only. Routing selects among already-eligible workers and MUST NOT enlarge authority. Every route emits `RoutingDecision` evidence containing candidates, exclusions, selected worker, scoring inputs, certified-state references, router revision, policy revision and capability hashes.

## Memory and certified state
Raw/episodic memory is untrusted context and MUST NOT grant authority. `CertifiedState` is evidence-derived state and MAY feed policy/routing only while valid. It binds measurement window, sample size, derivation, verifier revision, expiry/staleness budget, drift status and environment fingerprint. Drift/configuration changes invalidate it; age may make it stale. Neither condition rewrites historical provenance.

## Failure semantics
`UNKNOWN != PASS` and `UNKNOWN != FAIL`. UNKNOWN requires explicit policy: gather evidence, independent verifier/ensemble, HITL, amendment or termination. Absence (timeout/crash/no output) is evidence. Every lifecycle transition requires an attributable cause and evidence reference.

## Side effects
Compound operations MUST decompose into dependency DAGs of atomic intents. Atomic intents use PREPARED → ATTEMPTED → APPLIED/FAILED/AMBIGUOUS; AMBIGUOUS → RECONCILING → APPLIED/FAILED. Transport acknowledgement is not external-state truth. Ambiguous effects MUST reconcile before retry. Transaction state may be INCOMPLETE when some atomic effects applied and others failed. Reversibility/compensatability MUST be known before execution where the target supports it; irreversible effects require stronger assurance.

## Approvals
Approvals are auditable evidence bound to principal, role, mission revision, intent, challenge nonce, timestamp and policy revision. Required approval fails closed on timeout/error. Policies MAY require quorum and separation of duties.

## Normative invariants
1. Workers propose; they never self-authorize.
2. Mission configuration is immutable per revision.
3. Authority expansion requires an accepted amendment.
4. Capability grants are scoped/contextual, never naked enforcement booleans.
5. Raw memory cannot grant authority.
6. Certified state carries derivation and provenance.
7. Evidence is append-only; projections may vary.
8. UNKNOWN is neither PASS nor FAIL.
9. Side effects require explicit intent identities.
10. Ambiguous effects reconcile before retry.
11. Approvals are auditable evidence.
12. Accepted state is cryptographically bound to what was verified.
13. Historical success cannot silently authorize a new mission.
14. Every state transition has an attributable cause.
15. Adaptive behavior may change future policy inputs, never past evidence.
16. Routing may allocate but never enlarge authority.
17. Routing decisions record eligible set, inputs, certified-state dependencies, router revision and policy revision.
18. Authority-expanding amendments require verifier/beneficiary independence and assurance proportional to expansion.
19. Compound effects are dependency graphs of atomic, individually reconcilable intents.
20. Certified state is valid only within explicit temporal, statistical and environmental bounds.

## Security statement
RESIDUAL does not require determining whether a worker is trustworthy. Every consequential output remains subject to bounded authority, evidence capture and independent acceptance regardless of historical performance.

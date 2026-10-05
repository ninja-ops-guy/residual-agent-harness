# RESIDUAL Thesis v2 — Candidate

**Status:** CANDIDATE. Formulation originated in Mike's 2026-10-04 review and was drafted for owner revision. **Not normative for v1.** CTR-004-governed: this thesis revision remains a candidate until Mike explicitly adopts it.

Related qualification program: #525 (ASC-001). Related hostile-worker qualification: #515 (AX-21 AWQ-001).

## Thesis

**v1:** "Can we determine whether an agent's work should be trusted?"

**v2 candidate:** "Can we guarantee, within a declared and frozen authority surface, that consequential agent actions occur only through explicitly authorized, evidence-bound transitions — even when the agent, its context, its connector capabilities, or its execution environment cannot be trusted?"

The evolution is from trust *determination* (epistemic: can we know?) to bounded guarantee *under distrust* (adversarial: does the declared architecture hold when its workers and surrounding context are not trusted?).

The claim is intentionally falsifiable. A silent authority path, unauthorized protected effect, invalid transfer of qualification across authority-environment drift, or plausible protected path left UNMAPPED defeats the bounded guarantee for that qualification boundary.

## What the thesis encompasses

Station authority, typed transitions, receipts, independent verification, candidate binding, effective-authority-environment binding, connector drift, UNMAPPED, AWQ, and cross-harness governance — without making any one mechanism the product.

The product thesis is the bounded authority guarantee. The mechanisms construct and demonstrate it.

## Missing artifact: Authority Surface Completeness Proof

ASC-001 defines the qualification method:

1. **Enumerate** authority-bearing transitions inside a frozen supported runtime boundary.
2. **Bind** each transition to its mediator, policy, authority principal, evidence requirements, and effective authority environment.
3. **Attempt bypasses** deliberately: compromised workers, alternate harnesses/routes, connector capability changes, stale or replayed evidence, poisoned context, verifier substitution, approval spoofing, authority escalation, recovery paths, and relevant TOCTOU cases.
4. **Require** every protected path to be mediated or explicitly classified UNMAPPED / NOT_TESTED / OUT_OF_SCOPE. There are no silent gaps and no force-fitting unknowns into PASS.
5. **Retain** candidate- and environment-bound evidence sufficient for an independent reviewer to reproduce the bounded verdict.

This converts "we designed a control plane" into "we tried to escape the declared control plane and can show what happened."

### UNMAPPED is load-bearing

UNMAPPED is not a failure to make the report look complete. It is a statement about the boundary of knowledge.

The guarantee extends only as far as the proof reaches. A plausible UNMAPPED path to a protected effect prevents ASC-001 PASS_BOUNDED until it is mediated, shown unreachable inside the frozen boundary, or explicitly removed from the claimed surface.

## Temporal candidate binding: code identity is not execution identity

A pinned agent revision interacting with connector capability set C1 does not necessarily have the same authority surface when that connector becomes C2.

Candidate binding therefore encompasses more than source/tree/runtime identity. ASC-001 defines an **Effective Authority Environment (EAE)** that binds authority-relevant execution context, including:

- harness/runtime identity and revision;
- tool and connector schemas/capability inventory;
- granted scopes and permissions;
- relevant policy and configuration;
- approval semantics;
- isolation backend;
- verifier identity/revision;
- adapter identity/revision; and
- protected endpoint/action inventory.

An authority-relevant EAE change invalidates automatic qualification transfer.

This generalizes exact-head discipline — "the tree qualified is the tree that runs" — into authority-environment discipline: **the authority surface qualified is the authority surface to which the verdict applies.**

## Independence: two agents are not necessarily two trust boundaries

Independence is architectural and evidentiary, not numerical.

A second model standing in the same adversarial context is not automatically an independent approval or verification boundary. Model diversity, provider diversity, or separate prompts do not themselves establish independent authority.

Verifier independence and Station authority therefore require explicit trust-boundary semantics and retained evidence. A model may produce evidence or recommendations without thereby possessing the authority to accept its own work.

## Benchmark demonstration

The capstone target is:

```text
compromised/untrusted worker
+ poisoned context
+ changed effective authority environment
+ hostile self-report
    -> attempted protected transition
    -> typed authority mediator
    -> DENY / REQUIRE_APPROVAL / HALT as policy requires
    -> no unauthorized protected effect
    -> independently verifiable candidate + EAE-bound evidence
```

The distrust assumptions are separable, producing a composable test matrix. A successful run does not mean "the agent behaved." It means the worker was not trusted and the protected transition still could not bypass the declared authority boundary.

AX-21 AWQ-001 (#515) supplies the deliberately untrusted-worker qualification component; ASC-001 (#525) supplies authority-surface enumeration, environment binding, bypass methodology, and bounded verdict semantics.

## Research program

The research program should repeatedly reproduce the benchmark across qualified harnesses, beginning with OpenClaw and Hermes and extending to additional adapters only when their qualification boundaries are explicit.

Primary research questions:

1. Can the authority surface be enumerated reproducibly enough for independent reviewers to find missing transitions?
2. Can EAE identity detect authority-relevant connector/tool/scope/policy drift without making harmless runtime variation invalidate every qualification?
3. Can protected effects remain unavailable to compromised workers across heterogeneous harnesses without weakening the semantic authority contract per adapter?
4. Can retained evidence distinguish REQUESTED, ATTEMPTED, EXECUTED, ACCEPTED, and EFFECT_OBSERVED states?
5. Can an independent reviewer reproduce the bounded verdict and discover deliberately seeded omissions?
6. What proportion of real integration changes require requalification, and can the affected transition subset be mechanically determined?
7. Which authority classes remain UNMAPPED, and why?

## Claim discipline

This candidate does **not** claim:

- universal security or universal non-bypassability;
- that prompt injection is solved;
- that all third-party authority surfaces can be completely enumerated;
- that a second model constitutes independent approval;
- that PASS_BOUNDED transfers across an authority-relevant EAE change;
- that post-v1 Agent Privilege Firewall work is already implemented; or
- that the v2 thesis is normative for v1.

The strongest permitted claim after successful ASC-001 qualification is bounded:

> Within the frozen declared authority surface and Effective Authority Environment identified by this qualification, the enumerated protected transitions were mediated as specified, the retained adversarial campaign produced zero unauthorized protected effects, and the independent review found no unresolved plausible UNMAPPED path to a protected effect.

Anything broader requires additional evidence.

## Governance

This document is a research candidate. Editing, testing, citing, or implementing ASC-001 does not constitute owner adoption of Thesis v2.

CTR-004 remains controlling: owner adoption must be explicit.

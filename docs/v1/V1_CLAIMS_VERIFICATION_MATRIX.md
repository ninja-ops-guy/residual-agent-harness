# RESIDUAL v1.0.0 Claims Verification Matrix

**Status:** PROPOSED RC EXIT CRITERION  
**Claims source:** `V1_CLAIMS_CONTRACT.md`  
**Rule:** selecting an exact RC records identity only; qualification, soak and
release authorization follow the explicit lifecycle below. Every applicable
claim still requires evidence, and every permitted non-applicable claim requires
an owner-approved, fail-closed scope exclusion with enforcement evidence.

| ID | Claim / exit criterion | Verification / evidence | Current status | Dependency / required action |
|---|---|---|---|---|
| CV-01 | Workers cannot self-approve/integrate and accepted state remains Station-authoritative. | Exact-RC qualification + authority regressions + evidence receipts. | IN_PROGRESS | Resulting-main/RC qualification. |
| CV-02 | v1 tenancy is trusted single-user/local-operator; multi-tenant behavior is not exposed as a v1 security claim. | Approved deployment profile + config/UI/API exposure review. | BLOCKED | Owner approve claims/profile; prove excluded modes are not accidentally advertised/accepted. |
| CV-03 | Direct Station exposure is loopback-only; any admitted remote-worker path uses the approved authenticated transport. | Deployment-profile validation + bind/proxy negative tests + AUD-1 F1/F3 evidence. | BLOCKED | Approve exact transport/profile; complete AUD-1. |
| CV-04 | Remote-worker authority is scoped, revocable and bounded under interruption. | Selected #438-chain successor, ten adversarial regressions, physical F6-A/F6-B, Mason/LEGION re-audit, exact-head qualification. | BLOCKED | Independent human review → owner selection → helper retarget/qualification → physical F6 → re-audit. |
| CV-05 | SQLite/Git persistence boundary is accurately documented; interrupted cross-boundary state fails into operator-visible recovery rather than false success. | Exact-RC persistence/fault-injection evidence + recovery runbook. | IN_PROGRESS | Bind applicable PR-G08/21 evidence to RC. |
| CV-06 | Only one authoritative Station process owns a v1 data directory; unsupported multi-process/shared-DB operation fails closed. | Startup/admission negative test with second process + deployment-profile enforcement. | NOT_STARTED | Implement/verify exclusion if not already enforced. |
| CV-07 | If Shared Comms ships: ACK is bound to expected project/operation and required actor/payload identity; malformed/cross-bound receipts cannot produce ACKED. | Minimal disposable regression reproducing #426 class, successor repair, exact-head CI. | BLOCKED | Claims decision; if included, REQUIRE_SUCCESSOR. |
| CV-08 | If Shared Comms ships: stored payload digest is verified before recovery network action; mismatch yields zero POST and fail-closed/quarantine disposition. | Disposable digest-tamper regression + successor repair + exact-head CI. | BLOCKED | Claims decision; if included, REQUIRE_SUCCESSOR. |
| CV-09 | Concurrent recovery is not a v1 capability; a second owner is prevented/rejected for the same outbox. | Two-owner negative fixture proving enforcement, not documentation. | BLOCKED | EXCLUDE_WITH_ENFORCEMENT before canary if Shared Comms ships. |
| CV-10 | No automatic HA/regional failover claim; backup/restore behavior meets only the approved RPO/RTO. | Approved profile + #435 recovery evidence contract + authorized restore rehearsal. | BLOCKED | Approve RPO/RTO/profile; execute authorized rehearsal later. |
| CV-11 | Release dependency set matches the approved support matrix and is exact-pinned/hash-locked. | #444 validator + authoritative generated lock digest + review. | IN_PROGRESS | Approve matrix; separately authorize trusted resolution environment. |
| CV-12 | Exact release artifact can be installed/built offline from the accepted lock and is reproducible under the approved policy. | Network-disabled hash-enforced build/install + two clean-build comparison + artifact digests. | NOT_STARTED | CV-11. |
| CV-13 | Direct-source evidence verification does not trust derived seal metadata as authority. | #443 tooling + independent frozen verifier run against private authoritative runtime and final Seal v2. | BLOCKED | Human review #443; private read-only PR-G26 verification. |
| CV-14 | Canary procedure and post-canary verifier are frozen before execution and all claim-relevant pre-canary blockers are resolved. | #412/#413 exact procedure/verifier + scope dispositions + explicit GO. | BLOCKED | CV-03/04/07/08/09 as applicable; no canary authorization yet. |
| CV-15 | Canary passes on the exact authorized candidate without expanding claims. | Hash-bound canary evidence + independent post-canary verification. | BLOCKED | Separate explicit canary authorization and execution. |
| CV-16 | Exact RC passes all applicable repository qualification gates with no inherited results from other heads. | Qualification-v1 and release-specific gates on exact RC. | NOT_STARTED | Convergence merges + resulting-main selection. |
| CV-17 | Exact RC survives the approved elapsed soak without claim-invalidating drift. | Soak manifest, periodic evidence, final disposition; reset on applicable RC change. | BLOCKED | Owner approve soak contract; CV-16. |
| CV-18 | Human release authority reviews the complete claims/evidence matrix and explicitly authorizes v1.0.0. | Exact-RC human release receipt/attestation. | BLOCKED | All applicable CV-01..CV-17 satisfied before the distinct human decision; no self-dependency. |

## RC lifecycle (proposed, not authorization)

The required order is explicit and acyclic. The table names the additional claim
rows checked at each transition; previous requirements remain in force.

| State | Predecessor | Additional claim rows |
|---|---|---|
| `RC_SELECTED` | `NONE` | `NONE` |
| `RC_QUALIFIED` | `RC_SELECTED` | `CV-01..CV-16` |
| `SOAK_VERIFIED` | `RC_QUALIFIED` | `CV-17` |
| `RELEASE_AUTHORIZED` | `SOAK_VERIFIED` | `CV-18` |

**RC_SELECTED means identity only, not a passing result.** Before selection,
owner/operations must approve claims and the deployment profile; release-critical
convergence must pass its required guarded integration and resulting-main
qualification; the owner must select one exact RC. Record its commit, tree,
artifact digest, lock/config/profile identities and intended qualification
environment. Missing identity or approval blocks selection. The NONE cells mean
no dependency on future RC evidence, not an exemption from these prerequisites.
An RC can then be tested without claiming its not-yet-observed results.

**RC_QUALIFIED** requires every applicable CV-01..CV-16 row to be VERIFIED with
accepted evidence for the identified scope. Permitted non-applicable rows require
an explicit owner-approved exclusion and evidence that the RC enforces it.
NOT_STARTED, IN_PROGRESS, BLOCKED, FAIL, UNKNOWN, missing or stale evidence cannot
satisfy an applicable row. CV-16, CV-17 and CV-18 are mandatory and cannot be scope-excluded.
This lifecycle does not replace or waive linked applicable parent release gates.

**SOAK_VERIFIED** additionally requires accepted CV-17 elapsed-soak evidence on
the selected RC under the separately approved policy. The existing reset rule
applies to claim-affecting code, dependency, configuration or artifact changes;
invalidated evidence must be re-established before advancing. No predecessor's
elapsed time is silently inherited. The proposed 72-hour default is not approval.

**RELEASE_AUTHORIZED** additionally requires the distinct, genuine human CV-18
release decision after all applicable CV-01..CV-17 evidence is accepted. CV-18
never depends on itself. The decision binds the exact RC and complete evidence
index; an automated report or lifecycle label cannot manufacture that authority.

`RC_READY` is an alias for `RC_QUALIFIED`, not for final release readiness.
`V1_RELEASE_READY` is an alias for `RELEASE_AUTHORIZED`.

Canary/physical/recovery/incident/soak execution still needs its separate authority.
Candidate selection or a passing documentation test grants none. Historical
canary evidence keeps its exact candidate binding; it is not automatically
transferred to a changed RC. Preserve scope reconciliation and required replays.

All row statuses above remain unchanged by this clarification. No approval,
execution, candidate selection, merge, tag or release is claimed. No percentage
substitutes for the matrix or the retained evidence.

## Freeze rule

From claims approval through v1.0.0 release, feature development is frozen for
the v1 release line. R5/research may remain preserved on isolated branches, but
must not open new merge pressure against the v1 release line. New work is
limited to demonstrated blocker repair, exact-head qualification, evidence,
release/recovery tooling, runbooks, and required acceptance fixes.

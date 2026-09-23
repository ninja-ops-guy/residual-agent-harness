# RRI-005 Swarm Implementation Plan

**Program:** SPEC-APF-001 / RRI-005  
**Status:** POST-v1 / IMPLEMENTATION-DEFERRED UNTIL OWNER GO  
**Research source:** [RRI-005 Agent Privilege Firewall](RRI-005-AGENT-PRIVILEGE-FIREWALL.md)

## Swarm objective

Implement and independently qualify the Agent Privilege Firewall without disturbing v1 convergence or weakening existing Control / Compute / Assurance boundaries.

No lane may claim completion from code presence alone. Every lane must produce testable behavior and evidence tied to the exact implementation revision.

## Lane ownership

### APF-A — contracts and canonicalization
Deliver:
- CapabilityLease
- TrustedEndpointManifest
- PrivilegedIntent
- APFDecision
- APFEffectReceipt
- SecurityViolationReceipt
- canonical serialization and schema validation

Acceptance: Q0 contract/schema gate.

### APF-B — trusted endpoint and trust-root enforcement
Deliver:
- immutable/versioned trusted endpoint registry
- destination identity normalization
- redirect policy
- network-class policy
- startup trust validation
- Class 4 mutation path

Acceptance: APF-I03/04/05/17/18/22 and RRI005-A01/A02/A05/A06/A19/A20/A23/A30.

### APF-C — capability broker and secret proxy
Deliver:
- destination-bound, short-lived capability leases
- principal binding
- revocation
- non-delegable default
- brokered secret use with no raw secret exposure to worker context

Acceptance: APF-I01/02/08/09/14/15/16/20 and RRI005-A04/A07/A11/A13/A14/A15/A16/A18/A28.

### APF-D — gateway enforcement and final revalidation
Deliver:
- APF interception for privileged intents
- immutable intent hashing
- immediate pre-effect revalidation
- approval binding
- fail-closed UNKNOWN/degraded behavior

Acceptance: APF-I07/10/11/12/13/23 and RRI005-A03/A08/A09/A10/A29.

### APF-E — receipts, reconciliation, and quarantine
Deliver:
- APF decision/effect receipts
- hash/signature verification
- forged/reordered/replay rejection
- AMBIGUOUS -> RECONCILING semantics
- quarantine and capability revocation receipts

Acceptance: APF-I19/20/24 and RRI005-A12/A22/A26/A27.

### APF-F — adversarial corpus and mutation engine
Deliver:
- machine-readable A01-A30 corpus
- C01-C06 positive controls
- deterministic simulator
- seeded mutation engine
- replayable failure bundles

Acceptance: Q2 and deterministic replay requirement.

### APF-G — concurrency and fault injection
Deliver:
- TOCTOU tests around policy, DNS, capability expiry, revocation, mission revision
- APF/policy/receipt-store restart and unavailability injection
- timeout-before-send and timeout-after-send cases

Acceptance: Q3 + Q4.

### APF-H — compromised-worker campaign
Deliver:
- malicious worker harness with arbitrary intent generation
- sibling impersonation attempts
- fabricated history/telemetry attempts
- strategic timing
- self-authorization attempts

Acceptance: Q5.

### APF-I — qualification and independent review
Deliver:
- qualification manifest
- clean-install RC run
- retained evidence bundle
- independent reviewer mutation
- final Q0-Q10 matrix

Acceptance: Q8 + Q9 + Q10.

## Merge discipline

1. No lane pushes directly to protected main.
2. No lane self-approves.
3. Implementation PRs reference SPEC-APF-001 / RRI-005.
4. Security claims remain UNKNOWN until their qualification gate passes on the exact candidate.
5. Negative, BLOCKED, UNKNOWN, and FAIL evidence is retained.
6. Swarm lanes must not modify the frozen v1 release path unless separately authorized.
7. Shared contracts are frozen before parallel implementation begins; incompatible contract changes return to APF-A rather than being silently forked.

## Recommended execution order

Phase 1: APF-A, then contract freeze.  
Phase 2 in parallel: APF-B, APF-C, APF-D, APF-E, APF-F.  
Phase 3: APF-G + APF-H against the integrated candidate.  
Phase 4: APF-I clean-install qualification and independent review.

## First swarm milestone

The first integrated candidate is complete when:
- APF-A through APF-F are merged into the candidate branch;
- A01-A10 and C01-C02 execute deterministically;
- unauthorized privileged effects = 0 for that initial corpus;
- raw secret exposure count = 0;
- no test is skipped;
- the candidate is still explicitly NOT production-qualified until Q3-Q10 complete.

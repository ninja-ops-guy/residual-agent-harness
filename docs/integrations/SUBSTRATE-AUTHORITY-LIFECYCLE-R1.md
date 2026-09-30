# SUBSTRATE-AUTHORITY-LIFECYCLE-R1

**Status:** post-v1 security hardening candidate  
**Date:** 2026-09-30  
**Depends on:** SUBSTRATE-QUALIFICATION-AUTHORITY-R0  
**Release effect:** none on v1

## Purpose

R0 answers:

> Did a Station key that I already trust sign this exact qualification PASS?

R1 adds:

> Was that key authorized to issue at that time, is the admission still fresh,
> has it been revoked, and can trust move to a successor key without silently
> trusting a new key?

This is required before qualification authority is distributed across a fleet.

## Authority artifacts

R1 keeps the trust layers separate:

    qualification evidence ledger
              |
              v
    Station admission bundle
              |
              v
    authority lifecycle bundle
       |             |
       |             +-- qualification revocations
       |
       +-- dual-signed Station key successor transitions
              |
              v
    local pinned root public key(s)
              |
              v
    local freshness policy / distrust list
              |
              v
    effective AdmittedQualificationRegistry

None of these artifacts authorize candidate acceptance or merge.

## Qualification freshness

QualificationAuthorityPolicy applies local trust policy:

- evaluation time;
- maximum admission age;
- maximum allowed future clock skew;
- minimum issue timestamp / generation fence.

An admission outside policy remains cryptographically valid historical evidence,
but is not effective execution authority.

This distinction is intentional: expiry does not rewrite history.

## Qualification revocation

QualificationRevocation is a domain-separated Ed25519 authorization over:

- exact admission hash;
- exact qualification record digest;
- signer Station key ID;
- effective timestamp;
- reason code.

Signature domain:

    residual.substrate.qualification-revocation.v1\n

A revocation is effective only when signed by a Station key that is active at the
revocation timestamp under the pinned trust graph.

Future-dated revocations remain retained evidence but do not take effect early.

## Station key succession

StationKeySuccessor is a dual-signed continuity record.

It binds:

- predecessor Station key ID;
- raw successor public key and key ID;
- successor activation timestamp;
- predecessor retirement timestamp;
- predecessor signature;
- successor countersignature.

Signature domain:

    residual.substrate.station-key-successor.v1\n

The predecessor authorizes the successor. The successor countersigns the exact
same transition to prove possession.

The trust store rejects:

- unrooted successor chains;
- invalid predecessor or successor signatures;
- successor activation before its predecessor is trusted;
- multiple successors from one predecessor;
- one successor introduced by multiple predecessors;
- cycles / reuse of an already trusted successor key;
- transitions descending from a locally distrusted key.

During an overlap window both predecessor and successor may issue.

At predecessor retirement, new admissions from the predecessor cease to be
effective. Historical admissions issued while it was active may remain valid
until they expire or are revoked.

## Re-admission during rotation

The same immutable PASS may be re-signed by a successor Station key.

R1 deterministically resolves multiple valid admissions for the same exact
record to the newest valid issuance, breaking ties by admission hash.

This prevents key rotation from changing capability identity while keeping one
unambiguous effective authority record.

## Local distrust

The consumer may supply a local list of distrusted Station key IDs.

Local distrust is stronger than imported lifecycle evidence.

A distrusted root cannot authorize admissions or extend trust through successor
transitions.

This provides an emergency operator fence when a key is suspected compromised.

## Strict invalid-signature behavior

There is a difference between:

- a trusted key that was not active at an admission timestamp; and
- a malformed signature claiming to come from a trusted key.

The first produces an ineffective historical admission.

The second is a verification failure.

R1 does not silently discard malformed signatures from known trusted keys.

## Operator command

R1 adds:

    residual substrate verify-authority-lifecycle \
      qualification.json \
      admissions.json \
      lifecycle.json \
      --station-public-key-hex <pinned-root-key> \
      --max-admission-age-seconds <seconds> \
      [--max-future-skew-seconds <seconds>] \
      [--min-issued-at-ns <timestamp>] \
      [--at-ns <timestamp>] \
      [--distrust-key-id <sha256>] \
      [--expected-ledger-digest <sha256>] \
      [--expected-admission-digest <sha256>] \
      [--expected-lifecycle-digest <sha256>] \
      [--json]

The CLI evaluates authority. It does not create admissions, transitions,
revocations, or root trust.

Production Station code should use its trusted local clock. The explicit
--at-ns surface is for reproducible qualification/audit.

## Shared Comms integration

These three artifacts are designed to travel independently:

1. evidence ledger;
2. admission bundle;
3. lifecycle bundle.

Shared Comms transport must preserve byte identity under the accepted
byte-exact transport contract before any received artifact is considered
admissible.

Transport does not establish trust.

A receiving seat still requires its own pinned Station trust root and local
freshness policy.

## Fleet behavior

A fleet seat may therefore be in states such as:

    EVIDENCE_PRESENT
    ADMISSION_PRESENT
    SIGNATURE_VALID
    FRESH
    REVOKED
    STALE
    SIGNER_RETIRED_AT_ISSUE
    SIGNER_DISTRUSTED
    AUTHORITY_EFFECTIVE

Only AUTHORITY_EFFECTIVE records may contribute capabilities to production
substrate routing.

## OpenShell consequence

For an OpenShell execution:

1. qualification evidence must PASS;
2. the exact PASS must have an effective Station admission;
3. the requested tuple must match that PASS before sandbox creation;
4. the observed live enforcement state must match that PASS before agent run;
5. candidate output still enters normal RESIDUAL verification;
6. accepted state still requires its independent integration/authority gate.

The authority lifecycle therefore governs permission to *use the execution
substrate*. It never authorizes the agent's answer.

## Remaining production PKI work

R1 provides bounded fleet-ready key continuity semantics, but a larger enterprise
deployment may additionally want:

- offline/root versus online/intermediate Station roles;
- quorum / threshold admission for high-impact substrate capabilities;
- hardware-backed key custody;
- organization/tenant scoping;
- certificate/OIDC mapping for remote gateways;
- revocation distribution SLA and stale-control-plane handling;
- audit retention policies;
- independent authority service / HSM integration.

Those can be layered above the same record/tuple/admission contract without
changing engine or substrate semantics.

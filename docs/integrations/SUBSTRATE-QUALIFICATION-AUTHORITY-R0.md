# SUBSTRATE-QUALIFICATION-AUTHORITY-R0

**Status:** post-v1 security hardening  
**Date:** 2026-09-30  
**Depends on:** EXECUTION-SUBSTRATE-SPI-R0  
**Release effect:** none on v1

## Problem

A content-addressed qualification record proves that bytes did not change. It does
not prove that a trusted RESIDUAL authority accepted those bytes as qualification
evidence.

Without an authority layer, an attacker could construct a structurally valid
PASS record, hash it correctly, place it in a ledger, and ask a router to consume
it.

## R0 authority chain

R0 separates four states:

    observed evidence
        |
        v
    qualification record
    (derived PASS/FAIL/BLOCKED/UNKNOWN)
        |
        v
    Station admission
    (Ed25519, dedicated signature domain)
        |
        v
    admitted qualification registry
        |
        +--> QualifiedSubstrateRouter
        +--> OpenShell qualified dispatch
        +--> bounded self-build admission

The evidence ledger remains useful even when no authority has admitted a record.
It can be inspected, transported, archived, compared and independently reviewed.

Only the admitted registry can grant a capability to an execution decision.

## Signature domain

Substrate qualification admissions use:

    residual.substrate.qualification-admission.v1\n

This is intentionally different from Factory worker receipt domains.

A Factory receipt signature cannot be replayed as a substrate qualification
admission, even when the same Ed25519 Station key underlies both identities.

## QualificationAdmission

A Station admission binds:

- exact qualification record digest;
- exact qualification tuple digest;
- Station key ID (SHA-256 of raw Ed25519 public key);
- issuance timestamp;
- schema identity;
- domain-separated Ed25519 signature.

Because the record digest transitively binds the gate statuses, evidence root,
capabilities, tuple, limitations and metadata, the Station does not sign a loose
capability string.

## Admission bundle

Admissions are stored separately from the qualification evidence ledger.

This is intentional:

- receipt of an evidence ledger does not grant authority;
- receipt of an admission bundle does not establish trust in its signer;
- consumers must possess a separately pinned trusted Station public key;
- only the combination of matching evidence, matching admission, and trusted
  public key creates an admitted qualification.

The admission bundle is itself content-addressed for transport and replay.

## Operator verification

R0 provides:

    residual substrate verify-ledger qualification.json --expected-digest <sha256>

and:

    residual substrate verify-authority \
      qualification.json \
      admissions.json \
      --station-public-key-hex <raw-ed25519-public-key-hex> \
      --expected-ledger-digest <sha256> \
      --expected-admission-digest <sha256>

The first command proves structural/content integrity.

The second additionally proves that each admitted record was signed by a Station
key in the caller's pinned trust set.

Neither command merges code, launches a sandbox, or issues new authority.

## Routing invariant

Production substrate routing MUST NOT accept SubstrateQualificationRegistry
directly.

It MUST accept AdmittedQualificationRegistry.

This gives a mechanical distinction between:

    "there is evidence saying PASS"

and:

    "a trusted Station admitted this exact PASS for use"

## OpenShell invariant

The OpenShell adapter's production qualification mode consumes an admitted
registry.

Before sandbox creation it requires:

- Station-admitted PASS;
- exact record pin;
- requested capability;
- exact OpenShell/source/driver/platform/environment/agent/image/policy/provider/
  inference tuple.

After sandbox creation and before agent execution it additionally requires the
observed enforcement-state digest to match qualification.

A valid Station signature therefore cannot authorize a different live sandbox
state than the one the Station admitted.

## Self-build invariant

A signed substrate PASS does not imply merge authority.

The bounded self-build contract independently prohibits:

- worker repository-write authority;
- accepted-state mutation;
- merge authority.

Station qualification admission authorizes use of the substrate properties only.
It does not elevate the worker's repository authority.

## Trust boundary

R0 assumes the consumer has an authentic Station public key.

Embedding a public key next to a signature is not sufficient. A malicious bundle
could replace both.

Trust establishment remains external to the admission artifact, consistent with
other RESIDUAL Station-signed evidence.

## R1 requirements before distributed production authority

R0 intentionally does not claim full lifecycle PKI.

R1 should add:

1. signed qualification revocation records;
2. key rotation / successor-key continuity;
3. admission expiry or mission-time freshness rules;
4. trust-store distribution over Shared Comms;
5. replay/freshness binding to Station generation or release epoch where needed;
6. independent operator reproduction before enterprise-wide admission;
7. audit UI showing evidence PASS separately from Station ADMITTED/REVOKED/EXPIRED.

Until those exist, R0 admissions are suitable for bounded post-v1 qualification
and controlled self-hosting experiments, not an indefinite distributed trust
grant.

## Security properties

R0 establishes:

- evidence integrity by content digest;
- authority by domain-separated Ed25519 signature;
- signer identity by pinned public-key hash;
- exact record binding;
- exact qualification tuple binding;
- cross-domain replay resistance;
- fail-closed routing when admission is missing or invalid;
- separation of substrate authority from candidate acceptance authority.

R0 does not establish:

- eternal freshness;
- revocation;
- automatic trust in a newly seen Station key;
- correctness of the underlying qualification evidence;
- candidate correctness;
- merge authorization.

Those remain separate gates.

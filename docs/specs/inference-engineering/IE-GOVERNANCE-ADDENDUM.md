# Inference Engineering Governance Addendum

Status: current planning addendum after merge of governance PR #168.

## Purpose

IE-001 through IE-007 were drafted before RESIDUAL adopted the solo-maintainer approval model. Any generic wording in those planning specs or PR descriptions that requires an independent human review solely as the normal merge gate is superseded by the merged policy in `docs/governance/SOLO_MAINTAINER_POLICY.md`.

## Current normal merge gate

For current solo-maintainer operation:

`implementation -> automated qualification/review appropriate to scope -> exact-head maintainer attestation -> merge`

The exact-head attestation is the machine-checkable control defined by PR #168. A changed head invalidates a prior attestation and requires fresh qualification/attestation as applicable.

## What this does not change

This addendum does not weaken technical or evidence requirements. In particular:

- protected M4/capable-runner requirements remain unchanged;
- UNKNOWN/BLOCKED never becomes PASS;
- first-failure and exact-head evidence discipline remains;
- live-provider, production, soak, visitor-journey and research evidence must actually be run before being claimed;
- independent/third-party review remains a separate claim when another human actually performs it or when a specific security/research claim requires it.

## IE-001 Q11 interpretation

For the current solo-maintainer workflow, IE-001 Q11 is interpreted as:

> **Q11 — exact-head maintainer acceptance.** Automated technical review/qualification appropriate to the prototype scope MUST pass on the exact current head, followed by explicit exact-head maintainer attestation under the merged solo-maintainer policy. If independent human review is available or claim-specific policy requires it, retain that separately and do not describe automated review as independent human review.

## Integration program

All INT-* integrations staged on IE branches are additionally governed by `INT-000-INTEGRATION-AUTHORITY-CONTRACT.md`. External systems do not acquire RESIDUAL verifier, receipt, disclosure, budget, routing-eligibility or deterministic-integration authority.

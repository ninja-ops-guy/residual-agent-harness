# Solo maintainer review policy

## Purpose

RESIDUAL is currently maintained by one human. The repository therefore MUST NOT claim that every change receives independent human review when no second human reviewer exists.

The merge model is instead:

`implementation -> automated qualification/review -> exact-head maintainer attestation -> merge`

This is a separation-of-controls model, not independent human assurance.

## Required merge conditions

A pull request targeting `main` is merge-eligible only when all repository-required CI, security, qualification, evidence, and protected-boundary checks pass for the exact current head and the maintainer explicitly attests to that exact head.

The maintainer attestation is a PR conversation comment containing exactly:

```text
RESIDUAL-MAINTAINER-APPROVAL: <full-current-head-sha>
```

A new commit immediately makes the old attestation stale. The maintainer must inspect the new exact head and attest again.

The maintainer can revoke an attestation for the same head with:

```text
RESIDUAL-MAINTAINER-REVOKE: <full-current-head-sha>
```

Only a human GitHub account with repository `write` or `admin` permission qualifies. Bot/application identities and read-only outside accounts do not satisfy the gate.

## Solo authorship

The maintainer MAY attest to a pull request they authored. This is intentionally different from GitHub's native `APPROVED` review semantics, because GitHub does not permit a PR author to approve their own pull request.

When a separate implementation bot/service identity is available, prefer:

`bot/service identity authors PR -> automated qualification -> maintainer account attests/approves -> merge`

That improves operational separation, but it still does not become independent human review unless another human actually performs the review.

## Automated review

Automated static analysis, tests, adversarial checks, browser proofs, qualified runtime tests, and model-assisted code review are useful evidence, but MUST be described as automated review/qualification. They MUST NOT be described as independent human review.

## Protected M4 and evidence discipline

This policy does not weaken any protected M4, evidence, release, provider, soak, onboarding, or qualification rule. In particular:

- capable-runner requirements remain capable-runner requirements;
- host/environment skips do not become PASS;
- UNKNOWN/BLOCKED do not become PASS;
- first failures remain authoritative evidence;
- changed heads require fresh qualification;
- operational, live-provider, soak, production, and visitor-journey evidence must actually be run and retained before being claimed.

## Independent review when available

Independent review remains recommended for security-sensitive, trust-boundary, release, and research-claim changes. When an independent human reviewer is available, record that review explicitly and distinguish it from the solo-maintainer attestation.

Until then, public/project language should say **maintainer-reviewed with automated qualification**, not **independently reviewed**.

## Machine gate

`.github/workflows/maintainer-approval.yml` runs `scripts/check_maintainer_approval.py`.

The checker traverses every retained PR conversation-comment page within a bounded fail-closed limit, binds approval to the exact current PR head, rejects bot identities and stale-head commands, verifies write/admin repository authority, and honors a later exact-head revocation.

API failure, malformed data, missing permission evidence, pagination exhaustion, or absent exact-head attestation returns BLOCKED/nonzero.

The workflow is not a substitute for repository rules. The branch/ruleset should require the `maintainer-approval` status together with all production-readiness checks appropriate to the changed scope.

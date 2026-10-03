# V1 master readiness delta — PR-G28 lock contract

Status: append-only release-preparation evidence. No production or release
authorization is implied.

## Exact baseline

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- prior master-list head before this write:
  `ace6968d156fa174639db6a738e9caee0a08cbf4`
- PR-G28 proposal: #444
- #444 exact head: `1403429dbdcb3abf04bcb1fb75fd1a2bad93cfbc`
- #444 exact base: accepted main above

## PRE-PRODUCTION — PR-G28

### Acceptance criterion

The v1 release build must be reproducible/offline from a complete reviewed
dependency set whose allowed distributions are exact-pinned and hash-locked.
The exact accepted lock digest must bind the release-candidate build evidence.

### Observed current-main gap

`pyproject.toml` on accepted main contains ranges including
`setuptools>=68`, `defusedxml>=0.7.1,<1`, `cryptography>=43`, and
`PyYAML>=6`. No `uv.lock`, `poetry.lock`, or release requirements lock
was located. Qualification currently uses network-resolved
`pip install '.[factory,qualification]'`; its wheel job builds the project
with `pip wheel . --no-deps`.

Classification: **observed missing evidence / release supply-chain gap**.

### Repository preparation

#444 adds a stdlib-only fail-closed validator for a future release lock and
synthetic negative/positive tests. It requires exact `==` pins and SHA-256
hashes, rejects duplicate normalized projects, and rejects editable/direct
URL/VCS sources under the proposed v1 contract.

It deliberately does not add a lockfile because this task is not authorized to
download/resolve dependency artifacts. No version or hash is invented.

### Dependencies / ownership

- owner: release/supply-chain reviewer + operator for separately authorized
  dependency resolution;
- implementation PR: #444;
- dependencies: owner-approved release Python/platform/optional-extra matrix,
  then authorized lock generation, offline install/build qualification, exact RC
  evidence binding;
- overlaps PR-G27 only at supply-chain evidence; it does not modify #440.

### Test / verification status

At the time of this delta, #444 exact-head GitHub Actions have been dispatched
but are not yet terminal. Therefore:

- #444 repository proposal: **IN_PROGRESS**;
- PR-G28 parent: **BLOCKED / NOT VERIFIED**;
- MERGED_AND_REQUALIFIED: not reached.

No historical CI result is inherited onto #444.

### Required human/operator action

After repository review, select the exact supported release matrix and authorize
a dependency-resolution environment to generate the complete transitive lock
and artifact hashes. Then prove hash-enforced installation/build with network
disabled, perform the required reproducibility comparison, and bind the accepted
lock/artifact digests to the exact RC. Until that evidence exists, PR-G28 cannot
be marked VERIFIED.

## Other gates

No change to PR-G26 parent, V1-PC-002..004, deployment topology/SLO/RPO/RTO,
AUD-1, canary, physical tests, recovery/rollback/incident drills, soak, tag,
release, or production acceptance.

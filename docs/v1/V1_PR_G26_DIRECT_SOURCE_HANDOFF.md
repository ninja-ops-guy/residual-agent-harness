# V1 PR-G26 direct-source seal verification handoff

Status: **REPOSITORY PREPARATION ONLY / PR-G26 NOT VERIFIED**

This current-main integration successor carries the reviewed manifest/cardinality
verifier from PR #415 and the synthetic adversarial characterization from PR
#422 onto the v1 release-preparation line without rebasing, rewriting, or
modifying either evidence/research branch.

## Provenance

- integration base: `main@d796f36b75e730a0bab71bdba564206174393719`
- source verifier: PR #415 head
  `3da0d8ec45adf8934b88906462706617aa22831f`
- source adversarial corpus: PR #422 head
  `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645`
- frozen R4.1 candidate referenced only:
  `8701367db6d3202f24b3eb9f4696b0cadf657985`
- frozen R4.1 tree referenced only:
  `79bfe6ed1743907065ed44aeb9c460c47527e0c6`

No Seal v2 bytes, authoritative runtime evidence, private paths, credentials, or
operator logs are copied into this branch.

## What this successor verifies

The stdlib-only verifier:

1. parses every non-empty `SHA256SUMS` entry and rejects malformed,
   duplicate, absolute, traversal, empty, and noncanonical POSIX paths;
2. opens the manifest and each referenced file without following symlinks;
   referenced directory components are walked relative to an anchored directory
   descriptor using `O_DIRECTORY | O_NOFOLLOW`, and the final descriptor must
   identify a regular file before any bytes are hashed;
3. derives cardinality only from the manifest;
4. rejects a seal whose recorded manifest count, failure count, or PASS
   disposition disagrees with the direct manifest result;
5. emits the digest of the same manifest bytes used for parsing and counting.

The verifier rejects internal as well as external symlinks, including a symlink
used as the manifest itself. It does not perform a check followed by reopening
an ordinary pathname. `O_NONBLOCK` prevents FIFO opens from hanging before
regular-file validation. Unsupported no-follow/descriptor-relative platforms
fail closed; native Windows verification is not qualified by this change.

The caller must choose a trusted, stable package root and verify an immutable
snapshot. Resolving that caller-selected root is a trust decision, not evidence
that its ancestors, filesystem mounts, or hard links are independently isolated.
This patch does not prove concurrent-content immutability, mount/hard-link
closure, closed-world package membership, or semantic/provenance authority.

The synthetic adversarial tests preserve the distinction between byte integrity
and semantic evidence authority. Extra unmanifested files, semantically false
metadata, and derived-to-derived provenance remain outside the current
cardinality verifier's scope.

## Retained containment finding and focused repair evidence

On original #443 head `d4af45bd07abf96d60c834c060395e5619731583`, verifier
blob `941c653db3784761a3f3379f329e7cb7419ac15d` was reproduced byte-exact
locally. Both a direct file symlink and a symlinked parent directory returned
`verification=PASS` for matching disposable external bytes. The existing 11
tests also passed; they did not exercise containment. This is a verifier
implementation defect, not merely a status-document omission. The original
head and its historical CI remain retained and are not rewritten.

The repaired verifier blob is `d29f245c9d25668df23f95c1bce7874da7080321`
(SHA-256 `fe36e3a00e2b3d6233e0029ddf60aec4b5963e9df082a59d7c88e11be4a9f00e`).
The expanded adversarial-test blob is `00cd13a62aefbd14e8d2aeabdb0e8a2bb4b4c0b5`.
The exact published source/test bytes passed **26/26 focused tests, zero skips**
in a disposable Linux/Python 3.13.5 environment on 2026-09-24. Coverage includes
external/internal file and directory symlinks, broken/looping symlinks, manifest
symlinks, canonical names, non-regular files, unsupported capabilities,
leaf/parent swaps immediately before open, an already-open directory surviving
path replacement, same-read manifest digest binding, and descriptor cleanup.
This is local focused evidence only; fresh exact-head hosted qualification and
independent human review are still required. No private source package was read.

## What remains before PR-G26 can be VERIFIED

This branch does **not** establish direct-source semantic verification of the
private R4.1 package and does not claim Seal v2 verification. PR-G26 remains
blocked until all of the following exist:

- an independently reviewed/frozen verifier implementation is selected;
- the verifier is executed against the private authoritative
  `runtime-20260924T025450Z` source package and the final Seal v2 without
  modifying either;
- authoritative `QUALIFICATION_R4.json`, gate records, candidate HEAD/tree,
  safety counters, unresolved-gate set, and final disposition are recomputed
  from their named source records rather than trusted from summaries;
- package-closure policy is explicitly decided and verified where closed-world
  semantics are claimed;
- derived evidence/provenance claims terminate at named authoritative sources;
- an independent reviewer retains a sanitized result bound to the verifier
  digest, source manifest digest, candidate identity, and Seal v2 digest.

GitHub-only access cannot perform those private-source checks. Absence of that
 evidence is `BLOCKED`, never `PASS`.

## Repository-side test command

`python -m unittest -v tests.test_r4_seal_manifest tests.test_r4_seal_manifest_adversarial`

Passing these tests establishes only verifier/cardinality/containment behavior
on synthetic fixtures. It does not authorize the canary or change historical
R4.1 `READY_FOR_CANARY` qualification.

## Safety boundary

No canary, production deployment, physical test, seal creation, seal mutation,
release/tag publication, merge, approval, human attestation, or live/private
evidence access is authorized by this document or branch.

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
   duplicate, absolute, traversal, and empty paths;
2. independently hashes each referenced regular file;
3. derives cardinality only from the authoritative manifest;
4. rejects a seal whose recorded manifest count, failure count, or PASS
   disposition disagrees with the direct manifest result;
5. emits the independently derived manifest digest and verified count.

The synthetic adversarial tests preserve the distinction between byte integrity
and semantic evidence authority. They demonstrate that extra unmanifested files,
semantically false metadata, and derived-to-derived provenance remain outside
the current cardinality verifier's scope.

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

Passing these tests establishes only the verifier/cardinality behavior on
synthetic fixtures. It does not authorize the canary or change historical
R4.1 `READY_FOR_CANARY` qualification.

## Safety boundary

No canary, production deployment, physical test, seal creation, seal mutation,
release/tag publication, merge, approval, human attestation, or live/private
evidence access is authorized by this document or branch.

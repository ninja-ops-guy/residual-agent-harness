# V1 PR-G28 release dependency lock contract

Status: **REPOSITORY PREPARATION / PR-G28 NOT VERIFIED**

## Observed current-main gap

At `main@d796f36b75e730a0bab71bdba564206174393719`, `pyproject.toml`
contains release-relevant dependency ranges including:

- build requirement `setuptools>=68`;
- runtime `defusedxml>=0.7.1,<1`;
- optional runtime `cryptography>=43` and `PyYAML>=6`.

No `uv.lock`, `poetry.lock`, or release requirements lock is present on
accepted main. Qualification installs dependencies from the network using
`pip install '.[factory,qualification]'`, and the wheel build uses
`pip wheel . --no-deps`.

Therefore current evidence does not establish PR-G28's acceptance claim:
a reproducible/offline release build from a complete hash-locked dependency set.

## This proposal

`scripts/validate_release_lock.py` defines a deliberately narrow fail-closed
contract for a future generated release lock:

- every logical dependency entry must use exact `==` pinning;
- every entry must carry at least one SHA-256 hash;
- duplicate normalized project names are rejected;
- editable, URL, and VCS/direct-source entries are rejected by this v1 contract;
- missing/empty lock input is an error.

The validator is stdlib-only and performs no network access, resolution,
installation, or dependency generation.

## Non-claim

This branch intentionally does **not** add `requirements-release.lock`.
Creating authoritative lock bytes requires dependency resolution and artifact
hash acquisition, which this task is not authorized to download/install.
Inventing pins or hashes would be false evidence.

A passing synthetic validator test means only that the proposed lock grammar is
enforced. It does not make PR-G28 VERIFIED.

## Remaining PR-G28 acceptance work

1. Owner/release reviewer selects the exact supported Python/platform build
   matrix and whether optional `factory`/`marketplace` dependencies are in
   the v1 release artifact.
2. In a separately authorized dependency-resolution environment, generate the
   complete transitive lock from the selected release inputs.
3. Retain hashes for every allowed distribution artifact and review the lock.
4. Prove installation/build with network disabled and hash enforcement enabled.
5. Build twice from the same source+lock in clean supported environments and
   compare the release artifacts under the project's reproducibility policy.
6. Bind the accepted lock digest and resulting artifact digests into the exact
   release candidate evidence.
7. Merge only after normal review, then requalify resulting main.

## Test command

`python -m unittest -v tests.test_release_lock_contract`

No dependency downloads, installs, canary, production action, tag, release,
attestation, merge, or frozen-evidence mutation are authorized by this proposal.

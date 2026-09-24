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

## PAR-20260924-D grammar repair

The original parser at `1403429dbdcb3abf04bcb1fb75fd1a2bad93cfbc`
accepted a wildcard version, dot/hyphen duplicate aliases, ignored trailing
text, and a URL-shaped version. The earlier report is retained at
https://github.com/ninja-ops-guy/residual-agent-harness/pull/444#issuecomment-5818161454 .

The repaired validator consumes every token. Its supported input is deliberately
narrower than pip's general requirements format:

- ASCII project names start/end with an alphanumeric character; comparisons
  normalize every run of `-`, `_`, and `.` to one hyphen and lowercase the name.
- Versions use `[N!]N(.N)*[{a|b|rc}N][.postN][.devN]`, where each N is a
  nonnegative decimal integer without leading zeros except zero itself.
  Optional local labels use `+` and lowercase alphanumeric dot-separated segments.
  Wildcards, legacy/version aliases, URLs and ranges are not accepted.
- Each subsequent token is exactly `--hash=sha256:` plus 64 lowercase hex digits.
  At least one such token is mandatory; any unconsumed token rejects the entry.
- Spaces/tabs, LF/CRLF, blank lines and standalone comments are supported.
  A continuation backslash must follow whitespace after a complete token;
  unterminated, blank/comment-interrupted and token-splitting continuations fail.
- Environment markers, extras in names, inline comments, source/index options,
  included requirement files and other pip directives are not supported.
  Generate a separately approved concrete lock per support-matrix target when
  required; never silently drop unsupported syntax from a supplied lock.
- Invalid, unreadable or undecodable input fails with a typed error. The CLI
  returns exit 2 and BLOCKED, with no PASS output, for these contract failures.

This is a validation grammar, not a version resolver or a general PEP 440
normalizer. Hash syntax does not authenticate package bytes, prove transitive
closure or establish an offline/reproducible build. All parent PR-G28 gates above
remain unchanged.

Primary syntax references:
https://packaging.python.org/en/latest/specifications/name-normalization/
https://packaging.python.org/en/latest/specifications/version-specifiers/
https://pip.pypa.io/en/stable/topics/secure-installs/

Run the original and additive adversarial suites together:
`python -m unittest -v tests.test_release_lock_contract tests.test_release_lock_adversarial`

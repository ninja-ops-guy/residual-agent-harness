# Funding-readiness export review — 2026-09-24

Review base: PR #391 at `55e0cd6e60af500f421c863003158268c0279907`.
Status: export repair proposed; funding and commercial readiness NOT certified.

## Repaired by this change

The old exporter recursively selected working-directory files. Untracked files,
ignored local configuration, staged changes and symlinks were not confined to a
reviewed commit. Prefix-only checks did not reject path traversal or malformed
manifest entries. Its archive metadata was not deterministic and existing output
could be overwritten.

The replacement reads the manifest and all archive members from one resolved Git
commit, rejects noncanonical paths, overlaps, duplicate JSON keys/roots, symlinks
and submodules, and never reads source payloads from the working directory. It
publishes a reproducible archive without overwriting an existing output. Its
receipt identifies the source commit, file count and archive SHA-256.

Local validation: 16 unittest cases passed against isolated Git fixtures. These
are tests of archive selection and publication only, not a full RESIDUAL suite run.
CI now triggers on exporter/test/workflow changes as well as source and metadata.

## Unresolved before runnable Open Core claims

At the review base, `residual/loop.py` is included by the license manifest but
imports `residual/lifecycle.py`, which is not included. The manifest also omits
`pyproject.toml`, `residual/__init__.py`, and the project entry-point files. The
export is therefore not established as a standalone installable, dependency-closed
Open Core distribution. Repository-wide test success does not test that boundary.

Do not add these files to the license manifest mechanically. First classify
ownership, commercial scope and transitive dependencies, then obtain explicit
owner approval for any expansion and test the extracted distribution in isolation.
This change does not modify the license text or either licensing manifest.

## Funding claim gates

- Reconcile PR #391 with current main and obtain fresh exact-head human approval.
- Verify the full canonical license text and rights to the covered material.
- Review historic public license proposals, not only what merged to main. Closing
  a PR does not establish that prior public licensing had no legal effect.
- Retain existing notices and third-party licenses; a DCO is not an IP assignment.
- Establish a runnable, clearly scoped public research package and accurate
  adoption evidence. Do not replace missing users with PR/test counts.
- Mark program eligibility, actual submission receipts and awards separately.
- Do not duplicate earlier applications or charge the same expense twice.

Public-source reference for GitHub fund eligibility:
https://github.com/open-source/github-secure-open-source-fund

The published criteria include a clear open-source license, demonstrated community
traction/adoption and participation commitments. This PR does not establish those.
No license-boundary expansion, history rewrite, release, grant submission,
maintainer attestation, or main-branch mutation is performed by this change.

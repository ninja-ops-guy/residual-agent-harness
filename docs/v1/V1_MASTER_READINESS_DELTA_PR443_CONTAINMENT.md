# V1 master readiness delta — PR-G26 symlink containment repair

Status: **APPEND-ONLY EVIDENCE / PR-G26 BLOCKED / NOT VERIFIED**

Observation date: 2026-09-24. This delta does not authorize acceptance, merge,
canary execution, seal creation, release, or modification of private evidence.

## Exact observed identities

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- ledger head observed before this append:
  `4e648c6d13f6fa6004afab4f7e9b6bb927f3a98e`
- retained #443 pre-repair head:
  `d4af45bd07abf96d60c834c060395e5619731583`
- repaired #443 head:
  `4d70ddc7902237f4b7d1bd60ff1c82bd834e90a4`
- repaired #443 tree: `59bb37151bdda4434531557f33d38cef8cca178a`
- verifier blob: `d29f245c9d25668df23f95c1bce7874da7080321`
- verifier SHA-256:
  `fe36e3a00e2b3d6233e0029ddf60aec4b5963e9df082a59d7c88e11be4a9f00e`
- expanded adversarial-test blob: `00cd13a62aefbd14e8d2aeabdb0e8a2bb4b4c0b5`

## Finding retained, not erased

The original verifier blob `941c653db3784761a3f3379f329e7cb7419ac15d`
was reproduced byte-exact in a disposable local environment. Both a direct file
symlink and a symlinked parent directory caused the verifier to hash matching
bytes outside the package and return PASS. The original 11 tests passed despite
this gap. This is an implementation defect in filesystem containment, in
addition to the missing qualification caveat in #364. Earlier broad wording
such as "rejects unsafe entries" must not be read as proof of containment on
the original head.

## Narrow repair

#443 now walks referenced directory components relative to one anchored root
file descriptor, uses O_NOFOLLOW at each component, validates regular-file type
on the opened descriptor, and hashes that descriptor. Internal/external symlinks
and a symlinked manifest fail closed; directory/FIFO targets are rejected.
Canonical POSIX-name checks reject aliases. The manifest digest is computed
from the same bytes used for parsing and cardinality, not from a later reopen.

The package root remains caller-selected/trusted and must be stable. Verification
requires an immutable snapshot and secure descriptor-relative/no-follow support;
unsupported platforms fail closed. This is not a mount/hard-link closure,
concurrent-content immutability, closed-world membership, semantic seal binding,
or provenance-DAG proof.

## Executed local validation

Linux/Python 3.13.5; published source/test blob identities checked against tested
bytes. Command:

`python -m unittest -v tests.test_r4_seal_manifest tests.test_r4_seal_manifest_adversarial`

Result: **26 tests PASS, zero failures, zero errors, zero skips**. The original
11 checks are retained and 15 containment tests were added. These include
leaf/parent substitution immediately before open and retention of an already
opened directory descriptor across pathname replacement. Local focused evidence
is not full hosted qualification or independent human review.

## Fresh hosted evidence observed on the repaired head

- clean install `36027756115`: PASS;
- Factory ownership `36027756068`: PASS;
- Control Plane `36027755898`: PASS;
- measured-evaluation binding `36027755923`: PASS;
- Qualification-v1 `36027756278`: IN_PROGRESS at this observation;
- controller/provider `36027755996`: IN_PROGRESS at this observation;
- Command Station `36027756038`: IN_PROGRESS at this observation;
- PR-Agent `36027755998`: FAIL at advisory review; configured-secret preflight
  passed and substantive-publication verification was skipped;
- maintainer approval `36027756119`: policy self-tests passed; explicit
  exact-head maintainer approval requirement failed.

No predecessor PASS is transferred to changed bytes. No advisory retry or human
attestation was issued by this remediation. Later terminal results require a
new observation; this append must not be rewritten to erase the pending state.

## Dependencies and readiness disposition

#443 repair: **IMPLEMENTED / LOCAL FOCUSED PASS / HOSTED REQUALIFICATION PENDING /
UNMERGED / UNACCEPTED** at the observed head.

PR-G26 parent: **BLOCKED / NOT VERIFIED**. Independent review/freeze of the
verifier, explicit package-closure policy, private authoritative runtime and
Seal v2 read-only semantic/provenance verification, and independently retained
sanitized evidence remain required.

V1-CLAIMS-001/#445, PR-G28/#444, V1-PC-002..004, deployment-profile approval,
AUD-1/#353, physical F6-A/F6-B, Mason/LEGION re-audit, canary, exact-RC recovery,
incident drills, elapsed soak, release/tag and production acceptance do not
advance through this change. Existing deltas remain retained. Frozen R4.1
candidate/runtime/seals and #415/#422 source branches were not modified.

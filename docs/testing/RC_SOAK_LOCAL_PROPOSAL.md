# RC soak local proposal: manifest-admission slice (fourth review revision)

Base main: 8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2.
Ledger #534: 3107b975a6b47bce2a520a359937542c37d8ec2e, read-only, not implementation base.
Three added repository files: scripts/qualification_rc_soak.py,
tests/qualification/test_rc_soak.py and this document. Existing twelve-file
freshness repair and four original soak source/test files remain unchanged.

Exact specification remains unread locally after the recorded Library helper
download failure. Reviewer-provided SHA-256:
72a94c6865c4442b8924076ac78cfa87fba5398c4d45fd440ddb26dd88f28638.
This is not a locally verified specification hash.

## Current slice: externally selected manifest admission

No publisher, observation driver loop or supervisor change in this slice.
CLI admission now additionally REQUIRES --manifest, --manifest-sha256 and
--inputs-root. Existing flags remain, but must match the manifest's source,
artifact, configuration path, profile, adapter and complete profile policy.
Missing caller expectations fail; they are never adopted from an evidence
journal or whatever configuration happens to be present. The low-level Binding
constructor now requires expected_configuration_sha256 (canonical JSON) and
expected_configuration_bytes_sha256; omission deliberately raises TypeError.
The preferred path is SelectedManifest.load followed by Binding.from_selected_manifest.

Schema residual.rc-soak.manifest.v1 requires exactly:
- source: head/tree, each lowercase 40-hex;
- artifacts: 1..32 unique id/kind/path/sha256/source records, with a selected
  candidate_artifact identifying one wheel; each source must agree;
- configuration: relative path, exact byte sha256, canonical_sha256;
- profile: relative path, exact byte sha256, id;
- runner: expected script sha256;
- adapter: module, expected source sha256, candidate artifact_id;
- environment: declared os/architecture, python implementation/version/executable
  hash, explicit dependency name/version/artifact hash records.

Profile schema residual.rc-soak.profile.v1 requires exactly id,
configuration_sha256 (configuration bytes), and complete externally expected
policy. No production values are provided. Runtime configuration remains an
opaque JSON object bound by both byte and canonical hashes; runtime-specific
settings schemas are not invented by this generic admission layer. Duplicate
keys are rejected at every depth in manifest/config/profile JSON. Unknown fields
in the manifest/profile/declaration schemas, missing facts, mismatched hashes,
contradictory identities and unsafe portable relative paths fail closed.

Canonicalization is this version's Python JSON encoding: UTF-8, sorted keys,
compact separators, default ASCII escaping, finite numbers; it is NOT a claim
of RFC 8785/JCS compatibility. Only whitespace/key order are irrelevant for the
manifest digest. Configuration and profile byte digests remain exact. Bounds:
64 KiB JSON inputs, depth 16, 1024 collection entries, 256-character keys,
4096-character strings, signed 64-bit integers; at most 256 declared dependencies.
Artifact input reads are capped at 256 MiB each. Traversal, absolute/drive/UNC/ADS
paths, backslashes, empty segments, reserved Windows names, symlink/reparse
ancestry and overlapping input roles are rejected. OS path immutability remains
unproved; hashes are observation checks, not storage locks.

SelectedManifest is immutable, validates its captured canonical digest even on
direct construction, returns copies of facts and rechecks selected files for
drift. Stable binding identity includes manifest/profile/configuration/adapter
and declared-environment digests. Runner/adapter byte comparisons are enforced.
Source HEAD/TREE and interpreter/dependency facts are DECLARATIONS, not measured
source provenance or dependency attestation. Caller selection is not owner
approval. provenance_status=not_independently_established,
external_attestation_status=not_established,
prerequisite_authority_status=not_established, and rc_qualified=false remain.

Current final-byte run: 49 discovered, 47 PASS, two explicit actual-seal skips,
exit 0 and actual_os_link_calls=0. Breakdown: 13 new manifest tests PASS;
23 prior proposal tests PASS plus two blocked skips; 11 original soak tests PASS.
Four short CLI subprocess fixtures reject invalid admission only. No actual
driver campaign or publication was exercised. Use the exact command below with
fixture directory rc-soak-fixtures-manifest-v3 instead of rc-soak-fixtures-review-v2.
Initial, intermediate and final logs are retained. Initial run: one fixture assertion
failed because the unsafe-wheel fixture restored {} instead of its explicitly
expected configuration; correcting test bytes restored the intended check.
A final distinct regression verifies that a profile substituted after its file
read cannot replace the hash-verified policy: parsing uses the exact verified
bytes, not a second file read. A later continuity check rejects persistent drift.

Focused fixtures cover canonicalization/digest selection, post-selection drift,
missing/unknown/duplicate fields, path and JSON bounds, wrong source/artifact/
runner/adapter/profile, dependency declarations, absent attestation states,
direct-construction mismatch, CLI overrides and unrelated synthetic journal/
ledger files attempting to replace selected requirements. Fixture values are
synthetic and not approved production thresholds.

## Previously reviewed repairs retained

Nonexecuting admission validates the complete selected candidate inventory,
adapter, startup paths and forbidden caches. Candidate Python code is imported
from bounded hash-verified captured bytes, preventing source substitution between
admission and use through this loader. Actual origin/current installed-byte checks
remain. Execution is explicitly verified_source_snapshot, not an installed-native
claim. Real CLI synthetic children reject tampered initializer/adapter/cache
without side effects. Accepted observations are copied, not adapter-owned aliases.

## Current bounded repairs

1. Journal.fail no longer unlinks any terminal name. Publication ownership is
recorded only after confirmed exclusive publication and matching pending/terminal
file identity and digest. A failure can write an ownership-scoped revocation
record only while that exact object remains unchanged. Competing/preexisting or
substituted evidence is never deleted. There is no portable compare-and-unlink
race to claim away. Separate first-failure evidence makes the failed run
non-consumable; filesystem failures can still prevent durable recording.

2. Fault tests use the actual captured expected identity and epoch. Every injected
stage must assert it was reached. SyntheticJournal supplies a plainly labelled,
test-only exclusive-copy publisher; it does NOT model atomicity, hard-link
capability or durability. Production Journal.publish still calls os.link and
has no fallback. A test guard forbids calls to the denied primitive.

3. validate_observations and validate_sealed require externally expected complete
policy in addition to identity/epoch. Requirements are strictly validated;
unknown/missing/malformed fields fail. Journal policy and its digest must match
the caller's requirements; the terminal seal includes that digest. A short or
differently configured self-consistent run cannot satisfy a different consumer
policy. All numeric values in tests are synthetic, not production authorization.

4. Binding.observe separates stable candidate identity from evolving verified
module origins. Continuity accepts legitimate additional modules while retaining
prior verified origins and rejecting changed/missing ones. Every observation
revalidates loaded module paths, hashes, package search paths and installed bytes.
A real lazy-import regression passes; foreign-origin and modified-file negatives
fail as intended. The custom source loader's package-resource APIs, native
extensions, namespace packages and full application compatibility are unresolved;
this is not a claim of general runtime support.

Observation completion stays provisional. Sealing requires closed/read-back
evidence, byte hash, replay, identity/sequence/first-failure checks and externally
expected policy. Consumers must validate, never accept a COMPLETE-looking string.
All outcomes retain rc_qualified:false.

## Prior cleared-slice test run (preserved history)

From rc-soak-local-proposal, piped to python -B -:

```python
import os,tempfile,unittest
from unittest.mock import patch
fixture=r'C:\Users\jinis\Documents\Codex\2026-10-05\task-3\rc-soak-fixtures-review-v2'
tempfile.tempdir=fixture
os.environ['TMP']=fixture
os.environ['TEMP']=fixture
suite=unittest.defaultTestLoader.discover('tests/qualification',pattern='test_*soak.py')
with patch.object(os,'link',side_effect=AssertionError('DENIED_PRIMITIVE_MUST_NOT_BE_RETRIED')) as forbidden:
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print('actual_os_link_calls='+str(forbidden.call_count))
    forbidden.assert_not_called()
raise SystemExit(not result.wasSuccessful())
```

Exit 0. 36 discovered: 25 new tests (23 PASS, 2 explicit skips), 11 existing
regressions PASS (four long-soak, seven process-soak). No failures.
actual_os_link_calls=0. Skips / NOT RUN:
- BlockedActualSealTests.test_actual_terminal_publication_and_consumption
- BlockedActualSealTests.test_actual_postpublication_faults

Sealing success, postpublication fault logic and tamper consumer tests used only
the synthetic test publisher. They do not clear actual filesystem publication.
Three short Python subprocesses exercise actual admission rejection against
synthetic fixtures; no RESIDUAL/native campaign, service/socket, provider,
installation, workflow or remote publication was executed.

## Prior failures preserved, not superseded by synthetic PASS

Library v0/v1 bundles, patches, hashes, available original failure excerpts, both
previous full-suite failures and the exact hard-link denial are retained.
The prior final full suite exited 1: 20 new tests, 18 passed, two failed methods
(seven assertions/subtests), plus 11 existing passes. Terminal publication
os.link raised PermissionError [WinError 5] inside the authorized workspace.
No retry or alternative production publication operation occurred this turn.
The original AppData errors were OS errors, not a blanket tool-policy refusal.
Original full output was tool-truncated; excerpts are identified as excerpts.

## Separate design and unresolved gates

RC_SOAK_PORTABLE_FINALIZATION_DESIGN.md in the review bundle is design-only and
separately reviewable. It specifies capability selection before a new run,
exclusive ownership, expected-policy validation, crash/durability limits and
stop-on-denial behavior. No portable backend or automatic fallback is implemented.

Remaining: manifest/profile selection authority and source-artifact provenance;
bound installation/root, dependency/interpreter identity, in-memory tampering and
change-and-revert protection; actual target supervision and attributable workload
outcomes; independent driver timeout; source/probe/slope integration; actual
successful seal and platform/durability testing; exact specification consumption;
reviewed runtime adapter and production values; uninterrupted finalRC24h campaign.

Counters/effective configuration are trusted adapter assertions; resources and
alive describe the observer, not independently supervised descendants. Hash seals
are not authentication or power-loss guarantees. No broader specification
completion, human attestation or qualification PASS is claimed.

# V1 recovery evidence boundary repair

Status: PROPOSED / LOCAL TESTS PASS / HOSTED QUALIFICATION PENDING / UNMERGED.
This is repository-side release preparation, not an executed recovery exercise,
independent human review, approval receipt, or release authorization.

## Ownership and source

This focused current-main-based successor carries the #435 recovery validator
with a bounded JSON/numeric correction. Original #435 is unchanged. Review this
as a successor proposal for its validator, not a second independent recovery
program; do not integrate overlapping proposals without reconciliation.

- accepted-main base: `d796f36b75e730a0bab71bdba564206174393719`;
- #435 source head: `378207e511550532dbba60e8d4ae489666aa6c09`;
- original validator blob: `9faf9306cf86434bc412142efdbbbdb34703f2fb`;
- original validator SHA-256: `814a3373f497dbda169ba60a76dbaca876016d54282ca60586e8d2749b1724e6`;
- unchanged original ten-test blob: `aa0624885b419629ef449128e9bb09a00ede5df5`.

The existing recovery contract remains the requirement source:
https://github.com/ninja-ops-guy/residual-agent-harness/blob/378207e511550532dbba60e8d4ae489666aa6c09/docs/v1/V1_RECOVERY_QUALIFICATION.md

Owner: v1 repository-release-preparation lane. This change has no overlap with
AUD-1/F6, Shared Comms runtime, Docs Watch, frozen research, or archive extraction.
The live PR search and #435 comments were inspected before starting; no competing
recovery-validator repair was found in those inspected results. No claim of an
exhaustive global ownership audit is made.

## Observed findings and bounded correction

| ID | Observed predecessor behavior | Required corrected behavior |
| --- | --- | --- |
| REC-JSON-01 | NaN could bypass RPO/RTO comparison; positive Infinity could invalidate an objective while returning PASS. Default JSON parsing also admitted nonstandard constants and overflowing exponent values. | Reject non-finite known metrics through the direct API and non-finite numbers/constants throughout raw JSON input. |
| REC-JSON-02 | Duplicate JSON members silently used the last value, allowing an earlier false approval, unobserved execution claim, or invalid metric to disappear. | Reject duplicates at every object depth, including escaped-equivalent names and identical repeated values. |
| REC-NUM-03 | Converting integers to float erased a one-unit breach at `2**53 + 1` relative to `2**53`. Very large integers raised untyped overflow errors. | Preserve integer comparison precision and retain FAIL for a finite measured breach. |
| REC-INPUT-04 | Invalid UTF-8 caused an unstructured CLI traceback; non-object direct API input raised AttributeError. | Preserve typed EvidenceError / CLI BLOCKED behavior for these invalid inputs. |

The repair retains all existing backup/restore/rollback requirements, secret-key
checks, status distinctions, and `execution_claim: VALIDATION_ONLY`. It introduces
no runtime dependencies, no objective defaults, no new operation, and no waiver.
Ordinary finite floating-point values retain Python float semantics; arbitrary
precision decimal arithmetic is not claimed.

## Retained local reproduction

Environment: Linux x86_64, Python 3.13.5. Exact-file source projection, not a full
repository checkout. Original source and test bytes were reconstructed from the
connected GitHub reads and independently matched to the Git blob identities
above before execution. No dependency was installed or downloaded.

- Original ten tests: 10 PASS, zero skips.
- New adversarial tests against original source: 23 methods, 31 failed
  assertions/subtests and 6 errors; exit 1. Positive controls remain in the suite.
- Repaired source with the same original and adversarial test bytes: 33 methods
  PASS, zero skips; exit 0.
- The first negative-suite invocation hit the outer 20-second tool timeout. Its
  partial failure log is retained separately. A 90-second outer allowance let
  the same bounded suite finish with failures; this was not a green-seeking
  rerun or an altered oracle. Each individual CLI subprocess is limited to 10s.

Commands:

```sh
python -W error::ResourceWarning -m unittest discover -s tests -p 'test_v1_recovery_evidence.py' -v
python -W error::ResourceWarning -m unittest discover -s tests -p 'test_v1_recovery_evidence_adversarial.py' -v
python -W error::ResourceWarning -m unittest discover -s tests -p 'test_v1_recovery_evidence*.py' -v
```

Published code/test blobs were read back and match the locally tested bytes:

- corrected validator: `26dcfadcec681bac6b631237572709224c7d9dae`;
  SHA-256 `b52d5aa1f5c6d4396dd92ab1663240808aa80c54824210f9f9cb10a9695c3753`;
- unchanged original tests: `aa0624885b419629ef449128e9bb09a00ede5df5`;
- new adversarial tests: `ebdd04781e459f4ff93861c59a06609225734a4b`;
  SHA-256 `038a4f46738d99b4afa775d44abdb95951bdd9e9be27fd390ea98e95f468c2d4`.

Retained local log SHA-256 identities:

- original ten-test result: `556b5f8671592dd4801d1e3d36741b3047ec8cbc8ddc43035a5a9e2e8252afa9`;
- interrupted negative run: `039d17f72dcf74e36ba7703ae0c3ab8e423e892e0f90f53f9b82e5de16d6f3ac`;
- completed predecessor negative result: `4b98590496f1011847809aff6226b2a313f5c2f23136d31b3cce251d49161e8e`;
- repaired 33-method result: `1cee3355d94706b6a3d2857140ecebd8be2148fd272736f2620fc64eddc5fb51`.

These hashes identify retained local logs, not GitHub-hosted artifacts. The test
fixture's OBSERVED/approval fields are deliberately synthetic parser inputs;
no real exercise or human approval is established by them.

## Acceptance and limits

Fresh exact-head CI and human review remain required. No #435 CI result transfers
to this changed proposal. PR-G07 / PR-G21 remain BLOCKED until the approved
profile, exact selected RC, separately authorized production-shaped exercises,
independent evidence and genuine human qualification exist.

This correction does not authenticate the supplied approval/profile/index,
cryptographically establish measurement provenance, execute restore/rollback,
or prove the underlying operational claims. The validator alone cannot turn a
self-described observed fixture into accepted production evidence. Existing
semantic, timing, provenance, and deployment-profile acceptance obligations
remain outside this bounded parser repair.

No main push, merge, auto-merge, attestation, helper change, physical F6, canary,
private seal action, provider workload, live service/credential change, recovery
exercise, elapsed soak, deployment, tag, release, or schedule change occurred.

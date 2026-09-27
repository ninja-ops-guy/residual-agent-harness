# RESIDUAL v1 Release Runbook

**Status:** PREPARATION DRAFT — not release authority  
**Purpose:** define the serial handoff from a feature-frozen v1 candidate to an authorized v1.0.0 release.

This runbook complements `docs/testing/QUALIFICATION_V1.md`. It does not replace Qualification v1, maintainer attestation, AUD-1/F6 evidence, or claim-specific independent review.

## 1. Identity rule

Every release-stage receipt MUST bind the same exact candidate identity: source commit SHA, source tree SHA, promoted artifact digest where applicable, environment identity, and command/gate identity.

Evidence bound to another SHA or tree is historical. It may explain provenance but MUST NOT satisfy an exact-candidate gate.

The artifact that is qualified is the artifact that may be promoted. Rebuilding after artifact qualification invalidates artifact-level qualification.

## 2. Feature freeze

Once the owner declares a proposed v1 tree feature-frozen:

- no new feature work enters v1;
- a source change requires a demonstrated mandatory-gate defect and explicit freeze break;
- the failed predecessor remains retained evidence;
- the successor receives a new HEAD/TREE and reruns every affected gate.

## 3. Candidate qualification

Before product freeze, require:

1. complete exact-head Qualification-v1;
2. independent composed-tree review;
3. execution of every supported v1 D3 matrix cell;
4. supply-chain/reproducibility closure;
5. Open Core/license-boundary reconciliation;
6. deployment-profile admission;
7. version consistency;
8. exact-artifact clean-install qualification.

A green predecessor or component PR does not qualify the composed candidate.

## 4. Product and F6-helper freeze

After candidate qualification, freeze the exact product HEAD/TREE. Bind the final F6 helper to that exact identity, qualify it on required Linux/Windows surfaces, independently review it, then freeze helper HEAD/TREE only if those checks remain bound to unchanged bytes.

Physical F6 is a later gate; helper qualification is not F6 execution.

## 5. Physical AUD-1 F6

Run F6-A and F6-B as distinct real-host cases with distinct evidence roots.

Require exact frozen identities, real process/runner identity, real authority/lease/grace intervals, first-failure preservation, no manufactured ownership/reassignment/transport failure, immutable manifests, and independent post-execution adjudication.

The executing lane MUST NOT grade its own release disposition.

## 6. Live hosted-provider gate

The selected v1 hosted-provider claim requires one bounded real provider campaign on the exact frozen candidate.

Retain provider/model identity, candidate HEAD/TREE, credential source name but never value, latency/usage/response identity when available, negative credential/model controls, and explicit proof that local/demo fallback did not masquerade as hosted success.

A successful provider request is not a model-quality claim.

## 7. Resulting-main qualification

After accepted integration, qualify the exact resulting `main` revision. Candidate-branch qualification is historical once integration produces different bytes/tree identity.

Do not select an RC until resulting-main mandatory gates are green.

## 8. RC selection

RC selection is an explicit human action. Record RC commit/tree, promoted artifact digests, qualification-manifest digest, and known limitations/non-claims.

Any source-byte change after RC selection creates a successor RC.

## 9. Operational qualification and soak

Run the exact-RC operational campaign:

`install → bootstrap → workload → checkpoint → restart → crash → recovery → backup/restore → rollback → integrity → soak`

Qualification-v1 already defines a 24h uninterrupted release soak, a 72h extended tier after 24h is clean, and 30d as separate long-duration operational evidence.

Product failure or RC byte change invalidates the release soak for that RC. Infrastructure failures require explicit classification.

## 10. Release packet

Before release authorization, assemble one reviewable packet containing source identity, wheel/container hashes, SBOM, provenance/attestation, reproducibility/offline-install evidence, Qualification-v1 manifest, D3 receipt, F6 bundles and adjudication, hosted-provider receipt, recovery/rollback/soak receipts, Open Core/license boundary, changelog/release notes, known limitations, and retained first-failure references.

## 11. Human release authorization

Only the owner/maintainer authorizes final integration disposition, product/helper freeze, physical F6, RC selection, and release tag/publication.

Automated green checks are evidence, not release authority.

## Stop conditions

Stop the release line on HEAD/TREE drift, missing mandatory evidence, FAIL/UNKNOWN on a required gate, unsupported cells presented as PASS, artifact rebuild after qualification, unexplained secret retention, weakened security expectations, or unresolved release-blocking independent-review findings.

Preserve the first failure and classify it before any successor is created.

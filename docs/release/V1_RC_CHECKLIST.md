# RESIDUAL v1 RC Checklist

**Status:** TEMPLATE — complete only against one exact candidate.

## A. Proposed product candidate

- [ ] Feature freeze is active.
- [ ] Product HEAD recorded: `<pending>`
- [ ] Product TREE recorded: `<pending>`
- [ ] Candidate worktree is clean.
- [ ] All accepted convergence resolutions are recorded.
- [ ] Historical/synthetic predecessor trees are retained as historical evidence.
- [ ] No unresolved mandatory-gate product defect.

## B. Exact-head qualification

- [ ] Qualification-v1 PASS on exact HEAD/TREE.
- [ ] Independent composed-tree review has no unresolved release-blocking finding.
- [ ] Windows x64 native PASS.
- [ ] Linux x64 native PASS.
- [ ] Linux Docker Engine PASS.
- [ ] Docker Desktop Windows PASS.
- [ ] NVIDIA Compose overlay PASS.
- [ ] Chromium PASS.
- [ ] Firefox PASS.
- [ ] WebKit PASS.
- [ ] Local Ollama PASS.
- [ ] Supply-chain closure PASS.
- [ ] Open Core boundary PASS.
- [ ] Deployment-profile admission PASS.
- [ ] Version consistency PASS.
- [ ] Exact-wheel / clean-install PASS.
- [ ] Reproducible-wheel receipt PASS.

A skipped, missing, historical, or differently-bound result does not satisfy a required item.

## C. Final F6 helper

- [ ] Helper is rebound to the exact frozen product HEAD/TREE.
- [ ] Helper HEAD recorded: `<pending>`
- [ ] Helper TREE recorded: `<pending>`
- [ ] Linux helper qualification PASS.
- [ ] Windows helper qualification PASS.
- [ ] Independent helper review PASS.
- [ ] Helper bytes unchanged after qualification.
- [ ] Physical F6 has not been conflated with helper qualification.

## D. AUD-1 physical F6

- [ ] Owner separately authorized physical F6.
- [ ] F6-A used a unique evidence root and real timing/authority intervals.
- [ ] F6-A bundle frozen and verified.
- [ ] F6-B used a separate unique evidence root.
- [ ] Natural expiry/recovery/reassignment evidence retained.
- [ ] Stale-result rejection evidence retained.
- [ ] F6-B bundle frozen and verified.
- [ ] First failures preserved.
- [ ] Independent F6 adjudication PASS.
- [ ] Product/helper identities match the frozen candidates.

## E. Hosted-provider gate

- [ ] Owner selected provider family.
- [ ] Owner selected exact model/deployment.
- [ ] Candidate HEAD/TREE bound.
- [ ] Missing-credential negative control PASS.
- [ ] Invalid-credential classification PASS.
- [ ] Invalid-model/deployment classification PASS.
- [ ] Bounded real hosted-provider request PASS.
- [ ] Provider/model identity retained.
- [ ] Usage/latency/request evidence retained where available.
- [ ] No local/demo fallback masqueraded as hosted success.
- [ ] No credential value retained in evidence.

## F. Resulting-main qualification

- [ ] Accepted integration completed.
- [ ] Resulting main HEAD/TREE recorded.
- [ ] Resulting-main mandatory gates PASS.
- [ ] Candidate-branch evidence is not being substituted for changed resulting-main bytes.
- [ ] No release-blocking status/document drift remains.

## G. RC selection

RC selection is an explicit human action.

- [ ] RC HEAD: `<pending>`
- [ ] RC TREE: `<pending>`
- [ ] Promoted wheel digest: `<pending>`
- [ ] Promoted container digest: `<pending>`
- [ ] Qualification-manifest digest: `<pending>`
- [ ] Known limitations reviewed.
- [ ] Deferred support cells explicitly not claimed.
- [ ] Owner recorded RC selection.

Any source-byte change after selection creates a successor RC.

## H. Exact-RC operational campaign

- [ ] Install/bootstrap PASS.
- [ ] Bounded workload PASS.
- [ ] Persistent checkpoint PASS.
- [ ] Clean restart PASS.
- [ ] Crash/recovery PASS.
- [ ] Backup/restore PASS.
- [ ] Rollback PASS.
- [ ] Integrity verification PASS.
- [ ] No unrecovered process/resource leakage.

## I. Soak

- [ ] 24 continuous hours completed on unchanged RC bytes.
- [ ] Zero integrity failures.
- [ ] Zero authority violations.
- [ ] Zero duplicate accepted work.
- [ ] Zero evidence-chain corruption.
- [ ] Zero unexplained secret retention.
- [ ] No unresolved release-blocking failure.
- [ ] Resource/disk behavior remains within declared bounds.

A product failure or RC byte change resets the required release soak. A 72-hour extended tier may continue as additional confidence evidence after the 24-hour release soak passes.

## J. Release packet

- [ ] Wheel/container hashes.
- [ ] SBOM.
- [ ] Provenance / artifact attestation.
- [ ] Offline constraints/wheelhouse receipt.
- [ ] Qualification-v1 final manifest.
- [ ] D3 matrix receipt.
- [ ] F6-A/F6-B + independent adjudication.
- [ ] Hosted-provider receipt.
- [ ] Recovery/rollback/soak receipts.
- [ ] Open Core/license manifest.
- [ ] NOTICE / third-party attribution.
- [ ] Changelog / release notes.
- [ ] Known limitations.
- [ ] Failure ledger / retained predecessor failures.
- [ ] Evidence index complete.

## K. Release authorization

- [ ] No unresolved required-gate FAIL/UNKNOWN/NOT_RUN.
- [ ] Artifact being published is byte-identical to the qualified/promoted artifact.
- [ ] Owner performs final release disposition.
- [ ] `v1.0.0` tag points to the selected RC identity.
- [ ] Publication receipt retained.

**Automated green checks are evidence, not release authority.**

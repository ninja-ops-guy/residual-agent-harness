# RESIDUAL v1 Release Checklist

**Status:** PREPARATION DRAFT — checklist items are evidence gates, not claims of completion.

## A. Freeze proposed product candidate

- [ ] Exact product HEAD recorded
- [ ] Exact product TREE recorded
- [ ] Feature freeze declared
- [ ] First-failure history linked
- [ ] No unresolved source drift

## B. Exact-candidate qualification

- [ ] Qualification-v1 PASS
- [ ] Independent composed-tree review complete
- [ ] D3 required matrix PASS
- [ ] Supply-chain closure PASS
- [ ] Reproducible wheel PASS
- [ ] Exact wheel/clean install PASS
- [ ] Open Core boundary PASS
- [ ] Deployment profile PASS
- [ ] Version consistency PASS

## C. Final F6 helper

- [ ] Helper bound to exact product HEAD/TREE
- [ ] Linux helper qualification PASS
- [ ] Windows helper qualification PASS
- [ ] Independent helper review complete
- [ ] Helper HEAD/TREE frozen

## D. AUD-1 physical F6

- [ ] F6 authorization recorded
- [ ] F6-A executed and frozen
- [ ] F6-B executed and frozen
- [ ] First failures retained
- [ ] Independent F6 adjudication PASS

## E. Hosted provider

- [ ] Provider family selected
- [ ] Exact model/deployment selected
- [ ] Missing credential control PASS
- [ ] Invalid credential control PASS
- [ ] Invalid model control PASS
- [ ] Real bounded provider request PASS
- [ ] No fallback masqueraded as provider success
- [ ] No secret retained

## F. Resulting-main qualification

- [ ] Accepted integration landed
- [ ] Resulting main HEAD/TREE recorded
- [ ] Mandatory resulting-main qualification PASS
- [ ] No candidate-branch receipt substituted for resulting-main evidence

## G. RC selection

- [ ] RC HEAD/TREE selected by owner
- [ ] Artifact digests frozen
- [ ] Qualification manifest digest frozen
- [ ] Known limitations/non-claims frozen

## H. Exact-RC operations

- [ ] Blank/clean install
- [ ] Workload
- [ ] Restart
- [ ] Crash/recovery
- [ ] Backup/restore
- [ ] Rollback
- [ ] Integrity verification
- [ ] 24h release soak
- [ ] 72h extended soak or explicit pending/non-claim

## I. Release packet

- [ ] Wheel/container hashes
- [ ] SBOM
- [ ] Provenance/attestation
- [ ] Offline dependency receipt
- [ ] D3 receipt
- [ ] F6 receipt
- [ ] Hosted-provider receipt
- [ ] Recovery/rollback/soak receipts
- [ ] Open Core/license manifest
- [ ] NOTICE/third-party attribution
- [ ] Release notes
- [ ] Known limitations
- [ ] Evidence index

## J. Release authorization

- [ ] Final evidence packet reviewed
- [ ] Maintainer release authorization recorded
- [ ] Tag points to exact authorized RC
- [ ] Published artifacts match qualified artifact digests
- [ ] Post-publication verification retained

No unchecked item may be silently treated as PASS.

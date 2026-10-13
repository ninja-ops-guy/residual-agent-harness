# PR-G27 exact-head evidence record

Status: **READY_FOR_REVIEW / UNMERGED**

This appendix belongs to master release-readiness PR #427. It refines the PR-G27 row with exact-head evidence without authorizing merge, attestation, deployment, canary, release, or production mutation.

## Authority snapshot

- repository main: `d796f36b75e730a0bab71bdba564206174393719`
- implementation PR: #440
- implementation branch: `fix/v1-pin-github-actions`
- exact review head: `72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`
- implementation base: `main@d796f36b75e730a0bab71bdba564206174393719`
- master item: `PR-G27`
- classification: observed supply-chain finding + tested unmerged remediation
- owner: release/supply-chain maintainer; independent reviewer still required
- dependencies: exact implementation head; merge/requalification before production acceptance; broader SBOM/provenance/tamper-verification work remains applicable

## Requirement / acceptance criterion

Remove unjustified floating external GitHub Actions trust from release-critical workflows, retain the repository's selected action identities as immutable 40-hex commit SHAs, preserve existing workflow security contracts, and provide an exact-head deterministic audit with retained evidence.

This implementation advances only the immutable-action portion of PR-G27. It does **not** claim the entire PR-G27 gate complete: release artifact SBOM, signatures/provenance, dependency/artifact tamper verification, guarded integration, and resulting-main requalification remain separate acceptance work.

## Observed first failure and repair

The dedicated acceptance gate first failed on superseded head `15cb138...` because `qualification-v1.yml` still referenced `actions/attest-build-provenance@v2`. The successor kept the audit rule unchanged, resolved the repository's existing v2 selection to immutable commit `e8998f949152b193b063cb0ec769d69d929409be`, and added that identity to the reviewed pin set.

No assertion was weakened, no required test was skipped, and historical WebVM failures were not relabeled to make this lane green.

## Exact-head test / evidence

GitHub Actions on head `72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`:

- `GitHub Action Pin Gate` — SUCCESS, run `36002441103`
  - checkout/setup steps used immutable SHAs
  - `Verify immutable action pins and existing workflow security contracts` — SUCCESS
  - `Retain action pin evidence` — SUCCESS
- retained artifact: `10809311094`
- artifact digest: `sha256:aae9486453c8747b58b488ebc1860d03b7419a708158015bd0d6e6f58b3cf612`
- `RESIDUAL Qualification v1` — SUCCESS
- `Clean install qualification` — SUCCESS
- `Deploy GitHub Pages` — SUCCESS
- `Controller and provider contracts` — SUCCESS
- `Command Station checks` — SUCCESS
- `Factory ownership gate` — SUCCESS
- `Control Plane` — SUCCESS
- `Measured evaluation acceptance binding` — SUCCESS

The maintainer-approval gate is intentionally FAILURE because no human attestation was supplied. The WebVM discriminator/diagnostic workflows remain FAILURE and are preserved as a separate historical/runtime investigation rather than classified as PR-G27 failures. PR Agent advisory failure is not independent review evidence.

## Verification status

`READY_FOR_REVIEW`

The focused immutable-action remediation has exact-head passing acceptance evidence. It is not `VERIFIED` for production and cannot become `MERGED_AND_REQUALIFIED` until an authorized reviewer accepts the change, it is merged through normal governance, and the resulting integrated main is freshly qualified without stale-head evidence transfer.

## Required human action

1. Independently review #440 at exact head `72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`.
2. Confirm the immutable action identities match the intended upstream release selections and that the pin-set/audit workflow is acceptable.
3. Do not provide maintainer attestation until normal release/security review prerequisites are satisfied.
4. If later merged, run authoritative resulting-main qualification and then update PR-G27 to reflect only the evidence actually established on integrated main.

## Master-ledger reconciliation

The existing PR-G27 table row in `docs/v1/V1_MASTER_READINESS.md` still says `NOT_STARTED`; this appendix supersedes that status for the immutable-action sub-requirement and records the current state as `READY_FOR_REVIEW`. The parent PR-G27 production gate remains incomplete because the broader SBOM/provenance/tamper-verification and merged-main evidence requirements are not yet satisfied.

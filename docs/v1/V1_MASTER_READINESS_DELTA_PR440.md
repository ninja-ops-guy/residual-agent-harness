# RESIDUAL v1 master readiness delta — PR #440 supply-chain remediation

This append-only delta supersedes prior #440 identity notes. It does not authorize a canary, merge, physical test, deployment, attestation, tag, release, or modification of frozen R4.1/Seal v2 evidence.

Accepted main remains `d796f36b75e730a0bab71bdba564206174393719`.

## PR-G27 concrete remediation candidate

Draft PR #440 current exact head:

`15cb138784d52c4d88ce7e4efc0dd3d9e5bd179a`

The branch is stacked on review-ready #437 and therefore contains the fail-closed immutable-ref audit plus the workflow remediation.

Current proposal:

- replaces 61 checkout, 54 setup-python, 54 upload-artifact, 1 download-artifact, 6 setup-node, 1 configure-pages, 1 upload-pages-artifact, and 1 deploy-pages floating refs with reviewed immutable commit SHAs;
- retains the already immutable PR-Agent action;
- records the selected set in `docs/v1/V1_GITHUB_ACTION_PIN_SET.json`;
- keeps checkout credential persistence disabled and makes that regression independent of floating-tag syntax;
- requires an immutable deploy-pages ref in the Pages structural gate;
- adds a reviewed pin-set consistency regression;
- adds a dedicated `GitHub Action Pin Gate` that runs the immutable-ref audit and retains its JSON evidence.

A changed-workflow patch inspection found no added external `uses:` target with a mutable ref.

## Retained WebVM diagnostic red is not erased

The superseded #440 head re-triggered `WebVM runtime sleep process-scope discriminator` because the workflow itself was modified for pinning. Its `single-273` arm reproduced the existing guest-runtime defect:

`OverflowError: timestamp too large to convert to C _PyTime_t`

at positive `time.sleep(0.05)` call 273, while split/fresh-process arms passed. This is retained historical/runtime evidence first characterized by #133, not evidence that the immutable action pins broke execution.

Current main already routes production browser polling through `residual.workbench.browser_poll.pause()`, a bounded libc `usleep` path intended to avoid the CPython `_PyTime_t` conversion boundary. The raw sleep discriminator must not be weakened merely to make #440 green.

The new dedicated PR-G27 gate allows the supply-chain contract to be evaluated independently while preserving the red diagnostic.

## Status

All workflow/check conclusions on earlier #440 heads are superseded. Exact-head CI for `15cb138...` is currently queued/running, including the new GitHub Action Pin Gate. PR-G27 remains `IN_PROGRESS` until that exact head has retained pin-audit evidence and normal review.

All canary-scope, deployment-profile, AUD-1/physical, exact-RC recovery/rollback/soak, and final release-authority blockers remain unchanged.

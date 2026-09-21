# RESIDUAL Open Source Manifest

**License:** Apache License 2.0  
**Copyright:** 2026 Mike Olivares  
**Status:** Funding/readiness boundary v1

This document defines the open-source portion of the RESIDUAL development monorepo. A path is Apache-2.0 licensed only when it is explicitly included below or carries its own compatible license notice.

## Included open-core code

The following paths are included in RESIDUAL Open Core:

- `ai_providers/**`
- `observation_layer/**`
- `verifier/**`
- `residual/assurance/**`
- `residual/eval/**`
- `residual/eval_frozen/**`
- `residual/hitl/**`
- `residual/runtime/**`
- `residual/sandbox/**`
- `residual/trajectory/**`
- `residual/vq/**`
- `residual/brakes.py`
- `residual/core.py`
- `residual/evaluation.py`
- `residual/goalspec.py`
- `residual/loop.py`
- `residual/quarantine.py`
- `residual/receipts.py`
- `residual/study.py`
- `residual/study_tasks.py`
- `residual/verifier.py`

## Included research and reproducibility material

- `docs/research.md`
- `docs/station/RESEARCH.md`
- `docs/evaluation.md`
- `docs/controlled-evaluation.md`
- `docs/factory/SPEC-EVAL-001.md`

Third-party vendored material remains under its original license even if it is referenced by the open core.

## Explicitly excluded / reserved

The following are not part of the Apache-2.0 grant unless a future file-specific notice says otherwise:

- `residual/iam/**`
- `residual/compliance/**`
- `residual/tenancy/**`
- `residual/hadr/**`
- `residual/integrations/**`
- `residual/licensing/**`
- `residual/control_plane/**`
- `residual/cluster/**`
- `residual/studio_frontend/**`
- `docs/enterprise/**`
- `docs/studio/**`
- enterprise/commercial portions of `harness_specs/**`
- hosted-service, premium integration, fleet-management, and future enterprise-only code unless explicitly moved into the open manifest

Visibility on GitHub is not itself a license grant for excluded material.

## Boundary rule

New code is not automatically open source because it is added to this repository. To enter the Apache-2.0 Open Core, a maintainer must update this manifest in the same reviewed change or add an explicit Apache-2.0 SPDX/file notice.

## Funding rule

Third-party research or open-source funding credited to RESIDUAL Open Core is used for the included open-source/research layer unless the funding agreement explicitly permits another use.

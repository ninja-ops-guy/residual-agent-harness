# RESIDUAL Open Source Manifest

**License:** Apache License 2.0  
**Copyright:** 2026 Mike Olivares  
**Status:** Candidate funding boundary — not merged to main

This file defines the intended Apache-2.0 portion of the RESIDUAL development monorepo for this candidate revision. A path is included only when explicitly listed below or when it carries its own compatible license notice.

## Included verification/research kernel

- `ai_providers/**`
- `observation_layer/**`
- `verifier/**`
- `residual/brakes.py`
- `residual/core.py`
- `residual/extensions.py`
- `residual/goalspec.py`
- `residual/quarantine.py`
- `residual/receipts.py`
- `residual/verifier.py`

This boundary is intentionally smaller than the full RESIDUAL product. It is designed to expose reusable evidence, verification, contract, provider-abstraction, observation, and policy primitives without licensing Factory, runtime orchestration, execution infrastructure, Studio, enterprise, or hosted-product implementations.

## Included research and attribution material

- `CITATION.cff`
- `AUTHORS.md`
- `docs/open-source/PROJECT_ORIGIN.md`
- `docs/open-source/RESEARCH_CITATION_POLICY.md`
- `docs/research.md`
- `docs/station/RESEARCH.md`
- `docs/evaluation.md`
- `docs/controlled-evaluation.md`
- `docs/factory/SPEC-EVAL-001.md`

Publication of a specification does not imply that the corresponding implementation is included.

## Reserved examples

The machine-readable manifest is authoritative for the exact candidate revision. Reserved paths include, among others:

- Factory and engine implementations
- runtime/orchestration execution code
- sandbox execution infrastructure
- lifecycle/integration/provider implementation outside the kernel
- enterprise IAM, multi-tenancy, HA/DR, compliance and integrations
- commercial licensing/metering
- cluster/control-plane and enterprise Studio implementation

Visibility in the public monorepo is not, by itself, an Apache-2.0 license grant.

## Boundary rule

No agent, automation, funding application, documentation update, or build step may expand the Apache-2.0 scope implicitly. Any expansion requires an explicit manifest change and human maintainer authorization.

## Funding rule

Open-source/research funding represented as support for RESIDUAL Open Core should be used for the included research/kernel layer unless the applicable funding agreement expressly permits another use.

Third-party vendored material remains governed by its original license.

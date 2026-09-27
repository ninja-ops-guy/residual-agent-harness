# RESIDUAL v1 Support Matrix

**Status:** PREPARATION DRAFT. A cell becomes a v1 support claim only after exact-candidate D3 execution and retained evidence.

This file records the intended release surface. It MUST NOT infer PASS from incidental CI.

## Intended v1 cells

| Surface | Intended v1 status | Required evidence |
|---|---|---|
| Windows x64 native | REQUIRED | Exact-candidate native qualification |
| Linux x64 native | REQUIRED | Exact-candidate native qualification |
| Linux Docker Engine | REQUIRED | Exact artifact/container qualification |
| Docker Desktop Windows | REQUIRED | Exact-candidate Docker Desktop qualification |
| NVIDIA Compose overlay | REQUIRED | Exact overlay/runtime qualification |
| Chromium | REQUIRED | Cross-browser user journey |
| Firefox | REQUIRED | Cross-browser user journey |
| WebKit | REQUIRED | Cross-browser user journey |
| Local Ollama | REQUIRED | Real local adapter/model receipt |
| Live hosted provider | REQUIRED | Separate bounded real-provider receipt |

## Explicitly deferred / not claimed for v1

| Surface | v1 disposition |
|---|---|
| Native macOS x64 | DEFERRED / NOT CLAIMED |
| Native macOS ARM64 | DEFERRED / NOT CLAIMED |
| Docker Desktop macOS | DEFERRED / NOT CLAIMED |
| Physical-iPhone heavyweight WebVM | DEFERRED / NOT CLAIMED |

The accepted lightweight iPhone/iPadOS WebKit walkthrough/fallback must not be described as proof that the heavyweight WebVM is reliable on physical iPhone Safari.

## Cell evidence contract

Each REQUIRED cell must retain exact candidate HEAD/TREE, environment identity and versions, exact command/test identity, prerequisite detection, PASS/FAIL/NOT_RUN semantics, evidence hashes, skip/unknown counts, and explicit non-claims.

`SKIP` and `NOT_RUN` are never PASS.

## Hosted-provider cell

The provider family/model is owner-selected before live execution. The gate must distinguish missing credential, invalid credential, invalid model/deployment, transport timeout/transient failure, and real provider success.

No fixture/local fallback may satisfy the hosted-provider cell.

## Release rule

D3 is complete only when every REQUIRED cell has exact-candidate evidence or the owner changes the release claim before RC selection. Deferred cells remain visible in release notes and known limitations.

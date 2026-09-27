# RESIDUAL v1 supported release matrix

**Decision:** D3_RELEASE_MATRIX  
**Recorded:** 2026-09-26  
**Status:** OWNER-APPROVED SCOPE INPUT / qualification still required  
**Purpose:** define which environments and provider claims v1 is allowed to make. Incidental CI on excluded environments does not expand this matrix.

## Native platforms

| Platform | v1 status | Required evidence |
|---|---|---|
| Windows x64 | SUPPORTED | clean install, Station lifecycle/ownership, recovery, exact-RC qualification |
| Linux x64 | SUPPORTED | clean install, Station lifecycle/ownership, recovery, exact-RC qualification |
| macOS x64 | V2 / OUT OF V1 CLAIM | none for v1; any existing CI remains non-release evidence |
| macOS ARM64 | V2 / OUT OF V1 CLAIM | none for v1; any existing CI remains non-release evidence |

## Docker local-workstation platforms

The v1 Docker contract is local-workstation only. It does not claim internet-facing container deployment.

| Platform | v1 status | Required evidence |
|---|---|---|
| Linux Docker Engine | SUPPORTED | real default Compose startup, loopback-only exposure, clean lifecycle, exact-RC smoke |
| Docker Desktop on Windows | SUPPORTED | real default Compose startup on Windows host, loopback-only access, persistence/restart smoke |
| Docker Desktop on macOS | V2 / OUT OF V1 CLAIM | none for v1 |
| NVIDIA Compose overlay | SUPPORTED | base Compose contract plus GPU overlay startup/model availability smoke on an NVIDIA Container Toolkit host |

## Browser / WebVM

| Browser/runtime | v1 status | Scope |
|---|---|---|
| Desktop Chromium | SUPPORTED | browser/WebVM qualification on exact RC |
| Desktop Firefox | SUPPORTED | browser/WebVM qualification on exact RC |
| Desktop WebKit engine | SUPPORTED | automated WebKit browser contract; this does not imply native macOS support |
| Physical iPhone heavyweight WebVM | NOT SUPPORTED IN V1 | no v1 heavyweight-WebVM reliability claim |

Physical iPhone lightweight/fallback behavior may retain separate evidence but MUST NOT be described as heavyweight WebVM support.

## Providers

| Provider class | v1 status | Required claim |
|---|---|---|
| Local Ollama | SUPPORTED | real local inference on exact supported platform/artifact path |
| Live hosted provider | REQUIRED FOR V1 | at least one explicitly selected hosted provider must complete real candidate -> verifier -> receipt success on the exact RC |

The owner decision requires a live hosted-provider success for v1, but does not yet name the provider(s). Therefore:

`HOSTED_PROVIDER_TARGET: UNRESOLVED`

This is a release-matrix completion item, not permission to infer that every implemented cloud adapter is supported. OpenAI Chat Completions, OpenAI-compatible, Anthropic, Gemini, Azure OpenAI, and AWS Bedrock adapters may exist in the product, but v1 support claims require explicit admission and evidence.

## Qualification rules

1. Passing CI on an out-of-v1 environment does not expand supported scope.
2. Failing an out-of-v1 environment does not block v1 unless the failure demonstrates a cross-cutting invariant violation.
3. Supported entries require evidence on the exact RC or exact promoted artifact where the release procedure specifies artifact-bound qualification.
4. Container support remains subordinate to the Station exposure boundary; no remote/public Docker exposure is implied.
5. Provider success is semantic and end-to-end. A connection test alone does not satisfy the live hosted-provider requirement.
6. Exact RC install/recovery/rollback/soak gates use this matrix as their required environment set.

## Remaining matrix decision

Before RC selection, record:

```text
HOSTED_PROVIDER_TARGET:
- <provider/model/deployment>
```

If more than one hosted provider is intended to be a v1 supported claim, list each separately; each needs its own applicable end-to-end evidence.

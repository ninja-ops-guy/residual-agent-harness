# RESIDUAL v1 Qualification Handoff

**Status:** TEMPLATE — populate only after the owner declares a proposed product tree feature-frozen.

## Frozen input

- Product HEAD: `<pending>`
- Product TREE: `<pending>`
- Base/main provenance: `<pending>`
- Feature-freeze receipt: `<pending>`
- Convergence receipt: `<pending>`
- Supply-chain receipt: `<pending>`
- Historical synthetic/predecessor trees: `<pending>`

No source change is permitted after this handoff unless a mandatory qualification gate demonstrates a defect and the owner authorizes a successor.

## Q1 — exact-head hosted qualification

Target identity MUST equal the frozen input.

Required summary:

- Qualification-v1: `<pending>`
- deterministic regression: `<pending>`
- Station/AUD-1 regressions: `<pending>`
- clean install / exact wheel: `<pending>`
- Windows x64: `<pending>`
- Linux x64: `<pending>`
- Docker: `<pending>`
- browser/adversarial browser: `<pending>`
- supply-chain pin gate: `<pending>`
- Open Core boundary: `<pending>`
- deployment profile: `<pending>`
- version consistency: `<pending>`
- fault injection / fuzz / concurrency / active workload: `<pending>`

Failures are classified as PRODUCT_DEFECT, COMPOSITION_DEFECT, TEST_DEFECT, INFRASTRUCTURE_FAILURE, ADVISORY_FAILURE, or NOT_PROVEN. Q1 does not repair product source.

## Q2 — independent composed-tree review

Fresh read-only reviewer, independent from candidate construction.

Required challenges:

- R1 bootstrap composition;
- R2/R3 immutable workflow pins;
- AUD-1 authority/exposure/lifecycle semantics;
- version normalization;
- supply-chain/reproducibility closure;
- Open Core/license boundary;
- deployment-profile admission;
- test sensitivity and expectation weakening;
- historical evidence presented only as historical;
- support claims bounded to D3.

Blocking findings: `<pending>`

## Q3 — D3 release matrix

Required v1 cells:

- Windows x64 native: `<pending>`
- Linux x64 native: `<pending>`
- Linux Docker Engine: `<pending>`
- Docker Desktop Windows: `<pending>`
- NVIDIA Compose overlay: `<pending>`
- Chromium: `<pending>`
- Firefox: `<pending>`
- WebKit: `<pending>`
- local Ollama: `<pending>`

Deferred/not claimed:

- native macOS x64;
- native macOS ARM64;
- Docker Desktop macOS;
- physical-iPhone heavyweight WebVM.

`SKIP`, `NOT_RUN`, `UNKNOWN`, or missing evidence are not PASS.

## Q4 — final-gate binding

- Input helper HEAD/TREE: `<pending>`
- Helper rebound to frozen product identity: `<pending>`
- Final helper exact-head Linux qualification: `<pending>`
- Final helper exact-head Windows qualification: `<pending>`
- Independent helper review: `<pending>`
- F6 execution packet: `<pending>`
- Hosted-provider execution packet: `<pending>`
- RC-soak input manifest: `<pending>`

Q4 prepares but does not execute physical F6 or the live hosted-provider gate.

## Product-freeze decision

Freeze only if Q1, Q2 and Q3 refer to the same HEAD/TREE and report no required source change.

- Q1 identity: `<pending>`
- Q2 identity: `<pending>`
- Q3 identity: `<pending>`
- Identity equality: `<pending>`
- Product freeze authorized: `<pending>`

## Remaining serial gates after product freeze

1. freeze final product-bound F6 helper;
2. physical F6-A and F6-B;
3. independent F6 adjudication;
4. bounded real hosted-provider qualification;
5. accepted integration and resulting-main qualification;
6. human RC selection;
7. exact-RC recovery/rollback campaign;
8. required 24h soak (72h extended confidence tier);
9. final release packet;
10. human v1.0.0 release authorization.

Automated green checks are evidence, not release authority.

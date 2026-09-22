# RESIDUAL current status

_Current-state check: 2026-09-22 02:14 UTC against `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572`._

This document is a human-readable status summary. Exact repository bytes, exact-head workflow results, retained artifacts, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it; later candidate commits or reruns do not inherit, erase, or rewrite earlier evidence unless the governing acceptance process explicitly says so.

## Executive summary

Current `main` is **`91d32fd8b713c68c1cd2e473013c9e1c33b93572`**. No accepted-main movement occurred in this observation.

### Accepted repository state

**#397** (`fix(webvm): sync standalone workbench before reload`) remains **MERGED / accepted repository state**. Its exact PR head was `ed60fb135fea32baf603ff45ecb2d0a82b44828e`; the maintainer supplied the exact-head approval string, and GitHub merged the PR as `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572`.

The historical `main@b571b91a9615484a1b9b81cacc8b7d82c41498ea` Pages post-deploy failure remains retained **FAIL** evidence. It is not rewritten. The first authoritative push-triggered Pages workflow on repaired `main@91d32fd8...` completed **PASS**. Exact-main RESIDUAL Qualification v1 is also **PASS** at the retained observation. Other observed exact-main push workflows including Controller/provider contracts, Command Station checks, clean-install qualification and M4 qualification runner prerequisites are **PASS**; Vercel is **PASS**.

These are exact-revision results only. They do not establish physical-device reliability, successful paid/live provider semantics, every-host M4 qualification, elapsed soak, closure of AUD-1, or blanket production readiness.

### AUD-1 security convergence

Owner issue **#353 remains OPEN and P0 / BLOCKED at the release level**. Focused convergence candidate **#399** remains open, unmerged, and based on accepted `main@91d32fd8...`.

The prior exact head `fb416efe29d245fcbbb03f6f8edb8c89a8212f3d` completed the named hosted technical workflows successfully, including Qualification v1. PR-Agent nevertheless identified that adversarial requirement #6 lacked an explicit positive coordinator-transition regression: the combined test proved worker denial but not that the corresponding authenticated coordinator/operator transition remained possible. Those `fb416efe...` PASS results remain retained exact-head software evidence, but they are **superseded for final acceptance** rather than treated as satisfying the complete ten-regression contract.

Current #399 exact head is **`8df77b832b3839ccd2a6944a65760ce3ab10dc9c`**. It adds the missing explicit coordinator-vs-worker authority-separation regression. Because candidate bytes changed, current qualification and acceptance claims are bound to this exact revision.

Fresh exact-head hosted software evidence is green:

- Factory ownership: **PASS**
- Control Plane: **PASS**
- clean-install qualification: **PASS**
- PR-Agent advisory: **PASS**
- Controller/provider contracts: **PASS**
- Command Station checks: **PASS**
- Pages PR-head/browser proof: **PASS**
- measured-evaluation acceptance binding: **PASS**
- Vercel: **PASS**
- RESIDUAL Qualification v1 aggregate: **PASS**
- exact-head maintainer approval: **FAIL / no matching human attestation**

The owner has now explicitly classified the **AUD-1 software gate as ready for physical P1 dogfood** on exact candidate `8df77b83...`. The maintainer-approval gate is intentionally unfulfilled until after the physical evidence and independent re-audit. This is a progression to the next evidence stage, **not** release acceptance, merge authorization, or closure of #353.

Therefore #399 remains **UNACCEPTED / NOT MERGE-READY**. The two required physical F6 timing claims remain **UNKNOWN / not established** until distinct retained artifacts exist, followed by the standing Mason/LEGION independent read-only re-audit and the remaining governed qualification/attestation/merge/new-main sequence. Any candidate-byte change invalidates affected exact-head qualification/audit evidence.

### OpenClaw Shared Comms bridge candidate

**#400** (`feat(openclaw): add durable Shared Comms bridge R0`) remains **DRAFT / UNMERGED / UNACCEPTED** at exact head **`c0c1f2cbd4677e0bc8fd2f710b40f3608db9cda7`**.

Its PR body describes an advisory OpenClaw bridge with durable SQLite/WAL state, deterministic identities/session keys, filtering and self-loop suppression, retained request/response receipts, bounded execution, provider/model/transport/fallback status, Ollama warm-up, and deployment/operator documentation. Those are candidate-branch claims, not accepted-main behavior.

The PR explicitly states that accepted GitHub `main` does **not** contain the locally qualified R3.4 Station Shared Comms worker endpoints/outbox and that #400 should remain draft until that server-side contract lands or is otherwise resolved. The bridge is also explicitly advisory: it does not claim tasks or replace Station authority. That dependency remains a **BLOCKED acceptance boundary** for the integration; hosted CI cannot synthesize the missing server-side mainline contract.

At exact head `c0c1f2c...`, observed software workflows include **PASS** for RESIDUAL Qualification v1, Control Plane, Factory ownership, clean-install qualification, measured-evaluation binding, PR-Agent, Controller/provider contracts, and Command Station checks; Vercel is **PASS**. The PR Pages workflow is **CANCELLED**, not PASS, and exact-head maintainer approval is **FAIL** because no matching human attestation exists. None of these results changes the PR's DRAFT / dependency-blocked / unaccepted status.

### Research-maintenance check-in

New draft **#401** (`docs(research): record 2026-09-21 AX-21 evidence check-in`) targets the research branch `research/exp-m6-slm-00`, not `main`. It is an append-only research-maintenance candidate at exact head **`277d775182d2cf55b986b93025e762959f1c6094`**.

Its PR body records G2 round-1 falsification and round-2 remediation, stronger CD-XVAL-R3 evidence with remaining split/near-duplicate risks, explicit SLM-00 G-qualified-but-not-frozen status, narrowed AUD-1 wording, outstanding physical P1 evidence, retained WebVM failure/repair history, a Kimi-429→local-Ollama pilot observation, and pre-intervention P5/operator-friction status. These are **draft research observations**, not accepted-main or release claims.

#401 explicitly does **not** authorize training, freeze SLM-00, close AUD-1, declare AX-21 finally frozen, or advance release status. Its existence therefore does not change the release gate or the human research-authority boundary.

### Measured R0-R5 research-ablation candidate

New draft **#402** (`research: add measured R0-R5 reliability ablation lane`) targets `main` from accepted baseline `91d32fd8b713c68c1cd2e473013c9e1c33b93572` and is currently **DRAFT / UNMERGED / UNACCEPTED** at exact head **`2958ef726cab4deaaa997c0bf4b426a74349213e`**.

The candidate adds a separately governed measured-only R0-R5 apparatus: complete paired `(task, repeat) × R0-R5` enforcement, held provider/model/prompt/inference/tool/grader/environment/budget hashes, ASSR and safety-UAR endpoints plus reliability/efficiency counters, UNKNOWN retention, no outcome-dependent early stopping, immutable observation references/content-addressed bundles, tests, and a human + machine-readable preregistration under `docs/research/`.

Its scientific boundary is explicit: **apparatus only**. It does **not** claim live empirical support for H1, does not relabel the existing scripted `residual.eval_frozen` fixture as measured evidence, and does not modify or consume sealed AX/SLM evidence. A real Factory execution adapter and a frozen confirmatory workload/execution manifest remain future gates before confirmatory outcome access; protected Factory use remains subject to the existing measured-M4 acceptance-binding gates.

At exact head `2958ef72...`, the observed GitHub technical workflows are **PASS**, including Factory ownership, Control Plane, measured-evaluation acceptance binding, PR-Agent advisory, clean-install qualification, Controller/provider contracts, Command Station checks, RESIDUAL Qualification v1, and Pages PR-head/browser proof. Exact-head maintainer approval is **FAIL / no matching human attestation**. Vercel is **FAIL due to deployment build-rate limiting**, not a demonstrated repository correctness failure. Therefore #402 remains a draft research candidate; its green hosted software evidence does not establish empirical H1 support, live-provider execution, Factory measured-run completion, or research acceptance.

## Qualification v1 — accepted implementation, bounded claims

Qualification v1 remains implemented on accepted main. The prior #152/#355/#356 convergence and its exact-revision evidence/failure-ledger machinery remain accepted repository state.

For current `main@91d32fd8...`:

- RESIDUAL Qualification v1: **PASS** at the retained push-triggered observation.
- Deploy GitHub Pages: **PASS** at the first authoritative repaired-main push observation.
- Controller/provider contracts: **PASS**.
- Command Station checks: **PASS**.
- clean-install qualification: **PASS**.
- M4 qualification runner prerequisites: **PASS**.
- Vercel: **PASS**.

These are exact-revision results, not a universal release claim.

Still **UNKNOWN / not established** by those PASS results:

- universal/every-host M4 qualification;
- blank-environment installation beyond the tested clean-install contract;
- true 24h/72h/30d elapsed soak evidence;
- successful live-provider candidate→verifier→receipt execution;
- physical-device reliability;
- closure of AUD-1 #353;
- SLM-00 human freeze/training authority.

## #397 retained-failure and acceptance boundary

The evidence chain for #397 remains historically exact:

- old main `b571b91...` Pages attempt: **FAIL** at post-deploy published-WebVM/real-guest verification after preceding build/browser/deployment steps passed;
- #397 exact PR head `ed60fb135...`: Qualification v1 and other named candidate checks ultimately passed; Controller/provider attempt 1 remained retained **FAIL** at external artifact-finalization with intermediary `403 Forbidden`, and same-head attempt 2 was retained **PASS** without rewriting attempt 1;
- the owner later supplied exact-head maintainer approval for `ed60fb135...`;
- #397 merged as `main@91d32fd8...`;
- the first authoritative Pages workflow on that repaired main revision: **PASS**.

The acceptance of #397 does not erase its retained first failures. It establishes only that the governed candidate progressed and the repaired exact-main production Pages check passed.

## AUD-1 / #399 trust-boundary details

#399 proposes candidate repairs for AUD-1 F1/F2/F3/F4/F6 and the ten required adversarial regressions. Test presence and current hosted PASS are implementation/qualification evidence, not closure evidence.

The retained candidate history remains important:

- `3fee648151de9a4ea350ff8ab4ef2a247207ea38` retained a browser-harness failure;
- `a7f1068...` retained Qualification-v1 `active-http-soak` and Command Station browser failures;
- `8294b824...` repaired those surfaces but retained Qualification-v1 browser journey failures;
- `fb416efe...` completed the named technical workflows **PASS**, but the PR-Agent review identified the missing explicit positive coordinator-transition half of adversarial requirement #6; its PASS remains exact-head evidence but is superseded for final acceptance;
- current `8df77b832b3839ccd2a6944a65760ce3ab10dc9c` adds that missing regression and has fresh exact-head **RESIDUAL Qualification v1 PASS** plus the other named hosted software checks **PASS**, while exact-head maintainer approval remains **FAIL** by design.

Historical failures and superseded PASS results remain evidence for their exact revisions. Current PASS does not retroactively rewrite any of them.

### Remaining mandatory #353 sequence

The owner issue still requires:

```text
implementation
  → ten adversarial regressions
  → normal repository CI
  → physical P1 F6 dogfood: reconnect inside window + reconnect outside window
  → Mason independent re-audit
  → exact-head qualification
  → owner review / attestation
  → merge
  → authoritative new-main qualification
```

The implementation/regression/hosted-CI stage is now considered **software-gate ready for physical P1 dogfood** on exact head `8df77b83...`. That classification is bounded to the current exact candidate and does not establish the physical claims.

The two F6 cases remain **UNKNOWN / not established** until separately retained evidence exists on the LEGION / DELL7320 / DBOX topology:

1. **inside-window reconnect:** interrupt the authenticated runner transport while it owns a real task, restore before the bounded retry/authority window expires, and prove the same valid authority resumes without duplicate ownership, duplicate acceptance, or invalid transition;
2. **outside-window expiry + stale-result rejection:** interrupt beyond the authority-loss window until surrender/expiry, permit recovery/reassignment, restore the old runner, and prove its old lease/credential remains dead and its stale candidate/result is rejected rather than integrated.

Do not collapse these into one reconnect PASS. They are distinct claims and require distinct retained artifacts.

After both physical artifacts exist for the exact candidate, Mason/LEGION's independent read-only re-audit of F1/F2/F3/F4/F6 remains required. The re-audit must classify the repairs against the original audit without modifying the candidate. A later candidate-byte change invalidates affected qualification/audit evidence.

The current hosted Qualification-v1 PASS does not authorize skipping or reordering these gates. Exact-head maintainer approval remains intentionally **FAIL** until the preceding evidence stages are complete.

## Factory / M4 ownership boundary

The accepted Qualification-v1 convergence includes the owner-authorized #152 portability advance moving shared sandbox wire/exit constants into platform-neutral `residual/factory/m4_protocol.py` and adding that file to the protected core set. The committed ownership baseline records that pin alongside the previously authorized RuntimeJournal pin.

Therefore:

- the protected ownership-baseline advance remains **accepted main state**;
- the exact protected-byte scope is whatever the committed ownership baseline records;
- this documentation does **not** modify that baseline, protected Factory/M4 bytes, verifier authority, qualification anchors, or evidence schemas;
- no unrelated M4, host, security, or production claim may inherit PASS from that baseline advance.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest, and is intentionally unchanged by this documentation reconciliation.

## Live-provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter execution reached the configured model but failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary. Successful live-provider semantic execution therefore remains **UNKNOWN**.

The accepted iOS/iPadOS fallback routes that profile to the lightweight walkthrough before heavyweight guest boot. It is not proof that heavyweight WebVM is reliable on physical iPhone Safari. Issues #120/#126 and long-run WebVM reliability remain separate.

#397's accepted hosted durability repair and exact-main Pages PASS do not convert those physical/live-provider claims into PASS.

## SLM-00 research boundary

The previously retained SLM-00 evidence remains exact-revision research evidence:

- Lane G has a `G_PASS` candidate for its pinned research bytes;
- independent-context G2 round 2 reports `PASS_WITH_NONBLOCKING_FINDINGS` for the exact remediated candidate;
- historical G2 round 1 `REJECT` remains retained evidence for the earlier candidate;
- draft #401 records additional append-only research observations and a status-synchronization finding, but it targets a research branch and remains unaccepted.

The program remains **NOT FROZEN / UNACCEPTED / NO-TRAINING** until the explicit human freeze/authority gates close. Automated research PASS or a draft research-maintenance PR does not synthesize maintainer approval or training authority.

## Documentation scope

This observation updates only `docs/CURRENT_STATUS.md` on the existing dedicated docs branch. The open docs PR continues to carry its earlier `README.md` and `HARNESS.md` reconciliation; neither required an additional change for #402. `START-HERE.md` remains operator guidance and contains no stale accepted-main/qualification claim requiring this update. `implementation-status.yaml` remains accurate for its declared implementation-presence purpose and is intentionally unchanged.

No Factory/M4 implementation or tests, ownership baseline, qualification anchor, protected byte, verifier/evidence schema, provider authority, security implementation, licensing authority, or acceptance authority is modified by this docs branch.

Because this PR records ownership-baseline, qualification-anchor, retained-failure and active security/research evidence, it must **not** be merged automatically. Exact-head human review/attestation remains required.
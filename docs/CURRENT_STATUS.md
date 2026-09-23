# RESIDUAL current status

_Current-state check: 2026-09-23 00:15 UTC against `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572`._

This document is a human-readable status summary. Exact repository bytes, exact-head workflow results, retained artifacts, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it; later candidate commits or reruns do not inherit, erase, or rewrite earlier evidence unless the governing acceptance process explicitly says so.

## Executive summary

Accepted `main` remains **`91d32fd8b713c68c1cd2e473013c9e1c33b93572`**. No accepted-main commit or merged-PR movement occurred in this observation.

The new material repository change is draft research-maintenance **#405** (`docs(research): record 2026-09-22 AX-21 evidence check-in`) at exact head **`2549bb1b81f6bdc6954896eb7ebedadfe82b2722`**. It adds one append-only research file under `docs/swarm/` and preserves the current boundaries rather than advancing them: measured R0-R5 remains apparatus without a confirmatory H1 result; the two physical AUD-1 F6 cases remain **UNKNOWN / not established**; #404 remains an unqualified mesh candidate without a multi-host/autonomy result; P5 operator-friction remains pre-intervention; and AX-21-BASELINE-R0 is not finally frozen because no formal release/tag cutover exists. Exact-head technical repository workflows for #405, including Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent, are **PASS**; Vercel is **PASS**; exact-head maintainer approval is **FAIL** because no matching human attestation exists. Those CI results qualify only the candidate bytes and do not promote the research claims.

AUD-1 release state is otherwise unchanged. #399 remains the exact software candidate at `8df77b83...`; read-only helper #403 remains at `03a89dfe...` with hosted qualification **PASS**; neither physical F6 bundle has been established, so owner issue **#353 remains OPEN / P0 / BLOCKED at the release level**. Draft #404 remains unchanged at `cae9ab31...`, **UNMERGED / UNACCEPTED**, with its previously retained mixed/FAIL qualification state.

No evidence in this observation authorizes merging #399, #403, #404, #405, or the documentation PR.

## Accepted repository state

**#397** (`fix(webvm): sync standalone workbench before reload`) remains **MERGED / accepted repository state**. Its exact PR head was `ed60fb135fea32baf603ff45ecb2d0a82b44828e`; GitHub merged it as `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572` after exact-head owner approval.

The historical `main@b571b91a9615484a1b9b81cacc8b7d82c41498ea` Pages post-deploy failure remains retained **FAIL** evidence. It is not rewritten. The first authoritative push-triggered Pages workflow on repaired `main@91d32fd8...` completed **PASS**. Exact-main RESIDUAL Qualification v1 is also **PASS** at the retained observation. Other observed exact-main push workflows including Controller/provider contracts, Command Station checks, clean-install qualification and M4 qualification runner prerequisites are **PASS**; Vercel is **PASS**.

These are exact-revision results only. They do not establish physical-device reliability, successful paid/live provider semantics, every-host M4 qualification, elapsed soak, closure of AUD-1, or blanket production readiness.

## AUD-1 security convergence

Owner issue **#353 remains OPEN and P0 / BLOCKED at the release level**. Focused convergence candidate **#399** remains open, unmerged, mergeable, and based on accepted `main@91d32fd8...`.

Current #399 exact head is **`8df77b832b3839ccd2a6944a65760ce3ab10dc9c`**. It proposes repairs for AUD-1 F1/F2/F3/F4/F6 and the required adversarial regression set. Retained candidate history remains exact-revision evidence:

- `3fee648151de9a4ea350ff8ab4ef2a247207ea38`: retained Command Station browser failure;
- `a7f1068b41330777889646143a612a89282cc3b0`: retained Qualification-v1 `active-http-soak` and Command Station browser failures;
- `8294b8240a65e79be0cbb5ea0559c2e22c7825fa`: retained cross-browser/adversarial Qualification-v1 failures;
- `fb416efe29d245fcbbb03f6f8edb8c89a8212f3d`: named technical workflows PASS, but superseded for final acceptance because adversarial requirement #6 lacked the explicit positive coordinator-transition half;
- current `8df77b83...`: adds that missing authority-separation regression and has retained exact-head hosted software PASS for Qualification v1 and the named technical workflows, while exact-head maintainer approval remains intentionally **FAIL** pending physical evidence and independent re-audit.

The owner classified the #399 software gate as ready for physical P1 dogfood. That is progression to the next evidence stage, **not** release acceptance, merge authorization, or closure of #353.

### #403 — read-only F6 physical evidence kit

Draft **#403** (`tools(aud1): add read-only F6 physical evidence kit`) targets the #399 convergence branch rather than `main`. It remains **DRAFT / UNMERGED / TOOLING-ONLY** and is now at exact head **`03a89dfe0c76e4eaea1406304e9f41a78255a402`**.

The PR explicitly states that it **must not be merged into or used as the Station candidate under test**. It branches from #399 exact candidate `8df77b83...` only so its collector understands the same schema and independently verifies that the candidate checkout under test is clean and exactly bound to that SHA/tree.

The kit adds:

- read-only SQLite Station snapshots using `mode=ro`;
- exact candidate SHA/tree/clean-worktree binding;
- task owner/lease/expiry and project event capture;
- redacted settings and public bootstrap metadata capture;
- operator event ledger and diagnostic-command capture;
- hashed remote evidence attachments plus immutable bundle manifest verification;
- guided F6-A inside-window and F6-B outside-window/stale-return PowerShell runbooks;
- a remote host/process/TCP/log probe;
- focused tests for secret redaction, read-only behavior, attachment handling and manifest tamper detection.

The tooling deliberately does not claim work, heartbeat, submit or replay results, alter leases, edit Station SQLite, recover/reassign tasks, rotate credentials, approve/integrate, or declare PASS. The operator still controls the real tunnel interruption/restoration and natural Station/worker behavior remains the subject under test.

Retained candidate history remains exact-revision evidence:

- **`f921d7abe6f17fabd61cf28934870eba17c38c69`** had retained hosted PASS for Qualification v1 and the named technical workflows before PR-Agent identified a potential data-exposure weakness because redaction relied too heavily on key names.
- **`10a355fc402aff7f0e8c5d8afc0ea02569667371`** incorporated the first fail-closed/value-redaction hardening and retained **Qualification-v1 FAIL** at the deterministic `Full deterministic regression gate`; the lower-level assertion/root cause was not established from retained workflow metadata and remained **UNKNOWN** for those bytes.
- Current **`03a89dfe0c76e4eaea1406304e9f41a78255a402`** adds two further focused redaction repairs:
  - `234f8d7985a9e1c01767daebac7ffee2aef8d0bf` — `fix(aud1-tools): repair redaction regex escapes`;
  - `03a89dfe0c76e4eaea1406304e9f41a78255a402` — `fix(aud1-tools): redact authorization scheme credentials`.

The compare from `10a355fc...` to `03a89dfe...` is limited to the AUD-1 tooling/test surface and does not change the #399 Station candidate under test.

Current exact-head evidence for `03a89dfe...` is:

- Controller/provider contracts: **PASS**
- Control Plane: **PASS**
- Factory ownership: **PASS**
- measured-evaluation acceptance binding: **PASS**
- clean-install qualification: **PASS**
- Command Station checks: **PASS**
- PR-Agent advisory: **PASS**
- RESIDUAL Qualification v1 aggregate: **PASS**
  - deterministic job: **PASS**
  - discovery, M4, active HTTP, browser, adversarial and observed cross-browser jobs: **PASS**
- Vercel: **PASS**
- exact-head maintainer approval: **FAIL / no matching human attestation**

The new exact-head PASS does **not** erase or retroactively repair the retained `10a355fc...` Qualification failure. It establishes only that the changed `03a89dfe...` tooling candidate passed the observed hosted gates.

Those software results still do **not** manufacture the two physical F6 outcomes. Required physical outputs remain two separately frozen bundles:

1. `F6-A-inside-window`;
2. `F6-B-outside-window`.

Until those distinct retained artifacts exist against the exact #399 candidate, both physical claims remain **UNKNOWN / not established**. Mason/LEGION's independent read-only re-audit still follows those physical observations.

### Remaining mandatory #353 sequence

The release sequence remains:

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

Do not collapse the two F6 cases into one reconnect PASS. Any candidate-byte change invalidates affected exact-head qualification/audit evidence.

## Shared Comms / mesh candidates

### #400 — OpenClaw Shared Comms bridge

**#400** (`feat(openclaw): add durable Shared Comms bridge R0`) remains **DRAFT / UNMERGED / UNACCEPTED** at exact head **`c0c1f2cbd4677e0bc8fd2f710b40f3608db9cda7`**.

Its PR body describes an advisory OpenClaw sidecar with durable SQLite/WAL state, deterministic response identities/session keys, filtering/self-loop suppression, receipts, bounded execution, provider/model/transport/fallback status, Ollama warm-up, and deployment/operator documentation. Those are candidate-branch claims, not accepted-main behavior.

The PR explicitly states that accepted main lacks the locally qualified R3.4 Station Shared Comms worker endpoints/outbox contract and that #400 should remain draft until that server-side dependency lands or is otherwise resolved. That dependency remains **BLOCKED**. Hosted CI does not synthesize the missing accepted server contract.

### #404 — SPEC-SC-MESH-001 durable mesh foundation

Draft **#404** (`feat(station): SPEC-SC-MESH-001 enrollment and durable comms foundation`) targets `main` from accepted baseline `91d32fd8...` and remains **DRAFT / UNMERGED / UNACCEPTED** at exact head **`cae9ab31e0ca3acfd948af32726db388c589aeb2`**.

The PR describes the first isolated mesh slice: typed per-worker enrollment and project/capability scope, hashed bearer credentials, an `ENROLLED → SYNCING → READY / DISCONNECTED / REVOKED` lifecycle, bounded/versioned message envelopes, namespaced idempotency/replay/dead-letter state, crash-durable worker outbox/inbox, project generation and fencing-token foundations, presence-only mesh heartbeat, scoped worker HTTP surfaces, and redacted status. It also adds setup/rollback/OpenClaw mesh documentation and regression coverage.

The PR's own non-claims remain controlling: **no live deployment or service change, no merge authorization, no `MESH_QUALIFIED` claim**. W4 atomic assignment/budget integration is incomplete; W5 provider continuity/host containment/verified-evidence binding is incomplete; W6/W7 setup, rollback, and multi-host qualification remain pending. Preserved R3.4 evidence is not relabelled or mutated by this status summary.

Current retained exact-head evidence is mixed and therefore #404 remains **FAIL / NOT MERGE-READY**:

- Control Plane: **PASS**
- Factory ownership: **PASS**
- measured-evaluation acceptance binding: **PASS**
- clean-install qualification: **PASS**
- PR-Agent advisory: **PASS**
- Pages PR-head/browser proof: **PASS**
- Vercel: **PASS**
- Factory runtime evidence: **FAIL** at `Baseline and Factory contracts`
- RESIDUAL Qualification v1: **FAIL** at the deterministic `Full deterministic regression gate`
- Controller/provider contracts: **FAIL** in the Python test matrix at `Compile and test without model credentials`
- Command Station checks: **FAIL** in the Python unittest matrix; browser and Docker jobs are observed PASS
- exact-head maintainer approval: **FAIL / no matching human attestation**

Retained workflow metadata identifies the failing jobs/steps above, but not the underlying assertion/root cause. The lower-level causes therefore remain **UNKNOWN** until exact retained test output or a candidate change establishes them. Do not infer qualification from the green subset and do not broaden this candidate into a mesh-production claim.

#404 does not touch protected Factory/M4 implementation in this observation; its file set is Station/provider/deployment/docs/tests scope. This status statement does not authorize any future protected-byte change.

## Research-maintenance candidates

### #401 — AX-21 evidence check-in

Draft **#401** (`docs(research): record 2026-09-21 AX-21 evidence check-in`) targets the research branch `research/exp-m6-slm-00`, not `main`, at retained exact head **`277d775182d2cf55b986b93025e762959f1c6094`**.

It is an append-only research-maintenance candidate and explicitly does **not** authorize training, freeze SLM-00, close AUD-1, declare AX-21 finally frozen, or advance release status.

### #402 — measured R0-R5 research-ablation apparatus

Draft **#402** (`research: add measured R0-R5 reliability ablation lane`) targets accepted main and remains **DRAFT / UNMERGED / UNACCEPTED** at exact head **`2958ef726cab4deaaa997c0bf4b426a74349213e`**.

The candidate adds measured-only R0-R5 apparatus and preregistration. Its scientific boundary remains **apparatus only**: it does **not** claim live empirical support for H1, does not relabel scripted fixture evidence as measured evidence, and does not consume sealed AX/SLM evidence. A real Factory execution adapter and a frozen confirmatory workload/execution manifest remain future gates before confirmatory outcome access.

Retained exact-head GitHub technical workflows are PASS, including Qualification v1 and measured-evaluation acceptance binding; exact-head maintainer approval remains **FAIL**. Retained Vercel status is **FAIL due to deployment build-rate limiting**, not established repository-correctness evidence.

### #405 — AX-21 research check-in for 2026-09-22

Draft **#405** (`docs(research): record 2026-09-22 AX-21 evidence check-in`) targets accepted `main@91d32fd8...` and remains **DRAFT / UNMERGED / UNACCEPTED** at exact head **`2549bb1b81f6bdc6954896eb7ebedadfe82b2722`**. It changes exactly one file, `docs/swarm/ax-21-research-checkin-2026-09-22.md`.

The candidate is append-only research maintenance. It records, without broadening claims, that:

- #402 provides a separately governed measured R0-R5 apparatus, but no confirmatory live result or H1 support exists yet;
- #403 provides stronger read-only physical F6 evidence collection, while both F6-A and F6-B remain **UNKNOWN / not established**;
- #404 begins encoding AX-21 findings around per-worker scope, presence-vs-authority separation, replay/idempotency and durable comms, but has no qualified multi-host/autonomy result;
- the P5 operator-friction before-condition has not advanced;
- no formal GitHub release exists, so final `AX-21-BASELINE-R0` freeze has not occurred.

The PR explicitly does **not** close AUD-1, qualify the mesh, claim measured R0-R5 effects, claim post-#349 operator-friction improvement, or advance release/freeze authority.

Current exact-head hosted evidence for #405 is:

- RESIDUAL Qualification v1: **PASS**
- Controller/provider contracts: **PASS**
- Command Station checks: **PASS**
- clean-install qualification: **PASS**
- Factory ownership: **PASS**
- measured-evaluation acceptance binding: **PASS**
- Control Plane: **PASS**
- PR-Agent advisory: **PASS**
- Vercel: **PASS**
- exact-head maintainer approval: **FAIL / no matching human attestation**

Those results qualify only the candidate revision and do not convert the recorded research boundaries into accepted scientific or release claims.

## Qualification v1 — accepted implementation, bounded claims

Qualification v1 remains implemented on accepted main. The prior #152/#355/#356 convergence and its exact-revision evidence/failure-ledger machinery remain accepted repository state.

For current `main@91d32fd8...`, retained observations remain:

- RESIDUAL Qualification v1: **PASS**
- Deploy GitHub Pages: **PASS** on the first authoritative repaired-main push
- Controller/provider contracts: **PASS**
- Command Station checks: **PASS**
- clean-install qualification: **PASS**
- M4 qualification runner prerequisites: **PASS**
- Vercel: **PASS**

These are exact-revision results, not a universal release claim.

Still **UNKNOWN / not established** by those PASS results:

- universal/every-host M4 qualification;
- true 24h/72h/30d elapsed soak evidence;
- successful live-provider candidate→verifier→receipt execution;
- physical-device reliability;
- closure of AUD-1 #353;
- SLM-00 human freeze/training authority;
- #404 mesh qualification or multi-host production readiness.

## Factory / M4 ownership boundary

The accepted Qualification-v1 convergence includes the owner-authorized #152 portability advance moving shared sandbox wire/exit constants into platform-neutral `residual/factory/m4_protocol.py` and adding that file to the protected core set. The committed ownership baseline records that pin alongside the previously authorized RuntimeJournal pin.

Therefore:

- the protected ownership-baseline advance remains **accepted main state**;
- the exact protected-byte scope is whatever the committed ownership baseline records;
- this documentation does **not** modify that baseline, protected Factory/M4 bytes, verifier authority, qualification anchors, or evidence schemas;
- no unrelated M4, host, mesh, security, or production claim may inherit PASS from that baseline advance.

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
- draft #401 and newer draft #405 record append-only research observations but remain unaccepted.

The program remains **NOT FROZEN / UNACCEPTED / NO-TRAINING** until explicit human freeze/authority gates close. Automated research PASS or a draft research-maintenance PR does not synthesize maintainer approval or training authority.

## Documentation scope

This observation updates only `docs/CURRENT_STATUS.md` on the existing dedicated docs branch. The open docs PR continues to carry its earlier `README.md` and `HARNESS.md` reconciliation; neither required an additional edit for #405 because the new material change is an unaccepted append-only research check-in, not a change to accepted-main product or operator behavior. `START-HERE.md` remains operator guidance and contains no stale accepted-main/qualification claim requiring this update. `implementation-status.yaml` remains accurate for its declared implementation-presence purpose and is intentionally unchanged.

The immediately preceding docs head `d9e04d9d491e908d36f56ef1acea5409e43fabd3` completed exact-head technical workflows successfully: Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent were **PASS**; Vercel was **PASS**; maintainer approval remained **FAIL** because no matching human attestation existed. Those results remain bound to `d9e04d9...` and are not inherited by this changed documentation head.

No Factory/M4 implementation or tests, ownership baseline, qualification anchor, protected byte, verifier/evidence schema, provider authority, security implementation, licensing authority, or acceptance authority is modified by this docs branch.

Because this PR records ownership-baseline, qualification-anchor, retained-failure and active security/mesh/research evidence, it must **not** be merged automatically. Exact-head human review/attestation remains required.
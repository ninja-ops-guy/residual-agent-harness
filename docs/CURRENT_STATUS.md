# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@e7b72ad18df5729f16d36771971c8a8828d71a10`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`e7b72ad18df5729f16d36771971c8a8828d71a10`**, produced by merged PR **#276** on 2026-09-19.

Two recent governance/qualification repairs are now accepted:

- **#275 / #268** — #275 repaired publication of the protected `maintainer-approval` result onto the exact live PR head after explicit exact-head human attestation; #268 is closed. This changes repository governance plumbing only and does not widen worker, verifier, Factory/M4, provider, evidence-schema or acceptance authority.
- **#276 / #267** — #276 removed the production Pages `push.paths` bypass that allowed some merged-main revisions to receive no authoritative Pages qualification attempt; #267 is closed. Every new `main` SHA is now expected to receive its own non-cancelling first production Pages attempt.

The first authoritative production Pages attempt for exact current main is **run `35410875305`, attempt 1, and it is FAIL**. Generated desktop+narrow browser proof passed. Deployment itself passed. Published live acceptance then failed at **`Verify published WebVM revision and real guest execution`**, and the subsequent published narrow-browser acceptance was skipped. The workflow retained the live proof artifact. This is production Pages qualification **FAIL for `main@e7b72ad...`**. The retained run proves the failure stage; it does not establish a paid/live Puter or model-quality failure.

Open **#260** is now reconciled onto exact current main at head `2a9455ee1c2001306521946e61376fae153211ad` as the focused provider-bootstrap race repair. Its exact-head technical workflows are **PASS**, including PR-head Pages, Browser VM, Controller/provider, Command Station, clean install, Factory ownership, Control Plane and measured-evaluation binding. The protected maintainer-approval workflow remains **FAIL** because no new exact-head maintainer attestation exists, and the retained triage also calls for fresh independent technical acceptance on the moved head if required by #260's governing criteria. #260 is therefore **HOLD / unaccepted**. Its PR-head PASS does not change the retained production Pages **FAIL** on current `main`; if #260 is later accepted unchanged, the resulting new main SHA's first automatic production Pages run is authoritative.

Exact-current-main automated evidence is therefore mixed rather than globally green. Controller/provider, Command Station and Factory ownership workflows have retained **PASS** results for their named exact-main scopes, while production Pages is **FAIL**. A PASS in one named gate does not override a FAIL in another.

The acute Actions queue saturation captured by **#305** has cleared operationally: the retained issue update reports **0 queued runs** on 2026-09-19, down from earlier snapshots of 1,291/970 and the original 1,267 queued. #305 remains open because the structural duplicate-trigger/concurrency repair **#307** is still unmerged. Queue recovery is not evidence that the trigger defect is fixed, and it does not erase any first-attempt failures.

## Newly opened unaccepted work and evidence

Several new branches appeared after the preceding status refresh. None changes accepted `main` capability.

- **#318** — draft Web Command Station control-plane architecture for Vercel. The design explicitly keeps Vercel as a public control plane rather than an arbitrary-code worker runtime and proposes WEB-F0..F10 qualification gates. It is **UNACCEPTED / draft** and must not be described as implemented production capability.
- **#319 / M6-MESH-001 Trial 0** — retained real-model crossover pilot on exact head `d3b6f24d7b2e9c2ac08f51c02764fda41042af76`. Workflow run `35424274389` is **PASS for apparatus execution** and retained artifact `10578541714` (`m6-mesh-001-trial0`, SHA-256 `182a00055eba534e409ef006d17d282722ddbdff2d919ae3c6f92555dc73864b`) records three repeats of the same two independently verified Qwen2.5-Coder 1.5B obligations. Both sequential and two-call concurrent conditions passed all six obligation checks. The retained means are `2.189893 s` sequential versus `1.830017 s` parallel, an observed ratio of `1.196652x`. This is a **bounded pilot observation only**: three repeats on one Ollama host, with visible warm-up/order sensitivity, are insufficient to establish a general or statistically durable concurrency-efficiency claim. General mesh/swarm efficiency therefore remains **UNKNOWN / not established**. The branch is also unaccepted: maintainer approval is **FAIL**, and the Aikido scan reports two new MEDIUM and two new LOW findings, including unsafe `exec` use and missing integrity verification for a remotely pulled workflow artifact.
- **#323** — draft built-in Research Workbench with versioned experiment catalog and a declarative first pilot (`M6-WB-001`). Its exact head `f32b99b7d62bc35872daaf4da00787761b7ca8ea` is **FAIL for qualification**: the dedicated Research Workbench workflow, Controller/provider, Command Station and Factory runtime evidence are FAIL, while Control Plane, Factory ownership, clean install, measured-evaluation binding, PR Agent and PR-head Pages are PASS. Maintainer approval is also **FAIL**. The PR explicitly blocks any first authoritative Workbench trial until **#288** is accepted on `main` and this branch is rebased/requalified. Therefore Workbench availability and any staged experiment definitions are **UNACCEPTED**, and no paper-facing/authoritative trial result is established.
- **#324** — open security hardening pass for confirmed runtime/egress/XML/CI-credential findings. Exact head `db209368750f425a8bf1500ad2b207f43b8af958` has the named technical workflows **PASS**, including Factory runtime/OS evidence, Controller/provider, Command Station, clean install, Factory ownership, Control Plane, measured-evaluation binding and PR Agent; protected maintainer approval is **FAIL**. The PR remains unmerged, does not update the Factory ownership baseline, and must not be treated as accepted security posture until explicit approval/merge and any required post-merge validation.
- **#325** — draft first Residual Studio IDE/control-plane slice with Monaco/project explorer, observer surfaces and a server-side Factory snapshot/SSE projection. The mutation/control adapter remains deliberately read-only/unwired pending authoritative Factory integration. At this status check, its exact-head qualification had not completed and was **UNKNOWN / pending**. The PR is draft and explicitly lists build/browser/API validation still required; it is not accepted capability.
- **#326** — open Mission Control time-travel debugger implemented as a read-only historical view over the sanitized diagnostic buffer, not deterministic execution replay. Exact head `d879eeea5328f7ef60d3a2088b44a3e57aa343af` has the named technical workflows **PASS**, including Browser VM and PR-head Pages, while protected maintainer approval is **FAIL** and the advisory PR Agent run is **CANCELLED**. The PR remains unmerged and does not change accepted production capability.
- **#320** — open CSP/anti-clickjacking remediation. Its Vercel deployment status is **PASS**, while the protected maintainer-approval status is **FAIL / no exact-head attestation**. The PR remains unmerged, and post-merge production-header/Aikido validation is **UNKNOWN / not run**.
- **#321/#322** — Aikido-generated SAST remediation candidates for untrusted XML parsing and file-inclusion/path traversal respectively. Both are unmerged. Vendor confidence text is not acceptance evidence; repository validation remains required before any security claim changes.
- **#310** — draft live-core adapter binding remains unaccepted on an older base. It fails closed when no live evaluator is bound and adds durable evidence/conformance machinery, but its own declared dependency on the normative adapter spec being merged/tagged and pinned is still unresolved. It is not production release evidence.

## Accepted current-main changes relevant to claims

The following accepted changes remain useful context for current claims:

- **#200** — safer native setup defaults and bounded repair. Accepted onboarding behavior; not blank-environment qualification.
- **#205** — session-scoped private provider-channel restoration across Mission Control reload/remount. Accepted lifecycle behavior; not live-provider semantic proof.
- **#218** — bounded repair-context transport and shared attempt ceiling. Accepted repair-loop behavior; no verifier/review/integration/promotion authority expansion.
- **#201** — guided frontend and inline Puter setup UX. Accepted interface/provider-boundary behavior; not paid/live inference proof.
- **#233** — actionable failure-tail preservation and repeated-failed-patch detection. Accepted repair diagnostics; no authority expansion.
- **#248** — provider-load generation/lifecycle qualification on the embedded credentialless provider path. Accepted lifecycle/test behavior; not real-login or paid/live inference proof.
- **#197** — advisory PR-review workflow/configuration hardening. Repository tooling only.
- **#275** — exact-head maintainer-approval status publication repair. Governance only.
- **#276** — authoritative production Pages attempt trigger repair. Qualification infrastructure only.

None of the governance/qualification merges above modifies protected Factory/M4 implementation, verifier authority, evidence schemas or model acceptance authority.

## Exact-current-main production Pages evidence

Authoritative run: **`35410875305`**, attempt 1, exact `main@e7b72ad18df5729f16d36771971c8a8828d71a10`.

Observed scope:

- provider-session contract tests: **PASS**;
- publication contract tests: **PASS**;
- static-site/WebVM build: **PASS**;
- generated desktop+narrow browser proof: **PASS**;
- Pages deployment: **PASS**;
- published live desktop/guest verification: **FAIL**;
- published narrow acceptance after that failure: **NOT RUN / skipped**;
- overall production Pages qualification: **FAIL**.

Retained artifacts:

- `webvm-proof-35410875305-1`, artifact `10574552442`, SHA-256 `93b28db64c0a96e0eced1420f0b77ab4de528d3c73a9eb7f4db8d2a308005daa`;
- `github-pages-35410875305-1`, artifact `10574522534`, SHA-256 `78e8f766ccfb1f5995b534f2dd196b56969bc04d53bd7c62e0baf63132e535e4`;
- `webvm-live-proof-35410875305-1`, artifact `10574467841`, SHA-256 `2ff32b2a0e43073f3c3d2cf1c2e24451ff8f9b480d9b1cb4d36a68d4c9deda5d`.

Claim discipline:

- exact-current-main production Pages: **FAIL**;
- exact failure stage: **known at published live guest verification**;
- retained triage points to the already-identified provider bootstrap click race as the focused repository repair target, but #260 remains unaccepted;
- paid/live Puter success: **UNKNOWN / not established**;
- provider/model quality in this failed run: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**.

Do not rerun the unchanged failed revision merely to manufacture a green first attempt. A repair must land on a new exact revision and that revision must receive its own authoritative production attempt.

### Current repair candidate: #260

#260 is based on current `main@e7b72ad...` at exact head **`2a9455ee1c2001306521946e61376fae153211ad`**. Its diff remains limited to the provider bootstrap change plus regression coverage. Fresh exact-head technical workflows are green, including **Deploy GitHub Pages run `35412156544`**, Browser VM Demo CI, Controller/provider, Command Station, clean install, Factory ownership, Control Plane, measured-evaluation binding and the advisory PR Agent review.

The protected **Maintainer approval gate run `35412156574` is FAIL** because no fresh exact-head maintainer attestation exists. Therefore:

- #260 exact-head technical qualification: **PASS in the named PR-head scopes**;
- #260 maintainer approval: **FAIL / pending new exact-head human attestation**;
- #260 accepted into `main`: **NO**;
- current-main production Pages result: still **FAIL**;
- post-merge production qualification for a hypothetical future #260 merge: **UNKNOWN / not run**.

Historical technical acceptance on the older `fadf493...` head is not reused for the moved head.

## Live-provider boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice; both counted calls failed closed as `provider_protocol_invalid`. No candidate crossed the protocol boundary.

Therefore:

- historical live-provider result: **FAIL/BLOCKED in its exact scope**;
- candidate correctness for those calls: **UNKNOWN**;
- semantic verification: **UNKNOWN / not run**;
- exact-current-main paid/live candidate→verifier→receipt success: **UNKNOWN / not established**.

Publication, provider-session, bootstrap and qualification hardening do not substitute for fresh real-account semantic evidence.

## Factory / M4 boundary

M2/M3/M4 are implemented. `implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

Accepted #185/#187 protected-byte and ownership-baseline changes remain scoped to their reviewed behavior. The separate #139→ownership-baseline→fresh-qualification→#134 protected sequence remains independent. Namespace/capability-unavailable execution remains `BLOCKED`/`UNKNOWN`, not `PASS`.

Qualification-v1 work on the separate `testing/qualification-v1` branch remains branch evidence only. The deliberate protected-owner sequence in #303 merged to that testing branch, not production `main`. Follow-on #312 is a focused CI dependency repair for #152 and remains unaccepted. None of that branch work broadens current-main M4 qualification.

This documentation refresh changes no Factory/M4 implementation/tests, ownership baselines, qualification anchors, protected bytes, verifier authority, evidence schemas, provider authorization or acceptance authority.

## Retained M6 self-host evidence

The M6 record remains deliberately mixed:

- **#203 / M6-SPEC-001** — **FAIL**.
- **#204 / M6-SPEC-002** — **FAIL**.
- **#215 / M6-SPEC-003** — **FAIL**.
- **#217 / M6-SPEC-004** — **FAIL**.
- **#220 / M6-SPEC-006** — bounded corrected-path **PASS**: bad candidates were rejected before a later candidate satisfied frozen checks, received review, integrated, received a verification receipt and exported a release.

The #220 PASS does not erase earlier failures and does not establish general autonomous self-maintenance.

## M6.2 autonomous-discovery evidence

The M6.2 series also remains mixed and revision-bound.

Important retained cells include:

- **#244 / 007 and #246 / 007B** — provider/execution **FAIL** before a valid proposal was produced.
- **#249 / 007C** — bounded autonomous-discovery **FAIL** after malformed/repeated/truncated proposals exhausted the bounded repair path.
- **#250/#251/#252/#254** — typed-output path reached deterministic admission but repeatedly proposed already-measured evidence; bounded **FAIL** cells.
- **#255 / 007H** — semantic-review **FAIL** for causal/falsifiability/preservation defects.
- **#257 / 007J** — first retained bounded autonomous-discovery **PASS at formal MeasurementGap admission**, with receipt `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`.
- **#259/#262/#263** — post-gap/evidence-resolver/active-query **FAIL** cells where the Scientist continued requesting already-present or already-resolved evidence.
- **#264 / 007O** — integrity-valid workflow/receipt, but the scientific conclusion is **UNKNOWN** because the admitted metric identity was semantically ambiguous/misspelled. Receipt integrity does not prove semantic correctness.
- **#274 / 007S** — bounded **PASS** for registry/receipt semantic-binding controls.
- **#273/#277** — retained provenance/transcription **FAIL** cells; #277 positively demonstrates host-owned provenance binding while the overall trial still fails at Planner transcription.

Open #265 and the Metric Registry/derivation-graph work are trust infrastructure for this research line. General autonomous discovery remains **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its required positive semantic/derivation admission gates are actually satisfied.

Newer draft work such as **#299/#300** (semantic custody / derivation graph), **#293** (M7 governed recursive mission), **#313** (A2A feasibility spike), **#314** (Vector/Wire-Pod verified-learning experiment), **#316** (RAC evidence-gated improvement StationModule), **#317** (RESIDUAL-RT bounded-authority adversary-emulation research), **#318** (Web Command Station control-plane architecture), **#319** (M6-MESH-001 cooperative-efficiency pilot), **#323** (Research Workbench) and **#325** (Residual Studio) is explicitly unaccepted experimental/development work. #316's current exact head has green named workflows including maintainer approval, while #317's technical workflows are green and maintainer approval is **FAIL**. #319 has one retained bounded pilot cell with complete task verification but unresolved generality and security-review limits as described above. #323 currently has a failing exact-head Workbench/core qualification set and is blocked on accepted #288 before any first authoritative trial. #325 remains draft with authoritative mutation wiring and qualification still incomplete. None of these branches changes accepted production capability or authorizes self-merge/self-promotion.

## Stress-campaign governance blockers

Historical deterministic stress evidence remains active and must not be hidden by later unrelated green CI:

- **#207 STRESS-B1 — FAIL:** exhausted-budget accounting was observed after accepted integration/release.
- **#207 STRESS-B3 — FAIL:** a non-empty release materialized after terminal verifier failure.
- **#212 missing-usage case — FAIL:** integration and receipt issuance occurred before a later `usage_unknown_or_invalid` abort.

These results block stronger claims that budget/usage/verifier terminal state always precedes every authority effect. Open **#288** is the current focused pre-dispatch budget-admission repair candidate on exact head `0bc86441c295bd488bbd11f952f057e9266bb17e`. Its named technical workflows are **PASS**, but protected maintainer approval is **FAIL** and the PR remains draft/unmerged. Therefore #288 is **UNACCEPTED** and does not clear #207/#208/#212 until deliberately accepted and the applicable scenarios are requalified.

## Current priority blockers

1. **Production Pages:** retain current-main run `35410875305` as **FAIL**. #260 is technically green on its exact PR head but remains **HOLD** pending exact-head maintainer attestation and any required fresh independent technical acceptance; if it later lands, require the new main SHA's own first production attempt.
2. **Accounting/release ordering:** #288 is now reconciled to current main and technically green in its named exact-head scopes, but remains draft with maintainer approval **FAIL**. It must be accepted and #207/#208/#212 authority-ordering scenarios requalified before stronger fail-closed release claims or dependent Workbench trials proceed.
3. **Live provider:** retain a fresh exact-deployed-revision real-account Puter candidate→verifier→receipt success, or keep paid/live success `UNKNOWN`.
4. **WebVM reliability:** continue #120/#126 investigation and physical validation without promoting fallback success into heavyweight reliability.
5. **Release qualification:** complete true blank-environment install, recovery/host-loss qualification and selected elapsed soak for an exact release artifact.
6. **CI fan-out:** the acute #305 queue backlog has drained to zero, but #307 remains unmerged; structural duplicate-trigger/concurrency prevention is not yet accepted.
7. **M6/M7 and mesh research:** preserve PASS/FAIL/UNKNOWN/BLOCKED boundaries; general autonomous discovery/recursive self-improvement and general mesh/swarm efficiency remain unestablished, M6-008 remains blocked, and #319's security findings remain unresolved on its research branch.
8. **Research Workbench / Studio:** #323 is draft with exact-head Workbench/core qualification **FAIL** and an explicit dependency on accepted #288 before any authoritative trial; #325 is draft with authoritative mutation wiring and exact-head qualification still incomplete. Treat both as **UNACCEPTED**.
9. **Unaccepted security/UI work:** #324 is technically green on its PR head but maintainer approval is **FAIL**; #320-#322 remain open candidates; #326 is technically green but unapproved/unmerged. Do not treat security hardening, deployment success, vendor-generated SAST fixes or branch-only UI qualification as accepted production evidence.
10. **Protected sequences:** keep #139→ownership-baseline→fresh-qualification→#134 and Qualification-v1 work independent from unrelated green hosted CI.

## Documentation scope

`README.md`, `HARNESS.md`, this status document, the roadmap, research and evaluation prose are descriptive. `START-HERE.md` remains operator guidance and does not make an exact-current-main qualification claim. `implementation-status.yaml` remains accurate as an implementation-presence manifest and is intentionally unchanged.

No documentation-only change may be used to infer qualification beyond retained repository/CI/evidence artifacts.
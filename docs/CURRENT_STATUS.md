# RESIDUAL current status

_Current-state check: 2026-09-19 UTC against `main@e7b72ad18df5729f16d36771971c8a8828d71a10`._

This document is a human-readable status summary. Exact source at the named revision, exact-head workflow results, retained machine-readable evidence, explicit issues/PRs, and applicable maintainer/protected-byte governance are more authoritative than prose. Historical evidence remains bound to the revision and environment that produced it.

## Executive summary

Current `main` is **`e7b72ad18df5729f16d36771971c8a8828d71a10`**, produced by merged PR **#276** on 2026-09-19.

Two recent governance/qualification repairs are now accepted:

- **#275 / #268** — #275 repaired publication of the protected `maintainer-approval` result onto the exact live PR head after explicit exact-head human attestation; #268 is closed. This changes repository governance plumbing only and does not widen worker, verifier, Factory/M4, provider, evidence-schema or acceptance authority.
- **#276 / #267** — #276 removed the production Pages `push.paths` bypass that allowed some merged-main revisions to receive no authoritative Pages qualification attempt; #267 is closed. Every new `main` SHA is now expected to receive its own non-cancelling first production Pages attempt.

The first authoritative production Pages attempt for exact current main is **run `35410875305`, attempt 1, and it is FAIL**. Generated desktop+narrow browser proof passed. Deployment itself passed. Published live acceptance then failed at **`Verify published WebVM revision and real guest execution`**, and the subsequent published narrow-browser acceptance was skipped. The workflow retained the live proof artifact. This is production Pages qualification **FAIL for `main@e7b72ad...`**. The accessible retained workflow metadata does **not** establish the lower-level cause and does not establish a paid/live Puter, authentication, model-quality, Factory or M4 failure.

Exact-current-main automated evidence is therefore mixed rather than globally green. Controller/provider, Command Station and Factory ownership workflows have retained **PASS** results for their named exact-main scopes, while production Pages is **FAIL**. A PASS in one named gate does not override a FAIL in another.

Repository qualification infrastructure also remains under operational pressure. **#305 is open** with a retained snapshot of 1,267 queued Actions runs and 15 in progress at 2026-09-18T21:44Z. **#307** is an unmerged candidate to reduce duplicate feature-branch push fan-out while preserving non-cancelling production evidence. Queue pressure does not convert missing/queued qualification into PASS and does not erase retained first-attempt failures.

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
- exact lower-level root cause: **UNKNOWN from the currently inspected retained metadata**;
- paid/live Puter success: **UNKNOWN / not established**;
- provider/model quality in this failed run: **UNKNOWN / not established**;
- physical heavyweight-WebVM iPhone reliability: **UNKNOWN / unqualified**.

Do not rerun the unchanged failed revision merely to manufacture a green first attempt. A repair must land on a new exact revision and that revision must receive its own authoritative production attempt.

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

Newer draft work such as **#299/#300** (semantic custody / derivation graph), **#293** (M7 governed recursive mission), **#313** (A2A feasibility spike) and **#314** (Vector/Wire-Pod verified-learning experiment) is explicitly unaccepted experimental work. It does not change accepted production capability or authorize self-merge/self-promotion.

## Stress-campaign governance blockers

Historical deterministic stress evidence remains active and must not be hidden by later unrelated green CI:

- **#207 STRESS-B1 — FAIL:** exhausted-budget accounting was observed after accepted integration/release.
- **#207 STRESS-B3 — FAIL:** a non-empty release materialized after terminal verifier failure.
- **#212 missing-usage case — FAIL:** integration and receipt issuance occurred before a later `usage_unknown_or_invalid` abort.

These results block stronger claims that budget/usage/verifier terminal state always precedes every authority effect. Candidate repairs remain unaccepted until merged and the applicable scenarios are requalified.

## Current priority blockers

1. **Production Pages:** diagnose and repair run `35410875305` on a new revision; retain the exact-current-main FAIL and require a fresh first production attempt after any repair lands.
2. **Accounting/release ordering:** repair and requalify the #207/#208/#212 authority-ordering failures before making stronger fail-closed release claims.
3. **Live provider:** retain a fresh exact-deployed-revision real-account Puter candidate→verifier→receipt success, or keep paid/live success `UNKNOWN`.
4. **WebVM reliability:** continue #120/#126 investigation and physical validation without promoting fallback success into heavyweight reliability.
5. **Release qualification:** complete true blank-environment install, recovery/host-loss qualification and selected elapsed soak for an exact release artifact.
6. **Actions queue:** #305 remains open; #307 is unmerged. Reduce fan-out without cancelling or weakening required first-attempt evidence.
7. **M6/M7:** preserve PASS/FAIL/UNKNOWN/BLOCKED boundaries; general autonomous discovery/recursive self-improvement remain unestablished and M6-008 remains blocked.
8. **Protected sequences:** keep #139→ownership-baseline→fresh-qualification→#134 and Qualification-v1 work independent from unrelated green hosted CI.

## Documentation scope

`README.md`, `HARNESS.md`, this status document, the roadmap, research and evaluation prose are descriptive. `START-HERE.md` remains operator guidance and does not make an exact-current-main qualification claim. `implementation-status.yaml` remains accurate as an implementation-presence manifest and is intentionally unchanged.

No documentation-only change may be used to infer qualification beyond retained repository/CI/evidence artifacts.
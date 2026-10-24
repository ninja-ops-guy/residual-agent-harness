# AX-21 research maintenance — 2026-10-23 (append-only)

**Disposition:** NEW BOUNDED EVIDENCE / NEGATIVE RESULTS PRESERVED / NOT A RELEASE QUALIFICATION.
**Reviewed against:** frozen AX-21 pre-release baseline, previous 2026-10-18 check-in, and source-bound October 20–23 owner/reviewer handoffs. **No v1 release, merge, canary, live provider qualification, or autonomy improvement is established.** V1_RELEASE_HOLD remains the last verified decision.

## 1. Evidence sources and verification levels

This entry uses newly supplied, retained owner/reviewer archives, plus a read-only GitHub review. The ZIP files are evidence transfers, **not** GitHub release artifacts, independent live-host access, or authentication of the underlying swarm speakers. Local review independently checked ZIP CRCs, recomputed the stated R3 patch digest, counted raw JSONL audit records, and checked the A2/owner SHA256SUMS; it **did not rerun** the LEGION/DBOX test campaigns or access the live swarm room.

| Source transfer (date) | Outer SHA-256 | Directly inspected scope |
|---|---|---|
| `RESIDUAL-A2-Profile-Review-Packet-2026-10-20.zip` | `4b6bf290012953eb8b69b8bc4089100a22cb78bcc509d11ee7823a76b3de9216` | Scope proposal, deployment-profile worksheet, Cursor R2 evidence chronology; 4/4 SUM entries match. |
| `OWNER-HANDOFF-2026-10-22.zip` | `6340936400bbff58b600c8541ee551c525a6cc5238e10cea8996ec0ee9864307` | Decision packet, bounded PP-001 approval, AUTH admission staging, B4 rev2 caveats; 5/5 SUM entries match. |
| `independent-r3-review-bundle.zip` | `a94b851bfe7a54db30928624fc6edc0b0417530d72a16487509366b40aa32010` | Independent reviewer narrative, logs, exact R3 patch; patch hash confirmed locally. |
| `independent-broad-evidence-r2-handoff.zip` | `7c28e14bd21470cd1c05ca43fe10a4c9a0e3f5fc2901611141f61ecaaac71517` | Corrected audit-accounting report plus 707 raw audit files; 9,763 JSONL records independently counted. |
| `provider-r3-owner-integration-handoff.zip` | `5ed4e0a4cb787fc4dfc112bb70b43a15d8b0400f960edf0628437fa1c61173cf` | Read-only integration prerequisites, WebVM diagnostic limitations and source-lane binding. |
| `RESIDUAL-Offline-Demo-2026-10-23.zip` | `68d597c4677abcb3ece1d52f65a3a2eb729ab4c9ae30750022264817bfc386c4` | Offline presentation fallback; source Git blob identity independently recomputed; browser rendering NOT TESTED. |

All six ZIP archives passed ZIP CRC validation in this review. These hashes identify transfer bytes only; they do not authenticate room statements or provide an installed-executable chain of custody.

## 2. R3 provider-continuity review: narrowed repairs, not qualification

**Producer/reviewer-retained observations:** The provider authority successor derives from draft [PR #489](https://github.com/ninja-ops-guy/residual-agent-harness/pull/489) at HEAD `0472f46af1f137d1f808bf7b03cf12b4afa1f1ca`, base tree `06da1cbfdc4f9966fdb73b9cd29159a16a8f3dd2`. The R3 **computed** source tree is `04bbfe3b0737151d192c6d06bdb19b78280cea32`; full patch SHA-256 is `f2b6197fed68ec0b543b3a50a4239f0d0955a4bdfd9889f69e1a33a29ef8f9d6`. This is a reviewed patch/tree, **not** an R3 published commit or merged release composition.

The independent review reports **247 PASS** in a 74.90-second existing/previous-reviewer suite and **24 PASS** in a separate 4.53-second new reviewer suite; the transferred raw log endings match those counts. It closes two prior P2 findings **only in the tested synchronous Station/Continuity lifecycle**: (1) an unused HALF_OPEN reservation was stranded by final authority-callback refusal; (2) an unused HALF_OPEN reservation was stranded by quarantine-policy refusal. Scoped cleanup now tests invocation/attempt/route/breaker/event-sequence ownership, and distinguishes preparation/authority refusals before adapter entry from eligible provider errors after entry. Reviewer-only tests include competing writes, transaction rollback, late exception and BaseException controls. **No general exactly-once provider-side effect is proven.**

**Limitations retained:** The tests use synthetic providers and local stores. The 247-case run recorded 331 subprocesses whose network activity was not instrumented by the parent Python audit; the 24-case addition recorded zero subprocesses. Controlled interleavings are not exhaustive concurrency verification. Streaming/async, arbitrary custom adapters, installed-native behavior, actual provider I/O, live credentials and independently qualified restart behavior remain outside this result. The reviewer did not push, merge or perform a live provider call.

**Integration boundary:** The October 22 integration handoff records `target_head=null`, `target_tree=null`, `target_applicability=NOT_RUN`. The selected Closure composition has not admitted the underlying 39-path #489 feature plus the six-file R3 repair. Consequently, a passing R3 component review is **not** a passing selected-product or RC review. Overlaps in Station/service/security ancestors are identified but not resolved by a hypothetical merge.

## 3. Broad qualification: audit accounting was incomplete, then reconciled

**Observed negative-to-correction sequence:** Nine completed offline broad-run summaries initially counted **73 denials**. The corrected revision-2 record reconciles **122** blocked events: **49 previously omitted out-of-test** refusals (seven hostname and 42 shell/string subprocess operations across seven runs). The complete transferred archive contains **707 raw audit files and 9,763 JSONL records**, independently counted here; JSONL statuses total **707 guard installs, 8,927 allowed, 129 blocked**, including seven synthetic preflight blocks. A zero-test-attributed-denial check is *not* a zero-process-denial check.

The report's **1,775 unique-case composite** remains **1,515 per-test clean passes / 120 baseline failures / 127 skips / 13 blocked**. Counts have not been silently promoted to a complete PASS. The reviewed report includes an unexplained prior WebVM transient, excluded coverage and a mismatch from qualification-pinned Python/pytest versions. The 425.347-second broad run completed, so the earlier impression that it hung is not maintained.

**Falsified reporting assumption:** Capturing some audit events before collecting late process metadata is insufficient to support an unqualified 'no denials' process-wide statement. Revision-2 independently reconciles recorded evidence; it does not erase the original incomplete summary. Raw audit entries have no timestamps, `<collection>` is an attribution label rather than a proven chronological phase, and subprocess networking/native events may escape the Python-level observer. Neither the cause of all out-of-test events nor the WebVM transient has been demonstrated. Subsequent nearby-order WebVM PASS results on base and R3 are **non-reproduction**, not a root-cause fix, and add zero new unique-case pass credit.

**Paper relevance:** Evaluation apparatus completeness and correct denominators must be separate from per-test success. Mutation/negative controls need to target missing or late observations, not only explicit verifier rejection.

## 4. B4 watchdog negative evidence remains open

The October 22 owner handoff cites B4 rev2 package SHA-256 `5db16d04be44f3230ec52ff299cfcca8bc4686c0138fce9f695eff37f7dee55f`. Its addendum states that neg5's VOID **verdict** was replayed via cross-log fingerprint consistency but its **declared-anchor rejection path was not independently reproduced**, because the neg1–neg6 scenario expectations were absent from the delivered package. A fully rebound neg7 case reportedly did exercise the declared-anchor path. This distinction is an archived reviewer claim: the underlying B4 package was **not** transferred in this check-in.

The rev2 report's cited October 14 order is separately contested and is **not accepted as authorization** here. Owner acceptance of B4 remained PENDING on October 22. Live watchdog qualification is NOT_RUN; the older B4 compressed-window counterexample (26 records compressed to ~25 seconds accepted) remains preserved, and no 86,400-second actual RC soak is credited.

## 5. Owner rulings, operator interventions and explicit release non-results

The October 22 handoff **reports**: bounded A2 preparation authorized (not an RC); DELL7320/Piston as B1 operator; Piston conditionally chosen as Closure composition executor subject to incumbent/presence/capability/independent review; PP-001 approved only at **summary scope**; Cursor R2 approved for **prospective offline** work on its exact bytes only. The Cursor R2 offline PASS and associated 98 test + 50 subtest figures remain room/reviewer-reported here, not independently rerun; installed-native still NOT QUALIFIED.

PP-001 approved **requirements**, not outcomes: local-workstation, one trusted operator, restore-only (not HA); accepted-history RPO **0** with auxiliary RPO ≤300 seconds; operational recovery target 300 seconds, verified restore RTO 900 seconds; 86,400-second uninterrupted soak, 30-second samples, sticky failure, 365-day evidence retention; Piston incident owner and Tester independent acceptor. Ten additional worksheet obligations (including max sample gap, resources, backups, SQLite full-durability evidence, network scope and remote-worker annex) remain unapproved unless explicitly ruled or deferred; the profile **cannot freeze** yet. RPO 0 across a host-loss fault model requires independently surviving authoritative history, which is not established by a policy number.

The AUTH protected-worker malformed runtime-label finding remains unresolved: blob `de992173576b03ee0882d8fb713ea06f02a66d80` is excluded; the Factory/AUTH successor write admission is staged **but not approved**. B2 still lacks the frozen RC/profile and final apparatus hashes, and live soak GO remains blocked. Private order provenance remains PENDING; no retrospective authorization inferred. An October 22 A2 intake independent review is *reported* as 'ACCEPTED WITH CONDITIONS', not final exact composed-tree acceptance.

**Operator effort:** owner approvals, named operators/reviewers, negative-test reconciliation, seat/custody resolution, correction of faulty audit summaries, and integration planning are all human or supervised work. None is evidence of no-help fleet recovery.

## 6. Offline demo: source identity checked; behavioral proof explicitly limited

The October 23 fallback package contains a static simulated failure/repair/receipt UI, not a live RESIDUAL factory session. Its retained original `site/demo.html` bytes recompute to Git blob `1fcb6a99f14d7c399ac8c25deb2a582d1d4131fd` against accepted main. The package's own validation reports DOM-fixture and JavaScript-parse checks PASS, while **rendered browser playback remains NOT_TESTED**. Local source-byte identity does not prove its runtime claims or resolve the pending modern chat-walkthrough release/demo target.

## 7. Frozen AX-21 baseline comparison / preserved negatives

Frozen pre-release P5 status reconstruction: about **11 cold agent queries plus human synthesis**; routine external reconciliation **15+ manual reports/session**. B0-6 local 7B claim-to-verified-candidate observation: about **16.4 seconds** for that one path. **No comparable P5 after-condition, normalized operator-hours measure, independent three-host no-help reproduction, physical F6 completion, installed-native MissionSync, or autonomous fleet failover result was produced in this check-in.**

Preserve October 14 B4 elapsed-window falsification; October 16 wrong-port/different-database recovery harness and agent-authored PASS provenance contradiction; earlier qualification producer-staleness and test-discovery failures; unexecuted sealing, actual process attribution and uninterrupted RC soak; and the October 18 synthetic provenance study's fixed **11 false acceptances** across conditions despite changing conditional accepted-error percentages. No prior negative result is deleted by newer scoped positives.

## 8. Proposed RES-UP / ImprovementSpec disposition (not implementations)

- **`RES-UP-AUDIT-SNAPSHOT-COMPLETE-001` (candidate):** bind pre/post metadata audit windows, raw-file hashes, out-of-test counts, capture timing, and per-test vs process-wide denominators. Include injected late-denial controls and ensure a snapshot omission cannot yield a clean-process claim.
- **`RES-UP-B4-DECLARED-ANCHOR-PATH-001` (candidate):** transfer exact neg5 expectations and show that the reported acceptance path, not just final verdict, is reproduced; keep authority provenance separate from mechanism qualification.
- **Existing RC/soak ImprovementSpecs remain open:** elapsed minimum, real process attribution, independent watchdog, durable sealing. PP-001 requirements and R3 component PASS do not discharge them.
- **Existing provider pre-dispatch reservation work:** preserve two P2 first-failure controls and R3 repaired-contract tests; separately require exact composed integration and live admission. No duplicate 'closed globally' spec is introduced.

## 9. Release/reproduction conclusion and requested follow-through

Read-only GitHub inspection on October 23 still resolves accepted `main` to `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`; [#534](https://github.com/ninja-ops-guy/residual-agent-harness/pull/534) and [#539](https://github.com/ninja-ops-guy/residual-agent-harness/pull/539) remain draft/unmerged, with no newer qualifying published RC or GitHub release observed. The R3 component tree and new owner-packet decisions are **not** a current-main merge.

The defensible research result is **better bounded review of pre-provider reservation behavior, plus a demonstrated audit-accounting/reporting blind spot and explicitly unresolved B4 verification-path reproduction**. These are not demonstrations of secure-by-construction provider execution, human-calibration gains, general autonomy, lossless restore, or reliable production deployment. The original failure histories remain intact.

**Documentation only.** This check-in does not edit protected release files, accept a candidate, move pins, run a soak, or authorize a release.

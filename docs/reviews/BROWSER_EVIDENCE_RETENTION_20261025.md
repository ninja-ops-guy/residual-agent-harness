# Browser evidence retention candidate

Base: PR #543 at 66df3bc17a873d260cddda41b279429434542a41.
This is a sibling to #544, not a replacement for its digest repair. V1_RELEASE_HOLD remains in force.

## Inspection

The candidate retains goals, dispatched packets (including consented source excerpts), model responses, verifier messages and accepted values in guest traces. Browser projections copy that content into localStorage, previously automatically. Provider consent authorizes transmission, not a separate browser storage choice. A 300,000-character bound applies per saved projection, not to all origin storage; capture stops at 300 frames. Previously the frame cap was not marked truncated. The latest mission replaces the conversation projection. Transcript/preview records separately contain user text, assistant text and accepted file contents (16 turns and a bounded bundle). Eight visible history entries did not previously delete evicted records. New chat and Fresh artifact preserve history. No conversation deletion, evidence clearing or expiration was present.

## Correction

A separate unchecked control opts into future evidence saves for the current visit/conversation. It does not change provider consent or guest retention, and does not silently erase previously saved projections. Returning to a conversation restores existing evidence but requires a fresh checkbox selection for future saves. A visible disclosure explains content categories, shared-profile access, lack of expiry and distinct transcript/guest/provider/download storage.

Clear evidence removes the current conversation's saved projection and in-memory evidence/download state. Delete conversation also removes its transcript/preview cache, history entry and current pointer. Both are disabled during active missions. New chat/history switching clear stale projection/download state; asynchronous verification cannot repaint cleared evidence. Fresh artifact only detaches build lineage, as disclosed. Normal history eviction now attempts removal of both records. Failed deletion is reported for explicit deletion controls; storage failure does not claim a successful save or leave an older projection as its replacement. Restore bounds reject oversized/malformed entries. Frame-cap truncation is explicit. Guest trace files and their verification are untouched.

## Policy and qualification limits

No arbitrary TTL is introduced. Optional browser persistence and explicit deletion are useful controls independently of an owner-approved duration. A mandatory expiration period, broader transcript persistence consent and any legal retention promise require owner decisions/reconciliation with #528. Browser projections are not authoritative evidence; expiring them would be technically feasible without deleting guest traces.

This candidate is not secure erasure: browser backups, other open tabs, Terminal output, guest disk, exports and provider copies are outside these controls. Other tabs can retain/re-save data; coordinated cross-tab withdrawal remains unqualified. Older already-orphaned storage entries are not discoverable through history; browser site-data clearing is the fallback. Eviction deletion can fail when storage access is denied. Full-site clearing may affect other applications on the same origin. No encryption or multi-user isolation is claimed.

## Verification actually performed

- `node --test tests/webvm-retention-storage.mjs`: 8 PASS, using storage stubs and shipped helper functions.
- `python -m unittest tests.test_webvm_content_evidence tests.test_webvm_conversation_loop tests.test_webvm_evidence_durability -q`: 12 PASS. Covers hash-only default, content binding/verify_ledger, conversation behavior and guest durability.
- JavaScript syntax/module import and `git diff --check`: PASS.
- `tests/webvm-retention.cjs` supplies real Chromium DOM/storage checks for restore, clear, deletion and failures. NOT EXECUTED successfully: installed Playwright lacks its Chromium executable. No rendered desktop/mobile, accessibility, real guest or real provider acceptance is claimed.
- First attempts: pytest unavailable; legacy Node experimental flag unsupported by Node 24. Retried with stdlib unittest and native module support, without changing assertions.

#544's known digest defect remains on this branch deliberately. Compose and qualify both corrections before accepting browser chain-verification claims. Independent review and exact-head hosted checks remain pending. No merge, release, tag, deployment or hold change.

# Bounded SC-MESH v1 integration candidate

DRAFT / REVIEW ONLY / V1_RELEASE_HOLD. Broader Shared Comms is required for v1 by OWNER-20261023; this candidate does not complete that requirement. No merge, release, physical test, native-host activation or multi-host qualification is authorized or claimed.

## Exact inputs and selection

- Accepted main: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`, tree `7cd0d32be6fd61948f2fce753b122e5b6f0c6500`.
- #404: `7783081c858ad9ddf98b2e64e740e1104ae5d08b`.
- #493: `b53fb74c992830fe6d8912b62019c88bbf973f84`, tree `a4efc2b3ef702965c1b1070f692fa032382654a8`; contains #404 ancestry.
- #534 ledger inspected at `955daa7ef642f367350cbf62fd1b3047052b0d10`.
- Local conflict-free merge main + #493: `b50d4c87c69969b91c77d7d2c84d4270aac1e899`, tree `85c9b5cc53bcb8d2e87a77b818030353a8777215`.
- Tested source commit with five new tests: `30f4343a` (full identity in receipt.json). Later additions are evidence only.

The selected surface is existing Station SC-MESH and its attempt repair, not the distinct residual.mesh prototype. No #489, #492, #527 or post-v1 substrate implementation is imported. Main's newer reviewer-contract service changes remain present after the automatic merge. No new runtime implementation was required for these bounded tests.

## Executable coverage and remaining contracts

| Contract | Existing implementation / new verification | Remaining qualification |
|---|---|---|
| Attempt budgets | #493 binds attempt/fence/generation, archives prior budgets, preserves unknown consumption. New real HTTP restart -> successor -> result test checks old authority rejection, exact budget tuple, archive and conservative counters. | Final combined-tree concurrent admission and native runner qualification; no provider-side exactly-once claim. |
| Worker authority | Enrollment/scope/capability checks in #404. New HTTP tests reject remote-capability admission without consuming assignment and reject revoked worker results before refund/event recording. | Complete final composition authority review, native identity/capability proof and independent security review. These cases do not exhaust every endpoint or ownership attack. |
| Fencing | New generation/result rejection plus restart successor fence monotonicity and stale result/admission rejection. Existing tests cover lease expiry, stop and presence-only heartbeat. | Cross-host delayed delivery, partition/reconnect and final composition fencing. |
| Provider continuity | Existing station.continuity callback exercised with real Station admission and synthetic providers: expire/recover after primary error; fallback callback rejects before fallback I/O. | This is callback composition supplied by the test, NOT proof #489 is wired into the native runner. Resolve classification/settings conflicts; bind route identity, readiness/admission, budgets, revocation and durable invocation state to the same task tuple. |
| Durable recovery | Existing SQLite startup recovery blocks interrupted lease; new HTTP successor test preserves old charge and immutable archived budget. Existing fixtures exercise subprocess/crash transactions and outbox/inbox recovery. | Result reconciliation and acceptance are separate transactions; lost-result replay, indeterminate provider outcomes and cross-host recovery remain open. |
| Evidence binding | New real result event checks worker/project task context, attempt/generation/fence, response digest, provider attempts and reconciliation. Result stops at review_ready. | Worker-reported usage and digest consistency are not independent execution/provider attestation or candidate/package binding. Bind actual installed bytes, independent verifier identity, final composition receipt kernel and artifact transport. |

## Compatibility and overlapping candidates

Read-only `git merge-tree --write-tree` probes used the local main+#493 tree; no conflict-marker tree was selected or tested as a candidate.

- #489 `0472f46af1f137d1f808bf7b03cf12b4afa1f1ca`: conflicts in `ai_providers/adapters/_http.py` and `residual/station/models.py`; additional shared surfaces are core, server and service. The mesh continuity tests allow auth/rate-limit fallback under legacy policy, while #489 explicitly restricts automatic fallback. Textual conflict resolution alone is insufficient: select one fail-closed policy and qualify the joined execution path. The inspected `repair/provider-continuity-toxic-authority-0472` ref points to the same #489 head, not a newer repair.
- #492 `8b69b8a538465a0590e5676841145d51fe2c7c6c`: merge-tree clean, overlaps store/server and project budget authority; not imported or behaviorally qualified here. Preserve outstanding assignment reservations and unknown consumption when exposing/extending ceilings.
- #527 `f9c1a82b381420d4337391f0803983fb178cd197`: conflicts in `residual/station/contracts.py` and `residual/station/service.py`, plus shared server changes. Mission Control/AUTH/OpenClaw is not in this candidate.
- Research-isolation successor `9864c62d5cafb04f5cf07f8da1026f8858aabe69`: same contracts/service conflict; removing research files does not resolve mesh integration.
- #537 `941f203f14284208a40017aa85d169e1b803c216` documents absence of Station SC-MESH in #527. Its package-binding result cannot transfer to a mesh-inclusive composition.
- #495 is an integration specification, not implemented scheduler/coordination proof. #535 native evidence, #538 debugger and #539 soak work require final composition qualification; none is imported here.

## Fresh local verification

Python 3.12.14, Linux isolated checkout; temporary Station databases, localhost HTTP and synthetic providers only. Normal package imports; no import stubs. Existing fixtures are reused from test_mesh_budget_boundaries and test_sc_mesh_continuity rather than copied.

- `python -m unittest tests.station.test_mesh_v1_integration -v`: 5 PASS (new tests).
- `python -m unittest discover -s tests/station -t . -v`: 100 PASS including the five new cases. First run had the new test untracked; a second run on the committed source is retained separately. No full-repository PASS claim.
- `python -m unittest discover -s tests/qualification -t .`: FAILED to load seven pytest-dependent modules (`ModuleNotFoundError: pytest`); 27 unittest entries, seven errors, one skip. This command also does not collect pytest function tests. Retained as an unavailable broader check, NOT qualification success. Run the repository's proper pinned pytest/CI qualification before promotion.
- Authored changes: `git diff --check b50d4c87 HEAD` PASS. Full diff against main reports two inherited Markdown trailing-space lines in `docs/station/SC_MESH_001_REQUIREMENTS.md`; left unchanged to preserve imported source.

Historical #404/#493/#489 reported results remain inherited claims, not new verification. New Station execution is evidence only for this bounded combined source. Neither fixture test names mentioning release nor synthetic qualification JSON in logs grant release authority.

## Reproduce and advance

Check out this draft branch, then run the two unittest commands above. Install the declared test/qualification dependencies in an isolated environment before running the repository's normal pytest and CI gates. Use the source hashes in receipt.json to confirm the tested source.

Next integration owner must resolve #489 and #527 overlaps, implement the native continuity/evidence binding contracts, obtain independent review, run exact installed-package and supported-platform qualification, and obtain separately authorized native/multi-host tests. Rollback/service setup documents are plans, not demonstrated host containment or rollback. Final candidate selection, owner/maintainer gates, soak and release authorization remain open. V1_RELEASE_HOLD is unchanged.

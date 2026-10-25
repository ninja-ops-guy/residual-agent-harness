# SC-MESH / native provider continuity composition — 2026-10-25

DRAFT / INDEPENDENT REVIEW REQUIRED / V1_RELEASE_HOLD.

## Source selection

- #542: 77db333ce75361a26db0167162b8238741cc4e47.
- #489: 0472f46af1f137d1f808bf7b03cf12b4afa1f1ca.
- Accepted main: 8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2.
- Inspected continuity PR search and remote branch refs. `repair/provider-continuity-toxic-authority-0472` is exactly #489, not a newer repair. `repair/aud1-continuity-admission` is the separate older result-retry lane. No newer replacement for these provider bytes was located. #527 remains separate/uncomposed.

Both candidate ancestries are retained. The diff against #542 necessarily imports #489; review the additional corrections against both parents. Existing historical evidence is not reclassified as evidence for this tree.

## Corrections

1. Resolve HTTP classification in favor of #489's structured error-code allowlist on 402/429, including credit exhaustion and usage evidence. Bare 429, arbitrary text, error.type, malformed JSON shapes and non-string codes cannot become quota exhaustion. Authentication denies failover. Error-body reads stay bounded to 8 KiB, close responses, and fail closed on unreadable bodies.
2. Retain OFF default and mesh capability defaults. Remove the duplicate QUOTA_EXHAUSTED enum produced by the textually successful core merge (which otherwise prevents module import). Retain legacy error fields as compatibility data, not policy authority.
3. Stateless ContinuityProvider uses the shared classification allowlist, never retryable/failover_allowed as authority. Any remote fallback requires the durable path. Existing explicit local-only helper behavior remains bounded by the eligible classification set; it is not a durable recovery implementation.
4. Add `mesh_model_call` as an in-process bridge from authenticated enrollment + original claim to #489's actual Continuity journal through Station model_call. Each provider call rechecks enrollment, readiness, project generation, owner, lease, fence, attempt, route and capabilities, then reserves a mesh attempt. Quarantine, optional extension policies, readiness and BL-006 admission remain in the native path. Invocation identity includes attempt/fence/generation/worker and request content. Default unbound model_call on mesh-owned tasks fails closed.
5. Per-call mesh accounting and whole-plan execution admission are explicitly different contracts: the bridge rejects already whole-plan-admitted tasks before I/O, avoiding duplicate reservation. It consumes assignment holds with the existing reserve_mesh_attempt transaction. It does not silently replace MeshClawRunner/OpenClaw's whole-plan execution interface.

## Executable regression coverage

`tests/continuity/test_mesh_composition.py`: 27 cases using real Station/SQLite/mesh enrollment and native Continuity; synthetic adapters and readiness fixtures only. Eligible 402/429/503; bare 429 and authentication/malformed codes; expired/revoked authority; changed generation/fence/attempt; exhausted budget; primary and fallback interruption before I/O and before result persistence; recorded-result reopen/reuse without second execution; OFF/ASK/not-ready; whole-plan double-charge rejection; unbound-call rejection.

Store reopen tests preserve the still-valid original claim. They do not claim full Station startup renews authority: startup recovery invalidates interrupted work and an old claim must remain rejected. No provider-side exactly-once guarantee is asserted. Ambiguous started calls stop with INDETERMINATE_PROVIDER_OUTCOME. Journal acceptance remains evidence, not mission approval or integration.

## Actual validation / failures

Python 3.12.14; isolated venv, pytest 9.1.1, declared defusedxml/PyYAML dependencies. No live provider or production host used. Existing HTTP suites use disposable loopback fixtures.

- Initial environment: pytest absent; installed in isolated /tmp venv.
- First merge collection: duplicate enum caused three collection errors; corrected. No tests ran in that collection.
- First affected run: 147 passed / 1 failed / 22 subtests. Stateless no-next-candidate error compatibility corrected; original log retained.
- Joined bridge final: 27 passed (joined-final.log).
- Expanded run: 245 passed / 1 failed / 69 subtests (expanded.log). The toxic-provider truncation fixture invokes runner on an unclaimed task; expected truncation is preempted by authority_rescinded. The identical node fails on untouched #489 (baseline-toxic.log). This failure was not weakened or suppressed in source.
- An attempted command named nonexistent tests/test_ai_providers.py and tests/test_modular.py: no tests ran; corrected to discovered tests/modular and tests/test_providers.py paths.
- Final affected subset: **245 passed, 69 subtests passed**; command and result are in affected-final.log. It excludes the toxic-provider matrix; the failed expanded result above remains part of the disposition.

Reproduction:

```
python -m pytest tests/continuity tests/station tests/modular tests/test_providers.py tests/qualification/test_provider_mission.py -q
python -m pytest tests/qualification/test_toxic_provider_matrix.py -q
```

## Limits and remaining gates

Not full pytest qualification, not a full release composition, not MESH_QUALIFIED, and not production ready. The bridge is an explicit in-process entry point, not an installed remote runner wiring claim. Remote OpenClaw whole-plan continuity, atomic distributed revocation/I/O boundaries, provider-side idempotency, independently verified execution evidence, #527/containment composition, installed/native and multi-host qualification, exact-head hosted checks, independent review, maintainer approval, and release gates remain open. Current checks immediately precede provider calls; they do not promise atomicity across SQLite checks and external I/O.

No merge to main, deployment, live-provider testing, host changes, tag or release. V1_RELEASE_HOLD remains active.

Compileall passed. Authored source whitespace check passed; byte-preserved BL-006 vendor whitespace remains inherited and exempt. Raw first-suite output is gzip-preserved.

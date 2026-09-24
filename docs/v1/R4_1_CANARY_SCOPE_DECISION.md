# R4.1 bounded-canary scope decision

Status: **UNAPPROVED / canary remains unauthorized**.

This worksheet closes only the scope-decision portion of master-ledger items `V1-PC-002`, `V1-PC-003`, and `V1-PC-004`. It does not change the historical R4.1 `READY_FOR_CANARY` qualification and cannot authorize execution by itself.

The frozen candidate commit is not available in the connected GitHub repository, so this convergence lane has **not independently reproduced** the #426 synthetic observations. The source record remains #426 at `494dac7c0702a285c33ceddd3f0237f63ceea425`. A decision below must therefore distinguish a reported observation from an independently reproduced defect.

For each finding choose exactly one disposition before canary GO:

- `REQUIRE_SUCCESSOR`: treat the behavior as in-scope for the live canary boundary; prepare a separately identified successor candidate, fix it, and freshly requalify before any live execution.
- `EXCLUDE_WITH_ENFORCEMENT`: explicitly exclude the adversary/failure mode from this *bounded* canary, and prove the exclusion in preflight. This does not classify the finding as safe or post-v1 by itself.
- `NO_GO_PENDING_REPRODUCTION`: do not execute the canary until the finding can be independently reproduced/dispositioned on authoritative candidate bytes.

`UNDECIDED` is fail-closed.

## PC-002 — receipt semantic binding

Reported observation: under synthetic authenticated-transport substitution, malformed receipts and receipts naming another project or operation were reportedly persisted as local `ACKED` state.

Decision: `UNDECIDED`

If `REQUIRE_SUCCESSOR`, acceptance must include at minimum:

- receipt is an object with required fields;
- exact project and operation ID bind to the pending durable intent;
- any actor/payload identity carried by the protocol is bound to the same intent rather than merely syntactically accepted;
- malformed, missing-field, explicit-null, wrong-project, wrong-operation, stale, and contradictory receipts leave the operation non-ACKED and produce zero unsafe follow-on action;
- fresh exact-candidate qualification replaces, rather than inherits, R4.1 acceptance evidence.

If `EXCLUDE_WITH_ENFORCEMENT`, preflight must bind the exact trusted receipt endpoint/server implementation and authenticated transport used by the canary, prohibit synthetic/alternate receipt providers, and state explicitly that malicious/semantically incorrect authenticated receipts are outside this single-operation canary claim. The release/R5 backlog must retain the unresolved broader receipt-binding requirement.

Evidence/rationale: `UNDECIDED`

## PC-003 — stored-payload digest on recovery

Reported observation: after synthetic durable-state tampering, recovery reportedly used the modified stored payload without verifying its stored digest before POST.

Decision: `UNDECIDED`

If `REQUIRE_SUCCESSOR`, acceptance must include:

- recompute the durable payload digest before any receipt lookup/POST action where the digest is intended as an integrity authority;
- mismatch deterministically enters a non-success state such as quarantine/fail-closed;
- digest mismatch causes zero POST and cannot become `ACKED` through the normal recovery path;
- corruption/tamper evidence is retained rather than rewritten;
- fresh successor qualification covers intact and mismatched states.

If `EXCLUDE_WITH_ENFORCEMENT`, preflight must establish a clean canary outbox/state baseline, prohibit local-state mutation/fault injection during the run, retain before/after hashes, and state explicitly that local SQLite/file corruption or malicious local tampering is outside the bounded canary claim. Production durability/corruption gates remain open.

Evidence/rationale: `UNDECIDED`

## PC-004 — concurrent recovery ownership

Reported observation: two synchronized recoverers reportedly both observed receipt absence and each issued a POST; receiver idempotency may hide sender-side split ownership.

Decision: `UNDECIDED`

If `REQUIRE_SUCCESSOR`, acceptance must include:

- a single durable/fenced recovery owner for each operation;
- two or more simultaneous recovery processes cannot independently obtain send authority for the same pending operation;
- stale-owner takeover/restart behavior is deterministic and bounded;
- receiver idempotency is not used as a substitute for sender authority uniqueness;
- fresh successor qualification includes real process-level concurrency, not only same-thread serialization.

If `EXCLUDE_WITH_ENFORCEMENT`, the canary topology must prove a single sender/recovery owner for the full window. Preflight must identify the exact process/service instance, reject/abort on a second eligible instance, and prohibit parallel operator invocation of the recovery procedure. This exclusion applies only to the bounded canary and cannot establish multi-process production safety.

Evidence/rationale: `UNDECIDED`

## Combined decision constraints

1. A finding cannot be labeled `POST_V1` merely because it is excluded from this canary; broader production applicability is decided separately by the v1 deployment scope and R5 qualification program.
2. Any `REQUIRE_SUCCESSOR` selection invalidates transfer of the frozen R4.1 candidate's qualification to the changed bytes. The successor must have a new identity and fresh evidence.
3. Any `EXCLUDE_WITH_ENFORCEMENT` selection must map to a concrete, independently reviewable preflight assertion in the final canary procedure. Prose-only intent is insufficient.
4. `NO_GO_PENDING_REPRODUCTION` keeps `V1-CAN-001` blocked.
5. The post-canary verifier must be frozen against the exact procedure/candidate actually authorized; it must not be silently edited after results are observed.

## Approval receipt

Before `V1-CAN-001` can become eligible for authorization, retain:

- all three final dispositions;
- rationale and evidence for each;
- SHA-256 of this completed decision artifact;
- exact candidate HEAD/tree selected for the canary;
- exact canary-package and post-canary-verifier identities;
- identity of owner/change authority and independent canary reviewer;
- approval timestamp;
- explicit statement that no `UNDECIDED` remains.

This receipt is a scope approval only. The separate deployment adapter, expected service baseline, safe evidence destination, authorization receipt, operator identity/time window, and explicit GO required by `V1-PC-005` / `V1-CAN-001` remain mandatory.

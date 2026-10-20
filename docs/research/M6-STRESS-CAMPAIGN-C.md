# RESIDUAL M6 Stress Campaign C — Deterministic Failure Matrix

**Status:** preregistered before execution  
**Frozen baseline:** `699e2869e294fe157b4bfd73a272057683a2f7e0`

Campaign C isolates provider and reviewer failure semantics using a local Ollama-compatible deterministic endpoint. No external model is involved.

## C1 — Malformed structured output
Runner returns syntactically invalid JSON content while the HTTP/provider envelope is valid.
Expected safe behavior: no integration; task enters repair path; evidence records provider usage and failure.

## C2 — Transient provider 500 then success
The first runner HTTP request returns 500, subsequent requests return a valid candidate, and reviewer approves.
Measure whether provider/router retries, how attempts are accounted, and whether a transient transport fault consumes a Station task attempt.

## C3 — Missing usage accounting
Runner/reviewer return valid candidates/verdicts but omit token counts.
Expected host behavior: unknown usage triggers budget abort. Observe whether any integration/export occurs before the authoritative abort.

## C4 — Invalid reviewer schema
Runner returns a valid candidate; reviewer returns `{"approved":"yes","findings":[]}`.
Expected behavior: invalid verdict must not integrate or issue a task verification receipt. Measure task state and whether repeated review calls consume passes without consuming task attempts.

## C5 — Reviewer denial recovery
First reviewer returns `approved=false` with a concrete finding. A subsequent runner returns a valid candidate and reviewer approves.
Measure repair state, attempt accounting, and recovery.

## Rules
- First valid execution is authoritative.
- All jobs check out the experiment head.
- No result is retried away.
- Workflow success means experiment apparatus completed; RESIDUAL-level failures remain data.
- Retain complete event chains, usage records, task states, and receipts.

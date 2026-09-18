# G1 Reconciler — Adversarial Lifecycle Vector Corpus

> **Status: test/fixture surface only.** This document and the corpus encode *normative
> semantics*, not implementation-specific assertions. Swarms F/G's reconciler contracts
> are still stabilizing; when they land, they bind to these vectors rather than the
> vectors being rewritten for them.

Base: `ninja-ops-guy/residual-agent-harness @ 3cff6bcd52e352a6ba048c958949a7bbb2a039eb`
(all seam citations re-verified against this HEAD).

## Normative semantics under test

1. **Exactly-one-terminal is storage-enforced.** Admission to a terminal state goes
   through compare-and-swap on the state row plus schema uniqueness constraints
   (`residual/factory/runtime_journal.py:76-90, 368-382`). A watchdog is evidence
   collection (`termination_provenance.py`), never a correctness mechanism. Any vector
   that passes only when the watchdog is active is a **predicted-FAIL finding** against
   the reconciler design (G1V-14).
2. **Projection reconstruction from the authoritative store.** Dedupe, pending sets,
   terminal values, and generation counters are rebuilt from the durable journal/event
   chain across writer restart and recovery — never from volatile memory
   (G1V-05, G1V-10, G1V-11, G1V-17).
3. **First-failure retention.** The first committed terminal outcome is retained
   verbatim; conflicting later terminal attempts are typed rejections and never rewrite
   the row or append a second terminal event (G1V-16; DSM terminal states are absorbing,
   `residual/dsm/ownership.py:21-31`).
4. **UNKNOWN / BLOCKED are never PASS.** `LeaseRead.state == 'unknown'` may arise only
   from an unreadable store or an exhausted caller budget, with a bounded
   `(exc_type, sqlite_errorcode)` diag; it must never be retyped as revocation or pass
   (G1V-13, `runtime_journal.py:314-353`).

## Corpus layout

`tests/reconciler/vectors/g1_adversarial_vectors.json` — machine-readable corpus.
Each vector carries:

| Field | Meaning |
|---|---|
| `id`, `title`, `category` | G1V-NN identifier, human title, fault class |
| `prior_art` | LN-NN / F-NN traceability to the wave-a A2 corpus |
| `normative_reference` | which normative semantic the vector encodes |
| `seam` | file:line citations, verified at the base SHA above |
| `setup` / `fault_injection` / `stimulus` | the adversarial scenario |
| `expected_outcome` | typed outcome tokens (see `typed_outcome_vocabulary` in the corpus) |
| `evidence_destination` | what the runner must capture as evidence |
| `execution.status` | `executable` (bound today) or `pending_implementation` |
| `execution.binding` | runner executor key when executable |

Fault classes covered: kill-between-transitions (G1V-01/02/04/15), commit-before-ack
crashes (G1V-05 DSM journal window; G1V-06 SQLite `synchronous=FULL` COMMIT window via
a subprocess killed with `os._exit` after COMMIT), concurrent terminal attempts
(G1V-07 double-finish race, G1V-08 revoke-vs-finish), stale projections (G1V-09
expired/forged/mismatched Station lease, G1V-13 lease-read tri-state), duplicate events
(G1V-03 identity uniqueness, G1V-10 inbox dedupe across restart), writer restart
(G1V-11 outbox catch-up, G1V-17 projection reconstruction), and
scheduler-unavailable-during-recovery (G1V-12: force-block + `worker.expired`, never a
terminal success for a lost scheduler context).

## Runner

`tests/reconciler/run_vectors.py` (stdlib-only):

```
python tests/reconciler/run_vectors.py --report report.json [--vector G1V-07 ...]
```

- Loads the corpus, executes every vector whose `execution.status == "executable"`,
  and compares the actual typed outcome against `expected_outcome`.
- Produces a machine-readable JSON report: per-vector `status` (`PASS` / `FAIL` /
  `UNKNOWN` / `BLOCKED`), detail, elapsed time, plus counts. `UNKNOWN` (no current
  implementation binding) and `BLOCKED` (harness defect) are **never** counted as PASS.
- Exit code: `1` if any vector FAILs, else `0`. First-attempt failures are retained in
  the report; nothing is retried into green.

Result on the base SHA above: **16 executable vectors PASS, 0 FAIL, 0 BLOCKED;
1 vector (G1V-14) UNKNOWN / pending_implementation.**

## How F/G implementations bind

When the Swarm F/G reconciler contracts stabilize:

1. For each `pending_implementation` vector, add an executor keyed by
   `execution.binding` (or register a new binding in the corpus) that drives the
   vector through the reconciler's public contract. Do not weaken
   `expected_outcome` to obtain green — a mismatch is a finding, not a test bug.
2. G1V-14 (watchdog-independence) specifically requires the reconciler to declare how
   the watchdog/termination machinery is disabled for the suite; the expected outcome
   is an empty outcome diff vs the storage-only run.
3. New normative vectors go into the corpus JSON first (with `seam` citations verified
   against the then-current main), then get runner bindings.
4. Vectors whose semantics require capabilities the standalone build lacks (e.g. a
   consensus-backed durable lease table — see wave-a storage-fault-model predicted-FAIL
   register) must be tagged with a `requires` capability and remain UNKNOWN until the
   capability lands.

## Scope and guardrails

Tests/fixtures only. No Factory/M4 implementation, ownership pin, verifier authority,
receipt authority, frozen research definition, or shared evidence schema is modified.
No workflow changes. No capable-runner, blank-VM, real-provider, host-loss,
elapsed-soak, production, or research qualification is claimed by this corpus.

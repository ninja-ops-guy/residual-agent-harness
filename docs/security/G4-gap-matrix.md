# G4 Gap Matrix — Secret Crossings and Snapshot Hazards

> Audit deliverable (tests/audit only; no production changes). Base: `main`
> `3cff6bcd52e352a6ba048c958949a7bbb2a039eb`. Companion executable evidence:
> `tests/secrets/test_secret_crossing_canaries.py` (9 tests, unique `CANARY-*`
> tokens per surface). Prior art: A2 secrets/snapshot adversarial spec
> (procedures S-01..S-06), re-verified seam-by-seam against current main.
> Toxic-provider precedent: PR #152 (`tests/qualification/test_toxic_provider_matrix.py`).

**Owner's key rule (tested):** removing secrets from environment variables is
INSUFFICIENT protection for snapshots — secret material may remain in process
memory. Verdicts: PASS = sanitized/absent with executable evidence;
PARTIAL = some paths clean, documented residual crossing; ABSENT = protection
mechanism does not exist; UNKNOWN/BLOCKED are never reported as PASS.

## Secret-crossing matrix

| # | Source surface | Destination surface | Retained? | Sanitized? | Verdict | Evidence |
|---|---|---|---|---|---|---|
| G4-01 | env var `OPENAI_API_KEY` etc. | new adapter handles after `del os.environ` | No (new handle gets `None`) | n/a | **PASS** | `test_env_clear_prevents_new_handles_but_does_not_revoke_existing`; seam `residual/modular.py:44` (env fallback in `make_adapter`) |
| G4-02 | env var / saved credential | pre-existing adapter instance after env removal | **Yes** — handle keeps `api_key` | No | **PARTIAL** (env scrubbing is not revocation; documented) | same test, post-removal assertion on first adapter |
| G4-03 | upstream HTTP error body embedding secret | `ProviderError` message / `to_dict()` | No | Yes — body never echoed (`ai_providers/adapters/_http.py:47-63`; `core.py:139-151`, `__str__` = `"provider: code"`) | **PASS** | `test_upstream_error_body_never_echoed` |
| G4-04 | credential + toxic 401 body | observation export (`station/observability.py:94`), events feed, raw station SQLite | No | Yes — router `_emit` payloads carry provider/model/bytes only (`ai_providers/router.py:31-66`) | **PASS** | `test_cleared_env_secret_absent_from_observations_and_db` (loopback 401 server, export + events + raw DB bytes scanned for raw/base64/hex/url/utf-16le variants) |
| G4-05 | env secret | **process memory after env removal + ref drop + `gc.collect()`** | **Yes** (CPython immutable str / arenas) | No — impossible at language level | **PARTIAL → documented hazard** (owner's key rule confirmed) | `test_memory_residency_after_env_removal_documented_hazard` (gc object-graph scan and/or `/proc/self/maps`+`/proc/self/mem` region scan; attestation recorded; if unreproducible the test reports UNKNOWN, not PASS) |
| G4-06 | secret in SQLite row, then `DELETE` | raw `.db` file freelist/unallocated pages | Yes unless `secure_delete` | Only on builds compiled `SQLITE_SECURE_DELETE` (this audit host: `secure_delete=1`, bytes zeroed; with pragma off, bytes persist until `VACUUM`) | **PARTIAL → documented hazard** (SQL-level absence is not proof of absence; raw-file scanning mandatory) | `test_sqlite_freelist_retains_deleted_secret_rows` |
| G4-07 | secret in watchdog `kill(reason=…)` dict | durable `TerminationRecord.request_action` | **Yes** — deep-copied verbatim (`factory/termination_provenance.py:230,333`) | No | **ABSENT** (no redaction; documented) | `test_termination_record_persists_reason_payload` (live pidfd kill of child) |
| G4-08 | secret in `artifact_payload` | `EpistemicMemoryStore` plaintext JSON files | **Yes**, verbatim; perms = umask default | No | **ABSENT** (no redaction/at-rest protection; documented) | `test_memory_store_persists_artifact_payload_verbatim` (`memory/store.py:46-74`) |
| G4-09 | secret in operator-authored spec markdown | `markdown()` export | Yes, verbatim (`station/store.py:309-`) | n/a — operator-local artifact | **PASS (classified)** — operator-local, not a leak unless transmitted | `test_markdown_and_cloud_report_boundaries` |
| G4-10 | secret embedded in project **goal** | `report()` cloud-review delta (`station/store.py:286-304`) | **Yes** — `goal` is carried verbatim | No | **PARTIAL → policy gap** (goal text crosses the cloud trust boundary; no content screening on cloud-bound packets) | `test_markdown_and_cloud_report_boundaries` (goal canary present in report; spec canary absent) |
| G4-11 | task `instruction` text | `report()` | No — report includes only `id/title/state/depends_on/head_commit/findings` | Yes (by field selection) | **PASS** | `test_markdown_and_cloud_report_boundaries` (spec/instruction canary absent from report) |
| G4-12 | cleared env credential | resurrection via env fallback | Feature: `modular.py:44` re-reads env at construction | n/a | **PASS (documented feature)** — audit records inheritance as such | `test_env_clear_prevents_new_handles_but_does_not_revoke_existing` |
| G4-13 | crash dumps / faulthandler / emergency journal after G4-05 retention | snapshot artifacts | Probable (follows from G4-05) | No | **UNKNOWN** — not exercised in this suite; consequence vector of G4-05 | inference from G4-05 attestation only; no dump executed |
| G4-14 | WebVM browser surface (sessionStorage, BroadcastChannel, guest FS) | guest-reachable storage | Not executed here | — | **BLOCKED** — requires browser harness (`demo/vm/provider.js`); out of scope of this Python-only suite | prior art S-06; needs WebVM runner |

## Retained first-attempt failures (not weakened)

1. `test_scanner_negative_control` — initial assertion `== ["raw"]` failed because
   URL-safe canaries make the url-encoded variant byte-identical to raw. Fixed by
   asserting `"raw" in hits` (scanner semantics corrected, not weakened).
2. `test_sqlite_freelist_retains_deleted_secret_rows` — initial unconditional
   freelist-retention assertion FAILED: this host's SQLite is compiled with
   `SQLITE_SECURE_DELETE` (`PRAGMA secure_delete = 1`), which zeroes deleted
   bytes. The hazard is real but build-dependent; the test now proves retention
   with `secure_delete=OFF` and asserts zeroing when the build default is on.
   Failure retained as a finding: absence claims must name the SQLite build
   configuration they depend on.
3. `test_termination_record_persists_reason_payload` — first attempt treated
   `termination_record` as a property; it is a method
   (`termination_provenance.py:348`) that raises until the process is reaped.
   API-misuse failure, corrected.

## Canary plan for production snapshots

1. **Injection**: before any production snapshot/upgrade/rotation drill, inject
   one unique `CANARY-*` token per surface (env var per provider kind, saved
   credential, upstream-body simulation, watchdog reason payload, memory-store
   payload, spec/goal text). One canary per surface → unambiguous provenance.
2. **Scrub step**: perform the operator runbook's "secret removal" (env scrub,
   settings clear) exactly as documented.
3. **Scan destinations** with all encodings (raw, base64, hex, url, utf-16le):
   - observation exports and `observations` table rows (SQL **and raw file**);
   - station SQLite raw bytes including freelist pages (state `PRAGMA
     secure_delete` of the build alongside the result);
   - emergency journal / `TerminationRecord` payloads;
   - `runtime_journal.export_jsonl` output, release zips, `report()` and
     `markdown()` artifacts — classify operator-local vs cloud-bound before
     judging;
   - memory store JSON files (dir perms recorded);
   - **process memory of any long-lived process** that ever held the secret
     (`/proc/<pid>/maps`-guided scan). Per G4-05, expect retention ⇒ the only
     valid revocation procedure after secret exposure is **process restart**
     (or full host/VM replacement for kernel-level dumps).
4. **Negative control**: plant one canary in a scratch file every run; a scanner
   that cannot find its own control is INVALID, not green.
5. **Typed outcomes**: PASS only with byte-level absence across all encodings;
   any hit = FAIL with (surface, encoding, byte offset) evidence; inability to
   scan (ptrace scope, missing maps) = UNKNOWN, never PASS.
6. **Snapshot rule (from G4-05/G4-06/G4-13)**: a snapshot taken of a process or
   volume that ever held a secret must be treated as containing that secret,
   regardless of subsequent env/file deletion, until proven otherwise by
   byte-level scan of the snapshot artifact itself.

## Next gates

- G4-13: execute a controlled crash-dump/faulthandler capture after secret
  residency to close UNKNOWN.
- G4-14: WebVM browser-surface canary run (S-06) — requires browser harness.
- Policy decision: content screening for goal text in cloud-bound `report()`
  packets (G4-10) is a design/MS-spec question, not a test question.

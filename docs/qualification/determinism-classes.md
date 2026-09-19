# D0–D4 Determinism Qualification Classes

Status: additive tooling/framework. Audited against main `3cff6bcd52e352a6ba048c958949a7bbb2a039eb` and PR #152 head `cf41c997d08947549de2d973155e71b2d269f7d5` (review-ACCEPTED, merge pending). This document defines a determinism-class ladder for execution backends (models, adapters, sandboxes, browser providers, fixture harnesses) in the RESIDUAL agent harness.

**It assigns no class to any existing backend.** A backend earns its class exclusively through retained, hash-bound evidence bundles, and degrades after any relevant change until requalified (§4). Nothing here reinterprets `UNKNOWN` or `BLOCKED` as `PASS`.

Companion artifacts:

- JSON Schema: `docs/qualification/schemas/residual.determinism.bundle.v1.schema.json`
- Validator: `scripts/qualification_determinism.py` (stdlib-only, fail-closed)
- Blank worksheet: `docs/qualification/backend-worksheet.md`
- Fixture-valid bundle: `tests/fixtures/qualification/d2-valid.bundle.json`
- Tests: `tests/test_qualification_determinism.py`

## 1. Class definitions

A *backend* is any component that consumes a request and produces an output consumed by the harness: LLM provider adapters, WebVM browser providers, sandbox executors (`m4_sandbox`), fixture/simulation harnesses, and deterministic in-repo executors. A *qualified observation* is a run whose evidence bundle (§2) validates and whose result is `PASS`.

| Class | Name | Meaning | Entry evidence requirements |
|-------|------|---------|------------------------------|
| **D0** | Non-deterministic / unqualified | No determinism claim. Output may vary arbitrarily; timing, network, and external state are uncontrolled. | Default class. No evidence required. A backend is D0 until it earns D1+. No bundle may PASS a D0 attempt. |
| **D1** | Bounded-repeatability | Identical inputs produce *semantically equivalent* outputs under a stated equivalence relation, within a stated tolerance, on a stated platform. | ≥1 evidence bundle: ≥3 repeat runs of the same canonical input suite, same commit/tree, same platform; equivalence check `PASS`; skip/unknown counts = 0 for required checks. Float tolerance mode is permitted **only** at D1. |
| **D2** | Seed-reproducible | Outputs are bit-identical given identical inputs **and** an explicit seed, on one fixed platform/toolchain identity. | ≥2 replay runs of the same recorded seed with bitwise-equal canonical outputs (`canonical_bitwise`); canonicalization (§3) applied before comparison. A documented float tolerance is a D1 property, never D2. |
| **D3** | Cross-environment reproducible | Canonical outputs are identical across a declared matrix of environments (≥2 distinct OS/arch or container/host pairs) and across process restarts. | D2 evidence plus runs covering ≥2 distinct `(platform, machine)` pairs and ≥1 run with `restart_generation ≥ 1`; `tracked_source_dirty == false`. |
| **D4** | Hermetic replay | Execution is replayable from captured inputs alone: recorded request/response streams replay bit-identically without access to the original external dependency. | D3 evidence plus ≥1 network-disabled (air-gapped) replay run producing canonical-identical output, and a negative control proving that tampering with any captured input flips the comparison to `FAIL` (i.e. the comparison actually compares). |

Rules:

- Classes are cumulative: D_n evidence must satisfy all D_<n requirements against the **same commit/tree** and backend version.
- `SKIP` of a required check, any nonzero `unknown_count`, or `UNKNOWN`/`FAIL` in a required gate invalidates the bundle for class entry. A bundle that cannot be produced (missing capability, missing credentials) records `UNKNOWN`, never a silent PASS — consistent with the provider-canary rule in PR #152.
- Evidence older than any relevant change (§4) does not support a current class claim; it remains in the ledger as historical observation (append-only, `predecessor_id`-linked).
- D4 replay capture must disclose what is *not* replayed (e.g. wall-clock, true entropy) in the bundle's `non_claims`.

## 2. Evidence bundle

Each determinism qualification run emits one **D-class evidence bundle** (`residual.determinism.bundle.v1`). The bundle *wraps* a PR #152 `EvidenceEnvelope` (`residual.qualification.evidence.v1`) verbatim — it does not define a parallel envelope — and adds determinism-specific fields: `backend`, `class_attempted`, `suite` (id, version, seed, input hashes, excluded fields), `runs[]` (per-run environment, restart generation, network flag, raw and canonical output hashes), `canonicalization`, `equivalence`, optional `negative_control`, `predecessor_id`, and `non_claims`.

Cross-references enforced by the validator (fail-closed):

- `envelope.result` must equal the bundle `result`.
- `envelope.gate_id` must equal `determinism-<class-lowercase>-<backend_id>`.
- For class entry (`PASS`): `envelope.skip_count == 0`, `envelope.unknown_count == 0`, `envelope.source.tracked_source_dirty == false`, and `envelope.source.{commit,tree}` are full 40-hex git object ids (deliberately stricter than the envelope contract; see compat note C2 below).
- Unknown schema revisions of either the bundle or the embedded envelope are rejected outright (no forward-compatibility guessing).

When PR #152's `residual.qualification.evidence` module is importable, the validator additionally round-trips the embedded envelope through `EvidenceEnvelope.from_dict` and treats any rejection there as fatal, so the bundle can never accept an envelope the envelope's own authority rejects. On pre-#152 checkouts the structural contract is validated directly.

## 3. Canonicalization rules

Before any cross-run comparison, outputs are canonicalized:

1. **Encoding**: UTF-8, NFC normalization. Inputs not decodable as UTF-8 are compared as raw bytes and marked with a `bin:` key prefix in `output_hashes`.
2. **Newlines**: CRLF and CR are converted to LF before hashing; a trailing final newline is added if absent.
3. **Key ordering**: JSON objects serialized with keys sorted by UTF-8 code point, no insignificant whitespace (`json.dumps(..., sort_keys=True, separators=(",", ":"))`, matching `write_envelope`'s sorted-key convention in PR #152).
4. **Floats**:
   - D2+ default: IEEE-754 hex representation (`float.hex()`), preserving ±0 and NaN payloads; `-0.0` normalizes to `0.0`.
   - D1 tolerance mode: floats rounded to a declared fixed decimal precision (`float_policy: "tolerance"`, `float_tolerance` recorded); NaN/Inf fail the run unless declared in `non_claims`.
5. **Timestamps & entropy**: wall-clock timestamps, UUIDs, and other run-unique values are excluded from the canonical comparison surface and listed explicitly under `suite.excluded_fields`; they remain hashed in raw `output_hashes`. This mirrors PR #152 `schedule.py`, where unique IDs/timestamps are intentionally excluded from the replay identity hash.
6. **Platform-dependent values**: path separators normalized to `/`; absolute paths replaced by declared workspace-relative anchors before comparison.

## 4. Requalification-trigger / downgrade matrix

Any trigger degrades the affected backend to **D1-at-best pending requalification**; where marked "full reset", the backend returns to D0. Degradation is recorded by appending an amendment observation linked via `predecessor_id` — prior evidence is never deleted or edited, and first-attempt failures are retained.

| Trigger | Affected classes | Required requalification |
|---|---|---|
| Harness source change under `residual/` (any commit touching backend-relevant code) | All | Re-run entry evidence for the current class at the new commit/tree (evidence is commit/tree-bound; old bundles do not transfer) |
| Backend implementation change (adapter, sandbox, provider code) | All | Full reset to D0; re-earn from D1 upward |
| Backend version/config change (model identifier, flags, tool versions) | D2+ | Re-earn D2+; prior D1 evidence may stand if the equivalence relation is unchanged |
| Platform/toolchain change (OS, arch, Python, container image digest) | D3+ | Re-run the affected environments of the declared matrix |
| Canonicalization or suite-definition change (`suite_version` bump) | All | Full reset: comparisons across suite versions are invalid |
| Dependency/version-lock change in the qualification toolchain | D2+ | Re-run seed-replay evidence |
| Evidence-schema change (`residual.determinism.bundle.v1` → v2) | All | Old bundles remain valid historical observations but cannot support new class entry |
| Clock/schedule-only rerun of unchanged code | None | New observation appended; no degradation |
| Discovery of divergence in previously passing evidence | All | Immediate amendment: class claim REOPENED pending successor evidence |

## 5. Compatibility with PR #152 (reported, not silently resolved)

- **C1 — duplicate-evidence policy.** `aggregate_manifest` rejects two envelopes with the same `gate_id`, while determinism re-observation requires rerun chains. D-bundle chains are therefore recorded in a determinism ledger (append-only JSONL, `predecessor_id`-linked) and projected into a v1 manifest only by selecting the ACTIVE chain head per gate.
- **C2 — commit/tree strictness.** Envelopes accept any non-empty commit/tree; class entry requires full 40-hex. Non-git contexts (e.g. tarball fallback) are not accepted as class-entry evidence — a deliberate fail-closed tightening.
- **C3 — skip policy.** D-bundles are stricter than general regression envelopes: required class-entry checks demand `skip_count == 0`.
- **C5/C6 — schema versioning and timestamps.** Schema ids are pinned `const` v1 (a bump forces full reset per §4); recorded timestamps are operator-asserted and are never used as an ordering primitive — chain order is defined by `predecessor_id` linkage and append order.

## 6. Non-goals

No changes to Factory/M4, verifier authority, receipt serialization, ownership baselines, evidence schemas introduced by other work, frozen research definitions (`residual/eval_frozen`), workflows, or existing qualification tests. No existing backend has been assigned a determinism class; the worksheet is blank by design. This framework claims no capable-runner, blank-VM, real-provider, host-loss, elapsed-soak, production, or research qualification.

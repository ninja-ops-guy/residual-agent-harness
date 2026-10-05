# CHANGELOG — RESIDUAL INJ Class C Battery

## v0.2.1 (2026-10-03)

Two correctness fixes to the harness-faithful mode, both found by
independent review of v0.2.0 (mike, 2026-10-03). General-susceptibility
mode is unchanged from v0.2.0. Model qualification remains PENDING
(no endpoint available).

### 1. Exact `canonical(packet)` user-message serialization

- **Origin:** v0.2.0's docs and receipts claimed the user message
  reproduced `residual/station/models.py` `model_call` —
  `Message(Role.USER, canonical(packet))` — but `runner.run_cell`
  built `user_text` by concatenating evidence blocks as raw text
  (`positions.assemble`), and the HTTP provider sent that directly.
  Undelimited evidence was preserved, but the serialization step was
  not reproduced.
- **Discipline violated:** the battery's own byte-faithful claim
  (claim text vs implementation divergence).
- **Verification path:** read `model_call` (`models.py:52-65`),
  `canonical` (`residual/core.py:17`), and both packet constructions
  (`service.py:214-218` runner, `service.py:310-313` reviewer).
- **Fix:** new `inj_harness/assembly.py` builds evidence packets with
  the exact real key sets; the evidence text (injection at the trial's
  context position, undelimited) sits in `files["evidence.md"]`; the
  user message is `canonical(packet)` via the **live-imported**
  `residual.core.canonical` (`repo_import.import_canonical`), never a
  copied implementation. Receipts bind `user_content_serialization`
  and `packet_template_version` (1.0.0). A unit test pins the battery's
  packet key sets against the actual `service.py` packet literals via
  AST, so future v1 shape drift fails loudly.

### 2. Module-origin verification for the prompt-byte import

- **Origin:** `repo_import.import_prompt_bytes` resolved the repo path
  and recorded its commit, but never checked that the imported
  `residual.station.service` module's `__file__` belonged to the
  selected checkout. A previously cached module from another tree
  could supply prompt bytes while the receipt recorded the selected
  tree's commit.
- **Discipline violated:** source-binding (receipt provenance vs
  actual byte origin).
- **Verification path:** code inspection of `import_prompt_bytes`
  (no `__file__` check); reproduced in a unit test with two synthetic
  checkouts.
- **Fix:** `_import_from_repo` verifies `os.path.realpath(module.__file__)`
  is under the selected repo. On mismatch it evicts cached `residual*`
  modules, re-prepends the repo, reimports once, and re-verifies;
  a persistent mismatch raises `RepoImportError` (loud abort, never
  silent wrong bytes). Receipts bind `prompt_source_file` (the actual
  `__file__`) and `module_origin_verified`.

### 3. Expected-commit pin updated

- `EXPECTED_COMMIT` moved `ed271eee` → `ca6cd2e` (the repo HEAD the
  v0.2.1 fidelity claims were verified against). `service.py`,
  `models.py`, and `core.py` are byte-identical between the two
  commits, so the pin move changes no claim substance; it prevents a
  false-alarm mismatch warning on every run against the repo's own
  HEAD. The v1 AUTH qualification baseline is untouched by this
  battery-internal pin.

## v0.2.0 (2026-10-03)

Dual-mode versioned artifact: general-susceptibility mode (v0.1.0
design preserved, strict schema → UNEVALUABLE, detector v1.2.0 after
adversarial review) and harness-faithful mode (live prompt bytes,
three-state trials, N≥25/100, claim/not-claim separation).
Migration/parity: 16/16 cells identical, 11/11 corpora byte-identical;
`tests/inj/` retired after parity. Superseded by v0.2.1 for the
harness mode.

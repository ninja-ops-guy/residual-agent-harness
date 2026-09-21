# Split vocabulary (X-M6 unification)

The unified split vocabulary end-to-end is **{train, val, holdout}**:

* `research/slm/dataset/compile.py` split manifests use exactly
  `{train, val, holdout}` (REQUIRED_SPLIT_VALUES); any other value is a
  compile-time ERROR.
* `research/slm/ci/research_ci.py` consumes those manifests and is
  split-name-agnostic; CI always sees the unified vocabulary.
* Protocol/eval documents that say "validation" or "test" map as:
  `validation` ≡ `val`, `test` ≡ `holdout` (the frozen, never-trained-on,
  never-tuned-on split). These are documentation aliases only; data
  artifacts always carry the unified names.
* Scaffold expectations (`scaffold/data.py`): the scaffold requires an
  explicit mapping when materializing token streams. The mapping is:
  `train` -> train stream, `val` -> `val.bin` (the scaffold's validation
  stream), `holdout` -> untouched until final evaluation. Never feed
  `holdout` into a scaffold `val.bin` used for checkpoint selection, and
  never rename `val` to `test` or vice versa.

This document is the coordination point for the scaffold lane; the names
above are the aligned contract.

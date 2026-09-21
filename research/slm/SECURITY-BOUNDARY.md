# SLM security boundary (EXP-M6-SLM)

This directory contains **training-ready machinery only**. The following
boundaries are absolute until the SLM-00 benchmark freeze is complete, and
some apply permanently:

1. **No training before SLM-00 freeze.** No script in `scaffold/`, no
   container built from `training/`, and no config in `configs/` may be used
   to train any model — even as a smoke test against real corpora — until
   the SLM-00 benchmark freeze is signed off.
2. **No holdout access.** Nothing in this directory may read, copy, or
   derive from benchmark/holdout data. Corpus and benchmark artifacts are
   owned by SLM-00; the scaffold only consumes packed bins produced by the
   frozen pipeline.
3. **Configs are untrained.** Every YAML under `configs/` is an architecture
   specification only. Parameter counts are analytic estimates (arithmetic
   shown in each file); no weights exist, and no checkpoint produced outside
   the frozen protocol may be treated as a program artifact.
4. **No candidate-model execution.** Do not run inference with any
   Nano/StationLM checkpoint as a control-plane candidate until the freeze
   and evaluation protocol allow it.

Violations invalidate the benchmark comparison and must be reported to the
program lead immediately.

## Amendment A1 (2026-09-20, SLM-INFRA-QUAL MATERIAL-4/-5)

**Validation split must be explicit and distinct from holdout.**

- Packed token streams are **uint32-le** end to end: `dataset/compile.py`
  packs them and `scaffold/data.py` memory-maps `np.dtype("<u4")`. Any
  reader using a different dtype (e.g. uint16) misreads every token 2:1
  and is a boundary violation. `PackedBinDataset` also rejects vocab sizes
  beyond the uint32 range.
- The scaffold **requires an explicit split mapping** before any training
  loop starts: either `train.split_manifest` (a JSON object mapping
  `train` / `val` / `holdout` to three **distinct** bin paths) or explicit
  `train.train_bin` / `train.val_bin` paths. There is no default
  `val.bin`; a missing mapping raises immediately.
- **Holdout may never be used as the validation set.**
  `scaffold/data.validate_split_paths` refuses (raises `ValueError`) any
  configuration where train/val/holdout paths are not all distinct, or
  where the validation bin is the holdout bin by path or by name. This
  closes the configuration-level hole where mapping `holdout.bin` to
  `val.bin` would have made periodic `Trainer.evaluate()` calls read
  holdout data, violating rule 2 without touching code.
- The dataset toolchain supports a real `val` split: `compile.py` accepts
  `train`/`val`/`holdout` assignments in the split manifest and refuses
  any contamination group that spans splits.

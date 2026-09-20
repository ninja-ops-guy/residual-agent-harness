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
   owned by SLM-00; the scaffold only consumes packed `train.bin`/`val.bin`
   produced by the frozen pipeline.
3. **Configs are untrained.** Every YAML under `configs/` is an architecture
   specification only. Parameter counts are analytic estimates (arithmetic
   shown in each file); no weights exist, and no checkpoint produced outside
   the frozen protocol may be treated as a program artifact.
4. **No candidate-model execution.** Do not run inference with any
   Nano/StationLM checkpoint as a control-plane candidate until the freeze
   and evaluation protocol allow it.

Violations invalidate the benchmark comparison and must be reported to the
program lead immediately.

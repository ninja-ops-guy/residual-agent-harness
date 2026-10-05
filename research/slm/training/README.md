# SLM training container (EXP-M6-SLM)

Reproducible single-GPU container for the Residual-Nano / StationLM training
scaffold in `research/slm/scaffold/`. This is **machinery only**: no training
run is permitted before the SLM-00 benchmark freeze completes
(see `research/slm/SECURITY-BOUNDARY.md`).

## Reproducibility

- Base image pinned: `pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime`
  (PyTorch 2.4.0, CUDA 12.1, cuDNN 9).
- All pip dependencies locked with exact versions in `requirements.txt`.
- Deterministic seeds: `SLM_SEED` / `PYTHONHASHSEED` default to 1337,
  cuDNN deterministic mode forced via env; the trainer seeds python, numpy
  and torch (CPU + CUDA).
- Runs as non-root user `slm` (uid 10001).

## Build

```sh
docker build -t slm-training -f research/slm/training/Dockerfile research/slm/
```

(Build context must be `research/slm/` so `scaffold/` and `configs/` are
visible to the Dockerfile.)

## Usage

```sh
# Train (blocked until SLM-00 freeze):
docker run --gpus all -v "$PWD/data:/app/data" -v "$PWD/runs:/app/runs" \
  slm-training train --config configs/nano-30m.yaml

# Evaluate a checkpoint:
docker run --gpus all -v "$PWD/data:/app/data" -v "$PWD/runs:/app/runs" \
  slm-training eval --config configs/nano-30m.yaml \
  --checkpoint runs/default/ckpt_step0010000.pt
```

`data/` must contain packed uint16 token streams (`train.bin`, `val.bin`)
produced by the SLM-00 corpus pipeline; paths are set in the config's
`train:` section.

## Layout

- `Dockerfile` — pinned image, locked deps, non-root user, entrypoint.
- `requirements.txt` — exact pip versions (torch comes from the base image).
- `entrypoint.sh` — dispatches `train` / `eval` to the scaffold entrypoints.

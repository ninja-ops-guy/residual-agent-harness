# CPU Deployment — Residual-Nano-class models

Deployment path for Residual-Nano (30M/80M) on ordinary hosts: no GPU,
no orchestration, one container or one Python process. Everything below
is machinery validation on **randomly-initialized test artifacts**
(`qualification: non-production-test-artifact`); quality/latency numbers
for trained models come after the SLM-00 freeze lifts.

## Path

1. Export: `python -m research.slm.inference.export.export --config
   research/slm/configs/nano-30m.yaml --dtype int8-dynamic --output-dir out/nano30m-int8`
2. Serve: `python -m research.slm.inference.serve --manifest
   out/nano30m-int8/manifest.json --host 127.0.0.1 --port 8080`
   (or the `Dockerfile.inference` container — see README).

`serve.py` is stdlib-only HTTP (`/generate`, `/metadata`) bound to the
`Backend` interface, so the same deployment works unchanged when the
GGUF/ONNX backends land.

## Memory expectations (INT8 dynamic, CPU)

Rule of thumb: resident weights ≈ 1 byte/param for INT8-dynamic Linear
layers; embeddings/LayerNorm stay FP32 (~4 bytes/param). Add ~0.2–0.4 GB
for the Python/torch runtime and activations at ctx=2048.

| Model | Params | INT8 weights (est.) | Total RSS (est.) |
|---|---|---|---|
| Residual-Nano 30M | ~32.1M | ~25–30 MB | ~0.4–0.6 GB |
| Residual-Nano 80M | ~80M | ~60–75 MB | ~0.6–0.9 GB |

Both fit comfortably on a 2 GB host. StationLM 150–400M INT8 (~0.15–0.4 GB
weights) is plausible on 4 GB hosts but is not the target of this path.

## Latency expectations (single socket, 4 threads, INT8)

Rough order-of-magnitude targets to validate post-freeze with real
weights — measured on the export artifact path, not benchmarks:

| Model | Prompt eval | Token generation |
|---|---|---|
| Residual-Nano 30M | ~50–150 tok/s | ~20–60 tok/s |
| Residual-Nano 80M | ~20–60 tok/s | ~8–25 tok/s |

Tuning levers: `OMP_NUM_THREADS` (container default 4), shorter context
windows, and the documented lower-bit GGUF candidates
(`export/quantize.py: LOWER_BIT_CANDIDATES`) which typically give a
further 1.5–2x over torch INT8-dynamic on CPU.

## Operational notes

- Device is CPU-only; `SLM_DEVICE` is honored by the PyTorch backend but
  the inference container ships the CPU torch wheel only.
- Decoding is deterministic when `decoding.seed` is set (shared sampler
  in `runtime/backend.py`), which keeps CPU deployments reproducible.
- No streaming yet (`supports_streaming: false`); batch=1 only.

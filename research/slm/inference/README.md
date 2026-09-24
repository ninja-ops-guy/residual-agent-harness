# SLM Inference Runtime (test artifacts only)

CPU-first inference runtime, quantization/export tooling, and a minimal
serving path for the EXP-M6-SLM models (Residual-Nano 30–80M, StationLM
150–400M). This is the runtime/export counterpart to the
`StationLMProvider` decision-model lane: any backend (PyTorch today;
llama.cpp-style GGUF and ONNX Runtime as documented stubs) sits behind
one `Backend` interface, so the provider can swap runtimes via a
manifest change only.

**Boundary:** no training, no benchmark access, no model weights exist
yet. Everything runs on randomly-initialized tiny configs, and every
exported artifact is labeled `qualification: non-production-test-artifact`.
See `../SECURITY-BOUNDARY.md`.

## Layout

| Path | Purpose |
|---|---|
| `runtime/` | `Backend` protocol (`load`/`generate`/`metadata`), `pytorch_backend.py`, documented `gguf_backend.py` / `onnx_backend.py` stubs, shared sampling, capability reporting |
| `export/` | FP16/BF16 conversion, INT8 dynamic quantization, documented lower-bit (GGUF q8/q6/q4) candidate path, export manifest writer, CLI |
| `serve.py` | Minimal single-file HTTP server behind the Backend interface |
| `cpu_deploy.md` | CPU-only deployment notes for Residual-Nano-class models |
| `Dockerfile.inference` | CPU-only inference container (separate from training image) |
| `requirements.txt` | Pinned minimal deps (torch CPU wheel) |
| `tests/` | Round-trip / quantization / backend-swap tests on tiny random-init configs |

## Quickstart (repo checkout)

```bash
pip install -r research/slm/inference/requirements.txt

# Export a tiny random-init model (or point --config at configs/nano-30m.yaml)
python -m research.slm.inference.export.export \
    --config research/slm/inference/tests/tiny-config.yaml \
    --dtype int8-dynamic --output-dir /tmp/out-int8 --code-commit dev

# Serve it (CPU)
python -m research.slm.inference.serve --manifest /tmp/out-int8/manifest.json --port 8080

# Call it
curl -s localhost:8080/metadata
curl -s -X POST localhost:8080/generate \
    -d '{"tokens": [1, 2, 3], "decoding": {"max_new_tokens": 4, "seed": 7}}'
```

## Container

```bash
cd research/slm
docker build -f inference/Dockerfile.inference -t slm-inference .
docker run --rm slm-inference --help
docker run --rm -v "$PWD/out:/app/artifacts" -p 8080:8080 \
    slm-inference --manifest /app/artifacts/manifest.json
```

## Manifest fields

`export/manifest.py` writes the schema-on-branch provenance fields:
`model_hash`, `tokenizer_hash`, `dataset_manifest_hash`, `source_config`,
`training_config`, `code_commit`, `seed`, `qualification_receipt`
(pinned to `non-production-test-artifact`), and `model_card` fields.
Dataset/tokenizer hashes are `null` until real artifacts exist post-freeze.

## Backend swap

Callers only use `load_backend(manifest_path)`, `generate(tokens,
DecodingConfig)`, and `metadata()`. Selecting PyTorch vs (future)
GGUF/ONNX is the `backend` field in the manifest — no caller code
changes. Tests prove caller transparency (`tests/test_backend_swap.py`).

# SLM Research CI (tooling only, pre-freeze)

`research_ci.py` is the fail-closed validator for the SLM data toolchain
artifacts produced under `research/slm/`. It exits nonzero on any schema or
artifact violation. It performs no model training and never calls any
benchmark.

## Checks

| Flag | Validates |
| --- | --- |
| `--observations FILE` | Observation JSONL records against `docs/research/EXP-M6-SLM/observation.schema.json` (`--observation-schema` to override). |
| `--dataset-manifest FILE` | Packed dataset manifest against `research/slm/dataset/manifest.schema.json`, plus SHA-256 cross-checks of referenced `.bin` files when present on disk. |
| `--tokenizer-artifact FILE` | `.tiktoken` BPE artifact: 2-column format, unique ranks, all 256 base byte tokens present, and a tiktoken encode/decode round-trip (round-trip advisory if tiktoken not installed). |
| `--eval-output FILE --eval-schema FILE` | Evaluation output JSON against a caller-provided JSON Schema. `--eval-schema` is mandatory with `--eval-output`. |

All requested checks run independently; every failure is reported before a
single nonzero exit.

## Pinned dependencies

See `research/slm/requirements.txt`:

- `jsonschema==4.23.0` (schema validation)
- `tiktoken==0.8.0` (tokenization; optional for CI, required by compile/measure)
- `regex==2024.11.6` (BPE pre-tokenization pattern)

Python >= 3.11 (matches repo `pyproject.toml`).

## Integration with existing CI conventions

The repo's workflows (`.github/workflows/ci.yml`, `control-plane.yml`, etc.)
follow a common pattern: `ubuntu-latest`, Python matrix 3.11–3.13,
`actions/setup-python@v5` with `persist-credentials: false` on checkout,
pip-installed extras, and artifact upload with `if: always()` and
`retention-days: 14`. A future `research-slm.yml` workflow should follow the
same shape, e.g.:

```yaml
- name: Install SLM research deps
  run: python -m pip install -r research/slm/requirements.txt
- name: Validate SLM research artifacts
  run: |
    python research/slm/ci/research_ci.py \
      --dataset-manifest runs/slm/dataset_manifest.json \
      --tokenizer-artifact runs/slm/residual_bpe.tiktoken
```

This PR intentionally adds no workflow file (pre-freeze, tooling only); the
validator is runnable standalone with `--help`.

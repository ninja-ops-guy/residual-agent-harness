# Onboarding examples (Track O)

- `sample_project/` — a minimal bounded task (`task.json`) over a local
  artifact with mechanical `json_sum` checks, plus `config.toml` using the
  scripted `demo` providers. No model calls, no network, no cost.
- `demo.sh` — one-command demo: runs the sample project, verifies the
  evidence trace, and re-verifies the trace bound to the result. Exits 0 on
  success.
- `validate_tutorial.py` — module-author tutorial validation: generates a
  module per `docs/module-tutorial.md`, checks its quarantine / verifier /
  brake semantics, and runs `residual-module validate` on it.

All steps are exercised by `tests/test_onboarding.py`.

```bash
bash examples/onboarding/demo.sh
python3 examples/onboarding/validate_tutorial.py
```

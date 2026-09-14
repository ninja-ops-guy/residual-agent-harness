# Deterministic worker-degradation experiment

The reliability paper needs a way to lower worker quality while keeping the underlying model, prompt, tool surface, verifier, and integration policy fixed. `residual.experiments.degradation` provides that control.

## Why this exists

Comparing a strong model with a weak model confounds model identity with architecture. A stronger experiment holds the engine identity constant and injects a frozen, deterministic degradation step between generation and verification.

The question becomes:

```text
raw worker correctness decreases
        ↓
does accepted-state correctness decrease more slowly under Residual?
```

## Profile

`DegradationProfile` binds:

- a named degradation level;
- mutation rate in `[0, 1]`;
- a non-negative seed;
- a mutation strategy.

The canonical profile is hash-bound. The seed participates in that hash, so changing it creates a different experimental condition.

Supported v1 strategies:

- `type_aware_corruption` — deterministic candidate corruption based on candidate type;
- `replace_null` — replace selected candidate outputs with `None`;
- `truncate_text` — truncate selected text outputs and null non-text outputs.

## Engine wrapper

`DegradingExecutionEngine` wraps an existing `ExecutionEngine` while preserving its `name`, `version`, capabilities, health, and locality. It delegates normal execution to the original engine and then makes a deterministic mutation decision from:

- profile hash;
- task ID;
- task capability;
- engine name;
- engine version.

The result metadata records:

- profile hash;
- level/rate/seed/strategy;
- deterministic decision score;
- whether mutation occurred;
- original candidate hash;
- emitted candidate hash.

This allows the exact degradation pattern to be audited and reproduced.

## Example

```python
from residual.experiments import DegradationProfile, DegradingExecutionEngine

profile = DegradationProfile(
    level="medium",
    rate=0.35,
    seed=20260914,
    strategy="type_aware_corruption",
)
engine = DegradingExecutionEngine(base_engine, profile)
```

Freeze `profile.sha256` in the reliability manifest under `model_bindings` or another explicit preregistered experimental-binding field before execution.

## Recommended curve

Use at least a nominal condition plus several frozen degradation levels, for example:

```text
nominal  rate=0.00
mild     rate=0.15
medium   rate=0.35
severe   rate=0.60
extreme  rate=0.85
```

These are example rates, not scientifically privileged values. The final rates and stopping rule must be frozen before confirmatory evaluation.

For each level, run the same tasks and configurations. Plot independently measured worker correctness against Accepted Error Rate (AER), acceptance rate, and cost. Do not report a reliability improvement without the acceptance-rate curve; a controller that rejects everything is not a useful success.

## Non-claims

This wrapper is not a model-quality benchmark and does not simulate every real model failure distribution. It is a controlled fault transformation intended to test architectural containment under progressively worse candidate quality. Confirmatory claims should also be repeated with naturally weaker models or inference-budget reductions to check whether the result survives a different degradation mechanism.

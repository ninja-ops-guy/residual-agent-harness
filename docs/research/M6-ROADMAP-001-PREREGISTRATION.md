# M6-ROADMAP-001 Preregistration — Ship ImprovementSpec Using RESIDUAL

## Objective
Use the current production RESIDUAL harness to implement and qualify the first concrete M6.2 roadmap deliverable in the **real current repository**, not an empty fixture.

Roadmap source: #222 / M6.2 Evidence-driven Improvement Discovery.

## Baseline
- repository baseline: `260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`
- task: productionize `residual/improvement/ImprovementSpec`
- implementation agent: `qwen2.5-coder:7b`
- local provider: Ollama on dedicated endpoint `127.0.0.1:11438`
- max output tokens: 1600
- max task attempts: 5
- mission budget: 1800 s / 30,000 reported tokens
- independent local model review
- no cloud fallback

## Candidate authority
The agent may write only:
- `residual/improvement/__init__.py`
- `residual/improvement/spec.py`

The candidate may not edit tests, evaluator, M4, receipts, Station, integration logic, qualification, evidence stores, or promotion controls.

## Frozen acceptance contract
The task is accepted only if:
1. both generated Python files compile;
2. import through `from residual.improvement import ImprovementSpec` succeeds;
3. the frozen positive/negative behavior checks pass;
4. acceptance mutation through `to_dict()` cannot mutate internal state;
5. canonical JSON and SHA-256 identity are deterministic;
6. local reviewer approves the exact checked head;
7. integration checks pass;
8. a station receipt is issued;
9. export contains both generated files.

## Research questions
- Can RESIDUAL apply the M6-006 repair behavior to the real repository?
- Does repository context introduce new packaging/import failures?
- How many repairs are required?
- Are failure findings specific enough for a later repair?
- Does review agree with the deterministic checks?
- Does integration preserve the exact reviewed head?

## Failure policy
The first authoritative run is retained. Any required harness/spec change becomes a new numbered experiment rather than modifying this result.

## Shipping rule
A production PR may be opened only from source extracted from a successful RESIDUAL release export and independently re-tested on top of current main.

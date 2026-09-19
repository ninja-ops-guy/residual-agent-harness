# M6-ROADMAP-001C Preregistration — Immutable ImprovementSpec

## Why this experiment exists
M6-ROADMAP-001B successfully produced and qualified a production ImprovementSpec on an exact pinned main baseline. Independent post-run review found a content-identity weakness that the frozen test and model reviewer did not detect: a frozen dataclass can still expose mutable objects. If `acceptance` is mutable, the object represented by a previously computed SHA-256 can change after construction.

This trial strengthens the roadmap contract before shipment rather than shipping the weaker candidate.

## Baselines
Source repository is pinned exactly to:
`260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`

Harness includes the repair-diagnostics fix under test from #233:
`8801d5e0ba0f7c5aaee9346761cd1916a6254c53`

## New invariant
ImprovementSpec content identity MUST be stable after construction:
- caller mutation of the input acceptance object cannot alter the spec;
- direct mutation through `spec.acceptance` or nested objects must fail;
- nested mutation of `to_dict()` output cannot alter the spec;
- SHA-256 remains unchanged after all such attempts;
- acceptance is strict JSON-compatible with finite numbers and string object keys.

## Frozen authority boundaries
The candidate may write only:
- `residual/improvement/__init__.py`
- `residual/improvement/spec.py`

It cannot modify tests, verifier, M4, receipts, Station, integration, qualification, evidence, or promotion code.

## Runtime
- Qwen2.5-Coder 7B
- Ollama dedicated endpoint 127.0.0.1:11440
- 2,000 max output tokens
- five attempts
- 40,000-token mission budget
- 1,800-second wall-clock budget
- independent local review
- no cloud fallback

## Success
Success requires exact pinned source identity, 3/3 deterministic checks, reviewer approval, exact-head integration, verification receipt, and release export of both generated files.

## Failure policy
The first run is authoritative. Any further contract or harness change requires another numbered trial.

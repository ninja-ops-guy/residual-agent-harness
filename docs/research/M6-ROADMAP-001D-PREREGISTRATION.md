# M6-ROADMAP-001D Preregistration — Immutable ImprovementSpec with External Acceptance Fixture

## Why this experiment exists
M6-ROADMAP-001C did not reach candidate generation because the strengthened inline `python -c` acceptance program exceeded RESIDUAL's existing 2,000-character command-argument limit. That result is retained as an invalid experiment configuration.

This trial keeps the strengthened immutable-identity contract unchanged, but moves the deterministic acceptance program into an external research fixture whose SHA-256 is recorded in evidence.

## Baselines
- production source: exact detached `260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`
- harness: repair-diagnostics head `8801d5e0ba0f7c5aaee9346761cd1916a6254c53`
- model: Qwen2.5-Coder 7B
- local Ollama endpoint: 127.0.0.1:11441

## Acceptance fixture
The candidate cannot write the external verifier. The mission command invokes the verifier by absolute path from the research checkout. The verifier SHA-256 is retained in experiment evidence.

The verifier checks:
- deeply immutable acceptance data;
- no aliasing to caller input;
- no direct nested mutation;
- fully detached/thawed `to_dict()`;
- stable SHA-256 after attempted mutations;
- deterministic strict JSON serialization;
- rejection of NaN, Infinity, unsupported objects, non-string mapping keys;
- original positive and negative field invariants.

## Candidate write scope
Only:
- residual/improvement/__init__.py
- residual/improvement/spec.py

## Runtime limits
- max output tokens: 2,000
- max attempts: 5
- token budget: 40,000
- mission wall clock: 1,800 s
- independent local review
- no cloud fallback

## Success
Exact source identity + all deterministic checks + reviewer approval + exact-head integration + station verification receipt + release export.

## Failure policy
First run is authoritative. Any change to contract, verifier fixture, harness, or runtime becomes another numbered trial.

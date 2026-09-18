# M6-SHIP-001 Preregistration — Ship ImprovementSpec Using RESIDUAL

## Question

Can the production RESIDUAL harness implement and qualify the first M6.2 roadmap task against the real repository, rather than an empty experimental workspace, and produce a candidate suitable for a normal shipping PR?

## Roadmap task

Issue #222, deliverable 1: make `ImprovementSpec` a first-class production contract.

## Source repository

The experiment imports a clean clone of the exact experiment head into Station using the normal live source-import path. The model may write only:

`residual/improvement/spec.py`

Read-only context:
- `residual/core.py`
- `residual/goalspec.py`

## Runtime

- local Ollama on dedicated endpoint 127.0.0.1:11438
- qwen2.5-coder:7b
- max output tokens: 1600
- batch max passes: 5
- token budget: 30000
- wall-clock budget: 1800 s
- one worker
- local reviewer
- no cloud fallback

## Immutable acceptance

The candidate must:
- compile;
- expose the frozen ImprovementSpec contract;
- reject all blank/empty negative paths;
- remain frozen at runtime;
- copy mutable acceptance state in to_dict();
- canonicalize deterministically;
- produce stable SHA-256 identity.

The generated candidate cannot modify its checks, reviewer, receipts, M4, integration controls, or promotion authority.

## Success

The experiment passes only when:
- integrated == 1
- 2/2 checks pass
- independent review approves
- verification receipt exists
- release export succeeds
- generated source is retained

## Shipping rule

A successful experiment does **not** directly alter main. The exact exported source is copied to a new production branch, repository-level tests are added independently, and normal CI must pass before merge.

## Research logging

Retain:
- every failed candidate patch/check receipt;
- repair-context evidence;
- model usage/timing;
- review receipt;
- integration receipt;
- release export;
- generated-source SHA-256;
- any mismatch between experimental and production repository behavior.

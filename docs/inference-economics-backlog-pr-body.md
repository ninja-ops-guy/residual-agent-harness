## Summary

Adds a documentation-only implementation backlog for the follow-on inference-economics work discovered while evaluating the uploaded IE-002 through IE-007 prototype package.

The prototype package passes its own focused suite, but it is not production-qualified against the frozen RESIDUAL contracts. This PR deliberately records the missing production work instead of copying prototype code into runtime paths.

## What this adds

- dependency-ordered IE-002 through IE-007 task list;
- acceptance criteria and negative-path cases for telemetry, pressure/admission, context reuse, escalation, empirical routing and roofline analysis;
- mandatory cross-cutting gates for authority boundaries, exact-head evidence, UNKNOWN semantics, deterministic replay, concurrency, privacy and evaluation;
- a finer-grained future PR split so scheduler/provider/adaptation authority changes can be reviewed separately;
- a concise checkbox execution index;
- explicit global stop conditions and deferred research ideas.

## Sequencing

`IE-001 -> IE-002 -> IE-003 -> IE-004 -> IE-005 -> IE-006 -> IE-007 -> IE-EVAL`

PR #177 remains the IE-001 qualification candidate and is not modified by this branch.

## Authority boundary

Documentation only. No production runtime, scheduler, provider, verifier, receipt, integration, Factory/M4, protected-test, or evidence-schema behavior changes.

## Non-claims

This PR does not claim runtime speedup, token/cost reduction, quality improvement, production scheduling safety, provider-routing improvement, GPU optimization, or paper-facing research results.

## Intended use

Merge this as the durable backlog, then have future implementation work consume individual tasks/PR slices only after their prerequisites are accepted on current `main`.

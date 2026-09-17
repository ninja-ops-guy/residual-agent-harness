# PR notes — inference-economics follow-on backlog

## Scope

Documentation/planning only. No production runtime, provider, scheduler, verifier, receipt, integration, Factory/M4, protected-test, or evidence-schema authority changes.

## Why this PR exists

The uploaded IE-002 through IE-007 prototype package is useful design input but is not production-qualified against the frozen specs. Rather than copy it into runtime code, this PR records the concrete work required to implement the concepts safely later.

## Main outputs

- dependency-ordered IE-002 through IE-007 implementation backlog;
- acceptance criteria and failure-path tests for each track;
- mandatory cross-cutting authority, UNKNOWN, replay, privacy, concurrency and evaluation gates;
- finer-grained suggested PR split for high-risk production-authority changes;
- explicit deferred ideas so experimental work is not smuggled into qualification PRs;
- concise checkbox summary for later execution.

## Current IE-001 state

PR #177 remains the IE-001 qualification candidate. Its exact-head repository CI and maintainer gate are green; the backlog treats independent current-head technical review as the remaining qualification prerequisite before downstream production implementation.

## Non-claims

This PR does not claim any runtime speedup, token/cost reduction, quality improvement, production scheduling safety, provider-routing improvement, GPU optimization, or paper-facing result.

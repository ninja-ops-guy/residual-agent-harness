# M6-ROADMAP-001B — Exact-Main Baseline Replication

## Reason
M6-ROADMAP-001 executes from a workflow branch and its Station source path points at the checked-out experiment branch. Write scoping prevents the model from modifying the research apparatus, but the repository baseline contains experiment-only files and therefore is not byte-identical to the declared main baseline.

This replication corrects that methodological issue without replacing M6-ROADMAP-001.

## Independent correction
Before executing the Station mission, create a detached Git worktree at exactly:

`260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`

The Station clones that detached tree as its source. The experiment scripts/workflows remain outside the source repository seen by the agent.

## Everything else remains frozen
- same production ImprovementSpec contract;
- same writable paths;
- same deterministic checks;
- Qwen2.5-Coder 7B;
- max output 1600;
- five-attempt bounded repair loop;
- 30,000-token budget;
- 1,800-second mission budget;
- local independent review;
- no cloud fallback;
- same shipping criteria.

## Additional validity check
The evidence MUST record `source_head`, and success is not considered baseline-pinned unless:

`source_head == baseline_sha == 260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`

## Failure policy
This is a separate trial. Results from M6-ROADMAP-001 remain in the record.

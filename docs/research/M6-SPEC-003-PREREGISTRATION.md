# M6-SPEC-003 Preregistration — Repair-Context Intervention

## Question
Did the M6-SPEC-001 failure expose a harness repair-semantic defect, and does binding the previous failed candidate into the next repair prompt improve the exact same 1.5B self-host task without weakening acceptance?

## Comparison
Historical control: M6-SPEC-001 on baseline `699e2869e294fe157b4bfd73a272057683a2f7e0`.

Intervention trial: the same frozen baseline plus one harness change: repair calls receive the previous attempted writable-file contents as `prior_candidate_files`. The new attempt still begins from a clean baseline worktree, so failed code is context, not implicitly trusted state.

## Frozen controls
- model: `qwen2.5-coder:1.5b`
- provider: local Ollama
- Python: 3.12
- workers: 1
- exact ImprovementSpec task instruction and behavioral checks from M6-SPEC-001
- max output tokens: 1600
- batch token budget: 30000
- batch wall clock: 600 s
- no cloud fallback
- review placement: local
- success criteria and protected authority boundaries unchanged
- no retry may replace the first authoritative model trial

## Intervention
1. On repair, read only the prior attempt's declared writable files.
2. Supply them as bounded data in `prior_candidate_files`.
3. Keep the new candidate worktree rooted at the clean project baseline.
4. Record hashes of repair-context files as durable task evidence.
5. Do not alter checks, reviewer authority, integration, receipts, M4, or promotion.

## Evidence expansion
The experiment apparatus retains task artifacts (check receipts and patches where available) inside the final research evidence so failed candidates can be inspected after the temporary Station is destroyed.

## Primary endpoint
A complete accepted implementation: integrated 1/1, all frozen checks passing, review approved, verification receipt present, generated source exported, and no export error.

## Secondary endpoints
- whether repair context is exercised
- per-attempt candidate patch/check evidence
- first-pass result
- repair count
- provider calls and token counts
- request bytes
- wall clock
- truncation events
- final brake/outcome
- false acceptance (target zero)

## Interpretation
A success after a failed first attempt would support the hypothesis that repair context materially improved corrective behavior in this task. A first-pass success would not test the intervention itself. A failure remains informative and must be retained.

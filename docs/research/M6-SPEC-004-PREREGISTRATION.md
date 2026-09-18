# M6-SPEC-004 Preregistration — Transport/Source Clarity

## Question
Does explicitly separating RESIDUAL's outer structured JSON transport from the literal contents of writable source files allow the same Qwen2.5-Coder 1.5B agent to implement the frozen ImprovementSpec task more reliably?

## Comparison
Immediate control: M6-SPEC-003.

M6-SPEC-003 already includes:
- the original M6-SPEC-001 historical baseline;
- prior-candidate repair context;
- repair-context hash evidence;
- richer failed-attempt artifact retention.

M6-SPEC-004 changes one behavioral variable on top of that control: the runner system contract now states that the outer JSON object is transport only, that values are literal file contents, and that a .py file value must be Python source. A correctly escaped Python transport example is included.

## Frozen controls
- model: qwen2.5-coder:1.5b
- provider: local Ollama
- Python: 3.12
- exact ImprovementSpec task instruction
- exact acceptance checks
- workers: 1
- max output tokens: 1600
- batch token budget: 30000
- batch wall clock: 600 s
- no cloud fallback
- local review
- same repair-context mechanism
- same acceptance, review, receipt, integration, M4, and promotion boundaries
- first authoritative model trial is retained regardless of outcome

## Primary endpoint
Complete accepted implementation:
- integrated == 1
- task state == integrated
- all frozen checks pass
- review approved
- verification receipt present
- generated source exported
- no export error

## Secondary endpoints
- file-language correctness on attempt 1
- whether repair context is exercised
- candidate patches/check artifacts for every attempt
- calls, tokens, request bytes, wall clock
- truncation
- final brake/outcome
- false acceptance (target zero)

## Interpretation
If M6-SPEC-004 produces Python source where M6-SPEC-003 produced data objects, that supports the transport/source-clarity hypothesis even if the candidate still fails semantic checks. Full success requires every unchanged downstream gate.

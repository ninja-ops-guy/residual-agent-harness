# M6-SPEC-007C Preregistration — External Verifier, Minimal Scientist Context

M6-SPEC-007 and 007B both aborted before discovery because the first Qwen2.5-Coder 7B Scientist call reached the 300-second Ollama adapter timeout.

M6-SPEC-007C preserves:
- the same aggregate EvidenceSnapshot values;
- the same raw evidence hashes;
- no supplied improvement question;
- no supplied target metric;
- no supplied intervention;
- no supplied hypothesis;
- the exact deterministic proposal checker;
- review, receipt, integration, export, and human-promotion boundaries.

The only change is model-visible context.

The Scientist receives:
- the compact EvidenceSnapshot;
- the proposal schema/instructions embedded in the task.

The immutable checker remains external and authoritative but is no longer included in model context.

## Hypothesis

The Scientist does not need verifier implementation details to originate a defensible proposal. Removing checker source should reduce prompt cost enough for local 7B inference to execute while preserving independent verification.

## Success

Same as 007B: produce an admissible ImprovementSpec-like proposal or valid MeasurementGap; pass the external checker; independent review approves; receipt issued; export succeeds.

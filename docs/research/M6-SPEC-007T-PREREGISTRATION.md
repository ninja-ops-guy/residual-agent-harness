# M6-SPEC-007T Preregistration — Host Provenance Envelope

## Motivation

007R failed closed because the Hypothesis Scientist transcribed the correct EvidenceSnapshot hash into an incorrect 58-character value.

Snapshot identity, Metric Registry identity, and the retained human gate are immutable host facts. Requiring a model to copy them adds failure surface without adding epistemic value.

## Independent variable

Remove the following fields from all model-authored Scientist/Planner response schemas:

- EvidenceSnapshot hash;
- Metric Registry hash/revision;
- human approval required.

After each structured model response, the trusted host attaches those values in a deterministic envelope before any mechanical admission check.

The mechanical verifier remains unchanged and still verifies those fields. Only authorship moves from model to host.

## Preserved

- same versioned Metric Registry;
- same five retained source runs;
- same active evidence-query phase;
- same Hypothesis Scientist / Measurement Planner split;
- same deterministic metric duplicate/ambiguity gates;
- same independent metric/improvement review;
- same qwen2.5:7b model;
- same two-cycle bound;
- no supplied question/target/intervention/hypothesis;
- no registry mutation, candidate implementation, or promotion authority.

## Success

The host-bound proposal/request must pass exact provenance verification without relying on model transcription.

Subsequent epistemic outcomes remain open:
- admitted ImprovementSpec -> M6-008 eligible separately;
- admitted semantically valid MeasurementGap -> evidence acquisition only;
- duplicate/ambiguous/insufficient proposal -> fail closed.

# M6-SPEC-007B Preregistration — Compact Autonomous Discovery

M6-SPEC-007 aborted before discovery because the first 7B Scientist call timed out at 300 seconds with a 15,566-byte request.

M6-SPEC-007B preserves the epistemic question and all measured aggregate values, but removes verbose per-run rows from the model-visible EvidenceSnapshot.

## Preserved
- no supplied improvement question;
- no supplied target metric;
- no supplied intervention;
- no supplied hypothesis;
- exact aggregate M6 measurements;
- source artifact hashes binding the underlying raw evidence;
- metric catalog;
- protected invariant catalog;
- deterministic proposal checker;
- independent review;
- receipt/integration/export gates;
- human approval boundary.

## Changed
Only the model-visible representation of evidence: compact aggregate metrics + provenance hashes instead of aggregate metrics + full run rows.

## Hypothesis
A compact evidence representation is sufficient for defensible autonomous discovery while reducing local-model context cost and avoiding the provider timeout seen in M6-SPEC-007.

## Success
The Scientist must originate either:
1. a mechanically admissible ImprovementSpec-like proposal grounded exactly in measured metrics; or
2. a valid MeasurementGap for a truly absent metric.

The accepted proposal must pass the immutable checker, independent review, integration receipt, and export.

# Software verification and negative findings — not human results

Eight local stdlib unittest methods passed with zero skips. Two independently generated directory trees were byte-identical in the reproduction test. CLI build and synthetic analysis executed successfully. No full repository qualification or hosted CI success is claimed.

The intentionally always-ACCEPT fixture has 56 synthetic rows, 14 per arm. Each arm has 11 incorrect acceptances / 11 nonacceptable cases, appropriate HOLD 0/8, and Brier 0.5114285714285715. All four risk differences are exactly zero. Timing (30 seconds) and burden (4/7) are constant fabricated test inputs, not observations. The separate ideal-oracle unit fixture yields Brier 0, incorrect acceptance 0 and appropriate HOLD 1; this checks formulas, not achievable human performance.

Negative controls reject duplicate rows, unknown decisions, NaN, Boolean probabilities, negative duration, invalid burden, modified presentation hashes, mismatched case hashes and non-synthetic input. Missing/aborted rows remain explicit and empty denominators return null. These are bounded tests, not an independent security review.

Historical negative retained: draft #552 at 7c9a16432d69ae8ad39df6ef97c82415c4d76c0b reports an earlier synthetic provenance study with 11 incorrect acceptances in every condition. The underlying earlier run was not found/replayed in this inspection; treat this as a retained secondary-source report, not newly verified evidence. The new all-ACCEPT fixture deliberately exercises the same null pattern but is not a reconstruction of that study.

Open findings: no private Shared Comms access; unpublished agent deliverables unknown; private human corpus and independent truth review absent; no actual participant results; static pages lack instrumented response capture; no human uncertainty implementation; no owner gates passed; public synthetic truth is derivable. See protocol for confounds and readiness prerequisites. No result supports scientific validation, production readiness, verifier correctness or general AI safety.

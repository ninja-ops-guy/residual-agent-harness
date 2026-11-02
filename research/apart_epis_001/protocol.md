# APART-EPIS-001 — proposed protocol, NOT FROZEN

Question: Does candidate-bound provenance improve human decisions when worker reports, execution evidence and independent verification disagree? Null: no improvement, or improvement offset by decision time/burden. The purpose is to test this direction, not validate RESIDUAL.

## Matched interventions

Every underlying case is projected into A (self-report), B (A plus unbound ordinary log), C (B plus current identity and receipt/artifact binding), D (C plus advisory verifier and authority). Task and decision policy are constant. No fault labels or correct decisions appear in pages. Each case is seen once per participant, across four rotated packets with seed 510 order randomization. Allocation to packets must be randomized independently of skill and logged privately by a custodian; the development generator's SYN identifiers are not participant identities.

The 14 cases include two clean controls; confident wrong output; stale epoch; wrong candidate; replayed attempt; missing artifact; source mismatch; correct verifier rejection; UNKNOWN; false-PASS; false-FAIL; retry with older candidate; pending authority. Receipt bytes are constructed, sanitized fixture data. Tester must independently reconstruct each task answer and each binding/authority obligation without consulting worker or verifier votes. Two independent reviewers should record disagreement and adjudication before G2; none has done so here.

Admissible decisions: ACCEPT for supported correct current work with authority; REJECT for demonstrated incorrect output; HOLD for missing/ambiguous evidence, identity or authority. Truth distinguishes acceptance warranted in the full constructed world from what is knowable in each treatment. Confidence means **probability that acceptance is warranted**, not confidence that the chosen action is correct. UI asks 0–100; response encoding divides by 100 to [0,1]. HOLD is not a correctness failure simply because the hidden world is acceptable.

## Proposed human pilot (requires owner decisions and approval)

Proposed feasibility target: 16 consenting adult volunteers, four per packet, 14 judgments each; stop at 16 completed sessions or November 15, 2026 12:00 PM Eastern, whichever comes first. This is a convenience-sample feasibility target, not a power calculation or an approved recruitment plan. Do not inspect outcomes to extend collection. Below four completed sessions per packet, report feasibility/descriptive findings only. Record consent separately; retain only random study IDs in analysis. No names, emails, IP addresses, employers or free-text operational data. Proposed retention: delete identity/consent linkage after withdrawal window and before release; owner must approve the actual window and applicable ethics/privacy requirements before recruitment.

Prerequisites: independently validated private corpus, reviewed packet delivery/response capture, accessibility/usability dry run, exact revision/hash manifest, no answer-key access, and owner G1/G2/G3. Screen for prior exposure to the public generator; exposed participants are ineligible for the same cases. Give uniform instructions and a separate practice item without revealing adversarial proportions. Do not provide correctness feedback between trials. Record interruptions and technical failures without silently replacing trials.

Exclude only missing consent, predeclared prior-corpus exposure, duplicate participation, or failed presentation identity checks. Retain excluded records and reason counts separately. Missing outcomes remain missing; aborted trials retain null outcomes. Never exclude based on correctness, confidence, completion speed, or inconvenient effects. No imputation in the primary descriptive pilot; report missingness by arm and worst/best-case bounds before any human conclusion. Review invalid records without accepting arbitrary extra fields or nonfinite values.

## Outcomes and analysis

The implemented synthetic analyzer reports raw numerator/denominator and null for undefined ratios:

1. Incorrect acceptance: ACCEPT among cases where full-world acceptance is not warranted. Denominator is observed complete nonacceptable trials, with assigned/missing/aborted counts also reported.
2. Appropriate HOLD: HOLD among complete cases whose adjudicated action is HOLD.
3. Brier score: mean squared error of acceptance-warranted probability against the binary full-world truth. This is not calibration of action confidence; supplement with reliability bins before a human analysis freeze.
4. Median active seconds (manual interval excluding declared interruptions).
5. Mean burden, anchored 1 = very little effort, 7 = extreme effort.

Secondary implemented: false rejection among acceptable cases and descriptive metrics by fault class. Planned but **not implemented/frozen**: explicit contradiction/mismatch detection questions, verifier reliance measure, reliability bins. Do not infer mental trust from agreement alone.

Predeclared descriptive contrasts: C−B (incremental binding), D−C (verifier **and authority** bundle), C−A and D−A (total packages). Risk differences are in proportion units, negative favorable for incorrect acceptance. D−C cannot isolate verifier value from authority value. The same participant contributes multiple cases: trial rows are not independent samples. For a later approved human analysis, use participant-cluster resampling stratified by randomized packet, fixed seed and 10,000 resamples; report 95% intervals and raw counts, conditional on this fixed corpus. The bounded-outcome extension is implemented and tested as software only (see analysis-extension.md); owner review is required before G1. The current four-person development fixture withholds intervals because each packet has only one participant. Separate invented multi-participant fixtures exercise the interval code. No p-values are produced. No significance or generalization claims follow from fixtures or a small convenience pilot.

## Design challenges to resolve before freeze

- B exposes correct/incorrect artifact content, so some wrong-output cases may already be solved without provenance. This is an intended negative/control contrast, not evidence of a bug.
- C versus B bundles additional metadata/reading effort; time and burden may increase even if errors decrease.
- D reveals authority unavailable to A–C. Full-world acceptance is not equally knowable in all conditions. Report conservative HOLD and false rejection separately; do not call all nonacceptance incorrect. Consider an authority-held-constant secondary design before freeze.
- All tasks currently use simple arithmetic and each fault has one exemplar. Ecological validity, fault prevalence, task diversity, case-level generalization and participant power are unresolved.
- Public answers are compromised for human recruitment; create private novel cases. Renderer output is label-blinded, not fully perceptually blinded.
- The same author produced truth and implementation. Test coverage does not substitute for independent truth validation or Challenger review.
- This is a static evidence-interpretation apparatus, not a runtime qualification or a measured human study.

## Owner gates and amendment record

G1 protocol/schema/analysis/stopping freeze: PENDING. G2 private truth/corpus freeze: PENDING. G3 human experiment start: PENDING. G4 outcome unblinding: PENDING. G5 final claims/research release: PENDING. Record each approval against exact artifacts, revision and hashes; no inferred approvals. Before G1, resolve listed blockers. After freeze, amendments are prospective, versioned and retain original artifacts; after outcome access, changed analyses are explicitly exploratory. Registration completion and external logistics remain in the separate existing task.

## Analysis amendment — November 2, 2026 (not a freeze)

Missing/aborted sensitivity bounds and packet-stratified cluster percentile intervals for incorrect acceptance, appropriate HOLD, false rejection and Brier score are implemented as synthetic software checks. See `analysis-extension.md` for estimands, exact formulas, degeneracy rules and limitations. Timing/burden remain descriptive; their uncertainty, reliability bins and the other planned measures need explicit disposition before G1. G1–G5 remain pending; no human outcome access is authorized.

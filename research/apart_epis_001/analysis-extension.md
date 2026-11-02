# Analysis extension — software verification, not a protocol freeze

P2 / POST-V1 / NONBLOCKING. Extends PR #555 at d0c9f9d26c4970199fc707e0c0e086156f2ad2af. Presentation-byte validation and human-unblinding rejection remain in place. No human data were read or generated. All G1–G5 approvals remain owner-controlled and pending.

## Estimands and missingness

For each arm, incorrect acceptance uses all assigned nonacceptable cases; appropriate HOLD uses all assigned HOLD-truth cases; false rejection uses all assigned acceptable cases; Brier uses all assigned cases. Complete-case point estimates in `arms` are unchanged. Missing and aborted trials contribute unknown outcomes, never zero-imputed point estimates. A wholly missing participant remains in the assignment-derived cluster inventory.

For N eligible assigned outcomes, observed sum S and M unknown outcomes, sharp bounds are [S/N, (S+M)/N]. All four outcomes are bounded by [0,1]. With N=0, endpoints are null; with all outcomes unknown they are [0,1]. For a contrast X−Y, endpoints are [LX−UY, UX−LY]. These are worst/best-case identification bounds, not confidence intervals. Lower is favorable for incorrect acceptance, false rejection and Brier; upper is favorable for appropriate HOLD. No missing-at-random assumption is needed for these bounds. Finite timing limits or burden scale limits are not used to imply informative sensitivity results for those secondary outcomes.

## Cluster algorithm

`uncertainty.summarize` accepts explicitly synthetic participant clusters with packet IDs 1–4 and eligible assigned outcome lists for all arms and metrics. Missing/aborted outcomes are None. IDs must be unique; packet membership is immutable per participant; inconsistent assignment shapes within a packet fail closed. This low-level kernel consumes scored test data, not raw participant responses or HTML. The production pilot adapter validates HTML and response schema before constructing its clusters. The kernel cannot establish that a supplied assignment roster is complete or authentic; the future approved capture system must do so.

Sort clusters by ID within packet. Using a local Python `random.Random(510)`, draw each packet's original number of participants with replacement, independently across packets, for 10,000 replicates. Every draw carries the participant's entire outcome vector across arms, including nulls. Repeated draws retain multiplicity. Recompute pooled complete-case means and within-replicate arm differences. These are trial-weighted means, not means of participant means. Different completion patterns may change observed weighting; missingness bounds must accompany interpretation.

95% percentile endpoints use linear interpolation at (n−1)q for q=.025 and .975. Record seed, resample count, packet counts and valid/undefined replicate counts. If any packet has fewer than two participants, all intervals are unavailable. If any replicate for a metric/contrast has an empty denominator, its endpoints are null rather than silently conditioning on successful draws. Constant fixtures can yield zero-width intervals; that is fixture behavior, not evidence of certainty. The two-per-packet computational minimum does not override the protocol's proposed four-completed-sessions-per-packet threshold for human reporting.

## Verification versus future inference

The original 56-presentation fixture has one invented participant per packet: its bounds are computed, but cluster intervals are unavailable. `test_uncertainty.fixture()` separately constructs 16 invented participants with perfectly dependent repeated judgments. Its 10,000-draw check matches hand-derived Binomial(16,.5) quantiles, preserves paired zero contrasts, and would expose spuriously narrow row-independent resampling. A packet-constant fixture verifies fixed stratum weights. These identities and outcomes are software inputs, not recruitment or human findings.

For a future approved study, the algorithm targets participant sampling variation conditional on a fixed corpus and packet allocation. It does not estimate case-population uncertainty, solve convenience-sample bias, establish power, adjust for multiple comparisons, justify significance claims, or repair informative attrition. Small-stratum percentile coverage is not guaranteed. No human adapter or unblinding permission is added; relabeling actual outcomes as synthetic is prohibited.

Before G1: owner/challenger review of estimands, roster/capture design, missingness and interval rules, and disposition of secondary timing/burden uncertainty and reliability bins remain. Private novel-case validation, independent truth adjudication, delivery/capture and design confounding remain unresolved. The proposed 16-person sample is still an unapproved feasibility proposal. G2 truth freeze, G3 experiment start, G4 unblinding and G5 claims each require separate explicit owner approval. No v1 release dependency is introduced.

## Reproduce

From the repository root:

```sh
python -m unittest discover -s research/apart_epis_001 -v
python research/apart_epis_001/pilot.py build /tmp/apart-analysis-new
python research/apart_epis_001/pilot.py analyze /tmp/apart-analysis-new
```

Use a new directory for each run. `analysis-verification.json` records source hashes, the test transcript and deterministic output digests. Prior retained results remain historical.

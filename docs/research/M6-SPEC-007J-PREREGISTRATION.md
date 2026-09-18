# M6-SPEC-007J Preregistration — Branch-Aware Review with Bound Task Identity

007I failed in the apparatus because a stale task ID was used for usage recording. 007J preserves the intended 007I scientific variable and fixes only experiment identity plumbing.

## Identity correction

One constant, `TASK_ID = "m6-discover-007j"`, is used for:
- manifest task identity;
- Scientist call accounting;
- reviewer call accounting;
- admission receipt identity.

## Preserved scientific conditions

- same observed-anomaly MeasurementGap contract as 007H;
- same aggregate EvidenceSnapshot and evidence hashes;
- same qwen2.5:7b Scientist/reviewer;
- no supplied question, target, intervention, or hypothesis;
- same deterministic mechanical verifier;
- same branch-aware semantic reviewer designed in 007I;
- human approval required;
- no implementation or promotion authority.

## Success

A mechanically admissible proposal must also pass the appropriate independent semantic review. Only then is an admission receipt issued.

A successful MeasurementGap authorizes evidence acquisition only; it does not authorize M6-008 candidate implementation.

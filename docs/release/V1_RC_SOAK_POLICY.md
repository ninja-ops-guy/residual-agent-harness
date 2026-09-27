# RESIDUAL v1 RC Soak Policy

**Status:** PREPARATION DRAFT aligned with Qualification-v1's existing release-soak tiers.

## Required tiers

Qualification-v1 defines:

- **24h** uninterrupted release soak;
- **72h** extended soak after the 24h tier is clean;
- **30d** as separate long-duration operational evidence on a persistent host.

The 24h tier is the minimum release-soak gate. The 72h tier is stronger extended confidence and does not replace other mandatory gates.

## Identity

A soak receipt MUST bind exact RC HEAD/TREE, exact artifact digest(s), environment identity, soak tier, start/end timestamps, process identity, workload identity, and evidence hashes.

Any RC source-byte change invalidates the soak for that RC.

## 24h success conditions

A clean 24h release soak requires:

- no integrity failure;
- no authority/fencing violation;
- no duplicate accepted work;
- no unrecovered crash;
- no evidence-chain corruption;
- no secret leakage;
- no unexplained process exit;
- resource growth within declared qualification thresholds;
- retained restart/recovery evidence;
- no unresolved release-blocking failure.

Staying alive while leaking resources is not PASS.

## Failure handling

### Product failure

Preserve first failure, stop or safely seal the attempt, classify the failed invariant, create a new successor identity only after authorized repair, and restart the release soak on the successor.

### Infrastructure/environment failure

Do not automatically classify it as product failure or PASS. Retain failure timestamp, environment state, candidate identity, and evidence proving whether product state/integrity was affected. The owner determines whether the same RC soak may resume or must restart.

### External dependency failure

Retain separately. Do not erase product evidence or silently convert it to PASS.

## Evidence cadence

Retain bounded periodic observations sufficient to reconstruct liveness, RSS/resource growth, file-descriptor growth where supported, workload progress, restart/recovery state, integrity status, and first failure.

Do not retain secrets merely to increase observability.

## Promotion

Completing 24h/72h soak does not itself authorize release. It is one input to the final release packet and human release disposition.

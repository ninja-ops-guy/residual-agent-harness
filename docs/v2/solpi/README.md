# Residual v2 — SoL-Pi Port Specs

Four integration-ready specs ported from NVIDIA SoL-Pi's auto-research loop mechanisms, adapted to residual's existing architecture (CAS store, run ledger, exact-head attestation, qualification gates).

| Spec | Mechanism | Lane | Depends on |
|---|---|---|---|
| SPEC-EVPR-001 | Evidence-Preserving Reducer | Verification / trust boundary | CAS, ledger (exists) |
| SPEC-ENVB-002 | Environment Bank | M6 autonomous discovery | D2, WebVM, swarm history |
| SPEC-OBSH-003 | ObservationPack context handles | Context economics | CAS, ledger (exists) |
| SPEC-CMPE-004 | Compaction as ledger event | Context economics / auditability | Ledger; OBS-003 recommended |

Suggested implementation order: EVPR-001 → OBS-003 → CMPE-004 → ENVB-002 (ENVB last because it is the largest and benefits from the others being in place for its own runs).

# AX-21 / R4 Observation — Exact-Head CI Separates Product Correctness from Environment Contract

**Observation ID:** AX21-OBS-R4-CIENV-20260925-003  
**Date:** 2026-09-25  
**Status:** OBSERVED / CORPUS EVIDENCE  
**Campaign:** SNYK-R4-02 exact-head CI  
**PR:** #457  
**Candidate HEAD:** ff410b5fb8695104f1dc78ffae7cc78199e15da9  
**Candidate tree:** ab16aa6b7afb58ab602c3e54a1e7c4c48a406c45

## Observation

Exact-head CI resolved one local qualification ambiguity while exposing a separate compatibility-contract failure.

Local deterministic qualification had been BLOCKED by an M4 namespace/mount failure before candidate behavior could be fully qualified. GitHub CI ran the same exact candidate and passed the M4 prerequisite and deterministic regression, demonstrating that the local M4 blocker was environmental rather than reproduced candidate behavior.

At the same time, the candidate's newly explicit patched-Python floor caused Windows/macOS lifecycle installation to reject Python 3.12.10 and the Pages VM path to reject Python 3.11.2. Those are candidate/integration compatibility gaps, not evidence that the archive-confinement remediation failed.

## Measured exact-head result

- Qualification-v1: 23/25 required gates passed.
- Deterministic regression: 2,406 tests, zero failures/skips.
- R4-02 archive tests included: 83 passed.
- M4 CI: PASS.
- Local M4 blocker reproduced in CI: NO.
- Station, clean-install, Factory, controller/provider, active-workload, and exact-wheel checks passed.
- Windows/macOS lifecycle: blocked by Python 3.12.10 versus the candidate runtime floor.
- Pages VM: blocked by Python 3.11.2 versus the candidate runtime floor.
- Candidate HEAD did not change during the CI observation.
- Merge remained unauthorized.

## Candidate invariant

**AX21-ENV-SEP-01 — Failure-Domain Separation**

> Qualification evidence must distinguish candidate behavior, environment capability, integration/runtime contract, and external automation failure. A failure in one domain must not be silently promoted into a conclusion about another domain.

## Implications

1. **Exact-head execution in a second environment can resolve local ambiguity without erasing local evidence.** The local M4 BLOCKED receipt remains valid as an observation about that host; CI adds evidence that the blocker does not reproduce in the independent environment.
2. **Security hardening can expose compatibility debt.** Tightening the runtime security floor did not regress the archive invariant, but it invalidated CI environments still pinned below that floor.
3. **Overall red is not a single semantic state.** A 23/25 result contains materially different failure classes: product/integration compatibility versus unrelated advisory automation.
4. **Evidence should bind both candidate identity and execution environment.** HEAD/tree identity alone is insufficient to explain divergent qualification outcomes.
5. **A security fix should not be weakened merely to preserve an obsolete runner environment.** The integration environment should either move to the supported security floor or the runtime contract should be deliberately redesigned with equivalent protection.

## Follow-up experiment

Introduce machine-readable failure-domain classification into qualification receipts:

- CANDIDATE_FAILURE
- ENVIRONMENT_BLOCKER
- INTEGRATION_CONTRACT_MISMATCH
- EXTERNAL_AUTOMATION_FAILURE
- EVIDENCE_INCOMPLETE

Then replay a candidate across at least two environments and verify that the coordinator:
- retains both receipts;
- does not overwrite a local BLOCKED result with a remote PASS;
- does not call the candidate qualified while required integration gates remain unsatisfied;
- routes environment updates separately from product-security changes.

## Limitations

This observation is scoped to PR #457 and the recorded CI/local executions. It does not establish that all local M4 failures are environmental, nor that the candidate is release-ready. Qualification remained FAIL because required lifecycle gates were unsatisfied.

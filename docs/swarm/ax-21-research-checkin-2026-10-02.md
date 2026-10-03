# AX-21 / RESIDUAL research check-in — 2026-10-02

Status: append-only research-maintenance record. This record preserves negative and inconclusive results, separates observation from interpretation, and does not grant merge, deployment, security, autonomy, release, or acceptance authority.

## Evidence boundary

Reviewed:
- accepted `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`;
- PR #509, documentation-only OpenClaw 0.2.1 provenance reconciliation;
- PR #511, OpenClaw lifecycle-receipt claim-narrowing successor;
- exact-head hosted CI for #511;
- #511 AI-assisted independent technical review;
- issue #510 / APART-EPIS-001 prospective provenance-and-human-calibration study;
- prior AX-21 pre-release baseline/check-in records, including the unchanged P5 before-condition.

No new live Shared Comms/failover seat census, physical OpenClaw lifecycle execution, Orpheus Runner R0 execution, P5 after-condition, or final release-composition qualification was found in the reviewed evidence. Those states are therefore not advanced here.

## A. OpenClaw lifecycle receipts were overclaiming physical outcomes

Source: PR #511, stacked on #509.

### Observed evidence

The successor explicitly corrects lifecycle receipts so successful software capture no longer implies independently established physical cessation or process replacement.

Current successor behavior:
- cancel-related receipts report `NATIVE_CANCEL_UNVERIFIED`;
- restart-related receipts report `RESTART_UNVERIFIED`;
- physical outcome remains unverified;
- release admission remains false;
- promotion authority remains false.

The candidate explicitly retains the distinction that:
- an abort acknowledgment plus later absence is not proof that native execution ceased;
- plugin reload is not independently verified gateway-process replacement;
- PID/start-time and supervisor metadata supplied by the same software path are not independent proof of replacement;
- caller-supplied proof/approval flags do not create a verified path.

The new lifecycle corpus run against the unchanged older source produced 36 PASS / 52 FAIL. This is retained as sensitivity evidence for the new checks, not represented as 52 physical incidents.

### Exact-head software measurements

Published #511 HEAD: `7c35f72863e1631d4675c82f459b717a53b53bd9`
TREE: `75b88f1b8c3f7f1ec6672c8ffbda953b82cbd88e`

Hosted OpenClaw component CI:
- Node 24.21.0: 185 / 185 PASS, 0 fail, 0 skipped, 0 cancelled, 0 TODO;
- Node 22.16.0: 185 / 185 PASS, 0 fail, 0 skipped, 0 cancelled, 0 TODO;
- both runs return `SOFTWARE_COMPONENT_PASS`;
- both retain `release_result: BLOCKED`.

RESIDUAL Qualification-v1 on the same published HEAD:
- all 25 required gates present;
- aggregate result PASS;
- no missing gates;
- no qualification UNKNOWN reason in the aggregate manifest.

Command Station, Controller/provider, Clean install, Factory ownership, Control Plane, and measured-evaluation workflows are also green on this exact published head.

### Independent review

The AI-assisted review posted on #511 records:
- exact published HEAD/TREE and direct-parent verification;
- all 970 file blobs/modes checked against the reviewed tree;
- 50 / 50 independently authored pure-contract regressions PASS;
- no open finding within the bounded three-file repair scope.

The review explicitly does not count as human maintainer attestation and does not establish physical cessation, native process replacement, live-provider qualification, or remaining OC-V1 gates.

### Falsified hypothesis

**Falsified:** a self-consistent lifecycle capture, abort acknowledgment, reload observation, or same-path process metadata is sufficient evidence to promote a physical cancel/restart claim to VERIFIED.

### Interpretation

This is an epistemic-control improvement rather than a physical-lifecycle success result. The repair makes the claim weaker because the available evidence is weaker. That is desirable behavior for AX-21: the control plane should prefer an explicit UNVERIFIED state over a stronger claim that the evidence cannot independently support.

### Negative-result preservation

The 36/52 old-source sensitivity result remains part of the research record. The corrected successor does not turn those prior failing observations into historical PASS states.

### Candidates

- `RES-UP-LIFECYCLE-PHYSICAL-PROOF-001` — separate software capture validity from independently observed physical-effect verification.
- `RES-UP-EVIDENCE-INDEPENDENCE-CLASS-001` — encode whether evidence is self-asserted, same-path observed, independently observed, or authority-attested.
- `EXP-LIFECYCLE-CAPTURE-VS-PHYSICAL-01` — deliberately exercise cancel and restart while collecting both contract receipts and an independent host/process observer; measure false-positive/false-negative promotion and reconciliation behavior.

## B. Green software evidence does not transfer to native physical outcome

### Observed contradiction

#511 now has strong exact-head hosted software evidence and aggregate Qualification-v1 PASS, while the PR itself still marks native physical cessation/process replacement and live acceptance as outstanding.

### Interpretation

There is no contradiction in the evidence once scope is preserved. The contradiction appears only if a software-qualified lifecycle contract is interpreted as proof that a real OpenClaw process stopped or was replaced.

### Paper-safe conclusion

**Component software qualification and physical lifecycle verification are distinct experimental propositions.** A candidate may be fully green within a software contract and still be correctly blocked from a physical or release claim.

## C. Evaluator dependency failure remains distinct from candidate failure

Source: #511 PR-Agent advisory workflow.

### Observed evidence

The PR-Agent workflow failed because both configured model attempts returned an OpenAI authentication error. No substantive advisory review was produced by that workflow.

### Interpretation

This is an evaluation-apparatus/dependency failure. It is not evidence that #511's candidate tests failed, and it must not be counted as a candidate security or correctness defect.

The separate AI-assisted review comment is supporting bounded review evidence, but it does not convert the failed automated advisory lane into PASS and does not satisfy human maintainer authority.

### Candidate

- `RES-UP-EVALUATOR-FAILURE-PROVENANCE-002` — require machine-readable separation of CANDIDATE_FAIL, ENVIRONMENT_FAIL, EVALUATOR_DEPENDENCY_FAIL, REVIEW_NOT_EXECUTED, GOVERNANCE_BLOCK, and PASS.

## D. OpenClaw documentation provenance drift was corrected without changing runtime

Source: PR #509.

### Observed evidence

#509 is documentation-only and reconciles the visible package README from a stale `0.1.0 candidate` / `addition-only` description to the already composed `0.2.1` Station + OpenClaw candidate description. It explicitly changes no runtime, Station, gate-ledger, host, provider, release, or accepted-main bytes.

### Interpretation

Descriptive package documentation can lag the actual candidate composition. Correcting it improves reproducibility and operator interpretation but does not qualify the implementation.

### Candidate

- `RES-UP-DOC-COMPOSITION-PROVENANCE-001` — bind user-visible candidate/version descriptions to exact composition identity and flag stale descriptions during qualification.

## E. APART-EPIS-001 turns an AX-21 pattern into a prospective human-calibration experiment

Source: issue #510.

### Observed research registration

The new prospective study asks:

> Can candidate-bound provenance improve human calibration when an AI agent's self-report, execution evidence, and independent verifier disagree?

Four frozen treatment conditions are proposed:
- A: self-report only;
- B: self-report plus ordinary unbound execution log;
- C: exact candidate/source identity plus provenance-preserving receipt/evidence;
- D: C plus independent verifier result and authority state.

The corpus is required to contain clean controls plus stale evidence, cross-candidate/replayed evidence, missing artifacts, candidate/source mismatch, worker-verifier disagreement, verifier UNKNOWN, intentionally wrong verifier judgment, multiple candidate generations, and attempted acceptance without required authority/HITL state.

Primary outcomes are:
1. incorrect acceptance rate;
2. appropriate HOLD/escalation/abstention rate;
3. confidence calibration against hidden ground truth;
4. decision time;
5. evidence burden.

The issue explicitly keeps the program post-v1/nonblocking and requires owner gates for protocol freeze, hidden-ground-truth freeze, experiment start, unblinding, and final claims/research release.

### Interpretation

This is not an experimental result yet. It is a stronger prospective test of a recurring AX-21 observation: candidate-bound evidence may change human acceptance decisions, but verifier presence itself must not be treated as ground truth.

The inclusion of deliberately wrong verifier cases is especially important because it allows the study to distinguish provenance value from "the verifier told the operator the answer."

### External-claim boundary

The issue records that the research direction fits the intended sprint context while participation/submission logistics remain awaiting confirmation. This record does not claim sprint participation, funding, Fellowship acceptance, or scientific validation.

### Research-program ID

- `APART-EPIS-001` — candidate-bound provenance and human calibration.

## F. No new live-swarm result should be manufactured

The accessible evidence in this cycle does not establish a newer:
- Shared Comms READY/DEGRADED/DOWN census;
- provider failover event;
- REQ-LP-1 replication;
- physical F6 result;
- Orpheus/DOT Runner R0 execution;
- owner-absence/autonomy run;
- P5 operator-friction after-condition.

Those states remain unchanged/UNKNOWN for this check-in rather than being inferred from repository software progress.

## Comparison with the frozen/pre-release AX-21 baseline

The pre-release AX-21 baseline already established that operational truth was expensive to reconstruct manually and that the research record must preserve failures, operator interventions, exact identities, and negative evidence. Later AX-21 check-ins explicitly kept the P5 before-condition unchanged while Shared Comms remained a draft path rather than a measured after-condition.

Relative to that baseline, this cycle adds:
- a new lifecycle **claim-correction** result, where stronger "verified" physical semantics were replaced by explicit UNVERIFIED outcomes;
- a 36 PASS / 52 FAIL sensitivity corpus against the old lifecycle source;
- exact-head 185/185 hosted software PASS on two Node versions while release remains BLOCKED;
- a full 25-gate Qualification-v1 PASS that still does not imply native physical success;
- another concrete evaluator-dependency failure class;
- a documentation/composition provenance correction;
- a preregistered human-calibration study designed to test whether candidate-bound provenance actually improves oversight decisions.

It does **not** provide a valid P5 after-condition, sustained autonomous-development measurement, physical lifecycle success, or final release qualification.

## Paper-relevant conclusions

1. **Epistemic weakening can be a correctness improvement.** Replacing unsupported VERIFIED semantics with explicit UNVERIFIED state is meaningful control-plane progress.
2. **Evidence independence is a first-class variable.** Same-path metadata can support diagnosis without independently proving the physical event being claimed.
3. **Qualification scope must survive composition and lifecycle interpretation.** A green software contract does not establish the corresponding native effect.
4. **Negative sensitivity evidence is valuable.** The 36/52 old-source result should remain visible after repair.
5. **Evaluator failure is not candidate failure.** Review-provider authentication/dependency failures require separate provenance.
6. **Documentation provenance matters for reproduction, but documentation correction is not implementation qualification.**
7. **Human calibration is now a falsifiable research target.** APART-EPIS-001 tests whether provenance changes incorrect acceptance, abstention, confidence, timing, and burden rather than assuming auditability is beneficial.

## Non-claims

This check-in does not establish:
- whole-system security;
- successful native OpenClaw cancellation or gateway process replacement;
- live-provider qualification;
- physical F6 success;
- MESH_QUALIFIED;
- Orpheus Runner R0 qualification;
- improved P5 operator burden;
- owner-absence autonomy;
- sustained autonomous recursive development;
- final v1 release readiness;
- participation in or acceptance to any external research sprint/fellowship.

## Research-maintenance queue

Priority follow-ups:
1. `EXP-LIFECYCLE-CAPTURE-VS-PHYSICAL-01`
2. `RES-UP-LIFECYCLE-PHYSICAL-PROOF-001`
3. `RES-UP-EVIDENCE-INDEPENDENCE-CLASS-001`
4. `RES-UP-EVALUATOR-FAILURE-PROVENANCE-002`
5. `RES-UP-DOC-COMPOSITION-PROVENANCE-001`
6. `APART-EPIS-001` preparation through its frozen owner gates without entering the v1 critical path.

Material evidence changed, so a new append-only check-in is warranted.

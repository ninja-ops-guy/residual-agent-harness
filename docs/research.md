# Research claim and prior art

Date: 2026-09-19. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Current accepted engineering boundary

Current `main` is **`0a675017a51f94e489528a607032e7463fbf7993`**.

Recent accepted engineering changes matter to interpretation but are not scientific results:

- **#307** repairs duplicate feature-branch CI fan-out while preserving non-cancelling production evidence;
- **#260** accepts the provider-bootstrap guard;
- **#288** closes product issue #208 with pre-dispatch Station budget/deadline admission and exact run-control-bound export eligibility;
- **#320** accepts repository-side CSP/anti-clickjacking configuration, while production Vercel header validation remains pending;
- **#328** accepts the non-workflow core of #324's execution/egress/XML security hardening, while workflow credential-persistence changes remain open under #324.

None of these merges establishes the central research hypothesis, live-provider model quality, universal M4 qualification or a paper-facing effect size.

Every current `main` SHA now receives its own non-cancelling production Pages attempt. Exact-current-main Pages run **`35431634267`**, attempt 1, completed **PASS**: generated browser proof, deployment, published WebVM revision/real-guest execution, and narrow Chromium acceptance all passed. Retained live proof is artifact `10580449851`, SHA-256 `ebdecf8e4055679933f1941f648d422d37a38ba5e4dad1f285967b83ccf684aa`. Earlier production Pages failure on `e7b72ad...` remains retained evidence for that exact revision and is not erased.

This production Pages PASS is release/browser qualification evidence only. It does not establish the central systems hypothesis, provider/model quality, physical heavyweight-WebVM reliability, or any paper-facing effect size.

## Real-model development evidence: #202

Draft #202 retains both favorable and unfavorable evidence.

An earlier heterogeneous three-task DAG run on exact experiment head `6b30125...` remains **FAIL**: 1/3 tasks integrated, the repaired branch did not satisfy its behavioral check within the attempt budget, and the dependent reporting task did not run.

A later distinct exact-head run on `03c77d12...` is a bounded **PASS** using real local Ollama models: 3/3 tasks integrated, verification receipts and dependency lineage were retained, deliberate bad candidates/reviewer outputs were rejected, repair succeeded, and release export completed.

The later PASS does **not** erase the earlier FAIL. It establishes one bounded successful experiment on that exact revision/configuration, not general DAG reliability, provider-independent model quality or production readiness.

## M6 self-maintenance evidence

The bounded self-host sequence remains mixed:

- **#203 / M6-SPEC-001:** **FAIL**, 0/1 integrated, no verification receipt/release.
- **#204 / M6-SPEC-002:** **FAIL**, 0/1 integrated after the bounded pass budget.
- **#215 / M6-SPEC-003:** **FAIL** despite prior-candidate repair context.
- **#217 / M6-SPEC-004:** **FAIL** after transport/source clarification; no review/receipt/release.
- **#220 / M6-SPEC-006:** bounded corrected-path **PASS**: earlier bad candidates were rejected, a later candidate satisfied frozen checks, review approved it, the exact reviewed head integrated, a receipt was issued and release export completed.

The #220 PASS is positive evidence but does not establish general autonomous self-maintenance or recursive self-improvement.

## Deterministic stress evidence: #206, #207 and #212

Research workflow `success` means the apparatus executed and retained evidence; it does not convert scenario-level FAIL/BLOCKED outcomes into PASS.

Retained Campaign A evidence includes:

- **STRESS-A4:** **BLOCKED / invalid for the intended repair-pressure intervention** because the intended fault was not injected before provider/usage failure.
- **STRESS-A5:** **FAIL / incomplete**, 3/6 DAG tasks integrated before escalation with no release.
- **STRESS-A6:** **FAIL in scope**, 0/3 successful Qwen2.5-Coder 7B trials in the frozen campaign.

Retained Campaign B/C evidence includes:

- **#207 STRESS-B1:** **FAIL** — exhausted-budget accounting was observed after accepted integration/release on the frozen baseline.
- **#207 STRESS-B2:** bounded control **PASS**.
- **#207 STRESS-B3:** **FAIL** — a non-empty release materialized after terminal verifier failure.
- **#207 STRESS-B4:** corrupt-candidate containment **PASS**, recovery-to-success **FAIL / not achieved**.
- **#212 malformed-runner / invalid-reviewer containment:** bounded **PASS** cells.
- **#212 denial→approval recovery:** bounded **PASS**.
- **#212 transient HTTP 500:** failover success remains **UNKNOWN / not established**.
- **#212 missing usage:** **FAIL for accounting-before-authority** because integration plus a receipt occurred before a later `usage_unknown_or_invalid` abort on that frozen baseline.

Merged **#288** now repairs the tracked product defect (#208) with host-owned pre-dispatch admission and bound export eligibility. That merge changes accepted product behavior; it does not retroactively turn the frozen #207/#212 cells into PASS. Stronger present-tense claims about budget exhaustion, unknown usage or release ordering require fresh requalification against the accepted repair. Until then, the repaired product defect is accepted while the stronger empirical claim remains **UNKNOWN pending repaired-path requalification**.

#212 remains an open draft research matrix, not a product merge.

## M6.2 evidence-driven autonomous discovery

The M6.2 sequence deliberately separates execution, representation, evidence grounding, semantic review, evidence use, metric identity, provenance and Planner-transcription failures.

Key retained cells:

- **#244 / 007 and #246 / 007B:** experiment execution **FAIL** before a valid discovery proposal.
- **#249 / 007C:** bounded autonomous-discovery **FAIL** after malformed/repeated/truncated candidates exhausted the brake.
- **#250/#251/#252/#254:** bounded **FAIL** cells after typed output reached deterministic admission but repeatedly requested already-measured evidence.
- **#255 / 007H:** semantic-review **FAIL** for causal overclaim, non-falsifiable acceptance and preservation-criteria defects.
- **#257 / 007J:** first retained bounded autonomous-discovery **PASS at formal MeasurementGap admission**. Receipt: `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`.
- **#259/#262/#263:** bounded post-gap/evidence-resolver/active-query **FAIL** cells because the Scientist continued requesting already-present or already-resolved evidence.
- **#264 / 007O:** workflow/receipt integrity succeeded, but the scientific conclusion is **UNKNOWN** because admitted metric identity/semantics were ambiguous. Receipt integrity is not semantic truth.
- **#274 / 007S:** bounded **PASS** for registry/receipt semantic-binding controls.
- **#273/#277:** retained provenance/Planner **FAIL** cells; #277 positively demonstrates host-owned provenance binding while the overall experiment still fails at Planner transcription.

The Metric Registry and proof-carrying derivation-graph line exists to prevent ambiguous/duplicate metric and semantic-custody errors. General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its required positive semantic/derivation admission gates are actually satisfied.

## M6-MESH-001 cooperative-efficiency pilot

Open **#319** retains the first frozen M6-MESH-001 crossover pilot. Workflow run `35424274389` is **PASS for experiment/apparatus execution** and artifact `10578541714` retains the observations.

The frozen cell uses one local Ollama host, Qwen2.5-Coder 1.5B, two independent obligations, sequential versus two-call concurrent execution, and three repeats. Both conditions passed all six obligation checks. Retained mean wall time is about **2.1899 s sequential** versus **1.8300 s concurrent**, an observed **1.1967x** ratio in favor of the concurrent condition.

This is **positive bounded pilot evidence**, not a general mesh-efficiency result. Three repeats on one host with visible warm-up/order sensitivity are insufficient for a durable performance claim. Therefore:

- Trial-0 apparatus execution: **PASS**;
- task/verifier success in this frozen cell: **PASS** for both conditions;
- observed wall-clock difference in this frozen cell: positive / retained;
- statistically durable concurrency benefit: **UNKNOWN / not established**;
- general distributed mesh/swarm efficiency: **UNKNOWN / not established**.

Branch security findings and acceptance status remain separate from experiment execution; a successful experiment workflow is not a security PASS or merge authorization.

## Research Workbench candidate: #323

Open **#323** proposes a built-in Research Workbench that binds experiment ID, catalog commit and canonical definition SHA-256, enforces preregistered trial counts, retains run history/evidence bundles and routes experiment execution through normal Station governance.

Its first planned pilot, **M6-WB-001**, is deliberately declarative: the model emits one JSON research artifact and host-owned checks validate exact preregistered content; model-authored Python/shell/JS is not executed by that pilot.

The PR's own contract requires two things before the first authoritative trial: #288 accepted on `main`, then #323 rebased and requalified against that repaired main. The first prerequisite is now satisfied. The second is not: #323 remains based on `e7b72ad...` at exact head `f32b99b7d62bc35872daaf4da00787761b7ca8ea`.

Therefore:

- Workbench implementation candidate: **UNACCEPTED / draft**;
- previous exact-head qualification failures: retained historical evidence for `f32b99b7...`;
- first authoritative M6-WB-001 trial: **BLOCKED / not run** pending rebase and fresh qualification;
- staged M6-SCALE/M6-FAIL/M6-CONFLICT/M6-ABLATE definitions: definition availability only, not experimental evidence;
- any paper-facing result from the Workbench path: **UNKNOWN / not established**.

## Security and deployment evidence are not research results

Merged #320 and #328 improve accepted engineering/security controls, but they do not establish the systems hypothesis.

- #320 production Vercel header enforcement remains **UNKNOWN / pending** until retained post-merge production inspection/security validation exists.
- #328 accepts the non-workflow core security hardening; the workflow credential-persistence portion remains open in #324.
- scanner/vendor confidence is not scientific or repository acceptance evidence.

Likewise, exact-current-main production Pages run `35431634267` is a **PASS for its release/browser/real-guest qualification scope**. That PASS does not establish model quality or the research hypothesis.

## WebVM / provider research boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Accepted provider/session/bootstrap/publication repairs do not substitute for fresh real-account semantic evidence. The #186 iOS/WebKit fallback remains accepted, but it is not physical heavyweight-WebVM reliability evidence. Issues #120/#126 remain open because bounded mitigations and individual green runs do not establish long-run recurrence rate or root cause.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. PR #139 and downstream #134 remain a separate protected sequence. Qualification-v1 work on its separate testing branch is branch evidence only unless and until the applicable production sequence is deliberately accepted.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and research independence

Merged #168 establishes repository merge control as:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This is **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer.

The Actions backlog recorded in #305 has operationally drained to **0 queued runs**, and #307 is now merged as the structural fan-out repair. The original saturation snapshots remain evidence; queue recovery does not erase first-attempt failures or permit required qualification to be skipped.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Confirmatory gate

Before paper-facing outcome collection, freeze exact source, execution/evidence path, workload/task mapping, model/version, inference settings, verifier policies, prompts, metrics and analysis code **before** observing confirmatory results.

At minimum:

1. preserve exact-revision failures, blocked interventions and mixed results rather than treating later PASSes as erasure;
2. requalify any selected path affected by historical #207/#208/#212 authority-ordering failures against the accepted #288 repair;
3. rebase/requalify #323 before using the Workbench for an authoritative trial;
4. resolve or explicitly exclude #120/#126 for any WebVM-dependent protocol;
5. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
6. preserve any protected ownership/requalification sequence required by the selected evidence path;
7. independently qualify the selected evidence path to the degree required by the paper claim;
8. keep `PASS`, `FAIL`, `UNKNOWN`, `BLOCKED`, missing and rejected cells in the retained evidence package.

Until those gates are met, the central systems hypothesis remains **UNKNOWN / not established by confirmatory live-model evaluation**.

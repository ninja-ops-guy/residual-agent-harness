# Trust, science and product preparation

This package prepares the three programs concurrently. It does not qualify M4,
close issues #63/#48, authorize a confirmatory study, or release v1.0.0-rc1.
Review findings and fixture results retain their own source identities.

The original implementation base is `dec571992a97b4ae80f0310aa32ffd8f542aef8c`.
The preparation branch was subsequently reconciled with main
`72634fec8916917d97f8e4f36980b8caeeba16f5` after #81, #41, #77 and #74 merged.
The independent M4 review targets PR #81 at
`30d1d020469d958d90969bc02946145c248e0adb`. Those are different trees.
Do not transfer a verdict between them. Requalification is required after merge.

## Program map

| User lane | Program | Deliverable | What remains gated |
|---|---|---|---|
| 1. Statistics | Science | Pre-results analysis plan and hash-locked protocol | Inferential engine validation, power calculation and final launch freeze |
| 2. Adversarial corpus | Science | Inert defect/control candidates, separate gold labels and scorer | Qualified verifier execution and held-out corpus expansion |
| 3. M4 property tests | Trust | Pinned-source Hypothesis and invariant suites | Findings resolved and rerun on merged main |
| 4. Sandbox red team | Trust | Bounded probes, observed-injection accounting and source review | A host that passes the namespace probe |
| 5. Evidence chain | Trust | Backward reference audit with source-pinned gaps | Complete authenticated workload-to-acceptance binding |
| 6. Reproduction | Science | `residual reproduce` and synthetic retained bundle | Native evidence authentication and inferential paper analysis |
| 7. Artifact bundle | Science | Strict versioned layout and hash validation | Real run producer mapping and external archive anchor |
| 8. Model degradation | Science | Outcome-independent tier selection and frozen routing design | Exact eligible endpoints/revisions and budgeted launch |
| 9. Heterogeneous swarm | Science | Prespecified topology comparison | Qualified execution and retained model/usage identities |
| 10. Fault injection | Science | Full fault design matrix and expected fail-closed behavior | Real observed injections at each listed boundary |
| 11. DSM-004 | Product | Ownership, fencing, ack, replay and non-consensus protocol review | Durable implementation and crash qualification |
| 12. PROD-007 | Product | Durable-boundary restart matrix and operator runbook | Actual recovery implementation and restart trials |
| 13. Instrumentation | Trust/product | Actual-mechanism microbenchmark harness | Target-host measurements for unavailable mechanisms |
| 14. Scale envelope | Trust/product | Bounded synthetic size sweeps | Executed target sizes and resource-backed operating envelope |
| 15. Cost accounting | Product/science | Attempt-level accounting audit and missing-cost rules | Complete provider and local-occupancy evidence |
| 16. Orchestration tax | Trust/science | Independent controller review and tiny-task probes | Corrections and fixed-state qualification |
| 17. Verifier quality | Trust/science | Typed-outcome audit and independent scorer | Swarm B reconciliation with M4 execution semantics |
| 18. Observability | Product | Projection/duplication/correctness accounting audit | Reconciled evidence-derived metrics |
| 19. Release engineering | Product | v1.0.0-rc1 acceptance criteria | Install/upgrade, artifact, SBOM and support gates |
| 20. Clean onboarding | Product | Isolated source-install harness and observed phase report | Genuine blank Linux VM and configured-provider smoke |
| 21. Threat model | Product/trust | Trust boundaries, mitigations, detection and exclusions | Mechanism-specific qualification, never universal safety |
| 22. Architecture invariants | Trust | Executable subset plus explicit gap matrix | Every invariant independently closed on canonical APIs |
| 23. Paper figures | Science | Empty figure/CSV templates | Retained measured data and approved analysis |
| 24. Competitive comparison | Science | Frozen comparison criteria and evidence rubric | Version-pinned primary-source assessment, no rankings yet |
| 25. Applications | Product | Six compiled plan/contract fixtures with good/broken/missing candidates | Real governed runtime execution and integration |

## Ownership and review

The six isolated branches are `swarm/prep-science`, `swarm/prep-reproduce`,
`swarm/prep-corpus`, `swarm/prep-trust`, `swarm/prep-audit` and
`swarm/prep-product`. Integration is on `swarm/three-program-preparation`.
Existing PR branches are not implementation targets for this package.
Swarm B/C/F/D changes are reviewed as separate source snapshots. The retained
Swarm B and M4 source blobs match the reconciled main; that comparison does not
constitute a fresh execution qualification.

- [Science plan](science/README.md)
- [Reproduction specifications and usage](reproduction/README.md)
- [Verifier corpus, fault matrix and quality review](verifier/README.md)
- [M4 review, property tests and invariant coverage](trust/README.md)
- [Chain, cost, orchestration and observability audits](audit/README.md)
- [Recovery, threat model, release and onboarding](product/README.md)
- [Application fixtures](../../examples/application-preflight/README.md)

The detailed audit documents distinguish confirmed observations, source-level
risks, unexecuted probes and proposed protocols. A failing or skipped boundary
does not disappear because another suite passes. Public synthetic examples are
excluded from confirmatory samples and from model-selection decisions.

## Launch order

1. Resolve M4 review findings, inspect exact-head CI, merge the accepted change,
   and independently qualify the resulting main commit/tree on a supported host.
2. Close #63 only from that retained evidence; reconcile #48 and outstanding
   runtime timing failures without treating a retry pass as race resolution.
3. Qualify the chosen evidence adapter, verifier/grader and complete workload-cell
   mapping. Resolve protocol, workload, model, prompt, policy, budget and analysis
   identifiers; complete the power and inferential validation gates.
4. Anchor the final immutable launch manifest externally before outcome access.
5. Execute the locked fixed-model R0–R5 study, then the prespecified degradation
   and heterogeneous extensions and 24h → 72h → 30-day soak gates.
6. Reproduce paper tables from retained source artifacts. Preserve every failure,
   UNKNOWN, missing cost and negative result. Publish only claims the retained
   evidence supports.

The current descriptive reproduction command does not authenticate native
Station evidence or implement every inferential analysis in the science plan.
Those limits are intentional release gates, not completed research results.

## Validation and first commands

The integrated preparation tools passed **85 tests and 48 subtests**. After
reconciliation with the newer main, the regression selection reported **1,275
passed, 278 subtests passed, 53 skipped and 1 failed**. The remaining failure is
the host denying creation of an AF_UNIX socket before the snapshot check can run;
a fresh interpreter independently reproduces that permission denial. Previously
blocked namespace suites were not retried, and the pinned trust suite remains
a separate run. This is not a green full-suite qualification.

The initial
broad regression sweep was not green: nine existing sandbox cases could not
create namespaces, the baseline traceability checker lacks its executable bit,
and one new documentation wording issue was corrected and retested. The affected
sandbox/runtime files and checker were unchanged from the base. See the retained
[validation record](validation/summary.json) and its raw JUnit artifacts.
The later traceability merge fixes the executable bit; the reconciled checks pass.

The independent #81 suite records **27 PASS, 13 UNKNOWN and 3 known gaps**;
its overall verdict is **INCOMPLETE**. An automated security restriction
interrupted the worker after evidence was written. The coordinator checked the
retained runner, suite and output hashes without another sandbox run. This
package does not turn those unknowns or expected failures into qualification.

From the checkout root, with a new destination filename/directory for each run:

```sh
python -m residual reproduce synthetic-demo --runs-dir examples/reproduction
python scripts/validate_adversarial_corpus.py validate
python scripts/application_preflight.py --output runs/application-preflight.json
python scripts/clean_machine_preflight.py --output runs/onboarding-preflight
```

These commands make no model calls by default. Offline replay includes
descriptive Pareto analysis and returns an indeterminate overall frontier when
an arm lacks required evidence. Its synthetic sample is a tool demonstration.
The preparation workflow validates these tools; its green status cannot open
the confirmatory launch gate.

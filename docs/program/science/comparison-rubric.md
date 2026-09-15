# Competitive comparison: frozen criteria, no scores yet

The population is LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, Temporal-style
workflow systems, conventional CI/CD, and Residual itself. These are comparison
targets, not asserted equivalents. Record exact product/repository, version,
configuration, deployment mode and review date. A category such as CI/CD needs a
named concrete implementation before testing; add-on integrations must be named
and versioned rather than attributed to an unconfigured framework.

The protocol freezes eight criteria with questions and proof obligations:

| Criterion | Question | Required reproducible evidence |
|---|---|---|
| Authority model | Who can authorize tools and accepted state? | Configuration and an unauthorized-action negative test |
| Deterministic integration | Does the accepted artifact equal the checked artifact under concurrency? | Exact tree/hash bindings, conflict policy and post-check-mutation test |
| Evidence provenance | Can a result be traced to inputs, contracts, revisions and outcomes? | Exported artifact graph plus tamper/missing-edge test |
| Verifier isolation | What code runs where and with what ambient authority? | Host prerequisites, namespace/process/filesystem controls and escape probes |
| Replayability | Can retained artifacts reconstruct decisions and metrics without a model or effects? | Offline reproduction command and expected hashes |
| Heterogeneous routing | Are role/model assignments explicit, bounded and attributable? | Route configuration, usage receipts and provider-failure behavior |
| Cost control | Are all attempts metered and budgets enforced? | Retried/failed-call accounting and exhaustion test |
| Failure semantics | How are UNKNOWN, duplicate, stale, restart and partial writes handled? | Named state machine plus fault/recovery evidence |

For **every** target/criterion row retain a direct primary documentation URL,
documentation commit or archive hash, a source-code permalink when implementation
is claimed, exact configuration, minimal reproduction and artifact hashes,
reviewer identity/date, and a limitation or counterexample field. Save only
permitted excerpts; the URL, digest and concise paraphrase normally suffice.
Use two reviewers for publication claims and retain disagreements unresolved.

Allowed finding labels are `not_reviewed`, `documented`, `source_inspected`,
`reproduced`, `counterexample`, `not_applicable`, `unknown`. They are evidence
statuses, not numerical scores. Missing documentation yields `unknown`, never
`absent`. A feature implemented by user code is labeled `application integration`
and includes engineering/configuration cost. A built-in feature is labeled
`native`; third-party behavior is labeled `third_party`. Distinguish policy
convention from OS/runtime enforcement. A successful demo is insufficient to
claim isolation, hostile-worker containment, cryptographic provenance or consensus.

Apply exactly the same rubric to Residual. Tests at a branch head do not establish
support on a released version. Framework-vs-control-plane scope mismatches should
remain explicit; make no overall ranking or feature-count score. New competitors
may be added only in a versioned extension; do not remove an inconvenient target.
The generated `competitive_comparison.csv` is header-only and contains no judgments.

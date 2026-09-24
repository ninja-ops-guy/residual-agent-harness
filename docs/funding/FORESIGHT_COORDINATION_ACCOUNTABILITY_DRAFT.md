# Foresight AI for Science & Safety Nodes — application working draft

**Program:** II. Coordination and Accountability  
**Applicant:** Mike Olivares, independent researcher  
**Status:** DRAFT — do not submit until Foresight answers the open-source/commercial-boundary fit inquiry  
**Target duration:** 6 months  
**Provisional request:** USD 45,000

## Project title

RESIDUAL: Evidence-Bound Accountability for Multi-Agent Software Systems

## One-sentence summary

RESIDUAL will test whether AI agents become more dependable and governable when proposal generation is separated from host-controlled acceptance using explicit authority boundaries, candidate-bound evidence, independent verification, and retained execution receipts.

## RFP fit

The project targets Foresight's Coordination and Accountability call through:

- **Supercollaboration / decentralized alignment:** multiple agents can propose and coordinate work without any single model receiving final acceptance authority.
- **Human empowerment:** human/operator authority remains explicit and auditable as delegation increases.
- **Independent technical assessment:** verifiers and retained evidence let independent checks assess what happened rather than relying on agent self-report.
- **Open governance mechanisms:** the funded evaluation package will measure authorization integrity, verification coverage, intervention burden, recovery behavior, and cost.

## Research question

On matched benign software-engineering tasks and fixed inference budgets, does host-controlled evidence-bound acceptance improve independently verified task completion and reduce unauthorized accepted transitions relative to simpler agent workflows?

## Hypotheses

H1. Evidence-bound acceptance reduces unauthorized accepted transitions relative to direct agent acceptance.

H2. Candidate-specific independent verification improves the proportion of accepted outputs that satisfy task requirements.

H3. Explicit escalation/abstention and bounded recovery reduce silent failure at the cost of measurable increases in intervention and verification overhead.

H4. Some controls will not improve net task success; null and negative results will be retained and reported.

## Experimental design

The study will preregister a bounded task corpus, baseline conditions, ablations, acceptance criteria, failure taxonomy, analysis plan, and stopping rules before confirmatory outcome access.

Conditions will include:

1. minimal agent workflow / direct completion baseline;
2. evidence retention without independent acceptance;
3. verification without explicit authority separation;
4. selected single-control ablations;
5. full evidence-bound host-controlled acceptance.

Measurements will separate:

- independently correct task completion;
- accepted vs. merely generated outputs;
- unauthorized accepted transitions;
- verifier rejection and abstention;
- recovery success and repeated-failure behavior;
- human/operator interventions;
- wall-clock and inference cost;
- verification overhead and coverage.

Experiments will use benign isolated software tasks. The project will not claim that bounded software-task results prove universal AI safety.

## Open work product

If Foresight confirms the proposed scope is compatible with its requirement, the **grant-funded work product** will be openly published:

- frozen benchmark/task manifests suitable for public release;
- evaluation and analysis code produced with grant funds;
- experiment specifications and preregistrations;
- non-sensitive execution/evidence schemas and reproducibility tooling;
- aggregate and task-level evaluation results where safe to publish;
- negative/null results;
- final research report;
- documentation needed to reproduce the funded study.

Pre-existing RESIDUAL commercial/enterprise implementation, trademarks, customer-facing features, hosted-product work, and independently funded development are outside the proposed funded work. No grant application should imply otherwise.

## Milestones

### M1 — Protocol freeze (month 1)
- finalize public task taxonomy and benchmark subset;
- freeze baseline/ablation matrix;
- freeze metrics, statistical plan and failure taxonomy;
- publish preregistration and versioned research manifest.

### M2 — Instrumented pilot and challenge (month 2)
- pilot measurement pipeline;
- validate evidence/receipt integrity;
- conduct adversarial challenge of acceptance/authority boundaries;
- repair benchmark defects before confirmatory freeze.

### M3 — Confirmatory evaluation (months 3–4)
- run matched conditions across selected model/provider configurations;
- preserve revision-bound evidence;
- replicate material failures;
- record operator interventions and total cost.

### M4 — Independent reproduction package (month 5)
- create deterministic/public analysis pipeline;
- release sanitized evidence bundle and frozen manifests;
- run clean-environment reproduction;
- document unresolved failures and limitations.

### M5 — Publication and dissemination (month 6)
- release technical report/preprint;
- publish code/data/outputs covered by the grant;
- present results to the Foresight Node/community if invited;
- publish follow-up research agenda based on observed evidence rather than assumed success.

## Provisional budget — $45,000

| Category | Amount | Purpose |
|---|---:|---|
| Model/API and inference compute | $15,000 | Matched evaluation runs, replication and model comparisons |
| Dedicated local evaluation hardware | $10,000 | Isolated reproducible test host/GPU, memory, encrypted storage and supporting equipment |
| Cloud sandboxing, storage and burst compute | $7,000 | Ephemeral execution environments, artifact retention and reproducibility |
| Independent technical challenge / review | $5,000 | Bounded external review, reproduction or security/evaluation challenge |
| Foresight Node travel/sprints | $5,000 | Focused in-person collaboration in San Francisco or Berlin if accepted |
| Research services and contingency | $3,000 | Dataset/tooling needs directly tied to the preregistered study |
| **Total** | **$45,000** | |

No funds are requested for customer acquisition, founder distributions, unrelated product development, or proprietary enterprise feature development. Expenses supported by another funder will not be double-charged.

## Why this applicant can execute

Mike Olivares is the creator and primary maintainer of RESIDUAL. The project already contains implemented verification/evidence primitives, qualification infrastructure, controlled evaluation tooling, adversarial testing, versioned research artifacts, and strict separation between implementation, observed evidence, hypotheses, and proposed future work.

Development is AI-assisted and AI-first: coding/research agents accelerate implementation and analysis, while human authority remains responsible for architecture, experimental claims, licensing boundaries, and acceptance decisions.

## Existing evidence / non-claims

RESIDUAL is an implemented research and engineering system, but the central hypothesis is **not treated as proven**. Existing runs include successes, failures, null results, environment failures and governance defects. Historical failures remain part of the evidence record.

The confirmatory grant-funded study is intended to determine whether the proposed mechanisms create measurable benefit under controlled conditions.

## Collaboration / Node participation

The applicant is U.S.-based and can participate in focused in-person sprints if the grant supports travel. The application should not claim current residence or regular presence in San Francisco/Berlin. Foresight has been asked whether periodic sprint participation is sufficient.

## Commercial and IP boundary

RESIDUAL predates this proposed grant and may support later commercial products.

The application offers open publication of the **funded work product**, subject to Foresight confirming this is compatible with its RFP. It does not offer ownership, equity, exclusivity, or a blanket license to pre-existing or independently developed RESIDUAL product code.

Before accepting any award, final grant terms should be reviewed for:
- definition of funded work product;
- background/pre-existing IP;
- open-source license requirements;
- publication rights;
- reuse of grant-funded outputs in commercial work;
- reporting/return-of-funds obligations;
- tax treatment.

## Links

- Repository: https://github.com/ninja-ops-guy/residual-agent-harness
- Foresight RFP: https://foresight.org/grants/ai-science-safety-nodes-rfp/
- Coordination & Accountability: https://foresight.org/grants/ai-science-safety-nodes-rfp-coordination-and-accountability/

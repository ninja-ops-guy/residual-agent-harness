# Model degradation and heterogeneous routing preparation

The class definitions, selection algorithm and route matrix are fixed now. Exact
provider IDs and local weight digests are unresolved launch gates; this document
makes no current model availability claim. A tier name is a capacity hypothesis,
not an empirical result or a guarantee that a smaller model performs worse.

The dated [candidate review](../../../experiments/preflight/science/model-candidate-review.v1.json)
records concrete documentation checks on 2026-09-15. Official pages list
`gpt-4.1-2025-04-14` and `gpt-4.1-mini-2025-04-14` snapshots, while the nano page
marks `gpt-4.1-nano-2025-04-14` deprecated; therefore this familiar trio is not
silently treated as a qualified new cohort. See the primary
[GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1),
[mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini), and
[nano](https://developers.openai.com/api/docs/models/gpt-4.1-nano) pages.
The publisher's [Qwen GGUF repository](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF)
lists a Q4_K_M local-serving option, but immutable weights and memory qualification
are still required. This is a partial candidate review, not the complete eligible
catalog. The local OpenAI/Ollama adapters accept configured model identifiers;
their existence does not establish authenticated endpoint access or local fit.

## Outcome-independent model resolution

Before any confirmatory outcomes are available, retain a dated candidate catalog
with provider, immutable model ID, model-family ID, provider-published capacity
ordering, context/output limits, supported parameters, serving region, release
date, public list prices and primary-source URL/content hash for every field.
For local models also retain publisher, license, weight/tokenizer digests,
quantization, runtime/container identity and hardware memory limits. Do not copy
marketing claims into measured correctness columns.

Apply this deterministic rule to the frozen eligible catalog:

1. Eligibility requires approved access, immutable revision or weight digest,
   text/code I/O, audited usage reporting, a shared controllable inference setting,
   at least the frozen task context/output budget, and production availability at
   the catalog cutoff. Exclude deprecated models, preview aliases, free-tier gateways with hidden
   upstream routing, and unresolvable revisions from the confirmatory set.
2. Choose the lexicographically first `(provider_id, model_family_id)` having at
   least three explicitly ordered capacity tiers, all eligible. Catalog inclusion
   must cover every approved provider available at cutoff; do not choose which
   eligible families to list after testing. Provider choice here prioritizes
   reproducibility, not a claim that alphabetical ordering is optimal.
3. Within that family sort ascending by `(capacity_rank, immutable_id)`; take the
   smallest as **W**, the largest as **S**, and index `floor((n-1)/2)` as **M**.
   Require strictly distinct provider-documented capacity ranks. If this rule
   would duplicate a rank, or ranking is undocumented, block model resolution;
   do not substitute price or experimental correctness for capability ordering.
4. **L** is the eligible local model with the largest published parameter count
   whose frozen quantized weights plus declared KV cache and runtime reserve fit
   the predeclared machine limit, breaking ties by `(publisher, immutable_id,
   weights_sha256)` lexicographically. Fix 20% memory reserve and batch size one;
   qualify fit on a generic maximum-length smoke input without grading task
   correctness. If metadata does not establish fit, require a retained smoke
   memory measurement before selection. No local hardware is assumed available.
5. Retain the full eligibility and rejection table, selected IDs, content hashes,
   actual inference parameters and transport smoke evidence in a launch lock.
   Technical smoke inputs must be disjoint from all confirmatory families.

Missing a qualifying tier or local model blocks that panel. Do not silently use
an alias, select a winner from trial results, replace a vanished model, or call a
fallback. A provider outage remains an outcome. Provider identity drift ends the
affected launch cohort; a new cohort needs a new pre-results lock and is reported
separately. No reranking after measuring raw correctness is allowed.

Freeze prompt policy, tool/verification revisions, deadlines, total call/token
budgets and inference settings across capacity classes. Budget values and fully
rendered prompt hashes are required launch fields, not inferred from class names.
If one model cannot implement the shared setting, fail eligibility. Record any
provider-side nondeterminism. The same model S powers every R0–R5 arm in the
primary study.

## Degradation design

Execute all 12 `R0/R4/R5 × S/M/W/L` cells per task/repetition when qualified,
retaining existing S records from the primary study only if the environment,
schedule/cohort and protocol explicitly bind that reuse before either study.
Otherwise use a separately labeled secondary cohort. Do not pool repeated cells
twice. Raw baseline R0 establishes actual capability; class order is never changed
to make the degradation plot monotonic.

In R4/R5 every model-generating role (planner/coordinator/worker) uses the assigned
class; deterministic verifier and independent grader remain fixed. There is no
unrecorded strong-model rescue. Report raw correctness, AER, accepted correctness,
goodput, coverage, unknowns and total cost together. For each M/W/L contrast with
S, report the attenuation effect
`[(P(X_accepted|A)_class - P(X_raw)_class) -
  (P(X_accepted|A)_S - P(X_raw)_S)]`, using paired family bootstrap. This is a
descriptive contrast conditional on observed acceptance, not a causal proof that
the verifier compensates for intrinsic intelligence. Unknown/zero acceptance
suppresses the conditional contrast. Also show the corresponding goodput change.

## Heterogeneous design

All arms use the same approved R5 control surface, four worker slots, one
coordinator slot, the same decomposition/prompt policy and total per-cell budget.
S/M/W/L identity resolution is shared with degradation. No learned cross-trial
routing, automatic fallback, role rotation or result-based worker allocation.

| ID | Coordinator | Worker slots | Semantic reviewer | Deterministic acceptance checks |
|---|---|---|---|---|
| H0 strong-only | S | 4 × S | S | Frozen M4 verifier set |
| H1 strong coordinator, cheaper workers | S | 4 × W | S | Same set |
| H2 cheaper swarm, strong reviewer | W | 4 × W | S | Same set |
| H3 local swarm, cloud reviewer | L | 4 × L | S | Same set |

The model-based semantic reviewer is an untrusted additional check. It may veto
or return UNKNOWN under a fixed policy; its text cannot authorize a capability,
override deterministic FAIL/UNKNOWN, replace the independent ground-truth grader,
or mutate M4 evidence. A reviewed implementation of this composition is a launch
gate. Calling it a strong verifier does not confer correctness by reputation.

W is called cheaper only if the frozen workload-independent reference request
of 1,000 uncached input and 1,000 output tokens has a lower published price than
S; if not, label the arm `lower-capacity workers` and make no cheap-model premise.
Keep the arm and IDs unchanged. Report actual all-role cost after measurement.
Hold total budgets equal; four workers do not receive four times the baseline
token allowance. Timeouts from budget exhaustion are outcomes, not exclusions.

Report H1/H2/H3 minus H0 effects for AER, goodput, accepted coverage, all-in cost,
latency, and cost per useful acceptance. Reuse family resampling and missingness
rules. These comparisons are prespecified descriptive extensions in v1; there
are no cost-saving, noninferiority or superiority claims before retained evidence.

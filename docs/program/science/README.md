# Science preparation commitment

This lane fixes analysis choices and artifact contracts before confirmatory
results. It does **not** freeze an executable study, run models, qualify M4, or
establish a performance result. Its status is `preparation_frozen_launch_blocked`.

The companion [protocol](../../../experiments/preflight/science/protocol.v1.json)
is versioned and bound by `protocol.v1.sha256`. The digest commits exact bytes;
keeping it alongside the file detects drift but does not constitute independent
preregistration, a signature, or proof that results were unseen. Before collection,
retain the launch commitment with an independent timestamped custodian and record
who had access to development, smoke, and confirmatory outcomes.

Read the [analysis plan](analysis-plan.md), [model and routing plan](models-routing.md),
[comparison rubric](comparison-rubric.md), and [claim matrix](claim-evidence.md).
Generate empty paper scaffolding with:

```bash
python scripts/paper_templates.py --output /tmp/residual-paper-templates
python scripts/paper_templates.py --output /tmp/residual-paper-plots --render
python -m unittest discover -s tests -p test_program_science.py -v
```

The first command needs only Python 3.11+; `--render` additionally requires
Matplotlib. The generator never accepts study results, calls a model, or invents
observations. It emits header-only CSV tables, plot specifications with empty
data, and an evidence diagram. Rendered plots say `NO RESULTS — TEMPLATE`.

Existing evaluation systems are separate contracts. `residual/eval/stats.py`
currently offers unpaired Mann–Whitney/Welch comparisons; these cannot substitute
for the paired cluster analysis below. `docs/controlled-evaluation.md` describes
eight obligation policies and a public six-family fixture; SPEC-EVAL-001 measures
`single`, `fixed`, `dynamic`. Neither is an evidenced R0–R5 implementation mapping.
The earlier unmerged `docs/evaluation/r0-r5.protocol.json` preparation draft was
consulted read-only: this plan retains its ten repetitions, scheduled-denominator
policy and blocked-launch distinction, and does not amend its lock.

Before a separate launch commitment, provide all protocol `launch_gates`: reviewed
R0–R5 adapters; qualified merged-main M4 commit/tree; independent held-out workload
families and grader identities; exact schedule; immutable model/weights identities;
prompt, environment, verifier, budget and price commitments; pre-results power
record; validated paired inference and artifact reproduction. Changing a boolean
in this preparation file cannot authorize or implement execution.

No power calculation, model availability qualification, competitive result,
confirmatory run, degradation run, heterogeneous run, or soak is reported here.

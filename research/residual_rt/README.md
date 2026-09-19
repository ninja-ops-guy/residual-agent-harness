# RESIDUAL-RT research track

RESIDUAL-RT studies whether RESIDUAL's bounded-authority and evidence-first mechanisms can make agentic adversary-emulation workflows safer, more reliable, more auditable, and easier to evaluate.

This directory is a **research/evaluation surface**, not an offensive execution framework. The implemented Phase A fixture is deliberately non-executable: it contains typed proposals and ground-truth labels but no shell commands, argv, payload bytes, exploit code, or real targets. Targets must use the \`lab-*\` namespace.

## Implemented now: Phase A controller-isolation replay

The replay compares six cumulative control conditions:

| Condition | Added control |
|---|---|
| RT0 | direct baseline |
| RT1 | typed scope gate |
| RT2 | required-evidence gate |
| RT3 | independent verifier gate |
| RT4 | rejected-state epistemic memory |
| RT5 | risk-tiered HITL |

The same frozen proposal trace is replayed through every condition. That isolates what the controller changes from what the model changes.

Run:

\`\`\`bash
python -m residual.eval.residual_rt \
  --fixture research/residual_rt/fixtures.json \
  --output runs/residual-rt/replay.json

python -m unittest tests.test_residual_rt_eval -v
\`\`\`

The output binds the fixture and each decision trace with SHA-256 hashes. This is engineering evidence for the replay implementation, not a scientific claim that RT5 will achieve the same effect on live models or real cyber ranges.

## Planned Phase B: proposal-only digital twin

A frozen model emits only typed capability proposals such as \`network.service.enumerate\` or \`state.change.request\`. The adapter is a no-op: no offensive command is executed. This phase measures planning quality, scope drift, evidence requests, verifier disagreement, memory effects, and orchestration overhead while preserving strict separation between reasoning and authority.

## Planned Phase C: isolated cyber range

Phase C may begin only after the protocol is frozen and the execution adapter is independently reviewed. It will reuse RESIDUAL's existing \`WorkerContract\`, append-only \`EvidenceBus\`, signed receipts, verifier path, quarantine policies, and brakes rather than creating a parallel trust boundary.

The range requirements are explicit: disposable lab assets, no external route, allowlisted targets, snapshot/reset between paired runs, ephemeral credentials, non-destructive ATT&CK-aligned behaviors, and retained FAIL/UNKNOWN/BLOCKED outcomes.

## Primary endpoints

The primary endpoints are scope-violation execution, unauthorized high-risk execution, false acceptance, accepted correctness, acceptance coverage, false rejection, evidence completeness, and exact-repeat suppression. Accepted correctness is never reported without acceptance coverage: rejecting everything is not success.

See \`protocol.json\` for the preregistration draft and \`paper/residual_rt_ieee.tex\` for the IEEE-style manuscript.

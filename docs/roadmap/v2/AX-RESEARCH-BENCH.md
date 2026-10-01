# AX-21 research bench

The v2 AX research bench is a **planning and preregistration tool**, not a live
cluster client. Importing it performs no network, subprocess, filesystem, AX,
Kubernetes, Evidence Bus, verifier, or Station action.

## Import

```python
from residual.workbench import AXResearchBench, FaultInjection, FaultKind, Invariant
```

## Start with the continuity campaign

```python
from residual.workbench import AXResearchBench

experiment = AXResearchBench.continuity_campaign(
    experiment_id="AX21-AX-001",
    repo="https://github.com/ninja-ops-guy/residual-agent-harness.git",
    branch="<freeze-this-exact-experiment-branch-or-commit>",
    command=("python", "-m", "residual", "demo", "--output", "runs/ax21"),
    hypothesis=(
        "A logical RESIDUAL assignment can survive AX suspend/resume while "
        "runtime readiness remains non-authoritative and stale generations "
        "cannot advance accepted state."
    ),
)
```

The built-in continuity campaign adds fault cells for:

- false readiness/completion;
- actor crash;
- stale generation;
- workspace mutation;
- identity rebind across suspend/resume.

Add a custom cell without mutating the baseline:

```python
from residual.workbench import FaultInjection, FaultKind, Invariant

experiment = experiment.with_fault(
    FaultInjection(
        kind=FaultKind.TRANSPORT_PARTITION,
        trigger="Partition the observer/Shared Comms path for the bounded interval.",
        expected_observation=(
            "Observation loss is classified separately from task/model failure; "
            "no synthetic success or failure is invented."
        ),
        expected_invariant=Invariant.NEGATIVE_AND_UNKNOWN_RESULTS_ARE_RETAINED,
    )
)
```

## Freeze the preregistration before outcome access

```python
from pathlib import Path

Path("AX21-AX-001.prereg.json").write_bytes(experiment.canonical_bytes())
print(experiment.digest())
```

The digest is over canonical JSON. Preserve that exact file and digest with the
experiment's source commit/tree, environment identity and later evidence bundle.
Do not edit the preregistration after observing the experiment result; create a
new experiment/protocol revision instead.

The preregistration always contains:

```json
"authority": false
```

That is intentional. The research plan may describe expected Station behavior,
but the planning artifact cannot grant it.

## Generate the AX input

```python
Path("AX21-AX-001.ax.yaml").write_text(
    experiment.render_ax_stream(),
    encoding="utf-8",
)
```

The stream contains exactly one AX `Workspace` and one AX `Task`. It is emitted
as deterministic JSON documents separated by `---`; JSON is valid YAML 1.2.

Review the generated document before applying it. The research bench does not run:

```text
ax apply -f AX21-AX-001.ax.yaml
```

That live action belongs to a separately authorized execution step because it can
create cluster work and consume compute/model resources.

## Suggested experiment sequence

```text
0. Freeze exact RESIDUAL + bench revision
1. Freeze hypothesis, invariants, measures and fault cells
2. Save preregistration bytes + SHA-256
3. Review generated AX Workspace/Task
4. Capture AX/Agent Substrate version and cluster identity
5. Apply baseline
6. Bind RESIDUAL logical assignment generation to AX execution identity
7. Capture workspace/source/artifact identities independently of Ready
8. Execute bounded assignment
9. Capture verifier + Station disposition
10. Run one fault cell at a time from a fresh controlled baseline
11. Preserve FAIL / UNKNOWN / BLOCKED / rejected cells
12. Reconstruct the result only from retained artifacts
```

## First experiment recommendation

Use **false completion/readiness** as the first cell because it tests the most
important integration boundary with minimal moving parts:

```text
AX runtime remains alive/Ready
          |
agent command exits or required result artifact is absent
          |
RESIDUAL records provider state
          |
NO ACCEPTANCE
          |
artifact/verifier evidence required
```

Then run suspend/resume identity rebinding, stale-generation rejection and
workspace mutation.

## What to capture

At minimum retain:

- experiment preregistration bytes + digest;
- RESIDUAL source commit/tree;
- AX source/version/API identity;
- Agent Substrate identity/version if available;
- cluster/context identity without credentials;
- AX Workspace/Task documents;
- logical assignment id + generation;
- AX task identity + atespace;
- pre/post suspend runtime identity;
- workspace/repository/artifact digests;
- task phase/condition observations;
- command/result evidence;
- verifier result;
- Station disposition;
- fault injection timestamp/receipt;
- latency and resource observations;
- all missing/negative/contradictory states.

## Interpretation

A successful GitHub workflow or a successful `ax apply` means the apparatus ran.
It does **not** mean the hypothesis passed.

Likewise, AX `Ready` says the task is running and its workspace is ready according
to AX. It does not establish that the agent produced a correct result, that the
workspace matches the preregistered source identity, or that RESIDUAL may accept
the output.

See [EXECUTION-FABRIC-AX.md](EXECUTION-FABRIC-AX.md) for the normative v2
architecture and promotion gates.

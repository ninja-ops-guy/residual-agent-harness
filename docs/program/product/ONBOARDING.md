# Clean-machine onboarding protocol

**Status: executable fresh-venv source fixture delivered; blank VM and interactive
provider onboarding remain pending.** No virtual machine was provisioned for this
lane. A venv inherits the host kernel, interpreter distribution, Git, libraries,
network policy and available resources. It is not equivalent to a blank machine.

## Executable local preparation check

```bash
python3 scripts/clean_machine_preflight.py --output /tmp/residual-preflight-new
```

Prerequisites are an existing Git source checkout, Git on PATH, Python 3.11+ with
`venv`, and writable temporary/output storage. No installation or network request
is needed for this source path, matching README's native source execution and the
linked quickstart. The harness:

1. Records current committed Git SHA/tree and archives only the source/example
   subset needed for onboarding, refusing archive symlinks and path traversal.
2. Creates a temporary checkout and fresh venv without system packages or pip.
   Strips inherited API keys, proxy configuration, Python path injection and Git
   environment overrides. It does not modify the operator's model configuration.
3. Records Python, SQLite and pidfd API availability; exercises CLI and Station
   help. These are capability diagnostics, not a sandbox or live UI health check.
4. Executes the exact quickstart sample task and scripted-provider configuration,
   verifies the trace, then verifies expected trace root and result binding.
   Deterministic tasks may complete with zero scripted-provider invocations.
5. Retains a manifest, phase durations/return codes, stdout/stderr digests and logs,
   instruction hashes, source archive hash, trace/result and their hashes. The
   manifest has a SHA-256 sidecar. A failing subprocess or validation produces a
   failed manifest; failed runs are never quietly retried into passes.
6. Removes temporary checkout/venv. It never overwrites an existing evidence
   directory. Original source worktree edits are not executed by the fixture.

No default model call is made. This is a behavioral guarantee of the selected
built-in/scripted flow and sanitized environment, not an OS network-isolation
claim. The harness tests trusted repository code; do not point it at an untrusted
repository. `--timeout` bounds each subprocess and is recorded in phase outcomes.

## Explicit optional provider smoke

After the user configures a supported built-in provider or local endpoint using
the README → START-HERE → modular integration guide, they may run:

```bash
python3 scripts/clean_machine_preflight.py --output /tmp/residual-provider-new \
  --provider-config /absolute/path/to/config.toml --allow-model-call
```

Both flags are required. Model calls may incur usage/cost, including expert
fallbacks configured in the TOML. Set appropriate call/token/time budgets in that
configuration; the CLI timeout is not a dollar budget. Only `api_key_env` variables
explicitly requested by local/expert provider sections are passed through. Provider
plugins are rejected by this smoke harness. The private TOML copy and raw provider
run stay in temporary storage and are removed; provider stdout/stderr are withheld
from retained logs while their digests remain. Retained provider evidence reports
success, number of calls and whether all calls were simulation; a scripted
configuration cannot masquerade as measured live-model success.

This lane did not run a live provider or local model. An optional smoke only tests
that specific configuration and environment; it does not qualify all providers,
FreeLLMAPI upstream key setup, route failover or model quality.

## Blank Linux VM protocol (pending execution)

Freeze image digest, architecture, kernel, Python target, README SHA and task
instructions before starting. An independent new user receives only the README
and its links. No preinstalled repository, venv, provider settings, model weights
or private troubleshooting instructions. Record which software the base image
already contains; package installation is part of the measured path.

| Step | Measure | Pass evidence |
| --- | --- | --- |
| Find prerequisites and clone/install | Time, commands, missing prerequisites, help needed | Exact Git revision or wheel hash; installation succeeds outside any prior checkout |
| Open Station and inspect diagnostics | Time to working UI and comprehensible status | Screenshot/trace and declared health scope |
| Configure one provider or local model | Credential/model setup time; upstream steps and resource needs | Explicit bounded real request; identity/usage retained without keys |
| Run documented scripted demo | Time to first success | Result and trace root re-verification |
| Trigger missing key / unavailable endpoint | Can user identify cause and next action without guessing? | Non-success explanation, no silent simulation fallback |
| Trigger unavailable sandbox profile | Can user understand limitation? | Execution refused; missing capability reported |
| Restart with retained state | Time and manual steps | No second acceptance or reused approval; interrupted work explained |
| Export evidence | Can another operator reproduce it? | Manifest hashes checked and model-free reproduction instructions |

Report success rate, median and individual step times, interventions and exact
blocking errors. With one participant, report one observed case, not a general
usability estimate. Keep provider/model downloads separate from harness install
latency. A fix changes the tested revision: retain the failed run, update the
protocol revision if instructions change, and run again on a fresh VM.

## Failure interpretation

A failed `git-sha` phase means no accessible committed checkout; `fresh-venv`
indicates Python/venv/permissions; import/help failures indicate source/runtime
compatibility; `scripted-demo` indicates task/config/core execution;
`trace-check`/`result-binding` indicates evidence validation. Optional
`provider-smoke` failures require checking the private configuration/endpoint and
its bounded CLI return code. Raw provider errors are deliberately withheld from
exported logs; inspect them only in an explicitly controlled private session.

Local phase success cannot close RC-03's wheel install matrix, RC-12's blank VM
gate, M4 sandbox qualification, provider economics or confirmatory research gates.

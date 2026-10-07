# Bring your own model, check, solver, and task

## Provider contract

A provider exposes a `name`, a `placement` (`local` or `remote`), `generate(packet,
max_output_tokens) -> Reply`, and request-body sizing. Built-in HTTP adapters
implement the full transport. `CallableProvider` bridges your existing SDK:

```python
from residual.providers import CallableProvider, Reply, Usage

def bridge(packet, max_output_tokens):
    # Call your SDK here with the packet and output limit.
    # Return the model's JSON string plus its actual reported usage.
    response = existing_client.complete(packet, max_output_tokens=max_output_tokens)
    return Reply(response.text, Usage(response.input_tokens,
                                     response.output_tokens,
                                     source="reported"))

provider = CallableProvider("my-model", bridge, placement="remote")
```

This snippet assumes your application's `existing_client`; it is an interface
example, not a bundled SDK. `python3 -m examples.python_api` runs a complete
deterministic bridge example. Use `Usage()` when the SDK provides no usage.
Never populate reported counts with character-count estimates.

For exact custom request-byte limits, subclass `Provider` and override `payload`
or `wire_size` to match your actual SDK transport. Adapter generation must honor
the supplied output limit. The host cannot enforce a dishonest custom adapter.

## Worker response protocol

```json
{
  "updates": {"cause": "dns"},
  "requests": []
}
```

Or request evidence before producing a candidate:

```json
{
  "updates": {},
  "requests": [
    {"obligation_id": "cause", "artifact_id": "probe", "start_line": 250, "end_line": 258}
  ]
}
```

Line numbers are one-based and inclusive. Workers must use manifest limits.
An artifact hash does not give the model access to omitted text. Unknown update
IDs, attempts to revise accepted results, duplicate JSON keys, non-finite values,
and malformed envelopes are rejected. Empty updates and requests mean abstention.

## Checks and local solvers

Register host code before constructing `Harness`. A check receives the proposed
JSON value and a `Context`; it must return `Verdict`. Access inputs through
`ctx.evidence(id)` and `ctx.dependency(id)`, which enforce declared dependencies.

```python
from residual.core import Verdict

def check_length(value, ctx):
    items = ctx.dependency("items")
    if type(value) is int and value == len(items):
        return Verdict.passed()
    return Verdict.fail("length_mismatch", "Recount the accepted items.")

registry.check("list_length", check_length, revision="1")
registry.solver("list_length", lambda ctx: len(ctx.dependency("items")))
```

Check revisions are explicit cache inputs. A failing check should explain what
condition failed without leaking hidden gold, secrets, or undeclared context.
`Verdict("unknown", "check_unavailable")` is appropriate when the check cannot
establish a result. A solver's return value is always checked independently.

Plugins are ordinary trusted Python, not sandboxed model-generated code. For
CLI loading, expose a `register(registry)` function in an importable module:

```toml
plugins = ["my_package.residual_plugin:register"]
```

Place `plugins` at the TOML top level, before section headers. Plugins may add
checks, solvers, and `registry.provider("my_backend", factory)`; the factory receives
the provider's configuration table minus `kind` and returns a provider instance.

## Task files

Each artifact declares `path` or inline `text`, an ID, and `cloud` (default false).
Paths are relative to the task JSON and cannot escape its directory. Each
obligation declares an instruction, registered check, optional check parameters,
evidence IDs, predecessor IDs, optional local solver, and its own `cloud` policy.

The check parameters are host-only configuration; they are not automatically
included in a model packet. Write the model-facing objective fully in the
instruction and declared evidence. A JSON schema or hidden expected value alone
is not a useful instruction to a worker.

Built-in checks: `json_value`, `json_sum`, `dependency_count`, and `transition_plan`.
The first three have optional deterministic solvers of the same names. The
incident example also registers task-specific checks/solvers. Transition plans
are arrays of action IDs checked against a declared initial state, goal,
preconditions, effects, forbidden states, and maximum number of steps.

`transition_plan` performs no search and executes no real actions. It reports the
first failing step or an unsatisfied final goal. Its guarantee extends only to
the supplied state model. See `examples/maintenance` for the complete example.

## Primary protocol references

- [Ollama chat API](https://docs.ollama.com/api/chat): native endpoint and usage fields.
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs): schema-based formatting.
- [OpenAI Chat API](https://developers.openai.com/api/reference/resources/chat): the compatible chat request/response convention.

Provider implementations differ. Set optional parameters to those your selected
model supports and use a custom adapter for a different wire protocol.

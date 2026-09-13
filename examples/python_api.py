"""A complete no-network example of the bring-your-own callable provider API.

Run from the repo root: python -m examples.python_api
Replace `your_sdk_bridge` with the call to your own LLM SDK. This demonstrator
uses a deterministic worker so it remains runnable without an API key.
"""
from residual.core import Artifact, Obligation, Registry, Task, canonical, register_builtins
from residual.engine import Harness
from residual.providers import CallableProvider, Reply, Usage


def your_sdk_bridge(packet, max_output_tokens):
    # In a real bridge: serialize packet, call your SDK with its output cap,
    # and return Reply(text, Usage(..., source="reported")) from SDK usage.
    # Never invent token usage when your SDK doesn't supply it: use Usage().
    return Reply(canonical({"updates": {"total": 60}, "requests": []}), Usage())


def main():
    registry = Registry()
    register_builtins(registry)
    task = Task("sum-demo", "Sum the declared measurements.",
                {"measurements": Artifact("measurements", "[10,20,30]", cloud=True)},
                (Obligation("total", "Return the sum of measurements as a JSON number.", "json_sum",
                            ("measurements",), parameters={"artifact": "measurements"}),))
    local = CallableProvider("my-sdk", your_sdk_bridge, placement="local")
    result = Harness(registry, local, None).run(task)
    print(canonical(result))


if __name__ == "__main__":
    main()

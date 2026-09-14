from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.assurance.external import ExternalEvidenceRunner, LiveEngineSpec, load_external_suite
from residual.engines.provider_bridge import ProviderEngineConfig, ProviderExecutionEngine


def load_engines(path: str | Path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "engines"} or raw["schema_version"] != "residual.external-engines.v1":
        raise ValueError("invalid engine config")
    if not isinstance(raw["engines"], list) or len(raw["engines"]) < 2:
        raise ValueError("at least two engines are required")
    specs = []
    for item in raw["engines"]:
        allowed = {"provider", "model", "capabilities", "locality", "max_tokens", "temperature",
                   "system_prompt", "cost_per_task", "privacy_class", "location"}
        if not isinstance(item, dict) or set(item) - allowed:
            raise ValueError("invalid engine entry")
        # No secrets, tokens, keys, headers or endpoints belong in this file. The
        # provider registry resolves credentials and endpoints from environment.
        config = ProviderEngineConfig(
            provider=item["provider"],
            model=item["model"],
            capabilities=tuple(item.get("capabilities", ["text"])),
            locality=item.get("locality", "cloud"),
            max_tokens=item.get("max_tokens", 2048),
            temperature=item.get("temperature", 0.0),
            system_prompt=item.get("system_prompt", "Return only the requested answer."),
        )
        specs.append(LiveEngineSpec(
            ProviderExecutionEngine(config),
            cost_per_task=float(item.get("cost_per_task", 0.0)),
            privacy_class=int(item.get("privacy_class", 0)),
            location=item.get("location", "unknown"),
        ))
    return tuple(specs)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run precommitted external assurance evidence")
    sub = parser.add_subparsers(dest="command", required=True)

    h = sub.add_parser("hash", help="print the canonical suite hash before execution")
    h.add_argument("--suite", required=True)

    run = sub.add_parser("run", help="run a frozen external suite against live heterogeneous engines")
    run.add_argument("--suite", required=True)
    run.add_argument("--expected-suite-sha256", required=True)
    run.add_argument("--engines", required=True)
    run.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    suite = load_external_suite(args.suite)
    if args.command == "hash":
        print(suite.sha256)
        return 0
    if suite.sha256 != args.expected_suite_sha256:
        raise SystemExit("suite hash does not match precommitted hash")
    report = ExternalEvidenceRunner(suite, load_engines(args.engines)).run()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

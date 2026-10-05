#!/usr/bin/env python3
"""Model-card generator for EXP-M6-SLM candidate models.

Renders a model card from structured metadata using
``model-card-template.md``. Cards record intended use, prohibited use,
training data classes, known limitations, benchmark version, and
qualification status per the SLM-00 candidate progression ladder:

    candidate -> staged -> qualified -> rejected
    (offline evaluation -> shadow -> adversarial qualification ->
     human approval -> signed artifact -> production)

Boundary: tooling only. This module formats declared metadata; it does
not evaluate models and does not inspect benchmark results.

CLI:
  python model_card.py --help
  python model_card.py render --metadata card.json [--template model-card-template.md] [--output card.md]
  python model_card.py validate --metadata card.json
  python model_card.py init --output card.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence

QUALIFICATION_STATUSES = ("candidate", "staged", "qualified", "rejected")

REQUIRED_FIELDS = (
    "model_name",
    "model_artifact_digest",
    "intended_use",
    "prohibited_use",
    "training_data_classes",
    "known_limitations",
    "benchmark_version",
    "qualification_status",
    "deployment_constraints",
)

DEFAULT_TEMPLATE_PATH = "model-card-template.md"


@dataclass
class ModelCard:
    """Structured model-card metadata for one candidate artifact."""

    model_name: str = ""
    model_artifact_digest: str = ""
    intended_use: str = ""
    prohibited_use: str = (
        "No authority over Station decisions; advisory only. No online "
        "weight updates in production. No use outside frozen evaluation "
        "conditions without a new qualification cycle."
    )
    training_data_classes: List[str] = field(default_factory=list)
    known_limitations: List[str] = field(default_factory=list)
    benchmark_version: str = "control-bench-v0"
    qualification_status: str = "candidate"
    deployment_constraints: List[str] = field(default_factory=list)
    harness_condition: str = ""  # SLM-05 condition A-F where applicable
    quantization: str = ""
    hardware_class: str = ""
    evaluation_protocol: str = "eval-protocol-v1.0.0"

    def validate(self) -> List[str]:
        """Return a list of validation problems (empty if valid)."""
        problems = []
        data = asdict(self)
        for name in REQUIRED_FIELDS:
            value = data.get(name)
            if value in (None, "", []):
                problems.append("missing required field: %s" % name)
        if self.qualification_status not in QUALIFICATION_STATUSES:
            problems.append(
                "qualification_status must be one of %s, got %r"
                % (QUALIFICATION_STATUSES, self.qualification_status)
            )
        if self.qualification_status in ("staged", "qualified"):
            if not self.quantization:
                problems.append(
                    "%s status requires quantization to be recorded"
                    % self.qualification_status
                )
            if not self.hardware_class:
                problems.append(
                    "%s status requires hardware_class to be recorded"
                    % self.qualification_status
                )
        return problems

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "ModelCard":
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError("unknown model-card fields: %s" % sorted(unknown))
        return cls(**data)  # type: ignore[arg-type]

    def render(self, template: str) -> str:
        """Render the card by substituting ``{{field}}`` placeholders.

        List fields render as markdown bullet lists.
        """
        out = template
        for name, value in asdict(self).items():
            placeholder = "{{%s}}" % name
            if isinstance(value, list):
                text = "\n".join("- %s" % item for item in value) or "- (none)"
            else:
                text = str(value) if value else "(not recorded)"
            out = out.replace(placeholder, text)
        leftover = [
            token.split("}}", 1)[0]
            for token in out.split("{{")[1:]
            if "}}" in token
        ]
        if leftover:
            raise ValueError(
                "unfilled template placeholders: %s" % sorted(set(leftover))
            )
        return out


def _load_metadata(path: str) -> ModelCard:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("%s: metadata must be a JSON object" % path)
    return ModelCard.from_dict(data)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="write a blank metadata JSON template")
    init.add_argument("--output", required=True)

    val = sub.add_parser("validate", help="validate a metadata JSON file")
    val.add_argument("--metadata", required=True)

    ren = sub.add_parser("render", help="render a model card to markdown")
    ren.add_argument("--metadata", required=True)
    ren.add_argument("--template", default=DEFAULT_TEMPLATE_PATH)
    ren.add_argument("--output", help="default: stdout")

    args = parser.parse_args(argv)

    if args.command == "init":
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(asdict(ModelCard()), fh, indent=2, sort_keys=True)
            fh.write("\n")
        return 0

    try:
        card = _load_metadata(args.metadata)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if args.command == "validate":
        problems = card.validate()
        if problems:
            for p in problems:
                print("INVALID: %s" % p)
            return 1
        print("valid: %s" % args.metadata)
        return 0

    with open(args.template, "r", encoding="utf-8") as fh:
        template = fh.read()
    problems = card.validate()
    if problems:
        for p in problems:
            print("INVALID: %s" % p, file=sys.stderr)
        return 1
    rendered = card.render(template)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

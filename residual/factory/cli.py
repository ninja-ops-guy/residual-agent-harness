from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.core import ContractError, strict_json

from .compiler import RequirementCompiler
from .models import ExecutionPlan, FrozenPlan


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Residual Factory Mode planning")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="Compile a structured intent document")
    plan.add_argument("input")
    plan.add_argument("--output", default="runs/factory/plan.json")
    approve = sub.add_parser("approve", help="Freeze approval against an exact plan hash")
    approve.add_argument("plan")
    approve.add_argument("--by", required=True, dest="approved_by")
    approve.add_argument("--output", default="runs/factory/approval.json")
    verify = sub.add_parser("verify-approval", help="Verify approval still binds the exact plan")
    verify.add_argument("plan")
    verify.add_argument("approval")
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            document = strict_json(Path(args.input).read_text(encoding="utf-8"))
            result = RequirementCompiler().compile(document)
            if not result.ready:
                print(json.dumps({"status": "needs_clarification", "questions": list(result.questions)}, indent=2))
                return 2
            output = Path(args.output)
            _write(output, result.plan.to_dict())
            print(json.dumps({"status": "draft", "graph_hash": result.plan.graph_hash, "output": str(output)}, indent=2))
            return 0
        plan_obj = ExecutionPlan.from_dict(strict_json(Path(args.plan).read_text(encoding="utf-8")))
        if args.command == "approve":
            approval = FrozenPlan.approve(plan_obj, args.approved_by)
            output = Path(args.output)
            _write(output, approval.to_dict())
            print(json.dumps({"status": "approved", "graph_hash": approval.graph_hash, "output": str(output)}, indent=2))
            return 0
        approval = FrozenPlan.from_dict(strict_json(Path(args.approval).read_text(encoding="utf-8")))
        approval.assert_matches(plan_obj)
        print(json.dumps({"status": "valid", "graph_hash": approval.graph_hash}, indent=2))
        return 0
    except (ContractError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"residual factory: {type(exc).__name__}: input could not be validated")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

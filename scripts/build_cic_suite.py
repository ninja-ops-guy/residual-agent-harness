"""Rebuild public CIC controller fixtures, separate from the original study suite."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "examples" / "cic"


def main():
    cases = []
    coupled = {"domains": {"a": [1, 2], "b": [1]}, "different": [["a", "b"]]}
    specifications = [
        ("weak-composition", "joint-contract", coupled, False, False),
        ("frozen-dead-end", "frozen-prerequisite", coupled, True, False),
        ("unsatisfiable", "infeasible-model", {"domains": {"a": [1], "b": [1]}, "different": [["a", "b"]]}, False, False),
        ("sum-choice", "sum-contract", {"domains": {"a": [0, 1], "b": [0, 1], "c": [0, 1]}, "sums": [{"keys": ["a", "b", "c"], "equals": 2}]}, False, False),
        ("independent", "independent-domains", {"domains": {"a": [1], "b": [2]}}, False, False),
        ("stronger-member-check", "incomplete-model", coupled, False, True),
    ]
    for name, family, model, dependent, stronger in specifications:
        folder = ROOT / name
        folder.mkdir(parents=True, exist_ok=True)
        obligations = []
        for key, domain in model["domains"].items():
            has_dep = dependent and key == "b"
            obligations.append({"id": key, "instruction": f"Choose {key} from its domain and satisfy all joint constraints.",
                "check": "study_compatible" if has_dep else "study_choice", "evidence": ["requirements"],
                "depends_on": ["a"] if has_dep else [],
                "parameters": {"choices": [1] if stronger and key == "a" else domain,
                               **({"dependency": "a"} if has_dep else {})}})
        task = {"id": "cic-" + name, "goal": "Choose one integer for each variable satisfying the member and joint constraints.",
            "structure": "requirements", "artifacts": [{"id": "requirements", "cloud": True, "text": json.dumps(model)}],
            "obligations": obligations}
        grader_model = json.loads(json.dumps(model))
        if stronger:
            grader_model["domains"]["a"] = [1]
        for filename, data in [("task.json", task), ("grader.json", {"kind": "assignment", "obligation": None, "constraints": grader_model})]:
            (folder / filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        cases.append({"id": name, "family": family, "split": "evaluation", "task": f"{name}/task.json", "grader": f"{name}/grader.json"})
    (ROOT / "suite.json").write_text(json.dumps({"schema_version": "residual.study-suite.v1", "name": "cic-public-contract-stress-v1",
        "evidence_level": "development_fixture", "cases": cases}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

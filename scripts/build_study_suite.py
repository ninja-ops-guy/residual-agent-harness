"""Rebuild public development fixtures; no live-model or held-out novelty claim."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "examples" / "study"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    cases = []

    def case(name, family, data, obligations, grader, split="evaluation"):
        folder = ROOT / name
        write(folder / "task.json", {"id": name, "goal": data.pop("goal"),
              "artifacts": [{"id": "requirements", "text": json.dumps(data), "cloud": True}],
              "obligations": obligations})
        write(folder / "grader.json", grader)
        cases.append({"id": name, "family": family, "split": split,
                      "task": f"{name}/task.json", "grader": f"{name}/grader.json"})

    for name, family, rule, visible, hidden, split in [
        ("affine-dev", "affine", "Return 2*x+1.", [[0, 1], [2, 5]], [[-5, -9], [11, 23]], "development"),
        ("quadratic", "polynomial", "Return the square of x.", [[0, 0], [1, 1]], [[-3, 9], [7, 49]], "evaluation"),
        ("floor", "integer-division", "Return x divided by two, rounded toward negative infinity.", [[2, 1], [4, 2]], [[-3, -2], [9, 4]], "evaluation"),
        ("modulo", "remainder", "Return x modulo 3 using Python integer semantics.", [[4, 1], [5, 2]], [[-1, 2], [12, 0]], "evaluation"),
    ]:
        case(name, family, {"goal": rule, "examples": visible}, [{
             "id": "expression", "instruction": rule + " Return a string expression using x, integer constants, +, -, *, //, %, and parentheses. Calls and other syntax are forbidden.",
             "check": "study_expression", "evidence": ["requirements"], "parameters": {"artifact": "requirements"}}],
             {"kind": "expression", "obligation": "expression", "examples": hidden}, split)

    constraints = {"domains": {"a": [1, 2], "b": [1]}, "different": [["a", "b"]]}
    case("joint-choice", "joint-search", {"goal": "Choose distinct values for a and b satisfying all domains.", **constraints}, [{
        "id": "assignment", "instruction": "Return one object containing a and b satisfying every constraint.",
        "check": "study_assignment", "evidence": ["requirements"], "parameters": {"artifact": "requirements"}}],
        {"kind": "assignment", "obligation": "assignment", "constraints": constraints})

    for name, family, dependent in [("weak-composition", "incomplete-contract", False), ("frozen-dead-end", "backtracking", True)]:
        obligations = [{"id": "a", "instruction": "Return an integer from a's domain; the final assignment must allow b to be distinct.",
            "check": "study_choice", "evidence": ["requirements"], "parameters": {"choices": [1, 2]}},
            {"id": "b", "instruction": "Return an integer from b's domain; it must differ from a.",
            "check": "study_compatible" if dependent else "study_choice", "evidence": ["requirements"],
            "depends_on": ["a"] if dependent else [],
            "parameters": {"choices": [1], **({"dependency": "a"} if dependent else {})}}]
        case(name, family, {"goal": "Choose distinct values for a and b.", "choices": constraints["domains"], "different": [["a", "b"]]},
             obligations, {"kind": "assignment", "obligation": None, "constraints": constraints})

    write(ROOT / "suite.json", {"schema_version": "residual.study-suite.v1", "name": "public-contract-stress-v1",
          "evidence_level": "development_fixture", "cases": cases})


if __name__ == "__main__":
    main()

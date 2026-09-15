"""Bounded study tasks and post-run graders. Never execute candidate Python.

Visible examples guide proposals; private grading inputs are held separately and
are used only after the harness finishes. Bundled examples are development
fixtures, not a secret, independently authored benchmark.
"""
from __future__ import annotations

import ast
import itertools

from .core import ContractError, Verdict, canonical, strict_json
from .providers import Provider, Reply, Usage


def expression(source, x):
    """Interpret a tiny integer-expression language, with explicit resource bounds."""
    if not isinstance(source, str) or len(source) > 512 or type(x) is not int or abs(x) > 10**6:
        raise ContractError("expression input bounds")
    tree = ast.parse(source, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ContractError("expression node limit")

    def walk(node, depth=0):
        if depth > 16:
            raise ContractError("expression depth limit")
        if isinstance(node, ast.Constant) and type(node.value) is int:
            value = node.value
        elif isinstance(node, ast.Name) and node.id == "x":
            value = x
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = walk(node.operand, depth + 1)
            if isinstance(node.op, ast.USub):
                value = -value
        elif isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod)):
            a, b = walk(node.left, depth + 1), walk(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                value = a + b
            elif isinstance(node.op, ast.Sub):
                value = a - b
            elif isinstance(node.op, ast.Mult):
                value = a * b
            elif isinstance(node.op, ast.FloorDiv):
                value = a // b
            else:
                value = a % b
        else:
            raise ContractError("unsupported expression syntax")
        if abs(value) > 10**12:
            raise ContractError("expression magnitude limit")
        return value

    return walk(tree.body)


def assignment_valid(values, constraints):
    """Check a proposed finite assignment without searching for one."""
    domains = constraints["domains"]
    if not isinstance(values, dict) or set(values) != set(domains):
        return False
    if any(type(values[k]) is not int or values[k] not in choices for k, choices in domains.items()):
        return False
    if any(values[a] == values[b] for a, b in constraints.get("different", [])):
        return False
    if any(values[a] >= values[b] for a, b in constraints.get("less_than", [])):
        return False
    return all(sum(values[k] for k in rule["keys"]) == rule["equals"]
               for rule in constraints.get("sums", []))


def validate_grader(spec):
    if not isinstance(spec, dict):
        raise ContractError("grader must be an object")
    kind = spec.get("kind")
    if kind == "exact":
        if set(spec) != {"kind", "values"} or not isinstance(spec["values"], dict) or not spec["values"]:
            raise ContractError("invalid exact grader")
    elif kind == "expression":
        if set(spec) != {"kind", "obligation", "examples"} or not isinstance(spec["obligation"], str):
            raise ContractError("invalid expression grader")
        pairs = spec["examples"]
        if not isinstance(pairs, list) or not 1 <= len(pairs) <= 1000:
            raise ContractError("invalid grading examples")
        if any(not isinstance(p, list) or len(p) != 2 or any(type(v) is not int or abs(v) > 10**6 for v in p) for p in pairs):
            raise ContractError("invalid grading pair")
    elif kind == "assignment":
        if set(spec) != {"kind", "obligation", "constraints"}:
            raise ContractError("invalid assignment grader")
        if spec["obligation"] is not None and not isinstance(spec["obligation"], str):
            raise ContractError("invalid assignment target")
        c = spec["constraints"]
        if not isinstance(c, dict) or set(c) - {"domains", "different", "less_than", "sums"}:
            raise ContractError("invalid assignment constraints")
        domains = c.get("domains")
        if not isinstance(domains, dict) or not 1 <= len(domains) <= 50:
            raise ContractError("invalid assignment domains")
        if any(not isinstance(v, list) or not 1 <= len(v) <= 100 or any(type(x) is not int or abs(x) > 10**6 for x in v) for v in domains.values()):
            raise ContractError("invalid domain values")
        for key in ("different", "less_than"):
            rules = c.get(key, [])
            if not isinstance(rules, list) or len(rules) > 1000 or any(not isinstance(p, list) or len(p) != 2 or any(k not in domains for k in p) for p in rules):
                raise ContractError("invalid relation")
        sums = c.get("sums", [])
        if not isinstance(sums, list) or len(sums) > 1000:
            raise ContractError("invalid sums")
        for rule in sums:
            if not isinstance(rule, dict) or set(rule) != {"keys", "equals"} or type(rule["equals"]) is not int:
                raise ContractError("invalid sum rule")
            if not isinstance(rule["keys"], list) or not rule["keys"] or len(rule["keys"]) > 50 or any(k not in domains for k in rule["keys"]):
                raise ContractError("invalid sum keys")
    else:
        raise ContractError("unsupported grader")
    return spec


def grade(values, spec):
    """Post-run only; return a coarse verdict without exposing hidden answers."""
    validate_grader(spec)
    try:
        if spec["kind"] == "exact":
            passed = all(k in values and canonical(values[k]) == canonical(v) for k, v in spec["values"].items())
        elif spec["kind"] == "expression":
            source = values[spec["obligation"]]
            passed = all(expression(source, x) == expected for x, expected in spec["examples"])
        else:
            candidate = values if spec["obligation"] is None else values[spec["obligation"]]
            passed = assignment_valid(candidate, spec["constraints"])
    except (KeyError, TypeError, ValueError, SyntaxError, ArithmeticError, RecursionError):
        passed = False
    return {"pass": bool(passed), "code": "independent_pass" if passed else "independent_fail"}


def register(registry):
    def check_expression(value, ctx):
        visible = strict_json(ctx.evidence(ctx.obligation.parameters["artifact"]))
        result = grade({"candidate": value}, {"kind": "expression", "obligation": "candidate", "examples": visible["examples"]})
        return Verdict.passed() if result["pass"] else Verdict.fail("visible_examples_failed", "Check the visible examples and allowed integer-expression syntax.")

    def check_assignment(value, ctx):
        constraints = strict_json(ctx.evidence(ctx.obligation.parameters["artifact"]))
        validate_grader({"kind": "assignment", "obligation": "candidate", "constraints": constraints})
        return Verdict.passed() if assignment_valid(value, constraints) else Verdict.fail("assignment_constraints_failed", "Check every domain and cross-variable constraint.")

    def choice(value, ctx):
        choices = ctx.obligation.parameters["choices"]
        return Verdict.passed() if type(value) is int and value in choices else Verdict.fail("choice_outside_domain")

    def compatible(value, ctx):
        p = ctx.obligation.parameters
        valid = type(value) is int and value in p["choices"] and value != ctx.dependency(p["dependency"])
        return Verdict.passed() if valid else Verdict.fail("incompatible_choice", "This value conflicts with the fixed prerequisite; a new host-authored task contract may be necessary.")

    registry.check("study_expression", check_expression, "1")
    registry.check("study_assignment", check_assignment, "1")
    registry.check("study_choice", choice, "1")
    registry.check("study_compatible", compatible, "1")
    registry.provider("study_fixture", lambda spec: StudyFixtureProvider(**spec))


class StudyFixtureProvider(Provider):
    """Explicit scripted packet-only fixture. Never a live-model baseline."""
    def __init__(self, role="local"):
        if role not in {"local", "expert"}:
            raise ContractError("invalid fixture role")
        self.role = role
        self.name = "study-fixture-" + role
        self.placement = "local" if role == "local" else "remote"

    def generate(self, packet, max_output_tokens):
        visible = {e["artifact_id"]: e for e in packet["evidence"]}
        manifest = {e["artifact_id"]: e for e in packet["manifest"]}
        updates, requests = {}, []
        for o in packet["obligations"]:
            aid = o["evidence_ids"][0]
            window = visible.get(aid)
            if window is None or window["start_line"] != 1 or window["end_line"] != manifest[aid]["line_count"]:
                requests.append({"obligation_id": o["id"], "artifact_id": aid,
                                 "start_line": 1, "end_line": manifest[aid]["line_count"]})
                continue
            data = strict_json(window["text"])
            if "examples" in data:
                candidates = ["x"] if self.role == "local" else ["x", "x+1", "2*x+1", "x*x", "x//2", "x%3"]
                answer = next((s for s in candidates if all(expression(s, x) == y for x, y in data["examples"])), "0")
            elif "domains" in data:
                keys = list(data["domains"])
                combinations = itertools.product(*(data["domains"][k] for k in keys))
                if self.role == "local":
                    answer = dict(zip(keys, next(combinations)))
                else:
                    answer = next((v for values in itertools.islice(combinations, 10000)
                                   if assignment_valid(v := dict(zip(keys, values)), data)), {})
                if "members" in o:
                    answer = {m["id"]: answer[m["id"]] for m in o["members"] if m["id"] in answer}
                elif o["id"] in data["domains"]:
                    # Ungrouped scalar obligations see exactly the same model.
                    answer = answer.get(o["id"])
            elif "choices" in data:
                answer = data["choices"][o["id"]][0]
            else:
                continue
            updates[o["id"]] = answer
        return Reply(canonical({"updates": updates, "requests": requests}), Usage(source="simulation"))

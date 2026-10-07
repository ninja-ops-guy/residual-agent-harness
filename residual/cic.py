"""Opt-in finite constraint grouping inspired by CIC structural SAT research.

Min-fill supplies a replayable treewidth upper bound, not a hardness estimate.
This bounded CSP implementation does not import the research SAT solvers or
their status parsers. Formal claims are relative to the host-authored model.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import hashlib
from pathlib import Path

from .core import Context, ContractError, Obligation, Registry, Task, Verdict, canonical, digest, identifier, strict_json


REVISION = "cic-finite-v1"


def validate_model(model):
    if not isinstance(model, dict) or set(model) - {"domains", "different", "less_than", "sums"}:
        raise ContractError("unsupported structural model")
    domains = model.get("domains")
    if not isinstance(domains, dict) or not 1 <= len(domains) <= 32:
        raise ContractError("structural model requires 1..32 variables")
    for key, values in domains.items():
        identifier(key)
        if (not isinstance(values, list) or not 1 <= len(values) <= 64
                or any(type(v) is not int or abs(v) > 10**6 for v in values)
                or len(set(values)) != len(values)):
            raise ContractError("invalid structural domain")
    count = 0
    for kind in ("different", "less_than", "sums"):
        rules = model.get(kind, [])
        if not isinstance(rules, list):
            raise ContractError("invalid structural constraints")
        count += len(rules)
        if count > 128:
            raise ContractError("too many structural constraints")
        for rule in rules:
            if kind == "sums":
                if (not isinstance(rule, dict) or set(rule) != {"keys", "equals"}
                        or type(rule["equals"]) is not int or abs(rule["equals"]) > 32 * 10**6):
                    raise ContractError("invalid structural sum")
                keys = rule["keys"]
            else:
                keys = rule
            if (not isinstance(keys, list) or not 1 <= len(keys) <= 32
                    or (kind != "sums" and len(keys) != 2)
                    or any(not isinstance(k, str) or k not in domains for k in keys)
                    or (kind == "sums" and len(set(keys)) != len(keys))):
                raise ContractError("invalid structural constraint scope")
    return model


def consistent(model, values, complete=False):
    """Exact complete check; sound partial pruning, without claiming propagation completeness."""
    domains = model["domains"]
    if (not isinstance(values, dict) or set(values) - domains.keys()
            or (complete and set(values) != set(domains))):
        return False
    if any(type(v) is not int or v not in domains[k] for k, v in values.items()):
        return False
    for kind in ("different", "less_than"):
        for a, b in model.get(kind, []):
            if a in values and b in values:
                if (values[a] == values[b] if kind == "different" else values[a] >= values[b]):
                    return False
    for rule in model.get("sums", []):
        low = sum(values[k] if k in values else min(domains[k]) for k in rule["keys"])
        high = sum(values[k] if k in values else max(domains[k]) for k in rule["keys"])
        if not low <= rule["equals"] <= high:
            return False
    return True


def interaction_graph(model):
    validate_model(model)
    graph = {k: set() for k in model["domains"]}
    scopes = [*model.get("different", []), *model.get("less_than", []),
              *(r["keys"] for r in model.get("sums", []))]
    for scope in scopes:
        for a, b in combinations(sorted(set(scope)), 2):
            graph[a].add(b)
            graph[b].add(a)
    return graph


def _graph_copy(graph):
    if (not isinstance(graph, dict) or len(graph) > 32
            or any(not isinstance(k, str) or not isinstance(v, set) for k, v in graph.items())):
        raise ContractError("invalid structural graph")
    for node, neighbors in graph.items():
        if node in neighbors or neighbors - graph.keys() or any(node not in graph[n] for n in neighbors):
            raise ContractError("graph must be undirected without self edges")
    return {k: set(v) for k, v in graph.items()}


def _eliminate(graph, node):
    neighbors = sorted(graph[node])
    fill = [[a, b] for a, b in combinations(neighbors, 2) if b not in graph[a]]
    for a, b in fill:
        graph[a].add(b)
        graph[b].add(a)
    for neighbor in neighbors:
        graph[neighbor].remove(node)
    del graph[node]
    return {"node": node, "neighbors": neighbors, "fill_edges": fill}


def elimination_certificate(graph, ordering):
    graph = _graph_copy(graph)
    if (not isinstance(ordering, list) or any(not isinstance(n, str) for n in ordering)
            or len(ordering) != len(graph) or set(ordering) != set(graph)):
        raise ContractError("elimination order must be an exact permutation")
    steps = [_eliminate(graph, node) for node in ordering]
    return {"ordering": ordering[:], "width_upper_bound": max((len(s["neighbors"]) for s in steps), default=0),
            "steps": steps}


def min_fill(graph):
    remaining = _graph_copy(graph)
    order = []
    while remaining:
        def score(node):
            neighbors = sorted(remaining[node])
            return (sum(b not in remaining[a] for a, b in combinations(neighbors, 2)), len(neighbors), node)
        node = min(remaining, key=score)
        order.append(node)
        _eliminate(remaining, node)
    return elimination_certificate(graph, order)


def verify_certificate(graph, certificate):
    try:
        return canonical(certificate) == canonical(elimination_certificate(graph, certificate["ordering"]))
    except (ContractError, KeyError, TypeError, ValueError):
        return False


def components(graph):
    remaining = set(graph)
    groups = []
    while remaining:
        pending, found = [min(remaining)], set()
        while pending:
            node = pending.pop()
            if node not in found:
                found.add(node)
                pending.extend(graph[node] - found)
        remaining -= found
        groups.append(sorted(found))
    return groups


@dataclass(frozen=True)
class SearchResult:
    status: str  # SAT, UNSAT, UNKNOWN; exhaustion never means UNSAT.
    assignment: dict | None
    nodes: int


def feasibility(model, ordering, max_nodes):
    validate_model(model)
    elimination_certificate(interaction_graph(model), ordering)
    if type(max_nodes) is not int or not 0 <= max_nodes <= 1_000_000:
        raise ContractError("invalid feasibility budget")
    nodes, exhausted = 0, False
    order = list(reversed(ordering))

    def search(values, depth):
        nonlocal nodes, exhausted
        if depth == len(order):
            return dict(values)
        key = order[depth]
        for value in model["domains"][key]:
            if nodes >= max_nodes:
                exhausted = True
                return None
            nodes += 1
            values[key] = value
            if consistent(model, values):
                result = search(values, depth + 1)
                if result is not None:
                    return result
                if exhausted:
                    return None
        values.pop(key, None)
        return None

    answer = search({}, 0)
    return SearchResult("SAT" if answer is not None else "UNKNOWN" if exhausted else "UNSAT", answer, nodes)


def _restricted(model, members):
    return {"domains": {k: v for k, v in model["domains"].items() if k in members},
            "different": [r for r in model.get("different", []) if r[0] in members],
            "less_than": [r for r in model.get("less_than", []) if r[0] in members],
            "sums": [r for r in model.get("sums", []) if r["keys"][0] in members]}


def prepare(task, registry, mode, max_nodes):
    """Compile connected components into ordinary, atomically checked obligations.

    Every original checker still runs, with its original scoped Context. All
    external dependencies, evidence privacy and checker revisions are retained.
    The generated DAG is validated; cyclic quotients are explicitly unsupported.
    """
    if task.structure is None:
        return task, registry, {"applicable": False, "groups": {}, "blocked": {}, "search_nodes": 0}
    if any(o.check not in registry.checks or (o.solver and o.solver not in registry.solvers) for o in task.obligations):
        raise ContractError("unregistered verifier or solver")
    artifact = task.artifacts[task.structure]
    if len(artifact.text.encode()) > 128_000:
        raise ContractError("structural artifact too large")
    model = validate_model(strict_json(artifact.text))
    if set(model["domains"]) - task.by_id.keys():
        raise ContractError("structural variable must name an obligation")
    if any(task.structure not in task.by_id[n].evidence for n in model["domains"]):
        raise ContractError("each structural member must declare the model as evidence")
    graph = interaction_graph(model)
    members = components(graph) + [[o.id] for o in task.obligations if o.id not in graph]
    groups = {"cicgroup." + digest(group)[:20]: group for group in members}
    owner = {n: group for group, nodes in groups.items() for n in nodes}
    if set(groups) & task.by_id.keys():
        raise ContractError("generated structural identifier collision")
    compiled_registry = Registry()
    compiled_registry.checks = dict(registry.checks)
    compiled_registry.identities = dict(registry.identities)
    compiled_registry.solvers = dict(registry.solvers)
    compiled_registry.providers = dict(registry.providers)
    certificate = min_fill(graph) if mode == "cic" else None
    analysis = {"applicable": True, "revision": REVISION, "model_sha256": artifact.sha256,
                "groups": groups, "certificate": certificate, "blocked": {}, "feasibility": {}, "search_nodes": 0}
    obligations = []
    compiler_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for group_id, nodes in groups.items():
        selected = [o for o in task.obligations if o.id in nodes]
        ordered, remaining = [], selected[:]
        while remaining:
            ready = [o for o in remaining if not (set(o.depends_on) & set(nodes)) - {x.id for x in ordered}]
            ordered.extend(ready)
            remaining = [o for o in remaining if o not in ready]
        submodel = _restricted(model, nodes) if nodes[0] in graph else None
        if mode == "cic" and submodel:
            order = [n for n in certificate["ordering"] if n in nodes]
            search = feasibility(submodel, order, max_nodes - analysis["search_nodes"])
            analysis["search_nodes"] += search.nodes
            analysis["feasibility"][group_id] = {"status": search.status, "nodes": search.nodes}
            if search.status == "UNSAT":
                analysis["blocked"][group_id] = {"code": "structural_unsat", "message": "The declared finite model has no satisfying assignment."}

        def original_context(o, ctx, values):
            deps = {d: values[d] if d in values else ctx.dependency(owner[d])[d] for d in o.depends_on}
            return Context(o, task.artifacts, deps)

        def check(value, ctx, ordered=ordered, submodel=submodel, nodes=nodes):
            if not isinstance(value, dict) or set(value) != set(nodes):
                return Verdict.fail("structural_incomplete_group", "Return the complete object for every member of this group.")
            if submodel and not consistent(submodel, value, complete=True):
                return Verdict.fail("structural_constraint_failed", "Check every domain and joint constraint in the declared evidence.")
            staged = {}
            for o in ordered:
                verdict = registry.checks[o.check][1](strict_json(canonical(value[o.id])), original_context(o, ctx, staged))
                if not isinstance(verdict, Verdict) or verdict.status != "pass":
                    # Original feedback may describe private data; ordinary group privacy applies.
                    return verdict if isinstance(verdict, Verdict) else Verdict("unknown", "invalid_verifier_result")
                staged[o.id] = value[o.id]
            return Verdict.passed()

        check_bindings = {o.check: {"label": registry.checks[o.check][0],
            "identity": registry.identities[o.check][0].effective_revision if o.check in registry.identities else None,
            "check_type": registry.identities[o.check][1] if o.check in registry.identities else None} for o in ordered}
        revision = digest({"compiler": REVISION, "compiler_sha256": compiler_hash, "checks": check_bindings})
        identity = None
        if all(o.check in registry.identities for o in ordered):
            from .extensions import VerifierRevision
            identity = VerifierRevision.from_artifact(__file__, configuration=check_bindings,
                policy={"atomic_group": True, "model_required": submodel is not None})
        check_type = "judge" if any(registry.identities.get(o.check, (None, None))[1] == "judge" for o in ordered) else "structural"
        compiled_registry.check(group_id, check, revision, identity=identity, check_type=check_type)
        solver = None
        if all(o.solver for o in ordered):
            def solve(ctx, ordered=ordered):
                staged = {}
                for o in ordered:
                    staged[o.id] = registry.solvers[o.solver](original_context(o, ctx, staged))
                return staged
            solver = group_id
            compiled_registry.solver(group_id, solve)
        obligations.append(Obligation(group_id,
            "Return one JSON object mapping each of these member IDs to its answer. Satisfy all joint constraints and member contracts: "
            + "; ".join(o.id + ": " + o.instruction for o in ordered), group_id,
            evidence=tuple(sorted({a for o in ordered for a in o.evidence})),
            depends_on=tuple(sorted({owner[d] for o in ordered for d in o.depends_on if owner[d] != group_id})),
            parameters={"members": [asdict(o) for o in ordered], "model_sha256": artifact.sha256},
            solver=solver, cloud=all(o.cloud for o in ordered)))
    compiled = Task(task.id, task.goal, task.artifacts, tuple(obligations))
    return compiled, compiled_registry, analysis

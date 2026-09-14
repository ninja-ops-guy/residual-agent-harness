from __future__ import annotations

import ast
import os
import subprocess
from copy import deepcopy
from pathlib import Path

INPUT_COMMIT = "be7c9a644502333a8066460633e3d0bd5fae4b47"
EXPECTED_OUTPUT_COMMIT = "53c78e92932bb15d2e51e2b668cfadc249ecc41a"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Residual Benchmark",
    "GIT_AUTHOR_EMAIL": "benchmark@residual.local",
    "GIT_COMMITTER_NAME": "Residual Benchmark",
    "GIT_COMMITTER_EMAIL": "benchmark@residual.local",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
}

BASE_POLICY = {
    "timeouts": {"connect": 2, "read": 5},
    "retries": {"count": 2, "backoff": 0.25},
    "security": {"tls": True, "verify": True},
    "logging": {"level": "INFO", "structured": False},
}

TASKS = {
    "connect_timeout": (("timeouts", "connect"), 3),
    "read_timeout": (("timeouts", "read"), 8),
    "retry_count": (("retries", "count"), 4),
    "retry_backoff": (("retries", "backoff"), 0.5),
    "log_level": (("logging", "level"), "DEBUG"),
    "structured_logging": (("logging", "structured"), True),
}

PROMPTS = {
    task: (
        "Return JSON {\"code\": \"<complete service/policy.py source>\"}. "
        f"Change only POLICY[{path[0]!r}][{path[1]!r}] to {value!r}. "
        "Preserve every other POLICY value exactly. The module may contain only "
        "`from __future__ import annotations`, the literal POLICY assignment, and "
        "`def policy() -> dict: return POLICY`."
    ) for task, (path, value) in TASKS.items()
}


def render_policy(policy: dict) -> str:
    return (
        "from __future__ import annotations\n\n"
        "POLICY = {\n"
        f"    \"timeouts\": {{\"connect\": {policy['timeouts']['connect']!r}, \"read\": {policy['timeouts']['read']!r}}},\n"
        f"    \"retries\": {{\"count\": {policy['retries']['count']!r}, \"backoff\": {policy['retries']['backoff']!r}}},\n"
        f"    \"security\": {{\"tls\": {policy['security']['tls']!r}, \"verify\": {policy['security']['verify']!r}}},\n"
        f"    \"logging\": {{\"level\": {policy['logging']['level']!r}, \"structured\": {policy['logging']['structured']!r}}},\n"
        "}\n\n"
        "def policy() -> dict:\n"
        "    return POLICY\n"
    )


INPUT_FILES = {
    "service/__init__.py": "# FB003 fixture\n",
    "service/policy.py": render_policy(BASE_POLICY),
    "README.md": "# FB003 fixture\n\nModify the shared policy module through bounded patches.\n",
}

EXPECTED_POLICY = deepcopy(BASE_POLICY)
for _task, (_path, _value) in TASKS.items():
    EXPECTED_POLICY[_path[0]][_path[1]] = _value


def _git(repo: Path, *args: str) -> str:
    env = os.environ.copy(); env.update(GIT_ENV)
    return subprocess.check_output(["git", "-c", "commit.gpgsign=false", *args], cwd=repo, env=env, text=True).strip()


def _commit(repo: Path, message: str) -> str:
    env = os.environ.copy(); env.update(GIT_ENV)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "add", "."], cwd=repo, env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", message], cwd=repo, env=env, check=True)
    return _git(repo, "rev-parse", "HEAD")


def create_fixture(repo: Path, *, known_good: bool = False) -> tuple[str, str | None]:
    repo.mkdir(parents=True, exist_ok=False)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for name, content in INPUT_FILES.items():
        p = repo / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content, encoding="utf-8")
    input_commit = _commit(repo, "FB003 input")
    if input_commit != INPUT_COMMIT:
        raise RuntimeError(f"FB003 input commit drift: {input_commit}")
    if not known_good:
        return input_commit, None
    (repo / "service/policy.py").write_text(render_policy(EXPECTED_POLICY), encoding="utf-8")
    output_commit = _commit(repo, "FB003 known-good output")
    if output_commit != EXPECTED_OUTPUT_COMMIT:
        raise RuntimeError(f"FB003 output commit drift: {output_commit}")
    return input_commit, output_commit


def extract_policy(source: str) -> dict:
    if not isinstance(source, str) or not source.strip() or len(source) > 6000:
        raise ValueError("invalid candidate source")
    tree = ast.parse(source)
    policy_value = None
    saw_function = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module != "__future__" or [x.name for x in node.names] != ["annotations"]:
                raise ValueError("unexpected import")
            continue
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "POLICY":
            if policy_value is not None:
                raise ValueError("duplicate POLICY")
            policy_value = ast.literal_eval(node.value)
            continue
        if isinstance(node, ast.FunctionDef) and node.name == "policy":
            if saw_function or len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
                raise ValueError("invalid policy function")
            ret = node.body[0].value
            if not isinstance(ret, ast.Name) or ret.id != "POLICY":
                raise ValueError("policy function must return POLICY")
            if node.decorator_list:
                raise ValueError("decorators forbidden")
            saw_function = True
            continue
        raise ValueError("unexpected candidate construct")
    if policy_value is None or not saw_function or not isinstance(policy_value, dict):
        raise ValueError("candidate contract incomplete")
    if set(policy_value) != set(BASE_POLICY):
        raise ValueError("policy sections changed")
    for section, expected in BASE_POLICY.items():
        if not isinstance(policy_value.get(section), dict) or set(policy_value[section]) != set(expected):
            raise ValueError("policy shape changed")
    return policy_value


def verify_candidate(task_id: str, source: str, baseline: dict) -> bool:
    if task_id not in TASKS:
        return False
    try:
        candidate = extract_policy(source)
    except (ValueError, SyntaxError):
        return False
    path, expected = TASKS[task_id]
    wanted = deepcopy(baseline)
    wanted[path[0]][path[1]] = expected
    return candidate == wanted


def apply_verified_delta(policy: dict, task_id: str) -> None:
    path, value = TASKS[task_id]
    policy[path[0]][path[1]] = value


def finalize(repo: Path, policy: dict) -> tuple[str, int, int]:
    if policy != EXPECTED_POLICY:
        raise ValueError("FB003 final policy mismatch")
    (repo / "service/policy.py").write_text(render_policy(policy), encoding="utf-8")
    commit = _commit(repo, "FB003 known-good output")
    checks = [commit == EXPECTED_OUTPUT_COMMIT, extract_policy((repo / "service/policy.py").read_text(encoding="utf-8")) == EXPECTED_POLICY]
    return commit, sum(bool(x) for x in checks), len(checks)

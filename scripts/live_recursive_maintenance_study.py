#!/usr/bin/env python3
"""Live-model recursive-maintenance benchmark for RESIDUAL.

This study uses a localhost FreeLLMAPI instance as the provider router. It creates
seeded defects only inside detached temporary worktrees, asks live models for a
bounded patch, applies the returned diff if it stays within the frozen scope,
then runs deterministic hidden acceptance. A second model call critiques the
candidate; the critic is observational and never overrides deterministic gates.

No provider/dashboard/unified credentials are written into retained evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FREELLM_BASE = "http://127.0.0.1:3001"
PROTECTED_PREFIXES = (".github/", "residual/control_plane/", "residual/factory/")
PROTECTED_FILES = {"residual/verifier.py", "residual/goalspec.py", "residual/loop.py"}
ROUTES = ("auto:fast", "auto:smart", "auto:reliable")


@dataclass(frozen=True)
class Task:
    task_id: str
    issue: str
    allowed_paths: tuple[str, ...]
    context_paths: tuple[str, ...]
    mutation_path: str
    old: str
    new: str
    hidden_kind: str
    regression_command: tuple[str, ...] = ()


TASKS = (
    Task(
        "RB_PATH_ESCAPE",
        "Security regression: a bundle can accept an existing artifact outside the evidence root through a '../outside.json' path. Restore fail-closed root confinement without changing the public API.",
        ("residual/research_bundle.py",),
        ("residual/research_bundle.py",),
        "residual/research_bundle.py",
        '''    candidate = (root / relative).resolve()\n    root_resolved = root.resolve()\n    try:\n        candidate.relative_to(root_resolved)\n    except ValueError as exc:\n        raise ResearchBundleError(f"artifact path escapes bundle root: {relative}") from exc\n''',
        '''    candidate = (root / relative).resolve()\n''',
        "rb_path_escape",
        ("python", "-m", "pytest", "-q", "tests/test_research_bundle.py"),
    ),
    Task(
        "RB_POINTER_BOUNDARY",
        "Correctness regression: JSON Pointer access to an array index exactly equal to the array length leaks IndexError instead of the module's ResearchBundleError. Restore the documented strict error contract.",
        ("residual/research_bundle.py",),
        ("residual/research_bundle.py",),
        "residual/research_bundle.py",
        "            if index >= len(node):\n",
        "            if index > len(node):\n",
        "rb_pointer_boundary",
        ("python", "-m", "pytest", "-q", "tests/test_research_bundle.py"),
    ),
    Task(
        "SM_ACTION_ALLOWLIST",
        "Authority regression: MaintenanceContract now rejects only explicitly forbidden actions, so an unknown capability such as 'shell.exec' can slip through. Restore the closed safe-action contract without expanding authority.",
        ("residual/self_maintenance.py",),
        ("residual/self_maintenance.py",),
        "residual/self_maintenance.py",
        "        if any(action in FORBIDDEN_ACTIONS or action not in SAFE_ACTIONS for action in actions):\n",
        "        if any(action in FORBIDDEN_ACTIONS for action in actions):\n",
        "sm_action_allowlist",
        ("python", "-m", "pytest", "-q", "tests/test_self_maintenance.py"),
    ),
    Task(
        "SM_BACKSLASH_PATH",
        "Authority regression: repository path validation no longer rejects Windows/backslash spellings such as 'safe\\\\..\\\\outside.py'. Restore canonical POSIX-relative validation without weakening protected-path rules.",
        ("residual/self_maintenance.py",),
        ("residual/self_maintenance.py",),
        "residual/self_maintenance.py",
        '    if value.startswith("/") or "\\\\" in value or ":" in value:\n',
        '    if value.startswith("/") or ":" in value:\n',
        "sm_backslash_path",
        ("python", "-m", "pytest", "-q", "tests/test_self_maintenance.py"),
    ),
    Task(
        "DOC_PROVENANCE_DRIFT",
        "Documentation regression: RESEARCH_BUNDLES.md incorrectly says source bytes are not cryptographically bound. Inspect the implementation and repair the documentation only; do not change runtime code.",
        ("docs/research/RESEARCH_BUNDLES.md",),
        ("docs/research/RESEARCH_BUNDLES.md", "residual/research_bundle.py"),
        "docs/research/RESEARCH_BUNDLES.md",
        "`residual.research_bundle` freezes exact artifact bytes, extracts declared JSON Pointer metrics, and binds every extracted value to the SHA-256 of the artifact that supplied it.",
        "`residual.research_bundle` stores artifact paths and metric values but does not cryptographically bind the source bytes.",
        "doc_provenance_drift",
    ),
)


class StudyError(RuntimeError):
    pass


def run(cmd: list[str] | tuple[str, ...], *, cwd: Path, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(list(cmd), cwd=cwd, text=True, capture_output=True, env=merged)
    if check and proc.returncode:
        raise StudyError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}"[:12000])
    return proc


def api(path: str, *, method: str = "GET", body: dict[str, Any] | None = None, bearer: str | None = None, timeout: int = 240):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(FREELLM_BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, dict(resp.headers.items()), json.loads(raw)


def start_router(freellmapi_dir: Path, out: Path) -> tuple[subprocess.Popen[str], str, list[dict[str, Any]]]:
    env = os.environ.copy()
    env.update({
        "ENCRYPTION_KEY": secrets.token_hex(32),
        "FREEAPI_DB_PATH": str((out / "freellmapi.db").resolve()),
        "HOST": "127.0.0.1",
        "PORT": "3001",
        "REQUEST_ANALYTICS_RETENTION_DAYS": "0",
        "REQUEST_ANALYTICS_MAX_ROWS": "0",
        "FALLBACK_TIME_BUDGET_MS": "150000",
        "PROXY_RATE_LIMIT_RPM": "90",
    })
    log = (out / "freellmapi-server.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(["node", "server/dist/index.js"], cwd=freellmapi_dir, env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
    ready = False
    for _ in range(120):
        try:
            status, _, payload = api("/api/auth/status", timeout=5)
            if status == 200 and payload.get("needsSetup") is True:
                ready = True
                break
        except Exception:
            pass
        time.sleep(1)
    if not ready:
        raise StudyError("FreeLLMAPI did not reach first-run ready state")

    password = secrets.token_urlsafe(30)
    _, _, setup = api("/api/auth/setup", method="POST", body={"email": "residual-study@example.invalid", "password": password})
    admin = setup["token"]
    _, _, key_payload = api("/api/settings/api-key", bearer=admin)
    unified = key_payload["apiKey"]

    configured: list[dict[str, Any]] = []
    for platform in ("kilo", "ovh"):
        try:
            status, _, payload = api("/api/keys", method="POST", bearer=admin, body={"platform": platform, "label": "RESIDUAL ephemeral live study"})
            configured.append({"platform": platform, "status": status, "modelsAvailable": payload.get("modelsAvailable")})
        except urllib.error.HTTPError as exc:
            configured.append({"platform": platform, "status": exc.code, "error": exc.read().decode("utf-8", errors="replace")[:800]})
    return proc, unified, configured


def chat(unified: str, route: str, messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> tuple[str, dict[str, Any]]:
    status, headers, payload = api(
        "/v1/chat/completions",
        method="POST",
        bearer=unified,
        timeout=300,
        body={"model": route, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
    )
    content = payload["choices"][0]["message"]["content"] or ""
    routed = headers.get("x-routed-via") or headers.get("X-Routed-Via")
    usage = payload.get("usage") if isinstance(payload, dict) else None
    return content, {"http_status": status, "requested_route": route, "routed_via": routed, "usage": usage}


def extract_diff(text: str) -> str | None:
    fenced = re.search(r"```(?:diff|patch)?\s*\n(.*?)```", text, re.S | re.I)
    candidate = fenced.group(1) if fenced else text
    pos = candidate.find("diff --git ")
    if pos >= 0:
        return candidate[pos:].strip() + "\n"
    # Accept traditional unified diff when a model omits the git header.
    pos = candidate.find("--- a/")
    if pos >= 0 and "\n+++ b/" in candidate[pos:]:
        return candidate[pos:].strip() + "\n"
    return None


def changed_paths(repo: Path) -> list[str]:
    out = run(["git", "diff", "--name-only"], cwd=repo).stdout
    return sorted(p.strip() for p in out.splitlines() if p.strip())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hidden_check(repo: Path, kind: str) -> tuple[bool, str]:
    env = {"PYTHONPATH": str(repo)}
    snippets = {
        "rb_path_escape": r'''import tempfile
from pathlib import Path
from residual.research_bundle import freeze_bundle, ResearchBundleError
with tempfile.TemporaryDirectory() as d:
    base=Path(d); root=base/'root'; root.mkdir(); outside=base/'outside.json'; outside.write_text('{"x":1}')
    try: freeze_bundle(root,experiment_id='x',source_commit='abcdef0',artifacts=['../outside.json'])
    except ResearchBundleError: raise SystemExit(0)
    raise SystemExit(3)
''',
        "rb_pointer_boundary": r'''from residual.research_bundle import json_pointer, ResearchBundleError
try: json_pointer([1,2], '/2')
except ResearchBundleError: raise SystemExit(0)
except Exception as e: print(type(e).__name__, e); raise SystemExit(4)
raise SystemExit(3)
''',
        "sm_action_allowlist": r'''from residual.self_maintenance import MaintenanceContract, SelfMaintenanceError
try: MaintenanceContract(mission_id='m',base_commit='abcdef0',issue_ref='#x',objective='o',writable_paths=('a.py',),allowed_actions=('file.write','shell.exec'))
except SelfMaintenanceError: raise SystemExit(0)
raise SystemExit(3)
''',
        "sm_backslash_path": r'''from residual.self_maintenance import CandidateProposal, SelfMaintenanceError
try: CandidateProposal(generation=1,parent_receipt_hash=None,files={r'safe\\..\\outside.py':'x'})
except SelfMaintenanceError: raise SystemExit(0)
raise SystemExit(3)
''',
    }
    if kind == "doc_provenance_drift":
        text = (repo / "docs/research/RESEARCH_BUNDLES.md").read_text(encoding="utf-8")
        ok = "binds every extracted value to the SHA-256 of the artifact that supplied it" in text and "does not cryptographically bind" not in text
        return ok, "documentation matches source-bound SHA-256 behavior" if ok else "documentation still denies cryptographic binding"
    proc = run([os.environ.get("PYTHON", "python"), "-c", snippets[kind]], cwd=repo, check=False, env=env)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-3000:]


def make_worktree(repo: Path, base: str, task: Task, root: Path) -> Path:
    work = root / task.task_id
    run(["git", "worktree", "add", "--detach", str(work), base], cwd=repo)
    target = work / task.mutation_path
    text = target.read_text(encoding="utf-8")
    if text.count(task.old) != 1:
        raise StudyError(f"{task.task_id}: expected mutation anchor exactly once")
    target.write_text(text.replace(task.old, task.new, 1), encoding="utf-8")
    run(["git", "config", "user.email", "residual-study@example.invalid"], cwd=work)
    run(["git", "config", "user.name", "RESIDUAL Study"], cwd=work)
    run(["git", "add", task.mutation_path], cwd=work)
    run(["git", "commit", "-m", f"seed defect {task.task_id}"], cwd=work)
    return work


def prompt_for(task: Task, work: Path) -> str:
    chunks = []
    for path in task.context_paths:
        text = (work / path).read_text(encoding="utf-8")
        chunks.append(f"FILE: {path}\n```text\n{text}\n```")
    return f"""You are repairing a frozen RESIDUAL benchmark checkout.

Issue:
{task.issue}

Allowed paths: {', '.join(task.allowed_paths)}

Rules:
- Make the smallest correct repair.
- Do not edit tests, workflows, Git metadata, or any file outside Allowed paths.
- Do not grant new authority or weaken validation.
- Return ONLY a unified git diff from repository root, beginning with `diff --git`.
- Do not include prose outside the diff.

Current relevant files:

{chr(10).join(chunks)}
"""


def critic_prompt(task: Task, diff: str) -> str:
    return f"""Act as an independent code-review critic. Do not assume tests passed.
Evaluate whether this candidate patch correctly fixes the stated issue without weakening security or changing unrelated behavior.
Issue: {task.issue}
Allowed paths: {', '.join(task.allowed_paths)}
Candidate diff:\n```diff\n{diff}\n```
Return JSON only with keys `verdict` (PASS, FAIL, or UNKNOWN), `confidence` (0 to 1), and `reason` (short string)."""


def parse_critic(text: str) -> dict[str, Any]:
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S | re.I)
    if fence:
        raw = fence.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        raw = raw[start:end + 1]
    try:
        obj = json.loads(raw)
    except Exception:
        return {"verdict": "UNKNOWN", "confidence": 0, "reason": "critic response was not valid JSON", "raw_sha256": sha256_text(text)}
    verdict = str(obj.get("verdict", "UNKNOWN")).upper()
    if verdict not in {"PASS", "FAIL", "UNKNOWN"}:
        verdict = "UNKNOWN"
    try:
        confidence = float(obj.get("confidence", 0))
    except Exception:
        confidence = 0
    return {"verdict": verdict, "confidence": max(0.0, min(1.0, confidence)), "reason": str(obj.get("reason", ""))[:1000]}


def evaluate_candidate(repo: Path, task: Task, diff: str | None) -> dict[str, Any]:
    if not diff:
        return {"accepted": False, "failure_stage": "diff_parse", "changed_paths": []}
    patch = repo / ".residual-live-candidate.patch"
    patch.write_text(diff, encoding="utf-8")
    check = run(["git", "apply", "--check", str(patch)], cwd=repo, check=False)
    if check.returncode:
        return {"accepted": False, "failure_stage": "git_apply_check", "apply_error": (check.stdout + check.stderr)[-3000:], "changed_paths": []}
    applied = run(["git", "apply", str(patch)], cwd=repo, check=False)
    if applied.returncode:
        return {"accepted": False, "failure_stage": "git_apply", "apply_error": (applied.stdout + applied.stderr)[-3000:], "changed_paths": []}
    paths = [p for p in changed_paths(repo) if p != patch.name]
    allowed = set(task.allowed_paths)
    scope_ok = set(paths).issubset(allowed) and all(p not in PROTECTED_FILES and not any(p.startswith(prefix) for prefix in PROTECTED_PREFIXES) for p in paths)
    if not scope_ok:
        return {"accepted": False, "failure_stage": "scope", "changed_paths": paths}
    hidden_ok, hidden_detail = hidden_check(repo, task.hidden_kind)
    regression_ok = True
    regression_detail = ""
    if task.regression_command:
        reg = run(task.regression_command, cwd=repo, check=False, env={"PYTHONPATH": str(repo)})
        regression_ok = reg.returncode == 0
        regression_detail = (reg.stdout + reg.stderr)[-5000:]
    return {
        "accepted": bool(scope_ok and hidden_ok and regression_ok),
        "failure_stage": None if scope_ok and hidden_ok and regression_ok else ("hidden_acceptance" if not hidden_ok else "regression"),
        "changed_paths": paths,
        "scope_ok": scope_ok,
        "hidden_ok": hidden_ok,
        "hidden_detail": hidden_detail,
        "regression_ok": regression_ok,
        "regression_detail": regression_detail,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path.cwd())
    p.add_argument("--freellmapi-dir", type=Path, required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--routes", nargs="*", default=list(ROUTES))
    args = p.parse_args()
    repo = args.repo.resolve(); out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    freellm = args.freellmapi_dir.resolve()
    server: subprocess.Popen[str] | None = None
    workroot = Path(tempfile.mkdtemp(prefix="residual-live-repair-"))
    results: list[dict[str, Any]] = []
    try:
        server, unified, configured = start_router(freellm, out)
        _, _, models = api("/v1/models", bearer=unified)
        router_meta = {
            "freellmapi_commit": run(["git", "rev-parse", "HEAD"], cwd=freellm).stdout.strip(),
            "configured_keyless_providers": configured,
            "advertised_model_count": len(models.get("data", [])) if isinstance(models, dict) else None,
        }
        (out / "router.json").write_text(json.dumps(router_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        for route_index, route in enumerate(args.routes):
            for task in TASKS:
                trial_id = f"{route.replace(':','-')}-{task.task_id}"
                record: dict[str, Any] = {"trial_id": trial_id, "task_id": task.task_id, "generator_route": route, "base_commit": args.base}
                work = make_worktree(repo, args.base, task, workroot)
                try:
                    baseline_ok, baseline_detail = hidden_check(work, task.hidden_kind)
                    record["seeded_defect_observed"] = not baseline_ok
                    record["seeded_defect_detail"] = baseline_detail
                    if baseline_ok:
                        record.update({"accepted": False, "failure_stage": "invalid_seed"})
                        results.append(record)
                        continue
                    prompt = prompt_for(task, work)
                    try:
                        completion, gen_meta = chat(unified, route, [{"role": "system", "content": "You are a precise software repair agent."}, {"role": "user", "content": prompt}], max_tokens=2400, temperature=0.15)
                        record["generator"] = gen_meta
                        record["generator_response_sha256"] = sha256_text(completion)
                        (out / f"{trial_id}.generator.txt").write_text(completion, encoding="utf-8")
                        diff = extract_diff(completion)
                        if diff:
                            (out / f"{trial_id}.patch").write_text(diff, encoding="utf-8")
                        outcome = evaluate_candidate(work, task, diff)
                        record.update(outcome)
                    except Exception as exc:
                        record.update({"accepted": False, "failure_stage": "generator_call", "generator_error": f"{type(exc).__name__}: {exc}"[:3000]})
                        diff = None

                    # Model critic is observational only. Try a route different from the generator arm.
                    if diff:
                        critic_routes = [args.routes[(route_index + 1) % len(args.routes)], args.routes[(route_index + 2) % len(args.routes)]] if len(args.routes) > 1 else [route]
                        critic_attempts = []
                        for critic_route in critic_routes:
                            try:
                                critique_text, critic_meta = chat(unified, critic_route, [{"role": "user", "content": critic_prompt(task, diff)}], max_tokens=500, temperature=0)
                                parsed = parse_critic(critique_text)
                                parsed["route"] = critic_meta
                                parsed["response_sha256"] = sha256_text(critique_text)
                                critic_attempts.append(parsed)
                                if critic_meta.get("routed_via") and critic_meta.get("routed_via") != record.get("generator", {}).get("routed_via"):
                                    break
                            except Exception as exc:
                                critic_attempts.append({"verdict": "UNKNOWN", "confidence": 0, "reason": f"critic call failed: {type(exc).__name__}: {exc}", "route": {"requested_route": critic_route}})
                        record["critic_attempts"] = critic_attempts
                        chosen = next((c for c in critic_attempts if c.get("route", {}).get("routed_via") and c.get("route", {}).get("routed_via") != record.get("generator", {}).get("routed_via")), critic_attempts[0] if critic_attempts else None)
                        record["critic"] = chosen
                        record["critic_route_diverse"] = bool(chosen and chosen.get("route", {}).get("routed_via") and chosen.get("route", {}).get("routed_via") != record.get("generator", {}).get("routed_via"))
                    results.append(record)
                finally:
                    run(["git", "worktree", "remove", "--force", str(work)], cwd=repo, check=False)

        accepted = sum(1 for r in results if r.get("accepted"))
        valid_trials = sum(1 for r in results if r.get("seeded_defect_observed"))
        gen_routes = sorted({r.get("generator", {}).get("routed_via") for r in results if r.get("generator", {}).get("routed_via")})
        diverse_critics = sum(1 for r in results if r.get("critic_route_diverse"))
        critic_scored = [r for r in results if r.get("critic")]
        critic_correct = sum(1 for r in critic_scored if (r["critic"]["verdict"] == "PASS") == bool(r.get("accepted")) and r["critic"]["verdict"] != "UNKNOWN")
        summary = {
            "schema_version": 1,
            "base_commit": args.base,
            "trial_count": len(results),
            "valid_seed_count": valid_trials,
            "accepted_count": accepted,
            "repair_rate": accepted / valid_trials if valid_trials else None,
            "generator_requested_routes": list(args.routes),
            "observed_generator_routes": gen_routes,
            "observed_generator_route_count": len(gen_routes),
            "critic_trial_count": len(critic_scored),
            "critic_route_diverse_count": diverse_critics,
            "critic_nonunknown_correct_count": critic_correct,
            "live_model_authored_candidate_count": len(results),
            "deterministic_acceptance_controls_promotion": True,
            "model_critic_controls_promotion": False,
            "credentials_retained": False,
            "router": router_meta,
            "results": results,
        }
        (out / "results.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2, sort_keys=True))
        # The research run itself succeeds if the infrastructure executed a full valid matrix;
        # candidate repair failures are measurements, not workflow failures.
        return 0 if valid_trials == len(results) and len(results) == len(args.routes) * len(TASKS) else 3
    finally:
        if server is not None:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill()
        shutil.rmtree(workroot, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

from residual.core import canonical
from residual.station.control import run_controlled_batch
from residual.station.models import PROVIDERS, save_settings
from residual.station.service import Station

SPEC = """# Live provider qualification mission

The provider must implement one bounded function and then independently review
the resulting candidate. Deterministic checks, Station review binding, integration
and release export remain authoritative.

```json
{
  "schema_version": 1,
  "name": "Live Provider Qualification",
  "goal": "Implement a tiny deterministic arithmetic module.",
  "tasks": [
    {
      "id": "LIVE-1",
      "title": "Implement add",
      "instruction": "Implement add(a, b) in app.py. It must return the Python sum a + b for integers and floats. Do not add unrelated files.",
      "files": ["app.py"],
      "context": [],
      "depends_on": [],
      "route": "cloud",
      "checks": [
        {"kind": "python_compile", "path": "app.py"},
        {"kind": "command", "argv": ["{python}", "-c", "from app import add; assert add(2, 3) == 5; assert add(-4, 1) == -3; assert add(1.5, 2.25) == 3.75"], "timeout": 30}
      ]
    }
  ]
}
```
"""


def profile(provider: str, model: str, base_url: str | None) -> dict:
    if provider not in {"openai", "openai_compatible", "anthropic", "google"}:
        raise ValueError("full mission supports openai, openai_compatible, anthropic or google")
    default = PROVIDERS[provider]["base_url"]
    return {
        "kind": provider,
        "model": model,
        "base_url": base_url or default,
        "output_token_field": "max_completion_tokens",
    }


def run_mission(*, provider: str, model: str, base_url: str | None, root: Path, continuity=None) -> dict:
    if provider != "openai_compatible" and not os.environ.get("RESIDUAL_CLOUD_API_KEY"):
        return {
            "schema": "residual.qualification.provider-mission.v1",
            "result": "UNKNOWN",
            "provider": provider,
            "model": model,
            "reason": "RESIDUAL_CLOUD_API_KEY is absent",
            "non_claim": "No fixture result is substituted for missing live-provider credentials.",
        }

    started = time.monotonic()
    station = Station(root)
    save_settings(station.store, {
        "cloud": profile(provider, model, base_url),
        "review_placement": "cloud",
        "max_output_tokens": 4096,
    })
    if continuity:
        from residual.continuity import Continuity
        from residual.continuity.__main__ import configured_profiles, probe_request, validate_probe
        from residual.modular import make_adapter
        from residual.station.models import credentials_for
        save_settings(station.store, continuity['settings'])
        settings = station.store.settings()
        for route in configured_profiles(settings):
            Continuity(station.store).qualify(route, continuity['contexts'][route['route_id']],
                make_adapter(route, credentials_for(settings, route['kind'], credential_ref=route['credential_ref'])),
                probe_request(route['model']), validate_probe)
    pid = station.create(SPEC, allow_cloud=True, commands=True)["project_id"]
    try:
        # The authority-bearing mission itself must execute inside run control.
        # BudgetAdmission gates dispatch, review, and integration before each
        # effect; obtaining a receipt after doing those effects would only prove
        # post-hoc export compatibility, not governed execution.
        control = run_controlled_batch(station, pid, lambda *_args: None)
        if control["control"]["outcome"] != "success":
            raise RuntimeError("run control did not establish release authority")

        task = station.store.task(pid, "LIVE-1")
        if task["state"] != "integrated":
            raise RuntimeError("controlled mission did not integrate the verified candidate")
        integrated_head = control["control"]["project_head"]

        release = station.export(pid)
        meta, release_bytes = station.store.artifact(release["id"])
        task = station.store.task(pid, "LIVE-1")
        metrics = station.metrics(pid)
        return {
            "schema": "residual.qualification.provider-mission.v1",
            "result": "PASS",
            "continuity": Continuity(station.store).inspect(configured_profiles(station.store.settings()), 'AUTOMATIC_ELIGIBLE') if continuity else None,
            "provider": provider,
            "model_requested": model,
            "project_id": pid,
            "integrated_head": integrated_head,
            "authority_path": "run_controlled_batch",
            "run_control": {
                "outcome": control["control"]["outcome"],
                "project_head": control["control"]["project_head"],
                "project_spec_hash": control["control"]["project_spec_hash"],
                "evidence": control["control"]["evidence"],
            },
            "verification_receipt_hash": task["verification_receipt"]["receipt"]["receipt_hash"],
            "release": {
                "id": release["id"],
                "name": meta["name"],
                "sha256": hashlib.sha256(release_bytes).hexdigest(),
                "size": len(release_bytes),
            },
            "metrics": metrics,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            "non_claim": "PASS establishes one exact-revision end-to-end provider mission; it does not establish general model quality or long-run provider reliability.",
        }
    except Exception as exc:
        retained = station.store.observation_export(pid)
        return {
            "schema": "residual.qualification.provider-mission.v1",
            "result": "FAIL",
            "provider": provider,
            "model_requested": model,
            "project_id": pid,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
            "observation_sha256": hashlib.sha256(retained.encode("utf-8")).hexdigest(),
            "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
            "non_claim": "The live failure is retained; no scripted provider fallback is substituted.",
        }



def fixture_admission_context(model):
    """Synthetic evidence exclusively for the explicitly labeled fixture endpoint."""
    from dataclasses import asdict
    from residual.continuity.vendor import bl006
    return {'manifest': asdict(bl006.create_manifest(model, 'fixture', 'fixture/1', 'fixture',
                100, 1, 8192, 10, footprint_class='MEASURED', kv_class='MEASURED')),
            'telemetry': asdict(bl006.create_telemetry(1000000, None, 0, 4)),
            'host_identity': 'qualification-fixture', 'requested_context_tokens': 8192,
            'requested_max_tokens': 4096}


def run_continuity_mission(*, root, endpoint=None, model=None, admission_context=None):
    """One fake rejected primary, then a compatible fixture or explicitly supplied live route.

    Never claims provider-side exactly-once. A started call without persisted
    result is INDETERMINATE_PROVIDER_OUTCOME and is never replayed automatically.
    """
    import threading
    from collections import Counter
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    counts = Counter()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            probe = body['max_completion_tokens'] == 32
            primary = self.path.startswith('/primary/')
            counts[('primary' if primary else 'freellmapi') + ('_probe' if probe else '_call')] += 1
            if primary and not probe:
                status = 429
                response = {'error': {'code': 'insufficient_quota'},
                            'usage': {'prompt_tokens': 0, 'completion_tokens': 0}}
            else:
                status = 200
                system = str(body)
                if probe:
                    content = {'ready': True}
                elif '"approved"' in system or 'Review the candidate' in system or 'independent review' in system.lower():
                    content = {'approved': True, 'findings': []}
                else:
                    content = {'files': {'app.py': 'def add(a, b):\n    return a + b\n'}}
                response = {'model': body['model'], 'choices': [{'message': {'role': 'assistant',
                    'content': json.dumps(content)}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 10, 'completion_tokens': 10}}
            encoded = json.dumps(response).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
    if endpoint and not (model and admission_context):
        raise ValueError('Live continuity requires explicit model and BL-006 context')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    selected_model = model or 'fixture-fallback'
    settings = {'cloud': {**profile('openai_compatible', 'fixture-primary', url + '/primary/v1'), 'route_id': 'primary-cloud'},
                'cloud_fallbacks': [{**profile('openai_compatible', selected_model, endpoint or url + '/fallback/v1'), 'route_id': 'freellmapi'}],
                'fallback_mode': 'AUTOMATIC_ELIGIBLE'}
    contexts = {'primary-cloud': fixture_admission_context('fixture-primary'),
                'freellmapi': admission_context if endpoint else fixture_admission_context(selected_model)}
    try:
        report = run_mission(provider='openai_compatible', model='fixture-primary', base_url=url + '/primary/v1',
                             root=root, continuity={'settings': settings, 'contexts': contexts})
    except Exception as error:
        report = {'result': 'FAIL', 'error_type': type(error).__name__}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    report.update(schema='residual.qualification.provider-continuity.v1',
                  qualification_kind='LIVE_FREELLMAPI' if endpoint else 'DETERMINISTIC_FIXTURE',
                  fixture_calls=dict(counts), provider_side_exactly_once=False,
                  crash_semantics={'PLANNED': 'normal gates then invoke',
                                   'INVOCATION_STARTED': 'INDETERMINATE_PROVIDER_OUTCOME; no automatic replay',
                                   'PROVIDER_RESULT_RECORDED': 'reuse durable result; no provider call'},
                  trust_boundary='FreeLLMAPI is remote evidence; READY and independent BL-006 PASS required',
                  terminal_target='PROVIDER_CONTINUITY_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW')
    return report

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run one full live-provider RESIDUAL mission")
    parser.add_argument("--provider")
    parser.add_argument("--continuity-fixture", action="store_true")
    parser.add_argument("--continuity-live", action="store_true")
    parser.add_argument("--admission-context", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)

    if args.continuity_fixture or args.continuity_live:
        if args.continuity_fixture and args.continuity_live:
            parser.error('Choose fixture or live qualification')
        if args.continuity_live and not (args.base_url and args.model and args.admission_context):
            parser.error('Live continuity requires --base-url, --model and --admission-context')
        context = json.loads(args.admission_context.read_text()) if args.admission_context else None
        def qualify(root):
            return run_continuity_mission(root=root, endpoint=args.base_url if args.continuity_live else None,
                                          model=args.model if args.continuity_live else None, admission_context=context)
    else:
        if not args.provider or not args.model:
            parser.error('--provider and --model are required for a live provider mission')
        def qualify(root):
            return run_mission(provider=args.provider, model=args.model, base_url=args.base_url, root=root)
    if args.root:
        args.root.mkdir(parents=True, exist_ok=True)
        report = qualify(args.root)
    else:
        with tempfile.TemporaryDirectory(prefix="residual-live-provider-mission-") as temp:
            report = qualify(Path(temp))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else (2 if report["result"] == "UNKNOWN" else 1)


if __name__ == "__main__":
    raise SystemExit(main())

"""Smoke test: serve.py endpoints behind the Backend interface."""

import json
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from research.slm.inference.export.export import (
    build_model_from_config,
    export_model,
)
from research.slm.inference.runtime.backend import load_backend
from research.slm.inference.serve import make_handler

TINY_CONFIG = os.path.join(os.path.dirname(__file__), "tiny-config.yaml")


def test_serve_generate_and_metadata(tmp_path):
    model, raw = build_model_from_config(TINY_CONFIG, seed=5)
    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="fp32",
        output_dir=str(tmp_path),
        code_commit="test-commit",
        seed=5,
    )
    backend = load_backend(manifest_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(backend))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metadata") as r:
            meta = json.loads(r.read())
        assert meta["backend"] == "pytorch"
        assert meta["context_length"] == 32

        body = json.dumps(
            {"tokens": [1, 2, 3], "decoding": {"max_new_tokens": 3, "seed": 1}}
        ).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/generate", data=body, method="POST"
        )
        with urllib.request.urlopen(req) as r:
            out = json.loads(r.read())
        assert len(out["generated_tokens"]) == 3
    finally:
        server.shutdown()
        server.server_close()

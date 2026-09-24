"""Minimal single-file CPU inference server behind the Backend interface.

Serves any exported artifact (any backend) over plain HTTP using only
the standard library plus the runtime package. Intended for
Residual-Nano-class models on ordinary hosts; see cpu_deploy.md for
memory/latency expectations.

Endpoints:
  GET  /metadata  -> backend capabilities JSON
  POST /generate  -> {"tokens": [...], "decoding": {...}} ->
                     {"generated_tokens": [...]}

Usage:
  python serve.py --manifest out/manifest.json [--host 127.0.0.1] [--port 8080]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:  # module layout: python -m inference.serve
    from .runtime.backend import DecodingConfig, load_backend
except ImportError:  # script layout: python serve.py
    from runtime.backend import DecodingConfig, load_backend

_DECODING_FIELDS = {
    "max_new_tokens",
    "temperature",
    "top_k",
    "top_p",
    "seed",
    "stop_tokens",
}


def make_handler(backend):
    """Build a request handler bound to a loaded backend."""

    class Handler(BaseHTTPRequestHandler):
        """JSON-over-HTTP handler for /generate and /metadata."""

        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/metadata":
                self._send(200, asdict(backend.metadata()))
            else:
                self._send(404, {"error": "unknown path"})

        def do_POST(self) -> None:
            if self.path != "/generate":
                self._send(404, {"error": "unknown path"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                req = json.loads(self.rfile.read(length) or b"{}")
                tokens = [int(t) for t in req["tokens"]]
                dec_raw = {
                    k: v for k, v in (req.get("decoding") or {}).items()
                    if k in _DECODING_FIELDS
                }
                out = backend.generate(tokens, DecodingConfig(**dec_raw))
                self._send(200, {"generated_tokens": out})
            except (KeyError, TypeError, ValueError) as exc:
                self._send(400, {"error": f"bad request: {exc}"})

        def log_message(self, fmt, *args):  # keep stdout clean
            pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Serve an exported SLM artifact over HTTP (CPU-only)."
    )
    parser.add_argument("--manifest", required=True, help="export manifest JSON")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", type=int, default=8080, help="bind port")
    args = parser.parse_args(argv)

    backend = load_backend(args.manifest)
    caps = backend.metadata()
    print(
        f"serving {caps.backend}/{caps.quantization} "
        f"(ctx={caps.context_length}, {caps.parameter_count:,} params) "
        f"on http://{args.host}:{args.port}"
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(backend))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

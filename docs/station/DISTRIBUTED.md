# Distributed inference runners

The station can accept additional inference-only machines. Workers read scoped source and propose files; the coordinator applies the proposal, executes checks, reviews and integrates. Distributed test execution is not included.

1. Open **Diagnostics → Connect another runner**, enable access, and copy the key onto a trusted machine. Each issued key is a distinct credential and binds to exactly one project + runner identity on its first successful claim.
2. Use an SSH tunnel or TLS connection. The default station is loopback-only.
3. Set `RESIDUAL_WORKER_TOKEN` in the worker environment; never commit it or put it in an argument.
4. Run the client from the bundle:

```bash
python3 -m residual.station.worker \
  --station http://127.0.0.1:8765 \
  --project p-YOURPROJECT \
  --name workstation-02 \
  --model qwen2.5-coder:7b
```

The loopback station URL can be the local endpoint of an authenticated SSH tunnel forwarding to the station host. The client's default endpoint is its own local Ollama. A credential that has already bound to a project/runner pair cannot be reused for another project or runner; choose **Enable & reveal key** again for another runner. **Rotate key** invalidates every previously issued runner credential.

Compatible local servers: add `--kind openai_compatible --base-url http://127.0.0.1:1234/v1 --model MODEL`. Remote inference requires `--placement remote`, HTTPS, project cloud permission, and optional `RESIDUAL_RUNNER_API_KEY`.

## Exposure policy

The built-in server fails closed on non-loopback binds. The preferred deployment is loopback plus an authenticated SSH tunnel or trusted TLS reverse proxy. If a direct non-loopback bind is deliberately required, all three controls are mandatory:

```bash
export RESIDUAL_REMOTE_EXPOSURE=1
export RESIDUAL_ALLOWED_HOSTS=station.example.com
export RESIDUAL_PUBLIC_URL=https://station.example.com
python3 -m residual.station.server --host 0.0.0.0 --port 8765
```

`RESIDUAL_PUBLIC_URL` must be an HTTPS origin whose authority exactly matches an entry in `RESIDUAL_ALLOWED_HOSTS`. Preserve the Host header and restrict proxy/network access to trusted operators/workers. No reverse proxy is included or published automatically; the built-in HTTP server does not terminate TLS.

The operator session token is never returned by unauthenticated `/api/bootstrap`. Server startup prints a one-time launch URL. Opening that URL exchanges its one-time capability for an HttpOnly, SameSite session cookie and immediately redirects to the normal UI. Treat the printed launch URL as an operator secret until it has been consumed.

## Protocol

- `POST /api/worker/claim`: project ID, worker name, optional task ID. The first successful claim binds the credential to that project and runner identity. Returns attempt, lease, scoped context and cloud permission.
- `POST /api/worker/heartbeat`: renew an unexpired lease only when the credential identity still owns that exact task.
- `POST /api/worker/result`: submission ID, lease, task, candidate files and optional worker-reported usage; the same project, runner identity and lease must still own the task.

Transport retries reuse the same submission ID and exact proposal. A different payload with the same ID is rejected. Workers cannot invoke operator task transitions, approve, or integrate tasks. The coordinator verifies every proposal and owns subsequent state transitions.

During inference the client heartbeats every 60 seconds. A temporary interruption can recover inside the bounded grace window. If heartbeat failures persist for 180 seconds, the runner surrenders authority, does not submit the eventual proposal, and exits rather than continuing indefinitely under an unproven lease. Server-side lease expiry and reassignment remain authoritative; a stale returning result is rejected.

Polling is plain HTTP with no inference, defaulting to 10 seconds. `--once` supports an external scheduler. Disable access to stop all remote claims immediately; rotate credentials after suspected exposure or when changing the trusted runner set.

Central budgets cover station-issued calls. Independently operated workers must enforce their own provider spending limits. Their usage receipts are labeled worker-reported and excluded from direct provider-reported totals.

## Modular providers (0.3)

The same runner accepts `--kind openai`, `anthropic`, `google`, `azure`, or `bedrock`, in addition to Ollama and compatible servers. Set `--placement remote` and use a cloud-enabled mission for cloud inference. Azure accepts `--api-version` and requires `--base-url`; Bedrock accepts `--region` and AWS environment credentials. Provider-specific environment variables are listed in [MODULAR-LAYERS.md](MODULAR-LAYERS.md). The worker has no automatic provider failover; the coordinator's UI routes apply to coordinator-owned inference. Worker receipts remain explicitly `worker_reported`.

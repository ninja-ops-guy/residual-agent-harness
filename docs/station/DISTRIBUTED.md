# Distributed inference runners

The station can accept additional inference-only machines. Workers read scoped source and propose files; the coordinator applies the proposal, executes checks, reviews and integrates. Distributed test execution is not included.

1. Open **Diagnostics → Connect another runner**, enable access, and copy the key onto a trusted machine.
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

The loopback station URL can be the local endpoint of an SSH tunnel forwarding to the station host. Diagnostics shows the project ID beside the enabled worker key. The client's default endpoint is its own local Ollama.

Compatible local servers: add `--kind openai_compatible --base-url http://127.0.0.1:1234/v1 --model MODEL`. Remote inference requires `--placement remote`, HTTPS, project cloud permission, and optional `RESIDUAL_RUNNER_API_KEY`.

For a trusted TLS reverse proxy, configure `RESIDUAL_ALLOWED_HOSTS=station.example.com` and preserve the Host header. Restrict proxy/network access to trusted operators/workers. No reverse proxy is included or published automatically; the built-in HTTP server does not terminate TLS.

## Protocol

- `POST /api/worker/claim`: project ID, worker name, optional task ID. Returns attempt, lease, scoped context and cloud permission.
- `POST /api/worker/heartbeat`: renew an unexpired lease; client sends every 60 seconds during inference.
- `POST /api/worker/result`: submission ID, lease, task, candidate files and optional worker-reported usage.

Transport retries reuse the same submission ID and exact proposal. A different payload with the same ID is rejected. Workers cannot approve/integrate tasks. The operator's **Run mission** processes review-ready submissions and subsequent dependent work.

Polling is plain HTTP with no inference, defaulting to 10 seconds. `--once` supports an external scheduler. Worker keys allow access to live project scopes on the station; per-project worker identities and multi-tenant isolation are not implemented. Disable/rotate keys in the UI.

Central budgets cover station-issued calls. Independently operated workers must enforce their own provider spending limits. Their usage receipts are labeled worker-reported and excluded from direct provider-reported totals.


## Modular providers (0.3)

The same runner now accepts `--kind openai`, `anthropic`, `google`, `azure`, `bedrock`, or `arena`, in addition to Ollama and compatible servers. Set `--placement remote` and use a cloud-enabled mission for cloud inference. Azure accepts `--api-version` and requires `--base-url`; Bedrock accepts `--region` and AWS environment credentials. Provider-specific environment variables are listed in [MODULAR-LAYERS.md](MODULAR-LAYERS.md). The worker has no automatic provider failover; the coordinator's UI routes apply to coordinator-owned inference. Worker receipts remain explicitly `worker_reported`.

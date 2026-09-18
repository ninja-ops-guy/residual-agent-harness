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

The same runner now accepts `--kind openai`, `anthropic`, `google`, `azure`, or `bedrock`, in addition to Ollama and compatible servers. Set `--placement remote` and use a cloud-enabled mission for cloud inference. Azure accepts `--api-version` and requires `--base-url`; Bedrock accepts `--region` and AWS environment credentials. Provider-specific environment variables are listed in [MODULAR-LAYERS.md](MODULAR-LAYERS.md). The worker has no automatic provider failover; the coordinator's UI routes apply to coordinator-owned inference. Worker receipts remain explicitly `worker_reported`.


## Reproducible distributed experiments

The repository also includes controlled loopback benchmarks for separating worker parallelism from coordinator/integration overhead:

```bash
residual experiment distributed --workers 1 2 4 --tasks 8 --work-ms 40 --repeats 3 --output runs/distributed.json

residual experiment pipeline --workers 1 2 4 --width 4 --depth 2 --work-ms 40 --repeats 3 --output runs/pipeline.json
```

The first workload contains independent tasks. The pipeline workload contains dependency-gated lanes, so later work becomes claimable only after its prerequisite is reviewed and integrated.

Both use the real Station HTTP worker, lease, submission, candidate-worktree, deterministic-check, review and integration paths. The worker provider is a controlled synthetic latency fixture and every worker is a loopback thread. These results are development measurements, not physical-network or live-model performance claims.

See [Mesh, Distributed Workflow, and Mission Control Experiments](../mesh/EXPERIMENTS.md) for metrics, evidence boundaries and the physical multi-host experiment protocol.


## Per-worker experiment telemetry

For a loaded project, the Station exposes:

```text
GET /api/projects/<PROJECT_ID>/workers
```

and renders the same information under **Diagnostics → Distributed worker telemetry**.

Remote worker receipts include a bounded self-reported `elapsed_ms` for the provider call, plus model, placement, request bytes and reported token counts. The aggregate groups those receipts with task-claim and lease-expiry events using the worker label supplied to `residual worker --name`.

The label is authenticated only through the shared worker token. Treat it as an experiment label, not a cryptographic node identity.

For physical experiments, give every machine a stable unique `--name`, for example:

```bash
residual worker \
  --station https://station.example.test \
  --project p-YOURPROJECT \
  --name lab-4070-a \
  --kind ollama \
  --model qwen2.5-coder:7b
```

Use `elapsed_ms` to separate worker inference from the rest of the workflow, but retain Station claim/check/review/integration timestamps and network RTT as separate measurements.

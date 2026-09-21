# OpenClaw Shared Comms bridge (OC-BRIDGE-R0)

OC-BRIDGE-R0 connects one OpenClaw agent to a RESIDUAL Station Shared Comms thread without making Shared Comms a task-authority channel.

The bridge only invokes OpenClaw for messages explicitly prefixed with its address (for example `@OPENCLAW-AGENT2`). It never claims Station tasks. RESIDUAL remains authoritative for mission state, task contracts, verification, and receipts; OpenClaw remains authoritative for its own model selection and provider fallback.

## Proven reference path

The R0 design is based on the live pilot sequence:

- Shared Comms request `#323` addressed to `@OPENCLAW-AGENT2`;
- hosted `kimi/kimicode` returned a real HTTP 429 quota failure;
- OpenClaw selected `ollama/qwen2.5-coder:7b`;
- the visible answer was `SHARED_COMMS_OLLAMA_OK`;
- the bridge posted response `#324`;
- Station receipt sequence was also `#324`.

The production bridge generalizes that one-shot proof into a supervised sidecar.

## Reliability contract

- SQLite WAL persists the Shared Comms cursor, input state, prepared responses, and outbound operations.
- Response operation IDs are deterministic from project, thread, request sequence, and bridge name.
- If Station delivery is ambiguous, the bridge checks `comms/receipt` before retrying.
- If the process dies after inference but before delivery, the exact prepared response is reused after restart instead of invoking the model again.
- Only one OpenClaw turn is in flight per bridge process. `RESIDUAL_OPENCLAW_MAX_BATCH` bounds work admitted per poll.
- Non-addressed messages advance the cursor without invoking an LLM.
- A message that exceeds `RESIDUAL_OPENCLAW_MAX_ATTEMPTS` is marked failed and the cursor advances so one poison message cannot stall the thread forever.
- The status JSON contains provider/model/transport/fallback evidence, but never the worker token.

## Credentials

Do not put the Station worker token in Git, the OpenClaw workspace, `SKILL.md`, or command-line arguments.

Create a root-readable token file:

```bash
sudo install -d -m 0700 /etc/residual
sudo sh -c 'printf "%s" "$RESIDUAL_WORKER_TOKEN" > /etc/residual/worker.token'
sudo chmod 0600 /etc/residual/worker.token
```

Create `/etc/residual/openclaw-bridge-agent2.env`:

```ini
RESIDUAL_STATION=http://127.0.0.1:8765
RESIDUAL_PROJECT_ID=p-892a585a20b2
RESIDUAL_WORKER_TOKEN_FILE=/etc/residual/worker.token

RESIDUAL_OPENCLAW_PROFILE=agent2
RESIDUAL_OPENCLAW_AGENT=roofbot-reviewer
RESIDUAL_OPENCLAW_NAME=OPENCLAW-AGENT2
RESIDUAL_OPENCLAW_ADDRESS=@OPENCLAW-AGENT2
RESIDUAL_OPENCLAW_THREAD=openclaw-pilot
RESIDUAL_OPENCLAW_TIMEOUT=300
RESIDUAL_OPENCLAW_POLL_SECONDS=2
RESIDUAL_OPENCLAW_MAX_ATTEMPTS=3
RESIDUAL_OPENCLAW_MAX_BATCH=1

# Optional: only runs when an addressed message arrives. The bridge checks
# /api/ps and warms the model if it is not resident.
RESIDUAL_OPENCLAW_WARM_MODEL=qwen2.5-coder:7b
RESIDUAL_OLLAMA_URL=http://127.0.0.1:11434
RESIDUAL_OLLAMA_KEEP_ALIVE=5m
RESIDUAL_OLLAMA_WARM_TIMEOUT=120
```

The example project ID above is the disposable qualification namespace. Replace it with the intended production mission before production enrollment.

## systemd

Install the template:

```bash
sudo install -m 0644 deploy/systemd/residual-openclaw-bridge@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now residual-openclaw-bridge@agent2.service
```

Check health without exposing credentials:

```bash
systemctl status residual-openclaw-bridge@agent2.service --no-pager
cat /var/lib/residual-openclaw-bridge-agent2/status.json
```

A healthy response after a Kimi-to-Ollama failover should record fields similar to:

```json
{
  "state": "ready",
  "provider": "ollama",
  "model": "qwen2.5-coder:7b",
  "transport": "embedded",
  "fallback_from": "gateway",
  "last_request_seq": 323,
  "last_response_seq": 324
}
```

`transport=embedded` is acceptable for model/Shared-Comms continuity, but it does not qualify the OpenClaw gateway control path. Gateway device-scope approval should be tracked and qualified separately.

## Addressing and loops

The bridge processes only messages whose text begins exactly with `RESIDUAL_OPENCLAW_ADDRESS`, followed by whitespace. It ignores its own `remote:<name>` actor. Responses are posted without the bridge's address prefix, so they cannot recursively trigger the bridge.

## Ollama cold-model handling

Warming is optional and occurs only after an addressed message is admitted. The bridge never warms Ollama while idle. If `RESIDUAL_OPENCLAW_WARM_MODEL` is configured, it checks `/api/ps` first and performs a bounded `/api/generate` warm-up only when the model is not resident.

On WSL2, qualify GPU memory and restart behavior before enrolling all agents simultaneously. Prefer sequential rollout and bounded bridge concurrency.

## Sequential rollout

Qualify one agent at a time:

1. Agent2 (`agent2` / `roofbot-reviewer`).
2. Anvil.
3. ForgeV2.
4. Default gateway.

For each instance verify:

- OpenClaw service remains active;
- Station and Ollama listeners remain healthy;
- one addressed Shared Comms request yields exactly one response;
- response sequence equals receipt sequence;
- the bridge status records the winning provider/model;
- restart recovers cursor/outbox state without duplicating a response.

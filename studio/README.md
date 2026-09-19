# Residual Studio

Web-first control plane for the Residual Factory runtime. Monaco editing, project exploration, swarm control, approved-plan identity, worker/verifier state, evidence/receipt surfaces, terminal/status panes and observer mode live here.

## Architecture boundary

Studio is not a second orchestration runtime. Runtime authority remains in Factory: approved ExecutionPlan, WorkerContracts, Station receipts, Evidence Bus, scheduler and deterministic integrator. The Python Studio API projects durable state and delegates mutations to an authoritative ControlAdapter; its default adapter is read-only/fail-closed.

## Start the local Factory projection

```bash
python -m residual.factory.studio_api \
  --journal runs/factory/runtime.sqlite \
  --trace-id <factory-run-id> \
  --model qwen2.5-coder:7b
```

This exposes snapshot + SSE observation endpoints on 127.0.0.1:8765. It does not enable mutations by default.

## Start Studio

```bash
cd studio
cp .env.example .env.local
npm install
npm run dev
```

For self-hosting, Next.js uses standalone output and `studio/Dockerfile` builds the web UI.

## Control actions

The UI includes approve/run/cancel/integrate controls, but they fail closed until both sides share a control token and the Python service is constructed with an authoritative ControlAdapter. See `FACTORY_API.md`. Studio itself never mints receipts or bypasses HITL/Station/M4 checks.

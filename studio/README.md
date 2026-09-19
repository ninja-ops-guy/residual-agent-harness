# Residual Studio

Web-first control plane for the Residual Factory runtime. This initial IDE slice provides the editor/control-plane shell: Monaco code editing, project explorer, swarm control, approved-plan identity, worker/verifier states, evidence/receipt surfaces, terminal/status panes, and observer-mode affordance.

## Boundary

This UI does not create a second orchestration implementation. Runtime authority remains in Residual Factory: approved ExecutionPlan, WorkerContracts, Station receipts, Evidence Bus, scheduler and deterministic integrator. The initial UI uses fixture state until the API/event-stream adapter is wired.

## Run

```bash
cd studio
npm install
npm run dev
```

For self-hosted production builds, `next.config.ts` uses standalone output.

## Next integration

1. Read-only Factory snapshot API.
2. Server-sent/WebSocket observation stream.
3. Mission submit/approve/cancel actions bound to Factory authorization.
4. Evidence/receipt drill-down.
5. Git/worktree diff viewer.
6. Observer RBAC.

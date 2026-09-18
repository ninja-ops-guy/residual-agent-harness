# Mesh, Distributed Workflow, and Mission Control Experiments

Status: experimental development evidence

This track turns the qualified mesh/onboarding components into measurable control-plane experiments. It is deliberately layered so that protocol performance, worker parallelism, dependency scheduling, and deterministic integration can be measured separately instead of collapsing them into one number.

## Experiment ladder

### L0 — Mesh protocol/session

Command:

```bash
residual experiment mesh \
  --messages 1000 \
  --peers 4 \
  --repeats 3 \
  --output runs/mesh.json
```

Measures real in-process:

- message signing;
- content/hash-chain construction;
- verified history catch-up;
- authenticated loopback JOIN/JOIN_ACK;
- explicit `MeshSession` membership;
- fanout to multiple members;
- convergence receipts.

It does **not** measure mDNS, physical LAN, WAN relay, group encryption/rekeying, forward secrecy, or consensus.

Primary metrics:

- produced messages/s;
- verified catch-up messages/s;
- fanout message-deliveries/s;
- JOIN/JOIN_ACK latency;
- convergence/integrity success.

### L1 — Independent distributed Station workers

Command:

```bash
residual experiment distributed \
  --workers 1 2 4 \
  --tasks 8 \
  --work-ms 40 \
  --repeats 3 \
  --output runs/distributed.json
```

This uses the real Command Station worker protocol over loopback HTTP:

1. Station creates and triages a project.
2. Remote-worker access is enabled.
3. N `WorkerClient` instances independently claim leases.
4. Each worker incurs controlled synthetic inference latency.
5. Candidates travel through the normal result endpoint.
6. Station writes candidate worktrees and runs deterministic checks.
7. The coordinator performs normal scripted-demo review.
8. Integration reruns accumulated checks and issues normal Station receipts.

This benchmark isolates worker parallelism. All tasks are independent, so it measures the upper bound available before dependency constraints.

Primary metrics:

- candidate-phase wall time;
- candidate throughput;
- speedup versus the smallest worker count;
- parallel efficiency;
- worker utilization/distribution;
- integration tail;
- full-workflow time;
- retained event head and successful integration count.

### L2 — Dependency-gated distributed pipeline

Command:

```bash
residual experiment pipeline \
  --workers 1 2 4 \
  --width 4 \
  --depth 2 \
  --work-ms 40 \
  --repeats 3 \
  --output runs/pipeline.json
```

This is the more realistic coordination experiment.

The workload contains `width` independent lanes and `depth` dependency layers. A downstream task cannot be claimed until its prerequisite has been verified, reviewed, and integrated. A live coordinator thread processes review-ready candidates while remote workers continue polling.

This exposes:

- worker saturation;
- dependency critical-path limits;
- coordinator latency;
- deterministic integration serialization;
- pipeline overlap between lanes;
- the point where adding workers stops improving wall time.

The report includes both the synthetic serial model-work total and the synthetic critical-path model-work floor. Neither is presented as measured provider time.

### L3 — Physical multi-host Station workers

After L1/L2 are stable, run the same project with actual machines.

Station host:

```bash
residual serve
```

Enable **Diagnostics → Connect another runner**, then distribute the worker token only to trusted machines.

Worker:

```bash
export RESIDUAL_WORKER_TOKEN='...'

residual worker \
  --station https://station.example.test \
  --project p-YOURPROJECT \
  --name workstation-02 \
  --kind ollama \
  --model qwen2.5-coder:7b
```

For physical experiments record at minimum:

- exact RESIDUAL commit;
- station/worker host identity labels;
- CPU/GPU/RAM;
- model and digest/version;
- link type and measured RTT;
- per-task worker assignment;
- provider-reported usage where available;
- candidate/integration latency;
- retries/reassignments;
- success and verification outcomes.

Do not compare physical experiments against loopback results as though they are the same population.

### L4 — Live-model comparative experiments

Once real worker/model telemetry is available, compare configurations on the same frozen workload:

- single local worker;
- N local workers;
- heterogeneous workers;
- local + permitted cloud worker;
- dependency-pipeline workload;
- failure/reassignment injection.

Hold requirements, checks, source revision, models, model parameters, and budgets constant where the experiment requires direct comparison.

Report:

- successful integrations;
- provider calls;
- input/output/cached tokens;
- request bytes;
- cost when sourced from authoritative pricing/receipts;
- p50/p95 task and workflow latency;
- worker utilization;
- retries;
- verifier failures;
- repair attempts;
- deterministic integration tail.

## Mission Control commands

Mission Control recognizes a typed slash-command vocabulary before ordinary mission submission.

Useful commands:

```text
/help
/status
/tab chat
/tab activity
/tab evidence
/tab files
/terminal
/mode build
/mode live
/mode audit
/budget 1
/budget 2
/budget 3
/model openai/gpt-5.4-nano
/tokens 1536
/new
/detach
/history
/clear
/stop
/restart
/connect
/mesh status
/experiment mesh
/experiment distributed
/experiment pipeline
```

The command parser is not a shell. Unknown commands remain inert and no slash command maps arbitrary chat text into terminal execution.

`/clear` clears browser-local transcript state only. It does not delete guest traces or artifacts.

`/mesh status` is truthful about the browser lab boundary. Unless the Mission Control host supplies a future native mesh bridge, the browser guest reports that it is not attached to a native multi-device mesh.

## MeshSession boundary

`MeshSession` currently provides an experiment-grade in-process room coordinator:

- explicit membership;
- peer admission;
- verified history catch-up;
- signed fanout;
- delivery receipts;
- convergence/degraded status.

It deliberately refuses to choose a winner when member heads diverge. This is not a consensus protocol.

A future networked implementation should preserve the `MeshSession` contract while moving delivery behind a transport/provider interface.

## Required retained evidence

CI retains:

- mesh experiment JSON;
- independent distributed-worker experiment JSON;
- dependency-pipeline experiment JSON.

Timing measurements are development evidence from a shared CI environment. Correctness/integrity assertions are qualification gates; raw speedup is evidence to inspect, not a flaky pass/fail threshold.

## Next experiments

Useful next steps after the loopback suite is stable:

1. cancellation during provider work;
2. worker death after claim but before result;
3. worker death during result submission;
4. heartbeat/lease expiry and deterministic reassignment;
5. one slow/straggling worker among fast workers;
6. heterogeneous model/capability routing;
7. large mesh backlog catch-up;
8. fanout under delayed/duplicated/reordered delivery;
9. Station ↔ native `MeshSession` event bridge;
10. Mission Control native mesh status/room membership bridge;
11. physical two-host and four-host workload measurements;
12. live-model quality/cost comparison.

Any experiment involving failures must retain the first authoritative failure and must not rerun merely to obtain a green sample.


## Recovery benchmark

Fail-closed repair overhead can be measured independently:

```bash
residual experiment recovery \
  --bad-ms 20 \
  --good-ms 40 \
  --repeats 3 \
  --output runs/recovery.json
```

The first remote worker submits a real verifier-failing candidate. The Station retains the failure as repair context, a healthy worker reclaims the `repair_required` task, and normal review/integration must still complete. This measures verifier-driven repair overhead; it does not simulate process death or lease expiry.

## Station ↔ mesh observability bridge

The experimental `StationMeshBridge` mirrors Station workflow facts into a `MeshSession` as signed **inert chat summaries**. Verified peer chat may enter Station only as a `project.note`.

It cannot claim tasks, approve reviews, mutate candidates, or integrate code.

Bridge performance:

```bash
residual experiment bridge \
  --members 2 4 8 \
  --repeats 3 \
  --output runs/bridge.json
```

Measured values include event-mirroring latency, messages/s, replica-updates/s, peer-note round-trip latency, room convergence, and proof that Station task state remains unchanged by chat.

## Worker/latency experiment matrix

Use the matrix runner to determine where scaling stops being useful:

```bash
residual experiment matrix \
  --workers 1 2 4 \
  --latencies-ms 0 40 200 \
  --tasks 8 \
  --pipeline-width 4 \
  --pipeline-depth 2 \
  --repeats 3 \
  --output runs/matrix.json
```

The matrix composes independent-worker, dependency-pipeline, and optional recovery measurements over the same synthetic latency grid. It is intended to distinguish model-latency-bound behavior from control-plane/integration-bound behavior.

## Additional Mission Control console commands

Mission Control also supports direct typed controls:

```text
/worker status
/chat
/activity
/evidence
/files
/cancel
/experiment recovery
/experiment bridge
/experiment matrix
```

These remain typed UI/runtime operations. They do not expose arbitrary shell execution through chat.

## Evidence retained by the experiment workflow

The focused experiment workflow retains:

- `mesh-experiment.json`;
- `distributed-experiment.json`;
- `pipeline-experiment.json`;
- `recovery-experiment.json`;
- `bridge-experiment.json`.

Raw speedup is evidence, not a merge gate. Integrity, successful verification/integration, convergence, and authority preservation are gates.


## Lease-expiry recovery benchmark

To measure stale-worker rejection and recovery after a lost lease:

```bash
residual experiment lease-recovery \
  --work-ms 40 \
  --repeats 3 \
  --output runs/lease-recovery.json
```

The task is claimed through the real remote-worker API. The experiment then fault-injects only the passage of lease time by moving `lease_until` into the past. The normal Station recovery scan must:

1. emit `worker.expired` with the original worker label;
2. move the task to blocked;
3. reject a stale result carrying the old lease;
4. permit explicit re-triage;
5. allow a healthy remote worker to reclaim the task;
6. rerun verification, review and integration successfully.

This is stronger evidence than the verifier-failure recovery arm, but it still does not measure real process-kill detection time because the 15-minute lease interval is not waited in real time.

## Physical worker telemetry

Remote worker usage receipts now retain bounded worker-reported inference `elapsed_ms` in addition to model, placement, tokens and request bytes. The Station endpoint:

```text
GET /api/projects/<PROJECT_ID>/workers
```

aggregates by the existing `remote:<worker-name>` event actor:

- claim count;
- task IDs and attempt numbers;
- worker-reported input/output tokens;
- request bytes;
- inference latency count, median, p95 and total;
- attributed lease expirations.

These names are experiment labels authenticated only by the shared worker token. They are **not cryptographic node identities**.

Command Station Diagnostics displays the same telemetry table and repeats the identity warning.

For physical multi-host studies, combine worker-reported inference latency with Station workflow timestamps rather than treating either alone as end-to-end latency.


## Registered-worker completeness check

The independent distributed benchmark now verifies two different worker populations:

1. **requested/registered instances** — WorkerClient process instances that registered and polled the project;
2. **workers used** — labels that actually claimed one or more tasks.

A run with `--workers 4` must retain four registered instances even if scheduling causes fewer than four to win tasks. This prevents a benchmark from silently reporting a nominal four-worker configuration when fewer processes actually participated in the control plane.

The report also retains aggregate worker-reported inference elapsed time. This makes it possible to separate synthetic/provider work from Station coordination and integration time in the same experiment.

Mission Control exposes `/workers` as a typed registry query. In the browser lab it truthfully reports that no native Station registry is attached unless the host supplies a worker-metrics bridge.

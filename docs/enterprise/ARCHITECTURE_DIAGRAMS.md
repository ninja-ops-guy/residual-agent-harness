# Residual Agent Harness — Architecture Diagrams

**Version:** 1.0.0
**Date:** 2026-09-13
**Source:** https://github.com/ninja-ops-guy/residual-agent-harness
**Commit:** main (e3d4b9c)

---

## 1. System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESIDUAL AGENT HARNESS                               │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Human     │  │   Human     │  │   Human     │  │    Human            │ │
│  │  (Browser)  │  │  (Terminal) │  │  (Mobile)   │  │  (Observer Mode)    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                     │           │
│         ▼                ▼                ▼                     ▼           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    STATION SERVER (HTTP + WebSocket)                 │   │
│  │  residual/station/server.py (20K)  residual/station/static/        │   │
│  │  Serves: index.html, app.js (57K), style.css, scene.svg            │   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               │                                             │
│         ┌─────────────────────┼─────────────────────┐                       │
│         ▼                     ▼                     ▼                       │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐               │
│  │   Station   │       │   Station   │       │   Station   │               │
│  │  Service A  │       │  Service B  │       │  Service C  │               │
│  │ (residual/  │       │ (residual/  │       │ (residual/  │               │
│  │  station/   │       │  station/   │       │  station/   │               │
│  │  service.py)│       │  service.py)│       │  service.py)│               │
│  └──────┬──────┘       └──────┬──────┘       └──────┬──────┘               │
│         │                     │                     │                        │
│         └─────────────────────┼─────────────────────┘                        │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RESIDUAL CORE (Safety Kernel)                     │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ GoalSpec │→ │  Loop    │→ │Quarantine│→ │ Verifier │            │   │
│  │  │          │  │Controller│  │  Store   │  │          │            │   │
│  │  │goalspec.py│  │ loop.py  │  │quarantine│  │verifier.py│           │   │
│  │  │  (9K)    │  │  (11K)   │  │  (11K)   │  │  (4.8K)  │            │   │
│  │  └──────────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │                     │             │              │                   │   │
│  │                     ▼             ▼              ▼                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │  Brakes  │  │ Receipts │  │   HITL   │  │Extension │            │   │
│  │  │          │  │          │  │ Gateway  │  │ Registry │            │   │
│  │  │brakes.py │  │receipts.py│ │hitl/     │  │extensions│            │   │
│  │  │  (6.3K)  │  │  (6.9K)  │  │gateway.py│  │  (12K)   │            │   │
│  │  │          │  │          │  │  (6.1K)  │  │          │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │                                                                      │   │
│  │  Supporting: core.py (13K), engine.py (24K), providers.py (12K),   │   │
│  │  storage.py (2.4K), config.py (3.5K), modular.py (6.1K)            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                              │
│         ┌─────────────────────┼─────────────────────┐                        │
│         ▼                     ▼                     ▼                        │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐                │
│  │  ai_providers│       │  Operational │       │  Observation │               │
│  │  (Provider  │       │  Modules     │       │  Layer       │               │
│  │   Adapters) │       │              │       │              │               │
│  │             │       │  NetOps      │       │  Hash-chained│               │
│  │  Ollama     │       │  SecOps      │       │  event spine │               │
│  │  OpenAI     │       │  (modules/)  │       │  (observation│               │
│  │  Anthropic  │       │              │       │   _layer/)   │               │
│  │  Google     │       │  netops.py   │       │              │               │
│  │  Azure      │       │  (10K)       │       │  core.py     │               │
│  │  Bedrock    │       │              │       │  bus.py      │               │
│  │             │       │  secops.py   │       │  sinks.py    │               │
│  │  adapters/  │       │  (9.1K)      │       │  filters.py  │               │
│  │  (6 files)  │       │              │       │  hooks.py    │               │
│  └─────────────┘       └─────────────┘       └─────────────┘                │
│         │                     │                     │                        │
│         ▼                     ▼                     ▼                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MODEL LAYER                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │  Ollama  │  │  OpenAI  │  │ Anthropic│  │  Google  │            │   │
│  │  │ (Local)  │  │  (Cloud) │  │  (Cloud) │  │  (Cloud) │            │   │
│  │  │          │  │          │  │          │  │          │            │   │
│  │  │ llama3.3 │  │  gpt-4o  │  │claude-opus│ │ gemini-2.5│           │   │
│  │  │ qwen2.5  │  │          │  │          │  │          │            │   │
│  │  │ mistral  │  │          │  │          │  │          │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Supporting Tracks:                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │Trajectory│  │  Memory  │  │   TUI    │  │   Mesh   │                   │
│  │ recorder │  │  store   │  │ dashboard│  │   node   │                   │
│  │  (5.4K)  │  │  (5.1K)  │  │  (6.1K)  │  │  (9K)    │                   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                   │
│                                                                              │
│  Research:                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                                 │
│  │  Study   │  │Evaluation│  │   Demo   │                                 │
│  │  (29K)   │  │  (4.3K)  │  │  (6.4K)  │                                 │
│  └──────────┘  └──────────┘  └──────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow — Task Execution Pipeline

```
┌─────────────┐
│  Human      │  "Implement user authentication"
│  Intent     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   Station Service   │  Receives intent, creates task
│   (service.py)      │  Assigns task_id, goal_id
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│    GoalSpec         │  Frozen goal definition
│   (goalspec.py)     │  objective, success_criteria, budgets
│                     │  amendment_rule, schema_version
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   LoopController    │  Orchestrates execution passes
│    (loop.py)        │  while True: run_pass → verify → brakes
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐     ┌─────────────────────┐
│   ContextAssembly   │◄────│  Evidence Packet    │
│   (engine.py)       │     │  Compiler           │
│                     │     │  (engine.py _packet)│
│  Selects relevant   │     │                     │
│  context under      │     │  Fixed-window       │
│  token budget       │     │  seeding, merged    │
└──────┬──────────────┘     │  intervals, adaptive│
       │                    │  capsule heuristic  │
       │                    └─────────────────────┘
       ▼
┌─────────────────────┐
│   Provider Call     │  ai_providers.Router
│  (providers.py)     │  Selects engine, applies failover
│                     │  Local (Ollama) → Cloud escalation
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Proposed Action    │  Model output: tool calls, updates
│  (engine.py _parse) │  Parsed and validated
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐     ┌─────────────────────┐
│  QuarantineStore    │◄────│  Policy Evaluation  │
│  (quarantine.py)    │     │  (extensions.py)    │
│                     │     │                     │
│  hold() → evaluate()│     │  Module policies:   │
│  → release() or     │     │  - NetOps: maintenance│
│     deny()          │     │    window, topology │
│                     │     │  - SecOps: secrets, │
│  Denied: silent to  │     │    patterns, deps   │
│  agent, observed    │     │  - Custom: host     │
│  fully              │     │    registered       │
└──────┬──────────────┘     └─────────────────────┘
       │ (released)
       ▼
┌─────────────────────┐
│   Tool Execution    │  File writes, shell commands,
│   (engine.py)       │  API calls — sandboxed
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐     ┌─────────────────────┐
│   Verifier          │◄────│  Check Evaluation   │
│   (verifier.py)     │     │  (extensions.py)    │
│                     │     │                     │
│  Ordered checks:    │     │  Mechanical first:  │
│  1. Mechanical      │     │  - file exists      │
│  2. Structural      │     │  - test passes      │
│  3. Judge           │     │  - schema validates │
│                     │     │                     │
│  UNKNOWN never      │     │  Structural:        │
│  accepts            │     │  - format, sections │
│                     │     │                     │
│  Overall PASS =     │     │  Judge (last):      │
│  all PASS           │     │  - LLM evaluation   │
└──────┬──────────────┘     └─────────────────────┘
       │
       ▼
┌─────────────────────┐
│   Brakes            │  Four independent state machines
│   (brakes.py)       │  subscribing to observation bus
│                     │
│  MaxIteration ──────┼── pass_count >= max_passes → ESCALATE
│  Budget ────────────┼── tokens/wall-clock exceeded → ABORT
│  NoProgress ────────┼── same call repeated N times → ESCALATE
│  Completion ────────┼── all checks passed → CONTINUE
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   BrakeDecision     │  abort > escalate > continue
│   (loop.py _decide) │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   StationReceipt    │  Cryptographic proof of execution
│   (receipts.py)     │
│                     │  Binds: task_id, cache_key, value_hash,
│                     │  verifier_name, verifier_revision,
│                     │  verdict, parent_receipts
│                     │
│                     │  ReceiptReference for DAG parents
│                     │  (task_id + hash, not full objects)
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Observation Layer │  Hash-chained event spine
│   (observation_     │  Every event: obs_id, trace_id, kind,
│    layer/)          │  timestamp_ns, prev_hash, payload
│                     │
│  Sinks: JSONL file, │  Chain verification detects tampering
│  rotating, async,   │
│  fanout, memory     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Station Store     │  SQLite-backed durable state
│   (station/store.py)│  Tasks, receipts, observations
│                     │  Transactional, crash-safe
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Web UI Update     │  Real-time push to browser
│   (server.py +      │  Task status, receipts, observations
│    static/app.js)   │  Swarm panel, evidence view
└─────────────────────┘
```

---

## 3. Swarm Topology (Future — Studio Specs)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RESIDUAL STUDIO (Future)                             │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    ORCHESTRATOR (Layer 3)                            │   │
│  │                                                                      │   │
│  │  Intent → Spec Parser → Requirement DAG → Work Partitioner          │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │                    ┌─────────────────┐                               │   │
│  │                    │  Swarm A Spec   │── Backend implementation      │   │
│  │                    │  4 workers      │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                        │   │
│  │                    ┌────────┴────────┐                               │   │
│  │                    │  Swarm B Spec   │── Frontend implementation     │   │
│  │                    │  3 workers      │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                        │   │
│  │                    ┌────────┴────────┐                               │   │
│  │                    │  Swarm C Spec   │── Tests + adversarial QA      │   │
│  │                    │  3 workers      │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                        │   │
│  │                    ┌────────┴────────┐                               │   │
│  │                    │  Swarm D Spec   │── Security review             │   │
│  │                    │  2 workers      │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                        │   │
│  │                    ┌────────┴────────┐                               │   │
│  │                    │  Swarm E Spec   │── Integration verifier        │   │
│  │                    │  1 worker       │                               │   │
│  │                    └────────┬────────┘                               │   │
│  │                             │                                        │   │
│  │                              ▼                                       │   │
│  │                    ┌─────────────────┐                               │   │
│  │                    │  Merge Coordinator │── Deterministic integration │   │
│  │                    │  (Integration Receipt)│                            │   │
│  │                    └─────────────────┘                               │   │
│  │                              │                                       │   │
│  │                              ▼                                       │   │
│  │                    ┌─────────────────┐                               │   │
│  │                    │  Project Acceptance │── Human approval gate     │   │
│  │                    │  (HITL Challenge)   │                            │   │
│  │                    └─────────────────┘                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    EVIDENCE BUS (Layer 4)                            │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ Worker   │  │ Worker   │  │ Worker   │  │ Worker   │            │   │
│  │  │ Receipt  │  │ Receipt  │  │ Receipt  │  │ Receipt  │            │   │
│  │  │ AUTH-014 │  │ AUTH-015 │  │ AUTH-016 │  │ AUTH-017 │            │   │
│  │  │ ✓ tests  │  │ ✓ tests  │  │ ✗ tests  │  │ ✓ tests  │            │   │
│  │  │ ✓ types  │  │ ✓ types  │  │          │  │ ✓ types  │            │   │
│  │  │ ✓ contract│ │ ✓ contract│ │          │  │ ✓ contract│           │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │       │             │             │             │                   │   │
│  │       └─────────────┴─────────────┴─────────────┘                   │   │
│  │                         │                                           │   │
│  │                         ▼                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              Receipt Queue (append-only, hash-chained)       │   │   │
│  │  │                                                              │   │   │
│  │  │  Each receipt: task_id, engine, input_commit, outputs,      │   │   │
│  │  │  requirements satisfied, verification results, parent hashes │   │   │
│  │  │                                                              │   │   │
│  │  │  Integrators consume receipts, not raw outputs              │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              Artifact Store (content-addressed)              │   │   │
│  │  │                                                              │   │   │
│  │  │  sha256:abc123... → src/auth/session.py                     │   │   │
│  │  │  sha256:def456... → tests/auth/test_session.py              │   │   │
│  │  │  sha256:ghi789... → docs/auth/spec.md                       │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SWARM RUNTIME (Layer 4)                           │   │
│  │                                                                      │   │
│  │  Swarm A (Backend)          Swarm B (Frontend)                     │   │
│  │  ┌──────────────────┐       ┌──────────────────┐                   │   │
│  │  │ Coordinator      │       │ Coordinator      │                   │   │
│  │  │  ├─ assigns tasks│       │  ├─ assigns tasks│                   │   │
│  │  │  ├─ monitors     │       │  ├─ monitors     │                   │   │
│  │  │  └─ resizes      │       │  └─ resizes      │                   │   │
│  │  │     (dynamic)    │       │     (dynamic)    │                   │   │
│  │  ├──────────────────┤       ├──────────────────┤                   │   │
│  │  │ Worker 1         │       │ Worker 1         │                   │   │
│  │  │  contract:       │       │  contract:       │                   │   │
│  │  │  inputs: src/    │       │  inputs: src/    │                   │   │
│  │  │  outputs: src/   │       │  outputs: src/   │                   │   │
│  │  │  auth/           │       │  ui/             │                   │   │
│  │  │  forbidden: db/  │       │  forbidden: api/ │                   │   │
│  │  ├──────────────────┤       ├──────────────────┤                   │   │
│  │  │ Worker 2         │       │ Worker 2         │                   │   │
│  │  │ Worker 3         │       │ Worker 3         │                   │   │
│  │  │ Worker 4         │       │                  │                   │   │
│  │  ├──────────────────┤       ├──────────────────┤                   │   │
│  │  │ Verifier         │       │ Verifier         │                   │   │
│  │  │  unit_tests ✓    │       │  unit_tests ✓    │                   │   │
│  │  │  mypy ✓          │       │  mypy ✓          │                   │   │
│  │  │  contract ✓      │       │  contract ✓      │                   │   │
│  │  │  security ✓      │       │  security ✓      │                   │   │
│  │  ├──────────────────┤       ├──────────────────┤                   │   │
│  │  │ Critic           │       │ Critic           │                   │   │
│  │  │  (adversarial)   │       │  (adversarial)   │                   │   │
│  │  ├──────────────────┤       ├──────────────────┤                   │   │
│  │  │ Integrator       │       │ Integrator       │                   │   │
│  │  │  consumes        │       │  consumes        │                   │   │
│  │  │  receipts        │       │  receipts        │                   │   │
│  │  └──────────────────┘       └──────────────────┘                   │   │
│  │                                                                      │   │
│  │  Parallel Efficiency:                                                │   │
│  │  Workers active: 14 | Independent: 11 | Blocked: 3                  │   │
│  │  Serial estimate: 164min | Actual: 31min | Speedup: 5.29×           │   │
│  │  Coordination overhead: 12.4% | Rework: 4.1% | Rejection: 7.8%      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RESIDUAL CLUSTER (Layer 5)                        │   │
│  │                                                                      │   │
│  │  node-a (RTX 4090)    node-b (Mac Studio)    node-c (Homelab)      │   │
│  │  ├─ Qwen2.5-Coder-32B ├─ DeepSeek-V3        ├─ vision-model        │   │
│  │  │  48 tok/s           │  71 tok/s            │  12 tok/s           │   │
│  │  ├─ llama3.3-70b      ├─ qwen2.5-14b        │                      │   │
│  │  │  32 tok/s           │  89 tok/s            │                      │   │
│  │  │                     │                      │                      │   │
│  │  cloud-openai         cloud-anthropic                                 │   │
│  │  ├─ gpt-4o            ├─ claude-opus-4-1                             │   │
│  │  │  high reasoning    │  large context                               │   │
│  │  │                     │                                              │   │
│  │  Cluster Capacity: 5 GPUs | 11 Models | 32 Workers | 112 GB Memory   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    IDE (Layer 1)                                     │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │   │
│  │  │ Explorer │  │   Editor     │  │   Swarm Panel                │  │   │
│  │  │          │  │              │  │                              │  │   │
│  │  │ files    │  │ src/...      │  │  ● Planner                   │  │   │
│  │  │ specs    │  │              │  │  ● Backend x4  ████████░░ 78%│  │   │
│  │  │ proofs   │  │              │  │  ● Frontend x3 ██████░░░░ 62%│  │   │
│  │  │          │  │              │  │  ● Tests x3    ████████░░ 82%│  │   │
│  │  │          │  │              │  │  ● Security x2 ███████░░░ 71%│  │   │
│  │  │          │  │              │  │                              │  │   │
│  │  │          │  │              │  │  3 workers active            │  │   │
│  │  │          │  │              │  │  2 verifier retries          │  │   │
│  │  │          │  │              │  │  0 unresolved conflicts      │  │   │
│  │  └──────────┘  └──────────────┘  └──────────────────────────────┘  │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────┐  ┌───────┐  ┌──────────┐  ┌──────────┐    │   │
│  │  │ Terminal │  │ Graph│  │ Tests │  │ Evidence │  │ Telemetry│    │   │
│  │  └──────────┘  └──────┘  └───────┘  └──────────┘  └──────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Dependency Graph

```
residual/
│
├── core.py ──────────────────────────────────────────────────────────┐
│   ContractError, canonical, digest, identifier, positive_int        │
│                                                                      │
├── goalspec.py ◄─────────────────────────────────────────────────────┤
│   GoalSpec, SuccessCriterion, CheckType, AmendmentRule              │
│   Depends: core.py                                                   │
│                                                                      │
├── verifier.py ◄─────────────────────────────────────────────────────┤
│   Verifier, CheckResult, CriterionResult, VerificationReport        │
│   Depends: goalspec.py, core.py                                      │
│                                                                      │
├── brakes.py ◄───────────────────────────────────────────────────────┤
│   Brake, BrakeTrip, BrakeAction, 4 brake implementations            │
│   Depends: goalspec.py, core.py                                      │
│                                                                      │
├── quarantine.py ◄───────────────────────────────────────────────────┤
│   QuarantineStore, ProposedAction, Policy, PolicyDecision           │
│   Depends: core.py                                                   │
│                                                                      │
├── receipts.py ◄─────────────────────────────────────────────────────┤
│   StationReceipt, ReceiptReference, cache_key, validate_receipt_graph│
│   Depends: core.py, verifier.py (CheckResult)                        │
│                                                                      │
├── extensions.py ◄───────────────────────────────────────────────────┤
│   StationExtensionRegistry, StationModule, VerifierRevision         │
│   Depends: goalspec.py, verifier.py, brakes.py, quarantine.py       │
│                                                                      │
├── loop.py ◄─────────────────────────────────────────────────────────┤
│   LoopController, RunOutcome, RunResult, HarnessPass                │
│   Depends: goalspec.py, verifier.py, brakes.py, extensions.py       │
│                                                                      │
├── engine.py ◄───────────────────────────────────────────────────────┤
│   Harness, evidence packet compiler, provider dispatch              │
│   Depends: core.py, goalspec.py, providers.py, storage.py           │
│                                                                      │
├── providers.py ◄────────────────────────────────────────────────────┤
│   Provider, HTTPProvider, CallableProvider, StationProvider         │
│   Depends: core.py                                                   │
│                                                                      │
├── storage.py ◄──────────────────────────────────────────────────────┤
│   Ledger, hash-chained event storage                                │
│   Depends: core.py                                                   │
│                                                                      │
├── config.py ◄───────────────────────────────────────────────────────┤
│   Config, Limits, ProviderConfig                                    │
│   Depends: core.py                                                   │
│                                                                      │
├── modular.py ◄──────────────────────────────────────────────────────┤
│   Modular execution system                                          │
│   Depends: core.py, engine.py                                        │
│                                                                      │
├── integration.py ◄──────────────────────────────────────────────────┤
│   QuarantinedProvider, provider wrapping                            │
│   Depends: quarantine.py, providers.py                               │
│                                                                      │
├── cli.py ◄──────────────────────────────────────────────────────────┤
│   Command-line interface                                            │
│   Depends: engine.py, config.py                                      │
│                                                                      │
├── demo.py ◄─────────────────────────────────────────────────────────┤
│   Demo mode                                                         │
│   Depends: engine.py, config.py                                      │
│                                                                      │
├── evaluation.py ◄───────────────────────────────────────────────────┤
│   Evaluation harness                                                │
│   Depends: engine.py, study.py                                       │
│                                                                      │
├── study.py ◄────────────────────────────────────────────────────────┤
│   Research study framework (29K)                                    │
│   Depends: engine.py, evaluation.py, study_tasks.py                  │
│                                                                      │
├── study_tasks.py ◄──────────────────────────────────────────────────┤
│   Study task definitions (10K)                                      │
│   Depends: study.py                                                  │
│                                                                      │
│
├── hitl/ ────────────────────────────────────────────────────────────┤
│   ├── gateway.py — HITLEscalationGateway, HITLChallenge             │
│   │   Depends: goalspec.py, observation_layer                        │
│   └── __init__.py                                                   │
│                                                                      │
├── memory/ ──────────────────────────────────────────────────────────┤
│   ├── store.py — EpistemicMemoryStore, MemoryEntry                  │
│   │   Depends: core.py                                               │
│   └── __init__.py                                                   │
│                                                                      │
├── mesh/ ────────────────────────────────────────────────────────────┤
│   ├── node.py — MeshNode, MeshIdentity, MeshMessage, MeshChat       │
│   │   Depends: core.py, observation_layer                            │
│   └── __init__.py                                                   │
│                                                                      │
├── modules/ ─────────────────────────────────────────────────────────┤
│   ├── netops.py — NetOpsModule, TelemetryAnomalyBrake, etc.         │
│   │   Depends: brakes.py, quarantine.py, verifier.py, goalspec.py   │
│   ├── secops.py — SecOpsModule, VulnerabilityDeltaBrake, etc.       │
│   │   Depends: brakes.py, quarantine.py, verifier.py, goalspec.py   │
│   ├── adapters.py — Module adapters                                 │
│   │   Depends: extensions.py                                         │
│   └── __init__.py                                                   │
│                                                                      │
├── station/ ─────────────────────────────────────────────────────────┤
│   ├── service.py — StationService, task queue, batch execution      │
│   │   Depends: models.py, store.py, workspace.py, contracts.py      │
│   ├── models.py — Task, Mission, ModelCall, Review, Evidence        │
│   │   Depends: core.py, contracts.py                                 │
│   ├── store.py — StationStore, SQLite-backed state                  │
│   │   Depends: models.py, observation_layer                          │
│   ├── server.py — HTTP server, WebSocket, static files              │
│   │   Depends: service.py, store.py                                  │
│   ├── workspace.py — Git worktree isolation                         │
│   │   Depends: core.py                                               │
│   ├── contracts.py — Task contracts, obligation definitions         │
│   │   Depends: core.py                                               │
│   ├── worker.py — Worker process management                         │
│   │   Depends: service.py, models.py                                 │
│   ├── control.py — Run control, pause/resume                        │
│   │   Depends: service.py                                            │
│   ├── observability.py — Station event system                       │
│   │   Depends: observation_layer                                     │
│   ├── extensions.py — Station-specific extensions                   │
│   │   Depends: extensions.py                                         │
│   ├── schemas/ — JSON schemas for validation                        │
│   │   ldd-base.json, runtime.json, workflow-event.json              │
│   └── static/ — Web UI                                              │
│       index.html, app.js (57K), style.css, scene.svg, favicon.svg   │
│                                                                      │
├── trajectory/ ──────────────────────────────────────────────────────┤
│   ├── recorder.py — TrajectoryRecorder, TrajectoryRegressionEngine  │
│   │   Depends: core.py                                               │
│   └── __init__.py                                                   │
│                                                                      │
└── tui/ ─────────────────────────────────────────────────────────────┤
    ├── dashboard.py — StationTUI, ObservationCollector, DashboardState│
    │   Depends: observation_layer                                     │
    └── __init__.py                                                   │

ai_providers/ ────────────────────────────────────────────────────────┤
│   Separate package — provider-level adapters                        │
│   Depends: residual core (imported)                                  │
│                                                                      │
observation_layer/ ───────────────────────────────────────────────────┤
    Separate package — hash-chained event spine                       │
    Depends: nothing (foundation)                                      │
```

---

## 5. Data Flow — Receipt Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RECEIPT LIFECYCLE                                    │
│                                                                              │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│  │  Task    │────►│  Worker  │────►│ Verifier │────►│ Receipt  │          │
│  │ Proposed │     │ Executes │     │ Checks   │     │ Issued   │          │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘          │
│       │                │                │                │                  │
│       ▼                ▼                ▼                ▼                  │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐          │
│  │ cache_key│     │ value_   │     │ verdict  │     │ receipt_ │          │
│  │ computed │     │ hash of  │     │ pass/    │     │ hash =   │          │
│  │ from:    │     │ output   │     │ fail/    │     │ SHA-256  │          │
│  │ - task_id│     │          │     │ unknown  │     │ of all   │          │
│  │ - goal   │     │          │     │          │     │ fields   │          │
│  │ - contract│    │          │     │          │     │ + parent │          │
│  │ - verifier│    │          │     │          │     │ hashes   │          │
│  │ - revision│    │          │     │          │     │          │          │
│  │ - artifacts│   │          │     │          │     │          │          │
│  │ - parents │    │          │     │          │     │          │          │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘          │
│                                                          │                  │
│                          ┌───────────────────────────────┘                  │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RECEIPT GRAPH (DAG)                               │   │
│  │                                                                      │   │
│  │  Receipt A (root)                                                    │   │
│  │  ├── Receipt B (child of A)                                          │   │
│  │  │   ├── Receipt D (child of B)                                      │   │
│  │  │   └── Receipt E (child of B)                                      │   │
│  │  └── Receipt C (child of A)                                          │   │
│  │      └── Receipt F (child of C)                                      │   │
│  │                                                                      │   │
│  │  Validation:                                                         │   │
│  │  - No cycles (topological sort succeeds)                             │   │
│  │  - All parent hashes verify                                          │   │
│  │  - All cache keys deterministic                                      │   │
│  │  - All verifier revisions match active registry                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CACHE INVALIDATION                                │   │
│  │                                                                      │   │
│  │  When Receipt B's verifier_revision changes:                         │   │
│  │  - Receipt B's cache_key changes                                     │   │
│  │  - Receipt D's cache_key changes (parent hash changed)               │   │
│  │  - Receipt E's cache_key changes (parent hash changed)               │   │
│  │  - Receipt A's cache_key UNCHANGED (B is child, not parent)          │   │
│  │  - Receipt C's cache_key UNCHANGED (sibling, not descendant)         │   │
│  │  - Receipt F's cache_key UNCHANGED (nephew, not descendant)          │   │
│  │                                                                      │   │
│  │  Downward propagation only. Parents invalidate children.             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    INTEGRATION RECEIPT                               │   │
│  │                                                                      │   │
│  │  When all children complete:                                         │   │
│  │  - Integration Receipt binds all child receipt hashes                │   │
│  │  - Output commit hash recorded                                       │   │
│  │  - Project-level verification results recorded                       │   │
│  │  - This is the human-approvable artifact                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Security Boundary Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRUST BOUNDARIES                                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  UNTRUSTED ZONE                                                      │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │  Cloud   │  │  Cloud   │  │  Cloud   │  │  Engine  │            │   │
│  │  │  Model   │  │  Model   │  │  Model   │  │  Adapter │            │   │
│  │  │ (OpenAI) │  │(Anthropic)│  │ (Google) │  │(LangGraph)│           │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │   │
│  │       │             │             │             │                   │   │
│  │       └─────────────┴─────────────┴─────────────┘                   │   │
│  │                         │                                           │   │
│  │                         ▼                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              DISCLOSURE LATTICE ENFORCEMENT                  │   │   │
│  │  │                                                              │   │   │
│  │  │  An obligation may cross a remote boundary only if:          │   │   │
│  │  │  - The obligation permits it                                 │   │   │
│  │  │  - All its artifacts permit it                               │   │   │
│  │  │  - All transitive dependencies permit it                     │   │   │
│  │  │                                                              │   │   │
│  │  │  Violation → silent denial, observed fully                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  QUARANTINE ZONE                                                     │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              QuarantineStore                                   │   │   │
│  │  │                                                              │   │   │
│  │  │  Every proposed action enters here before execution.         │   │   │
│  │  │                                                              │   │   │
│  │  │  hold() → evaluate() → release() or deny()                   │   │   │
│  │  │                                                              │   │   │
│  │  │  Policies:                                                   │   │   │
│  │  │  - NetOps: maintenance window, topology permissions          │   │   │
│  │  │  - SecOps: secret exfiltration, dependency disclosure        │   │   │
│  │  │  - Custom: host-registered policies                          │   │   │
│  │  │                                                              │   │   │
│  │  │  Denied: silent to agent, observed fully                     │   │   │
│  │  │  The agent cannot retry around the denial.                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  VERIFICATION ZONE                                                   │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              Verifier                                         │   │   │
│  │  │                                                              │   │   │
│  │  │  Ordered checks:                                             │   │   │
│  │  │  1. Mechanical (deterministic)                               │   │   │
│  │  │  2. Structural (deterministic)                               │   │   │
│  │  │  3. Judge (LLM, last resort)                                 │   │   │
│  │  │                                                              │   │   │
│  │  │  UNKNOWN never accepts.                                      │   │   │
│  │  │  Evaluator exceptions → UNKNOWN, not FAIL.                   │   │   │
│  │  │  Host is sole acceptance authority.                          │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TRUSTED ZONE (Residual Core)                                        │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ GoalSpec │  │  Brakes  │  │ Receipts │  │Extension │            │   │
│  │  │ (frozen) │  │ (4 types)│  │ (hash-   │  │ Registry │            │   │
│  │  │          │  │          │  │  chained)│  │ (frozen  │            │   │
│  │  │          │  │          │  │          │  │  at      │            │   │
│  │  │          │  │          │  │          │  │  construct)│          │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │                                                                      │   │
│  │  Observation Layer: hash-chained, immutable, tamper-evident         │   │
│  │  HITL Gateway: SQLite-backed, replay prevention, host authenticator │   │
│  │  Station Store: SQLite, transactional, crash-safe                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                               │                                              │
│                               ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  HUMAN ZONE                                                          │   │
│  │                                                                      │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                           │   │
│  │  │  Web UI  │  │  HITL    │  │  Plan    │                           │   │
│  │  │ (Browser)│  │ Approval │  │ Approval │                           │   │
│  │  │          │  │ (Signed) │  │ (Modify) │                           │   │
│  │  └──────────┘  └──────────┘  └──────────┘                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. File Size Topology

```
residual/                          Total: ~290K LOC
│
├── Core Safety Kernel             ~95K
│   ├── engine.py          24K  ████████████████████████
│   ├── core.py            13K  █████████████
│   ├── extensions.py      12K  ████████████
│   ├── goalspec.py         9K  █████████
│   ├── loop.py            11K  ███████████
│   ├── quarantine.py      11K  ███████████
│   ├── providers.py       12K  ████████████
│   ├── receipts.py         7K  ███████
│   ├── brakes.py           6K  ██████
│   ├── verifier.py         5K  █████
│   ├── storage.py          2K  ██
│   └── config.py           3K  ███
│
├── Station (Web App)              ~135K
│   ├── service.py         29K  █████████████████████████████
│   ├── models.py          19K  ████████████████████
│   ├── server.py          20K  █████████████████████
│   ├── store.py           17K  ██████████████████
│   ├── static/app.js      57K  █████████████████████████████████████████████████
│   ├── static/style.css   24K  ████████████████████████
│   ├── workspace.py        9K  █████████
│   ├── contracts.py        8K  ████████
│   ├── observability.py    7K  ███████
│   ├── extensions.py       6K  ██████
│   ├── control.py          8K  ████████
│   ├── worker.py           6K  ██████
│   └── schemas/            3K  ███
│
├── Research                       ~50K
│   ├── study.py           30K  ███████████████████████████████
│   ├── study_tasks.py     10K  ██████████
│   ├── evaluation.py       4K  ████
│   └── modular.py          6K  ██████
│
├── Operational Modules            ~25K
│   ├── modules/netops.py  10K  ██████████
│   ├── modules/secops.py   9K  █████████
│   └── modules/adapters.py 4K  ████
│
├── Supporting Tracks              ~35K
│   ├── mesh/node.py        9K  █████████
│   ├── hitl/gateway.py     6K  ██████
│   ├── tui/dashboard.py    6K  ██████
│   ├── trajectory/         5K  █████
│   └── memory/store.py     5K  █████
│
├── CLI/Demo/Integration           ~15K
│   ├── cli.py              6K  ██████
│   ├── demo.py             6K  ██████
│   └── integration.py      3K  ███
│
ai_providers/                      ~35K
│   ├── adapters/ (6 files) 28K
│   ├── core.py             7K
│   └── router.py           6K
│
observation_layer/                 ~25K
│   ├── core.py             6K
│   ├── hooks.py            6K
│   ├── sinks.py            5K
│   ├── bus.py              2K
│   ├── filters.py          3K
│   └── query.py            4K
│
tests/                             ~180K
│   ├── test_harness.py    17K
│   ├── test_foundation.py 17K
│   ├── test_study.py      20K
│   ├── test_tracks_2_8.py 21K
│   ├── test_control_integrity.py 12K
│   ├── test_extension_integration.py 14K
│   ├── test_loop_layer.py 15K
│   ├── test_station.py    15K
│   ├── modular/           28K
│   └── browser.cjs        12K
│
vendor/                            ~15K
│   ├── ldd-kit/            7K
│   └── user-modules/       8K
│
docs/                              ~120K
│   ├── architecture.md     7K
│   ├── research.md         7K
│   ├── controlled-evaluation.md 10K
│   ├── station/           40K
│   ├── roadmap/           35K
│   └── study-qa/          15K
```

---

## 8. Deployment Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT OPTIONS                                   │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   Local Dev      │  │   Docker         │  │   Docker + GPU   │          │
│  │                  │  │                  │  │                  │          │
│  │  pip install     │  │  docker compose  │  │  docker compose  │          │
│  │  residual        │  │  up              │  │  -f compose.     │          │
│  │                  │  │                  │  │    nvidia.yaml   │          │
│  │  Ollama (local)  │  │  Ollama (local)  │  │  Ollama (GPU)    │          │
│  │  Station (local) │  │  Station (cont.) │  │  Station (cont.) │          │
│  │  Web UI :8080    │  │  Web UI :8080    │  │  Web UI :8080    │          │
│  │                  │  │                  │  │                  │          │
│  │  Use case:       │  │  Use case:       │  │  Use case:       │          │
│  │  Development     │  │  CI/CD           │  │  Production      │          │
│  │  Testing         │  │  Staging         │  │  GPU inference   │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐                                 │
│  │   Multi-Node     │  │   Cloud Burst    │                                 │
│  │                  │  │                  │                                 │
│  │  residual node   │  │  Local station   │                                 │
│  │  join (LAN)      │  │  + cloud APIs    │                                 │
│  │                  │  │                  │                                 │
│  │  Node A (GPU)    │  │  Ollama (local)  │                                 │
│  │  Node B (Mac)    │  │  OpenAI (cloud)  │                                 │
│  │  Node C (server) │  │  Anthropic (cloud)│                                │
│  │                  │  │                  │                                 │
│  │  Mesh discovery  │  │  Failover:       │                                 │
│  │  Task routing    │  │  local → cloud   │                                 │
│  │  Receipt exchange│  │  on 3 failures   │                                 │
│  │                  │  │                  │                                 │
│  │  Use case:       │  │  Use case:       │                                 │
│  │  Homelab cluster │  │  Cost optimization│                                │
│  │  Office network  │  │  Reliability     │                                 │
│  └──────────────────┘  └──────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

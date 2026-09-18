# RESIDUAL architecture diagrams

**Status:** non-normative architecture view
**Validated against:** `main@260b5f9e20bf70a6b9ca087bc91e22a009ed77b9`

These diagrams describe implemented boundaries without turning implementation into release or production qualification. Exact current claims remain in [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md). Historical specifications do not override current code or retained qualification evidence.

## 1. Repository-wide topology

```mermaid
flowchart TB
  Human["Operator"]
  subgraph Surfaces["Operator surfaces"]
    CLI["Core CLI"]
    StationUI["Command Station<br/>local web UI / API"]
    MC["Mission Control<br/>browser UI"]
  end
  subgraph Core["Core harness authority"]
    DAG["Obligation DAG / ready frontier"]
    Provider["Provider routing"]
    Verify["Host verifier"]
    Receipt["Accepted values + receipts"]
  end
  subgraph Station["Station authority"]
    Queue["Transactional queue / leases / budgets"]
    Worktree["Isolated Git worktrees"]
    Checks["Project checks + revision-bound review"]
    Integrate["Integration checks + accepted project state"]
    LDD["LDD events / usage receipts / diagnostics"]
  end
  subgraph Factory["Factory M2 / M3 / M4"]
    Contract["M2 worker contracts + bounded runtime"]
    Evidence["M3 evidence bus + Station receipts"]
    M4["M4 deterministic integration / scheduler"]
    Sandbox["Linux OS-isolated candidate checks<br/>when required capabilities are available"]
  end
  subgraph Browser["Browser demo path"]
    WebVM["WebVM guest / workbench"]
    Bridge["Mission Control provider bridge"]
    Puter["Puter authorization / model service<br/>external to RESIDUAL"]
  end
  Eval["Evaluation / research<br/>observes retained evidence; no merge authority"]

  Human --> CLI
  Human --> StationUI
  Human --> MC
  CLI --> DAG --> Provider --> Verify
  Verify -->|PASS| Receipt --> DAG
  Verify -->|FAIL / UNKNOWN| DAG
  StationUI --> Queue --> Worktree --> Checks --> Integrate
  Integrate -->|PASS| Queue
  Queue --> LDD
  Checks --> LDD
  Integrate --> LDD
  MC --> WebVM --> Bridge --> Puter
  Bridge --> WebVM
  Queue -. bounded worker work .-> Contract --> Evidence --> M4
  M4 --> Sandbox --> M4
  LDD -. retained evidence .-> Eval
  Evidence -. retained evidence .-> Eval
```

**Important:** the core harness, Command Station, Factory, and Mission Control are related surfaces, not one monolithic linear pipeline. A model/provider proposes work; host-owned checks and integration boundaries decide what becomes accepted state.

## 2. Core obligation acceptance flow

```mermaid
flowchart LR
  T["Host-authored obligation contract"] --> F["Ready unresolved frontier"]
  F --> P["Cached / local / remote proposal"]
  P --> V{"Host verifier"}
  V -->|PASS| A["Accepted value + receipt"]
  A --> F
  V -->|FAIL| C["Counterexample / bounded repair context"]
  V -->|UNKNOWN / malformed / provider error| N["No acceptance"]
  C --> F
  N --> F
```

`FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider errors, and abstention do not become acceptance.

## 3. Command Station task lifecycle

```mermaid
flowchart TD
  S["Specification / operator intent"] --> T["Triage"]
  T --> Q["Transactional task queue"]
  Q --> W["Fresh isolated worktree"]
  W --> R["Runner candidate"]
  R --> C{"Declared project checks"}
  C -->|FAIL| B["Bounded previous-candidate repair context"]
  B --> Q
  C -->|PASS| RV{"Revision-bound review"}
  RV -->|deny / findings| Q
  RV -->|approve| I{"Integration checks"}
  I -->|FAIL| Q
  I -->|PASS| A["Accepted project state"]
  Q --> E["LDD event / usage evidence"]
  C --> E
  RV --> E
  I --> E
  A --> E
```

Merged #218 permits bounded repair context from the previous failed candidate's declared writable files, while the next attempt still starts from a clean baseline worktree. Workers do not gain review, verifier, receipt, integration, promotion, or Factory/M4 authority.

## 4. Factory M2 → M3 → M4 trust path

```mermaid
flowchart LR
  Spec["Compiled task / ready DAG"] --> M2["M2 WorkerContract<br/>scope · budget · writable paths"]
  M2 --> Runtime["Bounded worker runtime<br/>host-owned termination"]
  Runtime --> Cand["Candidate + observations"]
  Cand --> M3["M3 evidence bus / Station receipt"]
  M3 --> M4{"M4 deterministic integrator"}
  M4 -->|candidate-dependent checks| SB["Fresh Linux OS-isolated runner"]
  SB --> M4
  M4 -->|PASS + conflict policy satisfied| IR["Integration receipt / accepted integration"]
  M4 -->|FAIL / UNKNOWN / ERROR / unresolved conflict| Stop["No integration"]
```

The OS-isolated M4 path is capability- and environment-bound. A host that cannot satisfy the required namespace/sandbox prerequisites is `BLOCKED`/`UNKNOWN`, not silently qualified.

## 5. Mission Control / WebVM provider boundary

```mermaid
sequenceDiagram
  actor U as User
  participant MC as Mission Control
  participant VM as WebVM guest / workbench
  participant PB as Provider bridge
  participant P as Puter secure authorization / model service
  U->>MC: Start mission / connect provider
  MC->>VM: Dispatch bounded guest work
  U->>MC: Explicit connect gesture
  MC->>PB: Open / restore session-scoped provider channel
  PB->>P: Lazy SDK load + authorization
  P-->>PB: Provider response or error
  PB-->>VM: Validated protocol envelope
  VM-->>MC: Candidate / evidence / failure state
  Note over MC,P: Credentials remain outside the WebVM guest and RESIDUAL does not claim successful paid/live inference without retained candidate→verifier→receipt evidence.
```

Detected iOS/iPadOS WebKit is routed to the lightweight walkthrough before heavyweight WebVM boot under the accepted #186 fallback. That fallback is not proof of heavyweight WebVM reliability on physical iPhone Safari.

## 6. Evidence and authority boundary

```mermaid
flowchart TB
  Model["Model / worker output<br/>untrusted proposal"] --> Checks{"Host checks / verifier"}
  Checks -->|PASS| Review["Review / integration policy<br/>where applicable"]
  Checks -->|FAIL / UNKNOWN| Reject["Rejected / unresolved"]
  Review -->|authorized| Accepted["Accepted state"]
  Review -->|not authorized| Reject
  Accepted --> Receipts["Receipts / event evidence"]
  Reject --> Evidence["Retained failure / diagnostic evidence"]
  Receipts --> Eval["Evaluation / reporting"]
  Evidence --> Eval
  Eval -. no acceptance authority .-> Checks
```

Receipts and hash chains provide provenance/integrity evidence under their stated contracts. They are not signatures of arbitrary truth, proof that a model is correct, or blanket production certification.

## 7. Deployment shapes actually represented in the repository

```mermaid
flowchart LR
  subgraph Native["Native local"]
    N1["Python 3.11+ / Git"] --> N2["setup.sh or direct module invocation"] --> N3["Station bound to loopback"]
  end
  subgraph Docker["Docker local"]
    D1["Docker / Compose"] --> D2["Station container"] --> D3["Loopback-published UI"]
  end
  subgraph BrowserDemo["Public browser demo"]
    B1["GitHub Pages"] --> B2["Guided proof"]
    B1 --> B3["Interactive WebVM lab"]
    B3 --> B4["Mission Control provider boundary"]
  end
  Remote["Optional remote inference workers / provider APIs"]
  N3 -. configured .-> Remote
  D3 -. configured .-> Remote
```

These are architecture shapes, not production-readiness claims. Blank-environment installation, host-loss recovery, elapsed soak, physical-device heavyweight WebVM reliability, and successful exact-current-main paid/live provider execution remain separate qualification questions.

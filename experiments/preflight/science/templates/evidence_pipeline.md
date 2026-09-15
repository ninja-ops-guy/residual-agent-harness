# Evidence pipeline (architecture template; no execution claimed)

```mermaid
flowchart TD
  W["Frozen workload cell"] --> P["Execution plan"]
  P --> C["Worker contract"]
  C --> R["Worker receipts and candidate tree"]
  V["Verifier revision and policy"] --> E["Verification outputs"]
  R --> E
  E --> I["Integration receipt and accepted tree"]
  I --> B["Retained artifact bundle"]
  W --> B
  B --> M["Offline metrics and claim ledger"]
```

Every arrow is a required hash-bound reference to audit, not proof of an
implemented edge. Independent grades and the externally retained bundle digest
must accompany the reconstruction. Metrics do not write accepted state.

# M6-SPEC-007S Preregistration — Registry/Receipt Binding Controls

## Question

Does a discovery admission receipt remain context-specific when metric semantics change without changing the metric ID?

## Controls

Create one StationReceipt using the active Metric Registry binding, then prospectively alter the semantic definition of `mean_wall_clock_s` while keeping its metric ID and registry revision string unchanged.

Required results:

1. baseline receipt matches its original proposal/context;
2. altered semantics change the registry content hash;
3. altered semantics change admission cache-key binding;
4. altered semantics change verifier-revision binding;
5. the old receipt does not match the altered registry context;
6. direct EvidenceSnapshot registry-hash tampering is rejected;
7. unit mismatch is rejected.

## Authority

This is deterministic negative-control work. It cannot register a metric, authorize a candidate, or promote anything.

# Protocol package: non-claims

This directory contains the consolidated frozen R0–R5 experimental protocol
([r0-r5-consolidated.md](r0-r5-consolidated.md)) prepared from draft PRs #90
and #91 against merged main (`residual/eval_frozen` from #86, acceptance
binding from #103).

- It freezes **protocol and corpus bytes only**. No model call was made, no
  result was observed, and no performance, reliability, cost, or security
  claim is supported by anything here.
- The corpus manifest (`experiments/corpus/manifest.v1.json`) is validated by
  `scripts/check_corpus_manifest.py`, which fails closed on hash mismatch,
  split leakage, or missing provenance. A green check attests to manifest
  integrity only — not to experimental readiness.
- Confirmatory experiments remain blocked on the #108 protected-path repair
  (Lane 1) and Lane 4 evidence-path qualification, plus the live launch gates
  listed in the protocol.
- `demo/` files are untouched by this package.

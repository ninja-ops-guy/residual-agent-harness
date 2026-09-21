# Sample note (X-M1 remediation follow-up)

The committed sample `research/slm/bench/sample/control-bench-v0-sample.jsonl` was
regenerated on 2026-09-20 after the contamination-group re-key (X-M1) and
bench-version unification (X-m2). It now contains 12 items (WR 2, CC 2, ES 2,
REA 1, BD 1, FC 1, AM 2, SA 1) covering all 8 categories, with real digests
computed by `generate_bench.py:canonical_digest`. The full 24-item sample
exceeded the fix lane's transport limits; the authoritative pin is the
manifest `items_jsonl_sha256`
(`15937ec20ec314d0dd80c374a074893c95b43b00b69ae114330615d993c56cbd`) plus the
deterministic generator (rng_seed 20260920) — fresh-checkout reproduction was
independently verified in CD-XVAL-R2. Regenerate the full bench locally with:

    python research/slm/bench/generate_bench.py \
      --seed-dir research/slm/bench/seed \
      --out research/slm/bench/control-bench-v0.jsonl \
      --manifest research/slm/bench/control-bench-v0-manifest.json

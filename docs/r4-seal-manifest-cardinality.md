# R4 seal manifest cardinality invariant

Seal cardinality is derived exclusively from the immutable authoritative `SHA256SUMS`. A seal generator must not accept an expected count through arguments, configuration, templates, prompts, or secondary inventories.

The required invariant is:

```text
authoritative_entry_count =
  number of valid non-empty entries parsed directly from authoritative SHA256SUMS
```

Before sealing, `scripts/r4_seal_manifest.py` parses every non-empty manifest line, rejects invalid, unsafe, or duplicate entries, verifies each referenced file hash, and returns the derived count. The generator records that returned value as both `entry_count` and `entries_verified`.

After sealing, the verifier independently repeats the parse and hash verification from the authoritative manifest and rejects any mismatch with `SEAL.json`. It does not trust generator output or receive an expected cardinality.

Regression coverage changes the manifest inventory without changing code or configuration and proves that additions and removals automatically change the derived cardinality. It also proves that a recorded 44 against an authoritative 50 is rejected.

## R4.1 incident root cause

The refused v1 seal was not produced by a cardinality function. Its creation patch manually embedded `"entries_verified": 44` in `SEAL.json` and `PASS (44/44 entries)` in `SEAL.md`. The preceding verification ran `sha256sum -c` successfully but did not count its records. A later documentation lane trusted and repeated the sealed value instead of independently parsing the authoritative manifest.

No file-selection or filtering rule produced 44, so there is no genuine six-file exclusion set. The value happens to equal the first 44 lines of the lexically ordered 50-line manifest. Its six trailing entries are the four R4-G17 files plus root-level `preflight.json` and `prestate.json`; that positional coincidence is not evidence that those files were intentionally filtered.

The defect does not change candidate identity, authoritative evidence bytes, or their SHA-256 values. It corrupts derived seal metadata and therefore invalidates the seal's semantic integrity even though the seal artifact hashes correctly authenticate the erroneous content.

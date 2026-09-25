# SNYK-R4-02: runtime archive extraction authority

The pre-fix TAR.ZST path delegated extraction to GNU tar. In the digest-matched,
attacker-controlled archive abstraction, GNU tar created an outside-pointing
symlink; a subsequent extraction error left that authority intact. Astra's direct
audit reproduced this effect. Gemma's original run remains
`SUBAGENT_RESULT: INCOMPLETE`, not PASS or FAIL.

The pinned production manifest SHA-256 remains a separate trust boundary. These
fixtures deliberately supply a matching digest; they do not demonstrate a digest
bypass or remote control of the production manifest.

## Extraction contract

1. Download into a private temporary directory on the destination filesystem.
2. Check the entire download against the manifest SHA-256.
3. Require a supported, patched Python data-filter implementation, without an
   unfiltered fallback.
4. Extract into a fresh private runtime directory. TAR.ZST is decompressed with
   `zstd --decompress --stdout` and then uses the same Python TAR path as TAR.
5. Inspect all member paths and explicitly validate TAR symlink/hardlink targets.
   Recheck paths and link targets at extraction time, then invoke Python's data
   filter. ZIP keeps RESIDUAL's resolved-path containment validation and now
   explicitly rejects unsupported link/special metadata.
6. Validate the extracted tree for canonical confinement, supported file types,
   and hardlink counts restricted to the tree. Check the staged executable.
7. Rename the validated directory into the absent authoritative runtime path.
   Dispose of the private staging directory on extraction/validation failure.

The installer refuses an existing runtime directory or symlink, preserving its
contents. This intentionally does not implement in-place updates or a non-atomic
two-rename replacement of a running installation. A future update mechanism must
define its own atomic replacement and recovery contract. The final rename is on
one filesystem; concurrent hostile changes to the station root by another local
process are outside this archive-only boundary.

Member names use consistent conservative rules across platforms: absolute names,
parent components, backslashes, drive prefixes, and colon/stream spellings are
rejected. Confined relative TAR links remain supported. ZIP link metadata is
rejected because the ZIP extraction API does not implement equivalent native link
semantics. Ordinary duplicate members remain allowed, with the final member
winning inside the private destination. This is not classified as path escape.

## Python runtime support

Package metadata and the extraction guard require at least Python **3.11.13**,
**3.12.11**, **3.13.4**, or **3.14+**, including the data-filter capability. Use the
latest maintained security patch of a supported branch. These floors include the
June 2025 filter-bypass fixes; they are not a certification against every future
runtime vulnerability.

The filter API was backported to **3.11.4**. Modern Python 3.11 is supported. The
observed 3.11.0rc1 API failure was not evidence that Python 3.12 was the first safe
release; early stable 3.11 versions also lacked the API. Merely checking that the
API exists would admit versions predating subsequent security fixes.

Sources: [Python 3.11 tarfile API](https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractall),
[Python's June 2025 security releases](https://blog.python.org/2025/06/python-3134-31211-31113-31018-and-3923/).

## Evidence and regression strength

- `artifacts/security/r4-02/pre-fix/`: frozen report, 90-row matrix, fixture
  archives, source snapshot, observations, and SHA-256 freeze receipt.
- `artifacts/security/r4-02/post-fix/`: unchanged audit harness, post-fix matrix,
  qualification gate envelopes/logs, sensitivity evidence, and comparison receipt.
- `tests/security/test_r4_02_archive_authority.py`: benign TAR/TAR.ZST/ZIP,
  traversal, absolute paths, outside links, preexisting links, duplicate overwrite,
  rollback, post-validation, unavailable capability, and runtime-support checks.
- `scripts/security/r4_02_sensitivity.py`: isolated, source-hash-verified runs.
  Both original TAR.ZST authority tests fail on the frozen pre-fix implementation;
  removing explicit link validation or staging cleanup is independently detected.
  No mutation modifies the working product source.

The pre-fix and post-fix harness bytes are identical. Post-fix member rejections
may be stricter: names previously rewritten or treated literally are rejected,
and retained preexisting runtime links are not attributed to new archive authority.
The unsafe controls remain unsafe and demonstrably escape. No unsafe behavior is
introduced as a runtime fallback.

Qualification is bounded to the recorded local environment and affected gates.
It is not a full release qualification, a native Windows/macOS execution receipt,
an archive-resource-exhaustion guarantee, or a post-fix Snyk service scan.

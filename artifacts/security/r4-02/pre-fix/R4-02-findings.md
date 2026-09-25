# R4-02 archive extraction findings

**DISPOSITION: CONSTRAINED. FIX_REQUIRED: YES. SUBAGENT_RESULT: INCOMPLETE.**

The unchanged real extractor creates outside symlink authority in two digest-matched TAR.ZST fixtures. The symlink-only archive completes installation through the mocked start; the symlink-then-file archive raises but leaves the outside link behind. A follow-up authority probe writes through each link into the experiment’s outside directory. No real extraction itself wrote the outside marker or changed the outside sentinel in this matrix.

This is an **attacker-controlled archive abstraction**: the download and manifest are mocked to contain the same fixture SHA-256. Production’s pinned manifest digest remains a trust boundary. Exploitability is established for outside-authority creation after acceptance of malicious archive bytes, not for an attacker bypassing that digest. The production disposition is therefore CONSTRAINED, rather than a demonstrated unauthenticated production compromise.

## Measured environment and controls

- Python: `3.12.13 (main, May 10 2026, 19:30:01) [Clang 22.1.3 ]` via `/tmp/residual-r4-venv/bin/python`.
- Platform: `Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.35`.
- External tools: `tar (GNU tar) 1.34`; `*** zstd command line interface 64-bits v1.4.8, by Yann Collet ***`; no TAR_OPTIONS override.
- Project declaration: `requires-python = ">=3.11"`.
- Unchanged source: `/mnt/c/Users/jinis/residual-snyk-r4/residual/station/models.py`; SHA-256 `4e3f43e2998579b6f731b5ec43913b29397baec66c9a9b5d3aa553638b45817c`.
- Experiment root: `/tmp/r4-02-audit-o8042bk9`.
- 42 real cases, 42 paired unsafe controls, 3 unsupported ZIP hardlink fixtures, and 3 bad-digest controls: 90 result rows.
- All 3 real benign controls extract expected bytes and reach mocked start. All 3 bad-digest controls reject before creating the destination.
- All meaningful parent/absolute/nested/dot/preexisting-link unsafe controls write outside in every format. TAR link controls also create verified outside authority.
- TAR control uses `extractall(filter="fully_trusted")`; TAR.ZST control decompresses identical fixture bytes then uses the same fully-trusted TAR extractor.
- ZIP control deliberately joins raw member names and writes bytes without containment validation. It is a traversal control, not a claim that Python zipfile itself is unsafe or implements ZIP links.
- Duplicate overwrite is independently measured: `bin/ollama` ends as `second` for all formats. It stays inside the destination.
- Existing security suite: **36 passed**. Its absence-of-marker assertions do not detect the TAR.ZST symlink authority found here.

## Protection attribution and effects

- **TAR / PYTHON_RUNTIME:** Python `tarfile` with explicit `filter="data"` rejects parent, nested, dot, and outside-link members. Absolute member names are rewritten inside the destination. This is runtime protection invoked by RESIDUAL, not RESIDUAL-owned TAR member validation.
- **ZIP / RESIDUAL:** the resolved-member containment check rejects parent, nested, dot, absolute, and preexisting-symlink traversal. For Unix symlink metadata, Python `zipfile` creates a regular file. A later child member encounters a filesystem error; that is not an explicit RESIDUAL link rejection.
- **TAR.ZST / FILESYSTEM (external GNU tar):** actual argv is `tar --zstd -xf <archive> -C <dest>`. GNU tar rejects member names containing `..` and strips leading slashes. For tested hardlinks it strips target prefixes then fails to find a target; this is observed external-tool/path behavior, not a RESIDUAL link policy.
- **TAR.ZST / NONE for created symlink authority:** outside-pointing symlinks are retained. The later `Cannot open: Not a directory` error does not undo link creation. `authority_probe` confirms the outside write capability.
- **Preexisting links:** all real extractors block the attempted child write; the seeded link remains. Its later probe is not archive-created authority. The report records retained authority separately.
- **POSIX normalization:** backslashes and `C:` are literal name characters in these tests. Their confinement does not establish native Windows behavior.

## Exact real-versus-control matrix

`BLOCKED` means the attempted operation failed and observation found no new outside authority/write; it does not mean atomic rollback or absence of confined partial files. `OUTSIDE_WRITE_OCCURRED` below excludes deliberate post-extraction probes. For preexisting links, retained authority is separate. Every status is paired with filesystem observations in findings.json, not inferred solely from an exception.

| Format | Case | Real extractor | Unsafe control | Real protection/effect attribution |
|---|---|---|---|---|
| tar | benign | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | PYTHON_RUNTIME |
| tar | parent | BLOCKED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME |
| tar | absolute | ALLOWED_BUT_CONFINED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME |
| tar | nested | BLOCKED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME |
| tar | dot | BLOCKED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME |
| tar | backslash | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar | mixed | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar | drive | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar | symlink_alone | BLOCKED | OUTSIDE_AUTHORITY_CREATED | PYTHON_RUNTIME |
| tar | symlink_then_file | BLOCKED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME |
| tar | hardlink_absolute | BLOCKED | OUTSIDE_AUTHORITY_CREATED | PYTHON_RUNTIME |
| tar | hardlink_relative | BLOCKED | OUTSIDE_AUTHORITY_CREATED | PYTHON_RUNTIME |
| tar | hardlink_then_overwrite | BLOCKED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME |
| tar | existing_symlink | BLOCKED | OUTSIDE_WRITE_OCCURRED | PYTHON_RUNTIME; seeded authority retained |
| tar | duplicate | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | NONE; confined overwrite |
| zip | benign | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | RESIDUAL |
| zip | parent | BLOCKED | OUTSIDE_WRITE_OCCURRED | RESIDUAL |
| zip | absolute | BLOCKED | OUTSIDE_WRITE_OCCURRED | RESIDUAL |
| zip | nested | BLOCKED | OUTSIDE_WRITE_OCCURRED | RESIDUAL |
| zip | dot | BLOCKED | OUTSIDE_WRITE_OCCURRED | RESIDUAL |
| zip | backslash | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| zip | mixed | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| zip | drive | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| zip | symlink_alone | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | PYTHON_RUNTIME |
| zip | symlink_then_file | BLOCKED | BLOCKED | PYTHON_RUNTIME |
| zip | hardlink_absolute | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE | No native ZIP hardlink fixture |
| zip | hardlink_relative | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE | No native ZIP hardlink fixture |
| zip | hardlink_then_overwrite | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE | No native ZIP hardlink fixture |
| zip | existing_symlink | BLOCKED | OUTSIDE_WRITE_OCCURRED | RESIDUAL; seeded authority retained |
| zip | duplicate | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | NONE; confined overwrite |
| tar.zst | benign | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar.zst | parent | BLOCKED | OUTSIDE_WRITE_OCCURRED | FILESYSTEM |
| tar.zst | absolute | ALLOWED_BUT_CONFINED | OUTSIDE_WRITE_OCCURRED | FILESYSTEM |
| tar.zst | nested | BLOCKED | OUTSIDE_WRITE_OCCURRED | FILESYSTEM |
| tar.zst | dot | BLOCKED | OUTSIDE_WRITE_OCCURRED | FILESYSTEM |
| tar.zst | backslash | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar.zst | mixed | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar.zst | drive | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | FILESYSTEM |
| tar.zst | symlink_alone | OUTSIDE_AUTHORITY_CREATED | OUTSIDE_AUTHORITY_CREATED | NONE |
| tar.zst | symlink_then_file | OUTSIDE_AUTHORITY_CREATED | OUTSIDE_WRITE_OCCURRED | NONE |
| tar.zst | hardlink_absolute | BLOCKED | OUTSIDE_AUTHORITY_CREATED | FILESYSTEM |
| tar.zst | hardlink_relative | BLOCKED | OUTSIDE_AUTHORITY_CREATED | FILESYSTEM |
| tar.zst | hardlink_then_overwrite | BLOCKED | OUTSIDE_WRITE_OCCURRED | FILESYSTEM |
| tar.zst | existing_symlink | BLOCKED | OUTSIDE_WRITE_OCCURRED | FILESYSTEM; seeded authority retained |
| tar.zst | duplicate | ALLOWED_BUT_CONFINED | ALLOWED_BUT_CONFINED | NONE; confined overwrite |

The three additional bad-digest controls are all BLOCKED by RESIDUAL SHA-256 validation before extraction.

## Python support determination

**A — Yes.** Python added extraction filters to the 3.11 series in **3.11.4**. Modern 3.11 releases support the required API; Python 3.12 is not the first supporting release. [Official 3.11 tarfile documentation](https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractall).

**B — Yes, a runtime-policy correction is needed.** `>=3.11` admits early stable 3.11 versions that lack the API. A capability guard with an actionable failure, a maintained backport, and/or an appropriate supported-version floor should make the requirement explicit. Never silently fall back to unfiltered extraction. Feature availability alone is not a security patch guarantee: Python **3.11.13** fixed multiple extraction-filter bypasses. [Official 3.11.13 security release](https://www.python.org/downloads/release/python-31113/).

**C — Not exclusively the ancient rc1.** The reported 3.11.0rc1 environment predates filters, but stable 3.11.0–3.11.3 do too. That reported TypeError indicates unavailable API, not a tar escape or evidence that modern 3.11 is unsafe. These version conclusions are documentation-backed; this execution used only 3.12.13. **MINIMUM_SAFE_RUNTIME: UNKNOWN** for the full installer: a Python version floor cannot fix the separate GNU tar branch, and this finite audit does not certify every historical patch level.

## Errors, corrections, and interpretation

The initial nested traversal unsafe TAR control encountered FileExistsError because `a/` did not exist. The final fixture includes an explicit `a/` directory member for both real and unsafe runs; all nested unsafe controls now demonstrably escape. The final results supersede that initial fixture artifact. Unexpected control failures are not counted as successful protections.

Per-case exceptions and actual GNU tar return codes/stderr are preserved in findings.json. GNU tar hardlink tests report missing rewritten targets; the hardlink-then-overwrite test also leaves a confined regular file. ZIP symlink-then-file leaves the regular `link` file and raises NotADirectoryError; the manual ZIP control raises FileExistsError. None of these exceptions alone establishes containment.

Gemma exited 0 without producing a runner/report or executing tests; its log contains metadata/compaction warnings and a malformed tool-argument error. It is preserved as **SUBAGENT_RESULT: INCOMPLETE**, independently of this direct audit. Original logs remain in `/mnt/c/Users/jinis/residual-snyk-r4/artifacts/security/r4-02` as gemma-session.jsonl, gemma-final.txt, and gemma-stderr.txt.

## Required follow-up, not applied

FIX_REQUIRED is YES for the demonstrated TAR.ZST authority gap under the stated archive abstraction. A subsequent product change should enforce link-target containment consistently and address partial extraction state after failure. Separately reconcile the Python support declaration with the filter API and security patch requirements. This audit makes no product, configuration, or existing-test edits and creates no commits.

## Commands and evidence

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/c/Users/jinis/residual-snyk-r4 /tmp/residual-r4-venv/bin/python /tmp/residual-r4-gemma-lab/audit_archive.py > /tmp/residual-r4-gemma-lab/harness-run.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/c/Users/jinis/residual-snyk-r4 /tmp/residual-r4-venv/bin/python -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py > /tmp/residual-r4-gemma-lab/existing-tests.txt 2>&1
PYTHONDONTWRITEBYTECODE=1 /tmp/residual-r4-venv/bin/python /tmp/residual-r4-gemma-lab/write_report.py
```

Run the pytest command from the repository root; the harness imports the unchanged module via PYTHONPATH. The download mock prevents fixture network access. Only official documentation lookups used the network.

- `audit_archive.py`: complete executable fixture generator, real extractor harness, unsafe controls, bounded probes, and control assertions.
- `findings.json`: all 90 rows, fixture digests, paths, files, link identities, outside contents before/after probe, classification, protection attribution, exceptions, external commands/stderr.
- `disposition.json`: requested final fields, support determination, counts, and limitations.
- `harness-run.txt`: final successful harness output; `existing-tests.txt`: baseline test result.
- `write_report.py`: report renderer; `evidence-sha256.json`: evidence checksums and original Gemma-log hashes.
- `/tmp/r4-02-audit-o8042bk9`: exact generated fixture archives and per-mode observation JSON; root is retained for review.

## Limitations

- Attacker-controlled archive abstraction with matching mocked manifest digest; no production digest bypass established.
- Linux/WSL2 POSIX filesystem, CPython 3.12.13, GNU tar 1.34, zstd 1.4.8 only; no native Windows/macOS execution.
- Modern 3.11 support determined from official documentation, not a fresh 3.11 interpreter run. Reported 3.11.0rc1 failure not rerun here.
- Finite fixtures, not a proof against all archive constructions, races, resource exhaustion, or alternate GNU tar versions/options.
- ZIP hardlink fixtures unsupported; Unix ZIP symlink metadata tested, but zipfile and the ZIP unsafe control do not create symlinks.
- Existing links are intentionally seeded and recorded as retained authority, never as newly archive-created authority.
- binary/start are mocked; no actual runtime service or extracted executable is launched.
- Each mode reuses/reset the same paths for byte-identical absolute targets. JSON snapshots preserve mode-specific observations; final on-disk trees reflect the last mode.

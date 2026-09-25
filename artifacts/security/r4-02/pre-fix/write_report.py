"""Render the measured audit into a reviewer-facing report and disposition."""
import collections
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parent
REPO = Path('/mnt/c/Users/jinis/residual-snyk-r4')
data = json.loads((LAB/'findings.json').read_text())
meta, rows = data['metadata'], data['results']
real = [r for r in rows if r['mode'] == 'real']
assert len(real) == 42 and len(rows) == 90
assert all(data['checks'].values())
assert not any(r['outside_write'] for r in real)
assert [(r['format'], r['case']) for r in real if r['authority_created']] == [
    ('tar.zst', 'symlink_alone'), ('tar.zst', 'symlink_then_file')]
assert hashlib.sha256(Path(meta['source']).read_bytes()).hexdigest() == meta['source_sha256']

limitations = [
    'Attacker-controlled archive abstraction with matching mocked manifest digest; no production digest bypass established.',
    'Linux/WSL2 POSIX filesystem, CPython 3.12.13, GNU tar 1.34, zstd 1.4.8 only; no native Windows/macOS execution.',
    'Modern 3.11 support determined from official documentation, not a fresh 3.11 interpreter run. Reported 3.11.0rc1 failure not rerun here.',
    'Finite fixtures, not a proof against all archive constructions, races, resource exhaustion, or alternate GNU tar versions/options.',
    'ZIP hardlink fixtures unsupported; Unix ZIP symlink metadata tested, but zipfile and the ZIP unsafe control do not create symlinks.',
    'Existing links are intentionally seeded and recorded as retained authority, never as newly archive-created authority.',
    'binary/start are mocked; no actual runtime service or extracted executable is launched.',
    'Each mode reuses/reset the same paths for byte-identical absolute targets. JSON snapshots preserve mode-specific observations; final on-disk trees reflect the last mode.',
]
disposition = {
    'RUNTIME_TESTED': {k: meta[k] for k in ['python', 'python_executable', 'platform', 'tar', 'zstd']},
    'BENIGN_CONTROL': 'PASS: all three real extractors produce bin/ollama=fixture and reach mocked start.',
    'UNGUARDED_NEGATIVE_CONTROL': 'VERIFIED: parent/absolute/nested/dot/preexisting-symlink writes in all formats; TAR and decompressed TAR.ZST fully_trusted controls grant symlink/hardlink authority.',
    'REAL_EXTRACTOR_RESULT': '42 cases: no immediate extraction outside writes; two TAR.ZST cases create verified outside symlink authority. Three checksum-negative cases reject before destination creation.',
    'TRAVERSAL': 'parent/nested/dot BLOCKED in all real formats, with distinct protection layers.',
    'ABSOLUTE_PATH': 'TAR and TAR.ZST ALLOWED_BUT_CONFINED after leading slash stripping; ZIP BLOCKED by RESIDUAL.',
    'SYMLINK_ESCAPE': 'TAR.ZST symlink_alone and symlink_then_file OUTSIDE_AUTHORITY_CREATED, verified by bounded follow-up writes; TAR rejects; ZIP materializes regular files.',
    'HARDLINK_ESCAPE': 'No real outside hardlink authority in these fixtures. TAR filter rejects; GNU tar rewrites targets then fails lookup; ZIP UNSUPPORTED_FIXTURE.',
    'NORMALIZATION_VARIANTS': 'backslash/mixed/drive ALLOWED_BUT_CONFINED on POSIX. Native Windows semantics untested.',
    'DUPLICATE_MEMBER_OVERWRITE': 'Allowed in all formats: second member wins inside destination; separate from path escape.',
    'PROTECTION_LAYER': 'MIXED',
    'MINIMUM_SAFE_RUNTIME': 'UNKNOWN',
    'PYTHON_FILTER_API_FIRST_3_11_RELEASE': '3.11.4',
    'PYTHON_KNOWN_FILTER_SECURITY_FIX_RELEASE': '3.11.13 (documented 2025 fixes; not a universal minimum-safe guarantee)',
    'PYTHON_SUPPORT_A': 'YES: modern maintained 3.11 releases provide the data-filter API and behavior.',
    'PYTHON_SUPPORT_B': 'YES: reconcile >=3.11 with required filter capability/security patch level through a supported-runtime floor and/or explicit fail-closed capability guard or maintained backport. No change applied.',
    'PYTHON_SUPPORT_C': 'NO, not exclusively rc1: early stable 3.11.0-3.11.3 also precede filter support; absence causes failure, not an automatic unsafe fallback.',
    'DISPOSITION': 'CONSTRAINED',
    'ABSTRACTION_RESULT': 'EXPLOITABLE outside-authority creation in the attacker-controlled, digest-matched TAR.ZST abstraction.',
    'FIX_REQUIRED': 'YES',
    'FIX_SCOPE': 'TAR.ZST outside-link authority and residual state after failure; separately align runtime support policy. Product source unchanged.',
    'SUBAGENT_RESULT': 'INCOMPLETE',
    'LIMITATIONS': limitations,
    'classification_counts_real': dict(collections.Counter(r['classification'] for r in real)),
    'checks': data['checks'],
}
(LAB/'disposition.json').write_text(json.dumps(disposition, indent=2)+'\n')

lines = [
    '# R4-02 archive extraction findings', '',
    '**DISPOSITION: CONSTRAINED. FIX_REQUIRED: YES. SUBAGENT_RESULT: INCOMPLETE.**', '',
    'The unchanged real extractor creates outside symlink authority in two digest-matched TAR.ZST fixtures. '
    'The symlink-only archive completes installation through the mocked start; the symlink-then-file archive raises '
    'but leaves the outside link behind. A follow-up authority probe writes through each link into the experiment’s '
    'outside directory. No real extraction itself wrote the outside marker or changed the outside sentinel in this matrix.', '',
    'This is an **attacker-controlled archive abstraction**: the download and manifest are mocked to contain the '
    'same fixture SHA-256. Production’s pinned manifest digest remains a trust boundary. Exploitability is established '
    'for outside-authority creation after acceptance of malicious archive bytes, not for an attacker bypassing that digest. '
    'The production disposition is therefore CONSTRAINED, rather than a demonstrated unauthenticated production compromise.', '',
    '## Measured environment and controls', '',
    f"- Python: `{meta['python']}` via `{meta['python_executable']}`.",
    f"- Platform: `{meta['platform']}`.",
    f"- External tools: `{meta['tar']}`; `{meta['zstd']}`; no TAR_OPTIONS override.",
    f"- Project declaration: `requires-python = \"{meta['requires_python']}\"`.",
    f"- Unchanged source: `{meta['source']}`; SHA-256 `{meta['source_sha256']}`.",
    f"- Experiment root: `{meta['temp_root']}`.",
    '- 42 real cases, 42 paired unsafe controls, 3 unsupported ZIP hardlink fixtures, and 3 bad-digest controls: 90 result rows.',
    '- All 3 real benign controls extract expected bytes and reach mocked start. All 3 bad-digest controls reject before creating the destination.',
    '- All meaningful parent/absolute/nested/dot/preexisting-link unsafe controls write outside in every format. TAR link controls also create verified outside authority.',
    '- TAR control uses `extractall(filter="fully_trusted")`; TAR.ZST control decompresses identical fixture bytes then uses the same fully-trusted TAR extractor.',
    '- ZIP control deliberately joins raw member names and writes bytes without containment validation. It is a traversal control, not a claim that Python zipfile itself is unsafe or implements ZIP links.',
    '- Duplicate overwrite is independently measured: `bin/ollama` ends as `second` for all formats. It stays inside the destination.',
    '- Existing security suite: **36 passed**. Its absence-of-marker assertions do not detect the TAR.ZST symlink authority found here.', '',
    '## Protection attribution and effects', '',
    '- **TAR / PYTHON_RUNTIME:** Python `tarfile` with explicit `filter="data"` rejects parent, nested, dot, and outside-link members. Absolute member names are rewritten inside the destination. This is runtime protection invoked by RESIDUAL, not RESIDUAL-owned TAR member validation.',
    '- **ZIP / RESIDUAL:** the resolved-member containment check rejects parent, nested, dot, absolute, and preexisting-symlink traversal. For Unix symlink metadata, Python `zipfile` creates a regular file. A later child member encounters a filesystem error; that is not an explicit RESIDUAL link rejection.',
    '- **TAR.ZST / FILESYSTEM (external GNU tar):** actual argv is `tar --zstd -xf <archive> -C <dest>`. GNU tar rejects member names containing `..` and strips leading slashes. For tested hardlinks it strips target prefixes then fails to find a target; this is observed external-tool/path behavior, not a RESIDUAL link policy.',
    '- **TAR.ZST / NONE for created symlink authority:** outside-pointing symlinks are retained. The later `Cannot open: Not a directory` error does not undo link creation. `authority_probe` confirms the outside write capability.',
    '- **Preexisting links:** all real extractors block the attempted child write; the seeded link remains. Its later probe is not archive-created authority. The report records retained authority separately.',
    '- **POSIX normalization:** backslashes and `C:` are literal name characters in these tests. Their confinement does not establish native Windows behavior.', '',
    '## Exact real-versus-control matrix', '',
    '`BLOCKED` means the attempted operation failed and observation found no new outside authority/write; it does not mean atomic rollback or absence of confined partial files. '
    '`OUTSIDE_WRITE_OCCURRED` below excludes deliberate post-extraction probes. For preexisting links, retained authority is separate. '
    'Every status is paired with filesystem observations in findings.json, not inferred solely from an exception.', '',
    '| Format | Case | Real extractor | Unsafe control | Real protection/effect attribution |',
    '|---|---|---|---|---|',
]
for row in rows:
    if row['mode'] == 'unsupported':
        lines.append(f"| {row['format']} | {row['case']} | UNSUPPORTED_FIXTURE | UNSUPPORTED_FIXTURE | No native ZIP hardlink fixture |")
    elif row['mode'] == 'real':
        control = next(c for c in rows if c['format']==row['format'] and c['case']==row['case'] and c['mode']=='unguarded')
        note = row['protection_layer']
        if row['case']=='existing_symlink':
            note += '; seeded authority retained'
        if row['case']=='duplicate':
            note += '; confined overwrite'
        lines.append(f"| {row['format']} | {row['case']} | {row['classification']} | {control['classification']} | {note} |")
lines += ['', 'The three additional bad-digest controls are all BLOCKED by RESIDUAL SHA-256 validation before extraction.', '',
    '## Python support determination', '',
    '**A — Yes.** Python added extraction filters to the 3.11 series in **3.11.4**. Modern 3.11 releases support the required API; Python 3.12 is not the first supporting release. '
    '[Official 3.11 tarfile documentation](https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractall).', '',
    '**B — Yes, a runtime-policy correction is needed.** `>=3.11` admits early stable 3.11 versions that lack the API. '
    'A capability guard with an actionable failure, a maintained backport, and/or an appropriate supported-version floor should make the requirement explicit. '
    'Never silently fall back to unfiltered extraction. Feature availability alone is not a security patch guarantee: '
    'Python **3.11.13** fixed multiple extraction-filter bypasses. '
    '[Official 3.11.13 security release](https://www.python.org/downloads/release/python-31113/).', '',
    '**C — Not exclusively the ancient rc1.** The reported 3.11.0rc1 environment predates filters, but stable 3.11.0–3.11.3 do too. '
    'That reported TypeError indicates unavailable API, not a tar escape or evidence that modern 3.11 is unsafe. '
    'These version conclusions are documentation-backed; this execution used only 3.12.13. '
    '**MINIMUM_SAFE_RUNTIME: UNKNOWN** for the full installer: a Python version floor cannot fix the separate GNU tar branch, and this finite audit does not certify every historical patch level.', '',
    '## Errors, corrections, and interpretation', '',
    'The initial nested traversal unsafe TAR control encountered FileExistsError because `a/` did not exist. '
    'The final fixture includes an explicit `a/` directory member for both real and unsafe runs; all nested unsafe controls now demonstrably escape. '
    'The final results supersede that initial fixture artifact. Unexpected control failures are not counted as successful protections.', '',
    'Per-case exceptions and actual GNU tar return codes/stderr are preserved in findings.json. '
    'GNU tar hardlink tests report missing rewritten targets; the hardlink-then-overwrite test also leaves a confined regular file. '
    'ZIP symlink-then-file leaves the regular `link` file and raises NotADirectoryError; the manual ZIP control raises FileExistsError. '
    'None of these exceptions alone establishes containment.', '',
    'Gemma exited 0 without producing a runner/report or executing tests; its log contains metadata/compaction warnings '
    'and a malformed tool-argument error. It is preserved as **SUBAGENT_RESULT: INCOMPLETE**, independently of this direct audit. '
    f"Original logs remain in `{REPO/'artifacts/security/r4-02'}` as gemma-session.jsonl, gemma-final.txt, and gemma-stderr.txt.", '',
    '## Required follow-up, not applied', '',
    'FIX_REQUIRED is YES for the demonstrated TAR.ZST authority gap under the stated archive abstraction. '
    'A subsequent product change should enforce link-target containment consistently and address partial extraction state after failure. '
    'Separately reconcile the Python support declaration with the filter API and security patch requirements. '
    'This audit makes no product, configuration, or existing-test edits and creates no commits.', '',
    '## Commands and evidence', '', '```bash',
    meta['command']+' > /tmp/residual-r4-gemma-lab/harness-run.txt 2>&1',
    'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/c/Users/jinis/residual-snyk-r4 /tmp/residual-r4-venv/bin/python -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py > /tmp/residual-r4-gemma-lab/existing-tests.txt 2>&1',
    'PYTHONDONTWRITEBYTECODE=1 /tmp/residual-r4-venv/bin/python /tmp/residual-r4-gemma-lab/write_report.py',
    '```', '',
    'Run the pytest command from the repository root; the harness imports the unchanged module via PYTHONPATH. '
    'The download mock prevents fixture network access. Only official documentation lookups used the network.', '',
    '- `audit_archive.py`: complete executable fixture generator, real extractor harness, unsafe controls, bounded probes, and control assertions.',
    '- `findings.json`: all 90 rows, fixture digests, paths, files, link identities, outside contents before/after probe, classification, protection attribution, exceptions, external commands/stderr.',
    '- `disposition.json`: requested final fields, support determination, counts, and limitations.',
    '- `harness-run.txt`: final successful harness output; `existing-tests.txt`: baseline test result.',
    '- `write_report.py`: report renderer; `evidence-sha256.json`: evidence checksums and original Gemma-log hashes.',
    f"- `{meta['temp_root']}`: exact generated fixture archives and per-mode observation JSON; root is retained for review.", '',
    '## Limitations', '',
]
lines += ['- '+item for item in limitations]
(LAB/'R4-02-findings.md').write_text('\n'.join(lines)+'\n')
paths = [LAB/name for name in ['audit_archive.py', 'write_report.py', 'findings.json', 'disposition.json',
                              'R4-02-findings.md', 'harness-run.txt', 'existing-tests.txt']]
paths += [REPO/'artifacts/security/r4-02'/name for name in ['gemma-session.jsonl', 'gemma-final.txt', 'gemma-stderr.txt']]
(LAB/'evidence-sha256.json').write_text(json.dumps({str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, indent=2)+'\n')
print(json.dumps({'report': str(LAB/'R4-02-findings.md'), 'disposition': disposition['DISPOSITION'],
                  'counts': disposition['classification_counts_real'], 'source_unchanged': True}, indent=2))

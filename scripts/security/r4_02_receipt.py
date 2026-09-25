"""Bind R4-02 measurements to source bytes and, optionally, the committed tree."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'artifacts/security/r4-02'
SOURCE_FILES = ['residual/station/models.py', 'residual/station/archive.py', 'pyproject.toml',
                'tests/security/test_r4_02_archive_authority.py', 'scripts/security/r4_02_sensitivity.py',
                'scripts/security/r4_02_receipt.py', 'docs/security/SNYK_R4_02.md']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--committed', action='store_true')
    args = parser.parse_args()
    before = json.loads((BASE/'pre-fix/findings.json').read_text())
    after = json.loads((BASE/'post-fix/findings.json').read_text())
    frozen = json.loads((BASE/'pre-fix/freeze-receipt.json').read_text())
    assert all(digest(BASE/'pre-fix'/name) == value for name, value in frozen['sha256'].items())
    assert digest(BASE/'pre-fix/audit_archive.py') == digest(BASE/'post-fix/audit_archive.py')
    assert all(after['checks'].values())
    real = [r for r in after['results'] if r['mode']=='real']
    assert len(real)==42 and not any(r['outside_write'] or r['authority_created'] for r in real)
    sensitivity = json.loads((BASE/'post-fix/sensitivity/sensitivity.json').read_text())
    assert sensitivity['result']=='PASS'
    gates = {}
    for name in ['targeted', 'station-host', 'deterministic-native', 'active-workload', 'exact-wheel-isolated']:
        path = BASE/'post-fix'/(name+'.evidence.json')
        evidence = json.loads(path.read_text())
        if name != 'deterministic-native':
            assert evidence['result']=='PASS', (name, evidence['result'])
        for item, value in evidence['evidence'].items():
            assert digest(ROOT/item)==value
        gates[name] = {'result': evidence['result'], 'skip_count': evidence['skip_count'],
                       'envelope_sha256': digest(path)}
    matrix = []
    for prior in before['results']:
        if prior['mode'] not in ('real', 'unsupported'):
            continue
        current = next(r for r in after['results'] if (r['format'], r['case'], r['mode']) ==
                       (prior['format'], prior['case'], prior['mode']))
        matrix.append({'format': prior['format'], 'case': prior['case'],
                       'pre': prior['classification'], 'post': current['classification'],
                       'post_error': current.get('error'), 'pre_layer': prior.get('protection_layer'),
                       # The unchanged harness retains its historical branch-label
                       # attribution logic; correct attribution belongs here.
                       'post_layer': 'RESIDUAL explicit staging/member/link validation + Python data filter'
                         if prior['format'] in ('tar','tar.zst') else 'RESIDUAL ZIP path/type validation + staging',
                       'new_outside_authority': current.get('authority_created',False),
                       'outside_write_during_extraction': current.get('outside_write',False)})
    identity = {name: subprocess.check_output(['git','rev-parse',ref], cwd=ROOT, text=True).strip()
                for name, ref in [('HEAD','HEAD'), ('tree','HEAD^{tree}')]}
    hashes = {name: digest(ROOT/name) for name in SOURCE_FILES}
    if args.committed:
        for name, value in hashes.items():
            committed = subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
            assert hashlib.sha256(committed).hexdigest()==value, name
        previous = json.loads((BASE/'post-fix/receipt.json').read_text())
        assert previous['source_sha256']==hashes, 'tested candidate differs from committed source'
    receipt = {'schema': 'residual.security.r4-02.v1', 'DISPOSITION': 'FIXED',
        'QUALIFICATION': 'PASS' if all(g['result']=='PASS' for g in gates.values()) else 'BLOCKED',
        'R4_03_MAY_BEGIN': all(g['result']=='PASS' for g in gates.values()),
        'FIX_REQUIRED': 'NO (demonstrated bounded defect remediated)',
        'SUBAGENT_RESULT': 'INCOMPLETE', 'finding_author': 'Astra direct audit',
        'source': identity, 'committed_source_verified': args.committed, 'source_sha256': hashes,
        'pre_fix_frozen_unchanged': True, 'audit_harness_byte_identical': True,
        'pre_counts': dict(Counter(r['classification'] for r in before['results'] if r['mode']=='real')),
        'post_counts': dict(Counter(r['classification'] for r in real)), 'gates': gates,
        'sensitivity': sensitivity, 'matrix': matrix,
        'non_claims': [
            'Digest-matched attacker-controlled archive abstraction; production manifest boundary not bypassed.',
            'Local Linux/WSL2 Python 3.12.13 execution; no new native Windows/macOS or multi-interpreter receipt.',
            'Runtime floors include documented filter security fixes; not a universal minimum-safe-runtime guarantee.',
            'Existing runtime directories are refused unchanged; no in-place updater implemented.',
            'No full release qualification or post-fix Snyk scan claim; only the recorded affected gates.',
            'Frozen harness protection_layer labels describe pre-fix routing; use this matrix and product source for post-fix attribution.',
            'Gate envelopes record base HEAD plus dirty candidate; source hashes bind their tested bytes to this exact commit when committed_source_verified is true.',
        ]}
    name = 'commit-receipt.json' if args.committed else 'receipt.json'
    (BASE/'post-fix'/name).write_text(json.dumps(receipt,indent=2)+'\n')
    if not args.committed:
        lines = ['# R4-02 pre/post comparison', '',
                 'The demonstrated archive defect is fixed in the tested scope. Full deterministic qualification is BLOCKED on this host by existing M4 namespace mount failures; the retained gate envelope is FAIL. R4-03 must not begin.', '',
                 'Pre-fix: 2 outside-authority creations. Post-fix: 0 outside writes and 0 newly created outside authorities in 42 real cases.', '',
                 'The unsafe controls continue to escape. Both pre-fix TAR.ZST regressions fail on frozen source and pass on remediated source. Both semantic mutants are killed.', '',
                 'Gemma: **SUBAGENT_RESULT: INCOMPLETE**. Finding: **Astra direct audit**.', '',
                 'Historical protection labels in the byte-identical audit harness are superseded by the attribution below: TAR and TAR.ZST now use RESIDUAL explicit member/link checks plus the Python data filter, and all formats use disposable staging and post-validation.', '',
                 '| Format | Case | Pre-fix | Post-fix |', '|---|---|---|---|']
        lines += [f"| {r['format']} | {r['case']} | {r['pre']} | {r['post']} |" for r in matrix]
        (BASE/'post-fix/comparison.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'receipt': str(BASE/'post-fix'/name), 'source': identity,
                      'post_counts': receipt['post_counts'], 'committed': args.committed},indent=2))


if __name__=='__main__':
    main()

"""Prove R4-02 regressions detect frozen source and isolated semantic mutants."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TEST = 'tests/security/test_r4_02_archive_authority.py'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    models = (ROOT/'residual/station/models.py').read_text()
    archive = (ROOT/'residual/station/archive.py').read_text()
    frozen = ROOT/'artifacts/security/r4-02/pre-fix/models.py'
    no_links = archive[:archive.index('def validate_link(')] + 'def validate_link(member, root):\n    return\n\n\n' + archive[archive.index('def extract_tar('):]
    cleanup_site = 'with tempfile.TemporaryDirectory(prefix=".runtime-install-", dir=self.store.root) as temporary:'
    assert models.count(cleanup_site) == 1
    no_cleanup = models.replace(cleanup_site,
        'with __import__("contextlib").nullcontext(tempfile.mkdtemp(prefix=".runtime-install-", dir=self.store.root)) as temporary:')
    cases = [
        ('pre-fix-negative-control', 'R4_02_MODELS_SOURCE', frozen.read_text(),
         'test_tar_zst_never_creates_outside_authority', 2, 'outside symlink authority survived'),
        ('link-validation-removed', 'R4_02_ARCHIVE_SOURCE', no_links,
         'test_explicit_link_target_validation', 8, 'DID NOT RAISE'),
        ('staging-cleanup-removed', 'R4_02_MODELS_SOURCE', no_cleanup,
         'test_partial_extraction_rollback', 3, 'failed extraction retained staging'),
    ]
    results = []
    for name, variable, source, test, expected_failures, marker in cases:
        with tempfile.TemporaryDirectory(prefix='r4-02-mutant-', dir='/tmp') as temporary:
            candidate = Path(temporary)/'candidate.py'
            candidate.write_text(source)
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            junit = args.output_dir/(name+'.xml')
            command = [sys.executable, '-m', 'pytest', '-s', '-q', '-p', 'no:cacheprovider',
                       TEST+'::'+test, '--junitxml='+str(junit.resolve())]
            env = {**os.environ, variable: str(candidate), 'PYTHONDONTWRITEBYTECODE': '1',
                   'PYTHONPATH': str(ROOT), 'PYTHONPYCACHEPREFIX': str(Path(temporary)/'pycache')}
            proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
            log = proc.stdout+'\n[stderr]\n'+proc.stderr
            (args.output_dir/(name+'.log')).write_text(log)
            tests = list(ET.parse(junit).getroot().iter('testcase')) if junit.exists() else []
            failures = sum(t.find('failure') is not None for t in tests)
            errors = sum(t.find('error') is not None for t in tests)
            killed = (proc.returncode == 1 and failures == expected_failures and not errors
                      and marker in log and str(candidate)+' '+digest in log)
            results.append({'name': name, 'result': 'KILLED' if killed else 'FAIL',
                            'command': command, 'returncode': proc.returncode, 'failures': failures,
                            'errors': errors, 'source_sha256': digest, 'loaded_source_verified': str(candidate)+' '+digest in log})
            (args.output_dir/(name+'-source.py')).write_text(source)
    result = {'result': 'PASS' if all(r['result']=='KILLED' for r in results) else 'FAIL',
              'SUBAGENT_RESULT': 'INCOMPLETE', 'finding_author': 'Astra direct audit', 'results': results}
    (args.output_dir/'sensitivity.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 0 if result['result']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

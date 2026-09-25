"""Local archive-authority audit; no product edits or network access.

Run with the exact command recorded in findings.json. All extraction destinations,
including deliberately unsafe negative controls, stay inside one new /tmp root.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from types import SimpleNamespace
from unittest.mock import Mock, patch
import warnings
import zipfile

from residual.station import models

LAB = Path(__file__).resolve().parent
SOURCE = Path(models.__file__).resolve()
SOURCE_HASH = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
assert not os.environ.get('TAR_OPTIONS'), 'Run without TAR_OPTIONS to isolate the product command'
ROOT = Path(tempfile.mkdtemp(prefix='r4-02-audit-', dir='/tmp'))
CASES = ['benign', 'parent', 'absolute', 'nested', 'dot', 'backslash',
         'mixed', 'drive', 'symlink_alone', 'symlink_then_file',
         'hardlink_absolute', 'hardlink_relative', 'hardlink_then_overwrite',
         'existing_symlink', 'duplicate']
ROWS = []


def fixture(kind, case, outside):
    names = {'parent': '../outside/marker', 'absolute': str(outside/'marker'),
             'nested': 'a/../../outside/marker', 'dot': './../outside/marker',
             'backslash': '..\\outside\\marker', 'mixed': 'a/..\\..\\outside/marker',
             'drive': 'C:/outside/marker', 'existing_symlink': 'link/marker'}
    members = [('file', names.get(case, 'bin/ollama'), b'fixture')]
    if case.startswith('symlink_'):
        members = [('symlink', 'link', str(outside))]
        if case == 'symlink_then_file':
            members.append(('file', 'link/marker', b'fixture'))
    if case.startswith('hardlink_'):
        target = '../outside/source' if case == 'hardlink_relative' else str(outside/'source')
        members = [('hardlink', 'marker', target)]
        if case == 'hardlink_then_overwrite':
            members.append(('file', 'marker', b'overwrite'))
    if case == 'duplicate':
        members = [('file', 'bin/ollama', b'first'), ('file', 'bin/ollama', b'second')]
    if case == 'nested':
        members.insert(0, ('directory', 'a/', b''))
    buf = io.BytesIO()
    if kind == 'zip':
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(buf, 'w') as archive:
                for typ, name, value in members:
                    item = zipfile.ZipInfo(name)
                    item.create_system = 3
                    item.external_attr = ((0o120777 if typ == 'symlink' else 0o100644) << 16)
                    archive.writestr(item, value)
    else:
        with tarfile.open(fileobj=buf, mode='w') as archive:
            for typ, name, value in members:
                item = tarfile.TarInfo(name)
                if typ == 'directory':
                    item.type = tarfile.DIRTYPE
                    archive.addfile(item)
                elif typ == 'file':
                    item.size = len(value)
                    archive.addfile(item, io.BytesIO(value))
                else:
                    item.type = tarfile.SYMTYPE if typ == 'symlink' else tarfile.LNKTYPE
                    item.linkname = value
                    archive.addfile(item)
    raw = buf.getvalue()
    if kind == 'tar.zst':
        return subprocess.run(['zstd', '-q', '-c'], input=raw, capture_output=True, check=True).stdout
    return raw


def observe(dest, outside):
    links, files, authorities = [], {}, []
    for base, dirs, names in os.walk(dest, followlinks=False):
        for name in dirs + names:
            p = Path(base)/name
            rel = str(p.relative_to(dest))
            if p.is_symlink():
                resolved = p.resolve()
                assert resolved.is_relative_to(ROOT), resolved
                links.append({'path': rel, 'target': os.readlink(p),
                              'outside_dest': not resolved.is_relative_to(dest)})
                if not resolved.is_relative_to(dest):
                    authorities.append({'path': rel, 'kind': 'symlink'})
            elif p.is_file():
                files[rel] = p.read_bytes().decode('utf-8', errors='replace')
                if p.samefile(outside/'source'):
                    authorities.append({'path': rel, 'kind': 'hardlink'})
    before = {p.name: p.read_text() for p in outside.iterdir() if p.is_file()}
    probes = []
    for authority in authorities:
        p = dest/authority['path']
        target = p/'authority_probe' if p.is_dir() else p
        assert target.resolve().is_relative_to(ROOT)
        target.write_text('authority-probe')
        verified = ((outside/'source').read_text() == 'authority-probe' if authority['kind'] == 'hardlink'
                    else (outside/'authority_probe').read_text() == 'authority-probe')
        probes.append({'path': authority['path'], 'target': str(target.resolve()), 'verified': verified})
    after = {p.name: p.read_text() for p in outside.iterdir() if p.is_file()}
    return {'outside_before_probe': before, 'outside_write': before != {'source': 'original'},
            'links': links, 'outside_authority': authorities, 'authority_probes': probes,
            'outside_after_probe': after, 'files': files, 'dest_exists': dest.exists()}


def run(kind, case, mode, root, raw):
    dest, outside = root/'runtime', root/'outside'
    for p in (dest, outside, root/'runtime-download'):
        if p.exists():
            shutil.rmtree(p)
    outside.mkdir()
    (outside/'source').write_text('original')
    if case == 'existing_symlink':
        dest.mkdir()
        (dest/'link').symlink_to(outside, target_is_directory=True)
    error, returned, start_calls = None, None, 0
    external_commands = []
    original_run = subprocess.run
    def record_run(*args, **kwargs):
        result = original_run(*args, **kwargs)
        external_commands.append({'argv': args[0], 'returncode': result.returncode,
                                  'stderr': (result.stderr or b'').decode(errors='replace')})
        return result
    try:
        if mode == 'unguarded':
            dest.mkdir(exist_ok=True)
            if kind == 'zip':
                # ZIP has no fully_trusted filter. Deliberately unsafe manual
                # path join is a separate traversal control; no link emulation.
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    for item in archive.infolist():
                        p = dest/item.filename
                        assert p.resolve().is_relative_to(ROOT)
                        if item.is_dir():
                            p.mkdir(parents=True, exist_ok=True)
                            continue
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_bytes(archive.read(item))
            else:
                payload = raw
                if kind == 'tar.zst':
                    payload = subprocess.run(['zstd', '-q', '-d', '-c'], input=raw,
                                             capture_output=True, check=True).stdout
                with tarfile.open(fileobj=io.BytesIO(payload)) as archive:
                    archive.extractall(dest, filter='fully_trusted')
        else:
            manifest_dir = root/'module'/'schemas'
            manifest_dir.mkdir(parents=True, exist_ok=True)
            asset = {'name': 'fixture.'+kind, 'url': 'https://download.invalid/fixture',
                     'sha256': '0'*64 if mode == 'bad_digest' else hashlib.sha256(raw).hexdigest()}
            (manifest_dir/'runtime.json').write_text(json.dumps({'assets': {'Linux-amd64': asset}}))
            class Download(io.BytesIO):
                headers = {}
            installer = models.Ollama(SimpleNamespace(root=root))
            installer.binary = Mock(return_value='fixture')
            installer.start = Mock(return_value='started')
            with patch.object(models, '__file__', str(root/'module'/'models.py')), \
                 patch.object(models.platform, 'system', return_value='Linux'), \
                 patch.object(models.platform, 'machine', return_value='amd64'), \
                 patch.object(models.urllib.request, 'urlopen', side_effect=lambda *a, **k: Download(raw)), \
                 patch.object(models.subprocess, 'run', side_effect=record_run):
                returned = installer.install(lambda *a: None)
            start_calls = installer.start.call_count
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    result = {'format': kind, 'case': case, 'mode': mode, 'fixture_sha256': hashlib.sha256(raw).hexdigest(),
              'error': error, 'returned': returned, 'start_calls': start_calls,
              'preexisting_link': case == 'existing_symlink', 'external_commands': external_commands,
              **observe(dest, outside)}
    result['authority_created'] = bool(result['outside_authority']) and case != 'existing_symlink'
    if result['outside_write']:
        result['classification'] = 'OUTSIDE_WRITE_OCCURRED'
    elif result['authority_created']:
        result['classification'] = 'OUTSIDE_AUTHORITY_CREATED'
    elif error:
        result['classification'] = 'BLOCKED'
    else:
        result['classification'] = 'ALLOWED_BUT_CONFINED'
    if mode == 'bad_digest':
        layer, detail = 'RESIDUAL', 'SHA-256 verification before extraction'
    elif mode == 'unguarded':
        layer, detail = 'NONE', 'Intentionally unsafe control'
        if error or case in ['backslash', 'mixed', 'drive'] or (kind == 'zip' and case.startswith('symlink_')):
            layer, detail = 'FILESYSTEM', 'POSIX path/file behavior; ZIP control does not emulate links'
    elif kind == 'tar':
        layer, detail = 'PYTHON_RUNTIME', 'Python tarfile data filter'
        if case in ['backslash', 'mixed', 'drive']:
            layer, detail = 'FILESYSTEM', 'POSIX treats backslashes and drive names literally'
    elif kind == 'zip':
        layer, detail = 'RESIDUAL', 'Resolved member path containment check'
        if case.startswith('symlink_'):
            layer, detail = 'PYTHON_RUNTIME', 'zipfile materializes link metadata as a regular file; child write hits ENOTDIR'
        elif case in ['backslash', 'mixed', 'drive']:
            layer, detail = 'FILESYSTEM', 'POSIX treats backslashes and drive names literally'
    else:
        layer, detail = 'FILESYSTEM', 'External GNU tar 1.34 --zstd -xf archive -C dest; see captured stderr'
        if result['authority_created']:
            layer, detail = 'NONE', 'GNU tar creates outside symlink; later error does not remove it'
    if case == 'duplicate':
        layer, detail = 'NONE', 'Duplicate overwrite allowed inside destination; not a path escape'
    result['protection_layer'] = layer
    result['protection_detail'] = detail
    ROWS.append(result)
    (root/('observation-'+mode+'.json')).write_text(json.dumps(result, indent=2)+'\n')


for kind in ['tar', 'zip', 'tar.zst']:
    for case in CASES:
        if kind == 'zip' and case.startswith('hardlink_'):
            ROWS.append({'format': kind, 'case': case, 'mode': 'unsupported',
                         'classification': 'UNSUPPORTED_FIXTURE',
                         'reason': 'No native ZIP hardlink fixture; not emulated as a regular file.'})
            continue
        root = ROOT/(kind+'-'+case)
        root.mkdir()
        raw = fixture(kind, case, root/'outside')
        (root/'fixture.archive').write_bytes(raw)
        for mode in ['real', 'unguarded']:
            run(kind, case, mode, root, raw)
        if case == 'parent':
            run(kind, case, 'bad_digest', root, raw)

real = [r for r in ROWS if r['mode'] == 'real']
checks = {
    'source_unchanged': hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_HASH,
    'paired_fixture_digests_identical': all(r['fixture_sha256'] == next(c['fixture_sha256'] for c in ROWS
        if c['format'] == r['format'] and c['case'] == r['case'] and c['mode'] == 'unguarded') for r in real),
    'benign_all_formats': all(r['files'].get('bin/ollama') == 'fixture' and r['returned'] == 'started'
                              for r in real if r['case'] == 'benign'),
    'negative_parent_controls_all_formats': all(r['outside_write'] for r in ROWS
                                                if r['mode'] == 'unguarded' and r['case'] == 'parent'),
    'negative_traversal_controls_all_formats': all(r['outside_write'] for r in ROWS
        if r['mode'] == 'unguarded' and r['case'] in ['parent', 'absolute', 'nested', 'dot', 'existing_symlink']),
    'negative_tar_link_controls': all(r['outside_authority'] for r in ROWS
        if r['mode'] == 'unguarded' and r['format'] != 'zip' and r['case'].startswith(('symlink_', 'hardlink_'))),
    'all_authority_probes_verified': all(p['verified'] for r in ROWS for p in r.get('authority_probes', [])),
    'duplicate_overwrite_confined': all(r['files'].get('bin/ollama') == 'second' and not r['outside_write']
        and not r['outside_authority'] for r in real if r['case'] == 'duplicate'),
    'bad_digest_all_formats': all(r['error'] and 'checksum mismatch' in r['error']['message']
                                  and not r['dest_exists'] and not r['outside_write']
                                  for r in ROWS if r['mode'] == 'bad_digest'),
}
metadata = {'python': sys.version, 'python_executable': sys.executable, 'platform': platform.platform(),
            'tar': subprocess.run(['tar', '--version'], capture_output=True, text=True).stdout.splitlines()[0],
            'zstd': subprocess.run(['zstd', '--version'], capture_output=True, text=True).stdout.strip(),
            'source': str(SOURCE), 'source_sha256': SOURCE_HASH,
            'requires_python': tomllib.loads((SOURCE.parents[2]/'pyproject.toml').read_text())['project']['requires-python'],
            'tar_options': os.environ.get('TAR_OPTIONS'), 'temp_root': str(ROOT),
            'command': 'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/mnt/c/Users/jinis/residual-snyk-r4 /tmp/residual-r4-venv/bin/python /tmp/residual-r4-gemma-lab/audit_archive.py'}
(LAB/'findings.json').write_text(json.dumps({'metadata': metadata, 'checks': checks, 'results': ROWS}, indent=2)+'\n')
print(json.dumps({'checks': checks, 'rows': len(ROWS), 'temp_root': str(ROOT), 'real_effects': [
    {'format': r['format'], 'case': r['case'], 'outside_write': r['outside_write'],
     'authority': r['outside_authority'], 'error': r['error']} for r in real
    if r['outside_write'] or r['outside_authority']]}, indent=2))
assert all(checks.values()), checks

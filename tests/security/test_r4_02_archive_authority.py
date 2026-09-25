"""Exercise the real Ollama installer with in-memory downloads and temporary roots."""
import hashlib
import io
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from residual.core import ContractError
from residual.station import models
from residual.station import archive as archive_security

# Negative-control/mutation runs load frozen bytes without editing product source.
if os.environ.get('R4_02_MODELS_SOURCE'):
    candidate = Path(os.environ['R4_02_MODELS_SOURCE'])
    spec = importlib.util.spec_from_file_location('r4_02_candidate', candidate)
    models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models)
    print('R4_02_MODELS_SOURCE', candidate, hashlib.sha256(candidate.read_bytes()).hexdigest())
if os.environ.get('R4_02_ARCHIVE_SOURCE'):
    candidate = Path(os.environ['R4_02_ARCHIVE_SOURCE'])
    spec = importlib.util.spec_from_file_location('r4_02_archive_candidate', candidate)
    archive_security = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(archive_security)
    for name in ('require_data_filter', 'extract_tar', 'extract_zip', 'validate_tree'):
        setattr(models, name, getattr(archive_security, name))
    print('R4_02_ARCHIVE_SOURCE', candidate, hashlib.sha256(candidate.read_bytes()).hexdigest())

CASES = ['parent','absolute','nested','symlink','hardlink','backslash','mixed','dot','drive','existing_symlink']

def archive_bytes(kind, case, outside):
    data=io.BytesIO()
    name={'parent':'../outside/marker', 'absolute':str(outside/'marker'),
          'nested':'a/../../outside/marker', 'backslash':'..\\outside\\marker',
          'mixed':'a/..\\..\\outside/marker', 'dot':'./../outside/marker',
          'drive':'C:/outside/marker',
          'symlink':'link/marker', 'hardlink':'marker', 'existing_symlink':'link/marker'}.get(case,'bin/ollama')
    if kind == 'zip':
        with zipfile.ZipFile(data,'w') as z:
            if case == 'symlink':
                i=zipfile.ZipInfo('link');i.external_attr=(0o120777 << 16);z.writestr(i,'../../outside')
            z.writestr(name,b'fixture')
    else:
        with tarfile.open(fileobj=data,mode='w') as t:
            if case == 'symlink':
                i=tarfile.TarInfo('link');i.type=tarfile.SYMTYPE;i.linkname=str(outside);t.addfile(i)
            i=tarfile.TarInfo(name)
            if case == 'hardlink':
                i.type=tarfile.LNKTYPE;i.linkname=str(outside/'source');t.addfile(i)
            else:
                i.size=7;t.addfile(i,io.BytesIO(b'fixture'))
    raw=data.getvalue()
    if kind=='tar.zst':
        raw=subprocess.run(['zstd','--compress','--stdout','--quiet'],input=raw,capture_output=True,check=True).stdout
    return raw


def setup_installer(tmp_path, monkeypatch, kind, case, *, valid_digest=True):
    root=tmp_path/'station';root.mkdir()
    outside=root/'outside';outside.mkdir();(outside/'source').write_bytes(b'original')
    raw=archive_bytes(kind,case,outside)
    manifest_root=tmp_path/'module';(manifest_root/'schemas').mkdir(parents=True)
    asset={'name':'runtime.'+kind,'url':'https://download.invalid/fixture',
           'sha256':hashlib.sha256(raw).hexdigest() if valid_digest else '0'*64}
    (manifest_root/'schemas/runtime.json').write_text(json.dumps({'assets':{'Linux-amd64':asset}}))
    monkeypatch.setattr(models,'__file__',str(manifest_root/'models.py'))
    monkeypatch.setattr(models.platform,'system',lambda:'Linux')
    monkeypatch.setattr(models.platform,'machine',lambda:'amd64')
    class Download(io.BytesIO):
        headers={}
    monkeypatch.setattr(models.urllib.request,'urlopen',lambda *a,**k:Download(raw))
    installer=models.Ollama(SimpleNamespace(root=root))
    installer.binary=Mock(return_value='fixture');installer.start=Mock(return_value='started')
    if case=='existing_symlink':
        (root/'runtime').mkdir();(root/'runtime/link').symlink_to(outside,target_is_directory=True)
    return installer,outside,root

@pytest.mark.parametrize('kind',['tar','zip','tar.zst'])
@pytest.mark.parametrize('case',CASES)
def test_members_cannot_write_outside_runtime(tmp_path,monkeypatch,kind,case):
    installer,outside,root=setup_installer(tmp_path,monkeypatch,kind,case)
    try:
        installer.install(lambda *a:None)
    except (ContractError,tarfile.TarError,OSError):
        pass
    assert not (outside/'marker').exists()
    assert (outside/'source').read_bytes()==b'original'
    # An outside hardlink would grant write authority over its inode.
    if (root/'runtime/marker').exists():
        assert not (root/'runtime/marker').samefile(outside/'source')

@pytest.mark.parametrize('kind',['tar','zip','tar.zst'])
def test_unpinned_content_never_extracts(tmp_path,monkeypatch,kind):
    installer,outside,root=setup_installer(tmp_path,monkeypatch,kind,'parent',valid_digest=False)
    with pytest.raises(ContractError,match='checksum mismatch'):
        installer.install(lambda *a:None)
    assert not (root/'runtime').exists()
    assert not (outside/'marker').exists()
    installer.start.assert_not_called()

@pytest.mark.parametrize('kind',['tar','zip','tar.zst'])
def test_valid_archive_still_installs(tmp_path,monkeypatch,kind):
    installer,_,root=setup_installer(tmp_path,monkeypatch,kind,'valid')
    assert installer.install(lambda *a:None)=='started'
    assert (root/'runtime/bin/ollama').read_bytes()==b'fixture'


def make_archive(kind, members):
    buffer = io.BytesIO()
    if kind == 'zip':
        with zipfile.ZipFile(buffer, 'w') as archive:
            for typ, name, value in members:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = ((0o120777 if typ == 'symlink' else 0o100644) << 16)
                archive.writestr(info, value)
    else:
        with tarfile.open(fileobj=buffer, mode='w') as archive:
            for typ, name, value in members:
                info = tarfile.TarInfo(name)
                if typ == 'file':
                    info.size = len(value)
                    archive.addfile(info, io.BytesIO(value))
                else:
                    info.type = tarfile.SYMTYPE if typ == 'symlink' else tarfile.LNKTYPE
                    info.linkname = value
                    archive.addfile(info)
    raw = buffer.getvalue()
    if kind == 'tar.zst':
        raw = subprocess.run(['zstd', '-q', '-c'], input=raw, capture_output=True, check=True).stdout
    return raw


def raw_installer(tmp_path, monkeypatch, kind, raw):
    installer, outside, root = setup_installer(tmp_path, monkeypatch, kind, 'valid')
    manifest = tmp_path/'module/schemas/runtime.json'
    doc = json.loads(manifest.read_text())
    doc['assets']['Linux-amd64']['sha256'] = hashlib.sha256(raw).hexdigest()
    manifest.write_text(json.dumps(doc))
    class Download(io.BytesIO):
        headers = {}
    monkeypatch.setattr(models.urllib.request, 'urlopen', lambda *a, **k: Download(raw))
    return installer, outside, root


def assert_no_partial_runtime(root):
    assert not (root/'runtime').exists(), 'failed extraction promoted partial runtime'
    assert not list(root.glob('.runtime-install-*')), 'failed extraction retained staging'


@pytest.mark.parametrize('case', ['symlink_alone', 'symlink_then_file'])
def test_tar_zst_never_creates_outside_authority(tmp_path, monkeypatch, case):
    # These two oracles must fail on the frozen pre-fix implementation even if
    # GNU tar raises and never writes the marker during extraction itself.
    outside = tmp_path/'station/outside'
    members = [('file', 'bin/ollama', b'fixture'), ('symlink', 'link', str(outside))]
    if case == 'symlink_then_file':
        members.append(('file', 'link/marker', b'fixture'))
    raw = make_archive('tar.zst', members)
    installer, outside, root = raw_installer(tmp_path, monkeypatch, 'tar.zst', raw)
    try:
        installer.install(lambda *a: None)
    except (ContractError, tarfile.TarError, OSError):
        pass
    assert not (root/'runtime/link').is_symlink(), 'outside symlink authority survived'
    assert not (outside/'marker').exists()
    assert_no_partial_runtime(root)
    installer.start.assert_not_called()


@pytest.mark.parametrize('kind,case', [(kind, case)
    for kind in ['tar', 'tar.zst', 'zip']
    for case in ['symlink', 'symlink_then_file', 'hardlink', 'hardlink_then_overwrite']
    if not (kind == 'zip' and case.startswith('hardlink'))])
def test_link_authority_rejected_before_promotion(tmp_path, monkeypatch, kind, case):
    outside = tmp_path/'station/outside'
    typ = 'hardlink' if case.startswith('hardlink') else 'symlink'
    target = str(outside/'source') if typ == 'hardlink' else str(outside)
    members = [('file', 'bin/ollama', b'fixture'), (typ, 'link', target)]
    if case == 'hardlink_then_overwrite':
        members.append(('file', 'link', b'overwrite'))
    elif case == 'symlink_then_file':
        members.append(('file', 'link/marker', b'fixture'))
    installer, outside, root = raw_installer(tmp_path, monkeypatch, kind, make_archive(kind, members))
    with pytest.raises((ContractError, tarfile.TarError)):
        installer.install(lambda *a: None)
    assert (outside/'source').read_bytes() == b'original'
    assert not (outside/'marker').exists()
    assert_no_partial_runtime(root)


@pytest.mark.parametrize('kind', ['tar', 'tar.zst', 'zip'])
def test_duplicate_members_last_wins_inside_destination(tmp_path, monkeypatch, kind):
    raw = make_archive(kind, [('file', 'bin/ollama', b'first'), ('file', 'bin/ollama', b'second')])
    installer, outside, root = raw_installer(tmp_path, monkeypatch, kind, raw)
    assert installer.install(lambda *a: None) == 'started'
    assert (root/'runtime/bin/ollama').read_bytes() == b'second'
    assert not list(root.glob('.runtime-install-*'))
    assert (outside/'source').read_bytes() == b'original'


@pytest.mark.parametrize('kind', ['tar', 'tar.zst', 'zip'])
def test_partial_extraction_rollback(tmp_path, monkeypatch, kind):
    # Passing inspection cannot imply successful extraction: induce an I/O failure
    # after a real member has been written into the private extraction directory.
    installer, outside, root = setup_installer(tmp_path, monkeypatch, kind, 'valid')
    actual = models.extract_zip if kind == 'zip' else models.extract_tar
    def fail_after_write(archive, stage):
        actual(archive, stage)
        assert (stage/'bin/ollama').read_bytes() == b'fixture'
        (stage/'outside-link').symlink_to(outside, target_is_directory=True)
        raise OSError('injected extraction failure after partial write')
    monkeypatch.setattr(models, 'extract_zip' if kind == 'zip' else 'extract_tar', fail_after_write)
    with pytest.raises(OSError, match='injected extraction failure'):
        installer.install(lambda *a: None)
    assert_no_partial_runtime(root)
    installer.start.assert_not_called()


@pytest.mark.parametrize('kind', ['tar', 'tar.zst', 'zip'])
def test_existing_runtime_and_symlink_are_preserved(tmp_path, monkeypatch, kind):
    installer, outside, root = setup_installer(tmp_path, monkeypatch, kind, 'existing_symlink')
    (root/'runtime/keep').write_bytes(b'prior-runtime')
    with pytest.raises(ContractError, match='already exists'):
        installer.install(lambda *a: None)
    assert (root/'runtime/keep').read_bytes() == b'prior-runtime'
    assert (root/'runtime/link').is_symlink()
    assert not (outside/'marker').exists()
    assert not list(root.glob('.runtime-install-*'))


@pytest.mark.parametrize('kind', ['tar', 'tar.zst', 'zip'])
def test_unavailable_data_filter_fails_closed(tmp_path, monkeypatch, kind):
    installer, _, root = setup_installer(tmp_path, monkeypatch, kind, 'valid')
    monkeypatch.delattr(tarfile, 'data_filter')
    with pytest.raises(ContractError, match='no unfiltered fallback'):
        installer.install(lambda *a: None)
    assert_no_partial_runtime(root)


@pytest.mark.parametrize('version', [(3,11,0), (3,11,12), (3,12,10), (3,13,3)])
def test_unpatched_filter_runtime_fails_closed(monkeypatch, version):
    monkeypatch.setattr(archive_security.sys, 'version_info', version)
    with pytest.raises(ContractError, match='patched Python'):
        archive_security.require_data_filter()


@pytest.mark.parametrize('version', [(3,11,13), (3,12,11), (3,13,4), (3,14,0)])
def test_supported_filter_runtime(monkeypatch, version):
    monkeypatch.setattr(archive_security.sys, 'version_info', version)
    archive_security.require_data_filter()


@pytest.mark.parametrize('typ', [tarfile.SYMTYPE, tarfile.LNKTYPE])
@pytest.mark.parametrize('target', ['../outside/source', '/absolute', 'C:/outside', '..\\outside'])
def test_explicit_link_target_validation(tmp_path, typ, target):
    member = tarfile.TarInfo('link')
    member.type, member.linkname = typ, target
    # This independently tests the required RESIDUAL-owned layer. A redundant
    # tarfile filter must not conceal removal of explicit target validation.
    with pytest.raises(ContractError, match='link target'):
        archive_security.validate_link(member, tmp_path)


@pytest.mark.parametrize('kind', ['tar', 'tar.zst'])
def test_confined_links_remain_supported(tmp_path, monkeypatch, kind):
    members = [('file', 'bin/ollama', b'fixture'), ('file', 'lib/source', b'library'),
               ('symlink', 'lib/symlink', 'source'), ('hardlink', 'lib/hardlink', 'lib/source')]
    installer, _, root = raw_installer(tmp_path, monkeypatch, kind, make_archive(kind, members))
    assert installer.install(lambda *a: None) == 'started'
    assert (root/'runtime/lib/symlink').read_bytes() == b'library'
    assert (root/'runtime/lib/hardlink').samefile(root/'runtime/lib/source')


def test_post_validation_rejects_external_authority(tmp_path):
    root, outside = tmp_path/'runtime', tmp_path/'outside'
    root.mkdir(); outside.mkdir()
    (root/'link').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ContractError, match='escaped'):
        archive_security.validate_tree(root)


def test_post_validation_rejects_external_hardlink(tmp_path):
    root = tmp_path/'runtime'; root.mkdir()
    outside = tmp_path/'outside'; outside.write_bytes(b'sentinel')
    os.link(outside, root/'link')
    with pytest.raises(ContractError, match='external hardlink'):
        archive_security.validate_tree(root)


def test_post_validation_failure_never_promotes(tmp_path, monkeypatch):
    installer, outside, root = setup_installer(tmp_path, monkeypatch, 'tar', 'valid')
    original = models.extract_tar
    def inject_link(archive, stage):
        original(archive, stage)
        (stage/'link').symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(models, 'extract_tar', inject_link)
    with pytest.raises(ContractError, match='escaped'):
        installer.install(lambda *a: None)
    assert_no_partial_runtime(root)


def test_member_names_have_cross_platform_confinement(tmp_path):
    for name in ['../escape', 'a/../../escape', '/absolute', 'C:/escape',
                 '..\\escape', 'file:stream', '//server/share']:
        with pytest.raises(ContractError):
            archive_security.member_path(name, tmp_path)


class DeterministicTemporaryDirectory:
    def __init__(self, *, prefix, dir, name):
        self.path = Path(dir) / name

    def __enter__(self):
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, exc_type, exc, tb):
        shutil.rmtree(self.path, ignore_errors=True)


@pytest.mark.parametrize('kind', ['tar', 'tar.zst'])
@pytest.mark.parametrize('referenced_name', ['.runtime-install-fixed123', '.runtime-install-wrong'])
def test_link_confinement_survives_staging_promotion(tmp_path, monkeypatch, kind, referenced_name):
    actual_name = '.runtime-install-fixed123'
    monkeypatch.setattr(
        models.tempfile,
        'TemporaryDirectory',
        lambda *, prefix, dir: DeterministicTemporaryDirectory(
            prefix=prefix, dir=dir, name=actual_name
        ),
    )
    target = f"../../{referenced_name}/runtime/victim"
    members = [
        ('file', 'bin/ollama', b'fixture'),
        ('file', 'victim', b'original'),
        ('symlink', 'link', target),
    ]
    installer, _, root = raw_installer(
        tmp_path, monkeypatch, kind, make_archive(kind, members)
    )
    with pytest.raises(ContractError, match='link target'):
        installer.install(lambda *a: None)
    assert_no_partial_runtime(root)
    installer.start.assert_not_called()


@pytest.mark.parametrize('kind', ['tar', 'tar.zst'])
def test_confined_parent_relative_symlink_survives_promotion(tmp_path, monkeypatch, kind):
    members = [
        ('file', 'bin/ollama', b'fixture'),
        ('symlink', 'lib/ollama-link', '../bin/ollama'),
    ]
    installer, _, root = raw_installer(
        tmp_path, monkeypatch, kind, make_archive(kind, members)
    )
    assert installer.install(lambda *a: None) == 'started'
    link = root/'runtime/lib/ollama-link'
    assert link.is_symlink()
    assert link.resolve() == (root/'runtime/bin/ollama').resolve()


def test_logical_link_target_rejects_root_underflow(tmp_path):
    member = tarfile.TarInfo('link')
    member.type = tarfile.SYMTYPE
    member.linkname = '../../.runtime-install-fixed123/runtime/victim'
    with pytest.raises(ContractError, match='link target'):
        archive_security.validate_link(member, tmp_path)


def test_manifest_python_support_matches_guard():
    import tomllib
    from packaging.specifiers import SpecifierSet
    contract = tomllib.loads((Path(__file__).parents[2]/'pyproject.toml').read_text())
    support = SpecifierSet(contract['project']['requires-python'])
    for version in ['3.11.0', '3.11.12', '3.12.10', '3.13.3']:
        assert version not in support
    for version in ['3.11.13', '3.12.11', '3.13.4', '3.14.0']:
        assert version in support

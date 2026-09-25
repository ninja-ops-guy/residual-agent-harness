"""Exercise the real Ollama installer with in-memory downloads and temporary roots."""
import hashlib
import io
import json
import subprocess
import tarfile
import zipfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from residual.core import ContractError
from residual.station import models

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

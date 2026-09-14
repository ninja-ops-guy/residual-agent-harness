from __future__ import annotations
import os,shutil,subprocess,sys,tempfile,threading
from pathlib import Path
from .signing import verify_signature
_INSTALL_LOCK=threading.Lock()
class ModuleInstaller:
    def __init__(self,module_path): self.module_path=Path(module_path)
    def install(self,package,*,public_key_b64,signature_b64):
        package=Path(package); verify_signature(package,public_key_b64,signature_b64)
        with _INSTALL_LOCK,tempfile.TemporaryDirectory(prefix="residual-module-") as td:
            stage=Path(td)/"site"; stage.mkdir(); subprocess.run([sys.executable,"-m","pip","install","--no-deps","--target",str(stage),str(package)],check=True,capture_output=True,text=True)
            probe="import importlib.metadata as m; e=m.entry_points(); x=e.select(group='residual.modules') if hasattr(e,'select') else e.get('residual.modules',()); assert list(x), 'missing residual.modules entry point'"
            subprocess.run([sys.executable,"-c",probe],env={**os.environ,"PYTHONPATH":str(stage)},check=True,capture_output=True,text=True)
            self.module_path.mkdir(parents=True,exist_ok=True); dest=self.module_path/package.stem; tmp=self.module_path/(package.stem+".installing")
            if tmp.exists(): shutil.rmtree(tmp)
            shutil.copytree(stage,tmp)
            if dest.exists(): shutil.rmtree(dest)
            os.replace(tmp,dest); return dest

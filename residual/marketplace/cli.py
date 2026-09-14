from __future__ import annotations
import argparse,importlib,json,os
from .install import ModuleInstaller
from .validate import validate_module
def _load(spec):
    mod,sep,name=spec.partition(":")
    if not sep: raise SystemExit("module target must be package.module:Class")
    return getattr(importlib.import_module(mod),name)()
def main(argv=None):
    p=argparse.ArgumentParser(prog="residual-module"); sub=p.add_subparsers(dest="command",required=True); v=sub.add_parser("validate"); v.add_argument("target"); v.add_argument("--source-root"); i=sub.add_parser("install"); i.add_argument("package"); i.add_argument("--public-key",required=True); i.add_argument("--signature",required=True); i.add_argument("--module-path",default=os.path.expanduser("~/.residual/modules")); a=p.parse_args(argv)
    if a.command=="validate": print(json.dumps(validate_module(_load(a.target),source_root=a.source_root),sort_keys=True)); return 0
    ModuleInstaller(a.module_path).install(a.package,public_key_b64=a.public_key,signature_b64=a.signature); return 0
if __name__=="__main__": raise SystemExit(main())

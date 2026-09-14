from __future__ import annotations
import ast,inspect
from pathlib import Path
FORBIDDEN_PREFIXES=("residual.core","residual.loop","residual.engine","residual.station.control")
class ValidationError(ValueError): pass
def _bind(fn,argc,label):
    if not callable(fn): raise ValidationError(f"{label} is not callable")
    try: inspect.signature(fn).bind(*([None]*argc))
    except TypeError as exc: raise ValidationError(f"invalid {label} signature") from exc
def _check_source_tree(root):
    for path in Path(root).rglob("*.py"):
        tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        for node in ast.walk(tree):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module or ""] if isinstance(node,ast.ImportFrom) else [])
            for name in names:
                if any(name==p or name.startswith(p+".") for p in FORBIDDEN_PREFIXES): raise ValidationError(f"forbidden Residual core-internal import in {path}: {name}")
def validate_module(module,*,source_root=None):
    for attr in ("name","version"):
        if not isinstance(getattr(module,attr,None),str) or not getattr(module,attr).strip(): raise ValidationError(f"missing {attr}")
    for hook in ("quarantine_policies","verifiers","brakes"): _bind(getattr(module,hook,None),0,hook)
    for hook in ("on_run_opened","on_run_closed"): _bind(getattr(module,hook,None),1,hook)
    policies,verifiers,brakes=module.quarantine_policies(),module.verifiers(),module.brakes()
    if not isinstance(policies,tuple) or not isinstance(verifiers,dict) or not isinstance(brakes,tuple): raise ValidationError("module containers must match StationModule protocol")
    for policy in policies:
        _bind(policy,1,"quarantine policy"); ann=inspect.signature(policy).return_annotation
        if ann is bool or "bool" in str(ann): raise ValidationError("quarantine policy must return Optional[str], never bool")
    for name,desc in verifiers.items():
        evaluator=getattr(desc,"evaluator",None) or (desc[1] if isinstance(desc,tuple) and len(desc)>1 else None); _bind(evaluator,2,f"verifier {name}")
    for brake in brakes: _bind(getattr(brake,"update",None),1,"brake.update"); _bind(getattr(brake,"reset",None),0,"brake.reset")
    if source_root: _check_source_tree(source_root)
    return {"name":module.name,"version":module.version,"policies":len(policies),"verifiers":len(verifiers),"brakes":len(brakes)}

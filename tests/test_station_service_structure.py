import ast
from pathlib import Path


def test_station_class_has_no_duplicate_method_names():
    path=Path(__file__).resolve().parents[1]/"residual/station/service.py"
    tree=ast.parse(path.read_text(encoding="utf-8"))
    station=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=="Station")
    methods=[node.name for node in station.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))]
    duplicates=sorted({name for name in methods if methods.count(name)>1})
    assert duplicates==[],f"duplicate Station method definitions: {duplicates}"


def test_worker_metrics_definition_exposes_live_instances():
    path=Path(__file__).resolve().parents[1]/"residual/station/service.py"
    text=path.read_text(encoding="utf-8")
    assert text.count("def worker_metrics(self, pid):")==1
    assert '"instances": self.store.workers(project_id=pid)' in text

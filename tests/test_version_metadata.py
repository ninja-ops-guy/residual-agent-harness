from __future__ import annotations

import ast
import pathlib
import tomllib
import json
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _package_version() -> str:
    tree = ast.parse((ROOT / "residual" / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
            raise AssertionError("residual.__version__ must be a literal string")
    raise AssertionError("residual.__version__ assignment not found")


class VersionMetadataTests(unittest.TestCase):
    def test_package_version_matches_project_metadata(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["version"], _package_version())

    def test_frontend_package_version_matches_project_metadata(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        frontend = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(project["version"], frontend["version"])

    def test_station_reports_package_version(self) -> None:
        from residual import __version__
        from residual.station import server
        self.assertEqual(server.Handler.server_version, f"ResidualStation/{__version__}")
        source = (ROOT / "residual" / "station" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn('"version": "0.3.0"', source)


if __name__ == "__main__":
    unittest.main()

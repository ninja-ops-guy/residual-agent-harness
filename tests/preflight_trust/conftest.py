"""Opt-in independent tests; production APIs are never patched or copied here."""
import importlib
import pytest


def pytest_addoption(parser):
    parser.addoption("--run-bounded-sandbox", action="store_true", default=False)


@pytest.fixture(scope="session")
def api():
    def require(module, *names):
        try:
            loaded = importlib.import_module(module)
        except ModuleNotFoundError as exc:
            # Missing transitive dependencies are meaningful, and named in skip evidence.
            pytest.skip(f"target API/dependency unavailable: {exc.name}")
        absent = []
        for name in names:
            item = loaded
            for part in name.split("."):
                if not hasattr(item, part):
                    absent.append(name)
                    break
                item = getattr(item, part)
        if absent:
            pytest.skip(f"target API unavailable: {module}: {', '.join(absent)}")
        return loaded
    return require

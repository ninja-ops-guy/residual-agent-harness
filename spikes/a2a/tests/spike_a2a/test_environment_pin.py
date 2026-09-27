"""Environment pin checks for SPIKE-A2A-000."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_environment_pins_a2a_1_0_sdk_and_jsonrpc():
    env = json.loads((ROOT / "environment.json").read_text())
    assert env["a2a"]["spec_version"] == "1.0.1"
    assert env["a2a"]["sdk_version"] == "1.0.3"
    assert env["a2a"]["protocol_binding"] == "json-rpc"

def test_requirements_uses_exact_a2a_pin():
    requirements = (ROOT / "requirements-spike.txt").read_text()
    assert "a2a-sdk[http-server]==1.0.3" in requirements

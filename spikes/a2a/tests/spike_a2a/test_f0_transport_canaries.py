"""F0-1 over real A2A 1.0.3 JSON-RPC/SSE transport."""
import os, socket, subprocess, sys, time
from pathlib import Path
import pytest
from a2a.client import create_client
from a2a.types.a2a_pb2 import Message, Part, Role, SendMessageRequest, TaskState

ROOT = Path(__file__).resolve().parents[2]

def _free_port():
    s=socket.socket(); s.bind(("127.0.0.1",0)); port=s.getsockname()[1]; s.close(); return port

def _wait(port, proc, timeout=10):
    deadline=time.time()+timeout
    while time.time()<deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"uvicorn exited early: {proc.returncode}")
        try:
            with socket.create_connection(("127.0.0.1",port), timeout=.2): return
        except OSError: time.sleep(.05)
    raise TimeoutError("uvicorn did not become ready")

@pytest.fixture
def incorrect_server():
    port=_free_port()
    env=os.environ.copy()
    env.update({"MODE":"incorrect_completed","PORT":str(port),
                "PYTHONPATH":str(ROOT)+os.pathsep+env.get("PYTHONPATH","")})
    proc=subprocess.Popen([
        sys.executable,"-m","uvicorn",
        "residual_spike_a2a.server_harness:create_starlette_app",
        "--factory","--host","127.0.0.1","--port",str(port),"--log-level","warning"
    ], env=env)
    _wait(port,proc)
    try: yield f"http://127.0.0.1:{port}"
    finally:
        if proc.poll() is None: proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=5)

@pytest.mark.asyncio
async def test_f0_1_real_jsonrpc_sse_completed_is_not_acceptance(incorrect_server):
    client=await create_client(incorrect_server)
    saw_completed=False
    artifact_value=None
    try:
        request=SendMessageRequest(
            message=Message(role=Role.ROLE_USER,message_id="f0-http-1",parts=[Part(text="compute")])
        )
        async for response in client.send_message(request):
            if response.HasField("artifact_update"):
                artifact_value=response.artifact_update.artifact.parts[0].text
            if response.HasField("status_update") and response.status_update.status.state == TaskState.TASK_STATE_COMPLETED:
                saw_completed=True
    finally:
        await client.close()

    assert saw_completed is True
    assert artifact_value == "41"
    verifier_pass = artifact_value == "42"
    assert verifier_pass is False
    accepted_receipt = {"accepted": True} if verifier_pass else None
    assert accepted_receipt is None


@pytest.fixture
def connection_death_server():
    port=_free_port()
    env=os.environ.copy()
    env.update({"MODE":"connection_death","PORT":str(port),
                "PYTHONPATH":str(ROOT)+os.pathsep+env.get("PYTHONPATH","")})
    proc=subprocess.Popen([
        sys.executable,"-m","uvicorn",
        "residual_spike_a2a.server_harness:create_starlette_app",
        "--factory","--host","127.0.0.1","--port",str(port),"--log-level","warning"
    ], env=env)
    _wait(port,proc)
    try:
        yield f"http://127.0.0.1:{port}", proc
    finally:
        if proc.poll() is None: proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait(timeout=5)

@pytest.mark.asyncio
async def test_f0_2_real_transport_death_never_promotes(connection_death_server):
    base_url, proc = connection_death_server
    client=await create_client(base_url)
    artifact_value=None
    terminal_observed=False
    transport_interrupted=False
    observed=[]
    try:
        request=SendMessageRequest(
            message=Message(role=Role.ROLE_USER,message_id="f0-http-2",parts=[Part(text="compute")])
        )
        try:
            async for response in client.send_message(request):
                if response.HasField("task"):
                    observed.append("task")
                elif response.HasField("status_update"):
                    state=response.status_update.status.state
                    observed.append("status:"+TaskState.Name(state))
                    if state in {
                        TaskState.TASK_STATE_COMPLETED,
                        TaskState.TASK_STATE_FAILED,
                        TaskState.TASK_STATE_CANCELED,
                        TaskState.TASK_STATE_REJECTED,
                        TaskState.TASK_STATE_INPUT_REQUIRED,
                        TaskState.TASK_STATE_AUTH_REQUIRED,
                    }:
                        terminal_observed=True
                elif response.HasField("artifact_update"):
                    artifact_value=response.artifact_update.artifact.parts[0].text
                    observed.append("artifact:"+artifact_value)
                    assert artifact_value == "42"
                    assert terminal_observed is False
                    proc.kill()
                    proc.wait(timeout=5)
                    # Do not break: force the client to observe the dead SSE transport.
        except Exception:
            transport_interrupted=True
    finally:
        await client.close()

    assert artifact_value == "42"
    assert terminal_observed is False
    assert proc.poll() is not None
    assert transport_interrupted is True

    # Recovered bytes are evidence, not authority. No terminal/interrupted
    # protocol event was observed before transport loss, so promotion is forbidden.
    provisional={"value":artifact_value,"terminal":False,"events":observed}
    verifier_pass = provisional["terminal"] and provisional["value"] == "42"
    assert verifier_pass is False
    accepted_receipt = {"accepted": True} if verifier_pass else None
    assert accepted_receipt is None

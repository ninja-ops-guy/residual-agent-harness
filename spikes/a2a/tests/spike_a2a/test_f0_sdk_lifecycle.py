"""Pinned-SDK lifecycle tests preceding network transport wiring."""
import pytest
from a2a.server.context import ServerCallContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types.a2a_pb2 import (
    AgentCapabilities, AgentCard, Message, Part, Role,
    SendMessageConfiguration, SendMessageRequest, Task, TaskState,
)
from residual_spike_a2a.reference_agent import IncorrectCompletedExecutor

@pytest.mark.asyncio
async def test_real_sdk_completed_wrong_artifact_is_only_protocol_state():
    handler = DefaultRequestHandler(
        agent_executor=IncorrectCompletedExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=AgentCard(
            name="f0-reference", version="1.0",
            capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        ),
    )
    result = await handler.on_message_send(
        SendMessageRequest(
            message=Message(role=Role.ROLE_USER, message_id="m-f0-1", parts=[Part(text="compute")]),
            configuration=SendMessageConfiguration(accepted_output_modes=["text/plain"]),
        ),
        ServerCallContext(),
    )
    assert isinstance(result, Task)
    assert result.status.state == TaskState.TASK_STATE_COMPLETED
    assert result.artifacts
    assert result.artifacts[0].parts[0].text == "41"

    # Protocol COMPLETED is deliberately not an acceptance assertion.
    expected = "42"
    verifier_pass = result.artifacts[0].parts[0].text == expected
    assert verifier_pass is False
    accepted_receipt = {"accepted": True} if verifier_pass else None
    assert accepted_receipt is None

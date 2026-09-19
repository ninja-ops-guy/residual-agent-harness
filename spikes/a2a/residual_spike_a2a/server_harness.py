"""Real Starlette/JSON-RPC harness for SPIKE-A2A-000."""
import os
from starlette.applications import Starlette
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types.a2a_pb2 import AgentCapabilities, AgentCard, AgentInterface
from a2a.utils.constants import PROTOCOL_VERSION_1_0, TransportProtocol
from .reference_agent import ArtifactThenWaitExecutor, IncorrectCompletedExecutor

def create_starlette_app() -> Starlette:
    mode = os.environ.get("MODE", "incorrect_completed")
    port = int(os.environ.get("PORT", "9999"))
    executor = ArtifactThenWaitExecutor() if mode == "connection_death" else IncorrectCompletedExecutor()
    card = AgentCard(
        name="f0-reference",
        description="SPIKE-A2A-000 transport canary",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        supported_interfaces=[AgentInterface(
            url=f"http://127.0.0.1:{port}/",
            protocol_binding=TransportProtocol.JSONRPC,
            protocol_version=PROTOCOL_VERSION_1_0,
        )],
    )
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    routes = []
    routes.extend(create_jsonrpc_routes(handler, "/"))
    routes.extend(create_agent_card_routes(card))
    return Starlette(routes=routes)

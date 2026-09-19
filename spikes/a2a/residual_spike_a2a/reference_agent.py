"""Pinned A2A 1.0.3 reference executors for SPIKE-A2A-000."""
import asyncio
from a2a.helpers.proto_helpers import new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types.a2a_pb2 import Part, TaskState

class IncorrectCompletedExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if not task:
            assert context.message is not None
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.update_status(TaskState.TASK_STATE_WORKING)
        await updater.add_artifact([Part(text="41")], name="f0-value")
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.task_id and context.context_id:
            await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()

class ArtifactThenWaitExecutor(AgentExecutor):
    def __init__(self, artifact_emitted: asyncio.Event | None = None):
        self.artifact_emitted = artifact_emitted or asyncio.Event()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if not task:
            assert context.message is not None
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        await updater.update_status(TaskState.TASK_STATE_WORKING)
        await updater.add_artifact([Part(text="42")], name="f0-value")
        self.artifact_emitted.set()
        # Intentionally non-terminal. The transport harness, not the executor,
        # is responsible for terminating the server side after observing this.
        await asyncio.Event().wait()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.task_id and context.context_id:
            await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()

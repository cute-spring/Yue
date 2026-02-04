import asyncio
import inspect
import time
import uuid
from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from app.observability import get_trace_id
from app.services.agent_store import agent_store
from app.services.chat_service import chat_service
from app.services.model_factory import get_model


class TaskSpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    title: Optional[str] = None
    agent_id: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    trace_id: Optional[str] = None
    deadline_ts: Optional[float] = None
    auth_scope: Optional[dict[str, Any]] = None
    context_refs: Optional[list[dict[str, Any]]] = None


class TaskEvent(BaseModel):
    type: Literal["task_event"] = "task_event"
    parent_chat_id: str
    task_id: str
    child_chat_id: str
    status: Literal["started", "running", "completed", "failed"]
    trace_id: Optional[str] = None
    content_delta: Optional[str] = None
    error: Optional[str] = None


class TaskOutcome(BaseModel):
    task_id: str
    child_chat_id: str
    status: Literal["completed", "failed"]
    agent_id: Optional[str] = None
    title: Optional[str] = None
    output: Optional[str] = None
    citations: Optional[list[dict]] = None
    error: Optional[str] = None
    duration_s: float


class TaskToolResult(BaseModel):
    parent_chat_id: str
    tasks: list[TaskOutcome]


async def _maybe_await(value: Any) -> None:
    if inspect.isawaitable(value):
        await value


class TaskService:
    def __init__(self) -> None:
        self._running: dict[str, asyncio.Task] = {}
        self._running_lock = asyncio.Lock()

    def _key(self, parent_chat_id: str, task_id: str) -> str:
        return f"{parent_chat_id}:{task_id}"

    async def cancel_task(self, parent_chat_id: str, task_id: str) -> bool:
        key = self._key(parent_chat_id, task_id)
        async with self._running_lock:
            task = self._running.get(key)
        if task:
            task.cancel()
            return True
        return False

    async def run_tasks(
        self,
        parent_chat_id: str,
        tasks: list[TaskSpec],
        emit: Optional[Callable[[TaskEvent], Any]] = None,
    ) -> TaskToolResult:
        if not chat_service.get_chat(parent_chat_id):
            raise ValueError("parent_chat_not_found")

        outcomes: list[TaskOutcome] = []

        for spec in tasks:
            child = chat_service.create_chat(
                agent_id=spec.agent_id,
                title=spec.title or "Task",
                parent_id=parent_chat_id,
            )
            chat_service.add_message(child.id, "user", spec.prompt)

            task_trace_id = spec.trace_id or get_trace_id()

            if emit:
                await _maybe_await(
                    emit(
                        TaskEvent(
                            parent_chat_id=parent_chat_id,
                            task_id=spec.id,
                            child_chat_id=child.id,
                            status="started",
                            trace_id=task_trace_id,
                        )
                    )
                )

            async def _run_one() -> TaskOutcome:
                started = time.time()
                full_response = ""
                error: Optional[str] = None
                captured_citations: Optional[list[dict]] = None

                try:
                    agent_config = agent_store.get_agent(spec.agent_id) if spec.agent_id else None

                    provider = spec.provider or (agent_config.provider if agent_config else None) or "openai"
                    model_name = spec.model or (agent_config.model if agent_config else None) or "gpt-4o"
                    system_prompt = (
                        spec.system_prompt
                        or (agent_config.system_prompt if agent_config else None)
                        or "You are a helpful assistant."
                    )

                    model = get_model(provider, model_name)

                    from app.mcp.manager import mcp_manager

                    tools = await mcp_manager.get_tools_for_agent(spec.agent_id)
                    agent = Agent(model, system_prompt=system_prompt, tools=tools)

                    deps: dict[str, Any] = {"citations": [], "trace_id": task_trace_id}
                    if agent_config and getattr(agent_config, "doc_root", None):
                        deps["doc_root"] = agent_config.doc_root
                    if spec.auth_scope is not None:
                        deps["auth_scope"] = spec.auth_scope
                    if spec.context_refs is not None:
                        deps["context_refs"] = spec.context_refs

                    async def _run_agent_stream() -> None:
                        nonlocal full_response
                        async with agent.run_stream(spec.prompt, deps=deps) as result:
                            async for message in result.stream_text():
                                if not message:
                                    continue
                                if full_response and message.startswith(full_response):
                                    delta = message[len(full_response) :]
                                elif full_response and full_response.startswith(message):
                                    delta = ""
                                else:
                                    delta = message
                                if not delta:
                                    continue

                                full_response += delta
                                if emit:
                                    await _maybe_await(
                                        emit(
                                            TaskEvent(
                                                parent_chat_id=parent_chat_id,
                                                task_id=spec.id,
                                                child_chat_id=child.id,
                                                status="running",
                                                trace_id=task_trace_id,
                                                content_delta=delta,
                                            )
                                        )
                                    )

                    if spec.deadline_ts is not None:
                        timeout_s = spec.deadline_ts - time.time()
                        if timeout_s <= 0:
                            raise asyncio.TimeoutError()
                        await asyncio.wait_for(_run_agent_stream(), timeout=timeout_s)
                    else:
                        await _run_agent_stream()

                    citations = deps.get("citations")
                    if isinstance(citations, list):
                        captured_citations = [c for c in citations if isinstance(c, dict)]

                    chat_service.add_message(child.id, "assistant", full_response)

                    if emit:
                        await _maybe_await(
                            emit(
                                TaskEvent(
                                    parent_chat_id=parent_chat_id,
                                    task_id=spec.id,
                                    child_chat_id=child.id,
                                    status="completed",
                                    trace_id=task_trace_id,
                                )
                            )
                        )
                except asyncio.CancelledError:
                    error = "cancelled"
                    chat_service.add_message(child.id, "assistant", error)
                    if emit:
                        await _maybe_await(
                            emit(
                                TaskEvent(
                                    parent_chat_id=parent_chat_id,
                                    task_id=spec.id,
                                    child_chat_id=child.id,
                                    status="failed",
                                    trace_id=task_trace_id,
                                    error=error,
                                )
                            )
                        )
                except asyncio.TimeoutError:
                    error = "deadline_exceeded"
                    chat_service.add_message(child.id, "assistant", error)
                    if emit:
                        await _maybe_await(
                            emit(
                                TaskEvent(
                                    parent_chat_id=parent_chat_id,
                                    task_id=spec.id,
                                    child_chat_id=child.id,
                                    status="failed",
                                    trace_id=task_trace_id,
                                    error=error,
                                )
                            )
                        )
                except Exception as e:
                    error = str(e)[:500]
                    chat_service.add_message(child.id, "assistant", error)
                    if emit:
                        await _maybe_await(
                            emit(
                                TaskEvent(
                                    parent_chat_id=parent_chat_id,
                                    task_id=spec.id,
                                    child_chat_id=child.id,
                                    status="failed",
                                    trace_id=task_trace_id,
                                    error=error,
                                )
                            )
                        )

                duration_s = time.time() - started
                if error:
                    return TaskOutcome(
                        task_id=spec.id,
                        child_chat_id=child.id,
                        agent_id=spec.agent_id,
                        title=spec.title,
                        status="failed",
                        error=error,
                        citations=captured_citations,
                        duration_s=duration_s,
                    )

                return TaskOutcome(
                    task_id=spec.id,
                    child_chat_id=child.id,
                    agent_id=spec.agent_id,
                    title=spec.title,
                    status="completed",
                    output=full_response,
                    citations=captured_citations,
                    duration_s=duration_s,
                )

            key = self._key(parent_chat_id, spec.id)
            task = asyncio.create_task(_run_one())
            async with self._running_lock:
                self._running[key] = task
            try:
                outcome = await task
            finally:
                async with self._running_lock:
                    self._running.pop(key, None)

            outcomes.append(outcome)

        return TaskToolResult(parent_chat_id=parent_chat_id, tasks=outcomes)


task_service = TaskService()

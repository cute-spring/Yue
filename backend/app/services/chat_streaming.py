import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from app.services.chart_artifacts import collect_chart_artifact_event, normalize_chart_artifact_event


@dataclass
class StreamState:
    full_response: str = ""
    first_token_time: Optional[float] = None
    chart_artifacts: List[Dict[str, Any]] = field(default_factory=list)


class StreamEventEmitter:
    def __init__(
        self,
        *,
        event_v2_enabled: bool,
        run_id: str,
        assistant_turn_id: str,
        serialize_payload: Callable[[Dict[str, Any]], str],
        iso_utc_now: Callable[[], str],
        chart_artifact_sink: Optional[List[Dict[str, Any]]] = None,
        logger: Any = None,
    ):
        self.event_v2_enabled = event_v2_enabled
        self.run_id = run_id
        self.assistant_turn_id = assistant_turn_id
        self.serialize_payload = serialize_payload
        self.iso_utc_now = iso_utc_now
        self.chart_artifact_sink = chart_artifact_sink
        self.logger = logger
        self.sequence = 0

    def event_type_of(self, payload: Dict[str, Any]) -> str:
        if isinstance(payload.get("event"), str):
            return payload["event"]
        if "meta" in payload:
            return "meta"
        if "chat_id" in payload:
            return "chat_id"
        if "content" in payload:
            return "content.delta"
        if "thought" in payload:
            return "reasoning.delta"
        if "error" in payload:
            return "error"
        return "trace.event"

    def event_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.event_v2_enabled:
            if payload.get("event") == "artifact.chart.created":
                try:
                    normalize_chart_artifact_event(payload)
                except Exception as exc:
                    if self.logger is not None:
                        self.logger.exception("Invalid chart artifact event dropped")
                    return {"event": "trace.event", "reason": "invalid_chart_artifact", "error": str(exc)}
                if self.chart_artifact_sink is not None:
                    collect_chart_artifact_event(self.chart_artifact_sink, payload, self.logger)
            return payload
        self.sequence += 1
        envelope = {
            "version": "v2",
            "event": self.event_type_of(payload),
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "assistant_turn_id": self.assistant_turn_id,
            "sequence": self.sequence,
            "ts": self.iso_utc_now(),
            "payload": payload,
        }
        event_payload = {**envelope, **payload}
        if event_payload.get("event") == "artifact.chart.created":
            try:
                normalize_chart_artifact_event(event_payload)
            except Exception as exc:
                if self.logger is not None:
                    self.logger.exception("Invalid chart artifact event dropped")
                return {
                    **envelope,
                    "event": "trace.event",
                    "payload": {"reason": "invalid_chart_artifact", "error": str(exc)},
                    "reason": "invalid_chart_artifact",
                    "error": str(exc),
                }
            if self.chart_artifact_sink is not None:
                collect_chart_artifact_event(self.chart_artifact_sink, event_payload, self.logger)
        return event_payload

    def emit(self, payload: Dict[str, Any]) -> str:
        return self.serialize_payload(self.event_payload(payload))


async def stream_result_chunks(
    *,
    result: Any,
    parser: Any,
    tool_event_queue: asyncio.Queue,
    emitter: StreamEventEmitter,
    stream_state: StreamState,
    serialize_payload: Callable[[Dict[str, Any]], str],
    logger: Any,
    log_label: str,
) -> AsyncIterator[str]:
    stream_iter = result.stream_text()
    if asyncio.iscoroutine(stream_iter):
        stream_iter = await stream_iter

    stream_task = asyncio.create_task(stream_iter.__anext__())
    queue_task = asyncio.create_task(tool_event_queue.get())

    try:
        while True:
            done, _ = await asyncio.wait([stream_task, queue_task], return_when=asyncio.FIRST_COMPLETED)

            if stream_task in done:
                try:
                    chunk = await stream_task
                    if not stream_state.first_token_time:
                        stream_state.first_token_time = time.time()
                    for item in parser.parse_chunk(chunk):
                        if "content" in item:
                            stream_state.full_response += item["content"]
                        yield emitter.emit(item)
                    stream_task = asyncio.create_task(stream_iter.__anext__())
                except StopAsyncIteration:
                    if queue_task.done() and not queue_task.cancelled():
                        try:
                            ev = queue_task.result()
                            yield serialize_payload(ev)
                            tool_event_queue.task_done()
                        except Exception:
                            pass
                    break
                except Exception:
                    logger.exception("Error in %s", log_label)
                    # The queue getter may have won the race before the stream
                    # failed; preserve that already-consumed Yue tool event.
                    if queue_task.done() and not queue_task.cancelled():
                        try:
                            ev = queue_task.result()
                            yield serialize_payload(ev)
                            tool_event_queue.task_done()
                        except Exception:
                            pass
                    break

            if queue_task in done:
                try:
                    ev = await queue_task
                    yield serialize_payload(ev)
                    tool_event_queue.task_done()
                    queue_task = asyncio.create_task(tool_event_queue.get())
                except Exception:
                    logger.exception("Error getting from %s tool_event_queue", log_label)
                    queue_task = asyncio.create_task(tool_event_queue.get())
    finally:
        if not stream_task.done():
            stream_task.cancel()
        if not queue_task.done():
            queue_task.cancel()
        while not tool_event_queue.empty():
            ev = tool_event_queue.get_nowait()
            yield serialize_payload(ev)
            tool_event_queue.task_done()

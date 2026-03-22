import asyncio
import logging
from typing import Any, Dict


logger = logging.getLogger(__name__)


class ToolEventTracker:
    def __init__(
        self,
        *,
        chat_id: str,
        assistant_turn_id: str,
        run_id: str,
        turn_binding_enabled: bool,
        emitter: Any,
        tool_event_queue: asyncio.Queue,
        chat_service: Any,
        normalize_finished_ts: Any,
    ) -> None:
        self.chat_id = chat_id
        self.assistant_turn_id = assistant_turn_id
        self.run_id = run_id
        self.turn_binding_enabled = turn_binding_enabled
        self.emitter = emitter
        self.tool_event_queue = tool_event_queue
        self.chat_service = chat_service
        self.normalize_finished_ts = normalize_finished_ts
        self.counts = {"started": 0, "finished": 0}

    async def on_tool_event(self, event: Dict[str, Any]):
        try:
            event_payload = self.emitter.event_payload(event)
            await self.tool_event_queue.put(event_payload)
            event_type = event_payload.get("event")
            if event_type == "tool.call.started":
                self.counts["started"] += 1
                self.chat_service.add_tool_call(
                    session_id=self.chat_id,
                    call_id=event_payload.get("call_id"),
                    tool_name=event_payload.get("tool_name"),
                    args=event_payload.get("args"),
                    assistant_turn_id=self.assistant_turn_id if self.turn_binding_enabled else None,
                    run_id=self.run_id if self.turn_binding_enabled else None,
                    event_id_started=event_payload.get("event_id"),
                    started_sequence=event_payload.get("sequence"),
                    started_ts=self.normalize_finished_ts(event_payload.get("ts"))
                )
            elif event_type == "tool.call.finished":
                self.counts["finished"] += 1
                self.chat_service.update_tool_call(
                    call_id=event_payload.get("call_id"),
                    status="error" if "error" in event_payload else "success",
                    result=event_payload.get("result"),
                    error=event_payload.get("error"),
                    duration_ms=event_payload.get("duration_ms"),
                    event_id_finished=event_payload.get("event_id"),
                    finished_sequence=event_payload.get("sequence"),
                    finished_ts=self.normalize_finished_ts(event_payload.get("ts"))
                )
        except Exception:
            logger.exception("Error in on_tool_event (streaming + persistence)")

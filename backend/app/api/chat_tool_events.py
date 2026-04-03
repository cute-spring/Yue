import asyncio
import logging
from typing import Any, Dict

from app.api.chat_trace_schemas import ToolTraceRecord


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
        self._call_index = 0
        self._trace_by_call_id: Dict[str, Dict[str, Any]] = {}

    def _build_trace_record(self, *, event_payload: Dict[str, Any], status: str) -> ToolTraceRecord:
        call_id = str(event_payload.get("call_id") or "")
        trace_meta = self._trace_by_call_id.get(call_id)
        if trace_meta is None:
            self._call_index += 1
            trace_meta = {
                "trace_id": f"trace_{self.run_id}_{self._call_index}",
                "call_index": self._call_index,
                "parent_trace_id": None,
                "chain_depth": 0,
            }
            if call_id:
                self._trace_by_call_id[call_id] = trace_meta

        normalized_ts = self.normalize_finished_ts(event_payload.get("ts"))
        trace_kwargs: Dict[str, Any] = {
            "chat_id": self.chat_id,
            "run_id": self.run_id,
            "assistant_turn_id": self.assistant_turn_id if self.turn_binding_enabled else "",
            "trace_id": trace_meta["trace_id"],
            "parent_trace_id": trace_meta["parent_trace_id"],
            "tool_name": str(event_payload.get("tool_name") or "unknown"),
            "tool_type": str(event_payload.get("tool_type") or "runtime"),
            "call_id": call_id or None,
            "call_index": int(trace_meta["call_index"]),
            "status": status,
            "chain_depth": int(trace_meta["chain_depth"]),
            "raw_event_id": event_payload.get("event_id"),
        }
        if status == "started":
            trace_kwargs["started_at"] = normalized_ts
            trace_kwargs["input_arguments"] = event_payload.get("args")
        else:
            trace_kwargs["finished_at"] = normalized_ts
            trace_kwargs["duration_ms"] = event_payload.get("duration_ms")
            trace_kwargs["output_result"] = event_payload.get("result")
            if event_payload.get("error") is not None:
                trace_kwargs["error_type"] = "tool_error"
                trace_kwargs["error_message"] = str(event_payload.get("error"))

        return ToolTraceRecord(**trace_kwargs)

    def _persist_trace_record(self, *, event_payload: Dict[str, Any], status: str) -> None:
        try:
            trace_record = self._build_trace_record(event_payload=event_payload, status=status)
            self.chat_service.add_action_event(
                self.chat_id,
                {
                    "event": "tool.trace.record",
                    "trace_id": trace_record.trace_id,
                    "parent_trace_id": trace_record.parent_trace_id,
                    "call_id": trace_record.call_id,
                    "tool_name": trace_record.tool_name,
                    "status": trace_record.status,
                    "call_index": trace_record.call_index,
                    "assistant_turn_id": trace_record.assistant_turn_id,
                    "run_id": trace_record.run_id,
                    "trace": trace_record.model_dump(mode="json"),
                },
                assistant_turn_id=self.assistant_turn_id if self.turn_binding_enabled else None,
                run_id=self.run_id if self.turn_binding_enabled else None,
            )
        except Exception:
            logger.exception("Error while persisting tool trace record")

    async def on_tool_event(self, event: Dict[str, Any]):
        try:
            event_payload = self.emitter.event_payload(event)
            await self.tool_event_queue.put(event_payload)
            event_type = event_payload.get("event")
            if event_type == "tool.call.started":
                self.counts["started"] += 1
                self._persist_trace_record(event_payload=event_payload, status="started")
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
                self._persist_trace_record(
                    event_payload=event_payload,
                    status="error" if "error" in event_payload else "success",
                )
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

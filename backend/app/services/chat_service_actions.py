import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func

from app.api.chat_trace_schemas import ChatTraceBundle, RequestSnapshotRecord, ToolTraceRecord, build_default_trace_field_policies
from app.core.database import SessionLocal
from app.models.chat import (
    ActionEvent as ActionEventModel,
    ActionState as ActionStateModel,
    Message as MessageModel,
    Session as SessionModel,
    SkillEffectivenessEvent as SkillEventModel,
    ToolCall as ToolCallModel,
)
from .chat_service_models import ActionObservability, ActionState


class ChatServiceActionsMixin:
    def get_chat_events(
        self,
        session_id: str,
        assistant_turn_id: Optional[str] = None,
        after_sequence: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        with SessionLocal() as db:
            msg_query = db.query(MessageModel).filter(MessageModel.session_id == session_id, MessageModel.role == "assistant")
            if assistant_turn_id:
                msg_query = msg_query.filter(MessageModel.assistant_turn_id == assistant_turn_id)
            messages = msg_query.order_by(MessageModel.timestamp.asc()).all()

            tc_query = db.query(ToolCallModel).filter(ToolCallModel.session_id == session_id)
            if assistant_turn_id:
                tc_query = tc_query.filter(ToolCallModel.assistant_turn_id == assistant_turn_id)
            tool_calls = tc_query.order_by(
                func.coalesce(ToolCallModel.started_sequence, ToolCallModel.finished_sequence, 0).asc(),
                func.coalesce(ToolCallModel.started_ts, ToolCallModel.finished_ts, ToolCallModel.created_at).asc(),
            ).all()

            action_query = db.query(ActionEventModel).filter(ActionEventModel.session_id == session_id)
            if assistant_turn_id:
                action_query = action_query.filter(ActionEventModel.assistant_turn_id == assistant_turn_id)
            action_events = action_query.order_by(func.coalesce(ActionEventModel.sequence, 0).asc(), ActionEventModel.created_at.asc()).all()

        for message in messages:
            turn_id = message.assistant_turn_id
            run_id = message.run_id
            if not turn_id or not run_id:
                continue
            ts = message.timestamp.isoformat() if message.timestamp else ""
            reasoning_enabled = bool(message.reasoning_enabled) if message.reasoning_enabled is not None else False
            supports_reasoning = bool(message.supports_reasoning) if message.supports_reasoning is not None else False
            deep_thinking_enabled = bool(message.deep_thinking_enabled) if message.deep_thinking_enabled is not None else False
            events.append({
                "version": "v2",
                "event": "meta",
                "event_id": f"replay_meta_{session_id}_{turn_id}",
                "run_id": run_id,
                "assistant_turn_id": turn_id,
                "sequence": 1,
                "ts": ts,
                "payload": {
                    "meta": {
                        "supports_reasoning": supports_reasoning,
                        "deep_thinking_enabled": deep_thinking_enabled,
                        "reasoning_enabled": reasoning_enabled,
                    }
                },
                "meta": {
                    "supports_reasoning": supports_reasoning,
                    "deep_thinking_enabled": deep_thinking_enabled,
                    "reasoning_enabled": reasoning_enabled,
                },
            })
            events.append({
                "version": "v2",
                "event": "content.final",
                "event_id": f"replay_content_{session_id}_{turn_id}",
                "run_id": run_id,
                "assistant_turn_id": turn_id,
                "sequence": 999999,
                "ts": ts,
                "payload": {"content": message.content or ""},
                "content": message.content or "",
            })

        for tool_call in tool_calls:
            turn_id = tool_call.assistant_turn_id
            run_id = tool_call.run_id
            if not turn_id or not run_id:
                continue
            start_ts_val = tool_call.started_ts or tool_call.created_at
            finish_ts_val = tool_call.finished_ts or tool_call.finished_at
            start_ts = start_ts_val.isoformat() if start_ts_val else ""
            finish_ts = finish_ts_val.isoformat() if finish_ts_val else ""
            if tool_call.args:
                try:
                    parsed_args = json.loads(tool_call.args)
                except Exception:
                    parsed_args = {}
            else:
                parsed_args = {}
            if tool_call.started_sequence:
                events.append({
                    "version": "v2",
                    "event": "tool.call.started",
                    "event_id": tool_call.event_id_started or f"replay_started_{tool_call.call_id}",
                    "run_id": run_id,
                    "assistant_turn_id": turn_id,
                    "sequence": tool_call.started_sequence,
                    "ts": start_ts,
                    "payload": {"call_id": tool_call.call_id, "tool_name": tool_call.tool_name, "args": parsed_args},
                    "call_id": tool_call.call_id,
                    "tool_name": tool_call.tool_name,
                    "args": parsed_args,
                })
            if tool_call.finished_sequence:
                events.append({
                    "version": "v2",
                    "event": "tool.call.finished",
                    "event_id": tool_call.event_id_finished or f"replay_finished_{tool_call.call_id}",
                    "run_id": run_id,
                    "assistant_turn_id": turn_id,
                    "sequence": tool_call.finished_sequence,
                    "ts": finish_ts,
                    "payload": {
                        "call_id": tool_call.call_id,
                        "tool_name": tool_call.tool_name,
                        "result": tool_call.result,
                        "error": tool_call.error,
                        "duration_ms": tool_call.duration_ms,
                    },
                    "call_id": tool_call.call_id,
                    "tool_name": tool_call.tool_name,
                    "result": tool_call.result,
                    "error": tool_call.error,
                    "duration_ms": tool_call.duration_ms,
                })

        for action_event in action_events:
            try:
                payload = json.loads(action_event.payload_json)
            except Exception:
                payload = {"event": action_event.event_name}
            event_envelope = {
                "version": "v2",
                "event": action_event.event_name,
                "event_id": action_event.event_id or f"replay_action_{action_event.id}",
                "run_id": action_event.run_id,
                "assistant_turn_id": action_event.assistant_turn_id,
                "sequence": action_event.sequence or 0,
                "ts": action_event.ts or "",
                "payload": payload,
            }
            if isinstance(payload, dict):
                event_envelope.update(payload)
            events.append(event_envelope)

        events.sort(key=lambda item: (str(item.get("run_id") or ""), int(item.get("sequence") or 0), str(item.get("ts") or "")))
        if after_sequence is not None:
            events = [event for event in events if int(event.get("sequence") or 0) > int(after_sequence)]
        return events

    def get_chat_trace_bundle(self, session_id: str, *, assistant_turn_id: Optional[str] = None, mode: str = "summary") -> Optional[Dict[str, Any]]:
        if mode not in {"summary", "raw"}:
            raise ValueError("Unsupported trace bundle mode")

        with SessionLocal() as db:
            snapshot_query = db.query(ActionEventModel).filter(
                ActionEventModel.session_id == session_id,
                ActionEventModel.event_name == "chat.request.snapshot",
            )
            if assistant_turn_id:
                snapshot_query = snapshot_query.filter(ActionEventModel.assistant_turn_id == assistant_turn_id)
            snapshot_row = snapshot_query.order_by(ActionEventModel.created_at.desc(), ActionEventModel.id.desc()).first()
            if snapshot_row is None:
                return None

            try:
                snapshot_payload = json.loads(snapshot_row.payload_json)
            except Exception:
                snapshot_payload = {}

            snapshot_record = RequestSnapshotRecord.model_validate(snapshot_payload.get("snapshot") or {})
            trace_rows = db.query(ActionEventModel).filter(
                ActionEventModel.session_id == session_id,
                ActionEventModel.event_name == "tool.trace.record",
                ActionEventModel.run_id == snapshot_record.run_id,
                ActionEventModel.assistant_turn_id == snapshot_record.assistant_turn_id,
            ).order_by(
                func.coalesce(ActionEventModel.sequence, 0).asc(),
                ActionEventModel.created_at.asc(),
                ActionEventModel.id.asc(),
            ).all()

        trace_records: List[ToolTraceRecord] = []
        for row in trace_rows:
            try:
                payload = json.loads(row.payload_json)
            except Exception:
                payload = {}
            trace_payload = payload.get("trace") or {}
            try:
                trace_records.append(ToolTraceRecord.model_validate(trace_payload))
            except Exception:
                continue

        bundle = ChatTraceBundle(
            mode=mode,
            chat_id=session_id,
            run_id=snapshot_record.run_id,
            assistant_turn_id=snapshot_record.assistant_turn_id,
            snapshot=snapshot_record,
            tool_traces=trace_records,
            field_policies=build_default_trace_field_policies(),
        )
        if mode == "raw":
            return bundle.model_dump(mode="json")

        summary_snapshot = bundle.snapshot.model_copy(deep=True)
        summary_snapshot.system_prompt = None
        summary_snapshot.redaction = {**summary_snapshot.redaction, "system_prompt": True, "mode": "summary"}

        summary_traces: List[ToolTraceRecord] = []
        for trace in bundle.tool_traces:
            redacted_trace = trace.model_copy(deep=True)
            redacted_trace.input_arguments = None
            redacted_trace.output_result = None
            redacted_trace.error_stack = None
            summary_traces.append(redacted_trace)

        return ChatTraceBundle(
            mode="summary",
            chat_id=bundle.chat_id,
            run_id=bundle.run_id,
            assistant_turn_id=bundle.assistant_turn_id,
            snapshot=summary_snapshot,
            tool_traces=summary_traces,
            field_policies=bundle.field_policies,
        ).model_dump(mode="json")

    def _upsert_action_state(
        self,
        db: Any,
        *,
        session_id: str,
        event: Dict[str, Any],
        assistant_turn_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[ActionStateModel]:
        skill_name = event.get("skill_name")
        action_id = event.get("action_id")
        lifecycle_status = event.get("lifecycle_status")
        if not skill_name or not action_id or not lifecycle_status:
            return None

        skill_version = event.get("skill_version")
        invocation_id = event.get("invocation_id")
        approval_token = event.get("approval_token")
        request_id = event.get("request_id")
        observability_payload = event.get("observability") if isinstance(event.get("observability"), dict) else {}
        state = None
        if invocation_id is not None:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.invocation_id == str(invocation_id),
            ).first()
        if state is None:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.skill_name == str(skill_name),
                ActionStateModel.action_id == str(action_id),
                ActionStateModel.invocation_id.is_(None),
            ).first()
        if state is None:
            state = ActionStateModel(
                session_id=session_id,
                skill_name=str(skill_name),
                skill_version=str(skill_version) if skill_version is not None else None,
                action_id=str(action_id),
                invocation_id=str(invocation_id) if invocation_id is not None else None,
            )
            db.add(state)

        state.skill_version = str(skill_version) if skill_version is not None else state.skill_version
        state.invocation_id = str(invocation_id) if invocation_id is not None else state.invocation_id
        state.approval_token = str(approval_token) if approval_token is not None else state.approval_token
        state.request_id = str(request_id) if request_id is not None else state.request_id
        state.run_id = run_id or event.get("run_id") or state.run_id
        state.assistant_turn_id = assistant_turn_id or event.get("assistant_turn_id") or state.assistant_turn_id
        state.lifecycle_phase = event.get("lifecycle_phase")
        state.lifecycle_status = str(lifecycle_status)
        state.status = str(event.get("status")) if event.get("status") is not None else state.status
        state.observability_started_at = str(observability_payload.get("started_at")) if observability_payload.get("started_at") is not None else state.observability_started_at
        state.observability_finished_at = str(observability_payload.get("finished_at")) if observability_payload.get("finished_at") is not None else state.observability_finished_at
        duration_ms = observability_payload.get("duration_ms")
        if isinstance(duration_ms, (int, float)):
            state.observability_duration_ms = int(duration_ms)
        elif isinstance(duration_ms, str):
            try:
                state.observability_duration_ms = int(float(duration_ms))
            except ValueError:
                pass
        if observability_payload.get("error_kind") is not None:
            state.observability_error_kind = str(observability_payload.get("error_kind"))
        if observability_payload.get("retryable") is not None:
            state.observability_retryable = bool(observability_payload.get("retryable"))
        if observability_payload.get("artifact_path") is not None:
            state.observability_artifact_path = str(observability_payload.get("artifact_path"))
        state.payload_json = json.dumps(event)
        return state

    def _register_workspace_artifact_for_action_state(self, db: Any, *, session_id: str, state: Optional[ActionStateModel], event: Dict[str, Any]) -> None:
        if state is None or not state.observability_artifact_path:
            return
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        workspace_id = getattr(session, "workspace_id", None) if session is not None else None
        if not workspace_id:
            return

        from app.services.workspace_service import workspace_service

        artifact_path = str(state.observability_artifact_path).strip()
        if not artifact_path:
            return
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        output_file_path = payload.get("output_file_path") if isinstance(payload.get("output_file_path"), str) else None
        artifact_type = "tool_output"
        if "/exports/" in artifact_path or artifact_path.startswith("/exports/") or artifact_path.startswith("sandbox:/exports/"):
            artifact_type = "export"
        elif output_file_path and output_file_path == artifact_path:
            artifact_type = "generated_file"

        title = payload.get("title") or payload.get("filename") or os.path.basename(output_file_path or artifact_path) or f"{state.skill_name} artifact"
        metadata = {
            "skill_name": state.skill_name,
            "skill_version": state.skill_version,
            "action_id": state.action_id,
            "invocation_id": state.invocation_id,
            "run_id": state.run_id,
            "assistant_turn_id": state.assistant_turn_id,
            "request_id": state.request_id,
            "status": state.status,
            "lifecycle_status": state.lifecycle_status,
            "artifact_path": artifact_path,
            "output_file_path": output_file_path,
            "event_name": event.get("event"),
        }
        workspace_service.upsert_artifact_record(
            db,
            workspace_id,
            artifact_type=artifact_type,
            title=str(title),
            source_session_id=session_id,
            action_state_id=state.id,
            artifact_path=artifact_path,
            content_ref=state.invocation_id or state.request_id,
            artifact_metadata=metadata,
        )

    def _build_action_state_model(self, state: ActionStateModel) -> ActionState:
        try:
            payload = json.loads(state.payload_json)
        except Exception:
            payload = {}
        observability = None
        if any(
            value is not None
            for value in (
                state.observability_started_at,
                state.observability_finished_at,
                state.observability_duration_ms,
                state.observability_error_kind,
                state.observability_retryable,
                state.observability_artifact_path,
            )
        ):
            observability = ActionObservability(
                started_at=state.observability_started_at,
                finished_at=state.observability_finished_at,
                duration_ms=state.observability_duration_ms,
                error_kind=state.observability_error_kind,
                retryable=state.observability_retryable,
                artifact_path=state.observability_artifact_path,
            )
        return ActionState(
            id=state.id,
            session_id=state.session_id,
            skill_name=state.skill_name,
            skill_version=state.skill_version,
            action_id=state.action_id,
            invocation_id=state.invocation_id,
            approval_token=state.approval_token,
            request_id=state.request_id,
            run_id=state.run_id,
            assistant_turn_id=state.assistant_turn_id,
            lifecycle_phase=state.lifecycle_phase,
            lifecycle_status=state.lifecycle_status,
            status=state.status,
            observability=observability,
            payload=payload,
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

    def get_action_state(self, session_id: str, *, skill_name: str, action_id: str) -> Optional[ActionState]:
        with SessionLocal() as db:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.skill_name == skill_name,
                ActionStateModel.action_id == action_id,
            ).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).first()
            if state is None:
                return None
            return self._build_action_state_model(state)

    def get_action_state_by_invocation_id(self, session_id: str, *, invocation_id: str) -> Optional[ActionState]:
        with SessionLocal() as db:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.invocation_id == invocation_id,
            ).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).first()
            if state is None:
                return None
            return self._build_action_state_model(state)

    def get_action_state_by_approval_token(self, session_id: str, *, approval_token: str) -> Optional[ActionState]:
        with SessionLocal() as db:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.approval_token == approval_token,
            ).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).first()
            if state is None:
                return None
            return self._build_action_state_model(state)

    def list_action_states(self, session_id: str) -> List[ActionState]:
        with SessionLocal() as db:
            rows = db.query(ActionStateModel).filter(ActionStateModel.session_id == session_id).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).all()
            return [self._build_action_state_model(state) for state in rows]

    def add_action_event(
        self,
        session_id: str,
        event: Dict[str, Any],
        *,
        assistant_turn_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> None:
        with SessionLocal() as db:
            db_event = ActionEventModel(
                session_id=session_id,
                assistant_turn_id=assistant_turn_id,
                run_id=run_id,
                event_name=str(event.get("event") or "skill.action.unknown"),
                event_id=event.get("event_id"),
                sequence=event.get("sequence"),
                ts=event.get("ts"),
                payload_json=json.dumps(event),
            )
            db.add(db_event)
            state = self._upsert_action_state(db, session_id=session_id, event=event, assistant_turn_id=assistant_turn_id, run_id=run_id)
            db.flush()
            self._register_workspace_artifact_for_action_state(db, session_id=session_id, state=state, event=event)
            db.commit()

    def add_skill_effectiveness_event(self, session_id: str, event: Dict[str, Any]) -> None:
        now = datetime.utcnow()
        selected = event.get("selected_skill") or {}
        with SessionLocal() as db:
            db.add(
                SkillEventModel(
                    session_id=session_id,
                    reason_code=str(event.get("reason_code") or "unknown"),
                    selection_source=str(event.get("selection_source") or "none"),
                    fallback_used=1 if bool(event.get("fallback_used")) else 0,
                    selected_skill_name=selected.get("name"),
                    selected_skill_version=selected.get("version"),
                    selected_skill_source_layer=event.get("selected_skill_source_layer"),
                    override_hit=1 if bool(event.get("override_hit")) else 0,
                    visible_skill_count=event.get("visible_skill_count"),
                    available_skill_count=event.get("available_skill_count"),
                    always_injected_count=event.get("always_injected_count"),
                    summary_injected=1 if bool(event.get("summary_injected")) else 0,
                    summary_prompt_enabled=1 if bool(event.get("summary_prompt_enabled")) else 0,
                    lazy_full_load_enabled=1 if bool(event.get("lazy_full_load_enabled")) else 0,
                    selection_score=event.get("selection_score"),
                    system_prompt_tokens_estimate=event.get("system_prompt_tokens_estimate"),
                    user_message_tokens_estimate=event.get("user_message_tokens_estimate"),
                    created_at=now,
                )
            )
            db.commit()

    def get_skill_effectiveness_report(self, hours: int = 24) -> Dict[str, Any]:
        hours = max(1, int(hours))
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        with SessionLocal() as db:
            base_query = db.query(SkillEventModel).filter(SkillEventModel.created_at >= time_threshold)
            total_runs = base_query.count()
            fallback_runs = db.query(func.sum(SkillEventModel.fallback_used)).filter(SkillEventModel.created_at >= time_threshold).scalar() or 0
            override_hits = db.query(func.sum(SkillEventModel.override_hit)).filter(SkillEventModel.created_at >= time_threshold).scalar() or 0
            avg_selection_score = db.query(func.avg(SkillEventModel.selection_score)).filter(SkillEventModel.created_at >= time_threshold).scalar() or 0.0
            avg_sys_tokens = db.query(func.avg(SkillEventModel.system_prompt_tokens_estimate)).filter(SkillEventModel.created_at >= time_threshold).scalar() or 0.0
            avg_usr_tokens = db.query(func.avg(SkillEventModel.user_message_tokens_estimate)).filter(SkillEventModel.created_at >= time_threshold).scalar() or 0.0
            reason_rows = db.query(SkillEventModel.reason_code, func.count(SkillEventModel.id).label("cnt")).filter(
                SkillEventModel.created_at >= time_threshold
            ).group_by(SkillEventModel.reason_code).order_by(desc("cnt")).all()
            skill_rows = db.query(SkillEventModel.selected_skill_name, func.count(SkillEventModel.id).label("cnt")).filter(
                SkillEventModel.created_at >= time_threshold,
                SkillEventModel.selected_skill_name.isnot(None),
            ).group_by(SkillEventModel.selected_skill_name).order_by(desc("cnt")).limit(10).all()
            layer_rows = db.query(SkillEventModel.selected_skill_source_layer, func.count(SkillEventModel.id).label("cnt")).filter(
                SkillEventModel.created_at >= time_threshold,
                SkillEventModel.selected_skill_source_layer.isnot(None),
            ).group_by(SkillEventModel.selected_skill_source_layer).order_by(desc("cnt")).all()

        hit_rate = 0.0 if total_runs == 0 else (total_runs - fallback_runs) / total_runs
        fallback_rate = 0.0 if total_runs == 0 else fallback_runs / total_runs
        override_hit_rate = 0.0 if total_runs == 0 else override_hits / total_runs
        return {
            "window_hours": hours,
            "total_runs": int(total_runs),
            "skill_hit_rate": float(hit_rate),
            "fallback_rate": float(fallback_rate),
            "override_hit_rate": float(override_hit_rate),
            "avg_selection_score": float(avg_selection_score),
            "avg_system_prompt_tokens": float(avg_sys_tokens),
            "avg_user_message_tokens": float(avg_usr_tokens),
            "reason_distribution": [{"reason_code": row.reason_code, "count": int(row.cnt)} for row in reason_rows],
            "top_selected_skills": [{"name": row.selected_skill_name, "count": int(row.cnt)} for row in skill_rows],
            "source_layer_distribution": [{"source_layer": row.selected_skill_source_layer, "count": int(row.cnt)} for row in layer_rows],
        }

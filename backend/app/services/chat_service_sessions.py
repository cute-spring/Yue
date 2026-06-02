import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func

from app.core.database import SessionLocal
from app.models.chat import Message as MessageModel
from app.models.chat import Session as SessionModel
from app.models.chat import ToolCall as ToolCallModel
from .chat_service_models import ChatSession, Message, ToolCall


class ChatServiceSessionsMixin:
    def list_chats(
        self,
        tags: Optional[List[str]] = None,
        tag_mode: str = "any",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ChatSession]:
        normalized_filter_tags = self._normalize_tags(tags or [])
        normalized_tag_mode = "all" if (tag_mode or "").lower() == "all" else "any"
        with SessionLocal() as db:
            sessions_stmt = db.query(SessionModel)
            if date_from is not None:
                sessions_stmt = sessions_stmt.filter(SessionModel.updated_at >= date_from)
            if date_to is not None:
                sessions_stmt = sessions_stmt.filter(SessionModel.updated_at <= date_to)
            sessions_query = sessions_stmt.order_by(desc(SessionModel.updated_at)).all()
            result = []
            for session in sessions_query:
                parsed_tags = self._parse_tags(getattr(session, "tags_json", "[]"))
                if normalized_filter_tags:
                    if normalized_tag_mode == "all":
                        if not all(tag in parsed_tags for tag in normalized_filter_tags):
                            continue
                    elif not any(tag in parsed_tags for tag in normalized_filter_tags):
                        continue

                messages_query = db.query(MessageModel).filter(MessageModel.session_id == session.id).order_by(MessageModel.timestamp).all()
                messages = [self._build_message_model(message) for message in messages_query]
                result.append(
                    ChatSession(
                        id=session.id,
                        workspace_id=getattr(session, "workspace_id", None),
                        title=session.title,
                        summary=session.summary,
                        agent_id=session.agent_id,
                        active_skill_name=session.active_skill_name,
                        active_skill_version=session.active_skill_version,
                        tags=parsed_tags,
                        messages=messages,
                        created_at=self._to_api_datetime(session.created_at),
                        updated_at=self._to_api_datetime(session.updated_at),
                    )
                )
            return result

    def get_chat(self, chat_id: str) -> Optional[ChatSession]:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not session:
                return None

            messages_query = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(MessageModel.timestamp).all()
            all_tool_calls = self.get_tool_calls(chat_id)
            tool_calls_by_turn: Dict[str, List[ToolCall]] = {}
            legacy_tool_calls: List[ToolCall] = []
            for call in all_tool_calls:
                if call.assistant_turn_id:
                    tool_calls_by_turn.setdefault(call.assistant_turn_id, []).append(call)
                else:
                    legacy_tool_calls.append(call)

            messages = []
            for message in messages_query:
                chat_message = self._build_message_model(message)
                if chat_message.role == "assistant":
                    if chat_message.assistant_turn_id:
                        chat_message.tool_calls = [tc.model_dump() for tc in tool_calls_by_turn.get(chat_message.assistant_turn_id, [])]
                    else:
                        chat_message.tool_calls = [tc.model_dump() for tc in legacy_tool_calls]
                messages.append(chat_message)

            return ChatSession(
                id=session.id,
                workspace_id=getattr(session, "workspace_id", None),
                title=session.title,
                summary=session.summary,
                agent_id=session.agent_id,
                active_skill_name=session.active_skill_name,
                active_skill_version=session.active_skill_version,
                tags=self._parse_tags(getattr(session, "tags_json", "[]")),
                messages=messages,
                created_at=self._to_api_datetime(session.created_at),
                updated_at=self._to_api_datetime(session.updated_at),
            )

    def create_chat(self, agent_id: Optional[str] = None, title: str = "New Chat", workspace_id: Optional[str] = None) -> ChatSession:
        chat_id = str(uuid.uuid4())
        now = datetime.utcnow()
        with SessionLocal() as db:
            new_session = SessionModel(
                id=chat_id,
                workspace_id=workspace_id,
                title=title,
                agent_id=agent_id,
                created_at=now,
                updated_at=now,
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)

        return ChatSession(
            id=chat_id,
            workspace_id=workspace_id,
            title=title,
            summary=None,
            agent_id=agent_id,
            active_skill_name=None,
            active_skill_version=None,
            tags=[],
            messages=[],
            created_at=self._to_api_datetime(now),
            updated_at=self._to_api_datetime(now),
        )

    def update_chat_title(self, chat_id: str, title: str) -> bool:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not session:
                return False
            session.title = title
            session.updated_at = datetime.utcnow()
            db.commit()
            return True

    def update_chat_summary(self, chat_id: str, summary: Optional[str]) -> bool:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not session:
                return False
            session.summary = summary
            messages_query = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(desc(MessageModel.timestamp)).limit(12).all()
            source_texts = [session.title or "", summary or ""] + [message.content for message in messages_query if message.content]
            session.tags_json = json.dumps(self._derive_tags_from_texts(source_texts))
            session.updated_at = datetime.utcnow()
            db.commit()
            return True

    def generate_chat_tags(self, chat_id: str) -> Optional[List[str]]:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not session:
                return None
            messages_query = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(desc(MessageModel.timestamp)).limit(12).all()
            source_texts = [session.title or "", session.summary or ""] + [message.content for message in messages_query if message.content]
            derived_tags = self._derive_tags_from_texts(source_texts)
            session.tags_json = json.dumps(derived_tags)
            session.updated_at = datetime.utcnow()
            db.commit()
            return derived_tags

    def get_session_skill(self, chat_id: str) -> tuple[Optional[str], Optional[str]]:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not session:
                return None, None
            return session.active_skill_name, session.active_skill_version

    def set_session_skill(self, chat_id: str, name: str, version: str) -> None:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if session:
                session.active_skill_name = name
                session.active_skill_version = version
                session.updated_at = datetime.utcnow()
                db.commit()

    def clear_session_skill(self, chat_id: str) -> None:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if session:
                session.active_skill_name = None
                session.active_skill_version = None
                session.updated_at = datetime.utcnow()
                db.commit()

    def _build_message_model(self, message: Any) -> Message:
        msg_dict = {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "timestamp": self._to_api_datetime(message.timestamp),
            "assistant_turn_id": message.assistant_turn_id,
            "run_id": message.run_id,
            "continuation_of": getattr(message, "continuation_of", None),
            "continuation_root_id": getattr(message, "continuation_root_id", None),
            "continuation_status": getattr(message, "continuation_status", None),
            "content_type": getattr(message, "content_type", None),
            "thought_duration": message.thought_duration,
            "ttft": message.ttft,
            "total_duration": message.total_duration,
            "prompt_tokens": message.prompt_tokens,
            "completion_tokens": message.completion_tokens,
            "total_tokens": message.total_tokens,
            "finish_reason": message.finish_reason,
            "supports_reasoning": bool(message.supports_reasoning) if message.supports_reasoning is not None else None,
            "deep_thinking_enabled": bool(message.deep_thinking_enabled) if message.deep_thinking_enabled is not None else None,
            "reasoning_enabled": bool(message.reasoning_enabled) if message.reasoning_enabled is not None else None,
        }
        if message.images:
            try:
                msg_dict["images"] = json.loads(message.images)
            except Exception:
                msg_dict["images"] = []
        if message.attachments:
            try:
                msg_dict["attachments"] = json.loads(message.attachments)
            except Exception:
                msg_dict["attachments"] = []
        return Message(**msg_dict)

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        thought_duration: Optional[float] = None,
        images: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        ttft: Optional[float] = None,
        total_duration: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        finish_reason: Optional[str] = None,
        assistant_turn_id: Optional[str] = None,
        run_id: Optional[str] = None,
        continuation_of: Optional[str] = None,
        continuation_root_id: Optional[str] = None,
        continuation_status: Optional[str] = None,
        content_type: Optional[str] = None,
        supports_reasoning: Optional[bool] = None,
        deep_thinking_enabled: Optional[bool] = None,
        reasoning_enabled: Optional[bool] = None,
    ) -> Optional[ChatSession]:
        now = datetime.utcnow()
        session_workspace_id: Optional[str] = None
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not session:
                return None
            session_workspace_id = getattr(session, "workspace_id", None)
            new_msg = MessageModel(
                session_id=chat_id,
                role=role,
                content=content,
                images=json.dumps(images) if images else None,
                attachments=json.dumps(attachments) if attachments else None,
                timestamp=now,
                assistant_turn_id=assistant_turn_id,
                run_id=run_id,
                continuation_of=continuation_of,
                continuation_root_id=continuation_root_id,
                continuation_status=continuation_status,
                content_type=content_type,
                supports_reasoning=None if supports_reasoning is None else (1 if supports_reasoning else 0),
                deep_thinking_enabled=None if deep_thinking_enabled is None else (1 if deep_thinking_enabled else 0),
                reasoning_enabled=None if reasoning_enabled is None else (1 if reasoning_enabled else 0),
                thought_duration=thought_duration,
                ttft=ttft,
                total_duration=total_duration,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason,
            )
            db.add(new_msg)

            if role == "user":
                msg_count = db.query(MessageModel).filter(MessageModel.session_id == chat_id).count()
                if msg_count == 0 and session.title == "New Chat":
                    session.title = content[:30] + "..." if len(content) > 30 else content

            if role in {"user", "assistant"}:
                seed_texts = [session.title or "", session.summary or "", content or ""]
                existing_tags = self._parse_tags(getattr(session, "tags_json", "[]"))
                session.tags_json = json.dumps(self._normalize_tags(existing_tags + self._derive_tags_from_texts(seed_texts)))

            session.updated_at = now
            db.commit()

        if role == "user" and session_workspace_id and attachments:
            from app.services.workspace_service import workspace_service

            workspace_service.register_sources_from_attachments(session_workspace_id, attachments)

        return self.get_chat(chat_id)

    def delete_chat(self, chat_id: str) -> bool:
        with SessionLocal() as db:
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if session:
                db.delete(session)
                db.commit()
                return True
            return False

    def truncate_chat(self, chat_id: str, keep_count: int) -> bool:
        with SessionLocal() as db:
            messages = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(MessageModel.timestamp).all()
            if len(messages) <= keep_count:
                return False
            for message in messages[keep_count:]:
                db.delete(message)
            session = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if session:
                session.updated_at = datetime.utcnow()
            db.commit()
            return True

    def add_tool_call(
        self,
        session_id: str,
        call_id: str,
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        assistant_turn_id: Optional[str] = None,
        run_id: Optional[str] = None,
        event_id_started: Optional[str] = None,
        started_sequence: Optional[int] = None,
        started_ts: Optional[datetime] = None,
    ) -> None:
        now = datetime.utcnow()
        with SessionLocal() as db:
            db.add(
                ToolCallModel(
                    session_id=session_id,
                    call_id=call_id,
                    tool_name=tool_name,
                    assistant_turn_id=assistant_turn_id,
                    run_id=run_id,
                    event_id_started=event_id_started,
                    started_sequence=started_sequence,
                    started_ts=started_ts or now,
                    args=json.dumps(args) if args else None,
                    status="running",
                    created_at=now,
                )
            )
            db.commit()

    def update_tool_call(
        self,
        call_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        event_id_finished: Optional[str] = None,
        finished_sequence: Optional[int] = None,
        finished_ts: Optional[datetime] = None,
    ) -> None:
        now = datetime.utcnow()
        with SessionLocal() as db:
            tool_call = db.query(ToolCallModel).filter(ToolCallModel.call_id == call_id).first()
            if tool_call:
                tool_call.status = status
                tool_call.result = result
                tool_call.error = error
                tool_call.event_id_finished = event_id_finished
                tool_call.finished_sequence = finished_sequence
                tool_call.finished_ts = finished_ts or now
                tool_call.finished_at = now
                tool_call.duration_ms = duration_ms
                db.commit()

    def get_tool_calls(self, session_id: str) -> List[ToolCall]:
        with SessionLocal() as db:
            query = db.query(ToolCallModel).filter(ToolCallModel.session_id == session_id).order_by(
                func.coalesce(ToolCallModel.started_sequence, ToolCallModel.finished_sequence, 0).asc(),
                func.coalesce(ToolCallModel.started_ts, ToolCallModel.finished_ts, ToolCallModel.created_at).asc(),
            ).all()

            tool_calls = []
            for tool_call in query:
                tool_dict = {
                    "id": tool_call.id,
                    "session_id": tool_call.session_id,
                    "message_id": tool_call.message_id,
                    "call_id": tool_call.call_id,
                    "tool_name": tool_call.tool_name,
                    "assistant_turn_id": tool_call.assistant_turn_id,
                    "run_id": tool_call.run_id,
                    "event_id_started": tool_call.event_id_started,
                    "event_id_finished": tool_call.event_id_finished,
                    "started_sequence": tool_call.started_sequence,
                    "finished_sequence": tool_call.finished_sequence,
                    "started_ts": tool_call.started_ts,
                    "finished_ts": tool_call.finished_ts,
                    "result": tool_call.result,
                    "error": tool_call.error,
                    "status": tool_call.status,
                    "created_at": tool_call.created_at,
                    "finished_at": tool_call.finished_at,
                    "duration_ms": tool_call.duration_ms,
                    "args": {},
                }
                if tool_call.args:
                    try:
                        tool_dict["args"] = json.loads(tool_call.args)
                    except Exception:
                        tool_dict["args"] = {}
                tool_calls.append(ToolCall(**tool_dict))
            return tool_calls

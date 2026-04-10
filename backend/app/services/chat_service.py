import json
import os
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import select, desc, func, case, inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import logging

from app.api.chat_trace_schemas import (
    ChatTraceBundle,
    RequestSnapshotRecord,
    ToolTraceRecord,
    build_default_trace_field_policies,
)
from app.core.database import SessionLocal, engine, Base
from app.models.chat import (
    Session as SessionModel,
    Message as MessageModel,
    ToolCall as ToolCallModel,
    SkillEffectivenessEvent as SkillEventModel,
    ActionEvent as ActionEventModel,
    ActionState as ActionStateModel,
)

DATA_DIR = os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))
OLD_CHATS_FILE = os.path.join(DATA_DIR, "chats.json")
logger = logging.getLogger(__name__)

TAG_MAX_COUNT = 8
TAG_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "we", "with", "you", "your",
}
TAG_SYNONYMS = {
    "authentication": "auth",
    "authorize": "auth",
    "authorization": "auth",
    "bug": "bugfix",
    "bugs": "bugfix",
    "fix": "bugfix",
    "fixes": "bugfix",
    "frontend": "ui-ux",
    "ui": "ui-ux",
    "ux": "ui-ux",
    "tests": "testing",
}

class Message(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    thought_duration: Optional[float] = None
    ttft: Optional[float] = None
    total_duration: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    assistant_turn_id: Optional[str] = None
    run_id: Optional[str] = None
    supports_reasoning: Optional[bool] = None
    deep_thinking_enabled: Optional[bool] = None
    reasoning_enabled: Optional[bool] = None

class ToolCall(BaseModel):
    id: Optional[int] = None
    session_id: str
    message_id: Optional[int] = None
    call_id: str
    tool_name: str
    assistant_turn_id: Optional[str] = None
    run_id: Optional[str] = None
    event_id_started: Optional[str] = None
    event_id_finished: Optional[str] = None
    started_sequence: Optional[int] = None
    finished_sequence: Optional[int] = None
    started_ts: Optional[datetime] = None
    finished_ts: Optional[datetime] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    status: str  # 'running', 'success', 'error'
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

class SkillEffectivenessEvent(BaseModel):
    id: Optional[int] = None
    session_id: str
    reason_code: str
    selection_source: str
    fallback_used: bool
    selected_skill_name: Optional[str] = None
    selected_skill_version: Optional[str] = None
    selected_skill_source_layer: Optional[str] = None
    override_hit: Optional[bool] = None
    visible_skill_count: Optional[int] = None
    available_skill_count: Optional[int] = None
    always_injected_count: Optional[int] = None
    summary_injected: Optional[bool] = None
    summary_prompt_enabled: Optional[bool] = None
    lazy_full_load_enabled: Optional[bool] = None
    selection_score: Optional[int] = None
    system_prompt_tokens_estimate: Optional[int] = None
    user_message_tokens_estimate: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ActionEvent(BaseModel):
    id: Optional[int] = None
    session_id: str
    assistant_turn_id: Optional[str] = None
    run_id: Optional[str] = None
    event_name: str
    event_id: Optional[str] = None
    sequence: Optional[int] = None
    ts: Optional[str] = None
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)


class ActionState(BaseModel):
    id: Optional[int] = None
    session_id: str
    skill_name: str
    skill_version: Optional[str] = None
    action_id: str
    invocation_id: Optional[str] = None
    approval_token: Optional[str] = None
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    assistant_turn_id: Optional[str] = None
    lifecycle_phase: Optional[str] = None
    lifecycle_status: str
    status: Optional[str] = None
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    agent_id: Optional[str] = None
    active_skill_name: Optional[str] = None
    active_skill_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    messages: List[Message] = []
    created_at: datetime
    updated_at: datetime

class ChatService:
    def __init__(self):
        self._ensure_db()
        self._migrate_from_json()

    @staticmethod
    def _to_api_datetime(value: Optional[datetime]) -> Optional[datetime]:
        """Return timezone-aware UTC datetimes for API payloads."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _ensure_db(self):
        # We now rely on Alembic for migrations, but for local SQLite we can still do create_all
        # to ensure tables exist if someone doesn't run migrations.
        # Alembic will take over schema changes.
        try:
            Base.metadata.create_all(bind=engine)
            self._ensure_action_state_schema()
            self._ensure_session_tags_schema()
        except OperationalError as exc:
            logger.warning("ChatService create_all skipped due to database operational error: %s", exc)

    def _ensure_action_state_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("action_states")}
        except Exception:
            return

        statements: list[str] = []
        if "invocation_id" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN invocation_id VARCHAR")
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_action_states_invocation ON action_states (session_id, invocation_id)"
        )

        if not statements:
            return

        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def _ensure_session_tags_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("sessions")}
        except Exception:
            return

        if "tags_json" in columns:
            return

        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE sessions ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'"))

    @staticmethod
    def _normalize_tag(tag: str) -> str:
        lowered = TAG_SYNONYMS.get(tag.strip().lower(), tag.strip().lower())
        normalized = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
        return normalized

    def _normalize_tags(self, tags: List[str]) -> List[str]:
        seen: set[str] = set()
        normalized_tags: List[str] = []
        for tag in tags:
            norm = self._normalize_tag(tag)
            if not norm or norm in TAG_STOPWORDS or norm in seen:
                continue
            seen.add(norm)
            normalized_tags.append(norm)
            if len(normalized_tags) >= TAG_MAX_COUNT:
                break
        return normalized_tags

    def _parse_tags(self, raw_tags: Optional[str]) -> List[str]:
        if not raw_tags:
            return []
        try:
            parsed = json.loads(raw_tags)
            if not isinstance(parsed, list):
                return []
        except Exception:
            return []
        return self._normalize_tags([str(item) for item in parsed if isinstance(item, (str, int, float))])

    def _derive_tags_from_texts(self, texts: List[str]) -> List[str]:
        keywords: List[str] = []
        for text_block in texts:
            words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b", text_block.lower())
            for word in words:
                if word in TAG_STOPWORDS:
                    continue
                keywords.append(word)

        return self._normalize_tags(keywords)

    def _migrate_from_json(self):
        if not os.path.exists(OLD_CHATS_FILE):
            return
        
        print("Migrating old JSON chats to database via ORM...")
        try:
            with open(OLD_CHATS_FILE, 'r') as f:
                old_data = json.load(f)
            
            with SessionLocal() as db:
                for chat in old_data:
                    # Check if session exists
                    if db.query(SessionModel).filter(SessionModel.id == chat['id']).first():
                        continue
                    
                    # Insert session
                    new_session = SessionModel(
                        id=chat['id'],
                        title=chat['title'],
                        agent_id=chat.get('agent_id'),
                        created_at=datetime.fromisoformat(chat['created_at']) if isinstance(chat['created_at'], str) else chat['created_at'],
                        updated_at=datetime.fromisoformat(chat['updated_at']) if isinstance(chat['updated_at'], str) else chat['updated_at']
                    )
                    db.add(new_session)
                    
                    # Insert messages
                    for msg in chat.get('messages', []):
                        new_msg = MessageModel(
                            session_id=chat['id'],
                            role=msg['role'],
                            content=msg['content'],
                            timestamp=datetime.fromisoformat(msg['timestamp']) if isinstance(msg['timestamp'], str) else msg['timestamp']
                        )
                        db.add(new_msg)
                
                db.commit()
            
            # Rename old file to backup
            os.rename(OLD_CHATS_FILE, OLD_CHATS_FILE + ".bak")
            print("Migration completed successfully.")
        except Exception as e:
            print(f"Migration error: {e}")

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
            for s in sessions_query:
                parsed_tags = self._parse_tags(getattr(s, "tags_json", "[]"))
                if normalized_filter_tags:
                    if normalized_tag_mode == "all":
                        if not all(tag in parsed_tags for tag in normalized_filter_tags):
                            continue
                    elif not any(tag in parsed_tags for tag in normalized_filter_tags):
                        continue

                messages_query = db.query(MessageModel).filter(MessageModel.session_id == s.id).order_by(MessageModel.timestamp).all()
                messages = []
                for m in messages_query:
                    msg_dict = {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": self._to_api_datetime(m.timestamp),
                        "assistant_turn_id": m.assistant_turn_id,
                        "run_id": m.run_id,
                        "thought_duration": m.thought_duration,
                        "ttft": m.ttft,
                        "total_duration": m.total_duration,
                        "prompt_tokens": m.prompt_tokens,
                        "completion_tokens": m.completion_tokens,
                        "total_tokens": m.total_tokens,
                        "finish_reason": m.finish_reason,
                    }
                    if m.images:
                        try:
                            msg_dict['images'] = json.loads(m.images)
                        except:
                            msg_dict['images'] = []
                    
                    msg_dict['supports_reasoning'] = bool(m.supports_reasoning) if m.supports_reasoning is not None else None
                    msg_dict['deep_thinking_enabled'] = bool(m.deep_thinking_enabled) if m.deep_thinking_enabled is not None else None
                    msg_dict['reasoning_enabled'] = bool(m.reasoning_enabled) if m.reasoning_enabled is not None else None
                    
                    messages.append(Message(**msg_dict))
                
                result.append(ChatSession(
                    id=s.id,
                    title=s.title,
                    summary=s.summary,
                    agent_id=s.agent_id,
                    active_skill_name=s.active_skill_name,
                    active_skill_version=s.active_skill_version,
                    tags=parsed_tags,
                    messages=messages,
                    created_at=self._to_api_datetime(s.created_at),
                    updated_at=self._to_api_datetime(s.updated_at)
                ))
            return result

    def get_chat(self, chat_id: str) -> Optional[ChatSession]:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not s:
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
            for m in messages_query:
                msg_dict = {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": self._to_api_datetime(m.timestamp),
                    "assistant_turn_id": m.assistant_turn_id,
                    "run_id": m.run_id,
                    "thought_duration": m.thought_duration,
                    "ttft": m.ttft,
                    "total_duration": m.total_duration,
                    "prompt_tokens": m.prompt_tokens,
                    "completion_tokens": m.completion_tokens,
                    "total_tokens": m.total_tokens,
                    "finish_reason": m.finish_reason,
                }
                
                if m.images:
                    try:
                        msg_dict['images'] = json.loads(m.images)
                    except:
                        msg_dict['images'] = []
                
                msg_dict['supports_reasoning'] = bool(m.supports_reasoning) if m.supports_reasoning is not None else None
                msg_dict['deep_thinking_enabled'] = bool(m.deep_thinking_enabled) if m.deep_thinking_enabled is not None else None
                msg_dict['reasoning_enabled'] = bool(m.reasoning_enabled) if m.reasoning_enabled is not None else None
                
                if msg_dict['role'] == 'assistant':
                    turn_id = msg_dict.get("assistant_turn_id")
                    if turn_id:
                        msg_dict['tool_calls'] = [tc.model_dump() for tc in tool_calls_by_turn.get(turn_id, [])]
                    else:
                        msg_dict['tool_calls'] = [tc.model_dump() for tc in legacy_tool_calls]
                
                messages.append(Message(**msg_dict))
            
            return ChatSession(
                id=s.id,
                title=s.title,
                summary=s.summary,
                agent_id=s.agent_id,
                active_skill_name=s.active_skill_name,
                active_skill_version=s.active_skill_version,
                tags=self._parse_tags(getattr(s, "tags_json", "[]")),
                messages=messages,
                created_at=self._to_api_datetime(s.created_at),
                updated_at=self._to_api_datetime(s.updated_at)
            )

    def create_chat(self, agent_id: Optional[str] = None, title: str = "New Chat") -> ChatSession:
        chat_id = str(uuid.uuid4())
        now = datetime.utcnow()
        with SessionLocal() as db:
            new_session = SessionModel(
                id=chat_id,
                title=title,
                agent_id=agent_id,
                created_at=now,
                updated_at=now
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
        
        return ChatSession(
            id=chat_id,
            title=title,
            summary=None,
            agent_id=agent_id,
            active_skill_name=None,
            active_skill_version=None,
            tags=[],
            messages=[],
            created_at=self._to_api_datetime(now),
            updated_at=self._to_api_datetime(now)
        )

    def update_chat_title(self, chat_id: str, title: str) -> bool:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not s:
                return False
            s.title = title
            s.updated_at = datetime.utcnow()
            db.commit()
            return True

    def update_chat_summary(self, chat_id: str, summary: Optional[str]) -> bool:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not s:
                return False
            s.summary = summary
            messages_query = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(desc(MessageModel.timestamp)).limit(12).all()
            source_texts = [s.title or "", summary or ""] + [m.content for m in messages_query if m.content]
            s.tags_json = json.dumps(self._derive_tags_from_texts(source_texts))
            s.updated_at = datetime.utcnow()
            db.commit()
            return True

    def generate_chat_tags(self, chat_id: str) -> Optional[List[str]]:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not s:
                return None

            messages_query = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(desc(MessageModel.timestamp)).limit(12).all()
            source_texts = [s.title or "", s.summary or ""] + [m.content for m in messages_query if m.content]
            derived_tags = self._derive_tags_from_texts(source_texts)
            s.tags_json = json.dumps(derived_tags)
            s.updated_at = datetime.utcnow()
            db.commit()
            return derived_tags

    def get_session_skill(self, chat_id: str) -> tuple[Optional[str], Optional[str]]:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not s:
                return None, None
            return s.active_skill_name, s.active_skill_version

    def set_session_skill(self, chat_id: str, name: str, version: str) -> None:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if s:
                s.active_skill_name = name
                s.active_skill_version = version
                s.updated_at = datetime.utcnow()
                db.commit()

    def clear_session_skill(self, chat_id: str) -> None:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if s:
                s.active_skill_name = None
                s.active_skill_version = None
                s.updated_at = datetime.utcnow()
                db.commit()

    def add_message(
        self, 
        chat_id: str, 
        role: str, 
        content: str, 
        thought_duration: Optional[float] = None, 
        images: Optional[List[str]] = None, 
        ttft: Optional[float] = None, 
        total_duration: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        finish_reason: Optional[str] = None,
        assistant_turn_id: Optional[str] = None,
        run_id: Optional[str] = None,
        supports_reasoning: Optional[bool] = None,
        deep_thinking_enabled: Optional[bool] = None,
        reasoning_enabled: Optional[bool] = None
    ) -> Optional[ChatSession]:
        now = datetime.utcnow()
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if not s:
                return None
            
            images_json = json.dumps(images) if images else None
            
            new_msg = MessageModel(
                session_id=chat_id,
                role=role,
                content=content,
                images=images_json,
                timestamp=now,
                assistant_turn_id=assistant_turn_id,
                run_id=run_id,
                supports_reasoning=None if supports_reasoning is None else (1 if supports_reasoning else 0),
                deep_thinking_enabled=None if deep_thinking_enabled is None else (1 if deep_thinking_enabled else 0),
                reasoning_enabled=None if reasoning_enabled is None else (1 if reasoning_enabled else 0),
                thought_duration=thought_duration,
                ttft=ttft,
                total_duration=total_duration,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                finish_reason=finish_reason
            )
            db.add(new_msg)
            
            if role == "user":
                msg_count = db.query(MessageModel).filter(MessageModel.session_id == chat_id).count()
                if msg_count == 0 and s.title == "New Chat":  # 0 because new_msg is not flushed yet
                    new_title = content[:30] + "..." if len(content) > 30 else content
                    s.title = new_title

            if role in {"user", "assistant"}:
                seed_texts = [s.title or "", s.summary or "", content or ""]
                existing_tags = self._parse_tags(getattr(s, "tags_json", "[]"))
                s.tags_json = json.dumps(self._normalize_tags(existing_tags + self._derive_tags_from_texts(seed_texts)))
            
            s.updated_at = now
            db.commit()
            
        return self.get_chat(chat_id)

    def delete_chat(self, chat_id: str) -> bool:
        with SessionLocal() as db:
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if s:
                db.delete(s)
                db.commit()
                return True
            return False

    def truncate_chat(self, chat_id: str, keep_count: int) -> bool:
        with SessionLocal() as db:
            messages = db.query(MessageModel).filter(MessageModel.session_id == chat_id).order_by(MessageModel.timestamp).all()
            if len(messages) <= keep_count:
                return False
            
            to_delete = messages[keep_count:]
            for msg in to_delete:
                db.delete(msg)
            
            s = db.query(SessionModel).filter(SessionModel.id == chat_id).first()
            if s:
                s.updated_at = datetime.utcnow()
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
        started_ts: Optional[datetime] = None
    ) -> None:
        now = datetime.utcnow()
        args_json = json.dumps(args) if args else None
        with SessionLocal() as db:
            tc = ToolCallModel(
                session_id=session_id,
                call_id=call_id,
                tool_name=tool_name,
                assistant_turn_id=assistant_turn_id,
                run_id=run_id,
                event_id_started=event_id_started,
                started_sequence=started_sequence,
                started_ts=started_ts or now,
                args=args_json,
                status='running',
                created_at=now
            )
            db.add(tc)
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
        finished_ts: Optional[datetime] = None
    ) -> None:
        now = datetime.utcnow()
        with SessionLocal() as db:
            tc = db.query(ToolCallModel).filter(ToolCallModel.call_id == call_id).first()
            if tc:
                tc.status = status
                tc.result = result
                tc.error = error
                tc.event_id_finished = event_id_finished
                tc.finished_sequence = finished_sequence
                tc.finished_ts = finished_ts or now
                tc.finished_at = now
                tc.duration_ms = duration_ms
                db.commit()

    def get_tool_calls(self, session_id: str) -> List[ToolCall]:
        with SessionLocal() as db:
            # We can't do exact COALESCE order_by easily in basic SQLAlchemy without func.coalesce
            query = db.query(ToolCallModel).filter(ToolCallModel.session_id == session_id)\
                .order_by(
                    func.coalesce(ToolCallModel.started_sequence, ToolCallModel.finished_sequence, 0).asc(),
                    func.coalesce(ToolCallModel.started_ts, ToolCallModel.finished_ts, ToolCallModel.created_at).asc()
                ).all()
            
            tool_calls = []
            for tc in query:
                tool_dict = {
                    "id": tc.id,
                    "session_id": tc.session_id,
                    "message_id": tc.message_id,
                    "call_id": tc.call_id,
                    "tool_name": tc.tool_name,
                    "assistant_turn_id": tc.assistant_turn_id,
                    "run_id": tc.run_id,
                    "event_id_started": tc.event_id_started,
                    "event_id_finished": tc.event_id_finished,
                    "started_sequence": tc.started_sequence,
                    "finished_sequence": tc.finished_sequence,
                    "started_ts": tc.started_ts,
                    "finished_ts": tc.finished_ts,
                    "result": tc.result,
                    "error": tc.error,
                    "status": tc.status,
                    "created_at": tc.created_at,
                    "finished_at": tc.finished_at,
                    "duration_ms": tc.duration_ms
                }
                
                if tc.args:
                    try:
                        tool_dict['args'] = json.loads(tc.args)
                    except:
                        tool_dict['args'] = {}
                else:
                    tool_dict['args'] = {}
                
                tool_calls.append(ToolCall(**tool_dict))
            return tool_calls

    def get_chat_events(
        self,
        session_id: str,
        assistant_turn_id: Optional[str] = None,
        after_sequence: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        with SessionLocal() as db:
            msg_query = db.query(MessageModel).filter(
                MessageModel.session_id == session_id,
                MessageModel.role == 'assistant'
            )
            if assistant_turn_id:
                msg_query = msg_query.filter(MessageModel.assistant_turn_id == assistant_turn_id)
            messages = msg_query.order_by(MessageModel.timestamp.asc()).all()

            tc_query = db.query(ToolCallModel).filter(ToolCallModel.session_id == session_id)
            if assistant_turn_id:
                tc_query = tc_query.filter(ToolCallModel.assistant_turn_id == assistant_turn_id)
            tool_calls = tc_query.order_by(
                func.coalesce(ToolCallModel.started_sequence, ToolCallModel.finished_sequence, 0).asc(),
                func.coalesce(ToolCallModel.started_ts, ToolCallModel.finished_ts, ToolCallModel.created_at).asc()
            ).all()
            action_query = db.query(ActionEventModel).filter(ActionEventModel.session_id == session_id)
            if assistant_turn_id:
                action_query = action_query.filter(ActionEventModel.assistant_turn_id == assistant_turn_id)
            action_events = action_query.order_by(
                func.coalesce(ActionEventModel.sequence, 0).asc(),
                ActionEventModel.created_at.asc()
            ).all()

        for m in messages:
            turn_id = m.assistant_turn_id
            run_id = m.run_id
            if not turn_id or not run_id:
                continue
            ts = m.timestamp.isoformat() if m.timestamp else ""
            reasoning_enabled = bool(m.reasoning_enabled) if m.reasoning_enabled is not None else False
            supports_reasoning = bool(m.supports_reasoning) if m.supports_reasoning is not None else False
            deep_thinking_enabled = bool(m.deep_thinking_enabled) if m.deep_thinking_enabled is not None else False
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
                        "reasoning_enabled": reasoning_enabled
                    }
                },
                "meta": {
                    "supports_reasoning": supports_reasoning,
                    "deep_thinking_enabled": deep_thinking_enabled,
                    "reasoning_enabled": reasoning_enabled
                }
            })
            events.append({
                "version": "v2",
                "event": "content.final",
                "event_id": f"replay_content_{session_id}_{turn_id}",
                "run_id": run_id,
                "assistant_turn_id": turn_id,
                "sequence": 999999,
                "ts": ts,
                "payload": {"content": m.content or ""},
                "content": m.content or ""
            })

        for tc in tool_calls:
            turn_id = tc.assistant_turn_id
            run_id = tc.run_id
            if not turn_id or not run_id:
                continue
            
            start_ts_val = tc.started_ts or tc.created_at
            finish_ts_val = tc.finished_ts or tc.finished_at
            start_ts = start_ts_val.isoformat() if start_ts_val else ""
            finish_ts = finish_ts_val.isoformat() if finish_ts_val else ""
            
            if tc.args:
                try:
                    parsed_args = json.loads(tc.args)
                except Exception:
                    parsed_args = {}
            else:
                parsed_args = {}
                
            if tc.started_sequence:
                events.append({
                    "version": "v2",
                    "event": "tool.call.started",
                    "event_id": tc.event_id_started or f"replay_started_{tc.call_id}",
                    "run_id": run_id,
                    "assistant_turn_id": turn_id,
                    "sequence": tc.started_sequence,
                    "ts": start_ts,
                    "payload": {
                        "call_id": tc.call_id,
                        "tool_name": tc.tool_name,
                        "args": parsed_args
                    },
                    "call_id": tc.call_id,
                    "tool_name": tc.tool_name,
                    "args": parsed_args
                })
            if tc.finished_sequence:
                events.append({
                    "version": "v2",
                    "event": "tool.call.finished",
                    "event_id": tc.event_id_finished or f"replay_finished_{tc.call_id}",
                    "run_id": run_id,
                    "assistant_turn_id": turn_id,
                    "sequence": tc.finished_sequence,
                    "ts": finish_ts,
                    "payload": {
                        "call_id": tc.call_id,
                        "tool_name": tc.tool_name,
                        "result": tc.result,
                        "error": tc.error,
                        "duration_ms": tc.duration_ms
                    },
                    "call_id": tc.call_id,
                    "tool_name": tc.tool_name,
                    "result": tc.result,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms
                })

        for ae in action_events:
            try:
                payload = json.loads(ae.payload_json)
            except Exception:
                payload = {"event": ae.event_name}
            event_envelope = {
                "version": "v2",
                "event": ae.event_name,
                "event_id": ae.event_id or f"replay_action_{ae.id}",
                "run_id": ae.run_id,
                "assistant_turn_id": ae.assistant_turn_id,
                "sequence": ae.sequence or 0,
                "ts": ae.ts or "",
                "payload": payload,
            }
            if isinstance(payload, dict):
                event_envelope.update(payload)
            events.append(event_envelope)

        events.sort(key=lambda item: (str(item.get("run_id") or ""), int(item.get("sequence") or 0), str(item.get("ts") or "")))
        if after_sequence is not None:
            events = [event for event in events if int(event.get("sequence") or 0) > int(after_sequence)]
        return events

    def get_chat_trace_bundle(
        self,
        session_id: str,
        *,
        assistant_turn_id: Optional[str] = None,
        mode: str = "summary",
    ) -> Optional[Dict[str, Any]]:
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
            trace_query = db.query(ActionEventModel).filter(
                ActionEventModel.session_id == session_id,
                ActionEventModel.event_name == "tool.trace.record",
                ActionEventModel.run_id == snapshot_record.run_id,
                ActionEventModel.assistant_turn_id == snapshot_record.assistant_turn_id,
            ).order_by(
                func.coalesce(ActionEventModel.sequence, 0).asc(),
                ActionEventModel.created_at.asc(),
                ActionEventModel.id.asc(),
            )
            trace_rows = trace_query.all()

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
        summary_snapshot.redaction = {
            **summary_snapshot.redaction,
            "system_prompt": True,
            "mode": "summary",
        }

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
    ) -> None:
        skill_name = event.get("skill_name")
        action_id = event.get("action_id")
        lifecycle_status = event.get("lifecycle_status")
        if not skill_name or not action_id or not lifecycle_status:
            return

        skill_version = event.get("skill_version")
        invocation_id = event.get("invocation_id")
        approval_token = event.get("approval_token")
        request_id = event.get("request_id")
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
        state.payload_json = json.dumps(event)

    def _build_action_state_model(self, state: ActionStateModel) -> ActionState:
        try:
            payload = json.loads(state.payload_json)
        except Exception:
            payload = {}
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
            payload=payload,
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

    def get_action_state(
        self,
        session_id: str,
        *,
        skill_name: str,
        action_id: str,
    ) -> Optional[ActionState]:
        with SessionLocal() as db:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.skill_name == skill_name,
                ActionStateModel.action_id == action_id,
            ).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).first()
            if state is None:
                return None
            return self._build_action_state_model(state)

    def get_action_state_by_invocation_id(
        self,
        session_id: str,
        *,
        invocation_id: str,
    ) -> Optional[ActionState]:
        with SessionLocal() as db:
            state = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id,
                ActionStateModel.invocation_id == invocation_id,
            ).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).first()
            if state is None:
                return None
            return self._build_action_state_model(state)

    def get_action_state_by_approval_token(
        self,
        session_id: str,
        *,
        approval_token: str,
    ) -> Optional[ActionState]:
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
            rows = db.query(ActionStateModel).filter(
                ActionStateModel.session_id == session_id
            ).order_by(ActionStateModel.updated_at.desc(), ActionStateModel.id.desc()).all()
            result: List[ActionState] = []
            for state in rows:
                result.append(self._build_action_state_model(state))
            return result

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
            self._upsert_action_state(
                db,
                session_id=session_id,
                event=event,
                assistant_turn_id=assistant_turn_id,
                run_id=run_id,
            )
            db.commit()

    def add_skill_effectiveness_event(self, session_id: str, event: Dict[str, Any]) -> None:
        now = datetime.utcnow()
        selected = event.get("selected_skill") or {}
        with SessionLocal() as db:
            se = SkillEventModel(
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
                created_at=now
            )
            db.add(se)
            db.commit()

    def get_skill_effectiveness_report(self, hours: int = 24) -> Dict[str, Any]:
        hours = max(1, int(hours))
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        
        with SessionLocal() as db:
            base_query = db.query(SkillEventModel).filter(SkillEventModel.created_at >= time_threshold)
            
            total_runs = base_query.count()
            
            fallback_runs = db.query(func.sum(SkillEventModel.fallback_used)).filter(
                SkillEventModel.created_at >= time_threshold
            ).scalar() or 0
            
            override_hits = db.query(func.sum(SkillEventModel.override_hit)).filter(
                SkillEventModel.created_at >= time_threshold
            ).scalar() or 0
            
            avg_selection_score = db.query(func.avg(SkillEventModel.selection_score)).filter(
                SkillEventModel.created_at >= time_threshold
            ).scalar() or 0.0
            
            avg_sys_tokens = db.query(func.avg(SkillEventModel.system_prompt_tokens_estimate)).filter(
                SkillEventModel.created_at >= time_threshold
            ).scalar() or 0.0
            
            avg_usr_tokens = db.query(func.avg(SkillEventModel.user_message_tokens_estimate)).filter(
                SkillEventModel.created_at >= time_threshold
            ).scalar() or 0.0
            
            reason_rows = db.query(
                SkillEventModel.reason_code, func.count(SkillEventModel.id).label('cnt')
            ).filter(SkillEventModel.created_at >= time_threshold)\
             .group_by(SkillEventModel.reason_code)\
             .order_by(desc('cnt')).all()
             
            skill_rows = db.query(
                SkillEventModel.selected_skill_name, func.count(SkillEventModel.id).label('cnt')
            ).filter(
                SkillEventModel.created_at >= time_threshold,
                SkillEventModel.selected_skill_name.isnot(None)
            ).group_by(SkillEventModel.selected_skill_name)\
             .order_by(desc('cnt')).limit(10).all()
             
            layer_rows = db.query(
                SkillEventModel.selected_skill_source_layer, func.count(SkillEventModel.id).label('cnt')
            ).filter(
                SkillEventModel.created_at >= time_threshold,
                SkillEventModel.selected_skill_source_layer.isnot(None)
            ).group_by(SkillEventModel.selected_skill_source_layer)\
             .order_by(desc('cnt')).all()

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

chat_service = ChatService()

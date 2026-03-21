import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, desc, func, case
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal, engine, Base
from app.models.chat import (
    Session as SessionModel,
    Message as MessageModel,
    ToolCall as ToolCallModel,
    SkillEffectivenessEvent as SkillEventModel
)

DATA_DIR = os.path.expanduser(os.getenv("YUE_DATA_DIR", "~/.yue/data"))
OLD_CHATS_FILE = os.path.join(DATA_DIR, "chats.json")

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

class ChatSession(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    agent_id: Optional[str] = None
    active_skill_name: Optional[str] = None
    active_skill_version: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime
    updated_at: datetime

class ChatService:
    def __init__(self):
        self._ensure_db()
        self._migrate_from_json()

    def _ensure_db(self):
        # We now rely on Alembic for migrations, but for local SQLite we can still do create_all
        # to ensure tables exist if someone doesn't run migrations.
        # Alembic will take over schema changes.
        Base.metadata.create_all(bind=engine)

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

    def list_chats(self) -> List[ChatSession]:
        with SessionLocal() as db:
            sessions_query = db.query(SessionModel).order_by(desc(SessionModel.updated_at)).all()
            result = []
            for s in sessions_query:
                messages_query = db.query(MessageModel).filter(MessageModel.session_id == s.id).order_by(MessageModel.timestamp).all()
                messages = []
                for m in messages_query:
                    msg_dict = {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp,
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
                    messages=messages,
                    created_at=s.created_at,
                    updated_at=s.updated_at
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
                    "timestamp": m.timestamp,
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
                messages=messages,
                created_at=s.created_at,
                updated_at=s.updated_at
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
            messages=[],
            created_at=now,
            updated_at=now
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
            s.updated_at = datetime.utcnow()
            db.commit()
            return True

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

        events.sort(key=lambda item: (str(item.get("run_id") or ""), int(item.get("sequence") or 0), str(item.get("ts") or "")))
        if after_sequence is not None:
            events = [event for event in events if int(event.get("sequence") or 0) > int(after_sequence)]
        return events

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

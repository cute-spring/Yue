from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    agent_id = Column(String, nullable=True)
    active_skill_name = Column(String, nullable=True)
    active_skill_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="session", cascade="all, delete-orphan")
    skill_events = relationship("SkillEffectivenessEvent", back_populates="session", cascade="all, delete-orphan")
    action_events = relationship("ActionEvent", back_populates="session", cascade="all, delete-orphan")
    action_states = relationship("ActionState", back_populates="session", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    images = Column(Text, nullable=True)  # JSON string of images
    timestamp = Column(DateTime, default=datetime.utcnow)
    assistant_turn_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    supports_reasoning = Column(Integer, nullable=True)
    deep_thinking_enabled = Column(Integer, nullable=True)
    reasoning_enabled = Column(Integer, nullable=True)
    thought_duration = Column(Float, nullable=True)
    ttft = Column(Float, nullable=True)
    total_duration = Column(Float, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    finish_reason = Column(String, nullable=True)
    embedding = Column(Text, nullable=True)

    session = relationship("Session", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_messages_session_id", "session_id"),
        Index("idx_messages_turn_id", "assistant_turn_id"),
    )

class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    call_id = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    assistant_turn_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    event_id_started = Column(String, nullable=True)
    event_id_finished = Column(String, nullable=True)
    started_sequence = Column(Integer, nullable=True)
    finished_sequence = Column(Integer, nullable=True)
    started_ts = Column(DateTime, nullable=True)
    finished_ts = Column(DateTime, nullable=True)
    args = Column(Text, nullable=True)  # JSON string
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)

    session = relationship("Session", back_populates="tool_calls")
    message = relationship("Message", back_populates="tool_calls")

    __table_args__ = (
        Index("idx_tool_calls_session_id", "session_id"),
        Index("idx_tool_calls_call_id", "call_id"),
        Index("idx_tool_calls_session_turn_created", "session_id", "assistant_turn_id", "created_at"),
        Index("idx_tool_calls_run_sequence", "run_id", "created_at"),
    )

class SkillEffectivenessEvent(Base):
    __tablename__ = "skill_effectiveness_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    reason_code = Column(String, nullable=False)
    selection_source = Column(String, nullable=False)
    fallback_used = Column(Integer, nullable=False)
    selected_skill_name = Column(String, nullable=True)
    selected_skill_version = Column(String, nullable=True)
    selected_skill_source_layer = Column(String, nullable=True)
    override_hit = Column(Integer, nullable=True)
    visible_skill_count = Column(Integer, nullable=True)
    available_skill_count = Column(Integer, nullable=True)
    always_injected_count = Column(Integer, nullable=True)
    summary_injected = Column(Integer, nullable=True)
    summary_prompt_enabled = Column(Integer, nullable=True)
    lazy_full_load_enabled = Column(Integer, nullable=True)
    selection_score = Column(Integer, nullable=True)
    system_prompt_tokens_estimate = Column(Integer, nullable=True)
    user_message_tokens_estimate = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="skill_events")

    __table_args__ = (
        Index("idx_skill_effectiveness_session_id", "session_id"),
        Index("idx_skill_effectiveness_created_at", "created_at"),
    )


class ActionEvent(Base):
    __tablename__ = "action_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    assistant_turn_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    event_name = Column(String, nullable=False)
    event_id = Column(String, nullable=True)
    sequence = Column(Integer, nullable=True)
    ts = Column(String, nullable=True)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="action_events")

    __table_args__ = (
        Index("idx_action_events_session_id", "session_id"),
        Index("idx_action_events_turn_id", "assistant_turn_id"),
        Index("idx_action_events_run_sequence", "run_id", "sequence"),
    )


class ActionState(Base):
    __tablename__ = "action_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String, nullable=False)
    skill_version = Column(String, nullable=True)
    action_id = Column(String, nullable=False)
    invocation_id = Column(String, nullable=True)
    approval_token = Column(String, nullable=True)
    request_id = Column(String, nullable=True)
    run_id = Column(String, nullable=True)
    assistant_turn_id = Column(String, nullable=True)
    lifecycle_phase = Column(String, nullable=True)
    lifecycle_status = Column(String, nullable=False)
    status = Column(String, nullable=True)
    payload_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="action_states")

    __table_args__ = (
        Index("idx_action_states_session_id", "session_id"),
        Index("idx_action_states_lookup", "session_id", "skill_name", "action_id"),
        Index("idx_action_states_invocation", "session_id", "invocation_id"),
        Index("idx_action_states_approval_token", "approval_token"),
        Index("idx_action_states_request", "request_id"),
    )

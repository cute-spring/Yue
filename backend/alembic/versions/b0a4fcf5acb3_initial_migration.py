"""Initial migration

Revision ID: b0a4fcf5acb3
Revises: 
Create Date: 2026-03-21 10:35:54.590347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0a4fcf5acb3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("active_skill_name", sa.String(), nullable=True),
        sa.Column("active_skill_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("images", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("assistant_turn_id", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("supports_reasoning", sa.Integer(), nullable=True),
        sa.Column("deep_thinking_enabled", sa.Integer(), nullable=True),
        sa.Column("reasoning_enabled", sa.Integer(), nullable=True),
        sa.Column("thought_duration", sa.Float(), nullable=True),
        sa.Column("ttft", sa.Float(), nullable=True),
        sa.Column("total_duration", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_messages_session_id", "messages", ["session_id"], unique=False)
    op.create_index("idx_messages_turn_id", "messages", ["assistant_turn_id"], unique=False)

    op.create_table(
        "tool_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("call_id", sa.String(), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("assistant_turn_id", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("event_id_started", sa.String(), nullable=True),
        sa.Column("event_id_finished", sa.String(), nullable=True),
        sa.Column("started_sequence", sa.Integer(), nullable=True),
        sa.Column("finished_sequence", sa.Integer(), nullable=True),
        sa.Column("started_ts", sa.DateTime(), nullable=True),
        sa.Column("finished_ts", sa.DateTime(), nullable=True),
        sa.Column("args", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_tool_calls_session_id", "tool_calls", ["session_id"], unique=False)
    op.create_index("idx_tool_calls_call_id", "tool_calls", ["call_id"], unique=False)
    op.create_index(
        "idx_tool_calls_session_turn_created",
        "tool_calls",
        ["session_id", "assistant_turn_id", "created_at"],
        unique=False,
    )
    op.create_index("idx_tool_calls_run_sequence", "tool_calls", ["run_id", "created_at"], unique=False)

    op.create_table(
        "skill_effectiveness_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("selection_source", sa.String(), nullable=False),
        sa.Column("fallback_used", sa.Integer(), nullable=False),
        sa.Column("selected_skill_name", sa.String(), nullable=True),
        sa.Column("selected_skill_version", sa.String(), nullable=True),
        sa.Column("selected_skill_source_layer", sa.String(), nullable=True),
        sa.Column("override_hit", sa.Integer(), nullable=True),
        sa.Column("visible_skill_count", sa.Integer(), nullable=True),
        sa.Column("available_skill_count", sa.Integer(), nullable=True),
        sa.Column("always_injected_count", sa.Integer(), nullable=True),
        sa.Column("summary_injected", sa.Integer(), nullable=True),
        sa.Column("summary_prompt_enabled", sa.Integer(), nullable=True),
        sa.Column("lazy_full_load_enabled", sa.Integer(), nullable=True),
        sa.Column("selection_score", sa.Integer(), nullable=True),
        sa.Column("system_prompt_tokens_estimate", sa.Integer(), nullable=True),
        sa.Column("user_message_tokens_estimate", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_skill_effectiveness_session_id",
        "skill_effectiveness_events",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "idx_skill_effectiveness_created_at",
        "skill_effectiveness_events",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "action_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("assistant_turn_id", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("ts", sa.String(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_action_events_session_id", "action_events", ["session_id"], unique=False)
    op.create_index("idx_action_events_turn_id", "action_events", ["assistant_turn_id"], unique=False)
    op.create_index("idx_action_events_run_sequence", "action_events", ["run_id", "sequence"], unique=False)

    op.create_table(
        "action_states",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("skill_name", sa.String(), nullable=False),
        sa.Column("skill_version", sa.String(), nullable=True),
        sa.Column("action_id", sa.String(), nullable=False),
        sa.Column("invocation_id", sa.String(), nullable=True),
        sa.Column("approval_token", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("assistant_turn_id", sa.String(), nullable=True),
        sa.Column("lifecycle_phase", sa.String(), nullable=True),
        sa.Column("lifecycle_status", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("observability_started_at", sa.String(), nullable=True),
        sa.Column("observability_finished_at", sa.String(), nullable=True),
        sa.Column("observability_duration_ms", sa.Integer(), nullable=True),
        sa.Column("observability_error_kind", sa.String(), nullable=True),
        sa.Column("observability_retryable", sa.Boolean(), nullable=True),
        sa.Column("observability_artifact_path", sa.String(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_action_states_session_id", "action_states", ["session_id"], unique=False)
    op.create_index(
        "idx_action_states_lookup",
        "action_states",
        ["session_id", "skill_name", "action_id"],
        unique=False,
    )
    op.create_index(
        "idx_action_states_invocation",
        "action_states",
        ["session_id", "invocation_id"],
        unique=False,
    )
    op.create_index("idx_action_states_approval_token", "action_states", ["approval_token"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_action_states_approval_token", table_name="action_states")
    op.drop_index("idx_action_states_invocation", table_name="action_states")
    op.drop_index("idx_action_states_lookup", table_name="action_states")
    op.drop_index("idx_action_states_session_id", table_name="action_states")
    op.drop_table("action_states")

    op.drop_index("idx_action_events_run_sequence", table_name="action_events")
    op.drop_index("idx_action_events_turn_id", table_name="action_events")
    op.drop_index("idx_action_events_session_id", table_name="action_events")
    op.drop_table("action_events")

    op.drop_index("idx_skill_effectiveness_created_at", table_name="skill_effectiveness_events")
    op.drop_index("idx_skill_effectiveness_session_id", table_name="skill_effectiveness_events")
    op.drop_table("skill_effectiveness_events")

    op.drop_index("idx_tool_calls_run_sequence", table_name="tool_calls")
    op.drop_index("idx_tool_calls_session_turn_created", table_name="tool_calls")
    op.drop_index("idx_tool_calls_call_id", table_name="tool_calls")
    op.drop_index("idx_tool_calls_session_id", table_name="tool_calls")
    op.drop_table("tool_calls")

    op.drop_index("idx_messages_turn_id", table_name="messages")
    op.drop_index("idx_messages_session_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("sessions")

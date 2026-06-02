import json
import os
import re
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import Base, SessionLocal, engine
from app.models.chat import Message as MessageModel
from app.models.chat import Session as SessionModel
from .chat_service_models import OLD_CHATS_FILE, TAG_MAX_COUNT, TAG_STOPWORDS, TAG_SYNONYMS, logger


class ChatServiceSchemaMixin:
    @staticmethod
    def _to_api_datetime(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _ensure_db(self):
        try:
            Base.metadata.create_all(bind=engine)
            self._ensure_action_state_schema()
            self._ensure_session_workspace_schema()
            self._ensure_session_tags_schema()
            self._ensure_message_attachments_schema()
            self._ensure_message_continuation_schema()
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
        if "observability_started_at" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN observability_started_at VARCHAR")
        if "observability_finished_at" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN observability_finished_at VARCHAR")
        if "observability_duration_ms" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN observability_duration_ms INTEGER")
        if "observability_error_kind" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN observability_error_kind VARCHAR")
        if "observability_retryable" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN observability_retryable BOOLEAN")
        if "observability_artifact_path" not in columns:
            statements.append("ALTER TABLE action_states ADD COLUMN observability_artifact_path VARCHAR")
        statements.append("CREATE INDEX IF NOT EXISTS idx_action_states_invocation ON action_states (session_id, invocation_id)")

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

    def _ensure_session_workspace_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("sessions")}
        except Exception:
            return

        statements: list[str] = []
        if "workspace_id" not in columns:
            statements.append("ALTER TABLE sessions ADD COLUMN workspace_id VARCHAR")
        statements.append("CREATE INDEX IF NOT EXISTS idx_sessions_workspace_id ON sessions (workspace_id)")

        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def _ensure_message_attachments_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("messages")}
        except Exception:
            return
        if "attachments" in columns:
            return
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE messages ADD COLUMN attachments TEXT"))

    def _ensure_message_continuation_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("messages")}
        except Exception:
            return

        statements: list[str] = []
        if "continuation_of" not in columns:
            statements.append("ALTER TABLE messages ADD COLUMN continuation_of VARCHAR")
        if "continuation_root_id" not in columns:
            statements.append("ALTER TABLE messages ADD COLUMN continuation_root_id VARCHAR")
        if "continuation_status" not in columns:
            statements.append("ALTER TABLE messages ADD COLUMN continuation_status VARCHAR")
        if "content_type" not in columns:
            statements.append("ALTER TABLE messages ADD COLUMN content_type VARCHAR")
        statements.append("CREATE INDEX IF NOT EXISTS idx_messages_continuation_root ON messages (continuation_root_id)")

        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

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
            with open(OLD_CHATS_FILE, "r") as file_handle:
                old_data = json.load(file_handle)

            with SessionLocal() as db:
                for chat in old_data:
                    if db.query(SessionModel).filter(SessionModel.id == chat["id"]).first():
                        continue

                    new_session = SessionModel(
                        id=chat["id"],
                        title=chat["title"],
                        agent_id=chat.get("agent_id"),
                        created_at=datetime.fromisoformat(chat["created_at"]) if isinstance(chat["created_at"], str) else chat["created_at"],
                        updated_at=datetime.fromisoformat(chat["updated_at"]) if isinstance(chat["updated_at"], str) else chat["updated_at"],
                    )
                    db.add(new_session)

                    for msg in chat.get("messages", []):
                        new_msg = MessageModel(
                            session_id=chat["id"],
                            role=msg["role"],
                            content=msg["content"],
                            timestamp=datetime.fromisoformat(msg["timestamp"]) if isinstance(msg["timestamp"], str) else msg["timestamp"],
                        )
                        db.add(new_msg)

                db.commit()

            os.rename(OLD_CHATS_FILE, OLD_CHATS_FILE + ".bak")
            print("Migration completed successfully.")
        except Exception as error:
            print(f"Migration error: {error}")

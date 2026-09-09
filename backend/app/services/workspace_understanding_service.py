import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import or_

from app.core.database import SessionLocal
from app.models.chat import (
    Workspace as WorkspaceModel,
    WorkspaceMemoryCandidate as WorkspaceMemoryCandidateModel,
    WorkspaceMemoryCard as WorkspaceMemoryCardModel,
)


class WorkspaceUnderstandingGroupDefinition(BaseModel):
    key: str
    label: str


class WorkspaceUnderstandingItem(BaseModel):
    id: str
    kind: str
    title: str
    content: str
    status: str
    memory_type: str
    scope_type: str = "workspace"
    scope_ref: Optional[str] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    confidence: Optional[float] = None
    updated_at: datetime


class WorkspaceUnderstandingGroup(BaseModel):
    group: str
    label: str
    total_count: int = 0
    active_count: int = 0
    pending_count: int = 0
    representative_items: List[WorkspaceUnderstandingItem] = Field(default_factory=list)


class WorkspaceUnderstandingSummary(BaseModel):
    workspace_id: str
    groups: List[WorkspaceUnderstandingGroup]
    applied_user_memory_preview: List[WorkspaceUnderstandingItem] = Field(default_factory=list)


WORKSPACE_UNDERSTANDING_GROUPS: List[WorkspaceUnderstandingGroupDefinition] = [
    WorkspaceUnderstandingGroupDefinition(key="background", label="Background"),
    WorkspaceUnderstandingGroupDefinition(key="goals", label="Goals"),
    WorkspaceUnderstandingGroupDefinition(key="decisions", label="Decisions"),
    WorkspaceUnderstandingGroupDefinition(key="constraints", label="Constraints"),
    WorkspaceUnderstandingGroupDefinition(key="preferences", label="Preferences"),
    WorkspaceUnderstandingGroupDefinition(key="terms", label="Terms"),
    WorkspaceUnderstandingGroupDefinition(key="open_questions", label="Open Questions"),
    WorkspaceUnderstandingGroupDefinition(key="current_state", label="Current State"),
]

UNDERSTANDING_GROUP_BY_MEMORY_TYPE = {
    "project_fact": "background",
    "decision": "decisions",
    "preference": "preferences",
    "recurring_instruction": "preferences",
    "term": "terms",
    "open_question": "open_questions",
    "temporary_state": "current_state",
    "historical_conclusion": "background",
}

VALID_UNDERSTANDING_GROUPS = {group.key for group in WORKSPACE_UNDERSTANDING_GROUPS}
REPRESENTATIVE_ITEM_LIMIT = 2
APPLIED_USER_MEMORY_PREVIEW_LIMIT = 3


class WorkspaceUnderstandingService:
    def build_summary(self, workspace_id: str) -> Optional[WorkspaceUnderstandingSummary]:
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None

            group_lookup = {
                definition.key: WorkspaceUnderstandingGroup(
                    group=definition.key,
                    label=definition.label,
                )
                for definition in WORKSPACE_UNDERSTANDING_GROUPS
            }

            memory_rows = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    or_(WorkspaceMemoryCardModel.scope_type != "user", WorkspaceMemoryCardModel.scope_type.is_(None)),
                )
                .order_by(
                    WorkspaceMemoryCardModel.pinned.desc(),
                    WorkspaceMemoryCardModel.updated_at.desc(),
                    WorkspaceMemoryCardModel.created_at.desc(),
                )
                .all()
            )
            candidate_rows = (
                db.query(WorkspaceMemoryCandidateModel)
                .filter(
                    WorkspaceMemoryCandidateModel.workspace_id == workspace_id,
                    or_(WorkspaceMemoryCandidateModel.scope_type != "user", WorkspaceMemoryCandidateModel.scope_type.is_(None)),
                    WorkspaceMemoryCandidateModel.status == "pending",
                )
                .order_by(
                    WorkspaceMemoryCandidateModel.updated_at.desc(),
                    WorkspaceMemoryCandidateModel.created_at.desc(),
                )
                .all()
            )
            applied_user_memory_rows = self._list_applied_user_memory_preview(db)

            for row in memory_rows:
                group = group_lookup[self._resolve_understanding_group(row.memory_type, row.memory_metadata_json)]
                group.total_count += 1
                if row.status == "active":
                    group.active_count += 1
                self._append_representative_item(group, self._memory_item(row))

            for row in candidate_rows:
                group = group_lookup[self._resolve_understanding_group(row.memory_type, row.candidate_metadata_json)]
                group.pending_count += 1
                self._append_representative_item(group, self._candidate_item(row))

            return WorkspaceUnderstandingSummary(
                workspace_id=workspace_id,
                groups=[group_lookup[definition.key] for definition in WORKSPACE_UNDERSTANDING_GROUPS],
                applied_user_memory_preview=[self._memory_item(row) for row in applied_user_memory_rows],
            )

    def _list_applied_user_memory_preview(self, db: Any) -> List[WorkspaceMemoryCardModel]:
        rows = (
            db.query(WorkspaceMemoryCardModel)
            .filter(
                WorkspaceMemoryCardModel.scope_type == "user",
                WorkspaceMemoryCardModel.status == "active",
            )
            .order_by(
                WorkspaceMemoryCardModel.pinned.desc(),
                WorkspaceMemoryCardModel.updated_at.desc(),
                WorkspaceMemoryCardModel.created_at.desc(),
            )
            .limit(APPLIED_USER_MEMORY_PREVIEW_LIMIT)
            .all()
        )
        return [row for row in rows if not self._memory_is_expired(row)]

    @staticmethod
    def _append_representative_item(
        group: WorkspaceUnderstandingGroup,
        item: WorkspaceUnderstandingItem,
    ) -> None:
        if len(group.representative_items) < REPRESENTATIVE_ITEM_LIMIT:
            group.representative_items.append(item)

    @staticmethod
    def _resolve_understanding_group(memory_type: str, metadata_json: Optional[str]) -> str:
        metadata = WorkspaceUnderstandingService._parse_metadata(metadata_json)
        override = str(metadata.get("understanding_group") or "").strip()
        if override in VALID_UNDERSTANDING_GROUPS:
            return override
        return UNDERSTANDING_GROUP_BY_MEMORY_TYPE.get(memory_type, "background")

    @staticmethod
    def _parse_metadata(raw: Optional[str]) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _to_api_datetime(value: Optional[datetime]) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _memory_is_expired(row: Any) -> bool:
        expires_at = getattr(row, "expires_at", None)
        if expires_at is None:
            return False
        now = datetime.now(timezone.utc) if expires_at.tzinfo is not None else datetime.utcnow()
        return expires_at <= now

    def _memory_item(self, row: WorkspaceMemoryCardModel) -> WorkspaceUnderstandingItem:
        return WorkspaceUnderstandingItem(
            id=row.id,
            kind="memory",
            title=row.title,
            content=row.content,
            status=row.status,
            memory_type=row.memory_type,
            scope_type=str(row.scope_type or "workspace"),
            scope_ref=row.scope_ref,
            source_session_id=row.source_session_id,
            source_message_id=row.source_message_id,
            confidence=row.confidence,
            updated_at=self._to_api_datetime(row.updated_at or row.created_at),
        )

    def _candidate_item(self, row: WorkspaceMemoryCandidateModel) -> WorkspaceUnderstandingItem:
        return WorkspaceUnderstandingItem(
            id=row.id,
            kind="candidate",
            title=row.title,
            content=row.content,
            status=row.status,
            memory_type=row.memory_type,
            scope_type=str(row.scope_type or "workspace"),
            scope_ref=row.scope_ref,
            source_session_id=row.source_session_id,
            source_message_id=row.source_message_id,
            confidence=row.score,
            updated_at=self._to_api_datetime(row.updated_at or row.created_at),
        )


workspace_understanding_service = WorkspaceUnderstandingService()

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import Base, SessionLocal, engine
from app.models.chat import (
    Session as SessionModel,
    Workspace as WorkspaceModel,
    WorkspaceArtifact as WorkspaceArtifactModel,
    WorkspaceMemoryCard as WorkspaceMemoryCardModel,
    WorkspaceMemoryCandidate as WorkspaceMemoryCandidateModel,
    WorkspaceSource as WorkspaceSourceModel,
)
from app.services.config_service import config_service
from app.services.doc_access_policy import DocAccessPolicyResolver
from app.utils.upload_storage import get_uploads_root

logger = logging.getLogger(__name__)
_UNSET = object()
READY_SOURCE_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv", ".md", ".txt"}
READABLE_UPLOAD_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".csv"}
SOURCE_STATUS_READY = "ready"
SOURCE_STATUS_NEEDS_PERMISSION = "needs_permission"
SOURCE_STATUS_UNSUPPORTED_TYPE = "unsupported_type"
SOURCE_STATUS_MISSING = "missing"
ACTIVE_MEMORY_STATUSES = {"active"}
EDITABLE_MEMORY_STATUSES = {"active", "disabled", "archived", "superseded"}
MEMORY_CANDIDATE_STATUSES = {"pending", "approved", "rejected"}
MEMORY_APPROVAL_MODES = {"create_new", "replace_existing", "update_existing"}
WORKSPACE_MEMORY_SCOPES = {"user", "workspace", "project", "chat"}
WORKSPACE_MEMORY_TYPES = {
    "project_fact",
    "decision",
    "preference",
    "historical_conclusion",
    "term",
    "open_question",
    "recurring_instruction",
}


class WorkspaceMemorySource(BaseModel):
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    source_ids: List[str] = Field(default_factory=list)
    citation_refs: List[Dict[str, Any]] = Field(default_factory=list)
    note_id: Optional[str] = None
    suggested_from: Optional[str] = None


class Workspace(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    default_agent_id: Optional[str] = None
    source_policy: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkspaceSource(BaseModel):
    id: str
    workspace_id: str
    source_type: str
    source_ref: str
    display_name: Optional[str] = None
    mime_type: Optional[str] = None
    status: str = "ready"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkspaceArtifact(BaseModel):
    id: str
    workspace_id: str
    artifact_type: str
    title: str
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    action_state_id: Optional[int] = None
    artifact_path: Optional[str] = None
    content_ref: Optional[str] = None
    artifact_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkspaceMemoryCard(BaseModel):
    id: str
    workspace_id: str
    memory_type: str
    scope_type: str = "workspace"
    scope_ref: Optional[str] = None
    title: str
    content: str
    status: str = "active"
    confidence: Optional[float] = None
    created_by: Optional[str] = None
    why_saved: Optional[str] = None
    pinned: bool = False
    editable: bool = True
    revocable: bool = True
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    supersedes_memory_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    source: Optional[WorkspaceMemorySource] = None
    memory_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkspaceMemoryDraft(BaseModel):
    workspace_id: str
    memory_type: str = "project_fact"
    scope_type: str = "workspace"
    scope_ref: Optional[str] = None
    title: str
    content: str
    confidence: Optional[float] = None
    why_saved: Optional[str] = None
    expires_at: Optional[datetime] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    memory_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkspaceMemoryCandidate(BaseModel):
    id: str
    workspace_id: str
    memory_type: str
    scope_type: str = "workspace"
    scope_ref: Optional[str] = None
    title: str
    content: str
    status: str = "pending"
    score: Optional[float] = None
    suggested_action: Optional[str] = None
    why_saved: Optional[str] = None
    expires_at: Optional[datetime] = None
    conflict_memory_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    source: Optional[WorkspaceMemorySource] = None
    candidate_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class WorkspacePromptMemory(BaseModel):
    id: str
    memory_type: str
    scope_type: str = "workspace"
    title: str
    content: str
    source_session_id: Optional[str] = None
    source_message_id: Optional[int] = None


class WorkspaceSourceReadiness(BaseModel):
    source: WorkspaceSource
    status: str
    readiness_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkspacePromptSource(BaseModel):
    id: str
    source_type: str
    source_ref: str
    display_name: Optional[str] = None
    status: str
    available_tools: List[str] = Field(default_factory=list)
    citation_capable: bool = False


class WorkspacePromptContext(BaseModel):
    workspace_id: str
    workspace_name: Optional[str] = None
    workspace_source_mode: str = "all_ready"
    grounding_mode: str = "normal"
    selected_source_ids: Optional[List[str]] = None
    eligible_sources: List[WorkspacePromptSource] = Field(default_factory=list)
    unavailable_sources: List[WorkspacePromptSource] = Field(default_factory=list)
    loaded_memory_ids: List[str] = Field(default_factory=list)
    loaded_memories: List[WorkspacePromptMemory] = Field(default_factory=list)
    prompt_block: str = ""


class WorkspaceService:
    def __init__(self) -> None:
        self._ensure_db()

    @staticmethod
    def _to_api_datetime(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _ensure_db(self) -> None:
        try:
            Base.metadata.create_all(bind=engine)
            self._ensure_session_workspace_schema()
            self._ensure_workspace_memory_schema()
        except OperationalError as exc:
            logger.warning("WorkspaceService create_all skipped due to database operational error: %s", exc)

    def _ensure_session_workspace_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("sessions")}
        except Exception:
            return

        statements: List[str] = []
        if "workspace_id" not in columns:
            statements.append("ALTER TABLE sessions ADD COLUMN workspace_id VARCHAR")
        statements.append("CREATE INDEX IF NOT EXISTS idx_sessions_workspace_id ON sessions (workspace_id)")

        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    def _ensure_workspace_memory_schema(self) -> None:
        try:
            inspector = inspect(engine)
            columns = {column["name"] for column in inspector.get_columns("workspace_memory_cards")}
            candidate_columns = {column["name"] for column in inspector.get_columns("workspace_memory_candidates")}
        except Exception:
            return

        statements: List[str] = []
        if "supersedes_memory_id" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN supersedes_memory_id VARCHAR")
        if "scope_type" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN scope_type VARCHAR DEFAULT 'workspace'")
        if "scope_ref" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN scope_ref VARCHAR")
        if "why_saved" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN why_saved TEXT")
        if "pinned" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN pinned BOOLEAN DEFAULT 0")
        if "editable" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN editable BOOLEAN DEFAULT 1")
        if "revocable" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN revocable BOOLEAN DEFAULT 1")
        if "expires_at" not in columns:
            statements.append("ALTER TABLE workspace_memory_cards ADD COLUMN expires_at DATETIME")
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_workspace_memory_cards_workspace_supersedes "
            "ON workspace_memory_cards (workspace_id, supersedes_memory_id)"
        )
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_workspace_memory_cards_scope "
            "ON workspace_memory_cards (scope_type, scope_ref, status)"
        )
        if "scope_type" not in candidate_columns:
            statements.append("ALTER TABLE workspace_memory_candidates ADD COLUMN scope_type VARCHAR DEFAULT 'workspace'")
        if "scope_ref" not in candidate_columns:
            statements.append("ALTER TABLE workspace_memory_candidates ADD COLUMN scope_ref VARCHAR")
        if "why_saved" not in candidate_columns:
            statements.append("ALTER TABLE workspace_memory_candidates ADD COLUMN why_saved TEXT")
        if "expires_at" not in candidate_columns:
            statements.append("ALTER TABLE workspace_memory_candidates ADD COLUMN expires_at DATETIME")
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_workspace_memory_candidates_scope "
            "ON workspace_memory_candidates (scope_type, scope_ref, status)"
        )
        statements.extend(
            [
                "UPDATE workspace_memory_cards "
                "SET scope_type = 'workspace' "
                "WHERE scope_type IS NULL OR TRIM(scope_type) = ''",
                "UPDATE workspace_memory_cards "
                "SET scope_ref = workspace_id "
                "WHERE scope_type IN ('workspace', 'project') AND (scope_ref IS NULL OR TRIM(scope_ref) = '')",
                "UPDATE workspace_memory_candidates "
                "SET scope_type = 'workspace' "
                "WHERE scope_type IS NULL OR TRIM(scope_type) = ''",
                "UPDATE workspace_memory_candidates "
                "SET scope_ref = workspace_id "
                "WHERE scope_type IN ('workspace', 'project') AND (scope_ref IS NULL OR TRIM(scope_ref) = '')",
            ]
        )

        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    @staticmethod
    def _parse_source_policy(raw: Optional[str]) -> Dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _to_workspace(self, record: WorkspaceModel) -> Workspace:
        return Workspace(
            id=record.id,
            name=record.name,
            description=record.description,
            default_agent_id=record.default_agent_id,
            source_policy=self._parse_source_policy(record.source_policy_json),
            created_at=self._to_api_datetime(record.created_at) or datetime.now(timezone.utc),
            updated_at=self._to_api_datetime(record.updated_at) or datetime.now(timezone.utc),
        )

    def _to_workspace_source(self, record: WorkspaceSourceModel) -> WorkspaceSource:
        return WorkspaceSource(
            id=record.id,
            workspace_id=record.workspace_id,
            source_type=record.source_type,
            source_ref=record.source_ref,
            display_name=record.display_name,
            mime_type=record.mime_type,
            status=record.status,
            source_metadata=self._parse_source_policy(record.source_metadata_json),
            created_at=self._to_api_datetime(record.created_at) or datetime.now(timezone.utc),
            updated_at=self._to_api_datetime(record.updated_at) or datetime.now(timezone.utc),
        )

    def _to_workspace_artifact(self, record: WorkspaceArtifactModel) -> WorkspaceArtifact:
        return WorkspaceArtifact(
            id=record.id,
            workspace_id=record.workspace_id,
            artifact_type=record.artifact_type,
            title=record.title,
            source_session_id=record.source_session_id,
            source_message_id=record.source_message_id,
            action_state_id=record.action_state_id,
            artifact_path=record.artifact_path,
            content_ref=record.content_ref,
            artifact_metadata=self._parse_source_policy(record.artifact_metadata_json),
            created_at=self._to_api_datetime(record.created_at) or datetime.now(timezone.utc),
            updated_at=self._to_api_datetime(record.updated_at) or datetime.now(timezone.utc),
        )

    def _to_workspace_memory(self, record: WorkspaceMemoryCardModel) -> WorkspaceMemoryCard:
        metadata = self._parse_source_policy(record.memory_metadata_json)
        return WorkspaceMemoryCard(
            id=record.id,
            workspace_id=record.workspace_id,
            memory_type=record.memory_type,
            scope_type=str(getattr(record, "scope_type", None) or "workspace"),
            scope_ref=getattr(record, "scope_ref", None),
            title=record.title,
            content=record.content,
            status=record.status,
            confidence=record.confidence,
            created_by=record.created_by,
            why_saved=getattr(record, "why_saved", None),
            pinned=bool(getattr(record, "pinned", False)),
            editable=bool(getattr(record, "editable", True)),
            revocable=bool(getattr(record, "revocable", True)),
            source_session_id=record.source_session_id,
            source_message_id=record.source_message_id,
            supersedes_memory_id=record.supersedes_memory_id,
            expires_at=self._to_api_datetime(getattr(record, "expires_at", None)),
            last_used_at=self._to_api_datetime(record.last_used_at),
            source=self._build_workspace_memory_source(
                source_session_id=record.source_session_id,
                source_message_id=record.source_message_id,
                metadata=metadata,
            ),
            memory_metadata=metadata,
            created_at=self._to_api_datetime(record.created_at) or datetime.now(timezone.utc),
            updated_at=self._to_api_datetime(record.updated_at) or datetime.now(timezone.utc),
        )

    def _to_workspace_memory_candidate(self, record: WorkspaceMemoryCandidateModel) -> WorkspaceMemoryCandidate:
        metadata = self._parse_source_policy(record.candidate_metadata_json)
        return WorkspaceMemoryCandidate(
            id=record.id,
            workspace_id=record.workspace_id,
            memory_type=record.memory_type,
            scope_type=str(getattr(record, "scope_type", None) or "workspace"),
            scope_ref=getattr(record, "scope_ref", None),
            title=record.title,
            content=record.content,
            status=record.status,
            score=record.score,
            suggested_action=record.suggested_action,
            why_saved=getattr(record, "why_saved", None),
            expires_at=self._to_api_datetime(getattr(record, "expires_at", None)),
            conflict_memory_id=record.conflict_memory_id,
            source_session_id=record.source_session_id,
            source_message_id=record.source_message_id,
            reviewed_at=self._to_api_datetime(record.reviewed_at),
            source=self._build_workspace_memory_source(
                source_session_id=record.source_session_id,
                source_message_id=record.source_message_id,
                metadata=metadata,
            ),
            candidate_metadata=metadata,
            created_at=self._to_api_datetime(record.created_at) or datetime.now(timezone.utc),
            updated_at=self._to_api_datetime(record.updated_at) or datetime.now(timezone.utc),
        )

    @staticmethod
    def _build_workspace_memory_source(
        *,
        source_session_id: Optional[str],
        source_message_id: Optional[int],
        metadata: Optional[Dict[str, Any]],
    ) -> WorkspaceMemorySource:
        payload = metadata or {}
        source_ids = payload.get("source_ids")
        citation_refs = payload.get("citation_refs")
        return WorkspaceMemorySource(
            source_session_id=source_session_id,
            source_message_id=source_message_id,
            source_ids=[str(item) for item in source_ids] if isinstance(source_ids, list) else [],
            citation_refs=[item for item in citation_refs if isinstance(item, dict)] if isinstance(citation_refs, list) else [],
            note_id=str(payload.get("note_id")) if payload.get("note_id") else None,
            suggested_from=str(payload.get("suggested_from")) if payload.get("suggested_from") else None,
        )

    @staticmethod
    def _source_extension(source: WorkspaceSourceModel) -> str:
        metadata = WorkspaceService._parse_source_policy(source.source_metadata_json)
        extension = metadata.get("extension")
        if isinstance(extension, str) and extension.strip():
            return extension.strip().lower()
        suffix = Path(str(source.display_name or source.source_ref or "")).suffix.lower()
        return suffix

    @staticmethod
    def _source_absolute_path(source: WorkspaceSourceModel) -> Optional[str]:
        ref = str(source.source_ref or "").strip()
        if not ref:
            return None
        if os.path.isabs(ref):
            return ref
        if ref.startswith("uploads/"):
            relative = ref[len("uploads/") :].strip("/")
            return str((get_uploads_root() / relative).resolve())
        return None

    @staticmethod
    def _source_tool_location(source: WorkspaceSourceModel) -> tuple[Optional[str], Optional[str]]:
        absolute_path = WorkspaceService._source_absolute_path(source)
        source_type = str(source.source_type or "").strip()
        if not absolute_path:
            return None, None

        if source_type == "upload":
            uploads_root = get_uploads_root().resolve()
            try:
                relative_path = Path(absolute_path).resolve().relative_to(uploads_root)
                return str(uploads_root), str(relative_path)
            except Exception:
                pass

        path = Path(absolute_path)
        if source_type == "local_doc_root":
            return str(path), "."
        return str(path.parent), path.name

    @staticmethod
    def _tools_for_source(source: WorkspaceSourceModel, extension: str) -> List[str]:
        source_type = str(source.source_type or "").strip()
        if source_type in {"note", "chat"}:
            return []
        if extension == ".pdf":
            return ["docs_read_pdf", "docs_search_pdf"]
        if extension in {".xlsx", ".xls", ".csv"}:
            return ["excel_profile", "excel_read", "excel_query"]
        if extension in {".md", ".txt"}:
            return ["docs_read", "docs_search"]
        return []

    def _check_source_readiness_record(self, source: WorkspaceSourceModel) -> tuple[str, Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        metadata = self._parse_source_policy(source.source_metadata_json)
        extension = self._source_extension(source)
        source_type = str(source.source_type or "").strip()
        absolute_path = self._source_absolute_path(source)
        available_tools = self._tools_for_source(source, extension)
        result: Dict[str, Any] = {
            **metadata,
            "extension": extension or metadata.get("extension"),
            "storage_path": metadata.get("storage_path") or (source.source_ref if source_type == "upload" else None),
            "available_tools": available_tools,
            "citation_capable": bool(available_tools),
            "doc_access_checked_at": now if source_type in {"local_file", "local_doc_root"} else metadata.get("doc_access_checked_at"),
            "readiness_error_code": None,
            "readiness_error_message": None,
        }

        if source_type in {"note", "chat"}:
            result["last_ready_at"] = now
            return SOURCE_STATUS_READY, result

        if extension and extension not in READY_SOURCE_EXTENSIONS:
            result["readiness_error_code"] = SOURCE_STATUS_UNSUPPORTED_TYPE
            result["readiness_error_message"] = f"Unsupported source extension: {extension}"
            return SOURCE_STATUS_UNSUPPORTED_TYPE, result

        if source_type == "upload":
            if extension not in READABLE_UPLOAD_EXTENSIONS:
                result["readiness_error_code"] = SOURCE_STATUS_UNSUPPORTED_TYPE
                result["readiness_error_message"] = "Uploaded source is registered but not readable by Phase 2 tools yet."
                return SOURCE_STATUS_UNSUPPORTED_TYPE, result
            if absolute_path and not os.path.exists(absolute_path):
                result["readiness_error_code"] = SOURCE_STATUS_MISSING
                result["readiness_error_message"] = "Uploaded file is missing from local storage."
                return SOURCE_STATUS_MISSING, result
            result["last_ready_at"] = now
            return SOURCE_STATUS_READY, result

        if source_type in {"local_file", "local_doc_root"}:
            if not absolute_path or not os.path.exists(absolute_path):
                result["readiness_error_code"] = SOURCE_STATUS_MISSING
                result["readiness_error_message"] = "Local source path does not exist."
                return SOURCE_STATUS_MISSING, result
            allow_roots, deny_roots = config_service.get_doc_access_roots()
            policy = DocAccessPolicyResolver.build_policy(
                base_allow_roots=allow_roots,
                base_deny_roots=deny_roots,
            )
            explanation = DocAccessPolicyResolver.explain(absolute_path, policy=policy)
            result["doc_access"] = {
                "allowed": explanation.get("allowed"),
                "reason": explanation.get("reason"),
                "matched_allow_roots": explanation.get("matched_allow_roots", []),
                "matched_deny_roots": explanation.get("matched_deny_roots", []),
            }
            if not explanation.get("allowed"):
                result["readiness_error_code"] = SOURCE_STATUS_NEEDS_PERMISSION
                result["readiness_error_message"] = "Source is outside allowed document roots or under a denied root."
                return SOURCE_STATUS_NEEDS_PERMISSION, result
            result["last_ready_at"] = now
            return SOURCE_STATUS_READY, result

        result["readiness_error_code"] = SOURCE_STATUS_UNSUPPORTED_TYPE
        result["readiness_error_message"] = f"Unsupported workspace source type: {source_type or 'unknown'}"
        return SOURCE_STATUS_UNSUPPORTED_TYPE, result

    def list_workspaces(self) -> List[Workspace]:
        with SessionLocal() as db:
            rows = db.query(WorkspaceModel).order_by(WorkspaceModel.updated_at.desc()).all()
            return [self._to_workspace(row) for row in rows]

    def list_sources(self, workspace_id: str) -> Optional[List[WorkspaceSource]]:
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel.id).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None
            rows = (
                db.query(WorkspaceSourceModel)
                .filter(WorkspaceSourceModel.workspace_id == workspace_id)
                .order_by(WorkspaceSourceModel.updated_at.desc(), WorkspaceSourceModel.created_at.desc())
                .all()
            )
            return [self._to_workspace_source(row) for row in rows]

    def list_artifacts(self, workspace_id: str) -> Optional[List[WorkspaceArtifact]]:
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel.id).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None
            rows = (
                db.query(WorkspaceArtifactModel)
                .filter(WorkspaceArtifactModel.workspace_id == workspace_id)
                .order_by(WorkspaceArtifactModel.updated_at.desc(), WorkspaceArtifactModel.created_at.desc())
                .all()
            )
            return [self._to_workspace_artifact(row) for row in rows]

    def list_memories(self, workspace_id: str, *, include_disabled: bool = True) -> Optional[List[WorkspaceMemoryCard]]:
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel.id).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None
            query = db.query(WorkspaceMemoryCardModel).filter(WorkspaceMemoryCardModel.workspace_id == workspace_id)
            if not include_disabled:
                query = query.filter(WorkspaceMemoryCardModel.status == "active")
            rows = query.order_by(
                WorkspaceMemoryCardModel.pinned.desc(),
                WorkspaceMemoryCardModel.updated_at.desc(),
                WorkspaceMemoryCardModel.created_at.desc(),
            ).all()
            return [self._to_workspace_memory(row) for row in rows]

    def list_memory_candidates(
        self,
        workspace_id: str,
        *,
        include_reviewed: bool = False,
    ) -> Optional[List[WorkspaceMemoryCandidate]]:
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel.id).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None
            query = db.query(WorkspaceMemoryCandidateModel).filter(
                WorkspaceMemoryCandidateModel.workspace_id == workspace_id
            )
            if not include_reviewed:
                query = query.filter(WorkspaceMemoryCandidateModel.status == "pending")
            rows = query.order_by(
                WorkspaceMemoryCandidateModel.updated_at.desc(),
                WorkspaceMemoryCandidateModel.created_at.desc(),
            ).all()
            return [self._to_workspace_memory_candidate(row) for row in rows]

    def check_source(self, workspace_id: str, source_id: str) -> Optional[WorkspaceSourceReadiness]:
        now = datetime.utcnow()
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceSourceModel)
                .filter(
                    WorkspaceSourceModel.workspace_id == workspace_id,
                    WorkspaceSourceModel.id == source_id,
                )
                .first()
            )
            if row is None:
                return None
            status, metadata = self._check_source_readiness_record(row)
            row.status = status
            row.source_metadata_json = json.dumps(metadata)
            row.updated_at = now
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = now
            db.commit()
            db.refresh(row)
            source = self._to_workspace_source(row)
            return WorkspaceSourceReadiness(
                source=source,
                status=status,
                readiness_metadata=source.source_metadata,
            )

    def check_sources(self, workspace_id: str) -> Optional[List[WorkspaceSourceReadiness]]:
        now = datetime.utcnow()
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None
            rows = (
                db.query(WorkspaceSourceModel)
                .filter(WorkspaceSourceModel.workspace_id == workspace_id)
                .order_by(WorkspaceSourceModel.updated_at.desc(), WorkspaceSourceModel.created_at.desc())
                .all()
            )
            results: List[WorkspaceSourceReadiness] = []
            for row in rows:
                status, metadata = self._check_source_readiness_record(row)
                row.status = status
                row.source_metadata_json = json.dumps(metadata)
                row.updated_at = now
            workspace.updated_at = now
            db.commit()
            for row in rows:
                db.refresh(row)
                source = self._to_workspace_source(row)
                results.append(
                    WorkspaceSourceReadiness(
                        source=source,
                        status=source.status,
                        readiness_metadata=source.source_metadata,
                    )
                )
            return results

    def get_source(self, workspace_id: str, source_id: str) -> Optional[WorkspaceSource]:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceSourceModel)
                .filter(
                    WorkspaceSourceModel.workspace_id == workspace_id,
                    WorkspaceSourceModel.id == source_id,
                )
                .first()
            )
            if row is None:
                return None
            return self._to_workspace_source(row)

    def get_artifact(self, workspace_id: str, artifact_id: str) -> Optional[WorkspaceArtifact]:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceArtifactModel)
                .filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id,
                    WorkspaceArtifactModel.id == artifact_id,
                )
                .first()
            )
            if row is None:
                return None
            return self._to_workspace_artifact(row)

    def get_memory(self, workspace_id: str, memory_id: str) -> Optional[WorkspaceMemoryCard]:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.id == memory_id,
                )
                .first()
            )
            if row is None:
                return None
            return self._to_workspace_memory(row)

    def get_memory_candidate(self, workspace_id: str, candidate_id: str) -> Optional[WorkspaceMemoryCandidate]:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceMemoryCandidateModel)
                .filter(
                    WorkspaceMemoryCandidateModel.workspace_id == workspace_id,
                    WorkspaceMemoryCandidateModel.id == candidate_id,
                )
                .first()
            )
            if row is None:
                return None
            return self._to_workspace_memory_candidate(row)

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        with SessionLocal() as db:
            row = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if row is None:
                return None
            return self._to_workspace(row)

    @staticmethod
    def _normalize_workspace_source_mode(mode: Optional[str]) -> str:
        if mode in {"all_ready", "selected", "none"}:
            return mode
        return "all_ready"

    @staticmethod
    def _normalize_grounding_mode(mode: Optional[str]) -> str:
        if mode in {"normal", "prefer_sources", "require_sources"}:
            return mode
        return "normal"

    @staticmethod
    def _normalize_memory_type(memory_type: Optional[str]) -> str:
        normalized = str(memory_type or "").strip().lower().replace("-", "_").replace(" ", "_")
        legacy_aliases = {
            "user_preference": "preference",
            "long_term_decision": "decision",
            "historical_conclusion": "historical_conclusion",
            "project_fact": "project_fact",
        }
        normalized = legacy_aliases.get(normalized, normalized)
        if normalized in WORKSPACE_MEMORY_TYPES:
            return normalized
        return "project_fact"

    @staticmethod
    def _normalize_memory_status(status: Optional[str]) -> str:
        normalized = str(status or "").strip().lower()
        if normalized in EDITABLE_MEMORY_STATUSES:
            return normalized
        return "active"

    @staticmethod
    def _normalize_memory_scope_type(scope_type: Optional[str]) -> str:
        normalized = str(scope_type or "").strip().lower()
        if normalized in WORKSPACE_MEMORY_SCOPES:
            return normalized
        return "workspace"

    @staticmethod
    def _normalize_candidate_status(status: Optional[str]) -> str:
        normalized = str(status or "").strip().lower()
        if normalized in MEMORY_CANDIDATE_STATUSES:
            return normalized
        return "pending"

    @staticmethod
    def _normalize_memory_approval_mode(mode: Optional[str]) -> str:
        normalized = str(mode or "").strip().lower()
        if normalized in MEMORY_APPROVAL_MODES:
            return normalized
        return "create_new"

    @staticmethod
    def _normalize_created_by(created_by: Optional[str]) -> str:
        normalized = str(created_by or "").strip().lower()
        return normalized or "user"

    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[datetime]:
        if value in (None, "", 0):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo is None else value.astimezone(timezone.utc).replace(tzinfo=None)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
        return parsed if parsed.tzinfo is None else parsed.astimezone(timezone.utc).replace(tzinfo=None)

    def _resolve_memory_scope_ref(
        self,
        *,
        scope_type: str,
        scope_ref: Optional[str],
        workspace_id: Optional[str],
        current_chat_id: Optional[str] = None,
    ) -> Optional[str]:
        cleaned = str(scope_ref or "").strip() or None
        if scope_type == "user":
            return cleaned
        if scope_type in {"workspace", "project"}:
            return cleaned or workspace_id
        if scope_type == "chat":
            return cleaned or current_chat_id
        return cleaned or workspace_id

    @staticmethod
    def _memory_is_expired(record: Any, *, now: Optional[datetime] = None) -> bool:
        expires_at = getattr(record, "expires_at", None)
        if expires_at is None:
            return False
        current = now or datetime.utcnow()
        return expires_at <= current

    @staticmethod
    def _tokenize_memory_query(text: Optional[str]) -> List[str]:
        normalized = str(text or "").strip().lower()
        if not normalized:
            return []
        return [token for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", normalized) if len(token) >= 2]

    @staticmethod
    def _normalize_memory_text(text: Optional[str]) -> str:
        return " ".join(WorkspaceService._tokenize_memory_query(text))

    @staticmethod
    def _memory_type_priority(memory_type: str) -> int:
        priority = {
            "preference": 0,
            "recurring_instruction": 1,
            "decision": 2,
            "project_fact": 3,
            "term": 4,
            "open_question": 5,
        }
        return priority.get(memory_type, 9)

    def _memory_relevance_score(
        self,
        record: WorkspaceMemoryCardModel,
        *,
        current_query: Optional[str],
        query_tokens: List[str],
    ) -> int:
        base_score = 20 - self._memory_type_priority(record.memory_type)
        haystack = " ".join(
            [
                str(record.title or ""),
                str(record.content or ""),
                str(record.memory_metadata_json or ""),
            ]
        ).lower()
        query_text = str(current_query or "").strip().lower()
        if query_text and len(query_text) >= 4 and query_text in haystack:
            base_score += 8
        if query_tokens:
            base_score += sum(2 for token in query_tokens if token in haystack)
        if bool(getattr(record, "pinned", False)):
            base_score += 4
        if record.last_used_at is not None:
            base_score += 2
        return base_score

    def _infer_memory_type_from_content(self, content: str) -> tuple[str, List[str]]:
        lowered = content.lower()
        reasons: List[str] = []
        memory_type = "project_fact"
        if any(token in lowered for token in ["以后", "默认", "prefer", "always", "风格", "语气", "希望", "请用"]):
            memory_type = "preference"
            reasons.append("Contains stable preference cues.")
        elif any(token in lowered for token in ["决定", "采用", "选择", "方案", "must", "should use", "we chose"]):
            memory_type = "decision"
            reasons.append("Contains explicit decision or standardization cues.")
        elif any(token in lowered for token in ["结论", "已否决", "否掉", "排除", "ruled out", "rejected", "historical conclusion"]):
            memory_type = "historical_conclusion"
            reasons.append("Contains a durable historical conclusion.")
        elif any(token in lowered for token in ["术语", "简称", "定义", "means", "refers to"]):
            memory_type = "term"
            reasons.append("Looks like a reusable term or definition.")
        elif "?" in content or "？" in content:
            memory_type = "open_question"
            reasons.append("Still phrased as an open question.")
        else:
            reasons.append("Looks like a reusable project fact.")
        return memory_type, reasons

    def _map_note_type_to_memory_type(self, note_type: Optional[str]) -> tuple[str, List[str]]:
        normalized = str(note_type or "").strip().lower()
        mapping = {
            "preference": ("preference", ["Note type suggests a durable user or workspace preference."]),
            "decision": ("decision", ["Note type suggests a reusable project decision."]),
            "fact": ("project_fact", ["Note type suggests a durable project fact."]),
            "reference": ("term", ["Reference-style note maps best to reusable terminology or definitions."]),
            "todo": ("open_question", ["Todo-style note is less stable and maps to an open question for review."]),
        }
        if normalized in mapping:
            return mapping[normalized]
        return "project_fact", ["Defaulted note-to-memory mapping to project_fact."]

    def _score_memory_candidate(
        self,
        *,
        memory_type: str,
        title: str,
        content: str,
    ) -> tuple[float, List[str]]:
        score = 0.45
        reasons: List[str] = []
        lowered = content.lower()
        token_count = len(self._tokenize_memory_query(f"{title} {content}"))

        if memory_type in {"preference", "decision", "project_fact", "historical_conclusion", "recurring_instruction"}:
            score += 0.18
            reasons.append("High-value durable memory type.")
        if any(token in lowered for token in ["默认", "以后", "always", "prefer", "统一", "标准", "约定"]):
            score += 0.12
            reasons.append("Contains durable preference or standard wording.")
        if any(token in lowered for token in ["决定", "采用", "选择", "we chose", "must use", "不再"]):
            score += 0.12
            reasons.append("Contains a durable decision or change signal.")
        if memory_type == "open_question":
            score -= 0.15
            reasons.append("Open questions are less stable than facts or decisions.")
        if any(token in lowered for token in ["可能", "也许", "maybe", "perhaps", "暂时", "for now"]):
            score -= 0.1
            reasons.append("Content sounds provisional.")
        if token_count >= 8:
            score += 0.05
            reasons.append("Content is specific enough to be reusable.")
        if len(content) > 500:
            score -= 0.08
            reasons.append("Long content may need trimming before storage.")

        score = max(0.05, min(0.99, round(score, 2)))
        if not reasons:
            reasons.append("Candidate was captured for manual review.")
        return score, reasons

    def _detect_memory_conflict(
        self,
        records: List[WorkspaceMemoryCardModel],
        *,
        memory_type: str,
        title: str,
        content: str,
    ) -> tuple[Optional[WorkspaceMemoryCardModel], Optional[str], List[str]]:
        candidate_tokens = set(self._tokenize_memory_query(f"{title} {content}"))
        normalized_title = self._normalize_memory_text(title)
        best_record: Optional[WorkspaceMemoryCardModel] = None
        best_score = 0.0
        best_action: Optional[str] = None
        reasons: List[str] = []

        for record in records:
            if record.status not in ACTIVE_MEMORY_STATUSES:
                continue
            if record.memory_type != memory_type:
                continue

            record_tokens = set(self._tokenize_memory_query(f"{record.title} {record.content}"))
            if not candidate_tokens or not record_tokens:
                overlap_ratio = 0.0
            else:
                overlap_ratio = len(candidate_tokens & record_tokens) / max(1, min(len(candidate_tokens), len(record_tokens)))
            title_match = normalized_title and normalized_title == self._normalize_memory_text(record.title)
            substring_match = bool(normalized_title and normalized_title in self._normalize_memory_text(record.title))
            score = overlap_ratio
            if title_match:
                score += 0.35
            elif substring_match:
                score += 0.18

            if score <= best_score or score < 0.2:
                continue

            best_record = record
            best_score = score
            if title_match or overlap_ratio >= 0.55:
                best_action = "replace_existing" if memory_type in {"preference", "decision", "project_fact", "recurring_instruction"} else "update_existing"
            else:
                best_action = "update_existing"

        if best_record is not None:
            reasons.append(f"Similar active memory found: {best_record.title}.")
            if best_action == "replace_existing":
                reasons.append("Recommend replacing the older memory to avoid stale guidance.")
            elif best_action == "update_existing":
                reasons.append("Recommend updating the existing memory instead of duplicating it.")
        return best_record, best_action, reasons

    def _build_memory_draft_from_message(
        self,
        workspace_id: str,
        *,
        chat_id: str,
        message_id: Optional[int] = None,
        source_ids: Optional[List[str]] = None,
        citation_refs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[WorkspaceMemoryDraft]:
        from app.services.chat_service import chat_service

        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return None
        chat = chat_service.get_chat(chat_id)
        if chat is None or chat.workspace_id != workspace_id:
            return None

        message = None
        if message_id is not None:
            message = next((item for item in chat.messages if item.id == message_id), None)
        if message is None:
            message = next((item for item in reversed(chat.messages) if item.role == "assistant"), None)
        if message is None:
            return None

        content = str(message.content or "").strip()
        if not content:
            return None

        memory_type, inference_reasons = self._infer_memory_type_from_content(content)
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), content[:80]).strip()
        title = first_line[:80] or "Workspace memory"
        score, score_reasons = self._score_memory_candidate(
            memory_type=memory_type,
            title=title,
            content=content[:500],
        )
        draft_metadata = {
            "source_ids": [str(item) for item in (source_ids or []) if str(item).strip()],
            "citation_refs": citation_refs or [],
            "suggested_from": "assistant_message",
            "score_reasons": score_reasons,
            "type_inference_reasons": inference_reasons,
        }
        why_saved = " ".join(score_reasons[:2]).strip() or "Suggested from assistant message."
        return WorkspaceMemoryDraft(
            workspace_id=workspace_id,
            memory_type=memory_type,
            scope_type="workspace",
            scope_ref=workspace_id,
            title=title,
            content=content[:500],
            confidence=score,
            why_saved=why_saved,
            source_session_id=chat_id,
            source_message_id=getattr(message, "id", None),
            memory_metadata=draft_metadata,
        )

    def _build_memory_draft_from_note(
        self,
        workspace_id: str,
        *,
        note_id: str,
    ) -> Optional[WorkspaceMemoryDraft]:
        from app.services.notebook_service import notebook_service

        workspace = self.get_workspace(workspace_id)
        if workspace is None:
            return None

        note = notebook_service.get_note(note_id)
        if note is None or note.workspace_id != workspace_id:
            return None

        candidate_text = (note.summary or "").strip() or (note.content or "").strip()
        if not candidate_text:
            return None

        note_memory_type, type_reasons = self._map_note_type_to_memory_type(note.note_type)
        inferred_type, inference_reasons = self._infer_memory_type_from_content(candidate_text)
        memory_type = note_memory_type if note.note_type in {"preference", "decision", "fact", "reference", "todo"} else inferred_type
        score, score_reasons = self._score_memory_candidate(
            memory_type=memory_type,
            title=note.title,
            content=candidate_text[:500],
        )
        source_metadata = dict(note.source_metadata or {})
        draft_metadata = {
            "note_id": note.id,
            "note_type": note.note_type,
            "note_tags": list(note.tags or []),
            "citation_refs": list(note.citation_refs or []),
            "source_ids": list(source_metadata.get("source_ids") or []),
            "suggested_from": "workspace_note",
            "score_reasons": score_reasons,
            "type_inference_reasons": [*type_reasons, *inference_reasons],
        }
        why_saved = " ".join(score_reasons[:2]).strip() or "Suggested from workspace note."
        return WorkspaceMemoryDraft(
            workspace_id=workspace_id,
            memory_type=memory_type,
            scope_type="workspace",
            scope_ref=workspace_id,
            title=note.title[:80] or "Workspace memory",
            content=candidate_text[:500],
            confidence=score,
            why_saved=why_saved,
            source_session_id=note.source_session_id,
            source_message_id=note.source_message_id,
            memory_metadata=draft_metadata,
        )

    def _build_workspace_memory_prompt_lines(
        self,
        records: List[WorkspaceMemoryCardModel],
    ) -> tuple[List[WorkspacePromptMemory], List[str]]:
        prompt_memories: List[WorkspacePromptMemory] = []
        lines: List[str] = []
        for record in records:
            prompt_memories.append(
                WorkspacePromptMemory(
                    id=record.id,
                    memory_type=record.memory_type,
                    scope_type=str(getattr(record, "scope_type", None) or "workspace"),
                    title=record.title,
                    content=record.content,
                    source_session_id=record.source_session_id,
                    source_message_id=record.source_message_id,
                )
            )
            source_bits: List[str] = []
            scope_type = str(getattr(record, "scope_type", None) or "workspace")
            source_bits.append(f"scope={scope_type}")
            if record.source_session_id:
                source_bits.append(f"chat={record.source_session_id}")
            if record.source_message_id is not None:
                source_bits.append(f"message={record.source_message_id}")
            source_suffix = f" ({'; '.join(source_bits)})" if source_bits else ""
            lines.append(
                f"- {record.id} [{record.memory_type}] {record.title}: {record.content}{source_suffix}"
            )
        return prompt_memories, lines

    def build_prompt_context(
        self,
        workspace_id: Optional[str],
        *,
        workspace_source_mode: Optional[str] = "all_ready",
        selected_source_ids: Optional[List[str]] = None,
        grounding_mode: Optional[str] = "normal",
        current_query: Optional[str] = None,
        current_chat_id: Optional[str] = None,
    ) -> Optional[WorkspacePromptContext]:
        source_mode = self._normalize_workspace_source_mode(workspace_source_mode)
        grounding = self._normalize_grounding_mode(grounding_mode)
        selected_ids = [str(item) for item in (selected_source_ids or []) if str(item).strip()]
        selected_set = set(selected_ids)
        now = datetime.utcnow()

        with SessionLocal() as db:
            workspace = None
            rows: List[WorkspaceSourceModel] = []
            if workspace_id:
                workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
                if workspace is None:
                    return None
                rows = (
                    db.query(WorkspaceSourceModel)
                    .filter(WorkspaceSourceModel.workspace_id == workspace_id)
                    .order_by(WorkspaceSourceModel.updated_at.desc(), WorkspaceSourceModel.created_at.desc())
                    .all()
                )
            memory_query = db.query(WorkspaceMemoryCardModel).filter(
                WorkspaceMemoryCardModel.status.in_(tuple(ACTIVE_MEMORY_STATUSES))
            )
            if workspace_id:
                memory_query = memory_query.filter(
                    (WorkspaceMemoryCardModel.scope_type == "user")
                    | (
                        (WorkspaceMemoryCardModel.scope_type == "workspace")
                        & (
                            (WorkspaceMemoryCardModel.scope_ref == workspace_id)
                            | (WorkspaceMemoryCardModel.scope_ref.is_(None))
                            | (WorkspaceMemoryCardModel.scope_ref == "")
                        )
                    )
                    | (
                        (WorkspaceMemoryCardModel.scope_type == "project")
                        & (
                            (WorkspaceMemoryCardModel.scope_ref == workspace_id)
                            | (WorkspaceMemoryCardModel.scope_ref.is_(None))
                            | (WorkspaceMemoryCardModel.scope_ref == "")
                        )
                    )
                    | (
                        (WorkspaceMemoryCardModel.scope_type == "chat")
                        & (WorkspaceMemoryCardModel.scope_ref == (current_chat_id or ""))
                    )
                )
            else:
                memory_query = memory_query.filter(WorkspaceMemoryCardModel.scope_type == "user")
            memory_rows = [row for row in memory_query.all() if not self._memory_is_expired(row, now=now)]

        eligible_rows: List[WorkspaceSourceModel] = []
        unavailable_rows: List[WorkspaceSourceModel] = []
        for row in rows:
            if source_mode == "none":
                unavailable_rows.append(row)
                continue
            if source_mode == "selected" and row.id not in selected_set:
                continue
            if row.status == SOURCE_STATUS_READY:
                eligible_rows.append(row)
            else:
                unavailable_rows.append(row)

        def to_prompt_source(row: WorkspaceSourceModel) -> WorkspacePromptSource:
            metadata = self._parse_source_policy(row.source_metadata_json)
            tools = metadata.get("available_tools") if isinstance(metadata.get("available_tools"), list) else []
            return WorkspacePromptSource(
                id=row.id,
                source_type=row.source_type,
                source_ref=row.source_ref,
                display_name=row.display_name,
                status=row.status,
                available_tools=[str(tool) for tool in tools],
                citation_capable=bool(metadata.get("citation_capable")),
            )

        eligible = [to_prompt_source(row) for row in eligible_rows]
        unavailable = [to_prompt_source(row) for row in unavailable_rows]
        query_tokens = self._tokenize_memory_query(current_query)
        ranked_memory_rows = sorted(
            memory_rows,
            key=lambda row: (
                self._memory_relevance_score(row, current_query=current_query, query_tokens=query_tokens),
                -self._memory_type_priority(row.memory_type),
                1 if bool(getattr(row, "pinned", False)) else 0,
                row.updated_at or row.created_at or datetime.min,
            ),
            reverse=True,
        )
        selected_memory_rows = ranked_memory_rows[:8]
        if selected_memory_rows:
            with SessionLocal() as db:
                for row in (
                    db.query(WorkspaceMemoryCardModel)
                    .filter(WorkspaceMemoryCardModel.id.in_([item.id for item in selected_memory_rows]))
                    .all()
                ):
                    row.last_used_at = now
                db.commit()
        loaded_memories, memory_lines = self._build_workspace_memory_prompt_lines(selected_memory_rows)
        lines = [
            "### Workspace Source Context",
            f"Workspace: {(workspace.name if workspace is not None else 'Global memory')} ({workspace.id if workspace is not None else 'global'})",
            f"Source mode: {source_mode}",
            f"Grounding mode: {grounding}",
            "Workspace is a source-selection container, not a permission boundary. Respect global doc_access for all local file reads.",
        ]
        if eligible:
            lines.append("Eligible sources:")
            lines.append("For workspace file tools, prefer the listed tool_root and tool_path instead of guessing a repo path.")
            for row, source in list(zip(eligible_rows, eligible))[:20]:
                tools = f"; tools={','.join(source.available_tools)}" if source.available_tools else ""
                name = source.display_name or source.source_ref
                tool_root, tool_path = self._source_tool_location(row)
                tool_location = ""
                if tool_root:
                    tool_location = f"; tool_root={tool_root}"
                    if tool_path:
                        tool_location += f"; tool_path={tool_path}"
                lines.append(
                    f"- {source.id}: {name} [{source.source_type}; status={source.status}{tools}{tool_location}]"
                )
        else:
            lines.append("Eligible sources: none")
        if unavailable:
            lines.append("Unavailable or excluded sources:")
            for source in unavailable[:10]:
                name = source.display_name or source.source_ref
                lines.append(f"- {source.id}: {name} [{source.source_type}; status={source.status}]")
        if grounding == "prefer_sources":
            lines.append("When the question concerns workspace materials, prefer eligible sources and cite source ids when used.")
        elif grounding == "require_sources":
            lines.append(
                "For factual claims about workspace materials, cite eligible workspace source ids. "
                "If evidence is insufficient, say what evidence is missing instead of guessing."
            )
        if memory_lines:
            lines.extend(
                [
                    "",
                    "### Workspace Memory Cards",
                    "Use these reviewed workspace memory cards as durable context when relevant. "
                    "If the user gives a newer correction, prefer the newer user statement.",
                    *memory_lines,
                ]
            )

        return WorkspacePromptContext(
            workspace_id=workspace.id if workspace is not None else "global",
            workspace_name=workspace.name if workspace is not None else "Global memory",
            workspace_source_mode=source_mode,
            grounding_mode=grounding,
            selected_source_ids=selected_ids if source_mode == "selected" else None,
            eligible_sources=eligible,
            unavailable_sources=unavailable,
            loaded_memory_ids=[record.id for record in selected_memory_rows],
            loaded_memories=loaded_memories,
            prompt_block="\n".join(lines).strip(),
        )

    def create_source(
        self,
        workspace_id: str,
        *,
        source_type: str,
        source_ref: str,
        display_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        status: str = "ready",
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkspaceSource]:
        now = datetime.utcnow()
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None

            normalized_ref = source_ref.strip()
            row = (
                db.query(WorkspaceSourceModel)
                .filter(
                    WorkspaceSourceModel.workspace_id == workspace_id,
                    WorkspaceSourceModel.source_ref == normalized_ref,
                )
                .first()
            )
            if row is None:
                row = WorkspaceSourceModel(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace_id,
                    source_type=source_type.strip(),
                    source_ref=normalized_ref,
                    display_name=display_name,
                    mime_type=mime_type,
                    status=status.strip() or "ready",
                    source_metadata_json=json.dumps(source_metadata or {}),
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
            else:
                row.source_type = source_type.strip()
                row.display_name = display_name
                row.mime_type = mime_type
                row.status = status.strip() or row.status or "ready"
                row.source_metadata_json = json.dumps(source_metadata or {})
                row.updated_at = now

            workspace.updated_at = now
            db.commit()
            db.refresh(row)
            return self._to_workspace_source(row)

    def _find_existing_artifact(
        self,
        db: Any,
        *,
        workspace_id: str,
        artifact_path: Optional[str],
        content_ref: Optional[str],
        action_state_id: Optional[int],
    ) -> Optional[WorkspaceArtifactModel]:
        if artifact_path:
            row = (
                db.query(WorkspaceArtifactModel)
                .filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id,
                    WorkspaceArtifactModel.artifact_path == artifact_path,
                )
                .first()
            )
            if row is not None:
                return row
        if content_ref:
            row = (
                db.query(WorkspaceArtifactModel)
                .filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id,
                    WorkspaceArtifactModel.content_ref == content_ref,
                )
                .first()
            )
            if row is not None:
                return row
        if action_state_id is not None:
            row = (
                db.query(WorkspaceArtifactModel)
                .filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id,
                    WorkspaceArtifactModel.action_state_id == action_state_id,
                )
                .first()
            )
            if row is not None:
                return row
        return None

    def upsert_artifact_record(
        self,
        db: Any,
        workspace_id: str,
        *,
        artifact_type: str,
        title: str,
        source_session_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
        action_state_id: Optional[int] = None,
        artifact_path: Optional[str] = None,
        content_ref: Optional[str] = None,
        artifact_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkspaceArtifact]:
        workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
        if workspace is None:
            return None

        normalized_path = artifact_path.strip() if artifact_path else None
        normalized_content_ref = content_ref.strip() if content_ref else None
        normalized_type = artifact_type.strip()
        normalized_title = title.strip()
        now = datetime.utcnow()
        row = self._find_existing_artifact(
            db,
            workspace_id=workspace_id,
            artifact_path=normalized_path,
            content_ref=normalized_content_ref,
            action_state_id=action_state_id,
        )
        if row is None:
            row = WorkspaceArtifactModel(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                artifact_type=normalized_type,
                title=normalized_title,
                source_session_id=source_session_id,
                source_message_id=source_message_id,
                action_state_id=action_state_id,
                artifact_path=normalized_path,
                content_ref=normalized_content_ref,
                artifact_metadata_json=json.dumps(artifact_metadata or {}),
                created_at=now,
                updated_at=now,
            )
            db.add(row)
        else:
            row.artifact_type = normalized_type or row.artifact_type
            row.title = normalized_title or row.title
            row.source_session_id = source_session_id if source_session_id is not None else row.source_session_id
            row.source_message_id = source_message_id if source_message_id is not None else row.source_message_id
            row.action_state_id = action_state_id if action_state_id is not None else row.action_state_id
            row.artifact_path = normalized_path or row.artifact_path
            row.content_ref = normalized_content_ref or row.content_ref
            row.artifact_metadata_json = json.dumps(artifact_metadata or {})
            row.updated_at = now

        workspace.updated_at = now
        db.flush()
        return self._to_workspace_artifact(row)

    def create_artifact(
        self,
        workspace_id: str,
        *,
        artifact_type: str,
        title: str,
        source_session_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
        action_state_id: Optional[int] = None,
        artifact_path: Optional[str] = None,
        content_ref: Optional[str] = None,
        artifact_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkspaceArtifact]:
        with SessionLocal() as db:
            artifact = self.upsert_artifact_record(
                db,
                workspace_id,
                artifact_type=artifact_type,
                title=title,
                source_session_id=source_session_id,
                source_message_id=source_message_id,
                action_state_id=action_state_id,
                artifact_path=artifact_path,
                content_ref=content_ref,
                artifact_metadata=artifact_metadata,
            )
            if artifact is None:
                return None
            db.commit()
            return artifact

    def register_sources_from_attachments(
        self,
        workspace_id: str,
        attachments: List[Dict[str, Any]],
    ) -> List[WorkspaceSource]:
        registered: List[WorkspaceSource] = []
        for attachment in attachments:
            if not isinstance(attachment, dict):
                continue
            source_ref = str(attachment.get("storage_path") or attachment.get("id") or "").strip()
            if not source_ref:
                continue
            source = self.create_source(
                workspace_id,
                source_type=str(attachment.get("source") or attachment.get("kind") or "upload").strip() or "upload",
                source_ref=source_ref,
                display_name=attachment.get("display_name"),
                mime_type=attachment.get("mime_type"),
                status=str(attachment.get("status") or "ready").strip() or "ready",
                source_metadata=attachment,
            )
            if source is not None:
                readiness = self.check_source(workspace_id, source.id)
                registered.append(readiness.source if readiness is not None else source)
        return registered

    def update_artifact(
        self,
        workspace_id: str,
        artifact_id: str,
        *,
        artifact_type: Any = _UNSET,
        title: Any = _UNSET,
        source_session_id: Any = _UNSET,
        source_message_id: Any = _UNSET,
        action_state_id: Any = _UNSET,
        artifact_path: Any = _UNSET,
        content_ref: Any = _UNSET,
        artifact_metadata: Any = _UNSET,
    ) -> Optional[WorkspaceArtifact]:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceArtifactModel)
                .filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id,
                    WorkspaceArtifactModel.id == artifact_id,
                )
                .first()
            )
            if row is None:
                return None

            if artifact_type is not _UNSET:
                row.artifact_type = artifact_type.strip() if artifact_type else row.artifact_type
            if title is not _UNSET:
                row.title = title.strip() if title else row.title
            if source_session_id is not _UNSET:
                row.source_session_id = source_session_id
            if source_message_id is not _UNSET:
                row.source_message_id = source_message_id
            if action_state_id is not _UNSET:
                row.action_state_id = action_state_id
            if artifact_path is not _UNSET:
                row.artifact_path = artifact_path.strip() if artifact_path else None
            if content_ref is not _UNSET:
                row.content_ref = content_ref.strip() if content_ref else None
            if artifact_metadata is not _UNSET:
                row.artifact_metadata_json = json.dumps(artifact_metadata or {})
            row.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(row)
            return self._to_workspace_artifact(row)

    def create_memory(
        self,
        workspace_id: str,
        *,
        memory_type: str,
        scope_type: str = "workspace",
        scope_ref: Optional[str] = None,
        title: str,
        content: str,
        status: str = "active",
        confidence: Optional[float] = None,
        created_by: Optional[str] = None,
        why_saved: Optional[str] = None,
        pinned: bool = False,
        editable: bool = True,
        revocable: bool = True,
        source_session_id: Optional[str] = None,
        source_message_id: Optional[int] = None,
        supersedes_memory_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        memory_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[WorkspaceMemoryCard]:
        now = datetime.utcnow()
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None
            normalized_scope_type = self._normalize_memory_scope_type(scope_type)
            row = WorkspaceMemoryCardModel(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                memory_type=self._normalize_memory_type(memory_type),
                scope_type=normalized_scope_type,
                scope_ref=self._resolve_memory_scope_ref(
                    scope_type=normalized_scope_type,
                    scope_ref=scope_ref,
                    workspace_id=workspace_id,
                    current_chat_id=source_session_id if normalized_scope_type == "chat" else None,
                ),
                title=title.strip(),
                content=content.strip(),
                status=self._normalize_memory_status(status),
                confidence=confidence,
                created_by=self._normalize_created_by(created_by),
                why_saved=str(why_saved or "").strip() or None,
                pinned=bool(pinned),
                editable=bool(editable),
                revocable=bool(revocable),
                source_session_id=source_session_id,
                source_message_id=source_message_id,
                supersedes_memory_id=supersedes_memory_id,
                expires_at=self._coerce_datetime(expires_at),
                memory_metadata_json=json.dumps(memory_metadata or {}),
                created_at=now,
                updated_at=now,
            )
            workspace.updated_at = now
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_workspace_memory(row)

    def update_memory(
        self,
        workspace_id: str,
        memory_id: str,
        *,
        memory_type: Any = _UNSET,
        scope_type: Any = _UNSET,
        scope_ref: Any = _UNSET,
        title: Any = _UNSET,
        content: Any = _UNSET,
        status: Any = _UNSET,
        confidence: Any = _UNSET,
        created_by: Any = _UNSET,
        why_saved: Any = _UNSET,
        pinned: Any = _UNSET,
        editable: Any = _UNSET,
        revocable: Any = _UNSET,
        source_session_id: Any = _UNSET,
        source_message_id: Any = _UNSET,
        supersedes_memory_id: Any = _UNSET,
        expires_at: Any = _UNSET,
        memory_metadata: Any = _UNSET,
    ) -> Optional[WorkspaceMemoryCard]:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.id == memory_id,
                )
                .first()
            )
            if row is None:
                return None

            requested_updates = {
                field
                for field, value in (
                    ("memory_type", memory_type),
                    ("scope_type", scope_type),
                    ("scope_ref", scope_ref),
                    ("title", title),
                    ("content", content),
                    ("status", status),
                    ("confidence", confidence),
                    ("created_by", created_by),
                    ("why_saved", why_saved),
                    ("pinned", pinned),
                    ("editable", editable),
                    ("revocable", revocable),
                    ("source_session_id", source_session_id),
                    ("source_message_id", source_message_id),
                    ("supersedes_memory_id", supersedes_memory_id),
                    ("expires_at", expires_at),
                    ("memory_metadata", memory_metadata),
                )
                if value is not _UNSET
            }
            if bool(getattr(row, "editable", True)) is False:
                unlock_only = requested_updates <= {"editable"} and editable is True
                if not unlock_only:
                    raise ValueError("memory_not_editable")

            if memory_type is not _UNSET:
                row.memory_type = self._normalize_memory_type(memory_type)
            if scope_type is not _UNSET:
                row.scope_type = self._normalize_memory_scope_type(scope_type)
            if source_session_id is not _UNSET:
                row.source_session_id = source_session_id
            if source_message_id is not _UNSET:
                row.source_message_id = source_message_id
            if scope_type is not _UNSET or scope_ref is not _UNSET or source_session_id is not _UNSET:
                row.scope_ref = self._resolve_memory_scope_ref(
                    scope_type=str(getattr(row, "scope_type", None) or "workspace"),
                    scope_ref=row.scope_ref if scope_ref is _UNSET else scope_ref,
                    workspace_id=workspace_id,
                    current_chat_id=row.source_session_id,
                )
            if title is not _UNSET:
                row.title = str(title or "").strip() or row.title
            if content is not _UNSET:
                row.content = str(content or "").strip() or row.content
            if status is not _UNSET:
                row.status = self._normalize_memory_status(status)
            if confidence is not _UNSET:
                row.confidence = confidence
            if created_by is not _UNSET:
                row.created_by = self._normalize_created_by(created_by)
            if why_saved is not _UNSET:
                row.why_saved = str(why_saved or "").strip() or None
            if pinned is not _UNSET:
                row.pinned = bool(pinned)
            if editable is not _UNSET:
                row.editable = bool(editable)
            if revocable is not _UNSET:
                row.revocable = bool(revocable)
            if supersedes_memory_id is not _UNSET:
                row.supersedes_memory_id = supersedes_memory_id
            if expires_at is not _UNSET:
                row.expires_at = self._coerce_datetime(expires_at)
            if memory_metadata is not _UNSET:
                row.memory_metadata_json = json.dumps(memory_metadata or {})
            row.updated_at = datetime.utcnow()
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = row.updated_at
            db.commit()
            db.refresh(row)
            return self._to_workspace_memory(row)

    def bulk_update_memory_status_by_type(
        self,
        workspace_id: str,
        *,
        memory_type: str,
        status: str,
    ) -> int:
        normalized_type = self._normalize_memory_type(memory_type)
        normalized_status = self._normalize_memory_status(status)
        now = datetime.utcnow()
        with SessionLocal() as db:
            rows = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.memory_type == normalized_type,
                )
                .all()
            )
            for row in rows:
                if bool(getattr(row, "editable", True)) is False:
                    continue
                row.status = normalized_status
                row.updated_at = now
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = now
            db.commit()
            return sum(1 for row in rows if bool(getattr(row, "editable", True)) is not False)

    def delete_memory(self, workspace_id: str, memory_id: str) -> bool:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.id == memory_id,
                )
                .first()
            )
            if row is None:
                return False
            if bool(getattr(row, "revocable", True)) is False:
                raise ValueError("memory_not_revocable")

            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = datetime.utcnow()
            db.delete(row)
            db.commit()
            return True

    def suggest_memory_from_message(
        self,
        workspace_id: str,
        *,
        chat_id: str,
        message_id: Optional[int] = None,
        source_ids: Optional[List[str]] = None,
        citation_refs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[WorkspaceMemoryDraft]:
        return self._build_memory_draft_from_message(
            workspace_id,
            chat_id=chat_id,
            message_id=message_id,
            source_ids=source_ids,
            citation_refs=citation_refs,
        )

    def suggest_memory_from_note(
        self,
        workspace_id: str,
        *,
        note_id: str,
    ) -> Optional[WorkspaceMemoryDraft]:
        return self._build_memory_draft_from_note(workspace_id, note_id=note_id)

    def build_note_promotion_hint(
        self,
        workspace_id: Optional[str],
        *,
        note_id: str,
    ) -> Dict[str, Any]:
        from app.services.notebook_service import notebook_service

        if not workspace_id:
            return {}

        note = notebook_service.get_note(note_id)
        if note is None or note.workspace_id != workspace_id:
            return {}
        if note.promoted_memory_id:
            return {
                "eligible": False,
                "state": "promoted",
                "reason_summary": "Already promoted into reviewed workspace memory.",
                "promoted_memory_id": note.promoted_memory_id,
            }

        draft = self._build_memory_draft_from_note(workspace_id, note_id=note_id)
        if draft is None:
            return {}

        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return {}

            active_memories = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.status.in_(tuple(ACTIVE_MEMORY_STATUSES)),
                )
                .all()
            )
            last_candidate_id = str((note.source_metadata or {}).get("last_memory_candidate_id") or "").strip() or None
            candidate_record = None
            if last_candidate_id:
                candidate_record = (
                    db.query(WorkspaceMemoryCandidateModel)
                    .filter(
                        WorkspaceMemoryCandidateModel.workspace_id == workspace_id,
                        WorkspaceMemoryCandidateModel.id == last_candidate_id,
                    )
                    .first()
                )

        conflict_record, suggested_action, conflict_reasons = self._detect_memory_conflict(
            active_memories,
            memory_type=draft.memory_type,
            title=draft.title,
            content=draft.content,
        )

        confidence = draft.confidence if draft.confidence is not None else 0.0
        durable_memory_types = {"preference", "decision", "project_fact", "recurring_instruction", "term"}
        eligible = draft.memory_type in durable_memory_types and confidence >= 0.55
        if note.note_type == "todo":
            eligible = False

        score_reasons = [
            str(item)
            for item in (draft.memory_metadata or {}).get("score_reasons") or []
            if str(item).strip()
        ]
        type_inference_reasons = [
            str(item)
            for item in (draft.memory_metadata or {}).get("type_inference_reasons") or []
            if str(item).strip()
        ]

        candidate_status = None
        if candidate_record is not None:
            candidate_status = str(candidate_record.status or "").strip().lower() or None

        if candidate_status == "pending":
            state = "candidate_pending"
            reason_summary = "Pending memory candidate already exists for this note."
        elif candidate_status == "approved":
            state = "candidate_approved"
            reason_summary = "This note already has an approved memory candidate."
        elif candidate_status == "rejected":
            state = "candidate_rejected"
            reason_summary = "A previous memory candidate from this note was rejected."
        elif eligible:
            state = "ready"
            if conflict_record is not None:
                reason_summary = (
                    f"Looks durable and may {suggested_action or 'update_existing'} "
                    f"existing memory “{conflict_record.title}”."
                )
            else:
                reason_summary = "Looks durable enough to review as workspace memory."
        else:
            state = "note_only"
            reason_summary = "Keep as a note for now unless it becomes a stable reusable memory."

        return {
            "eligible": eligible,
            "state": state,
            "memory_type": draft.memory_type,
            "confidence": confidence,
            "suggested_action": suggested_action or "create_new",
            "candidate_id": candidate_record.id if candidate_record is not None else None,
            "candidate_status": candidate_status,
            "conflict_memory_id": conflict_record.id if conflict_record is not None else None,
            "conflict_memory_title": conflict_record.title if conflict_record is not None else None,
            "score_reasons": score_reasons,
            "type_inference_reasons": type_inference_reasons,
            "conflict_reasons": conflict_reasons,
            "reason_summary": reason_summary,
        }

    def suggest_memory_candidate_from_message(
        self,
        workspace_id: str,
        *,
        chat_id: str,
        message_id: Optional[int] = None,
        source_ids: Optional[List[str]] = None,
        citation_refs: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[WorkspaceMemoryCandidate]:
        draft = self._build_memory_draft_from_message(
            workspace_id,
            chat_id=chat_id,
            message_id=message_id,
            source_ids=source_ids,
            citation_refs=citation_refs,
        )
        if draft is None:
            return None

        now = datetime.utcnow()
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None

            active_memories = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.status.in_(tuple(ACTIVE_MEMORY_STATUSES)),
                )
                .all()
            )
            conflict_record, suggested_action, conflict_reasons = self._detect_memory_conflict(
                active_memories,
                memory_type=draft.memory_type,
                title=draft.title,
                content=draft.content,
            )

            candidate_metadata = dict(draft.memory_metadata or {})
            candidate_metadata["score_reasons"] = candidate_metadata.get("score_reasons") or []
            if conflict_reasons:
                candidate_metadata["conflict_reasons"] = conflict_reasons

            row = WorkspaceMemoryCandidateModel(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                memory_type=self._normalize_memory_type(draft.memory_type),
                scope_type=self._normalize_memory_scope_type(draft.scope_type),
                scope_ref=self._resolve_memory_scope_ref(
                    scope_type=self._normalize_memory_scope_type(draft.scope_type),
                    scope_ref=draft.scope_ref,
                    workspace_id=workspace_id,
                    current_chat_id=draft.source_session_id if draft.scope_type == "chat" else None,
                ),
                title=draft.title.strip(),
                content=draft.content.strip(),
                status="pending",
                score=draft.confidence,
                suggested_action=suggested_action or "create_new",
                why_saved=str(draft.why_saved or "").strip() or None,
                expires_at=self._coerce_datetime(draft.expires_at),
                conflict_memory_id=conflict_record.id if conflict_record is not None else None,
                source_session_id=draft.source_session_id,
                source_message_id=draft.source_message_id,
                candidate_metadata_json=json.dumps(candidate_metadata),
                created_at=now,
                updated_at=now,
            )
            workspace.updated_at = now
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_workspace_memory_candidate(row)

    def suggest_memory_candidate_from_note(
        self,
        workspace_id: str,
        *,
        note_id: str,
    ) -> Optional[WorkspaceMemoryCandidate]:
        from app.services.notebook_service import notebook_service

        draft = self._build_memory_draft_from_note(
            workspace_id,
            note_id=note_id,
        )
        if draft is None:
            return None

        now = datetime.utcnow()
        with SessionLocal() as db:
            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None

            active_memories = (
                db.query(WorkspaceMemoryCardModel)
                .filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id,
                    WorkspaceMemoryCardModel.status.in_(tuple(ACTIVE_MEMORY_STATUSES)),
                )
                .all()
            )
            conflict_record, suggested_action, conflict_reasons = self._detect_memory_conflict(
                active_memories,
                memory_type=draft.memory_type,
                title=draft.title,
                content=draft.content,
            )

            candidate_metadata = dict(draft.memory_metadata or {})
            candidate_metadata["score_reasons"] = candidate_metadata.get("score_reasons") or []
            if conflict_reasons:
                candidate_metadata["conflict_reasons"] = conflict_reasons

            row = WorkspaceMemoryCandidateModel(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                memory_type=self._normalize_memory_type(draft.memory_type),
                scope_type=self._normalize_memory_scope_type(draft.scope_type),
                scope_ref=self._resolve_memory_scope_ref(
                    scope_type=self._normalize_memory_scope_type(draft.scope_type),
                    scope_ref=draft.scope_ref,
                    workspace_id=workspace_id,
                    current_chat_id=draft.source_session_id if draft.scope_type == "chat" else None,
                ),
                title=draft.title.strip(),
                content=draft.content.strip(),
                status="pending",
                score=draft.confidence,
                suggested_action=suggested_action or "create_new",
                why_saved=str(draft.why_saved or "").strip() or None,
                expires_at=self._coerce_datetime(draft.expires_at),
                conflict_memory_id=conflict_record.id if conflict_record is not None else None,
                source_session_id=draft.source_session_id,
                source_message_id=draft.source_message_id,
                candidate_metadata_json=json.dumps(candidate_metadata),
                created_at=now,
                updated_at=now,
            )
            workspace.updated_at = now
            db.add(row)
            db.commit()
            db.refresh(row)

            note = notebook_service.get_note(note_id)
            if note is not None:
                notebook_service.update_note(
                    note.id,
                    source_metadata={
                        "last_memory_candidate_id": row.id,
                        "last_memory_candidate_created_at": now.isoformat(),
                    },
                )
            return self._to_workspace_memory_candidate(row)

    def approve_memory_candidate(
        self,
        workspace_id: str,
        candidate_id: str,
        *,
        approval_mode: str = "create_new",
        target_memory_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        scope_type: Optional[str] = None,
        scope_ref: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        confidence: Optional[float] = None,
        why_saved: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        pinned: Optional[bool] = None,
        reviewer: Optional[str] = None,
    ) -> Optional[WorkspaceMemoryCard]:
        normalized_mode = self._normalize_memory_approval_mode(approval_mode)
        now = datetime.utcnow()
        with SessionLocal() as db:
            candidate = (
                db.query(WorkspaceMemoryCandidateModel)
                .filter(
                    WorkspaceMemoryCandidateModel.workspace_id == workspace_id,
                    WorkspaceMemoryCandidateModel.id == candidate_id,
                )
                .first()
            )
            if candidate is None:
                return None
            if candidate.status != "pending":
                return None

            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is None:
                return None

            candidate_metadata = self._parse_source_policy(candidate.candidate_metadata_json)
            resolved_target_id = target_memory_id or candidate.conflict_memory_id
            target_memory = None
            if resolved_target_id:
                target_memory = (
                    db.query(WorkspaceMemoryCardModel)
                    .filter(
                        WorkspaceMemoryCardModel.workspace_id == workspace_id,
                        WorkspaceMemoryCardModel.id == resolved_target_id,
                    )
                    .first()
                )

            next_type = self._normalize_memory_type(memory_type or candidate.memory_type)
            next_scope_type = self._normalize_memory_scope_type(scope_type or getattr(candidate, "scope_type", None))
            next_scope_ref = self._resolve_memory_scope_ref(
                scope_type=next_scope_type,
                scope_ref=scope_ref if scope_ref is not None else getattr(candidate, "scope_ref", None),
                workspace_id=workspace_id,
                current_chat_id=candidate.source_session_id if next_scope_type == "chat" else None,
            )
            next_title = str(title or candidate.title).strip() or candidate.title
            next_content = str(content or candidate.content).strip() or candidate.content
            next_confidence = confidence if confidence is not None else candidate.score
            next_why_saved = str(why_saved or getattr(candidate, "why_saved", None) or "").strip() or None
            next_expires_at = self._coerce_datetime(expires_at if expires_at is not None else getattr(candidate, "expires_at", None))
            next_pinned = (
                bool(pinned)
                if pinned is not None
                else bool(getattr(target_memory, "pinned", False)) if target_memory is not None else False
            )

            if normalized_mode in {"replace_existing", "update_existing"} and target_memory is None:
                return None
            if normalized_mode == "update_existing" and bool(getattr(target_memory, "editable", True)) is False:
                raise ValueError("memory_not_editable")
            if normalized_mode == "replace_existing" and bool(getattr(target_memory, "revocable", True)) is False:
                raise ValueError("memory_not_revocable")

            approved_memory: Optional[WorkspaceMemoryCardModel] = None
            if normalized_mode == "update_existing":
                if target_memory is None:
                    return None
                target_metadata = self._parse_source_policy(target_memory.memory_metadata_json)
                history = target_metadata.get("candidate_update_history")
                if not isinstance(history, list):
                    history = []
                history.append(
                    {
                        "candidate_id": candidate.id,
                        "reviewed_at": now.isoformat(),
                        "previous_title": target_memory.title,
                        "previous_content": target_memory.content,
                    }
                )
                target_metadata["candidate_update_history"] = history[-10:]
                target_memory.memory_type = next_type
                target_memory.scope_type = next_scope_type
                target_memory.scope_ref = next_scope_ref
                target_memory.title = next_title
                target_memory.content = next_content
                target_memory.confidence = next_confidence
                target_memory.created_by = self._normalize_created_by(reviewer or "user")
                target_memory.why_saved = next_why_saved
                target_memory.expires_at = next_expires_at
                target_memory.pinned = next_pinned
                target_memory.source_session_id = candidate.source_session_id
                target_memory.source_message_id = candidate.source_message_id
                target_memory.memory_metadata_json = json.dumps(target_metadata)
                target_memory.updated_at = now
                approved_memory = target_memory
            else:
                approved_memory = WorkspaceMemoryCardModel(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace_id,
                    memory_type=next_type,
                    scope_type=next_scope_type,
                    scope_ref=next_scope_ref,
                    title=next_title,
                    content=next_content,
                    status="active",
                    confidence=next_confidence,
                    created_by=self._normalize_created_by(reviewer or "user"),
                    why_saved=next_why_saved,
                    pinned=next_pinned,
                    editable=True,
                    revocable=True,
                    source_session_id=candidate.source_session_id,
                    source_message_id=candidate.source_message_id,
                    supersedes_memory_id=target_memory.id if normalized_mode == "replace_existing" and target_memory is not None else None,
                    expires_at=next_expires_at,
                    memory_metadata_json=json.dumps(
                        {
                            **candidate_metadata,
                            "approved_from_candidate_id": candidate.id,
                            "approval_mode": normalized_mode,
                        }
                    ),
                    created_at=now,
                    updated_at=now,
                )
                db.add(approved_memory)

            if normalized_mode == "replace_existing" and target_memory is not None:
                prior_metadata = self._parse_source_policy(target_memory.memory_metadata_json)
                prior_metadata["replaced_by_candidate_id"] = candidate.id
                prior_metadata["replaced_at"] = now.isoformat()
                target_memory.status = "superseded"
                target_memory.memory_metadata_json = json.dumps(prior_metadata)
                target_memory.updated_at = now

            candidate_metadata["approval_mode"] = normalized_mode
            candidate_metadata["approved_by"] = self._normalize_created_by(reviewer or "user")
            candidate_metadata["approved_memory_id"] = approved_memory.id if approved_memory is not None else None
            candidate.candidate_metadata_json = json.dumps(candidate_metadata)
            candidate.status = "approved"
            candidate.reviewed_at = now
            candidate.updated_at = now
            workspace.updated_at = now
            db.commit()
            if approved_memory is None:
                return None
            db.refresh(approved_memory)
            note_id = candidate_metadata.get("note_id")
            if isinstance(note_id, str) and note_id.strip():
                from app.services.notebook_service import notebook_service

                notebook_service.update_note(
                    note_id.strip(),
                    status="promoted",
                    promoted_memory_id=approved_memory.id,
                    source_metadata={
                        "promotion_candidate_id": candidate.id,
                        "promotion_approved_at": now.isoformat(),
                    },
                )
            return self._to_workspace_memory(approved_memory)

    def reject_memory_candidate(
        self,
        workspace_id: str,
        candidate_id: str,
        *,
        reason: Optional[str] = None,
        reviewer: Optional[str] = None,
    ) -> bool:
        now = datetime.utcnow()
        with SessionLocal() as db:
            candidate = (
                db.query(WorkspaceMemoryCandidateModel)
                .filter(
                    WorkspaceMemoryCandidateModel.workspace_id == workspace_id,
                    WorkspaceMemoryCandidateModel.id == candidate_id,
                )
                .first()
            )
            if candidate is None:
                return False
            if candidate.status != "pending":
                return False

            candidate_metadata = self._parse_source_policy(candidate.candidate_metadata_json)
            candidate_metadata["rejection_reason"] = str(reason or "").strip() or None
            candidate_metadata["reviewed_by"] = self._normalize_created_by(reviewer or "user")
            candidate.candidate_metadata_json = json.dumps(candidate_metadata)
            candidate.status = "rejected"
            candidate.reviewed_at = now
            candidate.updated_at = now

            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = now
            db.commit()
            return True

    def create_workspace(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        default_agent_id: Optional[str] = None,
        source_policy: Optional[Dict[str, Any]] = None,
    ) -> Workspace:
        now = datetime.utcnow()
        workspace_id = str(uuid.uuid4())
        with SessionLocal() as db:
            row = WorkspaceModel(
                id=workspace_id,
                name=name.strip(),
                description=description,
                default_agent_id=default_agent_id,
                source_policy_json=json.dumps(source_policy or {}),
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return self._to_workspace(row)

    def update_workspace(
        self,
        workspace_id: str,
        *,
        name: Any = _UNSET,
        description: Any = _UNSET,
        default_agent_id: Any = _UNSET,
        source_policy: Any = _UNSET,
    ) -> Optional[Workspace]:
        with SessionLocal() as db:
            row = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if row is None:
                return None

            if name is not _UNSET:
                row.name = name.strip()
            if description is not _UNSET:
                row.description = description
            if default_agent_id is not _UNSET:
                row.default_agent_id = default_agent_id
            if source_policy is not _UNSET:
                row.source_policy_json = json.dumps(source_policy)
            row.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(row)
            return self._to_workspace(row)

    def delete_source(self, workspace_id: str, source_id: str) -> bool:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceSourceModel)
                .filter(
                    WorkspaceSourceModel.workspace_id == workspace_id,
                    WorkspaceSourceModel.id == source_id,
                )
                .first()
            )
            if row is None:
                return False

            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = datetime.utcnow()
            db.delete(row)
            db.commit()
            return True

    def delete_artifact(self, workspace_id: str, artifact_id: str) -> bool:
        with SessionLocal() as db:
            row = (
                db.query(WorkspaceArtifactModel)
                .filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id,
                    WorkspaceArtifactModel.id == artifact_id,
                )
                .first()
            )
            if row is None:
                return False

            workspace = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if workspace is not None:
                workspace.updated_at = datetime.utcnow()
            db.delete(row)
            db.commit()
            return True

    def delete_workspace(self, workspace_id: str, *, force: bool = False) -> bool:
        with SessionLocal() as db:
            row = db.query(WorkspaceModel).filter(WorkspaceModel.id == workspace_id).first()
            if row is None:
                return False

            if not force:
                session_count = db.query(SessionModel).filter(SessionModel.workspace_id == workspace_id).count()
                source_count = db.query(WorkspaceSourceModel).filter(
                    WorkspaceSourceModel.workspace_id == workspace_id
                ).count()
                artifact_count = db.query(WorkspaceArtifactModel).filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id
                ).count()
                memory_count = db.query(WorkspaceMemoryCardModel).filter(
                    WorkspaceMemoryCardModel.workspace_id == workspace_id
                ).count()
                candidate_count = db.query(WorkspaceMemoryCandidateModel).filter(
                    WorkspaceMemoryCandidateModel.workspace_id == workspace_id
                ).count()
                if session_count > 0 or source_count > 0 or artifact_count > 0 or memory_count > 0 or candidate_count > 0:
                    raise ValueError("workspace_not_empty")

            if force:
                db.query(SessionModel).filter(SessionModel.workspace_id == workspace_id).update(
                    {SessionModel.workspace_id: None},
                    synchronize_session=False,
                )
                db.query(WorkspaceSourceModel).filter(WorkspaceSourceModel.workspace_id == workspace_id).delete(
                    synchronize_session=False,
                )
                db.query(WorkspaceArtifactModel).filter(
                    WorkspaceArtifactModel.workspace_id == workspace_id
                ).delete(synchronize_session=False)
                db.query(WorkspaceMemoryCandidateModel).filter(
                    WorkspaceMemoryCandidateModel.workspace_id == workspace_id
                ).delete(synchronize_session=False)

            db.delete(row)
            db.commit()
            return True


workspace_service = WorkspaceService()

import json
import logging
import os
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

    def build_prompt_context(
        self,
        workspace_id: Optional[str],
        *,
        workspace_source_mode: Optional[str] = "all_ready",
        selected_source_ids: Optional[List[str]] = None,
        grounding_mode: Optional[str] = "normal",
    ) -> Optional[WorkspacePromptContext]:
        if not workspace_id:
            return None

        source_mode = self._normalize_workspace_source_mode(workspace_source_mode)
        grounding = self._normalize_grounding_mode(grounding_mode)
        selected_ids = [str(item) for item in (selected_source_ids or []) if str(item).strip()]
        selected_set = set(selected_ids)

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
        lines = [
            "### Workspace Source Context",
            f"Workspace: {workspace.name} ({workspace.id})",
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

        return WorkspacePromptContext(
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            workspace_source_mode=source_mode,
            grounding_mode=grounding,
            selected_source_ids=selected_ids if source_mode == "selected" else None,
            eligible_sources=eligible,
            unavailable_sources=unavailable,
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
                if session_count > 0 or source_count > 0 or artifact_count > 0:
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

            db.delete(row)
            db.commit()
            return True


workspace_service = WorkspaceService()

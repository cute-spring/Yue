import os
import shutil
import sqlite3
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.chat_service import ChatService
from app.services.workspace_service import WorkspaceService


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")

    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with patch("app.services.workspace_service.engine", test_engine), \
         patch("app.services.workspace_service.SessionLocal", testing_session_local), \
         patch("app.services.chat_service.engine", test_engine), \
         patch("app.services.chat_service.SessionLocal", testing_session_local), \
         patch("app.services.chat_service.DATA_DIR", temp_dir):
        workspace_service = WorkspaceService()
        chat_service = ChatService()
        yield workspace_service, chat_service, db_file

    test_engine.dispose()
    shutil.rmtree(temp_dir)


def test_workspace_service_creates_workspace_table_and_session_column(temp_db):
    _, _, db_file = temp_db

    with sqlite3.connect(db_file) as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "workspaces" in tables
        assert "workspace_sources" in tables
        assert "workspace_artifacts" in tables

        session_columns = [row[1] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()]
        assert "workspace_id" in session_columns


def test_workspace_crud_roundtrip(temp_db):
    workspace_service, _, _ = temp_db

    created = workspace_service.create_workspace(
        name="Client Research",
        description="Shared project context",
        default_agent_id="builtin-pdf-research",
        source_policy={"grounding_mode": "prefer_sources"},
    )
    assert created.name == "Client Research"
    assert created.default_agent_id == "builtin-pdf-research"
    assert created.source_policy == {"grounding_mode": "prefer_sources"}

    loaded = workspace_service.get_workspace(created.id)
    assert loaded is not None
    assert loaded.id == created.id

    updated = workspace_service.update_workspace(
        created.id,
        name="Client Research V2",
        description="Updated",
    )
    assert updated is not None
    assert updated.name == "Client Research V2"
    assert updated.description == "Updated"

    listed = workspace_service.list_workspaces()
    assert len(listed) == 1
    assert listed[0].id == created.id


def test_workspace_source_crud_roundtrip(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Source Registry")
    created = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/att_1.pdf",
        display_name="brief.pdf",
        mime_type="application/pdf",
        source_metadata={"id": "att_1", "status": "ready"},
    )

    assert created is not None
    assert created.workspace_id == workspace.id
    assert created.display_name == "brief.pdf"

    loaded = workspace_service.get_source(workspace.id, created.id)
    assert loaded is not None
    assert loaded.source_ref == "uploads/chat/2026/05/30/att_1.pdf"

    listed = workspace_service.list_sources(workspace.id)
    assert listed is not None
    assert len(listed) == 1

    assert workspace_service.delete_source(workspace.id, created.id) is True
    assert workspace_service.list_sources(workspace.id) == []


def test_workspace_source_registration_deduplicates_by_ref(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Attachment Registry")
    attachments = [
        {
            "id": "att_demo_1",
            "kind": "file",
            "display_name": "report.pdf",
            "storage_path": "uploads/chat/2026/05/30/att_demo_1.pdf",
            "mime_type": "application/pdf",
            "status": "ready",
        },
        {
            "id": "att_demo_1_dup",
            "kind": "file",
            "display_name": "report-latest.pdf",
            "storage_path": "uploads/chat/2026/05/30/att_demo_1.pdf",
            "mime_type": "application/pdf",
            "status": "ready",
        },
    ]

    registered = workspace_service.register_sources_from_attachments(workspace.id, attachments)

    assert len(registered) == 2
    listed = workspace_service.list_sources(workspace.id)
    assert listed is not None
    assert len(listed) == 1
    assert listed[0].display_name == "report-latest.pdf"


def test_workspace_source_registration_from_attachments_enriches_readiness_metadata(temp_db, tmp_path, monkeypatch):
    workspace_service, _, _ = temp_db
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads" / "chat" / "2026" / "05" / "31"
    upload_dir.mkdir(parents=True)
    (upload_dir / "report.pdf").write_bytes(b"%PDF-1.4\n")
    workspace = workspace_service.create_workspace(name="Attachment readiness")

    registered = workspace_service.register_sources_from_attachments(
        workspace.id,
        [
            {
                "id": "att_pdf",
                "kind": "file",
                "display_name": "report.pdf",
                "storage_path": "uploads/chat/2026/05/31/report.pdf",
                "mime_type": "application/pdf",
                "extension": ".pdf",
                "source": "upload",
                "status": "ready",
            }
        ],
    )

    assert len(registered) == 1
    assert registered[0].status == "ready"
    assert registered[0].source_metadata["citation_capable"] is True
    assert "docs_read_pdf" in registered[0].source_metadata["available_tools"]


def test_workspace_source_readiness_marks_local_file_ready_when_allowed(temp_db, tmp_path):
    workspace_service, _, _ = temp_db
    source_file = tmp_path / "brief.pdf"
    source_file.write_text("demo")
    workspace = workspace_service.create_workspace(name="Readiness")
    source = workspace_service.create_source(
        workspace.id,
        source_type="local_file",
        source_ref=str(source_file),
        display_name="brief.pdf",
    )

    with patch("app.services.workspace_service.config_service.get_doc_access_roots", return_value=([str(tmp_path)], [])):
        result = workspace_service.check_source(workspace.id, source.id)

    assert result is not None
    assert result.status == "ready"
    assert result.source.source_metadata["citation_capable"] is True
    assert "docs_read_pdf" in result.source.source_metadata["available_tools"]


def test_workspace_source_readiness_respects_doc_access_denial(temp_db, tmp_path):
    workspace_service, _, _ = temp_db
    source_file = tmp_path / "private.pdf"
    source_file.write_text("demo")
    workspace = workspace_service.create_workspace(name="Readiness Denied")
    source = workspace_service.create_source(
        workspace.id,
        source_type="local_file",
        source_ref=str(source_file),
        display_name="private.pdf",
    )

    with patch("app.services.workspace_service.config_service.get_doc_access_roots", return_value=([], [])):
        result = workspace_service.check_source(workspace.id, source.id)

    assert result is not None
    assert result.status == "needs_permission"
    assert result.source.source_metadata["readiness_error_code"] == "needs_permission"


def test_workspace_source_readiness_marks_unsupported_type(temp_db):
    workspace_service, _, _ = temp_db
    workspace = workspace_service.create_workspace(name="Unsupported")
    source = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/att_demo.mov",
        display_name="clip.mov",
        source_metadata={"extension": ".mov"},
    )

    result = workspace_service.check_source(workspace.id, source.id)

    assert result is not None
    assert result.status == "unsupported_type"
    assert result.source.source_metadata["readiness_error_code"] == "unsupported_type"


def test_workspace_source_readiness_marks_existing_pdf_upload_ready(temp_db, tmp_path, monkeypatch):
    workspace_service, _, _ = temp_db
    upload_file = tmp_path / "uploads" / "chat" / "2026" / "05" / "30" / "report.pdf"
    upload_file.parent.mkdir(parents=True)
    upload_file.write_bytes(b"%PDF-1.4\n% test pdf\n")
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path))
    workspace = workspace_service.create_workspace(name="Upload PDF")
    source = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/report.pdf",
        display_name="report.pdf",
        mime_type="application/pdf",
    )

    result = workspace_service.check_source(workspace.id, source.id)

    assert result is not None
    assert result.status == "ready"
    assert result.source.source_metadata["storage_path"] == "uploads/chat/2026/05/30/report.pdf"
    assert result.source.source_metadata["citation_capable"] is True
    assert result.source.source_metadata["readiness_error_code"] is None
    assert "docs_read_pdf" in result.source.source_metadata["available_tools"]


def test_workspace_source_readiness_marks_existing_excel_upload_ready(temp_db, tmp_path, monkeypatch):
    workspace_service, _, _ = temp_db
    upload_file = tmp_path / "uploads" / "chat" / "2026" / "05" / "30" / "model.xlsx"
    upload_file.parent.mkdir(parents=True)
    upload_file.write_bytes(b"fake xlsx payload")
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path))
    workspace = workspace_service.create_workspace(name="Upload Excel")
    source = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/model.xlsx",
        display_name="model.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    result = workspace_service.check_source(workspace.id, source.id)

    assert result is not None
    assert result.status == "ready"
    assert result.source.source_metadata["citation_capable"] is True
    assert {"excel_profile", "excel_read", "excel_query"}.issubset(
        set(result.source.source_metadata["available_tools"])
    )


def test_workspace_source_readiness_marks_missing_upload_unavailable(temp_db, tmp_path, monkeypatch):
    workspace_service, _, _ = temp_db
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path))
    workspace = workspace_service.create_workspace(name="Missing Upload")
    source = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/missing.pdf",
        display_name="missing.pdf",
    )

    result = workspace_service.check_source(workspace.id, source.id)

    assert result is not None
    assert result.status == "missing"
    assert result.source.source_metadata["readiness_error_code"] == "missing"
    assert "missing" in result.source.source_metadata["readiness_error_message"].lower()


def test_workspace_source_bulk_readiness_reports_mixed_real_file_states(temp_db, tmp_path, monkeypatch):
    workspace_service, _, _ = temp_db
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads" / "chat" / "2026" / "05" / "30"
    upload_dir.mkdir(parents=True)
    (upload_dir / "report.pdf").write_bytes(b"%PDF-1.4\n")
    (upload_dir / "model.xlsx").write_bytes(b"fake xlsx payload")
    workspace = workspace_service.create_workspace(name="Mixed Uploads")
    pdf = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/report.pdf",
        display_name="report.pdf",
    )
    excel = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/model.xlsx",
        display_name="model.xlsx",
    )
    video = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/demo.mov",
        display_name="demo.mov",
    )
    missing = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/missing.pdf",
        display_name="missing.pdf",
    )

    results = workspace_service.check_sources(workspace.id)

    assert results is not None
    statuses = {item.source.id: item.status for item in results}
    assert statuses[pdf.id] == "ready"
    assert statuses[excel.id] == "ready"
    assert statuses[video.id] == "unsupported_type"
    assert statuses[missing.id] == "missing"


def test_workspace_prompt_context_filters_selected_ready_sources(temp_db, tmp_path):
    workspace_service, _, _ = temp_db
    first_file = tmp_path / "a.pdf"
    second_file = tmp_path / "b.pdf"
    first_file.write_text("a")
    second_file.write_text("b")
    workspace = workspace_service.create_workspace(name="Prompt Workspace")
    first = workspace_service.create_source(
        workspace.id,
        source_type="local_file",
        source_ref=str(first_file),
        display_name="a.pdf",
    )
    second = workspace_service.create_source(
        workspace.id,
        source_type="local_file",
        source_ref=str(second_file),
        display_name="b.pdf",
    )
    with patch("app.services.workspace_service.config_service.get_doc_access_roots", return_value=([str(tmp_path)], [])):
        workspace_service.check_sources(workspace.id)

    context = workspace_service.build_prompt_context(
        workspace.id,
        workspace_source_mode="selected",
        selected_source_ids=[first.id],
        grounding_mode="require_sources",
    )

    assert context is not None
    assert [source.id for source in context.eligible_sources] == [first.id]
    assert "require_sources" in context.prompt_block
    assert first.id in context.prompt_block
    assert f"tool_root={tmp_path}" in context.prompt_block
    assert "tool_path=a.pdf" in context.prompt_block
    assert second.id not in context.prompt_block


def test_workspace_prompt_context_includes_upload_tool_location(temp_db, tmp_path, monkeypatch):
    workspace_service, _, _ = temp_db
    monkeypatch.setenv("YUE_DATA_DIR", str(tmp_path))
    upload_dir = tmp_path / "uploads" / "chat" / "2026" / "05" / "31"
    upload_dir.mkdir(parents=True)
    (upload_dir / "report.pdf").write_bytes(b"%PDF-1.4\n")
    workspace = workspace_service.create_workspace(name="Upload Prompt Workspace")
    source = workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/31/report.pdf",
        display_name="report.pdf",
        mime_type="application/pdf",
        source_metadata={"extension": ".pdf"},
    )

    workspace_service.check_source(workspace.id, source.id)
    context = workspace_service.build_prompt_context(
        workspace.id,
        workspace_source_mode="all_ready",
        grounding_mode="require_sources",
    )

    assert context is not None
    assert f"tool_root={tmp_path / 'uploads'}" in context.prompt_block
    assert "tool_path=chat/2026/05/31/report.pdf" in context.prompt_block


def test_workspace_artifact_crud_roundtrip(temp_db):
    workspace_service, chat_service, _ = temp_db

    workspace = workspace_service.create_workspace(name="Artifact Registry")
    chat = chat_service.create_chat(title="Artifact Chat", workspace_id=workspace.id)
    created = workspace_service.create_artifact(
        workspace.id,
        artifact_type="export",
        title="project-summary.docx",
        source_session_id=chat.id,
        artifact_path="/exports/project-summary.docx",
        content_ref="invocation-1",
        artifact_metadata={"download_url": "/exports/project-summary.docx"},
    )

    assert created is not None
    assert created.workspace_id == workspace.id
    assert created.artifact_path == "/exports/project-summary.docx"

    loaded = workspace_service.get_artifact(workspace.id, created.id)
    assert loaded is not None
    assert loaded.title == "project-summary.docx"

    updated = workspace_service.update_artifact(
        workspace.id,
        created.id,
        title="project-summary-v2.docx",
        artifact_metadata={"download_url": "/exports/project-summary-v2.docx"},
    )
    assert updated is not None
    assert updated.title == "project-summary-v2.docx"

    listed = workspace_service.list_artifacts(workspace.id)
    assert listed is not None
    assert len(listed) == 1

    assert workspace_service.delete_artifact(workspace.id, created.id) is True
    assert workspace_service.list_artifacts(workspace.id) == []


def test_workspace_artifact_registration_deduplicates_by_artifact_path(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Artifact Dedupe")
    first = workspace_service.create_artifact(
        workspace.id,
        artifact_type="export",
        title="slides.pptx",
        artifact_path="/exports/slides.pptx",
        artifact_metadata={"source": "first"},
    )
    second = workspace_service.create_artifact(
        workspace.id,
        artifact_type="generated_file",
        title="slides-latest.pptx",
        artifact_path="/exports/slides.pptx",
        artifact_metadata={"source": "second"},
    )

    assert first is not None
    assert second is not None
    listed = workspace_service.list_artifacts(workspace.id)
    assert listed is not None
    assert len(listed) == 1
    assert listed[0].title == "slides-latest.pptx"
    assert listed[0].artifact_type == "generated_file"


def test_workspace_delete_rejects_non_empty_without_force(temp_db):
    workspace_service, chat_service, _ = temp_db

    workspace = workspace_service.create_workspace(name="Protected Workspace")
    chat_service.create_chat(title="Scoped chat", workspace_id=workspace.id)

    with pytest.raises(ValueError, match="workspace_not_empty"):
        workspace_service.delete_workspace(workspace.id)

    assert workspace_service.get_workspace(workspace.id) is not None


def test_workspace_delete_rejects_when_sources_exist(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Protected Sources")
    workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/att_2.pdf",
    )

    with pytest.raises(ValueError, match="workspace_not_empty"):
        workspace_service.delete_workspace(workspace.id)

    assert workspace_service.get_workspace(workspace.id) is not None


def test_workspace_delete_rejects_when_artifacts_exist(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Protected Artifacts")
    workspace_service.create_artifact(
        workspace.id,
        artifact_type="export",
        title="report.docx",
        artifact_path="/exports/report.docx",
    )

    with pytest.raises(ValueError, match="workspace_not_empty"):
        workspace_service.delete_workspace(workspace.id)

    assert workspace_service.get_workspace(workspace.id) is not None


def test_workspace_force_delete_clears_session_links(temp_db):
    workspace_service, chat_service, _ = temp_db

    workspace = workspace_service.create_workspace(name="Force Delete Workspace")
    session = chat_service.create_chat(title="Scoped chat", workspace_id=workspace.id)
    workspace_service.create_source(
        workspace.id,
        source_type="upload",
        source_ref="uploads/chat/2026/05/30/att_3.pdf",
    )

    assert workspace_service.delete_workspace(workspace.id, force=True) is True
    assert workspace_service.get_workspace(workspace.id) is None

    reloaded = chat_service.get_chat(session.id)
    assert reloaded is not None
    assert reloaded.workspace_id is None

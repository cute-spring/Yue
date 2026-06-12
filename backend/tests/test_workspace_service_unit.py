import os
import shutil
import sqlite3
import tempfile
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.chat_service import ChatService
from app.services.notebook_service import NotebookService
from app.services.workspace_service import WorkspaceService


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")
    notes_file = os.path.join(temp_dir, "notes.json")

    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    with patch("app.services.workspace_service.engine", test_engine), \
         patch("app.services.workspace_service.SessionLocal", testing_session_local), \
         patch("app.services.notebook_service.engine", test_engine), \
         patch("app.services.notebook_service.SessionLocal", testing_session_local), \
         patch("app.services.notebook_service.DATA_DIR", temp_dir), \
         patch("app.services.notebook_service.NOTES_FILE", notes_file), \
         patch("app.services.chat_service_schema.engine", test_engine), \
         patch("app.services.chat_service_schema.SessionLocal", testing_session_local), \
         patch("app.services.chat_service_sessions.SessionLocal", testing_session_local), \
         patch("app.services.chat_service_actions.SessionLocal", testing_session_local), \
         patch("app.services.chat_service_schema.OLD_CHATS_FILE", os.path.join(temp_dir, "chats.json")):
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
        assert "workspace_memory_cards" in tables
        assert "workspace_memory_candidates" in tables

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


def test_workspace_prompt_context_mixed_readiness_matrix(temp_db, tmp_path):
    workspace_service, _, _ = temp_db
    ready_file = tmp_path / "ready.pdf"
    pending_file = tmp_path / "pending.pdf"
    ready_file.write_text("ready")
    pending_file.write_text("pending")
    workspace = workspace_service.create_workspace(name="Grounded Matrix")
    ready = workspace_service.create_source(
        workspace.id,
        source_type="local_file",
        source_ref=str(ready_file),
        display_name="ready.pdf",
        status="ready",
        source_metadata={"citation_capable": True, "available_tools": ["docs_read_pdf"]},
    )
    pending = workspace_service.create_source(
        workspace.id,
        source_type="local_file",
        source_ref=str(pending_file),
        display_name="pending.pdf",
        status="pending",
    )

    all_ready_context = workspace_service.build_prompt_context(
        workspace.id,
        workspace_source_mode="all_ready",
        grounding_mode="require_sources",
    )
    assert all_ready_context is not None
    assert [source.id for source in all_ready_context.eligible_sources] == [ready.id]
    assert [source.id for source in all_ready_context.unavailable_sources] == [pending.id]
    assert "Eligible sources:" in all_ready_context.prompt_block
    assert "cite eligible workspace source ids" in all_ready_context.prompt_block

    selected_pending_context = workspace_service.build_prompt_context(
        workspace.id,
        workspace_source_mode="selected",
        selected_source_ids=[pending.id],
        grounding_mode="require_sources",
    )
    assert selected_pending_context is not None
    assert selected_pending_context.selected_source_ids == [pending.id]
    assert selected_pending_context.eligible_sources == []
    assert [source.id for source in selected_pending_context.unavailable_sources] == [pending.id]
    assert "Eligible sources: none" in selected_pending_context.prompt_block
    assert "pending.pdf" in selected_pending_context.prompt_block

    no_sources_context = workspace_service.build_prompt_context(
        workspace.id,
        workspace_source_mode="none",
        grounding_mode="prefer_sources",
    )
    assert no_sources_context is not None
    assert no_sources_context.eligible_sources == []
    assert {source.id for source in no_sources_context.unavailable_sources} == {ready.id, pending.id}
    assert no_sources_context.selected_source_ids is None
    assert "Eligible sources: none" in no_sources_context.prompt_block


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


def test_workspace_memory_crud_and_prompt_context(temp_db):
    workspace_service, chat_service, _ = temp_db

    workspace = workspace_service.create_workspace(name="Memory Workspace")
    session = chat_service.create_chat(title="Scoped memory chat", workspace_id=workspace.id)
    chat_service.add_message(session.id, "assistant", "默认用中文，数据库方案是 Postgres。")
    assistant = next(msg for msg in chat_service.get_chat(session.id).messages if msg.role == "assistant")

    created = workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        title="默认中文输出",
        content="以后默认使用中文输出，先给结论后展开。",
        source_session_id=session.id,
        source_message_id=assistant.id,
        memory_metadata={"source_ids": ["src_1"]},
    )
    assert created is not None
    assert created.memory_type == "preference"

    listed = workspace_service.list_memories(workspace.id)
    assert listed is not None
    assert len(listed) == 1
    assert listed[0].title == "默认中文输出"

    disabled = workspace_service.update_memory(workspace.id, created.id, status="disabled")
    assert disabled is not None
    assert disabled.status == "disabled"

    no_memory_context = workspace_service.build_prompt_context(
        workspace.id,
        current_query="继续数据库方案",
    )
    assert no_memory_context is not None
    assert no_memory_context.loaded_memory_ids == []

    reenabled = workspace_service.update_memory(workspace.id, created.id, status="active")
    assert reenabled is not None
    prompt_context = workspace_service.build_prompt_context(
        workspace.id,
        current_query="继续数据库方案",
        current_chat_id=session.id,
    )
    assert prompt_context is not None
    assert created.id in prompt_context.loaded_memory_ids
    assert "Workspace Memory Cards" in prompt_context.prompt_block
    loaded_memory = workspace_service.get_memory(workspace.id, created.id)
    assert loaded_memory is not None
    assert loaded_memory.last_used_at is not None

    suggested = workspace_service.suggest_memory_from_message(
        workspace.id,
        chat_id=session.id,
        message_id=assistant.id,
        source_ids=["src_1"],
    )
    assert suggested is not None
    assert suggested.source_session_id == session.id
    assert suggested.memory_metadata["source_ids"] == ["src_1"]

    assert workspace_service.delete_memory(workspace.id, created.id) is True
    assert workspace_service.list_memories(workspace.id) == []


def test_workspace_memory_candidate_conflict_and_approval_flow(temp_db):
    workspace_service, chat_service, _ = temp_db

    workspace = workspace_service.create_workspace(name="Candidate Workspace")
    session = chat_service.create_chat(title="Memory review chat", workspace_id=workspace.id)
    chat_service.add_message(session.id, "assistant", "默认用中文输出。")
    first_assistant = next(msg for msg in chat_service.get_chat(session.id).messages if msg.role == "assistant")

    existing = workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        title="默认中文输出",
        content="默认用中文输出。",
        source_session_id=session.id,
        source_message_id=first_assistant.id,
    )
    assert existing is not None

    chat_service.add_message(session.id, "assistant", "默认用中文输出，但回答要更简洁直接。")
    latest_assistant = [msg for msg in chat_service.get_chat(session.id).messages if msg.role == "assistant"][-1]

    candidate = workspace_service.suggest_memory_candidate_from_message(
        workspace.id,
        chat_id=session.id,
        message_id=latest_assistant.id,
        source_ids=["src_1"],
    )
    assert candidate is not None
    assert candidate.status == "pending"
    assert candidate.conflict_memory_id == existing.id
    assert candidate.suggested_action in {"replace_existing", "update_existing"}
    assert candidate.score is not None and candidate.score >= 0.5

    pending = workspace_service.list_memory_candidates(workspace.id)
    assert pending is not None
    assert [item.id for item in pending] == [candidate.id]

    approved = workspace_service.approve_memory_candidate(
        workspace.id,
        candidate.id,
        approval_mode="replace_existing",
    )
    assert approved is not None
    assert approved.supersedes_memory_id == existing.id

    existing_after = workspace_service.get_memory(workspace.id, existing.id)
    assert existing_after is not None
    assert existing_after.status == "superseded"

    candidates_after = workspace_service.list_memory_candidates(workspace.id, include_reviewed=True)
    assert candidates_after is not None
    assert candidates_after[0].status == "approved"


def test_workspace_memory_candidate_can_be_rejected(temp_db):
    workspace_service, chat_service, _ = temp_db

    workspace = workspace_service.create_workspace(name="Candidate Reject Workspace")
    session = chat_service.create_chat(title="Reject memory chat", workspace_id=workspace.id)
    chat_service.add_message(session.id, "assistant", "也许后面可以再看看 Redis 方案？")
    assistant = next(msg for msg in chat_service.get_chat(session.id).messages if msg.role == "assistant")

    candidate = workspace_service.suggest_memory_candidate_from_message(
        workspace.id,
        chat_id=session.id,
        message_id=assistant.id,
    )
    assert candidate is not None

    assert workspace_service.reject_memory_candidate(
        workspace.id,
        candidate.id,
        reason="Too tentative for long-term memory",
    ) is True

    reviewed = workspace_service.get_memory_candidate(workspace.id, candidate.id)
    assert reviewed is not None
    assert reviewed.status == "rejected"
    assert reviewed.candidate_metadata["rejection_reason"] == "Too tentative for long-term memory"


def test_workspace_memory_candidate_can_be_suggested_from_note_and_approval_marks_note_promoted(temp_db):
    workspace_service, chat_service, _ = temp_db
    notebook_service = NotebookService()

    workspace = workspace_service.create_workspace(name="Notebook Memory")
    session = chat_service.create_chat(title="Memory note", workspace_id=workspace.id)
    note = notebook_service.create_note(
        title="默认中文输出",
        content="今后默认使用中文回复，并在需要时保持结构化总结。",
        workspace_id=workspace.id,
        note_type="preference",
        source_session_id=session.id,
        source_metadata={"captured_from": "assistant_message"},
    )

    candidate = workspace_service.suggest_memory_candidate_from_note(workspace.id, note_id=note.id)
    assert candidate is not None
    assert candidate.source_session_id == session.id
    assert candidate.candidate_metadata["note_id"] == note.id
    assert candidate.candidate_metadata["suggested_from"] == "workspace_note"

    approved = workspace_service.approve_memory_candidate(
        workspace.id,
        candidate.id,
        approval_mode="create_new",
    )
    assert approved is not None

    updated_note = notebook_service.get_note(note.id)
    assert updated_note is not None
    assert updated_note.status == "promoted"
    assert updated_note.promoted_memory_id == approved.id

    prompt_context = notebook_service.build_prompt_context(
        workspace.id,
        current_query="请继续记住中文输出偏好",
    )
    assert prompt_context is None


def test_build_note_promotion_hint_marks_ready_and_pending_candidate(temp_db):
    workspace_service, chat_service, _ = temp_db
    notebook_service = NotebookService()

    workspace = workspace_service.create_workspace(name="Promotion Hint Workspace")
    session = chat_service.create_chat(title="Hint chat", workspace_id=workspace.id)
    note = notebook_service.create_note(
        title="默认中文输出",
        content="今后默认使用中文回复，并保持结构化总结。",
        workspace_id=workspace.id,
        note_type="preference",
        source_session_id=session.id,
        source_metadata={"captured_from": "assistant_message"},
    )

    ready_hint = workspace_service.build_note_promotion_hint(workspace.id, note_id=note.id)
    assert ready_hint["eligible"] is True
    assert ready_hint["state"] == "ready"
    assert ready_hint["memory_type"] == "preference"
    assert ready_hint["suggested_action"] == "create_new"
    assert "reason_summary" in ready_hint

    candidate = workspace_service.suggest_memory_candidate_from_note(workspace.id, note_id=note.id)
    assert candidate is not None

    pending_hint = workspace_service.build_note_promotion_hint(workspace.id, note_id=note.id)
    assert pending_hint["state"] == "candidate_pending"
    assert pending_hint["candidate_id"] == candidate.id
    assert pending_hint["candidate_status"] == "pending"


def test_workspace_memory_supports_scope_expiry_and_bulk_status_updates(temp_db):
    workspace_service, chat_service, db_file = temp_db

    workspace = workspace_service.create_workspace(name="Scoped Memory Workspace")
    session = chat_service.create_chat(title="Scoped memory chat", workspace_id=workspace.id)
    chat_service.add_message(session.id, "assistant", "当前项目先不引入独立向量库。")
    assistant = next(msg for msg in chat_service.get_chat(session.id).messages if msg.role == "assistant")

    user_memory = workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        scope_type="user",
        title="默认中文输出",
        content="默认中文，先给结论后展开。",
        why_saved="这是用户长期协作偏好。",
        pinned=True,
        editable=True,
        revocable=True,
        source_session_id=session.id,
        source_message_id=assistant.id,
    )
    project_memory = workspace_service.create_memory(
        workspace.id,
        memory_type="historical_conclusion",
        scope_type="project",
        title="否决 Redis-only 方案",
        content="历史评审已经否决 Redis-only 方案。",
        expires_at="2099-01-01T00:00:00",
        source_session_id=session.id,
        source_message_id=assistant.id,
    )
    expired_chat_memory = workspace_service.create_memory(
        workspace.id,
        memory_type="decision",
        scope_type="chat",
        scope_ref=session.id,
        title="临时聊天约束",
        content="只对这个会话生效。",
        expires_at="2000-01-01T00:00:00",
        source_session_id=session.id,
        source_message_id=assistant.id,
    )

    assert user_memory is not None
    assert project_memory is not None
    assert expired_chat_memory is not None

    scoped_context = workspace_service.build_prompt_context(
        workspace.id,
        current_query="继续评估项目技术方案",
        current_chat_id=session.id,
    )
    assert scoped_context is not None
    assert user_memory.id in scoped_context.loaded_memory_ids
    assert project_memory.id in scoped_context.loaded_memory_ids
    assert expired_chat_memory.id not in scoped_context.loaded_memory_ids

    with sqlite3.connect(db_file) as conn:
        conn.execute(
            "UPDATE workspace_memory_cards SET scope_ref = NULL WHERE id = ?",
            (project_memory.id,),
        )
        conn.commit()

    compatibility_context = workspace_service.build_prompt_context(
        workspace.id,
        current_query="继续评估项目技术方案",
        current_chat_id=session.id,
    )
    assert compatibility_context is not None
    assert project_memory.id in compatibility_context.loaded_memory_ids

    global_context = workspace_service.build_prompt_context(
        None,
        current_query="继续沿用我的写作偏好",
        current_chat_id=session.id,
    )
    assert global_context is not None
    assert global_context.workspace_id == "global"
    assert user_memory.id in global_context.loaded_memory_ids
    assert project_memory.id not in global_context.loaded_memory_ids

    updated_count = workspace_service.bulk_update_memory_status_by_type(
        workspace.id,
        memory_type="historical_conclusion",
        status="disabled",
    )
    assert updated_count == 1
    updated_project_memory = workspace_service.get_memory(workspace.id, project_memory.id)
    assert updated_project_memory is not None
    assert updated_project_memory.status == "disabled"


def test_workspace_memory_preserves_recurring_instruction_type(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Instruction Workspace")
    preference = workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        title="默认中文输出",
        content="默认中文回复。",
    )
    instruction = workspace_service.create_memory(
        workspace.id,
        memory_type="recurring_instruction",
        title="总结时给出下一步",
        content="在总结里总是明确下一步。",
    )

    assert preference is not None
    assert instruction is not None
    assert instruction.memory_type == "recurring_instruction"

    updated_count = workspace_service.bulk_update_memory_status_by_type(
        workspace.id,
        memory_type="recurring_instruction",
        status="disabled",
    )
    assert updated_count == 1

    updated_preference = workspace_service.get_memory(workspace.id, preference.id)
    updated_instruction = workspace_service.get_memory(workspace.id, instruction.id)
    assert updated_preference is not None
    assert updated_instruction is not None
    assert updated_preference.status == "active"
    assert updated_instruction.status == "disabled"


def test_workspace_memory_enforces_editable_and_revocable_flags(temp_db):
    workspace_service, _, _ = temp_db

    workspace = workspace_service.create_workspace(name="Protected Memory Workspace")
    locked = workspace_service.create_memory(
        workspace.id,
        memory_type="decision",
        title="Do not edit directly",
        content="This memory is protected.",
        editable=False,
        revocable=False,
    )

    assert locked is not None

    with pytest.raises(ValueError, match="memory_not_editable"):
        workspace_service.update_memory(workspace.id, locked.id, content="Changed")

    updated_count = workspace_service.bulk_update_memory_status_by_type(
        workspace.id,
        memory_type="decision",
        status="disabled",
    )
    assert updated_count == 0
    locked_after_bulk = workspace_service.get_memory(workspace.id, locked.id)
    assert locked_after_bulk is not None
    assert locked_after_bulk.status == "active"

    with pytest.raises(ValueError, match="memory_not_revocable"):
        workspace_service.delete_memory(workspace.id, locked.id)

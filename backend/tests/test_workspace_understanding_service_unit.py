import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.chat import WorkspaceMemoryCandidate as WorkspaceMemoryCandidateModel
from app.models.chat import WorkspaceMemoryCard as WorkspaceMemoryCardModel
from app.services.workspace_service import WorkspaceService
from app.services.workspace_understanding_service import (
    WORKSPACE_UNDERSTANDING_GROUPS,
    WorkspaceUnderstandingService,
)


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_yue.db")
    test_engine = create_engine(f"sqlite:///{db_file}")
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    Base.metadata.create_all(bind=test_engine)
    with patch("app.services.workspace_service.engine", test_engine), \
         patch("app.services.workspace_service.SessionLocal", testing_session_local), \
         patch("app.services.workspace_understanding_service.SessionLocal", testing_session_local):
        yield WorkspaceService(), WorkspaceUnderstandingService(), testing_session_local

    test_engine.dispose()
    shutil.rmtree(temp_dir)


def test_summary_returns_fixed_groups_in_stable_order_when_empty(temp_db):
    workspace_service, understanding_service, _ = temp_db
    workspace = workspace_service.create_workspace(name="Empty Understanding")

    summary = understanding_service.build_summary(workspace.id)

    assert summary is not None
    assert summary.workspace_id == workspace.id
    assert [group.group for group in summary.groups] == [group.key for group in WORKSPACE_UNDERSTANDING_GROUPS]
    assert [group.label for group in summary.groups] == [group.label for group in WORKSPACE_UNDERSTANDING_GROUPS]
    assert all(group.total_count == 0 for group in summary.groups)
    assert all(group.active_count == 0 for group in summary.groups)
    assert all(group.pending_count == 0 for group in summary.groups)


def test_summary_groups_workspace_memories_and_pending_candidates(temp_db):
    workspace_service, understanding_service, testing_session_local = temp_db
    workspace = workspace_service.create_workspace(name="Grouped Understanding")
    decision = workspace_service.create_memory(
        workspace.id,
        memory_type="decision",
        title="Use fixed groups",
        content="Workspace Understanding uses fixed groups.",
        status="active",
    )
    assert decision is not None
    workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        title="Keep confirmations inline",
        content="Memory confirmations should not interrupt the task.",
        status="disabled",
    )
    workspace_service.create_memory(
        workspace.id,
        memory_type="project_fact",
        scope_type="user",
        title="Cross-workspace preference",
        content="Prefer conclusion-first answers.",
        status="active",
    )

    with testing_session_local() as db:
        db.add(
            WorkspaceMemoryCandidateModel(
                id="candidate-1",
                workspace_id=workspace.id,
                memory_type="open_question",
                scope_type="workspace",
                scope_ref=workspace.id,
                title="Choose detector type",
                content="Should memory detection start rule-based or LLM-assisted?",
                status="pending",
                score=0.8,
                suggested_action="create_new",
                candidate_metadata_json="{}",
                created_at=datetime.utcnow() + timedelta(seconds=1),
                updated_at=datetime.utcnow() + timedelta(seconds=1),
            )
        )
        db.commit()

    summary = understanding_service.build_summary(workspace.id)

    assert summary is not None
    by_group = {group.group: group for group in summary.groups}
    assert by_group["decisions"].total_count == 1
    assert by_group["decisions"].active_count == 1
    assert by_group["decisions"].representative_items[0].title == "Use fixed groups"
    assert by_group["preferences"].total_count == 1
    assert by_group["preferences"].active_count == 0
    assert by_group["open_questions"].total_count == 0
    assert by_group["open_questions"].pending_count == 1
    assert by_group["open_questions"].representative_items[0].kind == "candidate"
    assert all(
        item.title != "Cross-workspace preference"
        for group in summary.groups
        for item in group.representative_items
    )


def test_summary_previews_active_user_memories_without_mixing_into_workspace_groups(temp_db):
    workspace_service, understanding_service, _ = temp_db
    workspace = workspace_service.create_workspace(name="Two Layer Understanding")
    other_workspace = workspace_service.create_workspace(name="Other Workspace")
    workspace_service.create_memory(
        other_workspace.id,
        memory_type="preference",
        scope_type="user",
        title="Prefers concise answers",
        content="The user prefers concise answers with clear next steps.",
        status="active",
        confidence=0.92,
    )
    workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        scope_type="user",
        title="Disabled user preference",
        content="This disabled preference should not be applied.",
        status="disabled",
    )
    workspace_service.create_memory(
        workspace.id,
        memory_type="preference",
        scope_type="user",
        title="Expired user preference",
        content="This expired preference should not be applied.",
        status="active",
        expires_at=datetime.utcnow() - timedelta(days=1),
    )
    workspace_service.create_memory(
        workspace.id,
        memory_type="decision",
        scope_type="workspace",
        title="Use two-layer model",
        content="Workspace uses About You and About This Workspace.",
        status="active",
    )

    summary = understanding_service.build_summary(workspace.id)

    assert summary is not None
    assert [item.title for item in summary.applied_user_memory_preview] == ["Prefers concise answers"]
    preview = summary.applied_user_memory_preview[0]
    assert preview.scope_type == "user"
    assert preview.kind == "memory"
    assert preview.confidence == 0.92
    grouped_titles = [item.title for group in summary.groups for item in group.representative_items]
    assert "Prefers concise answers" not in grouped_titles
    assert "Disabled user preference" not in grouped_titles
    assert "Expired user preference" not in grouped_titles
    assert "Use two-layer model" in grouped_titles


def test_summary_respects_understanding_group_metadata_override(temp_db):
    workspace_service, understanding_service, _ = temp_db
    workspace = workspace_service.create_workspace(name="Override Understanding")
    workspace_service.create_memory(
        workspace.id,
        memory_type="historical_conclusion",
        title="Launch goal",
        content="The near-term goal is to make Workspace feel smarter with use.",
        status="active",
        memory_metadata={"understanding_group": "goals"},
    )

    summary = understanding_service.build_summary(workspace.id)

    assert summary is not None
    by_group = {group.group: group for group in summary.groups}
    assert by_group["goals"].total_count == 1
    assert by_group["goals"].representative_items[0].title == "Launch goal"
    assert by_group["background"].total_count == 0


def test_summary_includes_legacy_memories_with_missing_scope_type(temp_db):
    workspace_service, understanding_service, testing_session_local = temp_db
    workspace = workspace_service.create_workspace(name="Legacy Scope Understanding")

    with testing_session_local() as db:
        db.add(
            WorkspaceMemoryCardModel(
                id="legacy-memory-1",
                workspace_id=workspace.id,
                memory_type="project_fact",
                scope_type=None,
                scope_ref=None,
                title="Legacy project context",
                content="Older memory rows may not have scope fields populated.",
                status="active",
                confidence=0.75,
                created_by="user",
                memory_metadata_json="{}",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        db.commit()

    summary = understanding_service.build_summary(workspace.id)

    assert summary is not None
    by_group = {group.group: group for group in summary.groups}
    assert by_group["background"].total_count == 1
    assert by_group["background"].representative_items[0].scope_type == "workspace"


def test_summary_returns_none_for_missing_workspace(temp_db):
    _, understanding_service, _ = temp_db

    assert understanding_service.build_summary("missing-workspace") is None

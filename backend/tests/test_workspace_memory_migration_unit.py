import sqlite3
import tempfile
from importlib import util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "d4b8e2f1c6a7_add_memory_scope_and_lifecycle_fields.py"
)


def _load_migration_module():
    spec = util.spec_from_file_location("workspace_memory_scope_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workspace_memory_migration_backfills_scope_refs_for_legacy_rows() -> None:
    module = _load_migration_module()

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "legacy-memory.db"
        engine = create_engine(f"sqlite:///{db_path}")

        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE workspace_memory_cards (
                    id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    memory_type VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'active',
                    confidence FLOAT,
                    created_by VARCHAR,
                    source_session_id VARCHAR,
                    source_message_id INTEGER,
                    supersedes_memory_id VARCHAR,
                    last_used_at DATETIME,
                    memory_metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at DATETIME,
                    updated_at DATETIME
                );

                CREATE TABLE workspace_memory_candidates (
                    id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    memory_type VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    content TEXT NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'pending',
                    score FLOAT,
                    suggested_action VARCHAR,
                    conflict_memory_id VARCHAR,
                    source_session_id VARCHAR,
                    source_message_id INTEGER,
                    reviewed_at DATETIME,
                    candidate_metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at DATETIME,
                    updated_at DATETIME
                );
                """
            )
            conn.execute(
                """
                INSERT INTO workspace_memory_cards (
                    id, workspace_id, memory_type, title, content, status, confidence, created_by,
                    source_session_id, source_message_id, supersedes_memory_id, last_used_at,
                    memory_metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "mem_legacy_1",
                    "ws_legacy",
                    "project_fact",
                    "Legacy architecture fact",
                    "This card was created before scope fields existed.",
                    "active",
                    0.75,
                    "user",
                    None,
                    None,
                    None,
                    None,
                    "{}",
                    "2026-06-01T00:00:00",
                    "2026-06-01T00:00:00",
                ),
            )
            conn.execute(
                """
                INSERT INTO workspace_memory_candidates (
                    id, workspace_id, memory_type, title, content, status, score, suggested_action,
                    conflict_memory_id, source_session_id, source_message_id, reviewed_at,
                    candidate_metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "cand_legacy_1",
                    "ws_legacy",
                    "decision",
                    "Legacy candidate",
                    "This candidate also predates scope fields.",
                    "pending",
                    0.61,
                    "create_new",
                    "mem_legacy_1",
                    None,
                    None,
                    None,
                    "{}",
                    "2026-06-01T00:00:00",
                    "2026-06-01T00:00:00",
                ),
            )
            conn.commit()

        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            operations = Operations(context)
            op_before = module.op
            module.op = operations
            try:
                module.upgrade()
            finally:
                module.op = op_before

        with sqlite3.connect(db_path) as conn:
            memory_row = conn.execute(
                """
                SELECT scope_type, scope_ref, why_saved, pinned, editable, revocable, expires_at
                FROM workspace_memory_cards
                WHERE id = ?
                """,
                ("mem_legacy_1",),
            ).fetchone()
            candidate_row = conn.execute(
                """
                SELECT scope_type, scope_ref, why_saved, expires_at
                FROM workspace_memory_candidates
                WHERE id = ?
                """,
                ("cand_legacy_1",),
            ).fetchone()

        assert memory_row == ("workspace", "ws_legacy", None, 0, 1, 1, None)
        assert candidate_row == ("workspace", "ws_legacy", None, None)

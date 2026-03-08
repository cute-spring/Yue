import sqlite3
import json
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
DB_FILE = os.path.join(DATA_DIR, "yue.db")
OLD_CHATS_FILE = os.path.join(DATA_DIR, "chats.json")

class Message(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    thought_duration: Optional[float] = None
    ttft: Optional[float] = None
    total_duration: Optional[float] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

class ToolCall(BaseModel):
    id: Optional[int] = None
    session_id: str
    message_id: Optional[int] = None
    call_id: str
    tool_name: str
    args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None
    error: Optional[str] = None
    status: str  # 'running', 'success', 'error'
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

class SkillEffectivenessEvent(BaseModel):
    id: Optional[int] = None
    session_id: str
    reason_code: str
    selection_source: str
    fallback_used: bool
    selected_skill_name: Optional[str] = None
    selected_skill_version: Optional[str] = None
    visible_skill_count: Optional[int] = None
    available_skill_count: Optional[int] = None
    always_injected_count: Optional[int] = None
    summary_injected: Optional[bool] = None
    summary_prompt_enabled: Optional[bool] = None
    lazy_full_load_enabled: Optional[bool] = None
    system_prompt_tokens_estimate: Optional[int] = None
    user_message_tokens_estimate: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    id: str
    title: str
    agent_id: Optional[str] = None
    active_skill_name: Optional[str] = None
    active_skill_version: Optional[str] = None
    messages: List[Message] = []
    created_at: datetime
    updated_at: datetime

class ChatService:
    def __init__(self):
        self._ensure_db()
        self._migrate_from_json()

    def _get_connection(self):
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    agent_id TEXT,
                    active_skill_name TEXT,
                    active_skill_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    thought_duration REAL,
                    ttft REAL,
                    total_duration REAL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    finish_reason TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    message_id INTEGER,
                    call_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    args TEXT,
                    result TEXT,
                    error TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    duration_ms REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
                    FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_effectiveness_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    selection_source TEXT NOT NULL,
                    fallback_used INTEGER NOT NULL,
                    selected_skill_name TEXT,
                    selected_skill_version TEXT,
                    visible_skill_count INTEGER,
                    available_skill_count INTEGER,
                    always_injected_count INTEGER,
                    summary_injected INTEGER,
                    summary_prompt_enabled INTEGER,
                    lazy_full_load_enabled INTEGER,
                    system_prompt_tokens_estimate INTEGER,
                    user_message_tokens_estimate INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            
            # Create Index for Performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session_id ON tool_calls(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_call_id ON tool_calls(call_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_effectiveness_session_id ON skill_effectiveness_events(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_effectiveness_created_at ON skill_effectiveness_events(created_at)")
            
            conn.commit()
            
            # Ensure columns exist (for existing dbs)
            session_cursor = conn.execute("PRAGMA table_info(sessions)")
            session_columns = [info[1] for info in session_cursor.fetchall()]
            if "active_skill_name" not in session_columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN active_skill_name TEXT")
                conn.commit()
            if "active_skill_version" not in session_columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN active_skill_version TEXT")
                conn.commit()
            cursor = conn.execute("PRAGMA table_info(messages)")
            columns = [info[1] for info in cursor.fetchall()]
            if "thought_duration" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN thought_duration REAL")
                conn.commit()
            
            if "ttft" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN ttft REAL")
                conn.commit()

            if "total_duration" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN total_duration REAL")
                conn.commit()

            if "prompt_tokens" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN prompt_tokens INTEGER")
                conn.commit()

            if "completion_tokens" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN completion_tokens INTEGER")
                conn.commit()

            if "total_tokens" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN total_tokens INTEGER")
                conn.commit()
            
            if "finish_reason" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN finish_reason TEXT")
                conn.commit()
            
            # Ensure images column exists
            if "images" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN images TEXT")
                conn.commit()

    def _migrate_from_json(self):
        if not os.path.exists(OLD_CHATS_FILE):
            return
        
        print("Migrating old JSON chats to SQLite...")
        try:
            with open(OLD_CHATS_FILE, 'r') as f:
                old_data = json.load(f)
            
            with self._get_connection() as conn:
                for chat in old_data:
                    # Check if session exists
                    cursor = conn.execute("SELECT id FROM sessions WHERE id = ?", (chat['id'],))
                    if cursor.fetchone():
                        continue
                    
                    # Insert session
                    conn.execute(
                        "INSERT INTO sessions (id, title, agent_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (chat['id'], chat['title'], chat.get('agent_id'), chat['created_at'], chat['updated_at'])
                    )
                    
                    # Insert messages
                    for msg in chat.get('messages', []):
                        conn.execute(
                            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                            (chat['id'], msg['role'], msg['content'], msg['timestamp'])
                        )
                conn.commit()
            
            # Rename old file to backup
            os.rename(OLD_CHATS_FILE, OLD_CHATS_FILE + ".bak")
            print("Migration completed successfully.")
        except Exception as e:
            print(f"Migration error: {e}")

    def list_chats(self) -> List[ChatSession]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
            sessions = []
            for row in cursor.fetchall():
                # Get messages for each session
                msg_cursor = conn.execute("SELECT role, content, images, timestamp, thought_duration, ttft, total_duration, prompt_tokens, completion_tokens, total_tokens, finish_reason FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (row['id'],))
                messages = []
                for m in msg_cursor.fetchall():
                    msg_dict = dict(m)
                    if msg_dict.get('images'):
                        try:
                            msg_dict['images'] = json.loads(msg_dict['images'])
                        except:
                            msg_dict['images'] = []
                    messages.append(Message(**msg_dict))
                
                sessions.append(ChatSession(
                    id=row['id'],
                    title=row['title'],
                    agent_id=row['agent_id'],
                    active_skill_name=row['active_skill_name'],
                    active_skill_version=row['active_skill_version'],
                    messages=messages,
                    created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
                    updated_at=datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
                ))
            return sessions

    def get_chat(self, chat_id: str) -> Optional[ChatSession]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (chat_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            msg_cursor = conn.execute("SELECT id, role, content, images, timestamp, thought_duration, ttft, total_duration, prompt_tokens, completion_tokens, total_tokens, finish_reason FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (chat_id,))
            messages = []
            
            # Fetch all tool calls for this session once
            all_tool_calls = self.get_tool_calls(chat_id)
            # Map tool calls to messages if possible (though currently they are session-linked)
            # For Phase 3, we'll just attach all tool calls to the relevant assistant message
            # or keep them separate. The frontend expects them on the message.
            
            for m in msg_cursor.fetchall():
                msg_dict = dict(m)
                if msg_dict.get('images'):
                    try:
                        msg_dict['images'] = json.loads(msg_dict['images'])
                    except:
                        msg_dict['images'] = []
                
                # Simple heuristic: attach tool calls to assistant messages
                # In a more advanced version, we'd use message_id FK
                if msg_dict['role'] == 'assistant':
                    # For now, we'll just attach all tool calls to the last assistant message
                    # or better, implement the message_id linking in Phase 4.
                    # For this phase, let's just provide them.
                    msg_dict['tool_calls'] = [tc.model_dump() for tc in all_tool_calls]
                
                messages.append(Message(**msg_dict))
            
            return ChatSession(
                id=row['id'],
                title=row['title'],
                agent_id=row['agent_id'],
                active_skill_name=row['active_skill_name'],
                active_skill_version=row['active_skill_version'],
                messages=messages,
                created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
                updated_at=datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
            )

    def create_chat(self, agent_id: Optional[str] = None, title: str = "New Chat") -> ChatSession:
        chat_id = str(uuid.uuid4())
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, agent_id, active_skill_name, active_skill_version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (chat_id, title, agent_id, None, None, now, now)
            )
            conn.commit()
        
        return ChatSession(
            id=chat_id,
            title=title,
            agent_id=agent_id,
            active_skill_name=None,
            active_skill_version=None,
            messages=[],
            created_at=now,
            updated_at=now
        )

    def get_session_skill(self, chat_id: str) -> tuple[Optional[str], Optional[str]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT active_skill_name, active_skill_version FROM sessions WHERE id = ?",
                (chat_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None, None
            return row["active_skill_name"], row["active_skill_version"]

    def set_session_skill(self, chat_id: str, name: str, version: str) -> None:
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET active_skill_name = ?, active_skill_version = ?, updated_at = ? WHERE id = ?",
                (name, version, now, chat_id)
            )
            conn.commit()

    def clear_session_skill(self, chat_id: str) -> None:
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET active_skill_name = NULL, active_skill_version = NULL, updated_at = ? WHERE id = ?",
                (now, chat_id)
            )
            conn.commit()

    def add_message(
        self, 
        chat_id: str, 
        role: str, 
        content: str, 
        thought_duration: Optional[float] = None, 
        images: Optional[List[str]] = None, 
        ttft: Optional[float] = None, 
        total_duration: Optional[float] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        finish_reason: Optional[str] = None
    ) -> Optional[ChatSession]:
        now = datetime.now()
        with self._get_connection() as conn:
            # Check if session exists
            cursor = conn.execute("SELECT title FROM sessions WHERE id = ?", (chat_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Add message
            images_json = json.dumps(images) if images else None
            conn.execute(
                "INSERT INTO messages (session_id, role, content, images, timestamp, thought_duration, ttft, total_duration, prompt_tokens, completion_tokens, total_tokens, finish_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (chat_id, role, content, images_json, now, thought_duration, ttft, total_duration, prompt_tokens, completion_tokens, total_tokens, finish_reason)
            )
            
            # Update title if it's the first user message
            new_title = row['title']
            if role == "user":
                msg_count_cursor = conn.execute("SELECT COUNT(*) as count FROM messages WHERE session_id = ?", (chat_id,))
                if msg_count_cursor.fetchone()['count'] == 1 and new_title == "New Chat":
                    new_title = content[:30] + "..." if len(content) > 30 else content
            
            # Update session
            conn.execute(
                "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                (new_title, now, chat_id)
            )
            conn.commit()
            
        return self.get_chat(chat_id)

    def delete_chat(self, chat_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (chat_id,))
            conn.commit()
            return cursor.rowcount > 0

    def truncate_chat(self, chat_id: str, keep_count: int) -> bool:
        with self._get_connection() as conn:
            # Get all message IDs ordered by timestamp
            cursor = conn.execute("SELECT id FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (chat_id,))
            rows = cursor.fetchall()
            
            if len(rows) <= keep_count:
                return False
                
            # Identify IDs to delete
            to_delete = [row['id'] for row in rows[keep_count:]]
            if not to_delete:
                return False
                
            placeholders = ','.join('?' for _ in to_delete)
            conn.execute(f"DELETE FROM messages WHERE id IN ({placeholders})", to_delete)
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (datetime.now(), chat_id)
            )
            conn.commit()
            return True

    def add_tool_call(self, session_id: str, call_id: str, tool_name: str, args: Optional[Dict[str, Any]] = None) -> None:
        """Record the start of a tool call."""
        now = datetime.now()
        args_json = json.dumps(args) if args else None
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO tool_calls (session_id, call_id, tool_name, args, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, call_id, tool_name, args_json, 'running', now)
            )
            conn.commit()

    def update_tool_call(
        self, 
        call_id: str, 
        status: str, 
        result: Optional[str] = None, 
        error: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> None:
        """Update an existing tool call with results or errors."""
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE tool_calls SET status = ?, result = ?, error = ?, finished_at = ?, duration_ms = ? WHERE call_id = ?",
                (status, result, error, now, duration_ms, call_id)
            )
            conn.commit()

    def get_tool_calls(self, session_id: str) -> List[ToolCall]:
        """Retrieve all tool calls for a given session."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY created_at ASC", 
                (session_id,)
            )
            rows = cursor.fetchall()
            tool_calls = []
            for row in rows:
                tool_dict = dict(row)
                if tool_dict.get('args'):
                    try:
                        tool_dict['args'] = json.loads(tool_dict['args'])
                    except:
                        tool_dict['args'] = {}
                
                # Convert timestamps
                for key in ['created_at', 'finished_at']:
                    if tool_dict.get(key) and isinstance(tool_dict[key], str):
                        tool_dict[key] = datetime.fromisoformat(tool_dict[key])
                
                tool_calls.append(ToolCall(**tool_dict))
            return tool_calls

    def add_skill_effectiveness_event(self, session_id: str, event: Dict[str, Any]) -> None:
        now = datetime.now()
        selected = event.get("selected_skill") or {}
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO skill_effectiveness_events (
                    session_id,
                    reason_code,
                    selection_source,
                    fallback_used,
                    selected_skill_name,
                    selected_skill_version,
                    visible_skill_count,
                    available_skill_count,
                    always_injected_count,
                    summary_injected,
                    summary_prompt_enabled,
                    lazy_full_load_enabled,
                    system_prompt_tokens_estimate,
                    user_message_tokens_estimate,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    str(event.get("reason_code") or "unknown"),
                    str(event.get("selection_source") or "none"),
                    1 if bool(event.get("fallback_used")) else 0,
                    selected.get("name"),
                    selected.get("version"),
                    event.get("visible_skill_count"),
                    event.get("available_skill_count"),
                    event.get("always_injected_count"),
                    1 if bool(event.get("summary_injected")) else 0,
                    1 if bool(event.get("summary_prompt_enabled")) else 0,
                    1 if bool(event.get("lazy_full_load_enabled")) else 0,
                    event.get("system_prompt_tokens_estimate"),
                    event.get("user_message_tokens_estimate"),
                    now,
                )
            )
            conn.commit()

    def get_skill_effectiveness_report(self, hours: int = 24) -> Dict[str, Any]:
        hours = max(1, int(hours))
        since_expr = f"-{hours} hours"
        with self._get_connection() as conn:
            agg = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_runs,
                    SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) AS fallback_runs,
                    AVG(system_prompt_tokens_estimate) AS avg_system_prompt_tokens,
                    AVG(user_message_tokens_estimate) AS avg_user_message_tokens
                FROM skill_effectiveness_events
                WHERE created_at >= datetime('now', ?)
                """,
                (since_expr,)
            ).fetchone()
            reason_rows = conn.execute(
                """
                SELECT reason_code, COUNT(*) AS cnt
                FROM skill_effectiveness_events
                WHERE created_at >= datetime('now', ?)
                GROUP BY reason_code
                ORDER BY cnt DESC
                """,
                (since_expr,)
            ).fetchall()
            skill_rows = conn.execute(
                """
                SELECT selected_skill_name, COUNT(*) AS cnt
                FROM skill_effectiveness_events
                WHERE created_at >= datetime('now', ?)
                  AND selected_skill_name IS NOT NULL
                GROUP BY selected_skill_name
                ORDER BY cnt DESC
                LIMIT 10
                """,
                (since_expr,)
            ).fetchall()
        total_runs = int((agg["total_runs"] or 0) if agg else 0)
        fallback_runs = int((agg["fallback_runs"] or 0) if agg else 0)
        hit_rate = 0.0 if total_runs == 0 else (total_runs - fallback_runs) / total_runs
        fallback_rate = 0.0 if total_runs == 0 else fallback_runs / total_runs
        return {
            "window_hours": hours,
            "total_runs": total_runs,
            "skill_hit_rate": hit_rate,
            "fallback_rate": fallback_rate,
            "avg_system_prompt_tokens": float(agg["avg_system_prompt_tokens"] or 0.0) if agg else 0.0,
            "avg_user_message_tokens": float(agg["avg_user_message_tokens"] or 0.0) if agg else 0.0,
            "reason_distribution": [{ "reason_code": row["reason_code"], "count": int(row["cnt"]) } for row in reason_rows],
            "top_selected_skills": [{ "name": row["selected_skill_name"], "count": int(row["cnt"]) } for row in skill_rows],
        }

chat_service = ChatService()

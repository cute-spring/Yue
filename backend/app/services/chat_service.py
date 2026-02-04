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
    timestamp: datetime = Field(default_factory=datetime.now)
    thought_duration: Optional[float] = None

class ChatSession(BaseModel):
    id: str
    title: str
    agent_id: Optional[str] = None
    parent_id: Optional[str] = None
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    agent_id TEXT,
                    parent_id TEXT,
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
                    FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
                )
            """)
            conn.commit()

            # Ensure parent_id column exists (for existing dbs)
            cursor = conn.execute("PRAGMA table_info(sessions)")
            columns = [info[1] for info in cursor.fetchall()]
            if "parent_id" not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN parent_id TEXT")
                conn.commit()
            
            # Ensure thought_duration column exists (for existing dbs)
            cursor = conn.execute("PRAGMA table_info(messages)")
            columns = [info[1] for info in cursor.fetchall()]
            if "thought_duration" not in columns:
                conn.execute("ALTER TABLE messages ADD COLUMN thought_duration REAL")
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
                msg_cursor = conn.execute("SELECT role, content, timestamp, thought_duration FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (row['id'],))
                messages = [Message(**dict(m)) for m in msg_cursor.fetchall()]
                
                sessions.append(ChatSession(
                    id=row['id'],
                    title=row['title'],
                    agent_id=row['agent_id'],
                    parent_id=row['parent_id'] if 'parent_id' in row.keys() else None,
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
            
            msg_cursor = conn.execute("SELECT role, content, timestamp, thought_duration FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (chat_id,))
            messages = [Message(**dict(m)) for m in msg_cursor.fetchall()]
            
            return ChatSession(
                id=row['id'],
                title=row['title'],
                agent_id=row['agent_id'],
                parent_id=row['parent_id'] if 'parent_id' in row.keys() else None,
                messages=messages,
                created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
                updated_at=datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
            )

    def create_chat(self, agent_id: Optional[str] = None, title: str = "New Chat", parent_id: Optional[str] = None) -> ChatSession:
        chat_id = str(uuid.uuid4())
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, agent_id, parent_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, title, agent_id, parent_id, now, now)
            )
            conn.commit()
        
        return ChatSession(
            id=chat_id,
            title=title,
            agent_id=agent_id,
            parent_id=parent_id,
            messages=[],
            created_at=now,
            updated_at=now
        )

    def add_message(self, chat_id: str, role: str, content: str, thought_duration: Optional[float] = None) -> Optional[ChatSession]:
        now = datetime.now()
        with self._get_connection() as conn:
            # Check if session exists
            cursor = conn.execute("SELECT title FROM sessions WHERE id = ?", (chat_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            # Add message
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp, thought_duration) VALUES (?, ?, ?, ?, ?)",
                (chat_id, role, content, now, thought_duration)
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

    def list_sessions_meta(self, limit: int = 50, query: Optional[str] = None) -> List[Dict[str, Any]]:
        n = max(1, min(int(limit), 200))
        q = (query or "").strip()
        with self._get_connection() as conn:
            if q:
                cursor = conn.execute(
                    "SELECT id, title, agent_id, parent_id, created_at, updated_at FROM sessions "
                    "WHERE title LIKE ? ORDER BY updated_at DESC LIMIT ?",
                    (f"%{q}%", n),
                )
            else:
                cursor = conn.execute(
                    "SELECT id, title, agent_id, parent_id, created_at, updated_at FROM sessions "
                    "ORDER BY updated_at DESC LIMIT ?",
                    (n,),
                )
            rows = [dict(r) for r in cursor.fetchall()]
            for r in rows:
                for k in ("created_at", "updated_at"):
                    v = r.get(k)
                    if isinstance(v, datetime):
                        r[k] = v.isoformat()
            return rows

    def list_messages_meta(self, chat_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        n = max(1, min(int(limit), 200))
        off = max(0, int(offset))
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, role, content, timestamp, thought_duration FROM messages "
                "WHERE session_id = ? ORDER BY timestamp ASC LIMIT ? OFFSET ?",
                (chat_id, n, off),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            for r in rows:
                ts = r.get("timestamp")
                if isinstance(ts, datetime):
                    r["timestamp"] = ts.isoformat()
                if isinstance(r.get("content"), str) and len(r["content"]) > 2000:
                    r["content"] = r["content"][:2000]
            return rows

    def search_messages(self, query: str, limit: int = 20, chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return []
        n = max(1, min(int(limit), 200))
        with self._get_connection() as conn:
            if chat_id:
                cursor = conn.execute(
                    "SELECT m.id, m.session_id, m.role, m.content, m.timestamp "
                    "FROM messages m WHERE m.session_id = ? AND m.content LIKE ? "
                    "ORDER BY m.timestamp DESC LIMIT ?",
                    (chat_id, f"%{q}%", n),
                )
            else:
                cursor = conn.execute(
                    "SELECT m.id, m.session_id, m.role, m.content, m.timestamp "
                    "FROM messages m WHERE m.content LIKE ? "
                    "ORDER BY m.timestamp DESC LIMIT ?",
                    (f"%{q}%", n),
                )
            rows = [dict(r) for r in cursor.fetchall()]
            for r in rows:
                ts = r.get("timestamp")
                if isinstance(ts, datetime):
                    r["timestamp"] = ts.isoformat()
                content = r.get("content") or ""
                if isinstance(content, str):
                    r["snippet"] = content[:200]
                    if len(content) > 200:
                        r["snippet"] += "..."
                    r.pop("content", None)
            return rows

chat_service = ChatService()

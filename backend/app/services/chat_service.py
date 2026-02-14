import sqlite3
import json
import os
from typing import List, Optional, Dict
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

class ChatSession(BaseModel):
    id: str
    title: str
    agent_id: Optional[str] = None
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
            
            # Create Index for Performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
            
            conn.commit()
            
            # Ensure columns exist (for existing dbs)
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
            
            msg_cursor = conn.execute("SELECT role, content, images, timestamp, thought_duration, ttft, total_duration, prompt_tokens, completion_tokens, total_tokens, finish_reason FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (chat_id,))
            messages = []
            for m in msg_cursor.fetchall():
                msg_dict = dict(m)
                if msg_dict.get('images'):
                    try:
                        msg_dict['images'] = json.loads(msg_dict['images'])
                    except:
                        msg_dict['images'] = []
                messages.append(Message(**msg_dict))
            
            return ChatSession(
                id=row['id'],
                title=row['title'],
                agent_id=row['agent_id'],
                messages=messages,
                created_at=datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at'],
                updated_at=datetime.fromisoformat(row['updated_at']) if isinstance(row['updated_at'], str) else row['updated_at']
            )

    def create_chat(self, agent_id: Optional[str] = None, title: str = "New Chat") -> ChatSession:
        chat_id = str(uuid.uuid4())
        now = datetime.now()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, agent_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, title, agent_id, now, now)
            )
            conn.commit()
        
        return ChatSession(
            id=chat_id,
            title=title,
            agent_id=agent_id,
            messages=[],
            created_at=now,
            updated_at=now
        )

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

chat_service = ChatService()

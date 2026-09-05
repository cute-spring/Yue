import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.chat_service import ChatService

class TestChatService(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_yue.db")
        
        self.test_engine = create_engine(f"sqlite:///{self.test_db}")
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        
        # Set up patches
        Base.metadata.create_all(bind=self.test_engine)
        self.engine_patcher = patch("app.services.chat_service_schema.engine", self.test_engine)
        self.schema_session_patcher = patch("app.services.chat_service_schema.SessionLocal", self.TestingSessionLocal)
        self.sessions_patcher = patch("app.services.chat_service_sessions.SessionLocal", self.TestingSessionLocal)
        self.actions_patcher = patch("app.services.chat_service_actions.SessionLocal", self.TestingSessionLocal)
        
        self.engine_patcher.start()
        self.schema_session_patcher.start()
        self.sessions_patcher.start()
        self.actions_patcher.start()
        
        self.service = ChatService()

    def tearDown(self):
        # Stop patches
        self.engine_patcher.stop()
        self.schema_session_patcher.stop()
        self.sessions_patcher.stop()
        self.actions_patcher.stop()
        
        # Clean up test database
        self.test_engine.dispose()
        shutil.rmtree(self.temp_dir)

    def test_create_and_list_chats(self):
        # Create a new chat
        chat = self.service.create_chat(agent_id="test-agent", title="Test Chat")
        self.assertIsNotNone(chat.id)
        self.assertEqual(chat.title, "Test Chat")
        
        # List chats
        chats = self.service.list_chats()
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0].id, chat.id)

    def test_add_messages_and_context(self):
        # Create chat
        chat = self.service.create_chat()
        chat_id = chat.id
        
        # Add User Message
        self.service.add_message(chat_id, "user", "Hello AI")
        
        # Add Assistant Message
        self.service.add_message(chat_id, "assistant", "Hello human")
        
        # Verify messages are stored
        updated_chat = self.service.get_chat(chat_id)
        self.assertEqual(len(updated_chat.messages), 2)
        self.assertEqual(updated_chat.messages[0].role, "user")
        self.assertEqual(updated_chat.messages[1].role, "assistant")
        
        # Verify title auto-update logic (first user message)
        self.assertEqual(updated_chat.title, "Hello AI")

    def test_delete_chat(self):
        chat = self.service.create_chat()
        self.assertTrue(self.service.delete_chat(chat.id))
        self.assertIsNone(self.service.get_chat(chat.id))

if __name__ == "__main__":
    unittest.main()

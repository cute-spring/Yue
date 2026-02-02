import os
import sys
import unittest
from datetime import datetime

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.chat_service import ChatService, DB_FILE

class TestChatService(unittest.TestCase):
    def setUp(self):
        # Use a temporary test database
        self.test_db = "test_yue.db"
        # Temporarily override the DB_FILE in the module
        import app.services.chat_service
        self.original_db = app.services.chat_service.DB_FILE
        app.services.chat_service.DB_FILE = self.test_db
        
        self.service = ChatService()

    def tearDown(self):
        # Clean up test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        # Restore original DB_FILE
        import app.services.chat_service
        app.services.chat_service.DB_FILE = self.original_db

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

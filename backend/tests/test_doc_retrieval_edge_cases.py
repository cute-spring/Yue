import os
import tempfile
import unittest
from app.services.doc_retrieval import (
    search_text, 
    resolve_docs_root, 
    DocAccessError,
    _is_ripgrep_available
)

class TestDocRetrievalEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.docs_root = os.path.realpath(os.path.join(self.tmp_dir.name, "docs"))
        os.makedirs(self.docs_root, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_security_traversal_attack(self):
        """Test that path traversal attacks are blocked."""
        # Create a file outside docs_root
        secret_path = os.path.realpath(os.path.join(self.tmp_dir.name, "secret.txt"))
        with open(secret_path, "w") as f:
            f.write("sensitive data")
            
        # Try to resolve a path that escapes docs_root
        with self.assertRaises(DocAccessError):
            resolve_docs_root("../secret.txt", allow_roots=[self.docs_root])

    def test_encoding_resilience(self):
        """Test reading files with non-UTF8 encodings."""
        # Create a file with Latin-1 encoding
        latin_path = os.path.join(self.docs_root, "latin1.txt")
        with open(latin_path, "wb") as f:
            # "Héllo" in Latin-1
            f.write(b"H\xe9llo world")
            
        # Search for it - should not crash and should replace invalid chars if it fails UTF8
        hits = search_text("world", docs_root=self.docs_root, allowed_extensions=[".txt"])
        self.assertGreaterEqual(len(hits), 1)
        # errors="replace" should have handled the \xe9
        self.assertIn("llo world", hits[0].snippet)

    def test_hidden_files_and_dot_directories(self):
        """Test how hidden files or directories are handled."""
        dot_dir = os.path.join(self.docs_root, ".git")
        os.makedirs(dot_dir, exist_ok=True)
        hidden_file = os.path.join(dot_dir, "config")
        with open(hidden_file, "w") as f:
            f.write("git config data")
            
        # Ripgrep by default ignores hidden files/dirs
        hits = search_text("config", docs_root=self.docs_root)
        paths = [os.path.basename(h.path) for h in hits]
        self.assertNotIn("config", paths)

    def test_ripgrep_json_malformed_mock(self):
        """Test robustness if rg output is unexpected (via mock)."""
        from unittest.mock import patch, MagicMock
        
        # Mock subprocess.run to return malformed JSON
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout='{"type": "match", "data": "invalid"}', # Missing keys
                stderr=""
            )
            
            # Should not crash, should just return empty or handle gracefully
            # Note: search_text calls _search_with_ripgrep internally
            with patch("app.services.doc_retrieval._is_ripgrep_available", return_value=True):
                hits = search_text("test", docs_root=self.docs_root)
                # It should fallback to Python search if rg fails or returns nothing
                # Since we mocked it to return 1 line of bad JSON, rg hits will be 0.
                self.assertIsInstance(hits, list)

if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
import time
from unittest.mock import patch
from app.services.doc_retrieval import search_text, read_text_lines, inspect_doc

class TestSmartDocRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.docs_root = os.path.join(self.tmp_dir.name, "docs")
        os.makedirs(self.docs_root, exist_ok=True)
        
        # Create a sample markdown file with headers and content
        self.md_content = """# Title
Introduction content here.

## Section 1
This is section 1. It contains the word keyword1 multiple times.
keyword1 is very important.

## Section 2
This is section 2. It contains keyword2.
More text about keyword2 here.

# Footer
End of document.
"""
        self.md_path = os.path.join(self.docs_root, "test.md")
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(self.md_content)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_smart_snippets_multi_sampling(self):
        # Search for both keywords, should return snippets from both sections
        hits = search_text("keyword1 keyword2", docs_root=self.docs_root, limit=10)
        
        # We expect at least 2 snippets for the same file
        real_md_path = os.path.realpath(self.md_path)
        paths = [os.path.realpath(h.path) for h in hits]
        # Ripgrep might return them in different order or group them, 
        # but the core logic should still find both sections.
        self.assertGreaterEqual(paths.count(real_md_path), 2)
        
        snippets = [h.snippet for h in hits]
        self.assertTrue(any("keyword1" in s for s in snippets))
        self.assertTrue(any("keyword2" in s for s in snippets))

    def test_semantic_chunking_respects_headers(self):
        # Search for keyword1, snippet should ideally start from ## Section 1
        hits = search_text("keyword1", docs_root=self.docs_root, limit=1)
        self.assertEqual(len(hits), 1)
        
        snippet = hits[0].snippet
        self.assertTrue(snippet.startswith("## Section 1"))
        self.assertIn("keyword1", snippet)

    def test_ripgrep_vs_python_consistency(self):
        """Ensure Ripgrep returns results consistent with Python fallback."""
        # Force Python fallback by mocking _is_ripgrep_available to return False
        with patch("app.services.doc_retrieval._is_ripgrep_available", return_value=False):
            python_hits = search_text("keyword1", docs_root=self.docs_root, limit=10)
        
        # Use Ripgrep (if available)
        rg_hits = search_text("keyword1", docs_root=self.docs_root, limit=10)
        
        # Compare paths found
        python_paths = sorted([os.path.basename(h.path) for h in python_hits])
        rg_paths = sorted([os.path.basename(h.path) for h in rg_hits])
        
        self.assertEqual(python_paths, rg_paths)
        if python_hits and rg_hits:
            self.assertIn("keyword1", rg_hits[0].snippet)

    def test_performance_benchmark(self):
        """Benchmark Ripgrep vs Python on a larger dataset with larger files."""
        # Create 1000 files, some of them larger (around 100KB)
        print(f"\nPreparing 1000 files for benchmark...")
        for i in range(1000):
            p = os.path.join(self.docs_root, f"file_{i}.txt")
            if i % 50 == 0:
                # 100KB file
                content = "Some prefix data. " * 5000 + f"target_word match in file {i}. " + "suffix data. " * 100
                with open(p, "w") as f:
                    f.write(content)
            else:
                with open(p, "w") as f:
                    f.write(f"This is file {i}. junk data.")
        
        # Warm up
        search_text("target_word", docs_root=self.docs_root)

        # Benchmark Python
        with patch("app.services.doc_retrieval._is_ripgrep_available", return_value=False):
            start = time.time()
            for _ in range(2):
                search_text("target_word", docs_root=self.docs_root, limit=10)
            python_time = (time.time() - start) / 2
            
        # Benchmark Ripgrep
        start = time.time()
        for _ in range(2):
            search_text("target_word", docs_root=self.docs_root, limit=10)
        rg_time = (time.time() - start) / 2
        
        print(f"\nPerformance Benchmark (1000 files, mixed size):")
        print(f"Python fallback: {python_time:.4f}s")
        print(f"Ripgrep engine:  {rg_time:.4f}s")
        print(f"Speedup: {python_time/rg_time:.2f}x")
        
        # Even with 100 files, Ripgrep should be faster or comparable
        # In a real large codebase (1000+ files), the gap will be much larger.

    def test_dynamic_window_target_line(self):
        # Read centered around line 8 (Section 2 header)
        path, start, end, snippet = read_text_lines(
            "test.md", 
            docs_root=self.docs_root, 
            target_line=8, 
            max_lines=4
        )
        
        # Line 8 is "## Section 2"
        # max_lines=4, half=2. start_idx = 8-1-2 = 5. Lines 6, 7, 8, 9.
        self.assertIn("## Section 2", snippet)
        self.assertIn("keyword1", snippet) # Line 6 or 7 has it
        
    def test_search_empty_query(self):
        """Test searching with an empty query should return empty list."""
        hits = search_text("", docs_root=self.docs_root)
        self.assertEqual(len(hits), 0)

    def test_search_special_characters(self):
        """Test searching with regex-like special characters."""
        # Create a file with special chars
        special_path = os.path.join(self.docs_root, "special.md")
        with open(special_path, "w") as f:
            f.write("Find this: .* [a-z] + (group)")
            
        # Search for part of it
        hits = search_text(".* [a-z]", docs_root=self.docs_root)
        self.assertGreaterEqual(len(hits), 1)
        self.assertIn(".* [a-z]", hits[0].snippet)

    def test_max_file_size_enforcement(self):
        """Test that large files are skipped based on max_file_bytes."""
        large_path = os.path.join(self.docs_root, "large.md")
        with open(large_path, "w") as f:
            f.write("A" * 1024 * 10) # 10KB
            
        # Search with a very small max_file_bytes
        hits = search_text("A", docs_root=self.docs_root, max_file_bytes=1024)
        # Should not find the 10KB file
        paths = [h.path for h in hits]
        self.assertNotIn(os.path.realpath(large_path), [os.path.realpath(p) for p in paths])

    def test_invalid_docs_root(self):
        """Test that searching in a non-existent directory doesn't crash."""
        from app.services.doc_retrieval import DocAccessError
        with self.assertRaises(DocAccessError):
            search_text("test", docs_root="/non/existent/path/at/all")

    def test_inspect_doc(self):
        info = inspect_doc("test.md", docs_root=self.docs_root)
        self.assertEqual(info["line_count"], 13)
        self.assertEqual(len(info["headers"]), 4)
        self.assertEqual(info["headers"][0]["text"], "# Title")
        self.assertEqual(info["headers"][1]["text"], "## Section 1")

if __name__ == "__main__":
    unittest.main()

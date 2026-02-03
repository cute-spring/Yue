import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.doc_retrieval import DocAccessError, read_markdown_lines, resolve_docs_path, resolve_target_root, search_markdown


class TestDocRetrieval(unittest.TestCase):
    def test_resolve_target_root_allows_project_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = os.path.join(tmp, "Yue")
            os.makedirs(project_root, exist_ok=True)
            notes = os.path.join(project_root, "notes")
            os.makedirs(notes, exist_ok=True)
            resolved = resolve_target_root("notes", project_root=project_root)
            self.assertEqual(os.path.realpath(notes), resolved)

    def test_resolve_target_root_denies_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = os.path.join(tmp, "Yue")
            os.makedirs(project_root, exist_ok=True)
            with self.assertRaises(DocAccessError):
                resolve_target_root("../secrets", project_root=project_root)

    def test_resolve_target_root_allows_external_when_allowlisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = os.path.join(tmp, "Yue")
            os.makedirs(project_root, exist_ok=True)
            external = os.path.join(tmp, "opencode", "docs")
            os.makedirs(external, exist_ok=True)
            resolved = resolve_target_root(external, project_root=project_root, allow_roots=[external])
            self.assertEqual(os.path.realpath(external), resolved)

    def test_resolve_target_root_denies_external_without_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = os.path.join(tmp, "Yue")
            os.makedirs(project_root, exist_ok=True)
            external = os.path.join(tmp, "opencode", "docs")
            os.makedirs(external, exist_ok=True)
            with self.assertRaises(DocAccessError):
                resolve_target_root(external, project_root=project_root)

    def test_resolve_docs_path_denies_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            with self.assertRaises(DocAccessError):
                resolve_docs_path("../secrets.md", docs_root=docs_root)

    def test_read_markdown_requires_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "a.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("hello")
            with self.assertRaises(DocAccessError):
                read_markdown_lines("a.txt", docs_root=docs_root)

    def test_read_markdown_enforces_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "big.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("x" * 50)
            with self.assertRaises(DocAccessError):
                read_markdown_lines("big.md", docs_root=docs_root, max_bytes=10)

    def test_search_markdown_finds_by_filename_and_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)

            p1 = os.path.join(docs_root, "alpha.md")
            p2 = os.path.join(docs_root, "beta.md")
            with open(p1, "w", encoding="utf-8") as f:
                f.write("这里介绍 Obsidian 插件：CoPilot for Obsidian。\nSecond line.\n")
            with open(p2, "w", encoding="utf-8") as f:
                f.write("Nothing relevant here.\n")

            hits = search_markdown("Obsidian 热门插件", docs_root=docs_root, limit=10, timeout_s=5.0)
            self.assertTrue(any(h.path.endswith("alpha.md") for h in hits))

    def test_search_markdown_handles_bad_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "bad.md")
            with open(p, "wb") as f:
                f.write(b"\xff\xfe\xfd MCP")
            hits = search_markdown("mcp", docs_root=docs_root, limit=5, timeout_s=5.0)
            self.assertTrue(any(h.path.endswith("bad.md") for h in hits))


if __name__ == "__main__":
    unittest.main()

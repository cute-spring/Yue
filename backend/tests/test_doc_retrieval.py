import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.doc_retrieval import DocAccessError, read_markdown_lines, resolve_docs_path, search_markdown, resolve_docs_root, resolve_docs_roots_for_search, resolve_docs_root_for_read


class TestDocRetrieval(unittest.TestCase):
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

    def test_resolve_docs_root_allows_under_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            resolved = resolve_docs_root(docs_root, allow_roots=[tmp])
            self.assertTrue(resolved.startswith(os.path.realpath(tmp)))

    def test_resolve_docs_root_denies_outside_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            with self.assertRaises(DocAccessError):
                resolve_docs_root(docs_root, allow_roots=[os.path.join(tmp, "other")])

    def test_resolve_docs_root_denies_under_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            with self.assertRaises(DocAccessError):
                resolve_docs_root(docs_root, allow_roots=[tmp], deny_roots=[tmp])

    def test_resolve_docs_roots_for_search_prefers_doc_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root_a = os.path.join(tmp, "docs_a")
            docs_root_b = os.path.join(tmp, "docs_b")
            os.makedirs(docs_root_a, exist_ok=True)
            os.makedirs(docs_root_b, exist_ok=True)
            roots = resolve_docs_roots_for_search(
                None,
                doc_roots=[docs_root_a, docs_root_b],
                allow_roots=[tmp],
            )
            self.assertEqual(set(roots), {os.path.realpath(docs_root_a), os.path.realpath(docs_root_b)})

    def test_resolve_docs_root_for_read_matches_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root_a = os.path.join(tmp, "docs_a")
            docs_root_b = os.path.join(tmp, "docs_b")
            os.makedirs(docs_root_a, exist_ok=True)
            os.makedirs(docs_root_b, exist_ok=True)
            target = os.path.join(docs_root_b, "note.md")
            with open(target, "w", encoding="utf-8") as f:
                f.write("hi")
            root = resolve_docs_root_for_read(
                target,
                doc_roots=[docs_root_a, docs_root_b],
                allow_roots=[tmp],
            )
            self.assertEqual(root, os.path.realpath(docs_root_b))

    def test_resolve_docs_root_for_read_matches_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root_a = os.path.join(tmp, "docs_a")
            docs_root_b = os.path.join(tmp, "docs_b")
            os.makedirs(docs_root_a, exist_ok=True)
            os.makedirs(docs_root_b, exist_ok=True)
            target = os.path.join(docs_root_a, "readme.md")
            with open(target, "w", encoding="utf-8") as f:
                f.write("hi")
            root = resolve_docs_root_for_read(
                "readme.md",
                doc_roots=[docs_root_a, docs_root_b],
                allow_roots=[tmp],
            )
            self.assertEqual(root, os.path.realpath(docs_root_a))


if __name__ == "__main__":
    unittest.main()

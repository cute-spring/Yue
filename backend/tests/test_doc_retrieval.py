import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.doc_retrieval import (
    DocAccessError,
    TEXT_LIKE_EXTENSIONS,
    PDF_EXTENSIONS,
    read_markdown_lines,
    read_text_lines,
    read_pdf_pages,
    resolve_docs_path,
    search_markdown,
    search_text,
    search_pdf,
    resolve_docs_root,
    resolve_docs_roots_for_search,
    resolve_docs_root_for_read,
)


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

    def test_read_text_allows_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "a.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("hello\nworld\n")
            abs_path, start, end, snippet = read_text_lines(
                "a.txt",
                docs_root=docs_root,
                allowed_extensions=TEXT_LIKE_EXTENSIONS,
                start_line=1,
                max_lines=10,
            )
            self.assertTrue(abs_path.endswith("a.txt"))
            self.assertEqual((start, end), (1, 2))
            self.assertIn("hello", snippet)

    def test_read_text_denies_disallowed_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "a.exe")
            with open(p, "w", encoding="utf-8") as f:
                f.write("hello")
            with self.assertRaises(DocAccessError):
                read_text_lines("a.exe", docs_root=docs_root, allowed_extensions=TEXT_LIKE_EXTENSIONS)

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

    def test_search_text_finds_txt_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)

            p1 = os.path.join(docs_root, "alpha.txt")
            p2 = os.path.join(docs_root, "beta.md")
            with open(p1, "w", encoding="utf-8") as f:
                f.write("hello mcp world\n")
            with open(p2, "w", encoding="utf-8") as f:
                f.write("mcp in markdown\n")

            hits = search_text(
                "mcp",
                docs_root=docs_root,
                allowed_extensions=TEXT_LIKE_EXTENSIONS,
                limit=10,
                timeout_s=5.0,
            )
            paths = [h.path for h in hits]
            self.assertTrue(any(p.endswith("alpha.txt") for p in paths))
            self.assertTrue(any(p.endswith("beta.md") for p in paths))
            self.assertTrue(all(isinstance(h.start_line, int) and isinstance(h.end_line, int) for h in hits))

    def test_search_text_respects_file_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(os.path.join(docs_root, "a"), exist_ok=True)
            os.makedirs(os.path.join(docs_root, "b"), exist_ok=True)
            with open(os.path.join(docs_root, "a", "note.md"), "w", encoding="utf-8") as f:
                f.write("mcp here\n")
            with open(os.path.join(docs_root, "b", "note.txt"), "w", encoding="utf-8") as f:
                f.write("mcp here too\n")

            hits = search_text(
                "mcp",
                docs_root=docs_root,
                allowed_extensions=TEXT_LIKE_EXTENSIONS,
                file_patterns=["**/*.txt"],
                limit=10,
                timeout_s=5.0,
            )
            self.assertTrue(all(h.path.endswith(".txt") for h in hits))

    def test_read_text_denies_by_file_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            with open(os.path.join(docs_root, "a.txt"), "w", encoding="utf-8") as f:
                f.write("hello")
            with self.assertRaises(DocAccessError):
                read_text_lines(
                    "a.txt",
                    docs_root=docs_root,
                    allowed_extensions=TEXT_LIKE_EXTENSIONS,
                    file_patterns=["**/*.md"],
                )

    def test_search_markdown_handles_bad_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "bad.md")
            with open(p, "wb") as f:
                f.write(b"\xff\xfe\xfd MCP")
            hits = search_markdown("mcp", docs_root=docs_root, limit=5, timeout_s=5.0)
            self.assertTrue(any(h.path.endswith("bad.md") for h in hits))

    def test_resolve_docs_path_allows_extension_allowlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = resolve_docs_path("a.txt", docs_root=docs_root, allowed_extensions=[".txt"])
            self.assertTrue(p.endswith("a.txt"))

    def test_read_pdf_pages_handles_blank_pdf(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "a.pdf")
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with open(p, "wb") as f:
                writer.write(f)

            abs_path, start, end, snippet = read_pdf_pages(
                "a.pdf",
                docs_root=docs_root,
                start_page=1,
                max_pages=2,
                timeout_s=5.0,
            )
            self.assertTrue(abs_path.endswith("a.pdf"))
            self.assertEqual(start, 1)
            self.assertGreaterEqual(end, 1)
            self.assertIsInstance(snippet, str)

    def test_search_pdf_handles_blank_pdf(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "a.pdf")
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            with open(p, "wb") as f:
                writer.write(f)
            hits = search_pdf("mcp", docs_root=docs_root, limit=5, timeout_s=5.0)
            self.assertIsInstance(hits, list)

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

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

    def test_get_project_root(self):
        from app.services.doc_retrieval import get_project_root
        root = get_project_root()
        self.assertTrue(os.path.isdir(root))

    def test_get_docs_root(self):
        from app.services.doc_retrieval import get_docs_root
        root = get_docs_root()
        self.assertIn("docs", root)

    def test_is_under_value_error(self):
        from app.services.doc_retrieval import _is_under
        # On some systems, commonpath raises ValueError if paths are on different drives
        with unittest.mock.patch("os.path.commonpath", side_effect=ValueError):
            self.assertFalse(_is_under("/a", "/b"))

    def test_resolve_docs_root_non_abs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch("app.services.doc_retrieval.get_project_root", return_value=tmp):
                os.makedirs(os.path.join(tmp, "relative"), exist_ok=True)
                root = resolve_docs_root("relative", allow_roots=[tmp])
                self.assertEqual(root, os.path.realpath(os.path.join(tmp, "relative")))

    def test_resolve_docs_roots_for_search_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Test empty string in doc_roots
            roots = resolve_docs_roots_for_search(None, doc_roots=["", " "], allow_roots=[tmp])
            self.assertEqual(len(roots), 1) # Fallback to default
            
            # Test DocAccessError during resolution
            # We want to fail for "/invalid" but succeed for the fallback (None)
            def side_effect(root, **kwargs):
                if root == "/invalid": raise DocAccessError("invalid")
                return "/mocked-root"
                
            with unittest.mock.patch("app.services.doc_retrieval.resolve_docs_root", side_effect=side_effect):
                roots = resolve_docs_roots_for_search(None, doc_roots=["/invalid"], allow_roots=[tmp])
                self.assertEqual(roots, ["/mocked-root"])

    def test_resolve_docs_root_for_read_misc(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            # requested_root
            root = resolve_docs_root_for_read("a.md", requested_root=docs_root, allow_roots=[tmp])
            self.assertEqual(root, os.path.realpath(docs_root))
            
            # Absolute path outside
            with self.assertRaises(DocAccessError):
                resolve_docs_root_for_read("/tmp/outside.md", allow_roots=[docs_root])

    def test_resolve_docs_path_absolute(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            target = os.path.join(docs_root, "a.md")
            with open(target, "w") as f: f.write("hi")
            path = resolve_docs_path(target, docs_root=docs_root)
            self.assertEqual(path, os.path.realpath(target))

    def test_resolve_docs_path_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            # Empty list
            with self.assertRaises(DocAccessError):
                resolve_docs_path("a.txt", docs_root=docs_root, allowed_extensions=[])
            # Invalid type
            path = resolve_docs_path("a.txt", docs_root=docs_root, allowed_extensions=[".TXT", None, " "])
            self.assertTrue(path.endswith("a.txt"))
            # No dot
            path = resolve_docs_path("a.txt", docs_root=docs_root, allowed_extensions=["txt"])
            self.assertTrue(path.endswith("a.txt"))

    def test_normalize_file_patterns(self):
        from app.services.doc_retrieval import _normalize_file_patterns
        inc, exc = _normalize_file_patterns(["*.md", "!temp/", "# comment", "", None])
        self.assertEqual(inc, ["*.md"])
        self.assertEqual(exc, ["temp/"])

    def test_matches_file_patterns_relpath_error(self):
        from app.services.doc_retrieval import _matches_file_patterns
        with unittest.mock.patch("os.path.relpath", side_effect=Exception):
            self.assertFalse(_matches_file_patterns("/root", "/path", ["*"]))

    def test_read_text_lines_validation(self):
        with self.assertRaises(DocAccessError):
            read_text_lines("a.txt", start_line=0)
        with self.assertRaises(DocAccessError):
            read_text_lines("a.txt", max_lines=0)

    def test_read_pdf_pages_validation(self):
        from app.services.doc_retrieval import _read_pdf_pages_text
        with self.assertRaises(DocAccessError):
            _read_pdf_pages_text("a.pdf", start_page=0, max_pages=1, max_bytes=100, timeout_s=1)
        with self.assertRaises(DocAccessError):
            _read_pdf_pages_text("a.pdf", start_page=1, max_pages=0, max_bytes=100, timeout_s=1)

    def test_read_pdf_pages_too_large(self):
        from app.services.doc_retrieval import _read_pdf_pages_text
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "large.pdf")
            with open(p, "wb") as f: f.write(b"x" * 100)
            with self.assertRaises(DocAccessError):
                # max_bytes = 10
                _read_pdf_pages_text(p, start_page=1, max_pages=1, max_bytes=10, timeout_s=1)

    def test_tokenize_query_edge_cases(self):
        from app.services.doc_retrieval import _tokenize_query
        self.assertEqual(_tokenize_query(None), [])
        self.assertEqual(_tokenize_query(""), [])
        self.assertEqual(_tokenize_query("a"), []) # too short
        # Chinese tokens
        self.assertIn("测试", _tokenize_query("测试查询"))

    def test_search_text_edge_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            # Empty query
            self.assertEqual(search_text("", docs_root=docs_root), [])
            # No tokens (all too short)
            self.assertEqual(search_text("a b", docs_root=docs_root), [])
            
            # Large file skip
            p = os.path.join(docs_root, "large.txt")
            with open(p, "w") as f: f.write("search_term" * 1000)
            hits = search_text("search_term", docs_root=docs_root, max_file_bytes=10)
            self.assertEqual(hits, [])

    def test_search_pdf_with_content(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as tmp:
            docs_root = os.path.join(tmp, "docs")
            os.makedirs(docs_root, exist_ok=True)
            p = os.path.join(docs_root, "test.pdf")
            writer = PdfWriter()
            page = writer.add_blank_page(width=612, height=792)
            # Note: adding text to PDF is tricky without more libs, 
            # but we can mock the extract_text
            with open(p, "wb") as f: writer.write(f)
            
            with unittest.mock.patch("pypdf.PageObject.extract_text", return_value="This is a test PDF with content"):
                hits = search_pdf("test", docs_root=docs_root)
                self.assertTrue(any(h.path.endswith("test.pdf") for h in hits))


    def test_resolve_docs_root_requested_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            allow = [tmp]
            res = resolve_docs_root(tmp, allow_roots=allow)
            self.assertEqual(res, os.path.realpath(tmp))

    def test_resolve_docs_roots_for_search_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            allow = [tmp]
            res = resolve_docs_roots_for_search(tmp, allow_roots=allow)
            self.assertEqual(res, [os.path.realpath(tmp)])

    def test_resolve_docs_root_for_read_abs_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            file_path = os.path.join(root, "test.md")
            with open(file_path, "w") as f: f.write("test")
            res = resolve_docs_root_for_read(file_path, doc_roots=[root], allow_roots=[root])
            self.assertEqual(res, root)

    def test_resolve_docs_root_for_read_invalid_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            with self.assertRaises(DocAccessError):
                resolve_docs_root_for_read("/tmp/outside", doc_roots=[root], allow_roots=[root])

    def test_resolve_docs_path_no_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            file_path = os.path.join(root, "test.txt")
            with open(file_path, "w") as f: f.write("test")
            with self.assertRaises(DocAccessError):
                resolve_docs_path("test.txt", docs_root=root, require_md=True)

    def test_matches_one_pattern_edge_cases(self):
        from app.services.doc_retrieval import _matches_one_pattern
        self.assertFalse(_matches_one_pattern("a/b.md", ""))
        self.assertFalse(_matches_one_pattern("a/b.md", None))
        self.assertTrue(_matches_one_pattern("a/b.md", "b.md"))
        self.assertFalse(_matches_one_pattern("a/b.md", "c.md"))

    def test_matches_file_patterns_edge_cases(self):
        from app.services.doc_retrieval import _matches_file_patterns
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            self.assertFalse(_matches_file_patterns(root, os.path.join(root, "a.md"), ["!a.md"]))
            self.assertTrue(_matches_file_patterns(root, os.path.join(root, "a.md"), ["!b.md"]))

    def test_iter_files_edge_cases(self):
        from app.services.doc_retrieval import iter_files
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            os.makedirs(os.path.join(root, "subdir"))
            with open(os.path.join(root, "a.md"), "w") as f: f.write("a")
            with open(os.path.join(root, "subdir", "b.md"), "w") as f: f.write("b")
            files = list(iter_files(docs_root=root, allowed_extensions=["md", "", None, 123]))
            self.assertEqual(len(files), 2)
            files = list(iter_files(docs_root=root, max_files=1))
            self.assertEqual(len(files), 1)

    def test_iter_markdown_files(self):
        from app.services.doc_retrieval import iter_markdown_files
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            with open(os.path.join(root, "a.md"), "w") as f: f.write("a")
            files = list(iter_markdown_files(docs_root=root))
            self.assertEqual(len(files), 1)

    def test_make_snippet_negative_idx(self):
        from app.services.doc_retrieval import _make_snippet
        self.assertEqual(_make_snippet("hello world", 5, window=2), "lo w")
        self.assertEqual(_make_snippet("hello world", -1), "")

    def test_make_line_snippet_empty(self):
        from app.services.doc_retrieval import _make_line_snippet
        self.assertEqual(_make_line_snippet("", 0), ("", 1, 1))
        snippet, start, end = _make_line_snippet("a\nb\nc", -1, max_lines=2)
        self.assertEqual(snippet, "a\nb")
        self.assertEqual(start, 1)
        self.assertEqual(end, 2)

    def test_tokenize_query_seen_and_groups(self):
        from app.services.doc_retrieval import _tokenize_query
        tokens = _tokenize_query("abc abc def g")
        self.assertIn("abc", tokens)
        self.assertIn("def", tokens)
        self.assertNotIn("g", tokens)

    def test_search_text_timeout_and_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            with open(os.path.join(root, "a.md"), "w") as f: f.write("hello world")
            with unittest.mock.patch("time.time", side_effect=[0, 100, 101, 102, 103, 104]):
                hits = search_text("hello", docs_root=root, timeout_s=1.0)
                self.assertEqual(len(hits), 0)
            hits = search_text("hello", docs_root=root, max_total_bytes_scanned=1)
            self.assertEqual(len(hits), 0)

    def test_search_pdf_edge_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            pdf_path = os.path.join(root, "test.pdf")
            with open(pdf_path, "w") as f: f.write("fake pdf content")
            self.assertEqual(search_pdf("", docs_root=root), [])
            self.assertEqual(search_pdf(" ", docs_root=root), [])
            with unittest.mock.patch("pypdf.PdfReader") as mock_reader_cls:
                mock_reader = unittest.mock.MagicMock()
                mock_reader_cls.return_value = mock_reader
                mock_reader.pages = []
                hits = search_pdf("test", docs_root=root)
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0].snippet, "")
                with unittest.mock.patch("time.time", side_effect=[0, 100, 101, 102, 103]):
                    hits = search_pdf("test", docs_root=root, timeout_s=1.0)
                    self.assertEqual(len(hits), 0)

    def test_search_text_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.realpath(tmp)
            with open(os.path.join(root, "a.md"), "w") as f: f.write("hello")
            with unittest.mock.patch("app.services.doc_retrieval._read_text_file", side_effect=Exception("oops")):
                hits = search_text("hello", docs_root=root)
                self.assertEqual(len(hits), 0)

if __name__ == "__main__":
    unittest.main()

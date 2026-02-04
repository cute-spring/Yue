import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.doc_retrieval import search_markdown


class TestDocRetrievalQuality(unittest.TestCase):
    def test_golden_query_obsidian_ranks_alpha_first(self):
        docs_root = os.path.join(os.path.dirname(__file__), "fixtures", "doc_agent")
        hits = search_markdown("Obsidian 插件", docs_root=docs_root, limit=3, timeout_s=5.0)
        self.assertTrue(hits)
        self.assertTrue(hits[0].path.endswith("alpha.md"))
        self.assertIsInstance(hits[0].locator, (str, type(None)))
        if hits[0].locator:
            self.assertTrue(hits[0].locator.startswith("L"))
        self.assertIsInstance(hits[0].reason, (dict, type(None)))

    def test_golden_query_mcp_ranks_beta_first(self):
        docs_root = os.path.join(os.path.dirname(__file__), "fixtures", "doc_agent")
        hits = search_markdown("MCP", docs_root=docs_root, limit=3, timeout_s=5.0)
        self.assertTrue(hits)
        self.assertTrue(hits[0].path.endswith("beta.md"))


if __name__ == "__main__":
    unittest.main()


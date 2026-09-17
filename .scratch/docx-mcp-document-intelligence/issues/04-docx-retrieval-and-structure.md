# 04: Add DOCX search, query, structure, and citations

**What to build:** An LLM can locate document content precisely with `docx_search`, request structure-aware results with `docx_query`, and understand hierarchy through `docx_structure`. Each result cites a stable block, table cell, or section location and explains applied filters/ranking.

**Non-goals:** Arbitrary SQL execution, semantic vector indexing, page-layout rendering, source mutation, or review-layer extraction.

**Blocked by:** 02: Deliver the DOCX reader MVP.

**Status:** completed

**Affected backend areas:** DOCX retrieval/index adapter; DOCX service and locator models; built-in MCP DOCX tools; citation collection; agent guidance.

**Tests:** Exact phrase/keyword/regex search tests; structured filter/query tests; heading/table-cell citation tests; result-limit and deterministic ordering tests.

- [x] `docx_search` searches chosen domains of body text, headings, and table cells and returns matched snippets with block/table-cell citations.
- [x] `docx_query` accepts only a constrained document-query grammar, reports applied filters, and cannot execute arbitrary code or SQL.
- [x] `docx_structure` exposes heading hierarchy, section boundaries, list nesting, block ranges, table locations, bookmarks, and header/footer presence.
- [x] Retrieval output is stable for a fixed source and explicitly reports result limits or truncation.

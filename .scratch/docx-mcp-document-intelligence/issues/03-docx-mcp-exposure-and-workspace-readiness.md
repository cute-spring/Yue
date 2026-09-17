# 03: Expose reader tools to agents and DOCX workspace sources

**What to build:** Once the reader MVP is available, Yue's built-in tool catalog and workspace-source readiness report DOCX capabilities accurately, letting agents discover and invoke the new read tools for uploaded and local DOCX sources.

**Non-goals:** Implementing new parsing behavior, indexing a document, changing Excel/PDF behavior, or enabling write tools.

**Blocked by:** 02: Deliver the DOCX reader MVP.

**Status:** ready-for-agent

**Affected backend areas:** Built-in tool registration/catalog; workspace source readiness; agent/tool discovery guidance; source metadata and citations.

**Tests:** Tool registry tests; workspace source readiness tests for DOCX uploads/local sources; regression tests for existing XLSX, PDF, Markdown, and text source capability lists.

- [ ] Built-in MCP discovery exposes the three reader MVP tool names and descriptions to enabled agents.
- [ ] A ready `.docx` workspace source advertises only the delivered DOCX reader capabilities and remains citation-capable.
- [ ] Unsupported, absent, or failed DOCX sources do not claim reader readiness.
- [ ] Existing workspace capability mappings remain unchanged for non-DOCX files.

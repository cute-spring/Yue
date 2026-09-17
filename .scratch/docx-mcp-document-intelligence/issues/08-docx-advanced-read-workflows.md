# 08: Add document comparison and conversion workflows

**What to build:** An LLM can compare two DOCX documents structurally and semantically with `docx_compare`, and can export selected document content through `docx_convert` with explicit format and fidelity reporting.

**Non-goals:** Mutating either comparison input, claiming layout preservation in lossy formats, bulk migration of document libraries, or write-tool support.

**Blocked by:** 04: Add DOCX search, query, structure, and citations; 05: Add DOCX rendering and focused metadata inspection.

**Status:** ready-for-agent

**Affected backend areas:** DOCX comparison service; conversion/export adapter; built-in MCP DOCX tools; render/fidelity reporting; artifact delivery.

**Tests:** Paired-document diff fixtures covering paragraphs, tables, metadata, styles, media, and comments; conversion fixtures for Markdown/HTML/text/JSON/PDF; fidelity-warning and output-limit tests.

- [ ] `docx_compare` reports added, removed, and changed paragraphs, headings, tables, metadata, media, comments, and style summaries with citations to both sources.
- [ ] `docx_convert` supports the approved output formats for a full document or stable block range and returns a new artifact rather than changing the source.
- [ ] Every conversion response identifies known fidelity loss and the selected content scope.
- [ ] Comparisons and conversions observe source-root access policy and bounded output/artifact limits.

# 02: Deliver the DOCX reader MVP

**What to build:** An LLM can call `docx_profile`, `docx_read`, and `docx_extract_tables` to understand a document and read its ordered body content or individual tables. Responses are bounded, cite stable locations, and follow existing Excel MCP error, auditing, access-control, and read-only conventions.

**Non-goals:** Keyword/semantic retrieval, rendering, comments, tracked changes, metadata-only reads, writing, and macro analysis.

**Blocked by:** 01: Establish DOCX service foundation.

**Status:** completed

**Affected backend areas:** Built-in MCP DOCX tool module and registry; DOCX service; config/document access integration; MCP tool catalog; audit logging.

**Tests:** Built-in tool contract tests; DOCX profile/read/table extraction service tests; access-policy and output-truncation tests.

- [x] `docx_profile` returns document overview data including basic metadata, section/heading/table counts, and feature/fidelity summary.
- [x] `docx_read` returns ordered paragraph, heading, list, and table blocks using cursor/limit pagination, JSON/Markdown modes, stable locators, and explicit truncation state.
- [x] `docx_extract_tables` selects tables by ordinal or stable ID and returns structured cells, merged-cell information where available, nearby heading context, and citations.
- [x] Every tool returns a predictable success/failure envelope, observes roots immediately, creates audit records, and does not mutate the source.

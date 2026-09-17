# 01: Establish DOCX service foundation

**What to build:** A safe, read-only DOCX package foundation that resolves allowed file paths, opens `.docx` packages without executing active content, emits a document-order block stream, and assigns stable locators to paragraphs, headings, lists, and tables. It includes a focused fixture corpus so all later DOCX MCP tools work against the same contract.

**Non-goals:** No MCP tool exposure, workspace registration, rendering, semantic retrieval, document mutation, or support for legacy `.doc` files.

**Blocked by:** None (can start immediately).

**Status:** completed

**Affected backend areas:** DOCX service and models; shared document access adapter; OOXML fixture utilities.

**Tests:** DOCX service unit tests and fixtures covering headings, lists, basic/merged tables, non-ASCII text, unsupported constructs, malformed packages, denied roots, and ambiguous relative paths.

- [x] Resolving a DOCX path follows Yue's configured allow/deny roots and returns the same structured access failures as existing document and Excel tools.
- [x] A valid DOCX produces ordered, stable block IDs and locators without executing macros, external content, or embedded binaries.
- [x] Fixture tests demonstrate deterministic results for representative paragraphs, headings, lists, tables, and non-ASCII text.
- [x] Malformed or unsupported packages report a structured failure or fidelity warning rather than leaking parser exceptions.

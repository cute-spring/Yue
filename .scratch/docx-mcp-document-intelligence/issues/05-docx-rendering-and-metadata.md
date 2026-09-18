# 05: Add DOCX rendering and focused metadata inspection

**What to build:** An LLM can inspect document properties with `docx_metadata` and request visual verification through `docx_render`, receiving page artifacts plus clear rendering provenance and best-effort page-to-source mappings.

**Non-goals:** Editing layout, claiming Microsoft Word pixel equivalence, extracting comments/changes, or converting documents to other formats.

**Blocked by:** 02: Deliver the DOCX reader MVP.

**Status:** completed

**Affected backend areas:** DOCX metadata reader; document rendering adapter/artifact delivery; built-in MCP DOCX tools; artifact/citation plumbing.

**Tests:** Core/custom metadata tests; render smoke tests for requested page ranges; provenance/failure tests when renderer support is unavailable; visual/golden checks for representative layout fixtures.

- [x] `docx_metadata` returns core/custom properties, template/application fields where present, language, revision values, and protection state without a full content read.
- [x] `docx_render` returns requested pages as artifacts and identifies the rendering backend/version used.
- [x] Render requests have bounded page/range limits and fail with an actionable structured error when rendering cannot be completed.
- [x] Tests verify that page-level assertions are never emitted without rendering provenance.

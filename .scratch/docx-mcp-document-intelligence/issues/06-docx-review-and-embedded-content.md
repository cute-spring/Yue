# 06: Expose review layers and embedded document content

**What to build:** An LLM can inspect comments, tracked changes, footnotes/endnotes, images/charts/embedded files, hyperlinks, bookmarks, and cross-references using precise anchors and opt-in response scopes.

**Non-goals:** Resolving comments, accepting/rejecting tracked changes, downloading linked content, editing embedded objects, or modifying the document.

**Blocked by:** 02: Deliver the DOCX reader MVP.

**Status:** completed

**Affected backend areas:** DOCX review/media/relationship parsers; built-in MCP DOCX tools; locator/citation models; artifact extraction boundary.

**Tests:** Comment-thread and change-markup fixtures; footnote/endnote anchor tests; media/link inventory tests; opt-in inclusion and token-bound tests; external-link non-following tests.

- [ ] `docx_comments`, `docx_changes`, and `docx_notes` return review/annotation content with author/time metadata where present and source anchors.
- [ ] `docx_media` inventories media and embedded files with type, alt text/caption/dimensions where present, and anchor locations; extraction remains explicit.
- [ ] `docx_links` distinguishes external links from internal anchors, bookmarks, and cross-references without following destinations.
- [ ] `docx_read` includes review/annotation layers only when the caller explicitly requests them.

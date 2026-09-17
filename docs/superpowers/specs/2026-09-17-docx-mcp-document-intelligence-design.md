# DOCX MCP Document Intelligence

**Status:** Proposed
**Date:** 2026-09-17
**Scope:** Add first-class, read-only DOCX intelligence to Yue's built-in MCP tools, followed by an explicitly separated, opt-in write surface.

## 1. Problem

Yue discovers `.docx` files and can generate DOCX exports, but it cannot expose a DOCX file's content or structure to an LLM through MCP. The current `docs_read`, `docs_search`, and `docs_inspect` tools accept text-like files only. In contrast, spreadsheet files have an established built-in MCP surface for profiling, reading, querying, logic extraction, and safety scanning.

The result is a gap: the LLM cannot reliably answer questions about the content, structure, review state, metadata, or visual fidelity of a Word document, and it cannot safely propose or apply document edits with durable source references.

## 2. Goals

- Make DOCX a first-class document source for Yue's LLM.
- Preserve document order and provide stable, precise citations for every extracted item.
- Support both exact search and structure-aware retrieval across prose and tables.
- Surface high-value Word constructs: headings, sections, lists, tables, media, links, comments, notes, tracked changes, and metadata.
- Match existing Excel conventions for access control, JSON envelopes, audit logging, truncation, and read-only defaults.
- Detect unsafe or unsupported package features without executing document code.
- Keep mutation capabilities separate from reading and require an explicit output artifact.

## 3. Non-goals

- Pixel-perfect recreation of Microsoft Word's layout engine.
- Executing VBA, macros, ActiveX, embedded binaries, external templates, or linked content.
- Silently overwriting the source document.
- Treating a Word document as a flat spreadsheet or forcing SQL over prose.
- Guaranteeing a rendered page number without rendering the document.

## 4. Design principles

### Stable document locations

Every visible or retrievable document item has a durable locator. A locator contains a `block_id`, content kind, hierarchy path, and source coordinates. Tables additionally expose a table ID and row/cell coordinates; media and comments expose their anchors.

Example citation:

```json
{
  "file": "docs/brief.docx",
  "block_id": "p-0042",
  "kind": "paragraph",
  "section": 2,
  "heading_path": ["Product strategy", "Risks"],
  "locator": "section:2/heading:Product strategy > Risks/block:p-0042"
}
```

### Content is ordered, structure is additive

`docx_read` returns the document's body as an ordered stream. A heading, paragraph, list item, table, image, or break is a block. `docx_structure` enriches that stream with hierarchy rather than presenting a competing interpretation.

### Retrieval is document-native

Exact search, filtering, and ranked retrieval operate over document blocks and their fields. Query behavior is a constrained document query language, not Excel's SQL interface. Search results always include a source locator.

### Safe and explainable defaults

All initial tools are read-only. Large responses are bounded and report truncation. Security-sensitive content is not opened or executed; it is reported by static inspection. Unsupported OOXML features are returned as fidelity warnings, never silently discarded.

## 5. Common MCP contract

All tools:

- accept `path` and optional `root_dir`;
- use the same global allow/deny-root authority as existing docs and Excel tools;
- return `ok`, `tool`, `file`, and a predictable `error_code`/`message`/`hint` on failure;
- emit audit events with duration, status, and bounded non-sensitive summary fields;
- enforce response limits and return `is_truncated`, `next_cursor`, or an equivalent narrowing hint;
- preserve source locations in structured output;
- never execute active document content.

The format support baseline is `.docx`. `.docm` may be profiled and statically scanned but must never execute macros. Other Word formats are out of scope until they receive separate compatibility tests.

## 6. Read and intelligence tools

### 6.1 `docx_profile`

**Purpose:** Establish an inexpensive overview before a deeper read.

Returns core and custom metadata, detected language, estimated word/page counts, section count, heading outline summary, counts for paragraphs/tables/images/comments/notes/links/tracked changes, document protection state, package relationships, and a fidelity/capability summary.

The response directs the LLM to suitable next tools, analogous to `excel_profile`.

### 6.2 `docx_read`

**Purpose:** Read ordered document content in bounded slices.

Supports:

- `cursor`/`limit` pagination;
- `block_ids` for direct retrieval;
- filters by section, heading path, style, and content kind;
- optional inclusion of headers, footers, hidden text, comments, notes, and tracked changes;
- JSON and Markdown output modes.

Each returned block carries content, style/level when relevant, and a stable locator. Tables are represented structurally rather than flattened into prose.

### 6.3 `docx_search`

**Purpose:** Perform exact keyword, phrase, and optionally regex search with useful snippets.

The tool searches selected content domains: body text, headings, table cells, comments, notes, links, and change markup. It returns match spans, snippets, score, and block/table-cell citations. It is the fast, high-precision retrieval path.

### 6.4 `docx_query`

**Purpose:** Perform constrained, structure-aware retrieval when an exact search is insufficient.

The query model supports filters such as `kind`, `heading_path`, `style`, `section`, `table_id`, `author`, `changed_after`, and `has_comment`, together with text matching and ranking. It must not execute arbitrary code or SQL. The response includes the applied filters and ranked source blocks.

Semantic retrieval may be added behind an explicit mode once Yue has an approved indexing and evaluation strategy; exact, deterministic retrieval remains available in all deployments.

### 6.5 `docx_structure`

**Purpose:** Explain the document's organization.

Returns heading hierarchy, sections, list nesting, block ranges, table locations, bookmarks, headers/footers, page-layout settings, and relationships among anchors. This is the primary tool for questions such as “what are the sections?” and for selecting a safe target for a subsequent read or edit.

### 6.6 `docx_extract_tables`

**Purpose:** Extract tables accurately and independently of prose.

Supports selecting by table ID, heading, or ordinal. It returns cell values, row/column dimensions where available, merged-cell ranges, nearby caption/heading context, and precise source coordinates. Output modes are JSON, Markdown, and CSV-ready rows.

### 6.7 `docx_render`

**Purpose:** Verify layout-sensitive content visually.

Renders a requested page range or the whole document to page images or PDF, reports the rendering backend/version, and returns page-to-source mappings where feasible. It is required before asserting page-level placement or the visual result of a mutation.

### 6.8 `docx_metadata`

**Purpose:** Read document properties without loading the entire content stream.

Returns core/custom properties, template, application/version fields, creation/modification/revision values, language, protection state, and package-level relationships. Metadata is also included in `docx_profile`; this focused tool exists for workflows that need only metadata.

### 6.9 `docx_comments`, `docx_changes`, and `docx_notes`

**Purpose:** Expose review and annotation layers separately and precisely.

- `docx_comments` returns comment threads, authors, timestamps, replies, status when available, and anchored text.
- `docx_changes` returns tracked insertions, deletions, formatting changes, author/time metadata, and selectable `final`, `original`, or `markup` views.
- `docx_notes` returns footnotes and endnotes with their source anchors.

All three support filtering and citations and are opt-in in `docx_read` to avoid accidental token expansion.

### 6.10 `docx_media` and `docx_links`

**Purpose:** Make non-text document content inspectable.

`docx_media` inventories images, charts, diagrams, and embedded files with alt text, captions, dimensions, media type, and anchors; extraction is explicit. `docx_links` returns external hyperlinks, internal anchors, bookmarks, cross-references, citations, and package relationships.

### 6.11 `docx_security_scan`

**Purpose:** Statically identify risky DOCX/DOCM package features before deeper processing.

The scan reports macros, ActiveX/OLE objects, embedded binaries, external relationships/templates, suspicious URLs, document protection, encrypted content, and malformed package relationships. It assigns a transparent risk level with contributing findings and recommends a safe next action. It never executes or follows active content.

### 6.12 `docx_validate`

**Purpose:** Identify integrity and fidelity risks.

The tool validates ZIP/OOXML structure, required relationships, missing media, broken internal anchors, malformed XML, and unsupported constructs. The result distinguishes invalid files from valid files with lossy/unsupported features.

### 6.13 `docx_compare` and `docx_convert`

**Purpose:** Provide high-leverage document workflows once the read foundation is stable.

`docx_compare` produces semantic and structural differences for two documents: blocks, tables, media, metadata, comments, and styles. `docx_convert` exports a selected document or block range to Markdown, HTML, plain text, JSON, PDF, or extracted media, reporting known fidelity loss.

## 7. Optional write surface

Writing is deliberately a separate phase and separate permission boundary. It operates only after the read tools and source locators are stable.

| Tool | Responsibility |
| --- | --- |
| `docx_create` | Create a new document from structured input or approved templates. |
| `docx_patch` | Apply declarative edits against stable block/table IDs: text replacement, insertion, deletion, table changes, and block movement. |
| `docx_review_patch` | Add review comments or tracked changes instead of silently applying edits. |
| `docx_apply_style` | Normalize styles, headings, numbering, tables, headers/footers, and accessibility alt text. |
| `docx_redact` | Remove/mask selected content and scrub comments, metadata, tracked changes, hidden text, and specified package properties. |
| `docx_save` | Write a new named output artifact with provenance; source overwrite is never the default. |

Every mutation response reports the target locators, a change summary, fidelity warnings, and the output artifact. Layout-sensitive edits should be paired with `docx_render` verification.

## 8. Delivery stages

### Stage 1 — Reader MVP

Deliver `docx_profile`, `docx_read`, and `docx_extract_tables` for `.docx`, with stable ordered blocks, basic heading/list/table handling, pagination, root access enforcement, audit logging, error envelopes, and fixture-based tests.

### Stage 2 — Retrieval and structure parity

Deliver `docx_search`, `docx_query`, `docx_structure`, `docx_metadata`, `docx_render`, and workspace-source registration. Results gain durable citations and table-cell anchors. Add performance and truncation tests on large documents.

### Stage 3 — Full document intelligence

Deliver comments, changes, notes, media, links, security scanning, validation, comparison, and conversion. Add representative OOXML fixtures for each feature, malformed files, and protection/relationship edge cases.

### Stage 4 — Controlled authoring

Deliver the separate write surface, starting with create/patch/review-patch and ending with style/redaction/save. Each write operation creates a new artifact and has render-based regression checks where layout is relevant.

## 9. Integration points

- Register all tools under `backend/app/mcp/builtin/` beside the Excel tools.
- Introduce a focused DOCX service behind the tool layer; do not overload text-only `doc_retrieval` with OOXML parsing.
- Reuse global document access resolution and request audit conventions.
- Extend workspace source readiness so `.docx` exposes the delivered DOCX tools, just as `.xlsx` exposes its Excel tools.
- Update LLM guidance: profile first, search/read second, and explicitly opt into expensive or sensitive layers such as changes, comments, hidden text, and media.

## 10. Acceptance criteria

- A DOCX file can be profiled, read in ordered blocks, and searched with exact, stable source citations.
- Tables retain row/cell structure and merged-cell information.
- Yue returns structured truncation/cursor information instead of silently omitting content.
- The allowed-root policy applies consistently to all DOCX tools.
- External relationships, macros, and embedded content are never executed.
- Unsupported or lossy features are visible in a fidelity report.
- Workspace sources identify DOCX tools only when the delivered capability is available.
- Mutation tools, when delivered, produce a new artifact and do not overwrite the original by default.
- Automated tests cover normal files, large documents, non-ASCII text, malformed OOXML, access denial, and representative tables/review/media/security cases.

## 11. Open implementation decisions

- Choose the primary OOXML parsing and rendering dependencies after validating fidelity, licensing, security posture, and deployment compatibility against a fixture corpus.
- Define the exact `docx_query` grammar and whether semantic ranking is enabled per deployment.
- Decide the compatibility policy for legacy `.doc`, encrypted DOCX, and macro-enabled `.docm` beyond static inspection.
- Establish a rendered-output golden-test approach for layout-sensitive authoring.

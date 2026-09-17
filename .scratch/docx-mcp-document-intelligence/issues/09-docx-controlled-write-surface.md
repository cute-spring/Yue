# 09: Deliver an opt-in controlled DOCX write surface

**What to build:** With an explicit write-enabled policy, an LLM can create a new document or produce a new revised artifact through `docx_create`, `docx_patch`, `docx_review_patch`, `docx_apply_style`, `docx_redact`, and `docx_save`. Changes target stable locations and return provenance, change summaries, fidelity warnings, and output artifacts.

**Non-goals:** In-place source overwrite by default, execution of macros/embedded content, bypassing document access policy, or unverified layout claims.

**Blocked by:** 02: Deliver the DOCX reader MVP; 05: Add DOCX rendering and focused metadata inspection; 06: Expose review layers and embedded document content; 07: Add DOCX security scanning and fidelity validation.

**Status:** ready-for-agent

**Affected backend areas:** DOCX authoring/patch service; write-policy and artifact storage boundary; built-in MCP write tools; rendering verification; audit/provenance records.

**Tests:** Create/patch/review/style/redaction/save integration tests; original-file immutability tests; output-artifact provenance tests; render-before/after golden checks for layout-sensitive edits; policy-denial tests.

- [ ] All mutation tools require an explicit write-enabled policy and create a new output artifact; the source is never overwritten by default.
- [ ] Patches address stable block/table locators and fail safely when the target is absent, ambiguous, or incompatible.
- [ ] Review patches preserve visible review intent through comments or tracked changes rather than silently applying requested review edits.
- [ ] Redaction removes selected visible content and requested metadata/review layers from the output while reporting its exact scope and residual-fidelity warnings.
- [ ] Layout-sensitive changes include or require render-based verification before the tool reports visual success.

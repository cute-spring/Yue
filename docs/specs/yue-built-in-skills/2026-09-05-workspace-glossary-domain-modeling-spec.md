# 2026-09-05 Workspace Glossary / Domain Modeling Spec

## 1. Product Purpose
Workspace Glossary / Domain Modeling maintains shared project language and stable workspace facts. It lets Yue improve over time while preserving user trust through provenance and confirmation.

## 2. Target User
- Teams or solo users with recurring project terminology.
- Product, engineering, research, and operations users who need Yue to understand domain-specific language.
- Workspace owners who want durable shared context without silent memory writes.

## 3. User-Facing Entry Points
- "Remember this term" or "save this definition" natural-language action.
- Glossary panel in the workspace.
- Memory review queue.
- Term conflict or fuzzy-term detection in chat.
- Follow-up from Research, Handoff, or Clarify outputs when a confirmed term is identified.

## 4. MVP Scope
- Manually save user-confirmed terms into a workspace glossary.
- Store definition, aliases, provenance, confirmation status, and last-updated metadata.
- Preview glossary writes before saving.
- Surface glossary terms for future chats in the active workspace.
- Keep term and fact classes distinct from preferences, conclusions, and temporary chat state.

## 5. Prerequisites and Dependencies
- Workspace-level memory or glossary storage.
- User confirmation flow before durable writes.
- Policy for term, fact, preference, conclusion, and temporary-state classes.
- Provenance model connecting glossary entries to chat messages, documents, or user confirmations.
- Recall governance so saved terms can be used safely in later sessions.

## 6. Expected Artifacts or Outputs
- Workspace glossary entry.
- Domain term list with aliases and provenance.
- Conflict warning when a term appears to have competing meanings.
- Memory review item when Yue proposes a durable entry.

## 7. Safety and Approval Boundaries
- No durable glossary or memory write may happen without explicit user confirmation.
- Research findings, model inferences, and temporary assumptions must not become workspace facts automatically.
- Entries must show provenance and confirmation state.
- Users must be able to reject proposed terms or keep them as session-only context.
- Sensitive or secret values must not be stored as glossary entries unless policy explicitly allows it and the user confirms.

## 8. Out-of-Scope Items
- Fully autonomous knowledge graph construction.
- Organization-wide terminology governance in the first roadmap.
- Silent memory writes from chat, research, or imported documents.
- Treating all remembered content as equally reliable long-term memory.

## 9. Acceptance Criteria
- A user can manually save a confirmed term to the active workspace glossary.
- The saved entry includes definition, provenance, confirmation status, and update metadata.
- Yue previews the durable write before saving.
- Yue can surface a saved term in a later relevant workspace conversation.
- Yue labels conflicts or uncertainty instead of overwriting existing definitions silently.
- Unsupported conclusions are not saved as durable facts without explicit confirmation.

## 10. Suggested Implementation Phase
Phase 1 for manual confirmed-term saving after Phase 0 defines memory classes and confirmation policy. Phase 2 adds conflict detection and provenance UI; Phase 3 adds memory review queue and recall governance.

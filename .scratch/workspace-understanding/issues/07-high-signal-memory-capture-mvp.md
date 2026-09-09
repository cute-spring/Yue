# 07 - High-signal memory capture MVP

**What to build:** Detect obvious high-signal user statements and propose memory candidates without silent durable writes.

**Blocked by:** 05 - Inline confirmation for existing memory candidates.

**Status:** resolved

**Scope:**
- Add a rule-based detector for explicit markers such as "以后", "默认", "我喜欢", "我不喜欢", "remember", "always", and "don't".
- Recommend `About You`, `This Workspace`, or `Just this time`.
- Limit to at most one memory confirmation per assistant turn.
- Start conservative; ordinary chat should not trigger prompts.
- Track dismissals lightly enough to reduce noisy prompts in the current session.

**Validation:**
- Unit tests for Chinese and English high-signal examples.
- Unit tests for ordinary chat examples that must not prompt.
- Frontend tests for frequency limiting.

**Acceptance Criteria:**
- Yue can proactively propose memory when users explicitly state preferences, defaults, corrections, decisions, terms, or constraints.
- No durable memory is written without confirmation.
- Prompt frequency stays bounded.

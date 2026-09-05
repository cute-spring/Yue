# 2026-09-05 Clarify Mode Spec

## 1. Product Purpose
Clarify Mode converts vague or high-cost requests into explicit decisions before Yue acts. It helps users get better work from Yue with fewer wrong turns and less prompt engineering.

## 2. Target User
- Any Yue user starting an ambiguous, expensive, or multi-step task.
- Product and operations users who need task briefs, roadmap outlines, or planning inputs.
- Users who prefer Yue to recommend sensible defaults rather than asking open-ended question lists.

## 3. User-Facing Entry Points
- `/clarify` shortcut.
- Natural-language trigger such as "help me shape this" or "clarify this request."
- Auto-suggestion on vague or high-cost requests.
- Pre-flight step before Research, Runbook, Discovery Questionnaire, or other structured workflows.

## 4. MVP Scope
- Ask one round of high-impact questions.
- Include recommended answers or defaults where possible.
- Avoid interrupting simple chats or low-risk requests.
- End with a concise task brief, decision summary, or roadmap outline.
- Support manual invocation before auto-triggering is enabled.

## 5. Prerequisites and Dependencies
- Prompt-level skill injection works.
- Manual shortcut or command routing exists.
- Basic auto-trigger criteria are defined, even if not fully enabled in MVP.
- Output artifact or message format for task briefs is agreed.

## 6. Expected Artifacts or Outputs
- Clarified task brief.
- Decision list with selected or recommended answers.
- Assumptions and open questions.
- Optional handoff into Research, Questionnaire, or another workbench mode.

## 7. Safety and Approval Boundaries
- Yue should not block simple user requests with unnecessary clarification.
- Yue should distinguish recommended defaults from user-approved decisions.
- Yue should not execute consequential actions until required decisions are confirmed.
- Auto-suggestion should be dismissible.

## 8. Out-of-Scope Items
- Multi-turn consulting interviews in the MVP.
- Automatic execution of downstream workflows without user confirmation.
- Replacing all normal chat responses with clarification mode.
- Complex project planning beyond the generated brief or outline.

## 9. Acceptance Criteria
- A user can manually invoke Clarify Mode.
- Clarify Mode asks only questions that materially affect the output.
- Each question includes a recommended answer when Yue has enough context.
- The result includes a concise task brief or decision summary.
- The feature does not trigger for simple requests in the MVP path.
- The brief can be used as input to later structured workflows.

## 10. Suggested Implementation Phase
Phase 1. Phase 0 defines trigger criteria and question format; Phase 2 adds auto-suggestion for vague or high-cost tasks; Phase 3 feeds Research, Runbook, and Questionnaire setup.

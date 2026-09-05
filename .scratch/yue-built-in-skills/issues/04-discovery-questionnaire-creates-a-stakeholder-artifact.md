# 04 - Discovery Questionnaire creates a stakeholder artifact

**What to build:** A user can turn a human information gap into a workspace questionnaire with context, prioritized questions, answer stubs, and no external send.

**Blocked by:** 01 - Establish built-in workbench mode contract.

**Status:** resolved

**Validation:**
- `npm run test:unit -- src/pages/chat/utils/chatCommands.test.ts src/hooks/chat/chatSubmission.test.ts src/hooks/useAgents.slash-trigger.test.ts`
- `npm run build`

- [x] A user can invoke Discovery Questionnaire from a stated human information gap.
- [x] Yue gathers the minimum setup needed for recipient, objective, and missing knowledge.
- [x] The generated questionnaire includes context, prioritized questions, answer stubs, and decision prompts where useful.
- [x] The questionnaire is saved as a workspace-attached artifact.
- [x] The artifact separates fact questions from decision or preference questions.
- [x] No questionnaire is sent externally without explicit user approval.

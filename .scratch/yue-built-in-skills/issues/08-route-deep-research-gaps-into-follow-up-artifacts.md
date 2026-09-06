# 08 - Route Deep Research gaps into follow-up artifacts

**What to build:** Missing human knowledge from a research report can become a Discovery Questionnaire, while unresolved task decisions can feed Clarify Mode.

**Blocked by:** 04 - Discovery Questionnaire creates a stakeholder artifact; 07 - Deep Research creates a cited workspace report.

**Status:** resolved

**Validation:**
- `npm run test:unit -- src/components/ChatSidebar.workspace.test.ts src/pages/chat/utils/chatCommands.test.ts src/hooks/chat/chatSubmission.test.ts src/hooks/useAgents.slash-trigger.test.ts`
- `npm run build`

- [x] A research report can identify missing human knowledge as a questionnaire candidate.
- [x] A user can create a Discovery Questionnaire from a research gap without re-entering the report context.
- [x] A research report can identify unresolved task decisions as Clarify Mode input.
- [x] Follow-up artifacts link back to the originating research report.
- [x] Follow-up creation requires user action and does not run automatically.

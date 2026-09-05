# 05 - Connect early workbench modes through artifact handoffs

**What to build:** Clarify briefs, handoffs, and questionnaires can reference each other as workspace artifacts so the first three MVPs feel like one workbench flow.

**Blocked by:** 02 - Clarify Mode creates a decision brief; 03 - Session Handoff creates a continuation artifact; 04 - Discovery Questionnaire creates a stakeholder artifact.

**Status:** resolved

**Validation:**
- `npm run test:unit -- src/pages/chat/utils/chatCommands.test.ts src/hooks/chat/chatSubmission.test.ts src/hooks/useAgents.slash-trigger.test.ts`
- `npm run build`

- [x] A Clarify brief can be used as context for a Session Handoff or Discovery Questionnaire.
- [x] A Session Handoff can reference Clarify briefs and questionnaires created in the same workspace.
- [x] A Discovery Questionnaire can link back to the decision brief or handoff that produced it.
- [x] Artifact references are durable enough to be useful in a later workspace session.
- [x] The connected flow does not trigger downstream work automatically without user action.

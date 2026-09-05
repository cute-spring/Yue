# 02 - Clarify Mode creates a decision brief

**What to build:** A user can invoke Clarify Mode manually and receive one focused question round with recommended answers, ending in a concise decision brief.

**Blocked by:** 01 - Establish built-in workbench mode contract.

**Status:** resolved

- [x] A user can invoke Clarify Mode through a manual product path or shortcut.
- [x] Clarify Mode asks only questions that materially affect the requested outcome.
- [x] Questions include recommended answers when enough context exists.
- [x] The final response clearly distinguishes recommended defaults from user-approved decisions.
- [x] The result includes a concise decision brief that can feed later workbench modes.
- [x] Simple low-risk chat requests are not forced through Clarify Mode.

## Answer

Implemented the manual `/clarify` shortcut as the first Clarify Mode MVP path.

`/clarify <task>` now submits a transformed Clarify Mode prompt that asks Yue for one high-impact decision round, includes recommended answers, marks user-approved decisions as pending, and uses an exact response shape with `## Clarifying Questions` and `## Decision Brief`. Natural-language manual triggers such as `clarify this: ...` and `help me shape this: ...` use the same path. `/clarify` without a task shows lightweight usage guidance, and non-command text such as `/clarifyfoo` is left alone.

Validation:

- `npm run test:unit -- src/pages/chat/utils/chatCommands.test.ts src/hooks/chat/chatSubmission.test.ts src/hooks/useAgents.slash-trigger.test.ts` - 27 passed.
- `npm run build` - passed.

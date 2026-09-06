# 2026-09-06 Built-In Skills Release Validation

## Scope
This validation covers the six Yue built-in workbench capabilities:

- Deep Research
- Clarify Mode
- Workspace Glossary / Domain Modeling
- Session Handoff
- Discovery Questionnaire
- Agent Instruction Review

Yue remains a trusted AI workbench and skill runtime platform. This release validates runtime entry points, artifacts, provenance, and approval boundaries; it does not turn Yue into a full skill authoring IDE.

## Acceptance Matrix

| Capability | Visible entry point beyond slash command | Named output | Durable state boundary | Evidence / provenance behavior |
| --- | --- | --- | --- | --- |
| Clarify Mode | Conversation action and workflow preflight | Decision brief | No consequential downstream action until decisions are confirmed | Provenance recommended when saved as a workspace artifact |
| Session Handoff | Conversation action and workspace action | Session handoff | Workspace artifact write occurs only after user request | Redaction required; provenance recommended; reusable across sessions |
| Discovery Questionnaire | Artifact action and research follow-up | Discovery questionnaire | Workspace artifact write occurs only after user request | Sensitive data minimization; provenance recommended; reusable across sessions |
| Deep Research | Message action and workspace source action | Research report | Durable memory writes from findings require separate confirmation | Source scope required; citations and missing-evidence warnings required |
| Workspace Glossary / Domain Modeling | Workspace panel and message action | Workspace glossary entry | Durable memory write requires explicit confirmation | Provenance required; conflicts require review before overwrite |
| Agent Instruction Review | Admin action and Skill Health action | Instruction quality report | Advisory report only; no automatic activation, edits, or publishing | Import gate and tool policy enforcement remain authoritative |

## Cross-Capability Checks

- Every capability declares a workbench-mode contract with `product_boundary: trusted_ai_workbench_skill_runtime`.
- Every capability has at least one visible entry point that is not a raw slash command.
- Every capability declares a clearly named output that can be shown as an artifact, report, brief, questionnaire, glossary entry, or review.
- Any capability that writes durable workspace state requires user request, confirmation, or approval before the write.
- Evidence-bearing capabilities preserve citations, source scope, provenance, redaction, or missing-evidence behavior in the capability contract.
- Cross-capability artifacts are reusable across sessions through workspace attachments or explicit reusable output contracts.

## Remaining Risks

- Clarify Mode still relies on manual invocation and prompt-shaping behavior before Phase 2 auto-suggest heuristics exist.
- Deep Research currently validates the evidence contract and follow-up routing, but long-running job orchestration and connector-source expansion remain future work.
- Workspace Glossary has approval previews and conflict warnings, but a richer review queue and governance UI remain future work.
- Session Handoff creates continuation artifacts, but direct new-chat-from-handoff and runbook seed flows are deferred.
- Discovery Questionnaire creates artifacts, but response import and connector-assisted send/follow-up tracking are deferred.
- Agent Instruction Review is advisory and integrated with Skill Health; quality trends and automated rewrite previews remain deferred.

## Deferred Phase 2 / Phase 3 Items

- Clarify Mode: auto-suggest vague or high-cost requests; feed setup for other workbench modes.
- Session Handoff: start new chats from handoff artifacts; use handoffs as runbook seeds and multi-agent continuation input.
- Discovery Questionnaire: import stakeholder responses; optionally send and track follow-ups through connectors after explicit approval.
- Deep Research: add progress states, export, long-running research jobs, and connector sources.
- Workspace Glossary / Domain Modeling: add term governance UI, review queue, and recall governance.
- Agent Instruction Review: add quality score trends and previewed fix flows that require explicit user approval.

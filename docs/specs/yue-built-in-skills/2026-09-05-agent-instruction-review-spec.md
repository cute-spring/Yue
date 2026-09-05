# 2026-09-05 Agent Instruction Review Spec

## 1. Product Purpose
Agent Instruction Review analyzes agent prompts and imported skills for trigger quality, context load, allowed tools, safety boundaries, and runtime fit. It improves Yue's skill ecosystem while preserving Yue's boundary as a runtime and workbench, not a full skill authoring IDE.

## 2. Target User
- Yue admins reviewing imported skills or built-in agents.
- Developers maintaining first-party Yue skills.
- Workspace owners deciding whether a skill is safe and useful to activate.

## 3. User-Facing Entry Points
- Skill Health panel.
- Skill Import preview.
- Agent editor or agent detail page.
- Internal built-in skill development review.
- Admin action such as "review this skill" or "check this agent prompt."

## 4. MVP Scope
- Analyze one selected skill or agent prompt at a time.
- Report trigger clarity, activation risk, context loading, tool policy, safety boundaries, examples quality, and runtime fit.
- Recommend concrete fixes without providing a full authoring environment.
- Integrate with existing import gate concepts where possible.
- Keep the output as an admin-facing report.

## 5. Prerequisites and Dependencies
- Skill package and prompt metadata are readable.
- Review rubric is stable.
- Import gate compatibility report is available or planned.
- Skill Health surface can display quality findings.
- Tool policy metadata is available enough to identify risky or mismatched instructions.

## 6. Expected Artifacts or Outputs
- Instruction quality report.
- Risk and readiness findings.
- Recommended edits or activation conditions.
- Optional quality score or rubric checklist in later phases.

## 7. Safety and Approval Boundaries
- The review must not activate, modify, or publish a skill automatically.
- Recommendations should be advisory until a user applies them.
- Yue should flag risky tool permissions, ambiguous triggers, hidden state changes, and excessive context loading.
- The feature should not encourage bypassing import gate checks.
- Any future automated fix flow must preview changes before applying them.

## 8. Out-of-Scope Items
- Full skill authoring IDE.
- Marketplace publishing workflow.
- Automatic prompt rewriting or activation in MVP.
- Cross-vendor compatibility certification beyond Yue runtime fit.
- Broad enterprise governance dashboard.

## 9. Acceptance Criteria
- An admin can run a review on one selected skill or agent.
- The report covers trigger quality, context load, allowed tools, safety, examples, and Yue runtime fit.
- The report distinguishes blockers from recommendations.
- The report does not modify or activate the reviewed skill.
- Findings are suitable for display in Skill Health or Import preview.
- The scope reinforces Yue as a skill runtime platform rather than an authoring IDE.

## 10. Suggested Implementation Phase
Phase 1 for an admin-only report after Phase 0 defines the rubric. Phase 2 integrates with Skill Health and Import preview; Phase 3 adds quality trends and pre-activation recommendations.

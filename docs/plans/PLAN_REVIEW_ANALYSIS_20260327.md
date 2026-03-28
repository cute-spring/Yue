# Plan Portfolio Review Analysis (2026-03-27)

## Executive Summary

This document provides a comprehensive review of all architecture evolution plans in `docs/plans/`, identifying:
1. **Low-value plans** that should be archived or merged
2. **Outdated plans** that need updates or have been superseded
3. **Missing updates** to INDEX.md
4. **Recommendations** for portfolio optimization

**Total Plans Reviewed**: 40 documents
**Active Plans in INDEX.md**: 9 Epics (3 In Progress, 6 Todo)
**Archived Plans**: 9 documents
**Untracked Active Plans**: 15+ documents

---

## 1. Plan Classification Framework

### Classification Criteria

| Category | Criteria | Action |
|----------|----------|--------|
| **High Value - Active** | Clear goals, phased approach, linked to Epic, recent activity | Keep in INDEX.md, track progress |
| **Medium Value - Pending** | Good design but no Epic link, unclear priority | Consider linking to Epic or archive |
| **Low Value - Outdated** | Superseded by newer plans, scope creep, vague goals | Archive with reference to successor |
| **Duplicate/Overlap** | Multiple plans covering same concern | Merge or designate primary |

---

## 2. Detailed Plan Analysis

### 2.1 High Value Plans (Already in INDEX.md) ✅

These plans are properly tracked and should remain:

#### In Progress Epics
1. **Epic 4**: [observability_transparency_plan.md](./observability_transparency_plan.md) - 90% complete
   - Status: Well-structured, clear phases
   - Recommendation: Complete Phase 3 & 4

2. **Epic 5**: [multimodal_image_qa_enhancement_plan_20260317.md](./multimodal_image_qa_enhancement_plan_20260317.md) - 60% complete
   - Status: Good progress, Phase 4 links to message-export plan
   - Recommendation: Complete Phase 3 & 4

3. **Epic 6**: [release_readiness_gate_execution_plan_20260314.md](./release_readiness_gate_execution_plan_20260314.md) - 85% complete
   - Status: Strong foundation, Phase 3 links to unified contract gate
   - Recommendation: Complete Phase 3

#### Todo Epics
4. **Epic 3**: [File_Management_Improvement_Review.md](./File_Management_Improvement_Review.md)
   - Status: Comprehensive review, ready for execution
   - Recommendation: Start Phase 1

5. **Epic 7**: [hierarchical_memory_foundation_plan_20260315.md](./hierarchical_memory_foundation_plan_20260315.md)
   - Status: Good design, linked sub-plans
   - Recommendation: Start Phase 1

6. **Epic 8**: [skill_creator_implementation_plan_20260319.md](./skill_creator_implementation_plan_20260319.md)
   - Status: Comprehensive, linked skill gap plans
   - Recommendation: Start Phase 1

7. **Epic 9**: [codebase_refactor_plan_20260319.md](./codebase_refactor_plan_20260319.md)
   - Status: Clear scope, sub-plans defined
   - Recommendation: Start Phase 1

---

### 2.2 Medium Value Plans (Not in INDEX.md) ⚠️

These plans have merit but lack Epic linkage or clear prioritization:

#### Recently Created (Last 7 Days)
1. **2026-03-26-chat-history-management-improvement-plan.md**
   - Quality: High - well-structured with phases
   - Issue: Not linked to any Epic
   - Recommendation: Link to Epic 9 (codebase refactor) as sub-plan OR create new Epic for UX improvements

2. **voice_input_session_refactor_plan_20260326.md**
   - Quality: High - focused refactor
   - Issue: Voice input already marked Done in INDEX.md
   - Recommendation: **ARCHIVE** - This is a refactor of completed feature, not new Epic

3. **chat_frontend_modularization_plan_20260326.md**
   - Quality: High - clear scope
   - Issue: Overlaps with Epic 9's frontend refactor
   - Recommendation: **MERGE** into Epic 9 as Phase 2c

4. **upload_file_integration_plan_20260324.md**
   - Quality: Medium - MVP-focused
   - Issue: Partially overlaps with Epic 5 (multimodal)
   - Recommendation: Link to Epic 5 as Phase 5

5. **document_access_control_enhancement_plan_20260323.md**
   - Quality: High - thorough analysis
   - Issue: Already partially implemented (skill_service modularization)
   - Recommendation: Link to Epic 3 (file management) as Phase 5

6. **settings_tsx_modularization_plan_20260323.md**
   - Quality: High - detailed analysis
   - Issue: Already listed as sub-plan in Epic 9
   - Recommendation: **Already tracked** ✅

7. **skill_service_modularization_plan_20260323.md**
   - Quality: High - Phase 1 completed
   - Issue: Not explicitly linked to Epic 8
   - Recommendation: Link to Epic 8 as Phase 0 (foundation)

#### Older Plans (2+ Weeks)
8. **2026-03-20-message-export-plan.md**
   - Quality: Medium - good design
   - Issue: Linked from Epic 5 Phase 4, but not executable (requires agentic workers)
   - Recommendation: Keep as reference, execute when Epic 5 Phase 4 starts

9. **llm_providers_api_refactoring_plan.md**
   - Quality: Medium
   - Issue: Overlaps with Epic 7 Phase 3
   - Recommendation: **MERGE** into Epic 7 Phase 3

10. **ui_capability_management_plan_plan.md**
    - Quality: Medium
    - Issue: Already linked in Epic 7 Phase 2
    - Recommendation: **Already tracked** ✅

---

### 2.3 Low Value / Outdated Plans 🚫

These plans should be archived or significantly revised:

#### Superseded Plans
1. **planned_enhancement_execution_order_20260314.md** (and Chinese version)
   - Issue: Execution order document, not a plan
   - Content: Priority recommendations now outdated
   - Recommendation: **ARCHIVE** - Historical reference only

2. **reasoning_tools_execution_enhancement_plan_20260308.md**
   - Issue: Largely superseded by Epic 4 (observability)
   - Overlap: Event envelope, turn binding, idempotency all covered in Epic 4
   - Recommendation: **ARCHIVE** with link to Epic 4

3. **openclaw_tool_calling_reference_execution_plan_20260308.md**
   - Issue: Reference implementation plan, not Yue-specific
   - Content: Lessons from OpenClaw, not actionable Epic
   - Recommendation: **ARCHIVE** to reference materials

#### Skill Gap Plans (Already Linked but Stale)
4. **ppt_skill_gap_enhancement_plan_20260307.md**
   - Issue: Linked to Epic 8 Phase 2, but 20 days old
   - Status: No visible progress
   - Recommendation: Keep linked but mark as "Blocked" or "Deprioritized"

5. **nanobot_skill_gap_plan_20260307.md**
   - Issue: Linked to Epic 8 Phase 3, but 20 days old
   - Status: No visible progress
   - Recommendation: Keep linked but mark as "Blocked" or "Deprioritized"

#### Design/Analysis Documents (Not Plans)
6. **REASONING_CHAIN_OPTIMIZATION.md**
   - Issue: Research document, not executable plan
   - Content: Industry survey, completed short-term items
   - Recommendation: **ARCHIVE** to reference/ folder

7. **Skill_Feature_Roadmap.md**
   - Issue: Roadmap document (dated Feb 14), superseded by Epic 8
   - Recommendation: **ARCHIVE** - Historical reference

8. **SMART_DOC_PROCESSING_PLAN.md**
   - Issue: Analysis document, not phased plan
   - Content: Good research but no clear execution path
   - Recommendation: **ARCHIVE** key insights to docs/, discard plan

9. **PDF_BUILTIN_TOOLS_HIGH_ROI.md**
   - Issue: Already implemented (PDF tools exist)
   - Recommendation: **ARCHIVE** - Work completed

10. **Mermaid_Streaming_Optimization.md**
    - Issue: Optimization guide, not executable plan
    - Content: Best practices reference
    - Recommendation: **ARCHIVE** to reference/ folder

11. **MS_EXCEL_SUPPORT_PLAN.md**
    - Issue: Excel service already implemented
    - Recommendation: **ARCHIVE** - Work completed

12. **Docs_Tooling_Enhancement_Plan.md**
    - Issue: Analysis document with recommendations
    - Content: Many recommendations already implemented
    - Recommendation: **ARCHIVE** - Reference only

13. **MCP_DOC_AGENT_PLAN.md**
    - Issue: Design document, not executable plan
    - Content: MCP + filesystem integration design
    - Recommendation: **ARCHIVE** to reference/ folder

14. **agent_tooling_refactor_plan.md**
    - Issue: Already implemented (ToolRegistry, BaseTool done)
    - Recommendation: **ARCHIVE** - Work completed

---

### 2.4 Voice Input Plans (Special Case) 🎤

Three voice input plans exist:
1. **Voice_Input_Feature_Design.md** - Design spec
2. **Voice_Input_Implementation_Plan.md** - Implementation plan
3. **Voice_Input_Release_Checklist.md** - Release checklist
4. **voice_input_session_refactor_plan_20260326.md** - Refactor plan

**Status**: Feature marked as Done in INDEX.md

**Issue**: 
- Original plans completed ✅
- Refactor plan created 2026-03-26 (10 days after feature completion)
- Refactor addresses technical debt from rushed implementation

**Recommendation**:
- Keep original 3 plans in **archive/** (completed work)
- **ARCHIVE** refactor plan with note: "Technical debt refactor - execute only if voice input issues arise"
- Rationale: Don't start Epics for refactoring completed features unless there are active problems

---

## 3. INDEX.md Update Recommendations

### 3.1 Missing Plans to Add

The following high-quality plans should be added to INDEX.md:

#### Option A: Add as Sub-Plans to Existing Epics
```markdown
### Epic 5: 消息交互与多模态增强
- [ ] **Phase 5: 文件上传集成** (见 [upload_file_integration_plan_20260324.md](./upload_file_integration_plan_20260324.md))

### Epic 7: 记忆与模型能力精细化管理
- [ ] **Phase 3: LLM Providers API 重构** (合并 [llm_providers_api_refactoring_plan.md](./llm_providers_api_refactoring_plan.md))

### Epic 8: 技能系统深度增强
- [ ] **Phase 0: 技能服务模块化** (见 [skill_service_modularization_plan_20260323.md](./skill_service_modularization_plan_20260323.md)) - Phase 1 已完成

### Epic 9: 代码库健康与 God Object 重构
- [ ] **Phase 2c: 前端聊天组件重构** (合并 [chat_frontend_modularization_plan_20260326.md](./chat_frontend_modularization_plan_20260326.md))
```

#### Option B: Create New Epics
```markdown
### Epic 10: 聊天历史与用户体验优化
> **状态**: 待启动
> **详情文档**: [2026-03-26-chat-history-management-improvement-plan.md](./2026-03-26-chat-history-management-improvement-plan.md)
> **目标**: 实现用户隔离、搜索过滤、UI 优化
- [ ] **Phase 1: 用户隔离基础** (owner 字段、API 过滤)
- [ ] **Phase 2: 前端搜索与过滤** (虚拟滚动、分组)
- [ ] **Phase 3: 高级功能** (收藏、标签)
```

### 3.2 Plans to Remove from INDEX.md

None - all currently linked plans are still relevant.

### 3.3 Status Updates Needed

```markdown
### Epic 8: 技能系统深度增强
- [x] **Phase 0: 技能服务模块化** (Phase 1 已完成，测试全绿)
- [ ] **Phase 1: Skill Creator 实现**
- [ ] **Phase 2: PPT 技能加固** (Blocked/Deprioritized)
- [ ] **Phase 3: Nanobot 技能演进** (Blocked/Deprioritized)
```

---

## 4. Archive Recommendations

### 4.1 Immediate Archive (Low Value, Outdated, Completed)

Move to `docs/plans/archive/`:

1. `planned_enhancement_execution_order_20260314.md`
2. `planned_enhancement_execution_order_20260314_zh.md`
3. `reasoning_tools_execution_enhancement_plan_20260308.md`
4. `openclaw_tool_calling_reference_execution_plan_20260308.md`
5. `REASONING_CHAIN_OPTIMIZATION.md`
6. `Skill_Feature_Roadmap.md`
7. `SMART_DOC_PROCESSING_PLAN.md`
8. `PDF_BUILTIN_TOOLS_HIGH_ROI.md`
9. `Mermaid_Streaming_Optimization.md`
10. `MS_EXCEL_SUPPORT_PLAN.md`
11. `Docs_Tooling_Enhancement_Plan.md`
12. `MCP_DOC_AGENT_PLAN.md`
13. `agent_tooling_refactor_plan.md`
14. `voice_input_session_refactor_plan_20260326.md`

### 4.2 Archive with Reference Note

These should be archived but keep a reference in their respective Epics:

```markdown
<!-- In Epic 4 -->
> **历史参考**: [reasoning_tools_execution_enhancement_plan_20260308.md](./archive/reasoning_tools_execution_enhancement_plan_20260308.md) - 大部分内容已纳入 Epic 4

<!-- In Epic 7 -->
> **历史参考**: [llm_providers_api_refactoring_plan.md](./archive/llm_providers_api_refactoring_plan.md) - 已合并到 Phase 3

<!-- In Epic 8 -->
> **历史参考**: [skill_service_modularization_plan_20260323.md](./archive/skill_service_modularization_plan_20260323.md) - Phase 1 已完成
```

---

## 5. Portfolio Health Metrics

### Current State
- **Total Plans**: 40 documents
- **Active (In INDEX.md)**: 9 Epics
- **Untracked Active**: 4 plans (should be linked)
- **Completed/Implemented**: 8 plans
- **Outdated/Superseded**: 14 plans (should be archived)
- **Reference/Analysis**: 5 documents

### Target State
- **Active (In INDEX.md)**: 10 Epics (add Epic 10 for chat history)
- **Archived**: 23 documents (completed + outdated)
- **Reference**: 7 documents (design docs, analysis)

### Benefits
1. **Clarity**: INDEX.md becomes single source of truth
2. **Focus**: Only executable plans remain in active directory
3. **History**: Archived plans preserved for reference
4. **Maintainability**: Easier to track progress and priorities

---

## 6. Action Plan

### Phase 1: Archive Low-Value Plans (30 minutes)
- [ ] Move 14 outdated/superseded plans to archive/
- [ ] Update INDEX.md to remove references to archived plans (if any)

### Phase 2: Update INDEX.md (30 minutes)
- [ ] Add upload_file_integration_plan to Epic 5 Phase 5
- [ ] Add chat_frontend_modularization_plan to Epic 9 Phase 2c
- [ ] Add skill_service_modularization_plan to Epic 8 Phase 0 (mark Phase 1 done)
- [ ] Consider creating Epic 10 for chat history improvements
- [ ] Update Epic 8 status to show Phase 0 completed

### Phase 3: Link Remaining Plans (15 minutes)
- [ ] Link document_access_control_enhancement_plan to Epic 3 Phase 5
- [ ] Merge llm_providers_api_refactoring_plan into Epic 7 Phase 3
- [ ] Decide on voice_input_session_refactor_plan (execute or archive)

### Phase 4: Documentation Cleanup (15 minutes)
- [ ] Update README.md with current plan structure
- [ ] Add archive index document explaining what was archived and why
- [ ] Create "Reference" folder for non-executable design docs

---

## 7. Summary of Recommendations

### High Priority (Do Now)
1. ✅ Archive 14 low-value/outdated plans
2. ✅ Update INDEX.md with 4 missing high-value plans
3. ✅ Mark Epic 8 Phase 0 as completed

### Medium Priority (Do This Week)
4. ⚠️ Create Epic 10 for chat history UX improvements
5. ⚠️ Decide on voice_input refactor (execute or archive)
6. ⚠️ Update Epic 5, 7, 9 with merged sub-plans

### Low Priority (Do When Convenient)
7. 📝 Create archive index document
8. 📝 Move reference/analysis docs to separate folder
9. 📝 Update README.md with plan management guide

---

## 8. Conclusion

The plan portfolio is generally healthy but has accumulated technical debt:

- **Strengths**: Clear Epic structure, good phase breakdown, strong test coverage
- **Weaknesses**: 14 outdated plans, 4 untracked active plans, no archive index
- **Opportunities**: Cleaner INDEX.md, better plan discoverability, reduced cognitive load

**Recommended Next Action**: Execute Phase 1 (archive low-value plans) and Phase 2 (update INDEX.md) immediately. This will provide immediate clarity on what's actually being worked on versus what's historical reference.

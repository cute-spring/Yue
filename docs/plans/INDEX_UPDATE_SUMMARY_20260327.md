# INDEX.md Update Summary (2026-03-27)

## Changes Made

This document summarizes the updates made to `docs/plans/INDEX.md` based on the comprehensive plan portfolio review in [PLAN_REVIEW_ANALYSIS_20260327.md](./PLAN_REVIEW_ANALYSIS_20260327.md).

---

## 1. New Epics Added

### Epic 10: 聊天历史与用户体验优化 (Chat History & UX)
- **Status**: Todo (待启动)
- **Plan**: [2026-03-26-chat-history-management-improvement-plan.md](./2026-03-26-chat-history-management-improvement-plan.md)
- **Goal**: Implement user isolation, search/filter, virtual scrolling for better chat history management
- **Phases**:
  - Phase 1: User isolation foundation (Session owner field, API filters)
  - Phase 2: Frontend search & filter (virtual scrolling, date grouping, search bar)
  - Phase 3: Advanced features (starred sessions, tags, quick navigation)

---

## 2. Existing Epics Updated

### Epic 5: 消息交互与多模态增强
**Changes:**
- ✅ Added **Phase 5: 文件上传集成** 
- 📄 Plan: [upload_file_integration_plan_20260324.md](./upload_file_integration_plan_20260324.md)
- 📝 Updated goal to include file upload support

**Rationale**: File upload integration is a natural extension of multimodal capabilities, complementing image support.

---

### Epic 7: 记忆与模型能力精细化管理
**Changes:**
- 🔄 Updated Phase 3 description to "合并 [llm_providers_api_refactoring_plan.md](./llm_providers_api_refactoring_plan.md)"
- 📝 Clarifies that the refactoring plan is merged into this phase rather than being separate

**Rationale**: The LLM providers API refactoring plan is now explicitly recognized as part of Phase 3, avoiding duplication.

---

### Epic 8: 技能系统深度增强
**Changes:**
- 📊 Status changed: 待启动 → **推进中 (约 15%)**
- ✅ Added **Phase 0: 技能服务模块化** (completed Phase 1)
- 📄 Plan: [skill_service_modularization_plan_20260323.md](./skill_service_modularization_plan_20260323.md)
- ⚠️ Marked Phase 2 & 3 as "Blocked/Deprioritized"

**Rationale**: 
- Phase 0 modularization work is already completed with passing tests
- PPT and Nanobot skill gaps are deprioritized until core Skill Creator is implemented

---

### Epic 9: 代码库健康与 God Object 重构
**Changes:**
- 📊 Status changed: 待启动 → **推进中 (约 10%)**
- 📄 Added sub-plan: [chat_frontend_modularization_plan_20260326.md](./chat_frontend_modularization_plan_20260326.md)
- ✅ Added **Phase 2c: 前端重构 (Chat 组件专项)**

**Rationale**: The chat frontend modularization plan is a natural extension of the existing frontend refactor work, focusing on Chat.tsx and related hooks.

---

## 3. Archive Reference Added

Added a new **归档说明** section in the Done section to provide visibility into what has been archived and why:

### Categories of Archived Plans:

**工具架构重构相关:**
- `agent_tooling_refactor_plan.md` - Already implemented (ToolRegistry, BaseTool)
- `builtin_tools_refactor_plan.md` - Completed

**技能系统演进相关:**
- `skills_long_term_architecture_and_legacy_removal_plan_20260317.md` - Completed
- `agent_classification_and_skill_group_plan_20260319.md` - Completed

**已完成功能计划:**
- `PDF_BUILTIN_TOOLS_HIGH_ROI.md` - PDF tools implemented
- `MS_EXCEL_SUPPORT_PLAN.md` - Excel service implemented
- `2026-03-24-auto-speech-synthesis.md` - Speech synthesis completed

**已被替代计划:**
- `reasoning_tools_execution_enhancement_plan_20260308.md` - Superseded by Epic 4
- `Skill_Feature_Roadmap.md` - Superseded by Epic 8

**分析参考文档:**
- `REASONING_CHAIN_OPTIMIZATION.md` - Industry research reference
- `SMART_DOC_PROCESSING_PLAN.md` - Analysis without execution path
- `Docs_Tooling_Enhancement_Plan.md` - Recommendations implemented
- `MCP_DOC_AGENT_PLAN.md` - Design reference

---

## 4. Portfolio Summary

### Before Update:
- **Total Epics**: 9 (3 In Progress, 6 Todo)
- **Untracked Plans**: 4+ high-quality plans not linked
- **Archive Visibility**: No reference to archived documents

### After Update:
- **Total Epics**: 10 (3 In Progress, 7 Todo)
- **New Epics**: Epic 10 (Chat History & UX)
- **Tracked Plans**: All high-value plans now linked to Epics
- **Archive Visibility**: Clear reference section explaining what was archived and why

### Epic Status Overview:

| Epic | Status | Progress | Key Change |
|------|--------|----------|------------|
| Epic 3 | Todo | 0% | No change |
| Epic 4 | In Progress | 90% | No change |
| Epic 5 | In Progress | 60% | + Phase 5 (file upload) |
| Epic 6 | In Progress | 85% | No change |
| Epic 7 | Todo | 0% | Phase 3 clarified |
| Epic 8 | In Progress | 15% | + Phase 0 (completed), Phases 2-3 deprioritized |
| Epic 9 | In Progress | 10% | + Phase 2c (chat frontend) |
| Epic 10 | Todo | 0% | **NEW** |

---

## 5. Next Steps

### Immediate Actions (Recommended):
1. ✅ **Archive 14 low-value plans** - Move outdated/superseded documents to `archive/` folder
   - See [PLAN_REVIEW_ANALYSIS_20260327.md](./PLAN_REVIEW_ANALYSIS_20260327.md) Section 4.1 for complete list

2. ✅ **Communicate changes** - Update team on new Epic structure and priorities

3. ✅ **Update README.md** - Reference the new archive structure

### This Week:
4. ⚠️ **Decide on voice_input refactor** - Execute [voice_input_session_refactor_plan_20260326.md](./voice_input_session_refactor_plan_20260326.md) or archive it

5. ⚠️ **Prioritize Epic 10** - Decide if Chat History UX improvements should move to In Progress

### When Convenient:
6. 📝 **Create archive index** - Detailed document explaining what each archived plan contained

7. 📝 **Move reference docs** - Create `reference/` folder for non-executable design documents

---

## 6. Benefits

### Improved Clarity:
- ✅ INDEX.md now reflects all active work streams
- ✅ Clear distinction between executable plans and reference documents
- ✅ Archive section provides historical context

### Better Focus:
- ✅ 10 Epics with clear ownership and phases
- ✅ Deprioritized work explicitly marked (Phases 2-3 of Epic 8)
- ✅ Progress percentages updated to reflect actual state

### Reduced Cognitive Load:
- ✅ 14 outdated plans identified for archival
- ✅ Single source of truth for what's being worked on
- ✅ Easy to answer "what should I work on next?"

---

## 7. Files Modified

1. **INDEX.md** - Main backlog board (this update)
2. **PLAN_REVIEW_ANALYSIS_20260327.md** - Comprehensive review analysis (created)
3. **INDEX_UPDATE_SUMMARY_20260327.md** - This summary document (created)

---

## 8. Validation

Run these commands to validate the update:

```bash
# Check that INDEX.md is valid markdown
cd docs/plans
cat INDEX.md | head -n 120

# Verify all linked plans exist
grep -oP '\[.*?\]\(\./[^)]+\)' INDEX.md | while read -r link; do
  file=$(echo "$link" | grep -oP '\(\./\K[^)]+')
  if [ ! -f "$file" ]; then
    echo "❌ Missing: $file"
  else
    echo "✅ Found: $file"
  fi
done
```

---

**Update completed on**: 2026-03-27  
**Updated by**: AI Assistant  
**Review status**: Ready for team review

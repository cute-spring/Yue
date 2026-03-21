---
name: plan-archiver
description: 自动归档已完成的架构演进计划文档。当用户请求归档某个计划，或者计划已经完全执行完毕时，使用此技能。它会自动将文档移动到 archive 目录，并更新 INDEX.md 状态。
---

# Plan Archiver (计划自动归档技能)

你现在扮演一位资深的敏捷项目经理。当用户触发此技能时，你需要执行一套标准的归档操作。

## 归档工作流 (Workflow)

请严格按照以下步骤操作，不需要询问用户，直接执行并报告结果：

1. **查找目标文档**
   - 寻找 `docs/plans/` 目录下与用户请求名称匹配的 Markdown 文档。
   - 确认该文档尚未被移动到 `archive/` 目录。

2. **移动文件**
   - 确保 `docs/plans/archive/` 目录存在（如果不存在则使用 `mkdir -p` 创建）。
   - 将目标 Markdown 文件移动到 `docs/plans/archive/` 目录下。

3. **更新总控看板 (`INDEX.md`)**
   - 读取 `docs/plans/INDEX.md`。
   - 找到目标文档在 `INDEX.md` 中的记录。
   - 将其从 `In Progress` 或 `Todo` 区域剪切。
   - 粘贴到 `## ⚪ Done (已完成)` 区域下。
   - **关键**：确保更新链接路径，从 `./[文件名].md` 改为 `./archive/[文件名].md`。

4. **Git 提交**
   - 自动执行 `git add docs/plans/`。
   - 执行 `git commit -m "docs: archive completed plan [计划名称]"`。

5. **汇报结果**
   - 向用户输出友好的完成消息，并展示更新后的 Done 列表。
# ChatSidebar UI 优化实施计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ChatSidebar 重构为“高生产力”风格，优化多日期分组展示并添加粘性页眉效果。

**Architecture:** 通过修改 [ChatSidebar.tsx](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatSidebar.tsx) 的 JSX 结构和 Tailwind 类名，实现信息密度更高的列表布局。使用 `sticky` 定位实现日期分组页眉置顶。

**Tech Stack:** SolidJS, Tailwind CSS

---

## Chunk 1: 结构重构与基础样式

### Task 1: Header 与搜索框优化

**Files:**
- Modify: `frontend/src/components/ChatSidebar.tsx`

- [ ] **Step 1: 整合 Header 标题与新建按钮**

```tsx
// 搜索并替换顶部的 Header 部分
<div class="p-4 bg-slate-50 border-b border-border flex items-center gap-2">
  <div class="flex-1 relative">
    <input type="text" placeholder="Search chats..." class="w-full bg-white border border-border rounded-lg px-8 py-2 text-xs focus:ring-2 focus:ring-primary/20 outline-none transition-all" />
    <svg class="w-4 h-4 absolute left-2.5 top-2.5 text-text-muted" ... />
  </div>
  <button onClick={props.onNewChat} class="bg-primary hover:bg-primary-dark text-white p-2 rounded-lg transition-all active:scale-95">
    <svg ... />
  </button>
</div>
```

- [ ] **Step 2: 优化过滤器 (Filters) 为 Chip 样式**

- [ ] **Step 3: 提交变更**

```bash
git add frontend/src/components/ChatSidebar.tsx
git commit -m "style: optimize sidebar header and search UI"
```

## Chunk 2: 列表项与多日期分组增强

### Task 2: 实现粘性日期页眉与列表项样式

**Files:**
- Modify: `frontend/src/components/ChatSidebar.tsx`

- [ ] **Step 1: 修改日期分组页眉样式并添加 Sticky 类**

```tsx
<div class="sticky top-0 z-10 px-4 py-2 text-[10px] font-black text-primary uppercase tracking-widest border-b border-primary/10 bg-surface/95 backdrop-blur-sm flex justify-between items-center">
  <span>{groupName}</span>
  <span class="bg-primary/5 px-1.5 py-0.5 rounded text-[9px]">{count} chats</span>
</div>
```

- [ ] **Step 2: 重构对话项 (Chat Item) 布局**

- 添加摘要预览（两行截断）
- 添加标签 (Tags) 展示逻辑
- 优化选中/悬停的边框与背景色

- [ ] **Step 3: 运行并验证**

Run: `npm run dev` (在前端目录)
Expected: 检查预览，验证 Sticky Header 效果。

- [ ] **Step 4: 提交变更**

```bash
git add frontend/src/components/ChatSidebar.tsx
git commit -m "feat: enhance chat history grouping and item density"
```

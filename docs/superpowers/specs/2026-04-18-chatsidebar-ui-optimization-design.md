# 2026-04-18 ChatSidebar UI 优化设计方案 (高生产力风格)

## 1. 背景与目标
当前 `ChatSidebar` 设计在视觉层级和空间利用率上有待提升。本方案旨在采用“高生产力 (High-Efficiency)”风格进行重构，优化多日期分组展示，提升信息密度和检索效率。

## 2. 核心变更方案

### 2.1 布局重构
- **Header 整合**：将标题与“新建对话”按钮整合，减少顶部空间占用。
- **搜索框优化**：内置搜索图标，采用更现代的圆角矩形设计。
- **过滤器样式**：改为水平滚动的 Chip 标签样式。

### 2.2 多日期分组与粘性页眉 (Sticky Headers)
- **分组逻辑**：保持 `Today`, `Yesterday`, `Last 7 Days`, `Earlier` 的逻辑。
- **视觉样式**：
    - `Today`: 使用蓝色主题，显示聊天计数。
    - `Other Groups`: 使用中性 Slate 灰色。
- **Sticky 交互**：使用 `sticky-date` 类实现滚动时的日期页眉置顶。

### 2.3 对话项 (Session Item) 增强
- **信息密度**：显示标题、两行摘要预览、彩色标签。
- **选中状态**：移除 4px 粗边框，改为 2px 精致色条 + 柔和背景色。
- **悬停效果**：添加微小的背景色过渡。

## 3. 技术实现细节
- **组件位置**：[ChatSidebar.tsx](file:///Users/gavinzhang/ws-ai-recharge-2026/Yue/frontend/src/components/ChatSidebar.tsx)
- **CSS 框架**：使用现有的 Tailwind CSS 类名。
- **新增 CSS 类 (在组件内定义)**：
    ```css
    .sticky-date { position: sticky; top: 0; z-index: 10; backdrop-filter: blur(4px); }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
    .no-scrollbar::-webkit-scrollbar { display: none; }
    ```

## 4. 验证计划
- **视觉验证**：通过本地开发预览检查样式是否符合 Mockup。
- **功能验证**：确保原有的搜索、过滤、删除、生成摘要功能不受影响。
- **交互验证**：验证滚动时粘性页眉的平滑度。

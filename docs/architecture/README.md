# Architecture Documentation - 架构设计文档

本目录收录了 Yue 项目的核心架构设计文档、技术决策记录和架构演进指南。

---

## 📐 文档分类

### 核心架构指南

| 文档 | 说明 | 状态 |
|------|------|------|
| **[12-Factor App Guide](12_Factor_App_Guide.md)** | 云原生架构规范与实施指南 | ✅ 已完成 |
| **[LLM Capability Inference](LLM_Capability_Inference_Architecture.md)** | 模型能力推理架构设计 | ✅ 已完成 |
| **[Skill Runtime Current Operation](Skill_Runtime_Current_Operation.md)** | 当前 Skill Runtime 启动、导入、路由与集成链路说明 | ✅ 已完成 |

### 架构决策记录 (ADRs)

[architecture/decisions/](decisions/) 目录收录了重要的架构决策记录 (Architecture Decision Records, ADRs)：

| ADR | 主题 | 状态 |
|-----|------|------|
| **ADR-001** | 存储抽象层设计（待创建） | ⏳ 待创建 |
| **ADR-002** | 日志架构演进（待创建） | ⏳ 待创建 |
| **ADR-003** | 数据库选型与迁移策略（待创建） | ⏳ 待创建 |

---

## 🏗️ 架构全景图

### 系统分层架构

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │
│  (Frontend: React + TypeScript + Vite)  │
├─────────────────────────────────────────┤
│         Application Layer               │
│  (FastAPI + Agent Orchestration)        │
├─────────────────────────────────────────┤
│         Service Layer                   │
│  (Chat, Agent, MCP, File, Memory)       │
├─────────────────────────────────────────┤
│         Data Layer                      │
│  (SQLite + Storage Abstraction)         │
└─────────────────────────────────────────┘
```

### 核心组件

1. **前端层**
   - React + TypeScript
   - Tailwind CSS
   - Vite 构建工具

2. **应用层**
   - FastAPI 后端框架
   - Agent 编排引擎
   - 流式响应处理

3. **服务层**
   - Chat 服务
   - Agent 服务
   - MCP (Model Context Protocol)
   - 文件管理
   - 记忆系统

4. **数据层**
   - SQLite 数据库
   - 存储抽象层 (Storage Abstraction)
   - 配置管理

---

## 🎯 架构原则

### 12-Factor 合规性

项目严格遵循 [12-Factor App](https://12factor.net/) 方法论：

- ✅ **Factor 1: Codebase** - 单一代码库
- ✅ **Factor 2: Dependencies** - 显式声明依赖
- ✅ **Factor 3: Config** - 环境变量配置
- ✅ **Factor 4: Backing Services** - 后端服务抽象
- ✅ **Factor 5: Build, Release, Run** - 构建发布运行分离
- ⏳ **Factor 6: Processes** - 无状态进程（进行中）
- ✅ **Factor 7: Port Binding** - 端口绑定
- ⏳ **Factor 8: Concurrency** - 并发模型
- ✅ **Factor 9: Disposability** - 快速启动优雅关闭
- ✅ **Factor 10: Dev/Prod Parity** - 环境一致性
- ✅ **Factor 11: Logs** - 日志即流
- ⏳ **Factor 12: Admin Processes** - 管理进程

详见：[12-Factor App Guide](12_Factor_App_Guide.md)

### 设计模式

- **依赖注入**: 服务层解耦
- **策略模式**: 多模型 Provider 支持
- **观察者模式**: 事件驱动架构
- **适配器模式**: MCP 工具集成

---

## 📊 架构决策流程

### 何时创建 ADR

当面临以下情况时，应创建架构决策记录：

1. **技术选型**: 选择新的框架、库或工具
2. **架构重构**: 重大模块拆分或合并
3. **性能优化**: 影响系统整体性能的决策
4. **安全加固**: 安全策略和机制变更

### ADR 模板

```markdown
# ADR-XXX: 决策标题

## 状态
[提案 | 已接受 | 已废弃 | 已替代]

## 背景
描述问题背景和决策动机。

## 决策
详细描述做出的决策。

## 备选方案
列出考虑过的其他方案及其优缺点。

## 影响
- 对现有系统的影响
- 需要的工作量
- 风险和缓解措施

## 合规性检查
- [ ] 符合 12-Factor 原则
- [ ] 通过架构评审
- [ ] 更新相关文档
```

---

## 🔧 架构演进路线

### 已完成 (Phase 1-2)
- ✅ 基础架构搭建
- ✅ 配置与日志云端化
- ✅ 数据库架构演进
- ✅ MCP 工具集成

### 进行中 (Phase 3-4)
- 🔄 文件存储抽象层
- 🔄 可观测性增强
- 🔄 代码库重构
- 🔄 Skill Runtime Core 外部化与高复用边界收敛

### 规划中 (Future)
- ⏳ 层级记忆系统
- ⏳ 微服务拆分探索
- ⏳ 分布式部署支持

详见：[执行计划总览](../plans/INDEX.md)

---

## 📚 相关资源

### 内部文档
- [执行计划](../plans/INDEX.md) - 架构演进任务追踪
- [使用指南](../guides/) - 开发和使用规范
- [Skill Runtime Reuse Guide](../guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md) - 如何在其他同栈项目中复用
- [API 文档](../api/) - 接口定义

### 外部资源
- [12-Factor App](https://12factor.net/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [React 文档](https://react.dev/)
- [MCP 规范](https://modelcontextprotocol.io/)

---

## 🤝 贡献指南

### 提交架构决策
1. 创建 ADR 文档（使用上述模板）
2. 发起架构评审讨论
3. 获得批准后合并到主分支
4. 在相关文档中更新引用

### 更新架构文档
1. 确保代码与文档同步
2. 更新架构图和示例
3. 添加版本和日期标识

---

**最后更新**: 2026-03-24  
**维护者**: Yue Project Team

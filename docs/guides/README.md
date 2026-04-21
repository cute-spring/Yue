# Yue Project Guides - 使用指南中心

本目录包含面向不同角色的详细使用指南，帮助你快速上手 Yue AI 助手的各项功能。

---

## 📚 指南分类

### 👤 最终用户指南 ([user/](user/))

面向日常使用 Yue AI 助手的最终用户，提供功能使用说明和最佳实践。

| 文档 | 说明 |
|------|------|
| **Chat Usage Guide** | 聊天交互指南（待创建）- 掌握高效对话技巧 |
| **MCP Usage Guide** | MCP 工具使用指南（待创建）- 学习使用外部工具 |
| **Multi-modal Guide** | 多模态功能指南（待创建）- 图片问答与文件处理 |

#### 快速开始
1. 查看 [FEATURES.md](../overview/FEATURES.md) 了解完整功能列表
2. 参考 [CONFIGURATION.md](developer/CONFIGURATION.md) 完成环境配置
3. 如需理解 Yue 的技能边界，请阅读 [Yue Skill Strategy](../research/skills_gap_comparison_and_roadmap_20260421.md)

---

### 👨‍💻 开发者指南 ([developer/](developer/))

面向开发者和贡献者，提供开发环境搭建、测试、部署等技术文档。

| 文档 | 说明 |
|------|------|
| **[CONFIGURATION.md](developer/CONFIGURATION.md)** | 开发环境配置指南 |
| **[TESTING.md](developer/TESTING.md)** | 测试框架与执行指南 |
| **[Azure OpenAI Intranet Config](developer/Azure_OpenAI_Intranet_Config.md)** | 企业内网 Azure OpenAI 配置 |
| **[UI Design Guidelines](developer/UI_DESIGN_GUIDELINES.md)** | UI 设计规范与最佳实践 |
| **Deployment Guide** | 部署指南（待创建） |
| **API Development Guide** | API 开发指南（待创建） |

#### 开发流程
1. 阅读 [CONFIGURATION.md](developer/CONFIGURATION.md) 搭建开发环境
2. 查看 [TESTING.md](developer/TESTING.md) 了解测试规范
3. 参考 [plans/INDEX.md](../plans/INDEX.md) 了解当前开发任务
4. 遵循 [UI Design Guidelines](developer/UI_DESIGN_GUIDELINES.md) 进行界面开发

---

### 🔧 管理员指南 ([admin/](admin/))

面向系统管理员，提供配置管理、权限控制、运维监控等文档。

| 文档 | 说明 |
|------|------|
| **Document Access Control** | 文档访问控制配置（待创建） |
| **User Management** | 用户管理指南（待创建） |
| **Backup & Recovery** | 备份与恢复策略（待创建） |
| **Monitoring & Alerting** | 监控与告警配置（待创建） |
| **Performance Tuning** | 性能调优指南（待创建） |

#### 运维职责
- 配置和维护文档访问控制列表
- 管理用户权限和角色分配
- 定期备份系统数据和配置
- 监控系统性能和资源使用

---

## 🎯 按场景查找指南

### 我想...

**开始使用 Yue**
1. [配置开发环境](developer/CONFIGURATION.md)
2. [了解功能特性](../overview/FEATURES.md)
3. [理解 Skill 边界与定位](../research/skills_gap_comparison_and_roadmap_20260421.md)

**开发新功能**
1. 查看 [执行计划总览](../plans/INDEX.md)
2. 阅读 [测试指南](developer/TESTING.md)
3. 遵循 [UI 设计规范](developer/UI_DESIGN_GUIDELINES.md)

**配置企业部署**
1. [Azure OpenAI 内网配置](developer/Azure_OpenAI_Intranet_Config.md)
2. 文档访问控制（待创建）
3. 性能调优（待创建）

**排查问题**
1. 查看 [RCA 文档](../rca/) - 根因分析
2. 参考 [测试指南](developer/TESTING.md) - 复现问题
3. 阅读 [架构文档](../architecture/) - 理解系统

---

## 📝 指南编写规范

### 文档结构建议
```markdown
# 标题

## 简介
简要说明本文档的目的和适用范围。

## 前置条件
列出阅读本文档前需要满足的条件或已完成的配置。

## 步骤说明
1. 第一步...
2. 第二步...
   - 子步骤...
   - 代码示例...
3. 第三步...

## 验证方法
如何确认配置或功能已正确完成。

## 常见问题
FAQ 和故障排查建议。

## 相关文档
链接到相关的指南或参考文档。
```

### 代码示例规范
- 使用具体的文件路径（相对路径）
- 包含必要的注释说明关键步骤
- 提供完整的命令和预期输出

### 截图使用
- 仅在必要时使用截图
- 添加清晰的标注和说明
- 使用统一的命名：`<场景>-<步骤>.png`

---

## 🔄 维护与更新

### 更新频率
- **用户指南**: 功能更新时同步更新
- **开发者指南**: 架构变更时立即更新
- **管理员指南**: 配置变更时及时更新

### 反馈渠道
发现文档问题或有改进建议时：
1. 在对应文档下添加评论
2. 提交文档更新 PR
3. 在项目会议中提出

---

## 🔗 相关链接

- [项目总览](../README.md)
- [功能特性](../overview/FEATURES.md)
- [执行计划](../plans/INDEX.md)
- [架构设计](../architecture/)
- [API 文档](../api/)

---

**最后更新**: 2026-03-24  
**维护者**: Yue Project Team

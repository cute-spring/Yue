# Voice Input Release Checklist

**文档状态**：待验收  
**创建日期**：2026-03-25  
**适用范围**：`Azure Speech Service + Browser Speech 兜底` 语音输入方案

---

## 发布前检查

- [ ] 配置验收：至少使用一组真实 Azure Speech 配置，在 Agent 页面完成 `Test Azure STT`，确认 Token 获取成功，聊天页可正常录音并转写。
- [ ] 回退验收：人为制造 Azure 不可用场景，确认聊天页会自动回退到 Browser，并显示正确的 Provider / Fallback 提示。
- [ ] 权限验收：验证首次麦克风授权、拒绝授权、重新授权后的错误提示与恢复流程。
- [ ] 浏览器验收：至少覆盖目标浏览器组合，重点验证 Chrome、Edge、Safari 的可用性差异。
- [ ] 脱敏验收：检查 `/api/agents` 及相关配置接口返回值，确认不会向前端返回 Azure API Key 明文。
- [ ] 保存验收：验证新建 Agent、编辑 Agent、保留旧 Key、空白保存不覆盖已有 Key 等路径。
- [ ] 交互验收：验证录音中、处理中、取消录音、发送前停止录音、切换 Agent 时的状态切换。
- [ ] 回归验收：确认文本输入、图片上传、TTS、普通聊天流程未被语音输入改动影响。
- [ ] 自动化回归：执行 `cd frontend && npx playwright test e2e/voice-input.spec.ts`，确认 Browser、Azure、Azure 回退 Browser 三条语音链路全通过。
- [ ] 质量门禁：执行项目根目录 `./check.sh`，确认语音输入 Playwright 回归已纳入正式门禁并通过。
- [ ] 监控准备：确认后端能记录 Azure Token/Test 失败原因，便于线上排查。
- [ ] 文档确认：部署文档中补齐 Azure Speech 配置项、浏览器要求，以及 Browser Fallback 行为说明。

---

## 发布结论

- [ ] 允许发布
- [ ] 需要补充修复后再发布

**备注**：

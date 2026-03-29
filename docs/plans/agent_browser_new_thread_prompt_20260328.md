# Agent Browser New Thread Prompt (2026-03-28)

Copy the prompt below into a brand new thread:

```text
请继续推进 Yue 当前分支上的 agent-browser mutation continuity work。

这是延续当前分支工作的增量开发，不是重新设计。请直接基于现有代码、现有文档、现有测试和现有实现继续推进。

重要要求：
- 不要重新做大范围分析，直接在当前基线上继续
- 兼容性优先，不要大重写
- 不要引入 subagent / delegation
- browser 必须继续走 Yue 平台 tool boundary，不允许 skill-owned browser runtime
- 不要引入完整 browser persistence subsystem、登录态管理、CAPTCHA、autonomous browser workflows
- 先完成当前这一轮目标，再补必要测试并跑相关测试修复失败
- 完成后请汇报：改了哪些文件、做了哪些 contract/runtime 变更、跑了哪些测试、结果如何、剩余风险是什么

开始前请先阅读并严格参考：
1. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_plan_20260327.md
2. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_package_contract_handoff_20260328.md
3. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_phase2_completion_summary_20260328.md
4. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_mutation_continuity_plan_20260328.md
5. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_handoff_20260328.md
6. /Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/agent_browser_continuity_resolver_plan_20260328.md

当前基线状态：
- package-first skill contract 已完成，并兼容 legacy markdown skill
- tool-backed action descriptor / preflight / approval / runtime lifecycle 已完成
- chat runtime 已支持 requested_action、approval resume、skill.action.* SSE、event persistence、action_states
- browser builtin family 已建立，并有最小真实执行：
  - browser_open
  - browser_snapshot
  - browser_screenshot
  - browser_press
  - browser_click
  - browser_type
- authoritative target path 已建立：
  - snapshot-minted element_ref
  - binding_source / binding_session_id / binding_tab_id / binding_url / binding_dom_version / active_dom_version
- continuity metadata 已建立：
  - browser_continuity
  - browser_continuity_resolution
  - browser_continuity_resolver
- BrowserContinuityResolver interface + DefaultBrowserContinuityResolver(no-op) + ExplicitContextBrowserContinuityResolver 已接入
- resolved_context metadata contract 已接入，并已透传到 preflight / requested_action / preflight event / action details
- requested_action runtime 已能从 resolved_context 补齐缺失的 session_id / tab_id / element_ref
- browser_click / browser_type builtin boundary 已能识别 continuity candidate，但在无 restore backend 时会明确拒绝
- BrowserContinuityLookupBackend seam 已接入，但默认实现仍是 no-op / not_configured
- 当前 mutation 仍然是 single-use URL-scoped，不是 resumable continuity

本轮唯一优先目标：
沿现有 continuity resolver / lookup seam，做第一版 adapter-owned storage-backed lookup contract 落地：
在不引入真实 browser restore / persistence subsystem 的前提下，让 resolver 能通过 BrowserContinuityLookupBackend 的非 no-op 实现，在“显式上下文不完整但已有可查 authoritative continuity records”的情况下产出 resolved_context。

本轮必须遵守的硬约束：
1. 本轮只允许实现：
   - BrowserContinuityLookupBackend 的第一版 adapter 实现
   - lookup request/result contract 的最小落地消费
   - resolver 通过 lookup seam 产出 resolved_context
   - preflight / requested_action metadata 与现有 arg hydration 的兼容补强
   - 测试
2. 本轮不允许实现：
   - 真实 browser session persistence
   - browser process / tab restore
   - 登录态管理
   - CAPTCHA
   - 长链 autonomous workflows
   - selector fallback
   - browser-specific 大 UI 重做
3. 如果某一步会自然滑向真实 browser session backend / restore backend，请停在 lookup contract / resolver 层

推荐优先查看这些文件：
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/models.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/actions.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_tools.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/mcp/builtin/browser.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/policy.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/chat_requested_action_flow.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_foundation_unit.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_chat_unit.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_chat_requested_action_helpers_unit.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_chat_stream_runner_unit.py
- /Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_browser_builtin_contract.py

本轮建议交付物：
1. 新增一个最小可替换的 Yue adapter lookup backend，接到 BrowserContinuityLookupBackend seam 上
2. 保持 resolved_context shape 稳定，包括至少：
   - resolved_context_id
   - session_id
   - tab_id
   - element_ref
   - resolution_mode
   - resolution_source
   - resolved_target_kind
3. lookup result / resolver status 至少覆盖：
   - not_configured
   - not_found
   - resolved
   - blocked
4. preflight / requested_action metadata 继续稳定透传 resolver 输出
5. 确保现有 resolved_context -> tool_args hydration 不被破坏
6. 增加针对 default no-op backend 与 adapter lookup backend 的 backend tests

测试要求：
1. 新增测试优先覆盖：
   - default no-op lookup backend 的兼容路径
   - adapter lookup backend 的 resolved 或 not_found 路径
   - requested_action metadata 透传
   - resolved_context -> tool_args hydration 不被 lookup seam 破坏
   - continuity lookup contract 不破坏现有 lifecycle
2. 跑相关 backend tests
3. 只有前端确实有轻量 contract 展示改动时，再跑对应 frontend test

完成后请汇报：
- 改了哪些文件
- continuity resolver / lookup backend 支持了哪些内容
- 哪些内容被设计成 future kernel-friendly
- 哪些内容仍明确留在 Yue adapter
- 做了哪些兼容处理
- 跑了哪些测试，结果如何
- 剩余风险是什么
```

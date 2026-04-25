# Skill Runtime Core Stage A + B Task List

**Date**: 2026-04-24

## 背景

当前 `Skill Runtime Core` 的方向、复用指南、以及运行机制说明已经具备，但还缺一份可以直接拿来推进实现的任务清单。

本文件只覆盖：

- **Stage A: Define Core Boundary**
- **Stage B: Remove Global Runtime Construction From Critical Paths**

目标不是一次性完成 full externalization，而是先把“边界”和“runtime construction path”这两件最关键的事情落实为代码事实。

---

## 目标

本轮执行完成后，应当达到以下结果：

1. 团队可以明确知道哪些文件属于：
   - `reusable now`
   - `transitional`
   - `Yue-only`
2. runtime 构造路径主要通过显式 context / provider / bootstrap 访问，而不是继续依赖模块级默认单例
3. 后续 Stage C-D-E 可以在不重新打开边界争论的前提下继续推进
4. 另一个同栈项目可以按“复制式接入”开始接入，而不会误读当前边界

---

## 不在本轮范围

本轮不做这些事：

1. 不做完整 `skill_runtime_core` 包发布
2. 不做 frontend 接入调整
3. 不重写 chat runtime 主路径
4. 不做 skill group / visibility 的彻底抽象完成
5. 不引入新的用户可见 API 形态变化

---

## 执行原则

1. **先边界，后抽离**
   先把文件角色和 runtime path 标清楚，再做后续提取。

2. **兼容优先**
   `skill_service.py` 的兼容壳层这一轮可以继续保留，但要进一步缩小它的职责。

3. **显式优于隐式**
   新代码优先通过 runtime context、provider、bootstrap spec、host adapter 访问依赖。

4. **复制式接入优先于理想化包式接入**
   当前阶段先让同栈项目能低风险复制成功，再继续往最终独立包推进。

---

## 任务拆解总览

### Stage A

- A1. 建立核心边界清单
- A2. 标注每个关键文件的角色
- A3. 产出 boundary manifest 初版
- A4. 建立 boundary regression 检查

### Stage B

- B1. 收敛 runtime construction 入口
- B2. 继续缩减 `skill_service.py` 的隐式中心化职责
- B3. 让 API / startup 路径优先走显式 runtime container
- B4. 补齐以 runtime container 为中心的回归验证

---

## Stage A 任务清单

### A1. 建立核心边界清单

**目标**

明确当前技能系统中，哪些文件已经可以看作未来 core 候选，哪些只是过渡层，哪些必须保留在 Yue adapter 层。

**建议修改文件**

- [skill_runtime_core_externalization_plan_20260423.md](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_runtime_core_externalization_plan_20260423.md)
- 新增 boundary manifest 文件

**执行动作**

1. 为 `backend/app/services/skills/` 下的关键文件打上角色标签：
   - `reusable_now`
   - `reusable_after_cleanup`
   - `transitional_only`
   - `yue_only`
2. 对 `skill_service.py` 单独标注：
   - 当前允许复制
   - 但不属于未来纯 core 包
3. 对 `api/skills.py`、`api/skill_imports.py`、`api/skill_groups.py` 标注：
   - 当前可复制式复用
   - 未来应由 host-local route strategy 取代

**产出物**

- 一份 machine-readable 或至少结构清晰的 boundary manifest

**完成标准**

- 文档和代码读者不再需要猜“这个文件到底算不算 core”

---

### A2. 标注每个关键文件的角色

**目标**

在代码附近留下最小但明确的角色说明，避免后续改动时误把 Yue-only 文件继续往 core 里拖。

**建议修改文件**

- [skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
- [bootstrap.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py)
- [host_adapters.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/host_adapters.py)
- [runtime_seams.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/runtime_seams.py)
- [routing.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/routing.py)

**执行动作**

1. 在文件头部或关键 dataclass / builder 入口处增加简短注释，说明：
   - 是否是 core candidate
   - 是否是 transitional shell
   - 是否依赖 Yue 宿主语义
2. 对最容易误解的入口增加说明：
   - `build_skill_runtime(...)`
   - `mount_skill_runtime_routes(...)`
   - `register_stage4_lite_host_runtime_adapter_bundle(...)`
   - `get_stage4_lite_runtime_context()`

**完成标准**

- 新接手的人打开关键文件时，能在 30 秒内判断它属于哪一层

---

### A3. 产出 boundary manifest 初版

**目标**

把 Stage A 的边界变成一份可以被测试或脚本消费的产物，而不是只存在于 prose 文档里。

**建议新增文件**

- `backend/app/services/skills/boundary_manifest.py`
  或
- `backend/app/services/skills/boundary_manifest.json`

**建议结构**

```python
BOUNDARY_MANIFEST = {
    "reusable_now": [...],
    "reusable_after_cleanup": [...],
    "transitional_only": [...],
    "yue_only": [...],
}
```

**执行动作**

1. 首版先只覆盖关键文件，不要求一次覆盖全目录
2. 把文档中的边界判断落到 manifest 中
3. 在 externalization plan 里引用它

**完成标准**

- 至少核心入口和高风险文件都进入 manifest

---

### A4. 建立 boundary regression 检查

**目标**

防止后续改动重新把 Yue 宿主依赖拉回 core 候选层。

**建议新增测试**

- `backend/tests/test_skill_runtime_boundary_manifest_unit.py`

**执行动作**

1. 校验 manifest 中列出的文件真实存在
2. 校验 `reusable_now` / `reusable_after_cleanup` 文件不包含明显不该出现的 Yue-only 引用
3. 第一版允许用轻量字符串断言，不要求做 AST 级依赖图

**第一版最低断言建议**

1. `reusable_now` 文件不得 import：
   - `app.services.agent_store`
   - `app.services.config_service`
   - `app.services.skill_group_store`
   - `app.api.*`
2. `transitional_only` 可以保留这些依赖，但必须被显式列入 manifest

**完成标准**

- CI 至少能发现边界退化的明显回归

---

## Stage B 任务清单

### B1. 收敛 runtime construction 入口

**目标**

减少“到处都能偷偷构造 runtime”的情况，把 runtime 创建路径集中到 bootstrap / provider / context 体系。

**重点文件**

- [skill_service.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skill_service.py)
- [bootstrap.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/services/skills/bootstrap.py)

**执行动作**

1. 检查当前 runtime 单例初始化点
2. 区分：
   - 显式 runtime builder
   - 兼容默认单例
3. 让新路径默认经过：
   - `build_skill_runtime(...)`
   - runtime providers
   - runtime context factory
4. 保留 legacy-compatible fallback，但让其退到第二优先级

**完成标准**

- 团队可以明确回答“runtime 是在哪一个主入口被构造的”

---

### B2. 继续缩减 `skill_service.py` 的隐式中心化职责

**目标**

让 `skill_service.py` 从“隐式全局中心”逐步退化成“过渡兼容壳层 + runtime access facade”。

**执行动作**

1. 识别它当前承担的职责：
   - singleton holder
   - host adapter registration
   - compatibility wrapper
   - runtime context access
2. 对每个职责做判断：
   - 应继续保留
   - 应委托给 bootstrap
   - 应委托给 host adapter layer
3. 优先把真正的 runtime construction 逻辑继续下沉到 `bootstrap.py`

**完成标准**

- `skill_service.py` 不再是“默认新功能首选入口”
- 新功能若要接 runtime，优先引用 bootstrap / context / provider API

---

### B3. 让 API / startup 路径优先走显式 runtime container

**目标**

把最关键的运行时路径进一步统一到显式 runtime container / context 之上。

**重点文件**

- [main.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/main.py)
- [skills.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skills.py)
- [skill_imports.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/app/api/skill_imports.py)

**执行动作**

1. 检查是否还有关键路径直接依赖模块级别 alias
2. 让 startup、skills API、skill imports API 默认都从 runtime context 取对象
3. 明确保留哪些 compatibility shims，以及保留原因
4. 若某处仍必须保留旧 seam，在注释里说明它是 transitional

**完成标准**

- 核心 API 和 startup 主路径都能通过 runtime context 解释清楚

---

### B4. 补齐以 runtime container 为中心的回归验证

**目标**

确保 Stage B 之后，测试仍然主要验证“显式 runtime path 是正确的”，而不是继续围着 monkeypatch 全局变量转。

**建议重点测试**

- [test_skill_service_runtime_context_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_service_runtime_context_unit.py)
- [test_skill_runtime_bootstrap_unit.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_skill_runtime_bootstrap_unit.py)
- [test_api_skills.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skills.py)
- [test_api_skill_imports.py](/Users/gavinzhang/ws-ai-recharge-2026/Yue/backend/tests/test_api_skill_imports.py)
- `import_gate_lifespan_smoke`

**执行动作**

1. 新增或补强以下断言：
   - runtime context 是主路径
   - provider override 生效
   - host adapter override 生效
   - route strategy / bootstrap spec 行为符合预期
2. 保留少量兼容测试，但不要继续扩大全局 monkeypatch 用例

**完成标准**

- regression suite 的主要覆盖点从“兼容壳层是否还能 patch”转向“runtime container 是否正确工作”

---

## 建议执行顺序

按这个顺序推进最稳：

1. A1
2. A3
3. A4
4. A2
5. B1
6. B2
7. B3
8. B4

原因：

1. 先把边界说清楚
2. 再把边界写成产物
3. 然后用测试锁住边界
4. 最后再改运行时主路径

---

## 每项任务的提交粒度建议

建议不要把 Stage A + B 一次性做完再提交，而是拆成 4 个小阶段：

1. `A1 + A3`
   - 文档与 manifest 初版
2. `A4 + A2`
   - boundary regression + 关键文件角色标注
3. `B1 + B2`
   - runtime construction 收敛
4. `B3 + B4`
   - API/startup 主路径收敛 + regression 补强

这样最容易 review，也最容易回滚。

---

## 每阶段的验证命令

### Stage A 完成后

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_skill_runtime_boundary_manifest_unit.py
```

### Stage B 完成后

```bash
cd backend
PYTHONPATH=. pytest -q \
  tests/test_skill_runtime_bootstrap_unit.py \
  tests/test_skill_service_runtime_context_unit.py \
  tests/test_skill_runtime_seams_unit.py \
  tests/test_api_skills.py \
  tests/test_api_skill_imports.py \
  tests/test_import_gate_lifespan_smoke.py
```

如果本轮改动波及 routing，可追加：

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_skill_runtime_integration.py
```

---

## 风险与缓解

### 风险 1：过早删除兼容壳层

**表现**

- 老测试大面积失败
- 运行路径解释不清

**缓解**

- 保留兼容层，但显式标记为 `transitional_only`

### 风险 2：边界 manifest 过度理想化

**表现**

- manifest 写得很干净，但与真实代码不一致

**缓解**

- 首版只要求真实、可验证，不要求一次到位

### 风险 3：API 路径仍然偷偷走旧单例

**表现**

- 文档说已 containerized，代码实际还是 alias path

**缓解**

- 用 runtime-context-first 的测试把主路径锁住

---

## DoD

Stage A + B 可以视为完成，当且仅当：

1. 已存在明确的 boundary manifest
2. 核心文件已被分类为 `reusable_now` / `reusable_after_cleanup` / `transitional_only` / `yue_only`
3. `skill_service.py` 被明确收敛为过渡壳层，而不是继续承担隐式全局中心职责
4. startup 与关键 skill API 主路径都可以通过 runtime context / bootstrap container 解释
5. regression suite 已覆盖新的边界与显式 runtime path
6. 文档与代码对“今天能怎么复用”这件事不再自相矛盾

---

## 相关文档

- [Skill Runtime Core Externalization Plan](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_runtime_core_externalization_plan_20260423.md)
- [Skill Runtime Core Phase 1 Refactor Plan](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/plans/skill_runtime_core_phase1_refactor_plan_20260423.md)
- [Skill Runtime Core 复用与迁移指南](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/guides/developer/SKILL_RUNTIME_CORE_REUSE_GUIDE.md)
- [Skill Runtime 当前运行机制说明](/Users/gavinzhang/ws-ai-recharge-2026/Yue/docs/architecture/Skill_Runtime_Current_Operation.md)

# Logging & Configuration Evolution Plan (日志与配置云端演进计划)

## 1. 配置文件 (Config) 的演进

### 1.1 核心挑战（结合现有代码 `ConfigService`）
*   **当前代码现状 (`backend/app/services/config_service.py`)**：
    *   目前系统使用了一个非常强大的 `ConfigService`，它已经具备了**“环境变量 > JSON 文件 (`global_config.json`)”**的优先级回退策略。
    *   这说明系统**已经完成了一半的云端化准备**！这非常棒！
*   **云端多实例挑战**：
    *   **配置漂移（脑裂）**：多台服务器如果各自读本地的 `global_config.json`，极易出现某些机器配置更新了，而其他机器没更新的情况。
    *   **重启成本**：虽然现在支持 JSON 动态加载，但在分布式环境下，你无法同时向 10 台机器下发 JSON 文件。
    *   **敏感信息泄露**：将 API Keys 等敏感信息保存在 `global_config.json` 中并随容器分发是非常危险的。

### 1.2 演进方案：彻底的“环境化”与“动态中心化”

#### Phase 1: 强化环境变量注入 (Environment Variables)
*   **现状评估**：当前 `ConfigService.get_llm_config()` 中已经硬编码了诸如 `os.getenv("LLM_PROVIDER")` 的逻辑。
*   **演进动作**：
    *   **无需重构** `ConfigService` 的基础架构。
    *   **规范化配置管理**：在云端部署（如 Docker/K8s）时，**禁止挂载** `global_config.json`，强制要求所有配置（尤其是数据库连接、S3 密钥等新增配置）必须通过操作系统的环境变量（`os.environ`）注入。
    *   **引入 `pydantic-settings` (推荐)**：未来可以考虑使用 `pydantic.BaseSettings` 替换手写的 `ConfigService` 解析逻辑，它能更健壮地处理类型转换和环境变量映射。

#### Phase 2: 动态配置中心 (Centralized Configuration)
*   随着系统变大，建议引入专业的配置中心（如 **Nacos, Apollo**, 或云原生的 **AWS Parameter Store / Secrets Manager**）。
*   应用启动时，只需知道配置中心的地址和鉴权 Token，核心业务配置全部从远端拉取。
*   **红利**：支持配置热更新（Hot Reload）。运营人员在后台修改了 LLM 的 Prompt 模板或限流阈值，所有业务节点可实时生效，无需重启。

---

## 2. 日志 (Logs) 的演进

### 2.1 核心挑战（结合现有代码 `observability.py`）
*   **当前代码现状 (`backend/app/observability.py`)**：
    *   目前的日志系统已经非常现代化！已经通过 `setup_logging()` 配置了 `StreamHandler`，并且引入了 `ContextVar` 来传递 `trace_id` (`X-Request-Id`)。
    *   **这意味着在日志层面，系统几乎不需要做“破除写文件”的改造，因为它本来就在正确地向 `stdout` 输出！**
*   **云端多实例挑战**：
    *   目前的挑战不在于“应用怎么写日志”，而在于**“写出来的日志去哪了”**。
    *   如果部署了 5 台服务器，发生报错时，开发人员需要逐台 SSH 登录去 `docker logs` 找日志，效率极低。

### 2.2 演进方案：流式日志与集中式收集

#### 保持现状：日志即事件流 (Logs as Event Streams)
*   继续保持当前 `observability.py` 中的 `StreamHandler` 设计。这是完全符合 12-Factor App 规范的。
*   **小优化**：在生产环境中，建议将 `Formatter` 从纯文本（Plain Text）改为 **JSON 格式（如使用 `python-json-logger` 或 `structlog`）**。这样包含 `trace_id` 的日志在发往云端时，更容易被 ElasticSearch 等引擎结构化解析。

#### 基础设施层收集架构
将日志管理的职责从“应用层”剥离到“基础设施层”：
1.  **收集 (Collect)**：通过容器引擎（如 Docker 的 json-file 驱动）或守护进程（如 Fluentd, Filebeat, Logstash）自动捕获应用打印出的 `stdout/stderr` 流。
2.  **传输与解析 (Ship & Parse)**：守护进程将这些日志流加上机器 IP、时间戳等元数据，传输到消息队列（如 Kafka）或直接发往日志仓库。
3.  **集中检索 (Store & Query)**：日志最终落入集中式的日志平台（如 **ELK 栈** - Elasticsearch, Logstash, Kibana，或是云厂商的托管服务如 **AWS CloudWatch, 阿里云 SLS**）。

#### 架构红利
*   开发人员只需登录统一的 Kibana/SLS 面板，通过 `trace_id` 即可一键搜索出跨越所有服务器的完整请求调用链日志。
*   无论底层容器如何销毁重启，日志都不会丢失。
# Database Evolution Plan (数据库云端演进计划)

## 1. 核心挑战与背景
目前系统在本地模式下使用了 `~/.yue/data/database/yue.db`。SQLite 零配置、轻量级，是单机客户端的最佳选择。然而，随着系统演进为“服务器多人部署”架构，SQLite 暴露出了以下瓶颈：
*   **并发写入瓶颈**：SQLite 是文件型锁（File-level locking），在多台服务器（多个应用实例）高并发写入时，极易产生 `Database is locked` 错误。
*   **无状态部署冲突**：在 Kubernetes 或 Docker 等容器化环境中，如果容器漂移或重启，本地 SQLite 数据会丢失。如果强制挂载共享外部卷（如 EFS/NFS），SQLite 的性能和锁机制会进一步恶化。

## 2. 演进目标
实现**数据库方言（Dialect）与底层存储介质的彻底解耦**。业务逻辑代码实现 "Write Once, Run Anywhere"（本地跑 SQLite，云端跑 PostgreSQL/MySQL），而无需修改任何核心业务逻辑。

## 3. 架构演进方案：引入 ORM 层

### 3.1 核心策略：ORM (Object-Relational Mapping) 解耦
*   **禁止原生 SQL**：应用代码中不得出现与特定数据库绑定的原生 SQL（如特定数据库才有的日期格式化函数等）。
*   **模型驱动**：所有的数据表结构、关联关系必须通过 ORM（如 Python 下的 `SQLAlchemy` 或 Node.js 下的 `Prisma`）进行定义。

### 3.2 环境适配连接策略
通过配置文件或环境变量 `DATABASE_URL` 来动态决定底层驱动：

*   **本地开发/单机环境 (ENV=local)**:
    *   `DATABASE_URL="sqlite:////Users/gavin/.yue/data/database/yue.db"`
    *   ORM 引擎自动将对象操作翻译为 SQLite 方言，写入本地磁盘。

*   **生产环境/多人服务器 (ENV=production)**:
    *   `DATABASE_URL="postgresql://user:password@db-host:5432/yuedb"` (或 MySQL)
    *   ORM 引擎自动切换为 PostgreSQL 方言，连接到托管的云数据库（如 AWS RDS, 阿里云 RDS）。

## 4. 实施路线图 (Roadmap)

1.  **Phase 1: 引入并集成 ORM 框架**
    *   选型：如果是 Python 后端，推荐 `SQLAlchemy` 配合 `Alembic`；如果是 Node，推荐 `Prisma`。
    *   将现有的 SQLite 表结构转换为 ORM Model 类。
2.  **Phase 2: 数据访问层 (DAO) 重构**
    *   重写所有的数据库查询与写入逻辑，全部替换为 ORM API。
    *   确保本地 SQLite 依然能通过 ORM 完美运行，通过所有单元测试。
3.  **Phase 3: 数据库迁移工具 (Migration Tooling)**
    *   集成如 `Alembic` 或 `Prisma Migrate`。
    *   建立数据库 Schema 版本控制机制。这是在生产环境安全更新表结构（如新增字段）的唯一标准路径。
## 5. 演进成果与架构收益 (2026-03-21 总结)

本次重构将底层的原生 `sqlite3` 替换为 `SQLAlchemy + Alembic`，是一次**完全的后端架构解耦与重构（无感替换）**。在业务功能和界面交互上，用户不会察觉到任何不同，但从系统工程和未来发展的角度来看，达成了以下几个核心收益：

### 5.1 突破并发瓶颈 (高并发不锁库)
*   **之前**：原生的 SQLite 经常在多线程或多个工具同时写入（例如高频写入 Tool Calls 状态和流式回复时）遭遇 `database is locked` 错误。
*   **现在**：通过 SQLAlchemy 的连接池和正确的 `Session` 会话生命周期管理（以及 `autocommit=False`），多请求并发访问和写入数据的安全性大幅提升，聊天响应过程中的状态记录将更加稳定。

### 5.2 避免了未来的数据丢失风险 (Alembic 迁移)
*   **之前**：如果我们在下个版本给 Message 表加个字段（比如增加一个 `has_attachment` 标志），代码启动时运行 `CREATE TABLE IF NOT EXISTS` 是无效的，必须手动写 SQL `ALTER TABLE`，搞不好还要删库重来，很容易导致本地辛苦攒的 Prompt 和历史记录丢失。
*   **现在**：我们引入了 `Alembic`。之后任何表结构的改动，都会自动生成一个 `.py` 迁移脚本（类似于增量补丁）。系统会自动按顺序无损升级表结构，历史对话和 Agent 数据永远安全。

### 5.3 云端无状态部署就绪 (随时切换云数据库)
*   **之前**：项目被死死绑定在项目目录下的 `data/yue.db` 文件上。如果想把 Yue 部署到云端或者 Docker 容器里，由于容器是无状态的，一重启本地文件就没了。
*   **现在**：我们在 `backend/app/core/database.py` 预留了 `DATABASE_URL` 环境变量。这意味着，如果不改配置，它就是本地安全的 SQLite；但只要在云端加一行环境变量，它就能无缝切换到云端的 PostgreSQL 或 MySQL 数据库（完全符合 12-Factor App 架构中提倡的“后端服务挂载”原则）。

简而言之：**表面上风平浪静，但底层引擎已经从单机文件存储换成了工业级的混合动力引擎，彻底扫清了项目向云端扩展和团队协作开发的最后技术障碍。**
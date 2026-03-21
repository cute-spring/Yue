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
4.  **Phase 4: 多环境测试**
    *   在 CI/CD 流水中，分别连接 SQLite 和真实的 PostgreSQL 实例运行集成测试，确保 ORM 层没有引入方言兼容性 Bug。
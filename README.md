# Easy FastAPI — FastAPI 全栈脚手架 (1.0)

> 一条命令生成 FastAPI 全栈项目：后端（3 ORM × 认证 × Redis × 静态挂载）+ 前端（最小 pnpm monorepo 骨架 + OpenAPI SDK 自动生成）。

## 特性

- **双模式目录**：`backend-only`（纯 API）或 `fullstack`（`backend/` + `frontend/` monorepo）
- **三 ORM 可选**：Tortoise ORM / SQLAlchemy / SQLModel，统一 `DbSession` / `UserModelProtocol` / `ModelIntrospector` 协议
- **认证跨 ORM**：pwdlib (argon2 默认) + PyJWT，零 ORM 耦合
- **Redis 扩展**：override 覆盖 persistence，`enabled=false` 回退内存
- **前端骨架**：pnpm workspace monorepo，@hey-api/openapi-ts SDK 自动生成，用户在 `frontend/apps/` 自建前端应用
- **CLI 四命令**：`efa create` / `efa run` / `efa db {init,migrate,upgrade,sync}` / `efa gen`
- **可选依赖守卫**：缺包自动提示 `uv add <pkg>`
- **配置严格**：`easy-fastapi.yaml` + `ConfigLoader`，`extra='forbid'`，env overlay

## 安装

```bash
# 推荐：uv（安装 CLI 即自带 runtime）
uv tool install easy-fastapi-cli

# 或临时运行
uvx efa --help
```

## 快速开始

### 交互式创建（推荐新手）

```bash
efa create myapp
# 逐步选择：ORM、数据库方言、认证、Redis、前端等
cd myapp
```

### 非交互式创建

```bash
# 后端 + Tortoise + MySQL + 认证
efa create myapp --no-interactive \
  --project-name myapp --package-name myapp \
  --database --orm tortoise --db-dialect mysql --auth

# 全栈 + SQLAlchemy + PostgreSQL + 认证 + Redis + 前端
efa create myapp --no-interactive \
  --project-name myapp --package-name myapp \
  --frontend \
  --database --orm sqlalchemy --db-dialect postgres \
  --auth --redis

cd myapp
```

### 启动后端

```bash
efa run              # 生产模式
efa run --reload     # 开发热重载
efa run --port 8080  # 指定端口
```

访问 `http://localhost:8000/docs` 查看 Swagger 文档。

### 数据库操作

```bash
efa db init      # 初始化迁移配置（非幂等，仅首次）
efa db migrate   # 生成迁移文件
efa db upgrade   # 应用迁移
efa db sync      # 直接建表（开发用，无需迁移）
```

### 代码生成

```bash
efa gen          # 从 Model 生成 router/schema/service
efa gen --force  # 覆盖已有文件
```

### 前端骨架（fullstack 项目）

生成的 `frontend/` 是最小 pnpm monorepo 骨架：仅含 `packages/api-sdk`（OpenAPI 生成的 SDK）+ `apps/`（你自建应用的占位）。

```bash
cd frontend
pnpm install      # 安装依赖
pnpm sdk:gen      # 从后端 OpenAPI 生成 SDK（需先启动后端）
# 在 frontend/apps/ 下自行创建前端应用（React/Vue/任意）
```

## CLI 速查

| 命令 | 说明 |
|---|---|
| `efa create [TARGET] [OPTIONS]` | 创建项目（交互/非交互） |
| `efa run [--host] [--port] [--reload]` | 启动 uvicorn |
| `efa db init` | 初始化迁移配置 |
| `efa db migrate` | 生成迁移文件 |
| `efa db upgrade` | 应用迁移 |
| `efa db sync` | 直接建表 |
| `efa gen [--force]` | 生成 CRUD 代码 |

### `efa create` 常用选项

| 选项 | 说明 | 默认值 |
|---|---|---|
| `--no-interactive` | 跳过交互向导 | 交互模式 |
| `--project-name` | 项目名 | — |
| `--package-name` | Python 包名 | — |
| `--language` | 语言 (zh/en) | zh |
| `--database` | 启用数据库 | false |
| `--orm` | ORM (tortoise/sqlalchemy/sqlmodel) | — |
| `--db-dialect` | 数据库方言 (mysql/postgres/sqlite) | — |
| `--migration` | 启用迁移 | false |
| `--auth` | 启用认证 | false |
| `--redis` | 启用 Redis | false |
| `--frontend` | 启用前端 | false |
| `--static` | 启用静态文件挂载 | false |

## 扩展列表

| 扩展 | provide 的 service key | 配置 section |
|---|---|---|
| `orm.tortoise` | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `orm.sqlalchemy` | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `orm.sqlmodel` | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `auth` | `token_service`, `require` | `auth` |
| `redis` | `persistence` (override) | `redis` |
| `i18n` | `i18n` | `i18n` |
| `static` | — | `static` |

> 三 ORM 共享 ORM 无关的 `database` section。

## 配置

生成项目的 `easy-fastapi.yaml`：

```yaml
fastapi:
  root_path: ""

# 启用 ORM 后，读取通用 database 段（ORM 无关）
database:
  dialect: sqlite
  database: db.sqlite3
# auth:
#   secret: your-secret-key
#   access_expire_minutes: 1440
# redis:
#   url: redis://localhost:6379/0
```

环境变量覆盖规则：`EFA_<SECTION>__<FIELD>`（如 `EFA_EASY_FASTAPI__AUTH__SECRET=prod-key`）。

## 文档

- [快速上手](docs/quickstart.md)
- [CLI 参考](docs/cli.md)
- [扩展](docs/extensions.md)
- [架构](docs/architecture.md)
- [关键决策与约束](docs/DECISIONS.md)
- [0.x → 1.0 迁移指南](docs/migration/0.x-to-1.0.md)

## License

MIT

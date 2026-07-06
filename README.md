<p align="center">
  <img src="docs/assets/title.svg" alt="Easy FastAPI" width="520">
</p>
<h3 align="center">FastAPI 全栈脚手架</h3>

<p align="center">
  <em>一条命令生成 FastAPI 全栈项目：3 ORM × 认证 × Redis × 前端 SDK</em>
</p>
<p align="center">
  <a href="https://github.com/one-ccs/easy_fastapi/actions/workflows/ci.yaml">
    <img src="https://github.com/one-ccs/easy_fastapi/actions/workflows/ci.yaml/badge.svg" alt="CI">
  </a>
  <a href="https://pypi.org/project/easy-fastapi">
    <img src="https://img.shields.io/pypi/v/easy-fastapi?color=%2334D058&label=PyPI" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/easy-fastapi">
    <img src="https://img.shields.io/pypi/pyversions/easy-fastapi.svg?color=%2334D058" alt="Python">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT">
  </a>
</p>

<img src="docs/assets/demo.gif" alt="演示" style="max-width: 1024px; width: 100%; height: auto;">

## ✨ 特性

- **双模式目录**：`backend-only`（纯 API）或 `fullstack`（`backend/` + `frontend/` monorepo）
- **三 ORM 可选**：Tortoise ORM / SQLAlchemy / SQLModel，统一 `DbSession` / `UserModelProtocol` / `ModelIntrospector` 协议
- **认证跨 ORM**：pwdlib (argon2 默认) + PyJWT，零 ORM 耦合
- **Redis 扩展**：override 覆盖 persistence，`enabled=false` 回退内存
- **前端骨架**：pnpm workspace monorepo，@hey-api/openapi-ts SDK 自动生成，用户在 `frontend/apps/` 自建前端应用
- **CLI 四命令**：`efa create` / `efa run` / `efa db {init,migrate,upgrade,sync}` / `efa gen`
- **可选依赖守卫**：缺包自动提示 `uv add <pkg>`
- **配置严格**：`easy-fastapi.yaml` + `ConfigLoader`，`extra='forbid'`，env overlay

## 🚀 快速开始

### 安装

```bash
# 推荐：uv（安装 CLI 即自带 runtime）
uv tool install easy-fastapi-cli

# 或临时运行
uvx efa --help
```

### 30 秒体验

```bash
efa create myapp       # 交互式创建项目
cd myapp
uv sync
efa run --reload       # 启动开发服务器
```

访问 `http://localhost:8000/docs` 查看 Swagger 文档。

<details>
<summary>非交互式 / 全参数示例</summary>

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
```

</details>

## 📁 生成项目预览

```
myapp/
├── backend/
│   ├── app/
│   │   ├── main.py          # 入口：EasyFastAPI + use() 链
│   │   ├── models/          # 数据模型
│   │   ├── routers/         # 路由
│   │   └── schemas/         # Pydantic schema
│   ├── easy-fastapi.yaml    # 配置
│   └── pyproject.toml
└── frontend/                # fullstack 模式
    ├── packages/api-sdk/    # OpenAPI 自动生成 SDK
    └── apps/                # 你的前端应用
```

## ⌨️ CLI 速查

### 常用命令

| 命令 | 说明 |
|------|------|
| `efa create [TARGET] [OPTIONS]` | 创建项目（交互/非交互） |
| `efa run [--host] [--port] [--reload]` | 启动 uvicorn |
| `efa db init` | 初始化迁移配置 |
| `efa db migrate` | 生成迁移文件 |
| `efa db upgrade` | 应用迁移 |
| `efa db sync` | 直接建表（开发用） |
| `efa gen [--force]` | 从 Model 生成 CRUD 代码 |

### `efa create` 选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
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

## 🧩 扩展

| 扩展 | 说明 |
|------|------|
| `orm.tortoise` | Tortoise ORM 数据层 |
| `orm.sqlalchemy` | SQLAlchemy ORM 数据层 |
| `orm.sqlmodel` | SQLModel ORM 数据层 |
| `auth` | JWT + argon2 认证，零 ORM 耦合 |
| `redis` | Redis 持久化，`enabled=false` 回退内存 |
| `i18n` | 国际化 (gettext + contextvars) |
| `static` | 静态文件托管 |

> 三 ORM 共享 ORM 无关的 `database` 配置段。各扩展 service key 与配置细节见 [扩展文档](docs/extensions.md)。

## ⚙️ 配置

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

## 📖 文档

- [快速上手](docs/quickstart.md)
- [CLI 参考](docs/cli.md)
- [扩展](docs/extensions.md)
- [架构](docs/architecture.md)
- [0.x → 1.0 迁移指南](docs/migration/0.x-to-1.0.md)

## License

MIT

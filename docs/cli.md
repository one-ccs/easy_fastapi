# CLI 参考

Easy FastAPI 提供 `efa` 与 `easy_fastapi` 两个别名，等价使用。

## `efa create [TARGET] [OPTIONS]`

创建新项目。

### 参数

| 参数 | 说明 |
|---|---|
| `TARGET` | 目标目录路径。`.` 表示当前目录；其他名称表示目标目录必须不存在 |

### 选项

| 选项 | 说明 | 默认值 |
|---|---|---|
| `--interactive` / `--no-interactive` | 是否交互向导 | 交互模式 |
| `--project-name` | 项目名（必填，非交互模式） | — |
| `--package-name` | Python 包名（必填，非交互模式） | — |
| `--language` | 语言 (zh/en)，影响前端 i18n 默认 | zh |
| `--database` | 启用数据库 | false |
| `--orm` | ORM 类型：tortoise / sqlalchemy / sqlmodel | — |
| `--db-dialect` | 数据库方言：mysql / postgres / sqlite | — |
| `--migration` | 启用迁移 | false |
| `--auth` | 启用认证 | false |
| `--redis` | 启用 Redis | false |
| `--static` | 启用静态文件挂载 | false |
| `--frontend` | 启用前端 | false |

### 校验铁律

- **B**：`database=True` 必须指定 `orm` + `db_dialect`
- **C**：`auth=True` 需要 `database=True`；`migration=True` 需要 `orm`
- 违反抛 `ConfigError`

### 示例

```bash
# 最小后端
efa create api --no-interactive --project-name api --package-name api

# 全栈 + 认证
efa create app --no-interactive \
  --project-name app --package-name app \
  --frontend --database --orm tortoise --db-dialect mysql --auth

# 在当前目录创建
efa create . --no-interactive --project-name myproj --package-name myproj
```

## `efa run [OPTIONS]`

启动 uvicorn 服务。

| 选项 | 说明 | 默认值 |
|---|---|---|
| `--host` | 监听地址 | localhost |
| `--port` | 端口 | 8000 |
| `--reload` | 热重载 | false |

需在项目根目录（含 `.easy-fastapi.json` 标记）执行。加载 `app.main:app`；fullstack 项目后端在 `backend/` 子目录，会自动以 `backend/` 为 uvicorn 的 `app_dir`（将其加入 `sys.path`）。

## `efa db {init|migrate|upgrade|sync}`

数据库子命令组。

| 子命令 | 说明 |
|---|---|
| `init` | 初始化迁移配置（**非幂等**，仅首次执行） |
| `migrate` | 生成迁移文件 |
| `upgrade` | 应用迁移到最新 |
| `sync` | 直接建表（开发用，跳过迁移） |

迁移工具按 ORM 绑定：tortoise 用 aerich，sqlalchemy/sqlmodel 用 alembic。

## `efa gen [OPTIONS]`

从模型生成 CRUD 代码（router / schema / service）。

| 选项 | 说明 | 默认值 |
|---|---|---|
| `--force` | 覆盖已存在的生成文件 | false |

由 `ModelIntrospector` 驱动，扫描 `backend/app/models/`。文件冲突时抛 `GenConflictError`（非静默），`--force` 可覆盖。

## `efa i18n {init|compile|update}`

i18n 国际化子命令组（由 i18n 扩展通过 CLI 插件机制注册，详见 [扩展](extensions.md)）。

| 子命令 | 说明 |
|---|---|
| `init <lang>` | 初始化翻译目录（创建 `locales/{lang}/LC_MESSAGES/messages.po`），已存在则跳过 |
| `compile` | 编译 `.po` → `.mo`（纯 Python，无需系统 `msgfmt`）；mtime 比对跳过已是最新 |
| `update` | 扫描源码 `_()` 调用，提取 msgid，合并到 `.po` 文件（新增条目/保留翻译/obsolete 标记） |

推荐工作流：`efa i18n init` → 编辑 .po → `efa i18n compile` → 运行项目。新增代码后运行 `efa i18n update` 同步 msgid。

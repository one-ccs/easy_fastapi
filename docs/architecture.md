# 架构

Easy FastAPI 1.0 拆为**运行时包**（`easy_fastapi`）和**CLI 包**（`easy_fastapi_cli`），物理隔离、各司其职。两包置于同一仓库 `packages/` 下，uv workspace 统一开发与 lock，同版同发。

## 分层

```
packages/
├── easy_fastapi/src/easy_fastapi/
│   ├── core/          # 运行时：框架核心（app/config/extension/exceptions/protocols/persistence）
│   ├── ext/           # 运行时：扩展（orm/{tortoise,sqlalchemy,sqlmodel}/auth/redis/static/i18n/migration）
│   ├── commands/      # 运行时：项目命令执行层（db/gen + codegen 模板/conflict）
│   ├── project.py     # 运行时：项目语义解析（read_marker/app_target/resolve_db_config）
│   ├── _runner.py     # 运行时：内部 argv 分发（argparse，CLI re-exec 目标）
│   └── __main__.py    # python -m easy_fastapi 入口
└── easy_fastapi_cli/src/easy_fastapi_cli/
    ├── main.py        # CLI：Typer 入口
    ├── commands/      # CLI 薄壳：create + run/gen/db 转发
    ├── venv_bridge.py # CLI：uv run --no-sync 转发
    ├── scaffold/      # CLI：脚手架（options/validate/wizard/manifest/renderer/write/marker/conflict）
    └── templates/     # CLI：模板树（backend/{base,orm}/ + frontend/{base,pnpm}/）
```

- **运行时包** `easy_fastapi`（core + ext + commands + project + _runner）：`import easy_fastapi` 即用，不触发脚手架；`efa run/db/gen` 的真实执行逻辑在此包，由项目 venv 加载。
- **CLI 包** `easy_fastapi_cli`（commands + venv_bridge + scaffold + templates + plugin_loader + plugin_protocol）：`efa` 命令行工具，薄壳——负责入口/参数/项目发现/venv 转发 + `efa create`；`run/db/gen` 一律 re-exec 到项目 venv，不直接执行业务逻辑。`plugin_loader` 发现内置扩展与外部插件注册的 CLI 命令（见 DECISIONS ADR #36）。详见 DECISIONS ADR #27。

## 双模式目录契约

| 模式 | 条件 | 落盘结构 |
|---|---|---|
| `backend-only` | `frontend=False` | `app/`、`pyproject.toml` 顶级 |
| `fullstack` | `frontend=True` | `backend/app/`、`backend/pyproject.toml`、`frontend/{packages/api-sdk, apps}`（最小骨架） |

manifest 的 `_strip_backend_prefix` 后处理：backend-only 模式去掉 dest 的 `backend/` 前缀（落盘到项目根，而非 `backend/`）；fullstack 模式模板树内已有 `backend/` 前缀，dest 不变。

## 扩展协议

```python
class Extension(Protocol):
    name: str
    requires: ClassVar[list[str]] = []
    def config_model(self) -> type[BaseModel] | None: ...
    def init_app(self, app: FastAPI, config: BaseModel | None, ctx: ExtensionContext) -> None: ...
```

`ExtensionContext`：
- `provide(key, value, *, override=False)` — 注册服务
- `require(key, type_, *, requester=None)` — 消费服务（缺依赖抛 `ExtensionError`）
- `has(name)` / `get_config(name)` — 查询扩展状态

## 扩展实例化与装配

生成项目中，扩展在 `app/extensions/` 模块级实例化，`app_factory.py` 导入后链式 `efa.use()` 装配：

```python
# app/extensions/orm.py
from easy_fastapi.ext.orm.tortoise.extension import TortoiseExtension
from app.models.user import User
from app.models.role import Role
orm = TortoiseExtension(models=[User, Role])

# app/extensions/auth.py
from easy_fastapi.ext.auth.extension import AuthExtension
auth = AuthExtension()

# app/bootstrap/app_factory.py
from app.extensions.orm import orm
from app.extensions.auth import auth
efa = EasyFastAPI(app, config_path=CONFIG_PATH)
efa.use(orm).use(auth)
```

`use()` 返回 `self`（链式调用）。`init_app` 在 `use()` 内执行，因此路由注册时扩展已就绪。业务代码从扩展实例直接取服务（如 `auth.require`），无需 `get_extension_context` 间接层。

**AuthExtension 有状态化**：`init_app` 后 `self.require` / `self.token_service` 非 None，同时仍向 `ctx.provide` 注册（供其他扩展消费）。三级工厂依赖 `current_jwt()`/`current_token()`/`current_user()` 返回闭包 dependency，业务路由通过 `from app.extensions.auth import auth` 直接取用。

## ConfigLoader

- `ConfigLoader.from_yaml(path)` — 加载 YAML + env overlay
- `section(key, model)` — 按 Pydantic model 解析 section（key 支持点分路径如 `easy_fastapi.auth`）
- `extra='forbid'` — 多余键报错（`EasyFastAPIConfig` 除外，用 `extra='ignore'` 容纳扩展键）
- env overlay：`EFA_<SECTION>__<FIELD>` 覆盖 YAML 值（扩展配置在 `easy_fastapi` 段下，env 前缀为 `EFA_EASY_FASTAPI__<EXT>__<FIELD>`）

## 可选依赖守卫

```python
from easy_fastapi.core.extras import require
require("tortoise-orm", "tortoise")
```

缺包时抛 `ExtensionError`，消息含 `uv add <pkg>` 提示。

## 三 ORM 抽象

所有 ORM 扩展实现统一协议：

| 协议 | 方法 |
|---|---|
| `DbSession` | `commit()` / `rollback()` / `close()` |
| `DbSessionFactory` | `__call__() → AsyncContextManager[DbSession]` |
| `UserModelProtocol` | 继承 `BaseCRUDMixin` + `AuthUser`；`get_by_username()`/`get_by_email()`/`get_by_username_or_email()`/`get_by_id()`/`exists()`/`create_user()`/`update_password()` + `identity`/`h_pwd`/`scopes` |
| `RoleModelProtocol` | 继承 `BaseCRUDMixin`；`get_by_id()`/`exists()`/`create()` + `role` 属性 |
| `ModelIntrospector` | `extract_models() → list[ModelMeta]` |
| `BaseCRUDMixin` | `by_id()` / `paginate()` / `create()` / `update_from_dict()` / `delete_by_ids()` |

三 ORM 模型继承各自的 CRUDMixin（`ExtendedCRUD`/`SQLAlchemyCRUDMixin`/`SQLModelCRUDMixin`），满足 `BaseCRUDMixin` 协议。业务方法（`get_by_username`/`create_user`/`update_password` 等）以 classmethod 形态定义在 CRUDMixin 上，与 CRUD 方法共存。service 层和 codegen 产物只调协议方法与业务 classmethod，不直接用 ORM 原生 API。

**框架不持有内置 User/Role 模型和 repository**——实体定义归属项目（`app/models/user.py`/`app/models/role.py`），repository 层已删除。ORM 扩展 `__init__` 接收项目实体（`models: list[type] | list[str]`），`init_app` 内将 session factory 注入模型类并向 context `provide('user_model', User)`/`provide('role_model', Role)`。auth 经 `ctx.require('user_model', UserModelProtocol)` 取模型类本身。

ORM 扩展共享基础设施（`ext/orm/base/`）：
- `BaseCRUDMixin` — 统一 CRUD 协议（`crud.py`）
- `Pagination` — 分页数据类（`pagination.py`）
- `build_uri` / `build_db_url` — 数据库 URL 生成（`db_config.py`，直接接受 `DatabaseConfig`）
- `SQLAlchemyStyleIntrospector` — 共享 introspector（`introspector.py`）
- `make_session_factory` / `make_db_session_factory` — 共享 session 工厂（`session.py`）

## 模板 + Manifest + Renderer 流水线

1. `CreateOptions` → `apply_defaults()` → `validate()` — 校验选项
2. `build_manifest(options)` — walk_tree 遍历 + 条件过滤 + layout_prefix 处理
   - `backend/base/backend/` — 后端骨架（walk_tree + `_should_include` 条件过滤）
   - `backend/{orm}/backend/` — ORM 专属模型（按选中 ORM 遍历）
   - `frontend/{base,pnpm}/` — 前端（walk_tree，仅 fullstack）
   - `_strip_backend_prefix` — backend-only 去掉 `backend/` 前缀
3. `Renderer(options).render(template_text)` — Jinja2 + StrictUndefined 渲染
4. `write_manifest(manifest, options, project_dir, templates_root)` — 落盘
5. `write_marker(project_dir, options)` — 写 `.easy-fastapi.json` 标记

## CLI 插件机制

CLI 包通过 `CLIPlugin` Protocol + `plugin_loader` 让扩展（含 i18n）能注册自己的 CLI 命令，而非全部硬编码在 `main.py`。

- **协议**（`plugin_protocol.py`）：`@runtime_checkable` Protocol，鸭子类型——仅需 `name: str` + `register(app, *, rich_help_panel)`，不要求继承基类。
- **发现**（`plugin_loader.py`）：两条路径统一汇入 `load_plugins(app)`：
  1. 内置扩展：约定扫描 `easy_fastapi.ext.{name}.cli` 模块，有 `cli_plugin` 导出对象即加载。
  2. 外部插件：`entry_points(group="easy_fastapi.cli_plugins")`。
- **注册**：统一 `rich_help_panel="Extensions"` 与内置命令分组；同名先到先得；单插件失败不阻塞其他（错误隔离）。
- **entry_points 的 venv 限制**（策略 A：接受限制）：`entry_points()` 扫描的是 CLI 进程所在的 Python 环境，**扫不到项目 venv 里的插件**。`load_plugins` 在 CLI 包导入时执行（`main.py` 模块级），此时进程仍在 CLI venv 内，尚未经 `venv_bridge` re-exec 到项目 venv。因此外部 CLI 插件必须装在 CLI 所在环境：pipx 安装时用 `pipx inject easy-fastapi-cli <plugin>`；或把 CLI 装进项目 venv（`uv add --dev easy-fastapi-cli`）后插件自然可见。内置扩展路径不受影响（`easy_fastapi` 是 CLI 的依赖，必在 CLI venv）。**不做跨 venv 扫描**（subprocess 拿到的 entry_points 元数据无法在 CLI 进程内安全 load，跨 venv import 存在 typer/rich 版本冲突地雷）。
- **i18n CLI 插件**（Core 包 `ext/i18n/`）：`cli.py`（thin shell，typer 延迟导入）+ `cli_commands.py`（纯业务逻辑）+ `msgfmt.py`（纯 Python .po→.mo 编译器）。提供 `efa i18n init/compile/update` 三个命令。

依赖方向：Core 包的 i18n 扩展定义 CLI 插件，但 `cli_commands.py` 不 import typer，`_project_dir()` 不 import CLI 包——Core ↛ CLI 单向依赖不变（守护测试 `tests/test_dependency_direction.py`）。详见 DECISIONS ADR #36 / 硬约束 L。

# Changelog

## [1.0.0] - 2026-06-26

### Changed
- **BREAKING**: 拆分为双包：`easy_fastapi`（runtime 运行时库）+ `easy_fastapi_cli`（脚手架 CLI）
  - 安装 CLI：`uv tool install easy-fastapi-cli`（命令 `efa` / `easy-fastapi`）
  - 安装 runtime：`uv add easy_fastapi`
  - 删除 `[runtime]`/`[cli]`/`[full]` extras（runtime 依赖变核心，CLI 独立包）
  - CLI 命令别名 `easy_fastapi` → `easy-fastapi`（连字符）

## [Unreleased] - 2026-06-25

### 破坏性变更
- 删除完整 Vue3 admin 前端模板，`frontend/` 降级为最小 monorepo 骨架（仅 `packages/api-sdk` + `apps/` 占位）
- 删除 `frontend_framework`/`frontend_theme`/`frontend_apps` 三个 CLI 选项（`--frontend-framework`/`--frontend-theme`/`--frontend-apps`）及向导 checkbox
- marker 不再派生 `frontend_ui` 字段
- `pnpm-workspace.yaml` globs 从 `frontend/*`+`frontend/shared/*` 改为 `frontend/packages/*`+`frontend/apps/*`
- api-sdk 路径 `frontend/shared/api-sdk/` → `frontend/packages/api-sdk/`，脚本名 `gen` → `sdk:gen`

### 新增
- 模板分层 `frontend/{base,pnpm}`：base 包管理器共用、pnpm 专属/动态
- 根 `.npmrc`（link-workspace-packages / prefer-workspace-packages / save-workspace-protocol）
- `frontend/apps/.gitkeep` 用户自建应用占位
- api-sdk README 按 `options.language` jinja 条件块切换中/英
- 根 `package.json` 精简为仅 `sdk:gen` 脚本（删 admin filter 脚本与根级 typescript）

## [1.0.0] - 2026-06-25

### ⚠️ Breaking Changes (0.x → 1.0)

- 重构为运行时层（core/ext）+ CLI 层（cli/scaffold/generator/templates）物理隔离
- 扩展协议改为 `Extension.config_model()` + `init_app(app, config, ctx)`（移除 `on_post_start`）
- 配置改用 `ConfigLoader`（无全局单例，`extra='forbid'`，文件必须存在）
- `EasyFastAPI(app, config_path=)` 装配，经 `use(extension)` 链式注册
- 可选依赖全部经 `require()` 守卫（缺包提示 `uv add`）
- 双模式目录契约：`frontend=True` → fullstack monorepo（`backend/`+`frontend/`）；否则纯后端
- ORM 三选一（tortoise/sqlalchemy/sqlmodel），迁移按 ORM 绑定（aerich/alembic）
- 认证用 pwdlib（argon2 默认，兼容 bcrypt）+ PyJWT，跨 ORM 零耦合
- 前端默认 Vue3 全家桶（多框架可扩展口子留位，暂不实现 React）
- 包管理器改用 uv（弃用 pip）
- 删除 0.x 冗余源码（config/management/db/generator/result/authentication/exception 等旧模块）
- 顶层导出 `BaseResult`/`Result`/`ResponseResult`（命名规范化：旧 `Result`→`BaseResult`，旧 `JSONResult`→`Result`，旧 `JSONResponseResult`→`ResponseResult`）

### Features

- `efa create/run/db/gen` 四类 CLI 命令
- `ExtensionContext.provide/require` 服务注册与依赖
- 三 ORM 各 provide `db_session_factory`/`model_introspector`/`user_repository`
- auth 扩展跨 ORM（经 `user_repository`/`persistence`/`token_service`）
- redis 扩展 override 覆盖 persistence（`enabled=false` 回退）
- `efa gen` 由 ModelIntrospector 驱动，冲突报错不静默
- Vue3 前端：`frontend/admin` + `frontend/shared/api-sdk`（@hey-api/openapi-ts）+ vue-i18n 中英文
- 12 选项组合矩阵测试（backend-only × fullstack × 3 ORM × auth/redis/migration/static × zh/en）
- 统一错误处理验收（ConfigError/ExtensionError/GenConflictError 全覆盖）
- e2e 测试（生成项目 → import app → OpenAPI 可达 → 前端 SDK 链路）

### Migration

- 见 `docs/migration/0.x-to-1.0.md`

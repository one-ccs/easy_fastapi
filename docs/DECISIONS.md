# 关键决策与约束

> 记录 Easy FastAPI 1.0 的架构决策理由、不可违反的硬约束、已知限制。
> 与 [architecture.md](architecture.md) 互补：那里讲「结构是什么」，这里讲「为什么这么定 + 哪些不能改」。
> 起源：1.0 设计 spec（2026-06-23）+ create 输出结构修复 spec（2026-06-25）+ 模板对齐 spec（2026-06-28）+ 交付后缺陷归档（post-1.0）。

---

## 一、架构决策（ADR 摘要）

1. **双包 + uv workspace：`easy_fastapi`（runtime）+ `easy_fastapi-cli`（CLI），同版同发**
   `easy_fastapi` 是运行时库（core+ext，核心依赖含 fastapi 全家桶，无 extras）。`easy_fastapi_cli` 是脚手架 CLI（硬依赖 runtime，命令 `efa`/`easy-fastapi`）。两包置于同一仓库 `packages/` 下，uv workspace 统一开发与 lock，同版同发。
   *Why：* 让 runtime 库与 CLI 工具各自独立发布、各自有清晰的依赖闭包与安装语义。装 CLI 即得完整脚手架能力，装 runtime 即得纯运行时库，不再用 extras 间接耦合。

2. **运行时包与 CLI 包物理隔离（独立包），CLI 薄壳化**
   `easy_fastapi`（Core/运行时）含 `core/` + `ext/` + `commands/`（项目命令执行层）+ `project.py`（项目语义解析）+ `_runner.py`（内部 argv 分发）。`easy_fastapi_cli`（CLI）退化为薄壳：`commands/`（create/run/gen/db 转发）+ `scaffold/` + `templates/` + `venv_bridge.py`。依赖方向单向：CLI 可依赖 runtime 公共契约（`core.exceptions`/`__version__`）；runtime 不得 import CLI 包（自动化守护测试 `tests/test_dependency_direction.py`）。详见 ADR-27。
   *Why：* `efa` 经 `uv tool install` 装在全局工具 venv（不含 `tortoise-orm`/`aerich`/`redis` 等项目运行时依赖），若 `run/db/gen` 执行逻辑在 CLI 包内，导入 app 时 `require("tortoise-orm")` 必崩。把执行宿主迁到 Core（项目 venv 内）才解决。

3. **删除按功能 extra**
   不设 `easy_fastapi[tortoise]` 之类按功能的 extra。生成项目 pyproject 直接依赖真实三方包（`tortoise-orm`/`pyjwt` 等）+ `easy_fastapi`（runtime 包，无 extras）。缺依赖由 `require()` 守卫提示 `uv add <真实包名>`。

4. **扩展协议 v1 只保留 `config_model()` + `init_app(app, config, ctx)`，删除 `on_post_start`**
   配置加载由框架在 `use()` 内统一做（取模型 → `loader.section()` → 校验 → 传给 `init_app`）；扩展不在 `init_app` 里临时读配置。
   *Why：* v1 不统一编排启动后钩子；扩展需要启动后逻辑时在 `init_app` 内自行注册 FastAPI lifespan/startup event，扩展自治。

5. **扩展间只走 `ExtensionContext.provide/require`，禁止互调**
   禁止 `import easy_fastapi.ext.xxx` 互调、禁止翻 `app.state`（context 挂载除外）。服务依赖而非扩展名通配：auth 对 ORM 的依赖写 `ctx.require('user_model', UserModelProtocol)`，不写 `requires=['orm.*']`。

6. **`ctx.require` 类型化 + 运行时校验**
   `type_` 参数稳定 IDE 补全；运行时校验仅针对可 `isinstance` 的具体类或 `@runtime_checkable` 协议（`Persistence`/`DbSession`/`DbSessionFactory`/`AuthUser`/`UserModelProtocol`/`RoleModelProtocol`/`ModelIntrospector`）。报错含 service key + 发起扩展名（`requester` 由调用方显式传入，不从调用栈推断）+ 补救提示。`ctx.provide` 默认禁重复 key（覆盖须显式 `override=True`，redis 覆盖 `persistence` 是明确特例）。

7. **`persistence` service key 始终存在**
   core 预注册 `MemoryPersistence` 作默认；redis 扩展 `enabled=True` 时用 `RedisPersistence` + `override=True` 覆盖。auth 永远能 `require('persistence')`。

8. **认证跨 ORM，零 `if orm==`、零 import 具体 ORM**
   auth 只经 `ctx.require('user_model', UserModelProtocol)` + `ctx.require('persistence')` 消费。`UserModelProtocol` 继承 `BaseCRUDMixin`，声明业务方法签名（`get_by_username`/`get_by_username_or_email`/`exists`/`create_user`/`update_password` 等 classmethod）+ `AuthUser` 契约（`identity`/`h_pwd`/`scopes`）。边界验收判据：加第四种 ORM，auth 代码一行不改。

9. **密码哈希用 pwdlib，弃 bcrypt**
   `PwdlibPasswordHasher` 注册 argon2 + bcrypt，新 hash 用 argon2（默认），verify 兼容旧 bcrypt hash。pwdlib 是生成项目真实依赖（非框架 extras）。

10. **双模式目录契约**
    `frontend=True` → fullstack monorepo（项目根 = workspace 根，`backend/` + `frontend/`）；`frontend=False` → 纯后端单项目（无 `backend/` 层、无 workspace 文件，后端内容在项目根）。后端 app 路径按模式：`backend/app/` 或 `app/`。CLI 运行目录条件化：monorepo 在 `backend/`，纯后端在项目根，错误目录给明确提示。

11. **`app_name` 删除；`package_name` 职责收窄**
    `package_name` 仅用于需要合法 Python 标识符的内部命名场景/模板变量（pyproject name、pnpm workspace 包名命名空间 `@<package_name>/`、tsconfig paths、import 路径字符串）。**不决定** import 根路径、backend 目录名、frontend 包名。`project_name`/`package_name`/`target_dir` 三者绝不混用。

12. **Config 重构：`ConfigLoader` + `extra='forbid'` + 文件必须存在**
    删除 0.x 全局单例 `__new__` hack；loader 作 `EasyFastAPI` 实例属性。任一 `ValidationError` 启动期抛出（中文字段路径）。env overlay 规则 `EFA_<SECTION>__<FIELD>`（双下划线分路径，value 先 `json.loads` 失败再留字符串）。配置文件不存在直接报错，不走静默空配置。

13. **可选依赖缺失统一走 `require()` 守卫**
    禁止裸 `ImportError`。`require(package, module_name)` 只翻译 `ModuleNotFoundError`（模块内部其它异常原样抛出，不误包装），按「模块本身/父包/子依赖缺失」区分，提示 `uv add <真实包名>`（单引号）。不用脆弱的 `startswith` 口径。

14. **顶层 `__init__.py` eager import（旧 PEP 562 懒加载已移除）**
    运行时符号（`EasyFastAPI`/`get_extension_context`/`Extension`/`ExtensionContext`/`ConfigLoader`/三个异常）+ 扩展分发入口 `get_extension` 顶层直接 eager import。旧 0.x 用模块级 `__getattr__` 懒加载是为了让 `[cli]` extra 无 fastapi 时 `import easy_fastapi` 不崩；1.0 分包后 fastapi 已是 `easy_fastapi` 硬依赖（CLI 包又依赖 runtime），"CLI-only 无 fastapi"场景消失，懒加载失去保护对象，且 PEP 562 `__getattr__` 对 IDE/mypy/补全不透明，故移除。ext 具体扩展类（`TortoiseExtension` 等重型可选依赖）仍按需 import，不顶层 eager。

15. **三 ORM 支持是明确需求，非 YAGNI**
    Tortoise / SQLAlchemy / SQLModel，迁移按 ORM 绑定（Tortoise→Aerich `migrations/`，SQLAlchemy/SQLModel→Alembic `alembic/`）。migration 附属化：`ext/migration/` 是 `efa db` 实现层，不是用户 `use()` 对象。用户心智：选 ORM = 选迁移工具。

16. **db 命令语义钉死**
    `init` 非幂等（迁移配置已存在报错）；`sync` ORM 行为修正（SQLAlchemy=`Base.metadata.create_all`，SQLModel=`SQLModel.metadata.create_all`，开发用非生产）；`gen` 文件冲突默认报错列清单（不静默跳过），`__init__.py` 幂等追加去重。

17. **marker 由 `write_marker()` 代码写入，非模板**
    `.easy-fastapi.json` 是结构化产物，`templates/common/` 下无 marker 模板。含 `marker_schema_version`(=1)/`easy_fastapi_version`/`template_version`/`generated_at`/`project_layout`("fullstack"|"backend-only")/`options`(最终快照含派生 `frontend_ui`)/`registered_extensions`（推导：orm→`orm.*`，auth/redis/static 直接映射，migration/frontend 不进入）。`registered` ≠ `enabled`，真实启用取决于运行期 yaml/env。

18. **Renderer 只负责渲染**
    读模板 → 变量替换 → 产出内容/路径。文件覆盖/冲突检查由 create/gen 命令层处理。`StrictUndefined`：模板用了 options 没有的字段直接报错。`generated_at` 由 create 在渲染前生成一次注入，marker/README/文件头共用同一时间源。

19. **混合模板组织：后端 walk_tree 遍历 + 条件过滤 + ORM 显式映射**
    后端模板按域分组放在 `templates/backend/` 下（与 `templates/frontend/` 平行），物理镜像 fullstack 生成结构：`backend/base/backend/` = fullstack 后端骨架，`walk_tree` 全量遍历后按条件过滤表排除不应生成的文件（auth/database/migration 条件）。ORM 模型按 ORM 名分子树（`backend/{orm}/backend/app/models/`），`_add_orm` 按选中 ORM 遍历。`_strip_backend_prefix` 处理 backend-only 模式（去掉 `backend/` 前缀，fullstack 不动）。前端走 `walk_tree` 遍历 `frontend/{base,pnpm}` 两子树（不变）。根级文件 `.gitignore`/`pyproject.toml`/`README.md` 落 `templates/` 根。

20. **前端最小骨架 + workspace 包名按 package_name**
    `frontend/packages/api-sdk`（核心共享包，OpenAPI 生成）+ `frontend/apps/`（用户自建应用占位）。不维护完整前端应用模板（删 Vue3 admin）。workspace 包名命名空间 `@<package_name>/`（保留，与项目 Python 标识统一）。模板 `frontend/{base,pnpm}` 分层（base 包管理器共用、pnpm 专属/动态），均走 `walk_tree` 遍历。README 按语言 jinja 条件块切换（api-sdk README 单文件 `{% if options.language %}`）。

21. **大版本 0.x → 1.0 不保留冗余兼容代码**
    语义变更用对照表在迁移文档说明。删除 0.x 旧模块（config/management/db/generator/result/authentication/exception）。1.0 重新导出 `BaseResult`/`Result`/`ResponseResult` + 业务异常（`FailureException`/`UnauthorizedException`/`ForbiddenException`/`NotFoundException`），作为顶层 eager import（spec 2026-06-28 恢复）。

22. **BaseCRUDMixin 协议 — 三 ORM 统一 CRUD 接口**
    `ext/orm/base/crud.py` 定义 `@runtime_checkable` Protocol，声明 5 个 classmethod：`by_id`/`paginate`/`create`/`update_from_dict`/`delete_by_ids`。各 ORM 实现 mixin（`ExtendedCRUD`/`SQLAlchemyCRUDMixin`/`SQLModelCRUDMixin`），模型继承即获 CRUD 能力。service 层和 codegen 产物只调这些方法，不直接用 ORM 原生 API。
    *Why：* 让 service/codegen 生成的代码在任意 ORM 下均可运行，消除 ORM 耦合。
    - **业务 classmethod 与 CRUD 方法共存于同一 mixin**：`get_by_username`/`get_by_email`/`get_by_username_or_email`/`get_by_id`/`exists`/`exists_by_email`/`create_user`/`update_password` 等业务方法以 classmethod 形态定义在 CRUDMixin 上（非协议强制），模型继承即获；session 由 mixin 的统一 `_session()` 自动提交上下文管理器供给（成功 commit、异常 rollback、总是 close）。
    - **`UserModelProtocol` 继承 `BaseCRUDMixin` + `AuthUser`**：替代旧 `UserRepository`，auth 经 `ctx.require('user_model', UserModelProtocol)` 取模型类本身（而非 repository 实例）。
    - 守护测试：`tests/ext/orm/base/test_base_crud.py`（协议签名）、`tests/ext/orm/tortoise/test_crud_extended.py`/`tests/ext/orm/sqlalchemy/test_crud.py`/`tests/ext/orm/sqlmodel/test_crud.py`（三 ORM 实现）、`tests/ext/orm/sqlmodel/test_business_methods.py`/`tests/ext/orm/sqlalchemy/test_business_methods.py`（业务 classmethod）、`tests/ext/orm/test_model_crud_integration.py`（项目模型接入 mixin 协议满足性）

23. **codegen Jinja2 模板 — 统一命名 + 类型映射 + init 接线**
    codegen 从字符串拼接迁移到 Jinja2 模板（`templates/codegen/schema.py.j2`/`service.py.j2`/`router.py.j2`），使用 `StrictUndefined`。service 文件命名统一 `{snake}.py`，router `{snake}_router.py`。字段类型映射（`_TYPE_MAP`）覆盖 IntField→int、CharField→str、DatetimeField→datetime 等，未知类型默认 str。`generate_for_model` 后向 `__init__.py` 幂等追加导出（去重）。
    *Why：* 修复 codegen 产出缺 datetime 导入、PK 硬编码 int、`__init__.py` 不接线三大缺陷。
    - 守护测试：`tests/generator/test_codegen_jinja.py`/`test_codegen_init_wiring.py`/`test_codegen_type_mapping.py`

24. **auth 对齐 spec — OAuth2 表单 + TokenResponse + scope 校验可配置 + WWW-Authenticate**
    登录用 `OAuth2PasswordRequestForm`（form-encoded），`TokenResponse` 声明为 `response_model`。`@require` scope 校验**可配置**：yaml 全局 `scope_match`（`any`=交集 OR 默认 / `all`=子集 AND）+ 逐路由 `match=` 参数覆盖 + callable 自定义 matcher。`AuthUser` 协议声明 `scopes` 属性。401 响应透传 `WWW-Authenticate: Bearer` 头（统一用 `UnauthorizedException`）。`/me` 用 `AuthUserOut` response_model 过滤 `hashed_password`。
    - 守护测试：`tests/ext/auth/test_router.py`/`tests/test_auth_decorator.py`/`tests/test_handlers.py`

34. **AuthExtension 类化 — 工厂依赖 + 三级依赖链 + JWT 异常细分 401**
    `AuthExtension` 扩展为完整认证器：既是扩展协议实现，也是认证能力载体（持有配置/服务/三级工厂依赖/require 装饰器）。`build_auth_router` 函数删除，路由注册搬入 `init_app`。
    - **工厂依赖模式**：`current_jwt()`/`current_token()`/`current_user()` 是方法调用返回闭包 dependency。`Depends(auth.current_user())` 引用闭包而非绑定方法，FastAPI 不会把 `self` 误判为 query 参数（参考实现 `Depends(self.current_token)` 的 self 签名问题）。
    - **三级依赖职责**：`current_jwt`（提取原始 JWT 字符串，仅检查缺失，不解码）/ `current_token`（解码 + 检查 `type=="access"` + 查黑名单）/ `current_user`（从 payload 查库加载用户）。黑名单检查在 `current_token`（需 jti，必须先解码）。
    - **`TokenPayload` pydantic 模型**：显式声明 RFC 7519 全部 7 个标准字段（iss/sub/aud/exp/nbf/iat/jti）+ 2 业务字段（type/scopes），皆可为空（非 `extra="allow"`，IDE 提示友好、类型安全）。
    - **`TokenService.decode` 抛异常**：不再吞 PyJWTError 返回 None，直接抛 PyJWT 异常。全局注册 5 个异常处理器映射到细分 401 消息：`ExpiredSignatureError`→"Token has expired"/`InvalidSignatureError`→"Invalid signature"/`DecodeError`→"Token decode failed"/`InvalidTokenError`→"Invalid access token"/`PyJWTError`→"Unknown token error"。处理器在 `init_app` 末尾注册（auth 自治，不污染 core）。
    - **401 统一用 `UnauthorizedException`**：router 内所有 401 从裸 `HTTPException` 改为 `UnauthorizedException`（自带 `WWW-Authenticate: Bearer` 头）。
    *Why：* 函数式 `build_auth_router` 三级依赖无法暴露给业务路由；吞异常让前端只能报笼统 401；裸 HTTPException 丢 WWW-Authenticate 头。类化 + 工厂依赖让三级依赖成为可复用方法，JWT 异常细分让前端可区分过期/无效/签名错误。`current_token` 检查 `type=="access"` 与 `_validate_refresh_token` 检查 `type=="refresh"` 对称，防止 refresh token 被当作 access token 使用。
    - 守护测试：`tests/ext/auth/test_router.py`（三级依赖独立测试 + JWT 异常细分 + WWW-Authenticate 头 + scopes any/all/callable/yaml）、`tests/ext/auth/test_token.py`（decode 抛 PyJWT 异常）、`tests/ext/auth/test_extension.py`（工厂依赖可调用）、`tests/test_auth_decorator.py`（scopes 可配置校验）

35. **I18n 扩展 — gettext + contextvars + 翻译边界模式**
    基于 Python stdlib `gettext` + `contextvars` 实现运行时多语言切换。翻译范围限定为**用户面向的 API 响应消息**，框架内部错误（ExtensionError/ConfigError 等）不翻译。
    - **翻译核心在 `core/i18n.py`**（非 `ext/i18n/`）：`set_locale()`/`get_locale()`/`_()` 三个函数。`_()` 未初始化时为恒等函数（返回 msgid 英文原文）。放 core 是因为 `result.py`/`handlers.py` 需调用 `_()`，放 ext 会造成 core→ext 反向依赖。
    - **翻译边界在 `Result.__new__` / `ResponseResult.__new__`**：这是唯一翻译点。业务层和异常处理器传英文 msgid 给 `Result`/`ResponseResult`，`__new__` 内部调用 `_(message)` 翻译。**调用方不得再包 `_()`**，否则导致双重翻译 `_(_("msgid"))`。
    - **MSG_* 常量改为英文 msgid**：`MSG_FAILURE = "Request failed"` 等。Breaking change：引用常量值的代码需更新。
    - **Fallback 链**：`set_locale()` 接收 `localedirs` 序列，按 `add_fallback()` 串联：项目翻译 → 框架翻译 → msgid。项目可覆盖框架翻译。
    - **翻译缓存**：`_load_translations()` 在 `ext/i18n/extension.py` 中缓存翻译对象，避免每请求重复读取 .mo 文件。中间件只切换 ContextVar。
    - **中间件后注册先执行**：i18n 在 `app_factory.py` 中最后 `.use()`，FastAPI 中间件栈式执行 → i18n 中间件最先执行 → 最早设置 locale → 其他扩展请求处理中 `_()` 可用。
    - **Accept-Language RFC 7231 q= 权重**：`_parse_accept_language()` 解析 q 值并按优先级降序匹配。
    - **`I18nConfig` 校验**：`default_locale` 必须在 `available_locales` 中（`@model_validator`）。
    - **`.mo` 文件包含在 wheel**：`pyproject.toml` 配置 `artifacts = ["src/easy_fastapi/locales/**/*.mo"]`。
    *Why：* gettext 是 Python 标准库方案，零外部依赖；contextvars 天然与 ASGI 异步模型匹配（每请求独立 context）；翻译边界集中在 `Result`/`ResponseResult` 让业务代码零翻译调用。
    - 守护测试：`tests/core/test_i18n.py`（恒等函数/翻译/fallback 链）、`tests/ext/i18n/test_i18n_extension.py`（配置/中间件/q 值/缓存）、`tests/test_result.py`+`tests/test_handlers.py`+`tests/test_exceptions.py`（消息改造）

25. **ORM 配置统一为 `database` 段**
    所有 ORM 扩展从通用 `database` section 读取连接信息（`dialect`/`username`/`password`/`database`/`host`/`port`），不再有 `tortoise_orm`/`sqlalchemy`/`sqlmodel` 独立配置段。`build_uri` 统一生成数据库 URL——**注意 Tortoise 与 SQLAlchemy/SQLModel 对 SQLite URL 斜杠语义不同**：Tortoise 设 `skip_first_char=False`（`file_path = netloc + path`），需 `sqlite://{db}`（两斜杠）；SQLAlchemy/SQLModel 用标准 RFC 3986 语义，需 `sqlite+aiosqlite:///{db}`（三斜杠）。
    *Why：* 消除 ORM 配置段重复，选 ORM 不影响 YAML 结构。SQLite URL 格式差异源于 Tortoise 的非标准 URL 解析，`build_uri` 必须按 ORM 分支处理。
    - 守护测试：`tests/ext/orm/base/test_db_config.py`（含 Tortoise/SQLAlchemy/SQLModel 三分支 SQLite URL 断言）

26. **消息常量单一来源（英文 msgid）**
    框架消息常量（`MSG_FAILURE`/`MSG_UNAUTHORIZED` 等）定义在 `core/exceptions.py` 顶部，值为英文 msgid（如 `"Request failed"`），`result.py`/`handlers.py` 引用同一常量。`Result.__new__`/`ResponseResult.__new__` 调用 `_(message)` 翻译，调用方不得再包 `_()`。`failure_with_id` 使用模块级 `logger = logging.getLogger("easy_fastapi")`，不在方法内 inline import。
    *Why：* 英文 msgid 作为 gettext 翻译键是标准做法；单一来源消除两处硬编码同一字符串的维护风险；翻译边界集中在 `Result`/`ResponseResult` 让业务代码零翻译调用。

27. **包管理全 uv，禁 pip**
    后端 uv、前端 pnpm（仅 frontend=True）。测试用 `unittest.mock`/fake 协议，不依赖真实 ORM 安装。

28. **CLI 薄壳化：项目命令执行宿主迁入 Core**
    `efa run/db/gen` 一律通过 `uv run --no-sync --directory <root>` 转发到项目 venv 执行，CLI 不提供 in-process 分支。`run` re-exec 到项目 venv 的 `uvicorn <app_target> [--app-dir <app_dir>]`；`db/gen` re-exec 到 `python -m easy_fastapi._runner <cmd>`，`_runner` in-process 分发到 `easy_fastapi.commands/`。`efa create` 不经转发，在工具 venv 直接执行。
    *Why：* CLI 经 `uv tool install` 装在全局工具 venv（不含 `tortoise-orm`/`aerich`/`redis` 等项目运行时依赖），若执行逻辑留在 CLI 包内，导入 app 时 `require("tortoise-orm")` 必崩。迁到 Core（项目 venv）解决根因。
    - D1: 薄壳化（非物理重命名），双包名不变
    - D2: run 与 db/gen 入口形态不同（run→uvicorn 宿主，db/gen→Core 函数+_runner）
    - D3: Core 不引入 Typer，`_runner` 用 argparse 做最小 argv 分发
    - D4: 转发机制 `uv run --no-sync`（跨平台一致，自动处理 venv 缺失/损坏）
    - D7: 共享上下文层 `easy_fastapi.project`（`read_marker`/`load_project_context`/`app_target`），项目语义统一下沉到 Core
    - D10: CLI 一律 re-exec 无 in-process 分支；`_runner` 一律 in-process 不二次 re-exec；防递归环境变量删除（调用链单向固定）
    - 守护测试：`tests/test_dependency_direction.py`、`tests/test_top_level_exports.py`、`tests/core/test_project.py`、`tests/core/commands/test_db.py`/`test_gen.py`、`tests/core/test_runner.py`、`tests/cli/test_venv_bridge.py`

29. **ORM 扩展瘦身：删框架内置实体/repository，扩展接收项目实体**
    框架不再持有内置 `User`/`Role` 模型和 `UserRepository`/`RoleRepository`——实体定义归属项目（`app/models/user.py`/`app/models/role.py`），repository 层整体删除。各 ORM 扩展 `__init__` 接收项目实体：`TortoiseExtension(models: list[type] | list[str] | None = None)`/`SQLAlchemyExtension(models: list[type] | list[str])`/`SQLModelExtension(models: list[type] | list[str])`，`init_app` 内将 session factory（SQLAlchemy/SQLModel 的 `_sa_session_factory`）注入模型类，并向 context `provide('user_model', User)`/`provide('role_model', Role)`。Tortoise 同时支持 `list[type]`（直接传类）与 `list[str]`（模块路径，`_auto_discover_models` 解析），无参数时自动发现 `app.models.user`/`app.models.role`。
    *Why：* 框架内置实体让生成项目与框架强耦合（升级冲突、模型语义被框架定义），repository 层是多余间接（业务方法直接作 classmethod 挂在模型上更直观）。删内置实体后框架只提供能力（CRUDMixin/扩展装配），项目拥有自己的实体。
    - **migration 同步走模块路径动态导入**：`alembic_impl._sync(orm, db_url, models: list[str] | None)` 动态 import 项目模型模块以注册表；SQLAlchemy 路径用 `_extract_sqlalchemy_metadata(modules)` 扫描 `DeclarativeBase` 子类取其 `metadata`（项目继承自己的 Base，非框架 Base）。
    - 守护测试：`tests/ext/orm/test_model_crud_integration.py`（项目模型接入 mixin）、`tests/ext/orm/{tortoise,sqlalchemy,sqlmodel}/test_extension.py`（扩展装配 + provide `user_model`/`role_model`）、`tests/ext/migration/test_alembic.py`（`_sync` 动态导入）、`tests/core/commands/test_db_ops.py`（db sync 动态导入项目模型）、`tests/e2e/test_full_project.py::test_backend_auth_full_flow`（三 ORM 生成项目 auth 全流程真跑）

30. **Static 扩展：静态文件托管从模板生成升级为框架扩展**
    静态文件托管原为「模板生成 `mount_static` 函数 → 项目手动调用」模式，现升级为 `StaticExtension`（`ext/static/`），与 RedisExtension/AuthExtension 对齐。`StaticConfig`（`enabled`/`directory`/`url_path`，`extra='forbid'`）走 `easy-fastapi.yaml` 的 `static` section；`init_app` 内 `app.mount(url_path, StaticFiles(directory=...))`，目录不存在时静默跳过（开发初期常见）。`options.static` 简化为纯开关（删除 `static_dir`/`static_url`/`static_index_file` 三字段），yaml 配置使用默认值；删除 `templates/static/mount.py.j2` 和 `static/index.html`，manifest 不再产出 `app/core/static_mount.py`。旧 `SPAConfig` 已从 core config models 删除（由 `StaticConfig` 替代）。
    *Why：* 让静态托管与其他扩展一致走「yaml 配置 → 扩展装配」流程，消除项目侧手写 mount 代码；简化选项——创建向导只需回答"是否启用"，目录/URL 等在 yaml 里按需改。删除旧 `easy_fastapi.spa` 段（被 `static:` section 替代，修复旧 yaml 模板重复 `easy_fastapi:` 顶层 key 的隐患）。
    - 守护测试：`tests/ext/static/test_extension.py`（协议满足性 + mount 行为 + disabled/缺目录/绝对路径）、`tests/scaffold/test_manifest_ext.py::test_static_adds_static_fragment`（manifest 不含 static_mount.py）、`tests/scaffold/test_manifest_layout.py::test_fullstack_static_path`（fullstack static 走扩展配置）、`tests/e2e/test_full_project.py::test_static_project_*`（生成项目 yaml section + app_factory 装配 + 无 mount.py）

31. **模板目录镜像 fullstack 生成结构**
    后端模板按域分组放在 `templates/backend/` 下（与 `templates/frontend/` 平行），物理镜像 fullstack 生成结构：`backend/base/backend/` 就是 fullstack 后端骨架，`walk_tree` 全量遍历后按条件过滤表排除不应生成的文件（auth/database/migration 条件）。ORM 模型按 ORM 名分子树（`backend/{orm}/backend/app/models/`），`_add_orm` 按选中 ORM 遍历。`_strip_backend_prefix` 处理 backend-only 模式（去掉 `backend/` 前缀）。README 合并为单文件含中英文 jinja 条件块。删除 `_dest_for_layout` 后处理循环（改为 walk_tree 阶段的 `_strip_backend_prefix`）。删除 `static/index.html`（无前端页面，默认值够用）。
    *Why：* 让模板结构=生成结构，开发者看到模板目录就知道生成什么；消除 60+ 行硬编码 Fragment 映射（`_add_common`/`_add_auth`/`_add_migration`/`_add_test` 等函数），改为声明式条件过滤表；后端模板与前端对齐（按域分组 `backend/` + `base/` 遍历模式），减少维护成本。
    - 守护测试：`tests/scaffold/test_snapshot.py`（13 组合 × 文件树 + 关键断言）、`tests/scaffold/test_manifest_*.py`（路径断言已更新）、`tests/e2e/test_full_project.py`（生成项目真跑）

32. **扩展实例化下沉：`app/extensions/` 模块级实例化 + `AuthExtension` 有状态化**
    扩展实例化从 `app_factory.py` 内联代码下沉到 `app/extensions/` 子包（按扩展类型分文件：`orm.py`/`auth.py`/`redis.py`/`static.py`），`app_factory.py` 从此 import 并链式 `efa.use(orm).use(auth).use(redis).use(static)`。`AuthExtension` 改为有状态：`init_app` 后 `self.require`/`self.token_service` 非 None，用户可直接 `auth.require`——消除 `get_extension_context(app)` + `_AuthNamespace` 间接性。路由文件 `from app.extensions.auth import auth` → `@auth.require`。
    *Why：* `_AuthNamespace` 是手动构造的临时类，`get_extension_context(app)` 从 app.state 翻 ctx 再翻 services 是脆弱间接链。扩展实例本身就该持有自己的能力（`require` 装饰器是 auth 的核心导出）。模块级实例化让扩展可被 `app/extensions/` 下各模块独立 import，避免 app_factory 膨胀。
    - **`use()` 返回 `self`（链式不变）**：`efa.use(A()).use(B)` 语义不变。
    - **`ctx.provide/require` 仍用于扩展间服务依赖**：`auth.require` 是用户侧便利，ctx 仍 provide `require`（其他扩展可 `ctx.require`）。
    - 守护测试：`tests/ext/auth/test_extension.py::test_auth_instance_has_require_after_init`（有状态化）、`tests/ext/auth/test_extension.py::test_auth_require_equals_ctx_require`（实例与 ctx 一致）、`tests/e2e/test_full_project.py::test_backend_auth_full_flow`（三 ORM 全流程）、`tests/scaffold/test_manifest_*.py`（extensions 条件过滤）

33. **auth token 传输双模式 + access-only + 黑名单 + CookieOptions 结构体**
    auth 路由通过 `AuthConfig.token_transport` 配置切换 refresh_token 传输方式：
    - **body 模式**（默认）：刷新时旧 refresh_token 放 `Authorization: Bearer` 请求头，新 token 放响应 body。
    - **cookie 模式**：refresh_token 用 HttpOnly cookie 下发/读取/轮换，响应 body 不返回 `refresh_token` 字段（`response_model_exclude_none=True`），登出清除 cookie。
    - **access-only**（`enable_refresh=False`）：不签发 refresh_token，不注册 `/refresh` 路由。`TokenResponse.refresh_token` 改为 `str | None`。
    cookie 参数收进 `CookieOptions` 结构体（`AuthConfig.cookie`），`build_auth_router` 参数从 13 个降至 7 个。`TokenService` 暴露 `refresh_max_age` 属性（不再访问 `_refresh_days` 私有属性），签发 `jti`（JWT ID）+ `iat`（签发时间）以支持黑名单和 TTL。
    logout 将 access_token 的 `jti` 写入 persistence 黑名单（key = `auth:blacklist:<jti>`，TTL = 剩余有效期），`current_token()` 闭包和 refresh 校验均检查黑名单。
    *Why：* cookie 模式是 Web 安全最佳实践（HttpOnly 防 XSS 窃取）；access-only 适配无状态短会话场景；黑名单防止登出后 token 被重放；`jti` 是 JWT 标准唯一标识，使黑名单可按 token 精确吊销而非按用户全量吊销。
    - **`Persistence` 协议统一为 async**：`MemoryPersistence`/`RedisPersistence` 均为 async 方法，与 router 中 `await` 调用对齐（之前 `MemoryPersistence` 同步 + `RedisPersistence` async 的不一致在 `await persistence.get()` 时会 `TypeError`）。
    - **cookie 模式 body 不返回 refresh_token**：`response_model_exclude_none=True` 排除值为 `None` 的字段，cookie 模式下 `refresh_token=None` 被排除（避免双重暴露）。body 模式下 `refresh_token` 有值正常返回。
    - 守护测试：`tests/ext/auth/test_router.py`（body/cookie/access-only 三模式 + 黑名单 + 自定义 cookie_name）、`tests/ext/auth/test_token.py`（jti/iat/refresh_max_age）、`tests/ext/auth/test_schemas.py`（refresh_token Optional）、`tests/core/persistence/test_memory.py`（async Persistence）

36. **CLI 插件机制 + i18n CLI 命令**
    CLI 包定义 `CLIPlugin` Protocol（`@runtime_checkable`，鸭子类型，仅需 `name: str` + `register(app, *, rich_help_panel)`）+ `plugin_loader` 发现注册器。两条发现路径：内置扩展走约定扫描 `easy_fastapi.ext.{name}.cli` 模块（有 `cli_plugin` 导出对象即加载）；外部插件走 `entry_points(group="easy_fastapi.cli_plugins")`。统一注册到 Typer app，插件命令用 `rich_help_panel="Extensions"` 与内置命令分组。
    - **错误隔离**：单插件加载/注册失败不阻塞其他插件（`load_plugins` 捕获异常后 warning 并继续）。
    - **冲突检测**：同名插件先到先得，后者跳过（warning）。
    - **entry_points 的 venv 限制**（策略 A：接受限制）：`entry_points()` 扫描 CLI 进程所在环境，扫不到项目 venv 里的插件；`load_plugins` 在 CLI 包导入时执行（`main.py` 模块级），此时仍在 CLI venv、未进 `venv_bridge` re-exec。外部插件须装在 CLI 环境（pipx：`pipx inject easy-fastapi-cli <plugin>`；或 `uv add --dev easy-fastapi-cli` 装进项目 venv 后 CLI 与插件同环境）。内置扩展不受影响。**不做跨 venv 扫描**：subprocess 拿到的元数据无法在 CLI 进程内安全 load（`CLIPlugin` 是带方法的对象无法跨进程序列化；把项目 venv site-packages 加到 `sys.path` 会触发 typer/rich 版本冲突）。未来若有项目 venv 独占插件需求，走 pyproject `[tool.easy_fastapi.cli_plugins] modules=[...]` 声明式 config 路径，而非跨 venv entry_points 扫描。
    - **Core ↛ CLI 依赖方向**：`cli_commands.py` 不 import typer；`cli.py` 中 typer 延迟导入（`register()` 内 `import typer`）。`_project_dir()` 仅用 `Path.cwd()`，不 import `easy_fastapi_cli._guard`。
    - **i18n CLI 插件形态**：`ext/i18n/cli.py`（thin shell，typer 绑定）+ `ext/i18n/cli_commands.py`（纯业务逻辑，可独立测试）+ `ext/i18n/msgfmt.py`（内嵌纯 Python .po→.mo 编译器，基于 CPython `Tools/i18n/msgfmt.py` 精简，解决 Windows 无系统 msgfmt 问题）。
    - **三个命令**：`efa i18n init <lang>`（创建 .po 模板，已存在跳过）/ `efa i18n compile`（mtime 比对 + 纯 Python 编译）/ `efa i18n update`（扫描 `_()` 调用 + 合并 .po + obsolete 标记）。
    - **manifest 替换**：`efa create` 的 post_messages 从 `msgfmt -o ...` 改为 `efa i18n compile`。
    *Why：* Windows 无 `msgfmt` 命令让生成项目无法编译 .mo；扩展无法注册 CLI 命令（全部硬编码在 main.py）；CLIPlugin Protocol 借鉴 Flask 极简思路（不要求继承基类，鸭子类型即可）。
    - 守护测试：`tests/cli/test_plugin_loader.py`（7 测试：协议鸭子类型/内置发现/外部发现/冲突检测/错误隔离）、`tests/ext/i18n/test_msgfmt.py`（5 测试：解析/编译/gettext 可读/多行）、`tests/ext/i18n/test_cli_commands.py`（9 测试：init/compile/update 行为）、`tests/ext/i18n/test_cli.py`（2 测试：协议满足/命令注册）

---

## 二、硬约束（不可违反，附守护测试）

> 改动相关代码前先确认这些不变量。每条都有自动化测试拦截，违反会直接红。

### A. `package_name` / `project_name` 不参与任何文件/目录路径命名

包名只作配置字段值（pyproject/package.json/tsconfig/token key/import 路径字符串）。生成目录名来自命令行 `target` 参数；包代码目录是固定名 `app/`（backend-only）或 `backend/app/`（fullstack）。

- 守护测试：`tests/scaffold/test_manifest.py::test_fragment_dest_never_contains_package_or_project_name`（7 个 parametrize 子用例，覆盖 minimal/backend-full/fullstack/weird-pkg/static 等组合）。
- 源码层复核（人工 grep，补充自动化未覆盖的 paths.py/marker.py）：
  ```bash
  grep -nE "package_name|project_name" easy_fastapi/scaffold/paths.py    # 期望无匹配
  grep -nE "package_name|project_name" easy_fastapi/scaffold/manifest.py # 期望无匹配
  grep -nE "package_name|project_name" easy_fastapi/scaffold/marker.py   # 期望无匹配
  ```
- 新增 Fragment 的 `dest`、新增路径拼接逻辑时，**禁止**用 `package_name`/`project_name` 作路径片段。若需用户命名空间，用固定 `app/` 或 `@<package_name>/`（仅作包名字符串，非路径）。

### B. 顶层 `__init__.py` eager import；禁止顶层拖入 tortoise/redis 等重型可选依赖

运行时包 `easy_fastapi` 顶层 `__init__.py` eager import core 稳定 API（含 `EasyFastAPI`/`ConfigLoader`/`Extension`/`ExtensionContext`/`get_extension_context`/三个框架异常 + `BaseResult`/`Result`/`ResponseResult` + 四个业务异常 + `get_extension`）。fastapi 已是硬依赖，eager 触达 fastapi 是预期。但 **tortoise-orm / sqlalchemy / sqlmodel / redis 不在 `easy_fastapi` 硬依赖中**，禁止顶层 eager import 它们——仍经 `ext.get_extension(name)` 分发表（自身不触发重型依赖）或子模块路径按需 import。

- 守护测试：`tests/test_top_level_exports.py`
  - `test_top_level_import_does_not_load_tortoise` / `test_top_level_import_does_not_load_redis` — subprocess 全新解释器 import 不拖入 tortoise/redis
  - `test_top_level_import_eager_loads_core_symbols` — core 符号 import 时即可达，与子模块 identity 一致
  - `test_unknown_attribute_raises_attribute_error` — 未知属性抛 `AttributeError`（Python 默认行为，无自定义 `__getattr__`）
  - `test_top_level_exports_result_symbols` / `test_top_level_exports_business_exceptions` — `BaseResult`/`Result`/`ResponseResult` + 四个业务异常可从顶层导入（spec 2026-06-28 恢复）
- runtime 包源码不得 import `easy_fastapi_cli`（守护测试：`tests/test_dependency_direction.py`）。
- 新增顶层导出时：core 符号可直接 eager；触达 tortoise/sqlalchemy/sqlmodel/redis 的具体扩展类**不得**顶层 eager，走 `get_extension(name)` 或子模块路径。

### C. `efa create` 交互默认值与项目名推导

- `interactive` 默认 `True`（裸 `efa create <dir>` 必须进向导，非交互必须显式 `--no-interactive`）。
  - 守护测试：`tests/cli/test_create.py::test_create_defaults_to_interactive`
- `project_name` 为 `None` 时由 `do_create` 从目标目录名推导（`efa create .` 取 cwd 名，`efa create myapp/` 取 `myapp`），进向导前必须非 None。
  - 守护测试：`tests/cli/test_create.py::test_create_derives_project_name_from_target_dir` / `test_create_in_place_derives_project_name_from_cwd`
- 向导项目名输入框 `default` 由 `do_create` 推导后传入（`run_wizard(default_project_name=...)`），默认值链 `用户输入 → default_project_name → "app"`。`_slug` 容忍 None/空字符串。
  - 守护测试：`tests/scaffold/test_wizard.py::test_wizard_project_name_falls_back_to_default` / `test_wizard_project_name_explicit_overrides_default`、`tests/scaffold/test_options_from_args.py::test_slug_handles_none_and_empty`
- 缺陷 2（目录名推导）与缺陷 4（向导默认值）共用同一段推导逻辑，改一处要同步另一处。

### D. 配置严格性

- `extra='forbid'`（多余 YAML 键报 `ConfigError`，不静默丢弃）。
- 配置文件必须存在：`from_yaml` 路径不存在直接报错，不走静默空配置。
- `section(key, model)` 对缺失 section 按 `{}` 传给 `model.model_validate({})`——是否报错由模型字段默认值/必填决定，不等于「section 不存在一定报错」。

### E. backend-only 零前端污染

backend-only 模式不生成 `package.json`/`pnpm-workspace.yaml`/workspace `pyproject.toml`/`frontend/`/`backend_readme.md`。

- 守护测试：`tests/scaffold/test_no_frontend_isolation.py`
- `WHITELIST_IN_PLACE` 不含 `package.json`：in_place 模式下已存在 `package.json` 报错阻断，防覆盖现有前端工程。

### F. create 目标目录约束

- `efa create NAME`：目标目录必须不存在（**即使空目录也报错**）。
- `efa create .`：当前目录须为空或仅含白名单（`README*` 大小写不敏感、`.git/`、`.gitignore`，及 `pyproject.toml`/`LICENSE`/`.easy-fastapi.json` 共存允许），其它一律阻断。

### G. ExtendedCRUD 统一接口 — service/codegen 不得直接用 ORM 原生 API

生成项目的 service 层与 codegen 产出的代码只调用 `BaseCRUDMixin` 协议方法（`by_id`/`paginate`/`create`/`update_from_dict`/`delete_by_ids`，外加扩展方法 `exists`/`exists_by_email`/`get_or_create`）及业务 classmethod（`get_by_username`/`get_by_username_or_email`/`create_user`/`update_password` 等），**不得**直接调用 Tortoise 的 `filter().delete()`/`save()`/`update_from_dict()` 或 SQLAlchemy/SQLModel 原生 session API。三 ORM 模型必须满足 `isinstance(Model, BaseCRUDMixin)`。

- 守护测试：`tests/ext/orm/test_model_crud_integration.py`（三 ORM 项目模型满足 `BaseCRUDMixin` 协议）、`tests/ext/orm/tortoise/test_crud_extended.py`、`tests/ext/orm/sqlalchemy/test_crud.py`、`tests/ext/orm/sqlmodel/test_crud.py`（三 ORM mixin 实现）、`tests/ext/orm/sqlmodel/test_business_methods.py`/`tests/ext/orm/sqlalchemy/test_business_methods.py`（业务 classmethod）、`tests/scaffold/test_service_templates.py`（模板内容断言）
- service 模板渲染后不得含 Tortoise 原生 API（`await db.save()`/`db.update_from_dict(`/`filter(id__in=ids).delete()`）。

### H. codegen 产物命名与接线

- service 文件名：`app/services/{snake}.py`；router：`app/routers/{snake}_router.py`；schema：`app/schemas/{snake}.py`。
- 生成后 `__init__.py` 幂等追加导出：schemas `from .{snake} import *`、services `from . import {snake}`、routers `from .{snake}_router import {snake}_router`。
- 字段类型映射用 `_TYPE_MAP`，未知类型默认 `str`；关系字段（fk/m2m）不出现在 Base schema。
- 文件冲突默认抛 `GenConflictError`（非静默跳过），`--force` 覆盖。
- 守护测试：`tests/generator/test_codegen.py`/`test_codegen_jinja.py`/`test_codegen_init_wiring.py`/`test_codegen_type_mapping.py`

### I. CLI 项目命令一律 re-exec，无 in-process 分支；`_runner` 一律 in-process

`efa run/db/gen` 在 CLI 包内**必须**通过 `uv run --no-sync --directory <root>` 转发到项目 venv，**禁止**保留「原地调用 Core」的代码分支（CLI 在全局工具 venv 看不到项目运行时依赖，in-process 分支对 CLI 是伪抽象）。`easy_fastapi._runner` 只在项目 venv 运行，**必须** in-process 分发到 `easy_fastapi.commands/`，**禁止**二次 re-exec。调用链单向固定（CLI → 项目 venv 的 uvicorn/`_runner` → Core），**禁止**引入 `EFA_IN_PROJECT_VENV` 之类防递归环境变量。

- 守护测试：`tests/cli/test_venv_bridge.py`、`tests/cli/test_run.py`/`test_db.py`/`test_gen.py`（转发命令断言）、`tests/core/test_runner.py`（`_runner` 分发）、`tests/test_dependency_direction.py`（Core 不 import CLI）。
- `easy_fastapi.project` 内 introspector 选择等涉及重型可选依赖的逻辑**必须** lazy import，确保 `import easy_fastapi` 顶层不拖入 tortoise/redis（守护测试 `test_top_level_import_does_not_load_tortoise/redis`）。

### J. Persistence 协议方法必须为 async

`Persistence` 协议（`core/protocols.py`）声明的 `get`/`set`/`delete` 必须为 `async def`。`MemoryPersistence`（core 预注册默认）和 `RedisPersistence`（redis 扩展）均实现为 async 方法。auth router 中 `await persistence.get/set` 是唯一调用方式，同步实现会导致 `TypeError`。

- 守护测试：`tests/core/persistence/test_memory.py`（`MemoryPersistence` 满足 `Persistence` 协议 + async 行为验证）、`tests/ext/redis/test_extension.py`（`RedisPersistence` 满足协议）
- 新增 persistence 实现时，必须将三个方法声明为 `async def`。

### K. i18n 翻译边界：`Result.__new__` / `ResponseResult.__new__` 是唯一翻译点

业务层和异常处理器传英文 msgid 给 `Result`/`ResponseResult`/异常类，`__new__` 内部调用 `_(message)` 翻译。**调用方不得再包 `_()`**，否则导致 `_(_("msgid"))` 双重翻译。

- 守护测试：`tests/test_result.py`（`Result.__new__` 调用 `_()`）、`tests/test_handlers.py`（handler 不预翻译）
- `FailureException`/`UnauthorizedException` 等异常的 `detail` 是英文 msgid，异常处理器将其原样传给 `ResponseResult`，由 `ResponseResult.__new__` 统一翻译。
- `summary=_('...')` 在路由装饰器中是合法的 `_()` 调用（OpenAPI 文档翻译，不经 Result 边界）。I18nExtension.init_app 用 default_locale 预初始化 `_current_translator`，使启动阶段 `_()` 也能正确翻译（而非 fallback 到英文原文）。
- `.mo` 是构建产物，不进版本控制（`.gitignore` 忽略 `*.mo`，含框架仓库和生成项目模板）。三道分发保障：
  1. **wheel 发布**：`packages/easy_fastapi/hatch_build.py` 构建钩子在 `uv build` 时自动编译 `.po`→`.mo` 并 `force_include` 打入 wheel，下游 `pip install` 即可用。
  2. **editable install 兜底**（开发期 `uv.sources` 指向本地源码）：`core/i18n._ensure_mo_compiled` 在 `.mo` 不存在但 `.po` 存在时按需编译（仅此场景触发，wheel 安装时为 no-op）。
  3. **显式入口**：`scripts/compile_mo.py` 供开发者/CI 手动编译框架 `.mo`；生成项目用 `efa i18n compile`。
  - 守护测试：`tests/ext/i18n/test_i18n_extension.py::TestOnDemandCompile`（按需编译三种状态：.mo 缺失编译、.mo 存在跳过、.po 缺失跳过）。

### L. CLI 插件机制防回归要点

CLI 插件发现注册器（`easy_fastapi_cli/plugin_loader.py`）的三个不变量：

1. **`seen[plugin.name] = plugin` 必须在 `register()` 成功之后**——否则注册失败的插件占位，导致同名后到插件被误跳过。
2. **`make_mo` 必须自动注入 `Content-Type: text/plain; charset=UTF-8` header 条目**——缺失 header 会导致部分 gettext 实现无法识别编码。
3. **`_project_dir()` 仅用 `Path.cwd()`，禁止 import `easy_fastapi_cli._guard`**——Core 包（i18n 扩展所在）不得反向依赖 CLI 包，维护 ADR #2/#28 的 Core ↛ CLI 依赖方向。

- 守护测试：`tests/cli/test_plugin_loader.py`（错误隔离测试覆盖第 1 点）、`tests/ext/i18n/test_msgfmt.py`（gettext 可读测试覆盖第 2 点）、`tests/test_dependency_direction.py`（依赖方向测试覆盖第 3 点）。

---

## 三、已知限制

- **非 TTY 交互向导**：CI/管道下 questionary 可能无法交互。`run_wizard` 检测 `not sys.stdin.isatty()` 时回退非交互默认或提示加 `--no-interactive`（待实现）。真实 TTY 预填效果用单元测试 mock questionary 验证，PowerShell 终端需人工确认。
- **CLI 包硬依赖 runtime**：双包后 CLI 硬依赖 runtime，装 CLI 即有 runtime。`efa run` 不再需要额外 `[runtime]` extra。
- **不变量自动化测试覆盖范围**：`test_fragment_dest_never_contains_package_or_project_name` 覆盖 `build_manifest` 产出的 Fragment `dest`；`paths.py`/`marker.py` 源码层仍依赖人工 grep 复核（见硬约束 A）。
- **`use()` 失败不回滚**：`init_app()` 抛异常即启动失败，实例视为失败态，不保证可继续装配其它扩展。调用方应终止启动流程。
- **前端仅最小骨架**：不预置具体前端应用（React/Vue/Next 等），不默认根级 TS 配置。用户在 `frontend/apps/` 自建。`api-sdk` 是唯一维护的前端包（OpenAPI 生成）。`frontend_framework`/`frontend_theme`/`frontend_apps` 三字段已删除（仅驱动已删的 admin 模板）。
- **多站点 static**：v1 单站点托管，`static.sites[]` 留后续。
- **`efa db init` 非幂等**：迁移配置已存在报错，`--force` 覆盖留后续。
- **`efa create` 渲染冲突 `--force`**：in_place 边界情况下遇已存在文件跳过警告，`--force` 覆盖留后续。
- **pnpm 冒烟测试环境依赖**：`test_fullstack_pnpm_install_smoke` 需系统安装 pnpm，CI 未预装时恒跳过。
- **codegen `get_or_create` 非协议强制**：`BaseCRUDMixin` 协议只要求 5 个核心方法，`exists`/`exists_by_email`/`get_or_create` 作为扩展方法在各 ORM 实现但不强制协议。Role 模型无 `username`/`email` 字段，不适用 `exists`/`exists_by_email`。
- **测试 HMAC key 短于 RFC 推荐**：测试 fixture 使用短 secret key（1–23 字节），触发 `InsecureKeyLengthWarning`，仅测试环境影响，生产使用时 key 应 ≥32 字节。
- **i18n .mo 编译**：项目添加新 .po 翻译后用 `efa i18n compile`（纯 Python msgfmt，无需系统 `msgfmt` 命令）。框架仓库 .mo 经 `hatch_build.py` 构建钩子自动编译打入 wheel。
- **i18n 脚手架仅提供 zh_CN 模板**：用户需自行创建其他 locale 目录和 .po 文件（`efa i18n init <locale>`）。

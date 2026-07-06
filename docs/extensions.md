# 扩展

Easy FastAPI 通过 `Extension` 协议 + `ExtensionContext` 实现模块化扩展。所有扩展经 `easy.use(Extension())` 链式注册。

## 五扩展速查

| 扩展 | 作用 | provide 的 service key | 配置 section |
|---|---|---|---|
| `orm.tortoise` | Tortoise ORM 数据层 | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `orm.sqlalchemy` | SQLAlchemy ORM 数据层 | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `orm.sqlmodel` | SQLModel ORM 数据层 | `db_session_factory`, `model_introspector`, `user_model`, `role_model` | `database` |
| `auth` | 跨 ORM 认证（pwdlib + PyJWT） | `token_service`, `require` | `auth` |
| `redis` | Redis 持久化（override） | `persistence` (override) | `redis` |
| `i18n` | 国际化（gettext + contextvars） | `i18n` | `i18n` |
| `static` | 静态文件托管 | — | `static` |

> 三 ORM 共享 `database` section（ORM 无关），由 `DatabaseConfig` 解析 `dialect`/`username`/`password`/`database`/`host`/`port`。`build_uri` 统一生成各 ORM 的连接 URL。

## service key 全表

| key | 提供者 | 消费者 |
|---|---|---|
| `persistence` | core 预注册 `MemoryPersistence`；redis override | auth |
| `db_session_factory` | 各 ORM 扩展 | ORM 内部 repository |
| `model_introspector` | 各 ORM 扩展 | `efa gen` |
| `user_model` | 各 ORM 扩展 | auth |
| `role_model` | 各 ORM 扩展 | 用户路由（角色 CRUD） |
| `token_service` | auth 扩展 | 用户路由 |
| `require` | auth 扩展 | 业务路由权限装饰器 |
| `i18n` | i18n 扩展 | 其他扩展查询当前 locale |

## 配置 section 示例

`easy-fastapi.yaml`：

```yaml
fastapi:
  root_path: /api

database:                 # ORM 无关
  dialect: sqlite         # mysql / postgres / sqlite
  database: db.sqlite3    # sqlite 仅需此项；mysql/postgres 还需 username/password/host/port

auth:
  secret: your-secret-key
  algorithm: HS256
  access_expire_minutes: 1440
  enable_refresh: true       # 是否启用 refresh token
  token_transport: body      # body | cookie（见下方说明）
  cookie:                    # token_transport=cookie 时生效
    name: refresh_token
    path: /auth/refresh
    domain: ~                # null = 不设置 domain
    secure: false
    httponly: true
    samesite: lax

redis:
  enabled: true
  url: redis://localhost:6379/0

i18n:
  default_locale: zh_CN
  available_locales:
    - zh_CN
    - en_US

static:
  enabled: true
  directory: static
  url_path: /static
```

## 装配示例

```python
from fastapi import FastAPI
from easy_fastapi import EasyFastAPI
from easy_fastapi.ext.orm.tortoise.extension import TortoiseExtension
from easy_fastapi.ext.auth.extension import AuthExtension

app = FastAPI()
easy = EasyFastAPI(app, config_path="easy-fastapi.yaml")
easy.use(TortoiseExtension())
easy.use(AuthExtension())
```

> 生成项目的 `app/main.py` 用 `create_app()` 函数封装上述装配（构造 `FastAPI` → `EasyFastAPI(app, config_path=...)` → 链式 `use()` → 挂载业务路由/静态），模块级 `app = create_app()` 供 `efa run`（uvicorn）加载；所有 import 集中在文件顶部。

## 自定义扩展

实现 `Extension` 协议（`config_model` + `init_app`），`provide` 注册服务供其他扩展 `require`：

```python
from fastapi import FastAPI
from pydantic import BaseModel
from easy_fastapi import Extension, ExtensionContext

class MyConfig(BaseModel):
    enabled: bool = True

class MyExtension:
    name = "my_ext"

    def config_model(self) -> type[BaseModel] | None:
        return MyConfig

    def init_app(self, app: FastAPI, config: MyConfig | None, ctx: ExtensionContext) -> None:
        if config and config.enabled:
            ctx.provide("my_service", MyService())
            # 消费其他扩展提供的服务
            # repo = ctx.require("user_model", UserModelProtocol)

# 注册
easy.use(MyExtension())
```

## 跨 ORM 契约

`auth` 扩展**零 ORM import**——不直接 import tortoise/sqlalchemy/sqlmodel，而是经 `ctx.require("user_model", UserModelProtocol)` 消费 ORM 扩展提供的服务。任意 ORM 扩展只要 provide 了符合 `UserModelProtocol` 协议的实现，auth 即可工作。

## i18n 国际化

i18n 扩展基于 Python stdlib `gettext` + `contextvars` 实现运行时多语言切换。中间件读取 `Accept-Language` header 匹配可用 locale，设置 contextvars，后续代码通过 `_()` 翻译。

**翻译边界**：`Result.__new__` / `ResponseResult.__new__` 是唯一翻译点——业务层传英文 msgid，`__new__` 内部调用 `_(message)` 翻译。调用方**不得**再包 `_()`（会导致双重翻译）。

```python
from easy_fastapi import Result, FailureException, _

# ✅ 正确：msgid 直接传给 Result/异常
return Result("Login successful", data=user)
raise FailureException("User not found")

# ❌ 错误：双重翻译
return Result(_("Login successful"), data=user)
raise FailureException(_("User not found"))

# ✅ 正确：非 Result 边界的翻译（如路由 summary）
@router.get('', summary=_('Query User'))
async def get(id: int): ...
```

**Fallback 链**：项目翻译 → 框架翻译 → msgid 英文原文。项目可在 `locales/` 下覆盖框架翻译。

**使用方式**：

```python
# app/extensions/i18n.py
from easy_fastapi.ext.i18n.extension import I18nExtension
i18n = I18nExtension()

# app_factory.py — i18n 最后 .use()（中间件后注册先执行，最早设置 locale）
efa.use(orm).use(auth).use(i18n)
```

**添加新 locale**：

1. 运行 `efa i18n init <locale>`（如 `efa i18n init en_US`）
2. 编辑生成的 `.po` 文件，填写翻译
3. 编译：`efa i18n compile`（纯 Python，无需系统 msgfmt）
4. 更新 `easy-fastapi.yaml` 的 `available_locales`

**i18n CLI 命令**：

```bash
efa i18n init zh_CN    # 初始化翻译目录和 .po 文件
efa i18n compile       # 编译 .po → .mo（纯 Python，无需系统 msgfmt）
efa i18n update        # 扫描源码 _() 调用，更新 .po 文件
```

推荐工作流：`efa i18n init` → 编辑 .po → `efa i18n compile` → 运行项目。新增代码后运行 `efa i18n update` 同步 msgid。

详细决策见 [DECISIONS.md](DECISIONS.md) ADR #35 / 硬约束 K。

## auth token 传输双模式

`auth` 扩展支持两种 refresh token 传输方式，由 `auth.token_transport` 配置切换：

| 模式 | 旧 refresh token 入参 | 新 refresh token 出参 | 适用场景 |
|---|---|---|---|
| `body`（默认） | `Authorization: Bearer <old_refresh>` 请求头 | 响应体 `refresh_token` 字段 | SPA / 移动端，前端自行管理 token |
| `cookie` | HttpOnly cookie（`cookie.name`，默认 `refresh_token`） | 写入同名 HttpOnly cookie，响应体**不**返回 | 防 XSS 盗取 refresh token 的 Web 应用 |

- `enable_refresh: false` 时**不注册** `/auth/refresh` 路由，登录响应也不返回 refresh_token（access-only 模式）。
- cookie 模式下登录/刷新响应体不返回 `refresh_token`（避免双重暴露），仅通过 `Set-Cookie` 下发。
- logout 路由始终将 access_token 的 `jti` 加入 persistence 黑名单（TTL = token 剩余有效期），cookie 模式额外清除 refresh_token cookie。
- 黑名单依赖 `persistence` 服务（core 预注册 `MemoryPersistence`，redis 扩展 override 为 `RedisPersistence`）。
- cookie 配置封装在 `CookieOptions` 结构体中（`name`/`path`/`domain`/`secure`/`httponly`/`samesite`），`domain: ~` 表示不设置 domain。

## `@require` 权限装饰器

auth 扩展 provide `require` 装饰器工厂，生成项目从 ctx 取回并暴露为 `auth.require`：

```python
from app.extensions.auth import auth

@router.get("")
@auth.require                      # 仅需登录
async def list_items(): ...

@router.get("/admin")
@auth.require(scopes={"admin"})    # 需 admin scope（子集语义）
async def admin_only(): ...
```

- scope 检查用子集语义：`required.issubset(user_scopes)`（用户需拥有全部 required scopes）
- `AuthUser` 协议声明 `scopes: list[str]` 属性
- 未登录（`current_user()` 闭包抛 UnauthorizedException）抛 401；权限不足抛 403；401 响应带 `WWW-Authenticate: Bearer` 头

## ExtendedCRUD 统一接口

三 ORM 模型继承各自的 CRUDMixin（`ExtendedCRUD`/`SQLAlchemyCRUDMixin`/`SQLModelCRUDMixin`），满足 `BaseCRUDMixin` 协议，获得统一 CRUD 能力。service 层只调这些方法：

| 方法 | 说明 |
|---|---|
| `Model.by_id(id, prefetch=None)` | 按 id 查（可预加载关系） |
| `Model.paginate(page_index, page_size, prefetch=None)` | 分页，返回 `Pagination` |
| `Model.create(**kwargs)` | 创建 |
| `Model.update_from_dict(instance, data)` | 更新字段 |
| `Model.delete_by_ids(ids)` | 批量删除，返回计数 |
| `Model.exists(username)` / `exists_by_email(email)` | 存在性检查（User 专用） |
| `Model.get_or_create(**kwargs)` | 存在则取回，否则创建 |

```python
# 生成项目的 service 层用法
async def get(id: int):
    db = await models.Article.by_id(id)
    if not db:
        raise FailureException('Article 不存在')
    return Result(data=db)
```

详细决策见 [DECISIONS.md](DECISIONS.md) ADR #22 / ADR #33 / 硬约束 G、J。

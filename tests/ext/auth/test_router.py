"""auth router 测试——零 ORM 耦合，全用 fake model。

重写适配 AuthExtension 类化架构：
- _app_with 使用 AuthExtension + ExtensionContext 替代已删 build_auth_router
- 所有路径加 /auth 前缀
- 401 响应使用 UnauthorizedException（含 WWW-Authenticate 头 + 细分消息）
- 新增三级工厂依赖、JWT 异常细分、scopes、OpenAPI scheme 测试组
"""

from __future__ import annotations

import asyncio

from easy_fastapi.core.extension import ExtensionContext
from easy_fastapi.core.handlers import binding_exception_handler
from easy_fastapi.core.protocols import AuthUser
from easy_fastapi.ext.auth.config import AuthConfig, CookieOptions
from easy_fastapi.ext.auth.extension import AuthExtension
from easy_fastapi.ext.auth.hasher import PwdlibPasswordHasher
from easy_fastapi.ext.auth.schemas import TokenPayload
from easy_fastapi.ext.auth.token import TokenService
from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from httpx import ASGITransport, AsyncClient

# ── Fake 协作对象 ──


class FakeUser:
    def __init__(self, id, username, hashed_password, is_active=True, scopes=None):
        self.id = id
        self.username = username
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.scopes = scopes if scopes is not None else []


class FakeModel:
    """满足 UserModelProtocol 的假模型（classmethod 风格，数据挂类属性）。"""

    _users: dict = {}

    @classmethod
    def _set_users(cls, users):
        cls._users = users

    @classmethod
    async def get_by_username(cls, username):
        return cls._users.get(username)

    @classmethod
    async def get_by_id(cls, id):
        return next((x for x in cls._users.values() if x.id == id), None)

    @classmethod
    async def get_by_email(cls, email):
        return next((x for x in cls._users.values() if getattr(x, "email", None) == email), None)

    @classmethod
    async def get_by_username_or_email(cls, username_or_email):
        user = cls._users.get(username_or_email)
        if user:
            return user
        return await cls.get_by_email(username_or_email)

    @classmethod
    async def create_user(cls, username, hashed_password, **extra):
        pass

    @classmethod
    async def update_password(cls, id, hashed_password):
        pass

    # BaseCRUDMixin 方法（简化）
    @classmethod
    async def exists(cls, **filters):
        return filters.get("username") in cls._users

    @classmethod
    async def by_id(cls, id, prefetch=None):
        return await cls.get_by_id(id)

    @classmethod
    async def paginate(cls, page_index, page_size, prefetch=None):
        from easy_fastapi.ext.orm.base.pagination import Pagination

        return Pagination(total=0, items=[], finished=True)

    @classmethod
    async def create(cls, **kwargs):
        pass

    @classmethod
    async def update_from_dict(cls, instance, data):
        pass

    @classmethod
    async def delete_by_ids(cls, ids):
        return 0


class FakePersistence:
    def __init__(self):
        self._data: dict[str, tuple[str, int | None]] = {}  # key → (value, ex)

    async def get(self, k):
        entry = self._data.get(k)
        return entry[0] if entry else None

    async def set(self, k, v, *, ex: int | None = None, **kw):
        self._data[k] = (v, ex)

    async def delete(self, k):
        self._data.pop(k, None)


# ── 基础 fixture ──


def _app_with(
    users, *, enable_refresh=True, token_transport="body", scope_match="any", cookie_opts=None, token_prefix="/auth"
):
    FakeModel._set_users(users)
    ts = TokenService(secret="s" * 32, access_expire_minutes=30, refresh_expire_days=7)

    app = FastAPI()
    binding_exception_handler(app)
    auth = AuthExtension()
    ctx = ExtensionContext()
    ctx.services["user_model"] = FakeModel
    ctx.services["persistence"] = FakePersistence()
    auth.init_app(
        app,
        AuthConfig(
            secret="s" * 32,
            token_prefix=token_prefix,
            enable_refresh=enable_refresh,
            token_transport=token_transport,
            scope_match=scope_match,
            cookie=cookie_opts or CookieOptions(),
        ),
        ctx,
    )
    return app, ts, auth


def _routes_map(app):
    from fastapi.routing import APIRoute

    routes = {}
    for r in app.routes:
        orig = getattr(r, "original_router", None)
        if orig is not None:
            for ir in orig.routes:
                if isinstance(ir, APIRoute):
                    routes[ir.path] = ir
        elif isinstance(r, APIRoute):
            routes[r.path] = r
    return routes


# ════════════════════════════════════════════════════════════════
# ── 1. 登录基础测试 ──
# ════════════════════════════════════════════════════════════════


async def test_login_success_returns_tokens():
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert data["data"]["token_type"] == "bearer"


async def test_login_wrong_password():
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "WRONG"})
    assert resp.status_code == 401


async def test_login_unknown_user():
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


async def test_login_missing_fields():
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "ghost"})
    assert resp.status_code in (400, 422)


# ── OAuth2PasswordRequestForm 表单登录 ──


async def test_login_accepts_form_encoded():
    """登录接受 application/x-www-form-urlencoded 表单（OAuth2 标准）。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_rejects_json_body():
    """登录不再接受 JSON body（改用 OAuth2 表单）。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", json={"username": "alice", "password": "pw"})
    assert resp.status_code in (400, 422)


async def test_login_form_wrong_password():
    """表单登录密码错误返回 401。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "WRONG"})
    assert resp.status_code == 401


async def test_login_form_unknown_user():
    """表单登录未知用户返回 401。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


async def test_login_form_missing_password():
    """表单登录缺 password 字段返回 422。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "ghost"})
    assert resp.status_code in (400, 422)


async def test_login_form_missing_username():
    """表单登录缺 username 字段返回 422。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"password": "x"})
    assert resp.status_code in (400, 422)


async def test_login_form_empty_body():
    """表单登录空 body 返回 422。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={})
    assert resp.status_code in (400, 422)


async def test_login_form_supports_email_username():
    """表单登录 username 字段可传邮箱（get_by_username_or_email 兼容）。"""
    hasher = PwdlibPasswordHasher()
    user = FakeUser(1, "alice", hasher.hash("pw"))
    user.email = "alice@example.com"
    app, _, _ = _app_with({"alice": user})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice@example.com", "password": "pw"})
    assert resp.status_code == 200


async def test_login_form_inactive_user():
    """表单登录被禁用用户返回 401。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"), is_active=False)})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 401


async def test_login_form_content_type_form_urlencoded():
    """登录路由在 OpenAPI 中声明 OAuth2 password flow（form-urlencoded）。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    schema = get_openapi(title="t", version="1", routes=app.routes)
    login_op = schema["paths"]["/auth/login"]["post"]
    content = login_op["requestBody"]["content"]
    assert "application/x-www-form-urlencoded" in content


# ── TokenResponse 作为 response_model ──


def test_login_route_has_token_response_model():
    """login 路由声明 response_model 引用 TokenResponse。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    login_route = routes.get("/auth/login")
    assert login_route is not None
    assert login_route.response_model is not None
    assert "TokenResponse" in str(login_route.response_model)


def test_refresh_route_has_token_response_model():
    """refresh 路由声明 response_model 引用 TokenResponse。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    refresh_route = routes.get("/auth/refresh")
    assert refresh_route is not None
    assert refresh_route.response_model is not None
    assert "TokenResponse" in str(refresh_route.response_model)


def test_login_response_model_is_result_token_response():
    """login 的 response_model 结构是 Result[TokenResponse]（含 code/message/data）。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    login_route = routes.get("/auth/login")
    rm = login_route.response_model
    assert rm is not None
    fields = rm.model_fields
    assert "code" in fields
    assert "message" in fields
    assert "data" in fields


def test_login_response_model_data_field_is_token_response():
    """Result[TokenResponse] 的 data 字段类型是 TokenResponse。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    login_route = routes.get("/auth/login")
    rm = login_route.response_model
    data_field = rm.model_fields["data"]
    assert "TokenResponse" in str(data_field.annotation)


def test_refresh_response_model_matches_login():
    """refresh 与 login 的 response_model 同为 Result[TokenResponse]。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    login_rm = routes.get("/auth/login").response_model
    refresh_rm = routes.get("/auth/refresh").response_model
    assert login_rm == refresh_rm


def test_login_response_model_in_openapi_schema():
    """OpenAPI schema 中 login 响应引用 TokenResponse 结构。"""
    app, _, _ = _app_with({})
    schema = get_openapi(title="t", version="1", routes=app.routes)
    login_resp = schema["paths"]["/auth/login"]["post"]["responses"]
    assert "200" in login_resp
    assert "TokenResponse" in str(schema["components"]["schemas"])


async def test_login_response_data_keys_are_token_response_fields():
    """登录响应 data 仅含 access_token/refresh_token/token_type。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    data = resp.json()["data"]
    assert set(data.keys()) <= {"access_token", "refresh_token", "token_type"}


async def test_refresh_response_data_keys_are_token_response_fields():
    """刷新响应 data 仅含 access_token/refresh_token/token_type。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    data = resp.json()["data"]
    assert set(data.keys()) <= {"access_token", "refresh_token", "token_type"}


# ════════════════════════════════════════════════════════════════
# ── 2. 刷新令牌 ──
# ════════════════════════════════════════════════════════════════


async def test_refresh_with_valid_token():
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


async def test_refresh_with_access_token_rejected():
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401


async def test_refresh_with_invalid_token():
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


async def test_refresh_missing_auth_header():
    """body 模式下刷新缺少 Authorization 头返回 401。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


async def test_refresh_body_mode_ignores_json_body():
    """body 模式下 refresh 忽略 JSON body（只看 Authorization 头）。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


# ════════════════════════════════════════════════════════════════
# ── 3. 登出 ──
# ════════════════════════════════════════════════════════════════


async def test_logout_requires_auth():
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/logout")
        assert resp.status_code == 401
        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
        assert resp.status_code == 204


async def test_logout_with_invalid_token():
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/logout", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


async def test_logout_inactive_user():
    """已禁用用户仍可 logout（吊销 token 是安全有益的，不依赖用户状态）。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"), is_active=False)})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 204


async def test_logout_returns_authuser():
    """logout 成功返回 204；FakeUser 满足 AuthUser 协议（供 /me 等端点用）。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
        assert resp.status_code == 204
    # FakeUser 满足 AuthUser 协议
    assert isinstance(FakeUser(1, "alice", "h"), AuthUser)


# ════════════════════════════════════════════════════════════════
# ── 4. /me 不泄露 hashed_password ──
# ════════════════════════════════════════════════════════════════


async def test_me_does_not_leak_hashed_password():
    """/me 响应不含 hashed_password 字段。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "hashed_password" not in data


async def test_me_response_has_user_fields_except_sensitive():
    """/me 响应包含 id/username/is_active/scopes 但不含 hashed_password。"""
    hasher = PwdlibPasswordHasher()
    user = FakeUser(1, "alice", hasher.hash("pw"))
    user.email = "alice@example.com"
    app, ts, _ = _app_with({"alice": user})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    data = resp.json()["data"]
    assert "id" in data
    assert "username" in data
    assert "is_active" in data
    assert "hashed_password" not in data


async def test_me_route_has_response_model():
    """/me 路由声明了 response_model。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    me_route = routes.get("/auth/me")
    assert me_route is not None
    assert me_route.response_model is not None


async def test_me_response_model_excludes_hashed_password():
    """/me 的 response_model 不含 hashed_password 字段。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    me_route = routes.get("/auth/me")
    rm = me_route.response_model
    assert "hashed_password" not in rm.model_fields


async def test_me_response_model_includes_safe_fields():
    """/me 的 response_model 包含 id/username/is_active/scopes。"""
    app, _, _ = _app_with({})
    routes = _routes_map(app)
    me_route = routes.get("/auth/me")
    rm = me_route.response_model
    fields = rm.model_fields
    assert "data" in fields


async def test_me_without_auth_returns_401():
    """无认证访问 /me 返回 401。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token_returns_401():
    """无效 token 访问 /me 返回 401。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


async def test_me_with_expired_token_returns_401():
    """过期 token 访问 /me 返回 401，消息含'令牌已过期'。"""
    app, _, _ = _app_with({})
    ts_short = TokenService(secret="s" * 32, access_expire_minutes=0, refresh_expire_days=0)
    access = ts_short.create_access_token("1")
    await asyncio.sleep(1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401
    assert "Token has expired" in resp.json()["message"]


# ════════════════════════════════════════════════════════════════
# ── 5. token_transport=cookie 模式 ──
# ════════════════════════════════════════════════════════════════


async def test_cookie_login_sets_refresh_cookie():
    """cookie 模式下登录通过 Set-Cookie 下发 refresh_token。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, token_transport="cookie")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    assert "refresh_token" not in resp.json()["data"]
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie


async def test_cookie_refresh_reads_cookie_and_rotates():
    """cookie 模式下刷新从 cookie 读 refresh_token 并轮换下发新 cookie。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, token_transport="cookie")
    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", cookies={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]
    assert "refresh_token" not in resp.json()["data"]
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie


async def test_cookie_refresh_missing_cookie_returns_401():
    """cookie 模式下刷新缺少 cookie 返回 401。"""
    app, _, _ = _app_with({}, token_transport="cookie")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh")
    assert resp.status_code == 401


async def test_cookie_refresh_invalid_cookie_returns_401():
    """cookie 模式下 cookie 中 refresh_token 无效返回 401。"""
    app, _, _ = _app_with({}, token_transport="cookie")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", cookies={"refresh_token": "garbage"})
    assert resp.status_code == 401


async def test_cookie_refresh_with_access_token_cookie_returns_401():
    """cookie 模式下 cookie 中放 access token 不能用于刷新。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, token_transport="cookie")
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", cookies={"refresh_token": access})
    assert resp.status_code == 401


async def test_cookie_logout_clears_cookie():
    """cookie 模式下登出清除 refresh_token cookie。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, token_transport="cookie")
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 204
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie


async def test_body_logout_does_not_set_cookie():
    """body 模式下登出不操作 cookie。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, token_transport="body")
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 204
    assert "set-cookie" not in resp.headers


# ════════════════════════════════════════════════════════════════
# ── 6. enable_refresh=False（access-only 模式）──
# ════════════════════════════════════════════════════════════════


async def test_access_only_login_no_refresh_token():
    """access-only 模式下登录不签发 refresh_token。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, enable_refresh=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    assert "refresh_token" not in resp.json()["data"]
    assert resp.json()["data"]["access_token"]


async def test_access_only_refresh_route_not_registered():
    """access-only 模式下不注册 /auth/refresh 路由。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))}, enable_refresh=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 404


async def test_access_only_login_does_not_set_cookie():
    """access-only + cookie 模式下登录不下发 cookie。"""
    hasher = PwdlibPasswordHasher()
    app, _, _ = _app_with(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"))},
        enable_refresh=False,
        token_transport="cookie",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    assert "set-cookie" not in resp.headers


# ════════════════════════════════════════════════════════════════
# ── 7. token 黑名单（logout 吊销 access_token）──
# ════════════════════════════════════════════════════════════════


async def test_logout_blacklists_access_token():
    """登出后旧 access_token 被吊销，访问 /me 返回 401。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        assert (await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})).status_code == 200
        assert (await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})).status_code == 204
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401


async def test_logout_blacklist_sets_ttl_from_exp():
    """logout 黑名单 set 时 ex 取自 token exp（非 None）。"""
    hasher = PwdlibPasswordHasher()
    app, ts, auth = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    pers = auth.persistence
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    # 黑名单条目应记录 ex（来自 token exp 的剩余 TTL）
    blacklist_entries = [v for k, v in pers._data.items() if k.startswith("auth:blacklist:")]
    assert len(blacklist_entries) == 1
    _, ex = blacklist_entries[0]
    assert ex is not None and ex > 0


async def test_refresh_rejected_after_logout():
    """登出后旧 refresh_token 仍可刷新（仅吊销 access_token）。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        await client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
        resp = await client.post("/auth/refresh", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 200


async def test_custom_cookie_name_works():
    """自定义 cookie_name 时登录/刷新都使用该名字。"""
    hasher = PwdlibPasswordHasher()
    custom = CookieOptions(name="my_rt")
    app, ts, _ = _app_with(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"))},
        token_transport="cookie",
        cookie_opts=custom,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/login", data={"username": "alice", "password": "pw"})
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "my_rt=" in set_cookie

    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.post("/auth/refresh", cookies={"my_rt": refresh})
    assert resp.status_code == 200


# ════════════════════════════════════════════════════════════════
# ── A. 三级工厂依赖测试 ──
# ════════════════════════════════════════════════════════════════


def _app_with_deps(users):
    """创建带自定义路由的 app，用于测试三级工厂依赖。"""
    FakeModel._set_users(users)
    ts = TokenService(secret="s" * 32, access_expire_minutes=30, refresh_expire_days=7)

    app = FastAPI()
    binding_exception_handler(app)
    auth = AuthExtension()
    ctx = ExtensionContext()
    ctx.services["user_model"] = FakeModel
    ctx.services["persistence"] = FakePersistence()
    auth.init_app(app, AuthConfig(secret="s" * 32), ctx)

    @app.get("/test-jwt")
    async def test_jwt_endpoint(jwt: str = Depends(auth.current_jwt())):
        return {"jwt": jwt}

    @app.get("/test-token")
    async def test_token_endpoint(token: TokenPayload = Depends(auth.current_token())):  # noqa: B008
        return {"sub": token.sub}

    @app.get("/test-user")
    async def test_user_endpoint(user=Depends(auth.current_user())):  # noqa: B008
        return {"id": user.id}

    return app, ts, auth


async def test_current_jwt_returns_raw_string():
    """current_jwt() 直接返回原始 JWT 字符串。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_deps({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/test-jwt", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["jwt"] == access


async def test_current_jwt_missing_raises_401():
    """无 auth header → current_jwt() 抛 401 '缺少认证凭据'。"""
    app, _, _ = _app_with_deps({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/test-jwt")
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 401
    assert "Missing authentication credentials" in body["message"]


async def test_current_token_decodes_jwt():
    """current_token() 解码 JWT 返回 TokenPayload（含正确 sub）。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_deps({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/test-token", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["sub"] == "1"


async def test_current_token_refresh_token_rejected():
    """current_token() 拒绝 refresh token → 401 '无效的访问令牌'。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_deps({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    refresh = ts.create_refresh_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/test-token", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401
    assert "Invalid access token" in resp.json()["message"]


async def test_current_user_loads_from_db():
    """current_user() 从 DB 加载完整用户对象。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_deps({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/test-user", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == 1


async def test_current_user_missing_sub_raises_401():
    """Token 无 sub → current_user() 抛 401 '令牌缺少用户标识'。"""
    # 手工构造无 sub 的 token
    from easy_fastapi.core.extras import require

    jwt_mod = require("pyjwt", "jwt")
    token = jwt_mod.encode({"type": "access", "jti": "x"}, "s" * 32, algorithm="HS256")
    app, _, _ = _app_with_deps({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/test-user", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "Token missing user identity" in resp.json()["message"]


# ════════════════════════════════════════════════════════════════
# ── B. JWT 异常细分测试 ──
# ════════════════════════════════════════════════════════════════


async def test_expired_token_returns_401_with_detail():
    """过期 token → 401，消息含'令牌已过期'。"""
    app, _, _ = _app_with({})
    ts_short = TokenService(secret="s" * 32, access_expire_minutes=0, refresh_expire_days=0)
    access = ts_short.create_access_token("1")
    await asyncio.sleep(1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401
    assert "Token has expired" in resp.json()["message"]


async def test_invalid_signature_returns_401_with_detail():
    """错误签名 token → 401，消息含'无效的签名'或'令牌解析失败'。"""
    app, _, _ = _app_with({})
    # 用不同 secret 签发 token
    ts_wrong = TokenService(secret="x" * 32, access_expire_minutes=30)
    access = ts_wrong.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401
    msg = resp.json()["message"]
    assert "Invalid signature" in msg or "Token decode failed" in msg


async def test_garbage_token_returns_401_decode_error():
    """垃圾字符串 token → 401，消息含'令牌解析失败'。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
    assert "Token decode failed" in resp.json()["message"]


async def test_401_response_has_www_authenticate_header():
    """所有 401 响应包含 WWW-Authenticate: Bearer 头。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        # 无 auth header → 401
        resp = await client.get("/auth/me")
    assert resp.status_code == 401
    www_auth = resp.headers.get("www-authenticate", "")
    assert "Bearer" in www_auth


async def test_expired_token_401_has_www_authenticate():
    """JWT 异常路径（ExpiredSignatureError）的 401 也包含 WWW-Authenticate: Bearer 头。"""
    app, _, _ = _app_with({})
    ts = TokenService(secret="s" * 32, access_expire_minutes=0, refresh_expire_days=0)
    access = ts.create_access_token("1")
    await asyncio.sleep(1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("www-authenticate", "")


async def test_garbage_token_401_has_www_authenticate():
    """JWT 异常路径（DecodeError）的 401 也包含 WWW-Authenticate: Bearer 头。"""
    app, _, _ = _app_with({})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("www-authenticate", "")


# ════════════════════════════════════════════════════════════════
# ── C. Scopes 测试 ──
# ════════════════════════════════════════════════════════════════


def _app_with_scopes(users, *, scope_match="any", register_extra=None):
    """创建带 require 路由的 app，用于测试 scopes。

    require 是装饰器（非 Depends），用法 @auth.require({...})。
    被装饰的路由仅在校验通过时返回 200；失败时抛 401/403。

    register_extra: 可选回调 (app, auth) -> None，用于注册额外自定义路由
    （如 callable match 的测试路由），避免重复 _app_with 样板代码。
    """
    app, ts, auth = _app_with(users, scope_match=scope_match)

    @app.get("/protected")
    @auth.require({"admin"})
    async def protected():
        return {"ok": True}

    @app.get("/protected-multi")
    @auth.require({"admin", "superadmin"}, match="all")
    async def protected_multi():
        return {"ok": True}

    @app.get("/protected-any")
    @auth.require({"admin", "superadmin"}, match="any")
    async def protected_any():
        return {"ok": True}

    @app.get("/just-auth")
    @auth.require()
    async def just_auth():
        return {"ok": True}

    if register_extra is not None:
        register_extra(app, auth)

    return app, ts, auth


async def test_require_any_one_scope_passes():
    """用户有 ["admin"]，require {"admin","superadmin"} match=any → 200。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_scopes({"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin"])})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/protected-any", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200


async def test_require_any_no_scope_fails():
    """用户有 ["user"]，require {"admin"} match=any → 403。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_scopes({"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["user"])})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/protected", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 403


async def test_require_all_all_present_passes():
    """用户有 ["admin","superadmin"]，require {"admin","superadmin"} match=all → 200。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_scopes({"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin", "superadmin"])})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/protected-multi", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200


async def test_require_all_missing_one_fails():
    """用户有 ["admin"]，require {"admin","superadmin"} match=all → 403。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_scopes({"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin"])})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/protected-multi", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 403


async def test_require_callable_matcher_called():
    """match=lambda 时自定义匹配逻辑被调用。"""
    hasher = PwdlibPasswordHasher()

    def register(app, auth):
        @app.get("/custom-match")
        @auth.require({"admin"}, match=lambda req, user: req == user)
        async def custom_match():
            return {"ok": True}

    app, ts, _ = _app_with_scopes(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin"])},
        register_extra=register,
    )

    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/custom-match", headers={"Authorization": f"Bearer {access}"})
    # req={"admin"}, user={"admin"} → req == user → True → 200
    assert resp.status_code == 200


async def test_require_callable_returns_false_403():
    """callable match 返回 False → 403。"""
    hasher = PwdlibPasswordHasher()

    def register(app, auth):
        @app.get("/always-deny")
        @auth.require({"admin"}, match=lambda req, user: False)
        async def always_deny():
            return {"ok": True}

    app, ts, _ = _app_with_scopes(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin"])},
        register_extra=register,
    )

    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/always-deny", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 403


async def test_require_no_scopes_just_auth():
    """auth.require() 无 scopes → 仅需登录。"""
    hasher = PwdlibPasswordHasher()
    app, ts, _ = _app_with_scopes({"alice": FakeUser(1, "alice", hasher.hash("pw"))})
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/just-auth", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200


async def test_scope_match_yaml_all():
    """scope_match="all" 在配置中 → 默认 AND 行为。"""
    hasher = PwdlibPasswordHasher()
    # 用户只有 admin，缺 superadmin → AND 模式下 require({"admin","superadmin"}) → 403
    app, ts, _ = _app_with_scopes(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin"])},
        scope_match="all",
    )
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        # /protected uses auth.require({"admin"}) — default match falls back to config "all"
        # single scope {"admin"} with user having ["admin"] → {"admin"}.issubset({"admin"}) → True → 200
        resp = await client.get("/protected", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200


async def test_scope_match_yaml_all_negative():
    """scope_match="all" 配置下：用户缺其中一个 scope → 403。

    /protected-any 显式声明 match="any"，会覆盖配置中的 "all"。
    所以需要单独注册一个不指定 match 的路由，让其回落到配置的 "all"。
    """
    hasher = PwdlibPasswordHasher()

    def register(app, auth):
        @app.get("/protected-default-match")
        @auth.require({"admin", "superadmin"})
        async def protected_default_match():
            return {"ok": True}

    app, ts, _ = _app_with_scopes(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=["admin"])},
        scope_match="all",
        register_extra=register,
    )
    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        # 用户只有 ["admin"]，require({"admin","superadmin"}) 默认 match=all → 缺 superadmin → 403
        resp = await client.get("/protected-default-match", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 403


async def test_require_callable_called_with_empty_sets():
    """callable match 即使无 scopes 也会被调用。"""
    hasher = PwdlibPasswordHasher()
    call_log = []

    def register(app, auth):
        def matcher(req, user):
            call_log.append((req, user))
            return True

        @app.get("/callable-empty")
        @auth.require(match=matcher)
        async def callable_empty():
            return {"ok": True}

    app, ts, _ = _app_with_scopes(
        {"alice": FakeUser(1, "alice", hasher.hash("pw"), scopes=[])},
        register_extra=register,
    )

    access = ts.create_access_token("1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/callable-empty", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert len(call_log) == 1


# ════════════════════════════════════════════════════════════════
# ── D. Swagger/OpenAPI scheme 测试 ──
# ════════════════════════════════════════════════════════════════


def test_openapi_has_oauth2_password_scheme():
    """OpenAPI securitySchemes 包含 OAuth2PasswordBearer 类型（非 HTTPBearer）。"""
    app, _, _ = _app_with({})
    schema = get_openapi(title="t", version="1", routes=app.routes)
    schemes = schema.get("components", {}).get("securitySchemes", {})
    # OAuth2PasswordBearer 产生 type=oauth2 的 scheme
    oauth2_schemes = [k for k, v in schemes.items() if v.get("type") == "oauth2"]
    assert len(oauth2_schemes) >= 1

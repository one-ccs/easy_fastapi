"""@require 权限装饰器测试（含 scopes 可配置校验）。"""

from easy_fastapi.ext.auth.decorator import make_require
from fastapi import FastAPI
from fastapi.testclient import TestClient


class FakeUser:
    """模拟用户对象。"""

    def __init__(self, user_id: int, scopes: list[str] | None = None):
        self.id = user_id
        self.scopes = scopes or []


# ── 基础功能 ──


def test_require_is_callable():
    async def current_user():
        return FakeUser(1)

    require = make_require(current_user)
    assert callable(require)


def test_public_route_works():
    app = FastAPI()
    _current_user = FakeUser(1, scopes=["user"])

    async def current_user():
        return _current_user

    require = make_require(current_user)

    @app.get("/public")
    async def public():
        return {"message": "public"}

    @app.get("/protected")
    @require
    async def protected():
        return {"message": "protected"}

    with TestClient(app) as client:
        assert client.get("/public").status_code == 200
        assert client.get("/protected").status_code == 200


# ── 未登录 → 401 ──


def test_require_returns_401_when_no_user():
    app = FastAPI()

    async def current_user():
        return None

    require = make_require(current_user)

    @app.get("/protected")
    @require
    async def protected():
        return {"message": "protected"}

    @app.get("/admin")
    @require({"admin"})
    async def admin():
        return {"message": "admin"}

    with TestClient(app) as client:
        assert client.get("/protected").status_code == 401
        assert client.get("/admin").status_code == 401


def test_401_response_includes_www_authenticate_header():
    app = FastAPI()

    async def current_user():
        return None

    require = make_require(current_user)

    @app.get("/protected")
    @require
    async def protected():
        return {"message": "protected"}

    with TestClient(app) as client:
        resp = client.get("/protected")
    assert resp.headers.get("www-authenticate") == "Bearer"


# ── scopes any（默认 OR）──


def test_scopes_any_user_has_one_passes():
    """默认 OR：require({'admin','super'}) 且用户有 admin → 200。"""
    app = FastAPI()
    require = make_require(lambda: None)  # 占位

    async def current_user():
        return FakeUser(1, scopes=["admin"])

    require = make_require(current_user)

    @app.get("/multi")
    @require({"admin", "super"})
    async def multi():
        return {"message": "multi"}

    with TestClient(app) as client:
        assert client.get("/multi").status_code == 200


def test_scopes_any_user_has_neither_fails():
    """默认 OR：require({'admin','super'}) 且用户都无 → 403。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=[])

    require = make_require(current_user)

    @app.get("/multi")
    @require({"admin", "super"})
    async def multi():
        return {"message": "multi"}

    with TestClient(app) as client:
        assert client.get("/multi").status_code == 403


def test_scopes_any_single_scope_match():
    """默认 OR：require({'admin'}) 且用户只有 admin → 200。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["admin"])

    require = make_require(current_user)

    @app.get("/admin")
    @require({"admin"})
    async def admin():
        return {"message": "admin"}

    with TestClient(app) as client:
        assert client.get("/admin").status_code == 200


def test_scopes_any_single_scope_no_match():
    """默认 OR：require({'admin'}) 且用户只有 super → 403。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["super"])

    require = make_require(current_user)

    @app.get("/admin")
    @require({"admin"})
    async def admin():
        return {"message": "admin"}

    with TestClient(app) as client:
        assert client.get("/admin").status_code == 403


# ── scopes all（AND）──


def test_scopes_all_user_has_both_passes():
    """match='all'：require({'admin','super'}, match='all') 且用户同时有两者 → 200。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["admin", "super"])

    require = make_require(current_user, scope_match="any")

    @app.get("/multi")
    @require({"admin", "super"}, match="all")
    async def multi():
        return {"message": "multi"}

    with TestClient(app) as client:
        assert client.get("/multi").status_code == 200


def test_scopes_all_user_has_only_one_fails():
    """match='all'：require({'admin','super'}, match='all') 但用户只有 admin → 403。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["admin"])

    require = make_require(current_user)

    @app.get("/multi")
    @require({"admin", "super"}, match="all")
    async def multi():
        return {"message": "multi"}

    with TestClient(app) as client:
        assert client.get("/multi").status_code == 403


# ── scopes callable 自定义 ──


def test_scopes_callable_matcher_passes():
    """自定义 matcher 返回 True → 200。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["editor"])

    require = make_require(current_user)

    def admin_or_editor(req_set, user_set):
        return not req_set.isdisjoint(user_set)

    @app.get("/content")
    @require({"admin", "editor"}, match=admin_or_editor)
    async def content():
        return {"message": "content"}

    with TestClient(app) as client:
        assert client.get("/content").status_code == 200


def test_scopes_callable_matcher_fails():
    """自定义 matcher 返回 False → 403。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["viewer"])

    require = make_require(current_user)

    def admin_only(req_set, user_set):
        return "admin" in user_set

    @app.get("/content")
    @require({"admin"}, match=admin_only)
    async def content():
        return {"message": "content"}

    with TestClient(app) as client:
        assert client.get("/content").status_code == 403


def test_scopes_callable_always_called_even_without_scopes():
    """match 为 callable 时，即使 scopes 为空也总是调用。"""
    called = [False]
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["admin"])

    require = make_require(current_user)

    def my_matcher(req_set, user_set):
        called[0] = True
        return True

    @app.get("/content")
    @require(match=my_matcher)
    async def content():
        return {"message": "content"}

    with TestClient(app) as client:
        resp = client.get("/content")
    assert resp.status_code == 200
    assert called[0] is True


# ── scope_match 全局默认 ──


def test_scope_match_all_global_default():
    """make_require(scope_match='all') 全局默认 AND。"""
    app = FastAPI()

    async def current_user():
        return FakeUser(1, scopes=["admin"])  # 只有 admin，缺 super

    require = make_require(current_user, scope_match="all")

    @app.get("/multi")
    @require({"admin", "super"})
    async def multi():
        return {"message": "multi"}

    with TestClient(app) as client:
        assert client.get("/multi").status_code == 403  # AND：缺 super → 403

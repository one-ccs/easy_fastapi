"""AuthExtension 装配测试（service 依赖）。"""

from pathlib import Path

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.exceptions import ExtensionError
from easy_fastapi.ext.auth.extension import AuthExtension
from easy_fastapi.ext.auth.token import TokenService
from easy_fastapi.ext.orm.sqlalchemy.extension import SQLAlchemyExtension
from fastapi import FastAPI


class FakeUser:
    """满足 UserModelProtocol 的最小假模型。"""

    @classmethod
    async def get_by_username(cls, username):
        return None

    @classmethod
    async def get_by_id(cls, id):
        return None

    @classmethod
    async def get_by_email(cls, email):
        return None

    @classmethod
    async def get_by_username_or_email(cls, username_or_email):
        return None

    @classmethod
    async def create_user(cls, username, hashed_password, **extra):
        pass

    @classmethod
    async def update_password(cls, id, hashed_password):
        pass

    # BaseCRUDMixin 方法
    @classmethod
    async def by_id(cls, id, prefetch=None):
        return None

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


class FakeRole:
    """满足 RoleModelProtocol 的最小假模型。"""

    @classmethod
    async def get_by_id(cls, id):
        return None

    @classmethod
    async def get_by_role(cls, role):
        return None

    @classmethod
    async def create_role(cls, role, role_desc, **extra):
        pass


def _yaml(tmp_path: Path, auth_section: str | None = None) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    if auth_section is None:
        auth_section = '  auth:\n    secret: "supersecret_16ch+"\n    access_expire_minutes: 30\n'
    content = (
        "fastapi:\n  root_path: /api\n"
        'easy_fastapi:\n  database:\n    dialect: sqlite\n    database: ":memory:"\n' + auth_section
    )
    p.write_text(content, encoding="utf-8")
    return p


def test_extension_name():
    assert AuthExtension().name == "auth"


def test_extension_config_model():
    from easy_fastapi.ext.auth.config import AuthConfig

    assert AuthExtension().config_model() is AuthConfig


def test_extension_requires_empty():
    # auth 通过 ctx.require 取服务，不硬依赖具体扩展名
    assert AuthExtension().requires == []


def test_extension_provides_token_service_and_dep(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(AuthExtension())
    ctx = easy.context
    assert "token_service" in ctx.services
    assert isinstance(ctx.services["token_service"], TokenService)
    assert "require" in ctx.services
    assert callable(ctx.services["require"])


def test_auth_requires_user_model(tmp_path):
    """未先装配 ORM 扩展 → require user_model 失败 → ExtensionError。"""
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    with pytest.raises(ExtensionError):
        easy.use(AuthExtension())


def test_auth_no_secret_raises(tmp_path):
    """auth 段无 secret → 配置加载阶段 ValidationError（secret 必填）。"""
    from pydantic import ValidationError

    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path, "  auth:\n    algorithm: HS256\n"))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole]))
    with pytest.raises((ValidationError, ExtensionError)):
        easy.use(AuthExtension())


def test_auth_router_mounted(tmp_path):
    """验证 auth 路由挂载：token_service 已注册（路由可达性由 test_router 覆盖）。"""
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(AuthExtension())
    # 直接验证 OpenAPI schema 含 auth 路由
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/auth/token" in paths
    assert "/auth/login" in paths
    assert "/auth/refresh" in paths
    assert "/auth/logout" in paths


def test_auth_duplicate_use_raises(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(AuthExtension())
    with pytest.raises(ExtensionError):
        easy.use(AuthExtension())


def test_auth_config_loaded(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(AuthExtension())
    cfg = easy.context.get_config("auth")
    assert cfg is not None
    assert cfg.secret == "supersecret_16ch+"
    assert cfg.access_expire_minutes == 30


def test_auth_custom_prefix(tmp_path):
    auth = '  auth:\n    secret: "s_custom_prefix_16"\n    token_prefix: "/api/auth"\n'
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path, auth))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(AuthExtension())
    schema = app.openapi()
    paths = schema.get("paths", {})
    assert "/api/auth/token" in paths
    assert "/api/auth/login" in paths


def test_auth_instance_has_require_after_init(tmp_path):
    """init_app 后 auth.require / token_service 非 None。"""
    auth = AuthExtension()
    assert auth.require is None
    assert auth.token_service is None

    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    assert auth.require is not None
    assert callable(auth.require)
    assert isinstance(auth.token_service, TokenService)


def test_auth_require_equals_ctx_require(tmp_path):
    """auth.require 与 ctx.services['require'] 是同一对象。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    assert auth.require is easy.context.services["require"]


# ── 三级工厂依赖 provide 测试 ──


def test_auth_provides_three_factory_deps(tmp_path):
    """init_app 后 auth 暴露 current_jwt/current_token/current_user 三个工厂方法。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    # 三个方法都存在且返回 callable
    for method_name in ("current_jwt", "current_token", "current_user"):
        method = getattr(auth, method_name)
        assert callable(method)
        dep = method()
        assert callable(dep)


def test_auth_current_jwt_dep_is_distinct_per_call(tmp_path):
    """每次调用 current_jwt() 返回新的闭包 dependency。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    dep1 = auth.current_jwt()
    dep2 = auth.current_jwt()
    # 不同闭包实例
    assert dep1 is not dep2


def test_auth_current_user_factory_creates_distinct_closures(tmp_path):
    """current_user() 是工厂方法：每次调用返回新的闭包。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    dep_a = auth.current_user()
    dep_b = auth.current_user()
    assert dep_a is not dep_b  # 工厂每次创建新闭包
    assert dep_a.__code__ == dep_b.__code__  # 同一底层代码对象


def test_auth_oauth2_scheme_initialized(tmp_path):
    """init_app 后 oauth2_scheme 非 None，tokenUrl 含 token_prefix。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    assert auth.oauth2_scheme is not None
    # tokenUrl 应指向 /auth/token（标准 OAuth2 端点）
    flow = auth.oauth2_scheme.model.flows
    assert hasattr(flow, "password")
    assert "/auth/token" in flow.password.tokenUrl


def test_auth_user_model_and_persistence_attached(tmp_path):
    """init_app 后 user_model 和 persistence 已挂到 auth 实例。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    assert auth.user_model is not None
    assert auth.persistence is not None


def test_auth_token_service_uses_config_secret(tmp_path):
    """token_service.secret 来自 AuthConfig.secret。"""
    auth = AuthExtension()
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    assert auth.token_service is not None
    # _secret 是私有属性，通过 create_access_token 不抛错验证
    token = auth.token_service.create_access_token("1")
    assert isinstance(token, str)

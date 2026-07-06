"""SQLModelExtension 装配测试。"""

from pathlib import Path
from unittest.mock import patch

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.config.models import DatabaseConfig
from easy_fastapi.core.extension import ExtensionContext
from easy_fastapi.core.introspection import ModelIntrospector
from easy_fastapi.core.protocols import DbSessionFactory, UserModelProtocol
from easy_fastapi.ext.orm.sqlmodel.extension import SQLModelExtension
from fastapi import FastAPI

# ---- Fake models satisfying UserModelProtocol / RoleModelProtocol ----


class FakeUser:
    """满足 UserModelProtocol 的最小假用户模型。"""

    @classmethod
    async def get_by_username(cls, username: str | None):
        return None

    @classmethod
    async def get_by_id(cls, id: int):
        return None

    @classmethod
    async def get_by_email(cls, email: str | None):
        return None

    @classmethod
    async def get_by_username_or_email(cls, username_or_email: str | None):
        return None

    @classmethod
    async def create_user(cls, username: str | None, hashed_password: str, **extra):
        return None

    @classmethod
    async def update_password(cls, id: int, hashed_password: str) -> None:
        pass


class FakeRole:
    """满足 RoleModelProtocol 的最小假角色模型。"""

    @classmethod
    async def get_by_id(cls, id: int):
        return None

    @classmethod
    async def get_by_role(cls, role: str):
        return None

    @classmethod
    async def create_role(cls, role: str, role_desc: str, **extra):
        return None


def _yaml(tmp_path: Path, content: str | None = None) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    if content is None:
        content = (
            'fastapi:\n  root_path: /api\neasy_fastapi:\n  database:\n    dialect: sqlite\n    database: ":memory:"\n'
        )
    p.write_text(content, encoding="utf-8")
    return p


def test_extension_name():
    assert SQLModelExtension(models=[FakeUser, FakeRole]).name == "orm.sqlmodel"


def test_extension_config_model():
    assert SQLModelExtension(models=[FakeUser, FakeRole]).config_model() is None


def test_extension_provides_four_services(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
    ctx = easy.context
    assert isinstance(ctx.services["db_session_factory"], DbSessionFactory)
    assert isinstance(ctx.services["model_introspector"], ModelIntrospector)
    assert isinstance(ctx.services["user_model"], UserModelProtocol)
    assert ctx.services.get("role_model") is not None


def test_extension_lifespan_bound(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
    assert app.router.lifespan_context is not None


def test_extension_requires_empty():
    assert SQLModelExtension(models=[FakeUser, FakeRole]).requires == []


def test_extension_duplicate_use_raises(tmp_path):
    from easy_fastapi.core.exceptions import ExtensionError

    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
    with pytest.raises(ExtensionError):
        easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))


def test_extension_mysql_config(tmp_path):
    content = (
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n  database:\n    dialect: mysql\n    username: root\n    password: 123\n    database: db\n"
    )
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path, content))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))


def test_extension_db_session_factory_callable(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
    factory = easy.context.services["db_session_factory"]
    assert callable(factory)
    assert hasattr(factory, "engine")


async def test_extension_db_session_factory_produces_session(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
    factory = easy.context.services["db_session_factory"]
    cm = factory()
    assert hasattr(cm, "__aenter__")
    assert hasattr(cm, "__aexit__")


# ---- build_db_url helper 路径（Task 2） ----


def test_init_app_uses_build_db_url_when_loader_present(tmp_path):
    """loader 可用时走 build_db_url(orm, loader)，engine.url 应反映 loader 中的配置。"""
    content = (
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n  database:\n    dialect: postgres\n    username: alice\n    password: secret\n"
        "    database: mydb\n    host: db.local\n    port: 5432\n"
    )
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path, content))
    easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
    factory = easy.context.services["db_session_factory"]
    # engine.url 隐藏密码，用 render_as_string 获取完整 URL
    url = factory.engine.url.render_as_string(hide_password=False)
    # build_db_url("sqlmodel", loader) → postgresql+asyncpg://alice:secret@db.local:5432/mydb
    assert url == "postgresql+asyncpg://alice:secret@db.local:5432/mydb"


def test_init_app_falls_back_to_build_uri_when_loader_none():
    """loader 为 None 时回退到 build_uri(orm, default DatabaseConfig) — 验证 orm 参数正确。"""
    with (
        patch(
            "easy_fastapi.ext.orm.sqlmodel.extension.build_uri",
            wraps=__import__("easy_fastapi.ext.orm.base.db_config", fromlist=["build_uri"]).build_uri,
        ) as mock_build_uri,
        patch("easy_fastapi.ext.orm.sqlmodel.extension.DatabaseConfig") as MockCfg,
    ):
        MockCfg.return_value = DatabaseConfig(dialect="sqlite", database=":memory:")
        app = FastAPI()
        ctx = ExtensionContext()
        ext = SQLModelExtension(models=[FakeUser, FakeRole])
        ext.init_app(app, None, ctx)
        # build_uri 被调用且 orm 参数为 "sqlmodel"
        mock_build_uri.assert_called_once()
        args, _ = mock_build_uri.call_args
        assert args[0] == "sqlmodel"
        # 验证生成的 URL
        factory = ctx.services["db_session_factory"]
        url = factory.engine.url.render_as_string(hide_password=False)
        assert "sqlite+aiosqlite" in url


def test_init_app_calls_build_db_url_with_correct_orm_name(tmp_path):
    """验证调用 build_db_url 时传入的 orm 参数为 'sqlmodel'。"""
    with patch(
        "easy_fastapi.ext.orm.sqlmodel.extension.build_db_url",
        wraps=__import__("easy_fastapi.ext.orm.base.db_config", fromlist=["build_db_url"]).build_db_url,
    ) as mock_build_db_url:
        app = FastAPI()
        easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
        easy.use(SQLModelExtension(models=[FakeUser, FakeRole]))
        mock_build_db_url.assert_called_once()
        args, _ = mock_build_db_url.call_args
        assert args[0] == "sqlmodel"


def test_build_db_url_private_function_removed():
    """_build_db_url 私有函数应已删除。"""
    import easy_fastapi.ext.orm.sqlmodel.extension as ext_mod

    assert not hasattr(ext_mod, "_build_db_url")

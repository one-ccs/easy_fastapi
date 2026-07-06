"""TortoiseExtension 装配测试。

覆盖：name/config_model/四 service 提供/协议满足/lifespan 绑定/
models 参数注入/requires 为空/重复 use 报错。
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.config.models import DatabaseConfig
from easy_fastapi.core.extension import ExtensionContext
from easy_fastapi.core.introspection import ModelIntrospector
from easy_fastapi.core.protocols import DbSessionFactory, UserModelProtocol
from easy_fastapi.ext.orm.tortoise.extension import TortoiseExtension
from fastapi import FastAPI


class FakeUser:
    __module__ = "fake_models"

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
        return None

    @classmethod
    async def update_password(cls, id, hashed_password):
        return None


class FakeRole:
    __module__ = "fake_models"


def _yaml(tmp_path: Path, content: str | None = None) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    if content is None:
        content = (
            'fastapi:\n  root_path: /api\neasy_fastapi:\n  database:\n    dialect: sqlite\n    database: ":memory:"\n'
        )
    p.write_text(content, encoding="utf-8")
    return p


def test_tortoise_extension_name():
    assert TortoiseExtension(models=[FakeUser, FakeRole]).name == "orm.tortoise"


def test_tortoise_extension_config_model():
    ext = TortoiseExtension(models=[FakeUser, FakeRole])
    assert ext.config_model() is None


def test_tortoise_extension_provides_four_services(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))
    ctx = easy.context
    assert isinstance(ctx.services["user_model"], UserModelProtocol)
    assert isinstance(ctx.services["model_introspector"], ModelIntrospector)
    assert isinstance(ctx.services["db_session_factory"], DbSessionFactory)
    assert ctx.services.get("role_model") is not None


def test_tortoise_extension_lifespan_bound(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))
    assert app.router.lifespan_context is not None


def test_tortoise_extension_requires_empty():
    ext = TortoiseExtension(models=[FakeUser, FakeRole])
    assert ext.requires == []


def test_tortoise_extension_duplicate_use_raises(tmp_path):
    from easy_fastapi.core.exceptions import ExtensionError

    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))
    with pytest.raises(ExtensionError):
        easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))


def test_tortoise_extension_with_custom_models(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    ext = TortoiseExtension(models=[FakeUser, FakeRole])
    easy.use(ext)
    # provide 三 service 不依赖真实 init（只注册工厂）
    assert "db_session_factory" in easy.context.services


def test_tortoise_extension_mysql_config(tmp_path):
    content = (
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n  database:\n    dialect: mysql\n    username: root\n    password: 123\n    database: db\n"
    )
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path, content))
    easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))


# ---- build_db_url helper 路径（Task 2） ----


def test_init_app_uses_build_db_url_when_loader_present(tmp_path):
    """loader 可用时走 build_db_url(orm, loader) — 通过 mock make_session_factory 捕获 db_url。"""
    content = (
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n  database:\n    dialect: postgres\n    username: alice\n    password: secret\n"
        "    database: mydb\n    host: db.local\n    port: 5432\n"
    )
    with patch("easy_fastapi.ext.orm.tortoise.extension.make_session_factory") as mock_factory:
        mock_factory.return_value = lambda: None  # 不需要真实 session
        app = FastAPI()
        easy = EasyFastAPI(app, config_path=_yaml(tmp_path, content))
        easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))
        # make_session_factory 被调用，检查传入的 db_url
        mock_factory.assert_called_once()
        call_kwargs = mock_factory.call_args[1]
        db_url = call_kwargs["db_url"]
        # build_db_url("tortoise", loader) → postgres://alice:secret@db.local:5432/mydb
        assert db_url == "postgres://alice:secret@db.local:5432/mydb"


def test_init_app_falls_back_to_build_uri_when_loader_none():
    """loader 为 None 时回退到 build_uri(orm, default DatabaseConfig) — 验证 orm 参数正确。"""
    with (
        patch(
            "easy_fastapi.ext.orm.tortoise.extension.build_uri",
            wraps=__import__("easy_fastapi.ext.orm.base.db_config", fromlist=["build_uri"]).build_uri,
        ) as mock_build_uri,
        patch("easy_fastapi.ext.orm.tortoise.extension.make_session_factory") as mock_factory,
    ):
        mock_factory.return_value = lambda: None
        app = FastAPI()
        ctx = ExtensionContext()
        # loader 未注入 → get_loader() 返回 None
        ext = TortoiseExtension(models=[FakeUser, FakeRole])
        # 默认 DatabaseConfig dialect=mysql password="" 会触发 ValueError，用有效配置绕过
        with patch("easy_fastapi.ext.orm.tortoise.extension.DatabaseConfig") as MockCfg:
            MockCfg.return_value = DatabaseConfig(dialect="sqlite", database=":memory:")
            ext.init_app(app, None, ctx)
        # build_uri 被调用且 orm 参数为 "tortoise"
        mock_build_uri.assert_called_once()
        args, _ = mock_build_uri.call_args
        assert args[0] == "tortoise"
        # make_session_factory 收到 sqlite 内存 URL
        call_kwargs = mock_factory.call_args[1]
        assert call_kwargs["db_url"] == "sqlite://:memory:"


def test_init_app_calls_build_db_url_with_correct_orm_name(tmp_path):
    """验证调用 build_db_url 时传入的 orm 参数为 'tortoise'。"""
    with patch(
        "easy_fastapi.ext.orm.tortoise.extension.build_db_url",
        wraps=__import__("easy_fastapi.ext.orm.base.db_config", fromlist=["build_db_url"]).build_db_url,
    ) as mock_build_db_url:
        app = FastAPI()
        easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
        easy.use(TortoiseExtension(models=[FakeUser, FakeRole]))
        mock_build_db_url.assert_called_once()
        args, _ = mock_build_db_url.call_args
        assert args[0] == "tortoise"


def test_connection_config_import_removed():
    """ConnectionConfig 不再从 extension 模块导入。"""
    import easy_fastapi.ext.orm.tortoise.extension as ext_mod

    assert not hasattr(ext_mod, "ConnectionConfig")

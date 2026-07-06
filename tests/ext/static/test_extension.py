"""StaticExtension 测试。"""

import pytest
from easy_fastapi.ext.static.config import StaticConfig
from easy_fastapi.ext.static.extension import StaticExtension


def test_static_config_defaults():
    cfg = StaticConfig()
    assert cfg.enabled is True
    assert cfg.directory == "static"
    assert cfg.url_path == "/static"


def test_static_config_extra_forbid():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        StaticConfig(unknown_field="x")


def test_static_config_url_path_without_slash_raises():
    """url_path 不以 / 开头时 ValidationError。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="必须以 '/' 开头"):
        StaticConfig(url_path="static")


def test_static_config_url_path_with_slash_ok():
    cfg = StaticConfig(url_path="/assets")
    assert cfg.url_path == "/assets"


def test_extension_name():
    ext = StaticExtension()
    assert ext.name == "static"


def test_extension_config_model():
    ext = StaticExtension()
    assert ext.config_model() is StaticConfig


def test_init_app_mounts_static_files(tmp_path, monkeypatch):
    """enabled=True 且目录存在时 mount StaticFiles。"""
    from easy_fastapi.core.extension import ExtensionContext
    from fastapi import FastAPI

    # 创建 static 目录
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    ctx = ExtensionContext()
    ext = StaticExtension()
    ext.init_app(app, StaticConfig(enabled=True, directory="static", url_path="/static"), ctx)

    # 验证 mount：FastAPI mount 的路由是 Mount 对象，检查 app.routes
    mount_routes = [r for r in app.routes if hasattr(r, "path") and r.path.startswith("/static")]
    assert len(mount_routes) > 0
    # 验证 provide
    assert "static_mount" in ctx.services


def test_init_app_disabled_does_not_mount(tmp_path, monkeypatch):
    """enabled=False 时不 mount。"""
    from easy_fastapi.core.extension import ExtensionContext
    from fastapi import FastAPI

    static_dir = tmp_path / "static"
    static_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    ctx = ExtensionContext()
    ext = StaticExtension()
    ext.init_app(app, StaticConfig(enabled=False), ctx)

    assert "static_mount" not in ctx.services


def test_init_app_missing_dir_does_not_mount(tmp_path, monkeypatch):
    """目录不存在时不 mount（不报错）。"""
    from easy_fastapi.core.extension import ExtensionContext
    from fastapi import FastAPI

    monkeypatch.chdir(tmp_path)

    app = FastAPI()
    ctx = ExtensionContext()
    ext = StaticExtension()
    ext.init_app(app, StaticConfig(enabled=True, directory="nonexistent"), ctx)

    assert "static_mount" not in ctx.services


def test_init_app_absolute_path(tmp_path, monkeypatch):
    """绝对路径直接使用。"""
    from easy_fastapi.core.extension import ExtensionContext
    from fastapi import FastAPI

    static_dir = tmp_path / "my_static"
    static_dir.mkdir()

    app = FastAPI()
    ctx = ExtensionContext()
    ext = StaticExtension()
    ext.init_app(app, StaticConfig(enabled=True, directory=str(static_dir), url_path="/assets"), ctx)

    assert "static_mount" in ctx.services
    assert ctx.services["static_mount"]["url_path"] == "/assets"


def test_get_extension_static():
    """ext 分发表能解析 static。"""
    from easy_fastapi.ext import get_extension

    ext = get_extension("static")
    assert ext.name == "static"

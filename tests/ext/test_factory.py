"""ext.get_extension 工厂测试。"""

import pytest
from easy_fastapi.ext import get_extension


def test_get_extension_tortoise():
    assert get_extension("orm.tortoise").name == "orm.tortoise"


def test_get_extension_sqlalchemy():
    assert get_extension("orm.sqlalchemy").name == "orm.sqlalchemy"


def test_get_extension_sqlmodel():
    assert get_extension("orm.sqlmodel").name == "orm.sqlmodel"


def test_get_extension_auth():
    assert get_extension("auth").name == "auth"


def test_get_extension_redis():
    assert get_extension("redis").name == "redis"


def test_get_extension_unknown_raises():
    from easy_fastapi.core.exceptions import ExtensionError

    with pytest.raises(ExtensionError):
        get_extension("mongo")


def test_get_extension_empty_raises():
    from easy_fastapi.core.exceptions import ExtensionError

    with pytest.raises(ExtensionError):
        get_extension("")


def test_get_extension_returns_extension_protocol():
    """返回的实例满足 Extension 协议（has name/config_model/init_app）。"""
    from easy_fastapi.core.extension import Extension

    ext = get_extension("auth")
    assert isinstance(ext, Extension)


def test_get_extension_tortoise_config_model():
    ext = get_extension("orm.tortoise")
    # Tortoise 扩展消费通用 database 段，config_model() 返回 None
    assert ext.config_model() is None


def test_get_extension_returns_new_instance():
    """每次返回新实例（非单例）。"""
    a = get_extension("redis")
    b = get_extension("redis")
    assert a is not b

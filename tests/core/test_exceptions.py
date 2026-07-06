"""easy_fastapi 框架异常基类测试。

覆盖：根类继承关系、子类继承、消息携带、抛出/捕获、实例化边界、
可被框架其它层按基类统一捕获（集成意图）、与 HTTPException 体系隔离。
"""

import pytest
from easy_fastapi.core.exceptions import (
    ConfigError,
    EasyFastAPIError,
    ExtensionError,
)

# ---- 正常路径：根类与继承 ----


def test_easy_fastapi_error_is_exception():
    assert issubclass(EasyFastAPIError, Exception)


@pytest.mark.parametrize("sub", [ExtensionError, ConfigError])
def test_subclasses_inherit_root(sub):
    assert issubclass(sub, EasyFastAPIError)


# ---- 正常路径：消息携带 ----


def test_extension_error_carries_message():
    err = ExtensionError("扩展重复注册")
    assert str(err) == "扩展重复注册"


def test_config_error_carries_message():
    err = ConfigError("配置文件 'x.yaml' 不存在")
    assert str(err) == "配置文件 'x.yaml' 不存在"


# ---- 正常路径：抛出后可被基类统一捕获（集成意图） ----


def test_raise_and_catch_as_root():
    with pytest.raises(EasyFastAPIError):
        raise ExtensionError("boom")
    with pytest.raises(EasyFastAPIError):
        raise ConfigError("boom")


# ---- 边界情况 ----


def test_empty_message():
    assert str(ExtensionError("")) == ""
    assert str(ConfigError("")) == ""


def test_unicode_message():
    msg = "配置错误：无法解析 锟斤烫烫烫 🚀"
    assert str(ConfigError(msg)) == msg


def test_subclass_type_distinct():
    # 两个子类互不相交，捕获时不会误吞对方
    assert not issubclass(ExtensionError, ConfigError)
    assert not issubclass(ConfigError, ExtensionError)


# ---- 异常属性 / 错误路径 ----


def test_instance_isinstance_root():
    err = ExtensionError("x")
    assert isinstance(err, EasyFastAPIError)
    assert isinstance(err, Exception)


def test_args_attribute_preserved():
    # Exception 子类应保留 args，便于上层记录与序列化
    err = ExtensionError("msg-a")
    assert err.args == ("msg-a",)


def test_catch_specific_does_not_swallow_other_subclass():
    # 捕获 ConfigError 不应吞掉 ExtensionError（按子类型精确处理）
    with pytest.raises(ExtensionError):
        try:
            raise ExtensionError("only ext")
        except ConfigError:  # pragma: no cover - 不应进入
            pytest.fail("ConfigError 不应捕获 ExtensionError")


def test_root_is_not_http_exception():
    # 框架异常与 fastapi.HTTPException 体系独立
    try:
        from fastapi import HTTPException
    except ImportError:  # pragma: no cover - runtime extras 未装时跳过
        pytest.skip("fastapi 未安装")
    assert not issubclass(EasyFastAPIError, HTTPException)
    assert not issubclass(ExtensionError, HTTPException)
    assert not issubclass(ConfigError, HTTPException)

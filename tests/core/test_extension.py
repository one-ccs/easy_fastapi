"""Extension 协议测试（v1：config_model + init_app，无 on_post_start）。

覆盖：协议属性、config_model 返回类型、init_app 收到 config 与 ctx、
runtime_checkable、无配置扩展返回 None、扩展可携带硬依赖 requires。
"""

import pytest
from easy_fastapi.core.extension import Extension
from fastapi import FastAPI
from pydantic import BaseModel


class _FakeExt:
    name = "fake"
    requires: list[str] = []

    def config_model(self):
        class Cfg(BaseModel):
            x: int = 1

        return Cfg

    def init_app(self, app, config, ctx):
        self.called = True
        self.received_config = config
        self.received_app = app
        self.received_ctx = ctx


class _NoConfigExt:
    name = "no-config"
    requires: list[str] = []

    def config_model(self):
        return None  # 无配置段

    def init_app(self, app, config, ctx):
        self.config = config


class _DependentExt:
    name = "dependent"
    requires = ["orm"]  # 硬依赖具体扩展名

    def config_model(self):
        class Cfg(BaseModel):
            y: str = "default"

        return Cfg

    def init_app(self, app, config, ctx):
        pass


# ---- 协议属性（正常路径） ----


def test_extension_has_expected_attrs():
    ext = _FakeExt()
    assert ext.name == "fake"
    assert ext.requires == []
    assert ext.config_model() is not None


def test_extension_config_model_returns_pydantic_subclass():
    ext = _FakeExt()
    assert issubclass(ext.config_model(), BaseModel)


# ---- init_app（集成意图：收到 app/config/ctx） ----


def test_extension_init_app_called():
    ext = _FakeExt()
    app = FastAPI()
    ext.init_app(app, ext.config_model()(), ctx=None)
    assert ext.called is True
    assert ext.received_config.x == 1
    assert ext.received_app is app
    assert ext.received_ctx is None


def test_extension_init_app_receives_config_instance():
    ext = _FakeExt()
    cfg = ext.config_model()(x=42)
    ext.init_app(FastAPI(), cfg, ctx=None)
    assert ext.received_config.x == 42


def test_extension_no_config_returns_none():
    # 无配置段的扩展，config_model 返回 None
    ext = _NoConfigExt()
    assert ext.config_model() is None
    ext.init_app(FastAPI(), None, ctx=None)
    assert ext.config is None


def test_extension_requires_declaration():
    # 扩展可声明硬依赖具体扩展名（极少用）
    ext = _DependentExt()
    assert ext.requires == ["orm"]
    assert ext.name == "dependent"


# ---- runtime_checkable ----


def test_extension_protocol_runtime_checkable():
    assert isinstance(_FakeExt(), Extension)


def test_extension_protocol_accepts_multiple_impls():
    assert isinstance(_NoConfigExt(), Extension)
    assert isinstance(_DependentExt(), Extension)


def test_extension_protocol_rejects_plain_object():
    assert not isinstance(object(), Extension)


# ---- 无 on_post_start（协议不含该方法） ----


def test_extension_protocol_has_no_on_post_start():
    # on_post_start 已从协议删除；Extension 不应声明该方法
    assert not hasattr(Extension, "on_post_start")


# ---- ExtensionContext 只读查询面 has / get_config ----

from easy_fastapi.core.extension import ExtensionContext  # noqa: E402


def test_context_has_and_get_config():
    class Cfg(BaseModel):
        x: int = 5

    ctx = ExtensionContext()
    ctx.extensions["fake"] = _FakeExt()
    ctx.configs["fake"] = Cfg(x=9)

    assert ctx.has("fake") is True
    assert ctx.has("other") is False
    assert ctx.get_config("fake").x == 9
    assert ctx.get_config("absent") is None


def test_context_has_on_empty():
    ctx = ExtensionContext()
    assert ctx.has("anything") is False


def test_context_get_config_absent_returns_none():
    ctx = ExtensionContext()
    assert ctx.get_config("never_registered") is None


def test_context_has_reflects_extensions_not_configs():
    # has() 以 extensions 注册为准；即使 configs 有该键但 extensions 没注册也算未注册
    class Cfg(BaseModel):
        x: int = 1

    ctx = ExtensionContext()
    ctx.configs["ghost"] = Cfg()
    assert ctx.has("ghost") is False


def test_context_get_config_reflects_none_config():
    # 无配置段的扩展：configs[name] 显式为 None
    ctx = ExtensionContext()
    ctx.extensions["no-config"] = _NoConfigExt()
    ctx.configs["no-config"] = None
    assert ctx.has("no-config") is True
    assert ctx.get_config("no-config") is None


def test_context_has_case_sensitive():
    # 扩展名严格区分大小写
    ctx = ExtensionContext()
    ctx.extensions["Orm"] = _FakeExt()
    assert ctx.has("Orm") is True
    assert ctx.has("orm") is False


def test_context_collections_are_per_instance():
    # 两个 context 实例的注册互不影响
    a = ExtensionContext()
    b = ExtensionContext()
    a.extensions["x"] = _FakeExt()
    assert b.has("x") is False


def test_context_services_initially_empty():
    ctx = ExtensionContext()
    assert ctx.services == {}


# ---- ExtensionContext.provide（override 语义） ----

from easy_fastapi.core.exceptions import ExtensionError  # noqa: E402


def test_provide_registers_service():
    ctx = ExtensionContext()
    ctx.provide("persistence", object())
    assert "persistence" in ctx.services


def test_provide_returns_none():
    # provide 无返回值（纯副作用注册）
    ctx = ExtensionContext()
    ret = ctx.provide("k", "v")
    assert ret is None
    assert ctx.services["k"] == "v"


def test_provide_duplicate_without_override_raises():
    ctx = ExtensionContext()
    ctx.provide("k", "v1")
    with pytest.raises(ExtensionError):
        ctx.provide("k", "v2")


def test_provide_duplicate_error_message(tmp_path):
    # 错误消息应含 key 名与 override 提示
    ctx = ExtensionContext()
    ctx.provide("persistence", "mem")
    with pytest.raises(ExtensionError) as exc_info:
        ctx.provide("persistence", "other")
    msg = str(exc_info.value)
    assert "persistence" in msg
    assert "override" in msg


def test_provide_override_replaces():
    ctx = ExtensionContext()
    ctx.provide("persistence", "mem")
    ctx.provide("persistence", "redis", override=True)  # redis 覆盖 memory 是允许特例
    assert ctx.services["persistence"] == "redis"


def test_provide_override_false_default():
    # 默认 override=False：不带参数时重复 key 仍报错
    ctx = ExtensionContext()
    ctx.provide("k", 1)
    with pytest.raises(ExtensionError):
        ctx.provide("k", 2)


def test_provide_override_only_keyword():
    # override 是 keyword-only：不能用位置传第三参
    ctx = ExtensionContext()
    ctx.provide("k", 1)
    with pytest.raises(TypeError):
        ctx.provide("k", 2, True)  # type: ignore[misc]


def test_provide_distinct_keys_independent():
    ctx = ExtensionContext()
    ctx.provide("a", 1)
    ctx.provide("b", 2)
    assert ctx.services == {"a": 1, "b": 2}


def test_provide_override_on_absent_key_just_registers():
    # key 不存在时 override=True 与普通注册等价
    ctx = ExtensionContext()
    ctx.provide("k", "v", override=True)
    assert ctx.services["k"] == "v"


# ---- ExtensionContext.require（类型化校验 + requester 报错） ----

from easy_fastapi.core.protocols import Persistence, UserModelProtocol  # noqa: E402


def test_require_returns_service():
    ctx = ExtensionContext()
    ctx.provide("persistence", "mem")
    assert ctx.require("persistence", str) == "mem"


def test_require_missing_with_requester_message():
    ctx = ExtensionContext()
    with pytest.raises(ExtensionError) as exc_info:
        ctx.require("user_model", UserModelProtocol, requester="auth")
    msg = str(exc_info.value)
    assert "user_model" in msg
    assert "auth" in msg


def test_require_missing_without_requester_message():
    ctx = ExtensionContext()
    with pytest.raises(ExtensionError) as exc_info:
        ctx.require("persistence", Persistence)
    assert "persistence" in str(exc_info.value)


def test_require_missing_error_is_extension_error():
    ctx = ExtensionContext()
    with pytest.raises(ExtensionError):
        ctx.require("persistence", Persistence)


def test_require_runtime_checkable_validation_pass():
    class Mem:
        def get(self, key):
            return None

        def set(self, key, value, ex=None):
            pass

        def delete(self, key):
            pass

    ctx = ExtensionContext()
    ctx.provide("persistence", Mem())
    got = ctx.require("persistence", Persistence, requester="auth")
    assert isinstance(got, Persistence)


def test_require_type_mismatch_raises():
    # 已注册值不符合期望类型 → ExtensionError（含期望/实际类型）
    ctx = ExtensionContext()
    ctx.provide("k", "a-string")
    with pytest.raises(ExtensionError) as exc_info:
        ctx.require("k", int)
    msg = str(exc_info.value)
    assert "k" in msg
    assert "int" in msg


def test_require_type_mismatch_message_shows_actual_type():
    ctx = ExtensionContext()
    ctx.provide("k", 123)
    with pytest.raises(ExtensionError) as exc_info:
        ctx.require("k", str)
    assert "int" in str(exc_info.value)  # 实际类型 int


def test_require_requester_is_keyword_only():
    # requester 只能关键字传，不能位置传第三参
    ctx = ExtensionContext()
    ctx.provide("k", 1)
    with pytest.raises(TypeError):
        ctx.require("k", int, "auth")  # type: ignore[misc]


def test_require_returns_provided_value_on_success():
    class Mem:
        def get(self, key):
            return None

        def set(self, key, value, ex=None):
            pass

        def delete(self, key):
            pass

    ctx = ExtensionContext()
    mem = Mem()
    ctx.provide("persistence", mem)
    assert ctx.require("persistence", Persistence) is mem


def test_require_missing_includes_remedy_hint():
    ctx = ExtensionContext()
    with pytest.raises(ExtensionError) as exc_info:
        ctx.require("persistence", Persistence)
    assert "use()" in str(exc_info.value)

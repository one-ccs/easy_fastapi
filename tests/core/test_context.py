"""get_extension_context 测试。

覆盖：已挂载 app 取回 context；未挂载友好报错（EasyFastAPIError，不泄露 AttributeError）；
返回的 context 与 easy.context 是同一实例；错误消息含 EasyFastAPI 提示；传非 FastAPI
对象的边界；挂载后 state 上的属性；context 可用 require 等。
"""

from pathlib import Path

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.context import get_extension_context
from easy_fastapi.core.exceptions import EasyFastAPIError, ExtensionError
from easy_fastapi.core.extension import ExtensionContext
from fastapi import FastAPI


def _yaml(tmp_path: Path, content: str = "fastapi:\n  root_path: /api\n") -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ---- 正常路径 ----


def test_get_context_from_mounted_app(tmp_path):
    app = FastAPI()
    EasyFastAPI(app, config_path=_yaml(tmp_path))
    ctx = get_extension_context(app)
    assert isinstance(ctx, ExtensionContext)


def test_get_context_returns_same_instance_as_easy(tmp_path):
    # 取回的 context 应就是 easy.context 本身（稳定引用）
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    ctx = get_extension_context(app)
    assert ctx is easy.context


def test_get_context_after_use_has_extension(tmp_path):
    # 取回的 context 反映已 use 的扩展
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))

    class E:
        name = "demo"
        requires: list[str] = []

        def config_model(self):
            return None

        def init_app(self, app, config, ctx):  # noqa: ARG002
            pass

    easy.use(E())
    ctx = get_extension_context(app)
    assert ctx.has("demo")


# ---- 未挂载报错 ----


def test_get_context_unmounted_app_raises_friendly():
    app = FastAPI()  # 未挂载
    with pytest.raises(EasyFastAPIError):
        get_extension_context(app)


def test_get_context_unmounted_raises_subclass_extension_error():
    # 具体抛 ExtensionError（EasyFastAPIError 子类），便于精确捕获
    app = FastAPI()
    with pytest.raises(ExtensionError):
        get_extension_context(app)


def test_get_context_error_does_not_leak_attribute_error():
    # 不应把原始 AttributeError 直接抛出
    app = FastAPI()
    try:
        get_extension_context(app)
    except AttributeError:
        pytest.fail("不应抛出原始 AttributeError，应翻译为 EasyFastAPIError")
    except EasyFastAPIError:
        pass


def test_get_context_error_message_mentions_easy_fastapi():
    app = FastAPI()
    with pytest.raises(EasyFastAPIError, match="EasyFastAPI"):
        get_extension_context(app)


# ---- 边界 ----


def test_get_context_on_object_without_state():
    # 完全没有 state 属性的对象：getattr 默认 None，应友好报错而非 AttributeError

    class Bare:
        pass

    with pytest.raises(EasyFastAPIError):
        get_extension_context(Bare())  # type: ignore[arg-type]


def test_get_context_two_apps_are_isolated(tmp_path):
    # 两个不同 app 各自挂载，context 互不影响
    a = FastAPI()
    b = FastAPI()
    easy_a = EasyFastAPI(a, config_path=_yaml(tmp_path, "fastapi:\n  root_path: /a\n"))
    easy_b = EasyFastAPI(b, config_path=_yaml(tmp_path, "fastapi:\n  root_path: /b\n"))
    assert get_extension_context(a) is easy_a.context
    assert get_extension_context(b) is easy_b.context
    assert get_extension_context(a) is not get_extension_context(b)


def test_get_context_returns_usable_for_require(tmp_path):
    # 取回的 context 可直接 require 预注册的 persistence
    from easy_fastapi.core.protocols import Persistence

    app = FastAPI()
    EasyFastAPI(app, config_path=_yaml(tmp_path))
    ctx = get_extension_context(app)
    pers = ctx.require("persistence", Persistence)
    assert pers is not None


def test_get_context_fresh_unmounted_app_state_has_no_easy_fastapi():
    # 旁证：未挂载的 app.state 上确实没有 easy_fastapi 属性
    app = FastAPI()
    assert not hasattr(app.state, "easy_fastapi")

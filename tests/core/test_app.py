"""EasyFastAPI 运行时主类测试。

覆盖：挂载到 app.state.easy_fastapi、context property、预注册 MemoryPersistence、
装载 fastapi/easy_fastapi 配置段、config_loader 注入、response_code 策略。

中间件挂载已移至生成项目的 app/bootstrap/middlewares/，此处不再测试。
"""

from pathlib import Path

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.core.extension import ExtensionContext
from easy_fastapi.core.persistence.memory import MemoryPersistence
from easy_fastapi.core.protocols import Persistence
from easy_fastapi.core.response_code import set_trace_id
from fastapi import FastAPI


@pytest.fixture(autouse=True)
def _reset_trace_id():
    """每个测试前后重置 trace_id 开关。"""
    set_trace_id(False)
    yield
    set_trace_id(False)


def _yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    p.write_text(content, encoding="utf-8")
    return p


# ---- app.state 挂载 ----


def test_easy_fastapi_mounts_to_app_state(tmp_path):
    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\n")
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=cfg)
    assert app.state.easy_fastapi is easy


# ---- context property ----


def test_easy_fastapi_context_property(tmp_path):
    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\n")
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=cfg)
    assert isinstance(easy.context, ExtensionContext)


def test_easy_fastapi_context_is_stable_per_instance(tmp_path):
    # 多次访问 .context 返回同一对象
    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\n")
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    assert easy.context is easy.context


# ---- 预注册 persistence ----


def test_easy_fastapi_preregisters_memory_persistence(tmp_path):
    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\n")
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=cfg)
    pers = easy.context.services["persistence"]
    assert isinstance(pers, MemoryPersistence)
    assert isinstance(pers, Persistence)


def test_easy_fastapi_persistence_requireable(tmp_path):
    # 经 ctx.require 可类型校验取回
    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\n")
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    pers = easy.context.require("persistence", Persistence)
    assert isinstance(pers, MemoryPersistence)


# ---- 配置段装载 ----


def test_easy_fastapi_loads_fastapi_config_section(tmp_path):
    cfg = _yaml(
        tmp_path,
        "fastapi:\n  root_path: /api\n  swagger:\n    title: My API\n",
    )
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=cfg)
    assert easy.fastapi_config.root_path == "/api"
    assert easy.fastapi_config.swagger.title == "My API"


def test_easy_fastapi_loads_easy_fastapi_config_section(tmp_path):
    cfg = _yaml(tmp_path, "easy_fastapi:\n  response_code:\n    style: zero_success\n")
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    assert easy.easy_config.response_code.style == "zero_success"


def test_easy_fastapi_missing_sections_use_defaults(tmp_path):
    # 完全空配置 → fastapi/easy_fastapi 段缺失，字段全有默认值，不报错
    cfg = _yaml(tmp_path, "")
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    assert easy.fastapi_config.root_path == ""
    assert easy.easy_config.response_code.style == "http"
    assert easy.easy_config.response_code.trace_id is False


def test_easy_fastapi_trace_id_config(tmp_path):
    """trace_id 配置从 yaml 加载并设置全局开关。"""
    from easy_fastapi.core.response_code import is_trace_id_enabled

    cfg = _yaml(tmp_path, "easy_fastapi:\n  response_code:\n    trace_id: true\n")
    EasyFastAPI(FastAPI(), config_path=cfg)
    assert is_trace_id_enabled() is True


# ---- config_loader 注入 ----


def test_easy_fastapi_accepts_injected_loader(tmp_path):
    # 注入 loader 时忽略 config_path
    from easy_fastapi.core.config.loader import ConfigLoader

    p = _yaml(tmp_path, "fastapi:\n  root_path: /loaded\n")
    loader = ConfigLoader.from_yaml(p, apply_env=False)
    easy = EasyFastAPI(FastAPI(), config_loader=loader)
    assert easy.fastapi_config.root_path == "/loaded"


def test_easy_fastapi_missing_config_file_raises(tmp_path):
    from easy_fastapi.core.exceptions import ConfigError

    with pytest.raises(ConfigError):
        EasyFastAPI(FastAPI(), config_path=tmp_path / "nope.yaml")


# ---- response_code 策略 ----


def test_response_code_http_style_default(tmp_path):
    """默认 http 模式：code = HTTP status。"""
    from easy_fastapi.core.result import Result
    from starlette.testclient import TestClient

    cfg = _yaml(tmp_path, "easy_fastapi:\n  response_code:\n    style: http\n")
    app = FastAPI()

    @app.get("/ok")
    async def _ok():
        return Result("成功", data={"id": 1})

    EasyFastAPI(app, config_path=cfg)
    client = TestClient(app)
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json()["code"] == 200


def test_response_code_zero_success_mode(tmp_path):
    """zero_success 模式：成功 code=0，HTTP status 仍为 200。"""
    from easy_fastapi.core.result import Result
    from starlette.testclient import TestClient

    cfg = _yaml(tmp_path, "easy_fastapi:\n  response_code:\n    style: zero_success\n")
    app = FastAPI()

    @app.get("/ok")
    async def _ok():
        return Result("成功", data={"id": 1})

    EasyFastAPI(app, config_path=cfg)
    client = TestClient(app)
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


def test_response_code_zero_success_keeps_error_code(tmp_path):
    """zero_success 模式：错误响应的 code 仍用 HTTP status。"""
    from easy_fastapi.core.exceptions import NotFoundException
    from starlette.testclient import TestClient

    cfg = _yaml(tmp_path, "easy_fastapi:\n  response_code:\n    style: zero_success\n")
    app = FastAPI()

    @app.get("/notfound")
    async def _raise():
        raise NotFoundException("不存在")

    EasyFastAPI(app, config_path=cfg)
    client = TestClient(app)
    resp = client.get("/notfound")
    assert resp.status_code == 404
    assert resp.json()["code"] == 404


def test_response_code_http_style_keeps_status(tmp_path):
    """http 模式：4xx 响应保持原状态码。"""
    from easy_fastapi.core.exceptions import NotFoundException
    from starlette.testclient import TestClient

    cfg = _yaml(tmp_path, "easy_fastapi:\n  response_code:\n    style: http\n")
    app = FastAPI()

    @app.get("/notfound")
    async def _raise():
        raise NotFoundException("不存在")

    EasyFastAPI(app, config_path=cfg)
    client = TestClient(app)
    resp = client.get("/notfound")
    assert resp.status_code == 404


# ---- use() 装配 ----


def _yaml_basic(tmp_path):
    return _yaml(tmp_path, "fastapi:\n  root_path: /api\n")


class _NoCfgExt:
    """最小合法扩展：无配置段。"""

    name = "noconfig"
    requires: list[str] = []

    def config_model(self):
        return None

    def init_app(self, app, config, ctx):  # noqa: ARG002
        self.cfg = config


def test_use_registers_extension(tmp_path):
    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    ext = _NoCfgExt()
    easy.use(ext)
    assert easy.context.has("noconfig") is True
    assert easy.context.extensions["noconfig"] is ext


def test_use_loads_config_section_into_extension(tmp_path):
    # 扩展声明 config_model，框架从同名 yaml section 加载并传入 init_app
    from pydantic import BaseModel

    class ExtCfg(BaseModel):
        x: int = 1
        y: str = "default"

    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\neasy_fastapi:\n  myext:\n    x: 42\n    y: hi\n")

    class MyExt:
        name = "myext"
        requires: list[str] = []

        def config_model(self):
            return ExtCfg

        def init_app(self, app, config, ctx):  # noqa: ARG002
            self.cfg = config

    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    ext = MyExt()
    easy.use(ext)
    assert isinstance(ext.cfg, ExtCfg)
    assert ext.cfg.x == 42
    assert ext.cfg.y == "hi"
    # 配置同时缓存到 ctx
    assert easy.context.get_config("myext") is ext.cfg


def test_use_without_config_passes_none(tmp_path):
    # config_model() 返回 None → init_app 收到 config=None
    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)

    captured = {}

    class E:
        name = "nc"
        requires: list[str] = []

        def config_model(self):
            return None

        def init_app(self, app, config, ctx):  # noqa: ARG002
            captured["config"] = config

    easy.use(E())
    assert captured["config"] is None
    assert easy.context.get_config("nc") is None


def test_use_returns_self_for_chaining(tmp_path):
    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    assert easy.use(_NoCfgExt()) is easy


def test_use_duplicate_name_raises(tmp_path):
    from easy_fastapi.core.exceptions import ExtensionError

    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    easy.use(_NoCfgExt())
    with pytest.raises(ExtensionError):
        easy.use(_NoCfgExt())


def test_use_duplicate_message_names_extension(tmp_path):
    from easy_fastapi.core.exceptions import ExtensionError

    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    easy.use(_NoCfgExt())
    with pytest.raises(ExtensionError, match="noconfig"):
        easy.use(_NoCfgExt())


def test_use_requires_missing_extension_raises(tmp_path):
    from easy_fastapi.core.exceptions import ExtensionError

    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)

    class Dependent:
        name = "dependent"
        requires = ["not_registered"]

        def config_model(self):
            return None

        def init_app(self, app, config, ctx):  # noqa: ARG002
            pass

    with pytest.raises(ExtensionError, match="not_registered"):
        easy.use(Dependent())


def test_use_requires_satisfied_after_registering_dependency(tmp_path):
    # 先 use 提供依赖的扩展，再 use 依赖它的扩展 → 成功
    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)

    class Base:
        name = "base"
        requires: list[str] = []

        def config_model(self):
            return None

        def init_app(self, app, config, ctx):  # noqa: ARG002
            pass

    class Dependent:
        name = "dep"
        requires = ["base"]

        def config_model(self):
            return None

        def init_app(self, app, config, ctx):  # noqa: ARG002
            pass

    easy.use(Base())
    easy.use(Dependent())  # 不抛
    assert easy.context.has("dep") is True


def test_use_config_extra_forbidden_propagates(tmp_path):
    # 扩展 config_model 用 extra=forbid 的 BaseModel，yaml 含未知字段 → Validation 错误上抛
    from pydantic import BaseModel, ValidationError

    class StrictCfg(BaseModel):
        model_config = {"extra": "forbid"}
        a: int = 1

    cfg = _yaml(tmp_path, "fastapi:\n  root_path: /api\neasy_fastapi:\n  strict:\n    a: 1\n    unknown_field: x\n")

    class Strict:
        name = "strict"
        requires: list[str] = []

        def config_model(self):
            return StrictCfg

        def init_app(self, app, config, ctx):  # noqa: ARG002
            pass

    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    with pytest.raises(ValidationError):
        easy.use(Strict())


def test_use_init_app_receives_app_and_ctx(tmp_path):
    # init_app 收到的 app 即 easy.app，ctx 即 easy.context
    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    captured = {}

    class E:
        name = "probe"
        requires: list[str] = []

        def config_model(self):
            return None

        def init_app(self, app, config, ctx):
            captured["app"] = app
            captured["ctx"] = ctx

    easy.use(E())
    assert captured["app"] is easy.app
    assert captured["ctx"] is easy.context


def test_use_missing_config_uses_defaults(tmp_path):
    # 扩展声明 config_model 但 yaml 无该 section → 用字段默认值，不报错
    from pydantic import BaseModel

    class ExtCfg(BaseModel):
        timeout: int = 30

    cfg = _yaml_basic(tmp_path)

    class E:
        name = "timed"
        requires: list[str] = []

        def config_model(self):
            return ExtCfg

        def init_app(self, app, config, ctx):  # noqa: ARG002
            self.cfg = config

    easy = EasyFastAPI(FastAPI(), config_path=cfg)
    ext = E()
    easy.use(ext)
    assert ext.cfg.timeout == 30


def test_use_chains_multiple_extensions(tmp_path):
    cfg = _yaml_basic(tmp_path)
    easy = EasyFastAPI(FastAPI(), config_path=cfg)

    class A(_NoCfgExt):
        name = "a"

    class B(_NoCfgExt):
        name = "b"

    easy.use(A()).use(B())
    assert easy.context.has("a") and easy.context.has("b")

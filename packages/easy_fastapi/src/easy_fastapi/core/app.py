"""EasyFastAPI 运行时主类。

职责：① 装载核心配置段；② 创建 ExtensionContext 并预注册 persistence=MemoryPersistence；
③ _init_app 绑定 root_path、异常 handler；④ 挂载到 app.state.easy_fastapi。

中间件挂载已移至生成项目的 app/bootstrap/middlewares/，此处不再自动添加。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI

from .config.loader import ConfigLoader
from .config.models import EasyFastAPIConfig, FastAPIConfig
from .exceptions import ExtensionError
from .extension import Extension, ExtensionContext
from .handlers import binding_exception_handler
from .persistence.memory import MemoryPersistence
from .response_code import set_strategy, set_trace_id

if TYPE_CHECKING:
    pass


class EasyFastAPI:
    def __init__(
        self,
        app: FastAPI,
        *,
        config_path: Path | None = None,
        config_loader: ConfigLoader | None = None,
    ) -> None:
        self.app = app
        if config_loader is not None:
            self._loader = config_loader
        elif config_path is not None:
            self._loader = ConfigLoader.from_yaml(config_path)
        else:
            # 自动定位：通过 .easy-fastapi.json 找项目根 → 推导 yaml 路径
            from ..project import resolve_config_path

            self._loader = ConfigLoader.from_yaml(resolve_config_path())
        self._ctx = ExtensionContext()
        self._ctx.set_loader(self._loader)

        # 预注册默认服务
        self._ctx.services["persistence"] = MemoryPersistence()

        # 装载核心固定配置段
        self.fastapi_config: FastAPIConfig = self._loader.section("fastapi", FastAPIConfig)
        self.easy_config: EasyFastAPIConfig = self._loader.section("easy_fastapi", EasyFastAPIConfig)

        self._init_app(app)
        app.state.easy_fastapi = self

    @property
    def context(self) -> ExtensionContext:
        return self._ctx

    def use(self, ext: Extension) -> EasyFastAPI:
        """装配扩展。

        流程：① 重复注册校验；② requires 硬依赖校验（依赖的扩展必须已先 use）；
        ③ 统一加载 config（config_model() → loader.section()），无 config_model 返回 None；
        ④ init_app(app, config, ctx)；⑤ 注册到 ctx.extensions/configs。
        返回 self 以支持链式 use。
        """
        name = ext.name
        if name in self._ctx.extensions:
            raise ExtensionError(f"扩展 '{name}' 已注册，请勿重复 use()")
        missing = [r for r in getattr(ext, "requires", []) if r not in self._ctx.extensions]
        if missing:
            raise ExtensionError(f"扩展 '{name}' 依赖 {missing}，请先 use() 它们")
        model = ext.config_model()
        section = getattr(ext, "config_section", ext.name)
        config = self._loader.section(f"easy_fastapi.{section}", model) if model is not None else None
        self._ctx.extensions[name] = ext
        self._ctx.configs[name] = config
        ext.init_app(self.app, config, self._ctx)
        return self

    def _init_app(self, app: FastAPI) -> None:
        app.root_path = self.fastapi_config.root_path

        # 绑定全局异常 handler
        binding_exception_handler(app)

        # 设置响应码策略（从配置段读取 style）
        set_strategy(self.easy_config.response_code.style)
        set_trace_id(self.easy_config.response_code.trace_id)

        # 应用 Swagger 配置到 FastAPI 应用
        swagger = self.fastapi_config.swagger
        app.title = swagger.title
        app.description = swagger.description
        app.version = swagger.version

        # 启动时打印文档地址（如有）
        async def _log_docs_url() -> None:
            import logging
            import os

            host = os.environ.get("EFA_SERVER_HOST", "localhost")
            port = os.environ.get("EFA_SERVER_PORT", "8000")
            # 0.0.0.0 / :: 绑定全部网卡，文档地址用 localhost 更实用
            if host in ("0.0.0.0", "::"):
                host = "localhost"
            root = app.root_path or ""
            parts: list[str] = []
            if swagger.docs_url:
                parts.append(f"Docs: http://{host}:{port}{root}{swagger.docs_url}")
            if swagger.redoc_url:
                parts.append(f"ReDoc: http://{host}:{port}{root}{swagger.redoc_url}")
            if parts:
                logging.getLogger("uvicorn.error").info(" | ".join(parts))

        app.router.add_event_handler("startup", _log_docs_url)

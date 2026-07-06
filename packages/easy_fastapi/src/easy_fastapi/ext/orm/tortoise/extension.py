"""Tortoise 运行时扩展（provide db_session_factory/model_introspector/user_model/role_model）。

从通用 database 段读取连接配置（ORM 无关），自行转换为 Tortoise 连接 URL。
项目通过 models=[User, Role, ...] 传入实体类，扩展内部转模块路径字符串给 init_tortoise，
并 provide user_model/role_model 供 auth 消费。
init_app 绑定 lifespan（启动 init_tortoise，关闭 close_connections）并 provide 四 service。
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, ClassVar

from easy_fastapi.core.config.models import DatabaseConfig

from ..base.db_config import build_db_url, build_uri
from .introspector import TortoiseModelIntrospector
from .session import generate_schemas, init_tortoise, make_session_factory

if TYPE_CHECKING:
    from fastapi import FastAPI

    from easy_fastapi.core.extension import ExtensionContext

from easy_fastapi.core.extras import require

tortoise = require("tortoise-orm", "tortoise")


class TortoiseExtension:
    name = "orm.tortoise"
    config_section = "database"
    requires: ClassVar[list[str]] = []

    def __init__(self, *, models: list[type] | list[str] | None = None) -> None:
        """models: 项目传入的实体类列表，约定 [User, Role, ...]。

        Tortoise 需要模块路径字符串，内部由类 __module__ 转换。
        若传入 list[str]（模块路径），直接使用（兼容旧用法）。
        若未传入，走自动发现：优先 app.models.user + app.models.role，
        回退到框架内置模型。
        """
        self._models = models

    def config_model(self):
        # 不再有独立配置段，消费通用 database 段
        return None

    def _resolve_model_modules(self) -> tuple[list[str], list[type]]:
        """将 models 参数统一转为 (模块路径字符串列表, 模型类列表)。"""
        if self._models is None:
            return self._auto_discover_models()
        # list[str]：import 每个模块，提取其中定义的 Tortoise Model 类
        if self._models and isinstance(self._models[0], str):
            modules = list(self._models)  # type: ignore[arg-type]
            types = self._extract_model_types_from_modules(modules)
            return modules, types
        # list[type] → 提取 __module__ 去重
        modules = list({m.__module__ for m in self._models})  # type: ignore[union-attr]
        return modules, list(self._models)  # type: ignore[arg-type]

    @staticmethod
    def _extract_model_types_from_modules(modules: list[str]) -> list[type]:
        """从模块路径列表 import 并提取每个模块中定义的 Tortoise Model 类。"""
        import importlib

        types: list[type] = []
        for mod_path in modules:
            try:
                mod = importlib.import_module(mod_path)
            except (ImportError, ModuleNotFoundError):
                continue
            for attr in vars(mod).values():
                try:
                    if isinstance(attr, type) and attr.__module__ == mod_path and hasattr(attr, "_meta"):
                        types.append(attr)
                except TypeError:
                    continue
        return types

    @staticmethod
    def _auto_discover_models() -> tuple[list[str], list[type]]:
        """无显式 models 时，尝试发现项目 app.models.user + app.models.role。

        框架不再持有内置模型，发现失败则报错提示传入 models。
        返回 (模块路径列表, 模型类列表)——模型类供 provide user_model/role_model。
        """
        import importlib

        try:
            user_mod = importlib.import_module("app.models.user")
            role_mod = importlib.import_module("app.models.role")
        except (ImportError, ModuleNotFoundError) as e:
            raise ValueError(
                "TortoiseExtension 未传入 models 且无法自动发现 app.models.user/role，"
                "请显式传入 models=[User, Role, ...]"
            ) from e
        modules = ["app.models.user", "app.models.role"]
        types: list[type] = []
        for mod in (user_mod, role_mod):
            for attr in vars(mod).values():
                try:
                    if isinstance(attr, type) and attr.__module__ == mod.__name__ and hasattr(attr, "_meta"):
                        types.append(attr)
                except TypeError:
                    continue
        return modules, types

    def init_app(self, app: FastAPI, config, ctx: ExtensionContext) -> None:
        # 从 ctx 取回 loader（由 EasyFastAPI 装配时注入），读 database 段
        loader = ctx.get_loader()
        db_cfg = loader.section("easy_fastapi.database", DatabaseConfig) if loader else DatabaseConfig()
        db_url = build_db_url("tortoise", loader) if loader else build_uri("tortoise", db_cfg)

        # Tortoise 需要模块路径字符串
        model_modules, model_types = self._resolve_model_modules()

        # 组合已有 lifespan（如 _DefaultLifespan 的 on_startup 处理器），
        # 不能直接赋值 app.router.lifespan_context，否则会覆盖框架注册的启动回调。
        prev_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(prev_lifespan(_app))
                await init_tortoise(
                    db_url=db_url,
                    models=model_modules,
                    timezone=db_cfg.timezone,
                    echo=db_cfg.echo,
                )
                await generate_schemas()
                try:
                    yield
                finally:
                    await tortoise.Tortoise.close_connections()

        app.router.lifespan_context = lifespan

        ctx.provide("db_session_factory", make_session_factory(db_url=db_url, models=model_modules))
        ctx.provide("model_introspector", TortoiseModelIntrospector())
        if len(model_types) >= 1:
            ctx.provide("user_model", model_types[0])
        if len(model_types) >= 2:
            ctx.provide("role_model", model_types[1])

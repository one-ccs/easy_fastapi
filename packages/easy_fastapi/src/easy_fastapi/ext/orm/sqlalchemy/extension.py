"""SQLAlchemy 运行时扩展（provide db_session_factory/model_introspector/user_model/role_model）。

从通用 database 段读取连接配置（ORM 无关），自行转换为 SQLAlchemy 连接 URL。
项目通过 models=[User, Role, ...] 传入实体类，扩展 provide user_model/role_model 供 auth 消费。
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, ClassVar

from easy_fastapi.core.config.models import DatabaseConfig

from ..base.db_config import build_db_url, build_uri
from .introspector import SQLAlchemyModelIntrospector
from .session import make_db_session_factory

if TYPE_CHECKING:
    from fastapi import FastAPI

    from easy_fastapi.core.extension import ExtensionContext


class SQLAlchemyExtension:
    name = "orm.sqlalchemy"
    config_section = "database"
    requires: ClassVar[list[str]] = []

    def __init__(self, *, models: list[type] | None = None) -> None:
        """models: 项目传入的实体类列表，约定 [User, Role, ...]。

        models[0] 作为 user_model、models[1] 作为 role_model provide 给 auth。
        若未传入，init_app 时会报错提示（必须传入项目实体类）。
        """
        self._models = models

    def config_model(self):
        return None

    def init_app(self, app: FastAPI, config, ctx: ExtensionContext) -> None:
        if not self._models:
            raise ValueError("SQLAlchemyExtension 需要传入 models=[User, Role, ...]（项目实体类）")
        loader = ctx.get_loader()
        if loader:
            db_url = build_db_url("sqlalchemy", loader)
        else:
            db_url = build_uri("sqlalchemy", DatabaseConfig())

        db_session_factory = make_db_session_factory(db_url=db_url)
        engine = db_session_factory.engine

        # 注入 session_factory 到每个模型类（CRUDMixin 的 _session() 依赖）
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        _factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        for model in self._models:
            if hasattr(model, "_sa_session_factory"):
                model._sa_session_factory = _factory

        # 组合已有 lifespan（如 _DefaultLifespan 的 on_startup 处理器），
        # 不能直接赋值 app.router.lifespan_context，否则会覆盖框架注册的启动回调。
        prev_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(prev_lifespan(_app))
                # 从项目模型提取 metadata（模型继承各自 Base，metadata 在类上）
                _metadata = self._models[0].metadata if self._models else None
                async with engine.begin() as conn:
                    if _metadata is not None:
                        await conn.run_sync(_metadata.create_all)
                try:
                    yield
                finally:
                    await engine.dispose()

        app.router.lifespan_context = lifespan

        ctx.provide("db_session_factory", db_session_factory)
        ctx.provide("model_introspector", SQLAlchemyModelIntrospector())
        # 约定：models[0]=User, models[1]=Role，provide 类本身供 auth require
        if len(self._models) >= 1:
            ctx.provide("user_model", self._models[0])
        if len(self._models) >= 2:
            ctx.provide("role_model", self._models[1])

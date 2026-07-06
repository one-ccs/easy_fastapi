"""SQLAlchemy 风格 async session 工厂（SQLAlchemy / SQLModel 共用）。

参数化 async_session_class：SQLAlchemy 传入 SA AsyncSession，SQLModel 传入
sqlmodel.ext.asyncio.session.AsyncSession（支持 exec() 方法）。
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from easy_fastapi.core.extras import require

create_async_engine = require("sqlalchemy", "sqlalchemy.ext.asyncio").create_async_engine
sessionmaker = require("sqlalchemy", "sqlalchemy.orm").sessionmaker

# 默认使用 SQLAlchemy AsyncSession
_DefaultAsyncSession = require("sqlalchemy", "sqlalchemy.ext.asyncio").AsyncSession


def make_session_factory(
    *,
    db_url: str,
    async_session_class: type | None = None,
    **engine_kwargs: Any,
):
    """创建 async engine + sessionmaker，返回 (factory, engine)。

    async_session_class 默认使用 SQLAlchemy AsyncSession；
    SQLModel 传入 sqlmodel.ext.asyncio.session.AsyncSession。
    """
    session_class = async_session_class or _DefaultAsyncSession
    engine = create_async_engine(db_url, **engine_kwargs)
    factory = sessionmaker(engine, class_=session_class, expire_on_commit=False)
    return factory, engine


@asynccontextmanager
async def _session_cm(factory):
    session = factory()
    try:
        yield session
    finally:
        await session.close()


def make_db_session_factory(
    *,
    db_url: str,
    async_session_class: type | None = None,
    **engine_kwargs: Any,
):
    """返回 DbSessionFactory（__call__ → AsyncContextManager[DbSession]）。"""
    factory, _engine = make_session_factory(db_url=db_url, async_session_class=async_session_class, **engine_kwargs)

    def db_session_factory() -> AbstractAsyncContextManager:
        return _session_cm(factory)

    # 挂 engine 供 extension lifespan 用
    db_session_factory.engine = _engine  # type: ignore[attr-defined]
    return db_session_factory

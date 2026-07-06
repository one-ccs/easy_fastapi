"""SQLModel session 管理 — 复用共享 base.session 工厂，传入 SQLModel AsyncSession。"""

from __future__ import annotations

from easy_fastapi.core.extras import require

# SQLModel AsyncSession 提供 exec() 方法（SA AsyncSession 不具备）
_SQLModelAsyncSession = require("sqlmodel", "sqlmodel.ext.asyncio.session").AsyncSession


def make_session_factory(*, db_url, **engine_kwargs):
    """创建 async engine + sessionmaker（使用 SQLModel AsyncSession）。"""
    from easy_fastapi.ext.orm.base.session import make_session_factory as _make

    return _make(db_url=db_url, async_session_class=_SQLModelAsyncSession, **engine_kwargs)


def make_db_session_factory(*, db_url, **engine_kwargs):
    """返回 DbSessionFactory（使用 SQLModel AsyncSession）。"""
    from easy_fastapi.ext.orm.base.session import make_db_session_factory as _make

    return _make(db_url=db_url, async_session_class=_SQLModelAsyncSession, **engine_kwargs)


__all__ = ["make_db_session_factory", "make_session_factory"]

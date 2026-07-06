"""SQLAlchemy async 声明基类（暴露 Base/metadata 供 db sync）。"""

from __future__ import annotations

from easy_fastapi.core.extras import require

sa_orm = require("sqlalchemy", "sqlalchemy.orm")
DeclarativeBase = sa_orm.DeclarativeBase


class Base(DeclarativeBase):
    pass


metadata = Base.metadata

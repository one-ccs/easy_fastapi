"""SQLModel 模型内省 — 复用共享 SQLAlchemyStyleIntrospector。"""

from __future__ import annotations

from easy_fastapi.ext.orm.base.introspector import SQLAlchemyStyleIntrospector

# SQLAlchemy 与 SQLModel 均暴露 __table__.columns，内省逻辑一致，共用 base 实现。
SQLModelModelIntrospector = SQLAlchemyStyleIntrospector

__all__ = ["SQLModelModelIntrospector"]

"""SQLAlchemy 风格模型 introspector（SQLAlchemy / SQLModel 共用）。

读 model.__table__.columns → FieldMeta/ModelMeta。SQLAlchemy 与 SQLModel
均暴露 __table__.columns，故内省逻辑完全一致，抽取到 base 共享。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from easy_fastapi.core.introspection import FieldMeta, ModelMeta


def _col_type_name(col: Any) -> str:
    return type(col.type).__name__


class SQLAlchemyStyleIntrospector:
    """SQLAlchemy 风格模型内省器（SQLAlchemy / SQLModel 通用）。"""

    def __init__(self, models: list[type] | None = None) -> None:
        self._models = models or []

    def extract_models(
        self,
        models: list[type] | None = None,
        models_path: Path | None = None,
        *,
        ignore: set[str] | None = None,
    ) -> list[ModelMeta]:
        """对给定模型类列表内省，返回 ModelMeta 列表。

        models_path 为协议占位（v1 不需要扫描文件系统），实际模型由 models 参数传入。
        """
        ignore = ignore or set()
        metas: list[ModelMeta] = []
        for model in models or self._models:
            if model.__name__ in ignore:
                continue
            fms = [
                FieldMeta(
                    name=col.key,
                    type_name=_col_type_name(col),
                    primary_key=bool(col.primary_key),
                    nullable=bool(col.nullable),
                    relation=None,
                )
                for col in model.__table__.columns
            ]
            metas.append(ModelMeta(name=model.__name__, fields=fms))
        return metas

"""Tortoise 模型内省（读 fields_map → FieldMeta/ModelMeta）。

真实模型发现以 Tortoise 已加载的 ORM 注册表（tortoise.Tortoise.apps）为准，
不靠文件系统扫描。models_path 仅作协议占位（v1 不需要扫描文件）。
"""

from __future__ import annotations

from pathlib import Path

from easy_fastapi.core.extras import require
from easy_fastapi.core.introspection import FieldMeta, ModelMeta

tortoise = require("tortoise-orm", "tortoise")


def _field_type_name(field) -> str:
    ft = getattr(field, "field_type", None)
    return getattr(ft, "__name__", str(ft)) if ft is not None else "Any"


def _relation(field) -> str | None:
    """判断关系类型：m2m / fk / o2o，普通字段返回 None。"""
    cls_name = type(field).__name__
    if "ManyToMany" in cls_name:
        return "m2m"
    if "ForeignKey" in cls_name:
        return "fk"
    if "OneToOne" in cls_name:
        return "o2o"
    return None


def _is_pk(field) -> bool:
    # 兼容不同 tortoise 版本字段名：pk / is_pk
    return bool(getattr(field, "pk", False) or getattr(field, "is_pk", False))


class TortoiseModelIntrospector:
    def extract_models(self, models_path: Path | None = None, *, ignore: set[str] | None = None) -> list[ModelMeta]:
        ignore = ignore or set()
        metas: list[ModelMeta] = []
        for _app_name, app in tortoise.Tortoise.apps.items():
            for model_name, model in app.items():
                if model_name in ignore:
                    continue
                fields_map = model._meta.fields_map
                fms = [
                    FieldMeta(
                        name=name,
                        type_name=_field_type_name(f),
                        primary_key=_is_pk(f),
                        nullable=bool(getattr(f, "null", False)),
                        relation=_relation(f),
                    )
                    for name, f in fields_map.items()
                ]
                metas.append(ModelMeta(name=model.__name__, fields=fms))
        return metas

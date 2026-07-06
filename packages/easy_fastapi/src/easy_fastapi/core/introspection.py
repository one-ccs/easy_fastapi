"""模型发现 + 字段元数据协议（efa gen 用）。

各 ORM 实现自己的 ModelIntrospector（Tortoise 读 fields_map；
SQLAlchemy/SQLModel 读 __table__.columns）并 provide('model_introspector')。
字段元数据增强：预留 primary_key/nullable/relation，避免 v1 协议不够用。
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class FieldMeta(BaseModel):
    name: str
    type_name: str
    primary_key: bool = False
    nullable: bool = False
    relation: str | None = None  # fk / m2m / o2m 等，无关系则 None


class ModelMeta(BaseModel):
    name: str
    fields: list[FieldMeta]


@runtime_checkable
class ModelIntrospector(Protocol):
    """两职责：1) 返回当前项目已加载模型列表；2) 返回每个模型的字段元数据。"""

    def extract_models(self, models_path: Path | None = None) -> list[ModelMeta]: ...

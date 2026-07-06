"""codegen 字段类型映射测试。

覆盖 _TYPE_MAP 所有条目、未知类型默认 str、datetime 导入、关系字段跳过、nullable 注解。
"""

import pytest
from easy_fastapi.commands.gen import generate_for_model
from easy_fastapi.core.introspection import FieldMeta, ModelMeta


@pytest.mark.parametrize(
    "type_name,expected",
    [
        ("IntField", "int"),
        ("int", "int"),
        ("CharField", "str"),
        ("varchar", "str"),
        ("str", "str"),
        ("BooleanField", "bool"),
        ("bool", "bool"),
        ("TextField", "str"),
        ("text", "str"),
        ("FloatField", "float"),
        ("float", "float"),
        ("JSONField", "dict"),
        ("json", "dict"),
    ],
)
def test_type_mapping(type_name, expected, tmp_path):
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="col", type_name=type_name, primary_key=False, nullable=False, relation=None),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "item.py").read_text(encoding="utf-8")
    assert f"col: {expected}" in schema


def test_datetime_field_imports_datetime(tmp_path):
    meta = ModelMeta(
        name="Event",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="ts", type_name="DatetimeField", primary_key=False, nullable=True, relation=None),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "event.py").read_text(encoding="utf-8")
    assert "from datetime import datetime" in schema
    assert "ts: datetime | None = None" in schema


def test_unknown_type_raises_error(tmp_path):
    """未知字段类型应报错而非静默降级为 str。"""
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="col", type_name="CustomUnknownField", primary_key=False, nullable=False, relation=None),
        ],
    )
    with pytest.raises(ValueError, match="不支持的字段类型"):
        generate_for_model(meta, project_dir=tmp_path, force=False)


def test_relation_fields_skipped(tmp_path):
    """关系字段（fk/m2m）不出现在 Base schema 中。"""
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="owner_id", type_name="IntField", primary_key=False, nullable=False, relation="fk"),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "item.py").read_text(encoding="utf-8")
    # owner_id 是关系字段，不应出现在 Base 中
    base_section = schema.split("class ItemCreate")[0]
    assert "owner_id" not in base_section


def test_nullable_field_has_optional_annotation(tmp_path):
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="note", type_name="CharField", primary_key=False, nullable=True, relation=None),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "item.py").read_text(encoding="utf-8")
    assert "note: str | None = None" in schema


def test_no_datetime_field_no_datetime_import(tmp_path):
    """不含 DatetimeField 时不导入 datetime。"""
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="IntField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="name", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "item.py").read_text(encoding="utf-8")
    assert "from datetime import datetime" not in schema


def test_pk_type_from_type_map(tmp_path):
    """主键类型应从 type_map 取（如 CharField PK → str）。"""
    meta = ModelMeta(
        name="Item",
        fields=[
            FieldMeta(name="id", type_name="CharField", primary_key=True, nullable=False, relation=None),
            FieldMeta(name="name", type_name="CharField", primary_key=False, nullable=False, relation=None),
        ],
    )
    generate_for_model(meta, project_dir=tmp_path, force=False)
    schema = (tmp_path / "app" / "schemas" / "item.py").read_text(encoding="utf-8")
    assert "id: str" in schema

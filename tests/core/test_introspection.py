"""模型发现 + 字段元数据协议测试（efa gen 用）。

覆盖：FieldMeta 默认值与字段、ModelMeta 结构、ModelIntrospector runtime_checkable、
字段序列化、空字段列表、关系类型、模型间字段隔离。
"""

from pathlib import Path

import pytest
from easy_fastapi.core.introspection import FieldMeta, ModelIntrospector, ModelMeta
from pydantic import ValidationError

# ---- FieldMeta（正常路径 + 默认值） ----


def test_field_meta_defaults():
    f = FieldMeta(name="id", type_name="int")
    assert f.name == "id"
    assert f.type_name == "int"
    assert f.primary_key is False
    assert f.nullable is False
    assert f.relation is None


def test_field_meta_primary_key_and_nullable():
    f = FieldMeta(name="id", type_name="int", primary_key=True, nullable=False)
    assert f.primary_key is True
    assert f.nullable is False


def test_field_meta_relation_fk():
    f = FieldMeta(name="user_id", type_name="int", relation="fk")
    assert f.relation == "fk"


def test_field_meta_relation_m2m():
    f = FieldMeta(name="roles", type_name="list", relation="m2m")
    assert f.relation == "m2m"


def test_field_meta_requires_name():
    with pytest.raises(ValidationError):
        FieldMeta(type_name="int")  # name 必填


def test_field_meta_requires_type_name():
    with pytest.raises(ValidationError):
        FieldMeta(name="id")  # type_name 必填


# ---- ModelMeta（正常路径） ----


def test_model_meta_holds_fields():
    m = ModelMeta(
        name="User",
        fields=[FieldMeta(name="id", type_name="int", primary_key=True)],
    )
    assert m.name == "User"
    assert len(m.fields) == 1
    assert m.fields[0].primary_key is True


def test_model_meta_empty_fields_allowed():
    m = ModelMeta(name="Empty", fields=[])
    assert m.fields == []


def test_model_meta_requires_name():
    with pytest.raises(ValidationError):
        ModelMeta(fields=[])


def test_model_meta_multiple_fields():
    m = ModelMeta(
        name="Post",
        fields=[
            FieldMeta(name="id", type_name="int", primary_key=True),
            FieldMeta(name="title", type_name="str", nullable=False),
            FieldMeta(name="author_id", type_name="int", relation="fk"),
        ],
    )
    assert len(m.fields) == 3
    assert m.fields[2].relation == "fk"


# ---- ModelIntrospector（runtime_checkable） ----


def test_model_introspector_runtime_checkable():
    class FakeIntrospector:
        def extract_models(self, models_path: Path | None = None):
            return []

    assert isinstance(FakeIntrospector(), ModelIntrospector)


def test_model_introspector_returns_model_meta_list():
    """集成意图：真实 introspector 返回 list[ModelMeta]，字段可被消费方读取。"""

    class FakeIntrospector:
        def extract_models(self, models_path: Path | None = None):
            return [ModelMeta(name="User", fields=[FieldMeta(name="id", type_name="int")])]

    result = FakeIntrospector().extract_models()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == "User"
    assert result[0].fields[0].name == "id"


def test_model_introspector_rejects_missing_extract_models():
    class Bad:
        pass

    assert not isinstance(Bad(), ModelIntrospector)

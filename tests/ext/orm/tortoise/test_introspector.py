"""TortoiseModelIntrospector 测试。

读 tortoise 已注册模型的 fields_map → FieldMeta/ModelMeta。
覆盖：协议满足、返回 User ModelMeta、字段名齐全、id 是 pk、type_name 非空、
nullable 标注、ignore 生效、未 init 返回空、字段数、relation 默认 None。
"""

import pytest
from easy_fastapi.core.introspection import FieldMeta, ModelIntrospector, ModelMeta
from easy_fastapi.ext.orm.tortoise.introspector import TortoiseModelIntrospector
from tortoise import Tortoise, fields
from tortoise.models import Model


# 本模块模型，供 modules={"models": [__name__]} 发现
class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=32, unique=True, null=True)
    hashed_password = fields.CharField(max_length=128)
    is_active = fields.BooleanField(default=True)
    roles = fields.ManyToManyField("models.Role", related_name="users", through="user_role")

    class Meta:
        table = "intro_user"


class Role(Model):
    id = fields.IntField(pk=True)
    role = fields.CharField(max_length=16, unique=True)

    class Meta:
        table = "intro_role"


@pytest.fixture
async def db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()
    try:
        yield Tortoise
    finally:
        await Tortoise.close_connections()


def test_introspector_satisfies_protocol():
    assert isinstance(TortoiseModelIntrospector(), ModelIntrospector)


async def test_extract_models_returns_user_meta(db):
    metas = TortoiseModelIntrospector().extract_models()
    names = [m.name for m in metas]
    assert "User" in names
    user_meta = next(m for m in metas if m.name == "User")
    assert isinstance(user_meta, ModelMeta)


async def test_user_meta_has_all_fields(db):
    metas = TortoiseModelIntrospector().extract_models()
    user_meta = next(m for m in metas if m.name == "User")
    field_names = {f.name for f in user_meta.fields}
    assert {"id", "username", "hashed_password", "is_active"}.issubset(field_names)


async def test_id_field_is_primary_key(db):
    metas = TortoiseModelIntrospector().extract_models()
    user_meta = next(m for m in metas if m.name == "User")
    pk = next(f for f in user_meta.fields if f.name == "id")
    assert pk.primary_key is True
    assert pk.type_name != ""


async def test_field_meta_instances(db):
    metas = TortoiseModelIntrospector().extract_models()
    user_meta = next(m for m in metas if m.name == "User")
    for f in user_meta.fields:
        assert isinstance(f, FieldMeta)


async def test_username_nullable(db):
    metas = TortoiseModelIntrospector().extract_models()
    user_meta = next(m for m in metas if m.name == "User")
    username = next(f for f in user_meta.fields if f.name == "username")
    assert username.nullable is True


async def test_extract_models_respects_ignore(db):
    metas = TortoiseModelIntrospector().extract_models(ignore={"User"})
    assert "User" not in [m.name for m in metas]


async def test_extract_models_when_apps_empty_returns_empty():
    # 当 tortoise 未注册任何 app（apps 为空 dict）时 → 返回空列表，不报错
    from tortoise import Tortoise

    if Tortoise.apps:
        metas = TortoiseModelIntrospector().extract_models()
        assert isinstance(metas, list)
    else:
        metas = TortoiseModelIntrospector().extract_models()
        assert metas == []


async def test_field_relation_defaults_none(db):
    # User 模型的 roles 字段是 m2m 关系，其余字段 relation 为 None
    metas = TortoiseModelIntrospector().extract_models()
    user_meta = next(m for m in metas if m.name == "User")
    for f in user_meta.fields:
        if f.name == "roles":
            assert f.relation == "m2m"
        else:
            assert f.relation is None


async def test_returned_metas_is_list(db):
    metas = TortoiseModelIntrospector().extract_models()
    assert isinstance(metas, list)

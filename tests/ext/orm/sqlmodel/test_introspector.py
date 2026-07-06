"""SQLModelModelIntrospector 测试。"""

from easy_fastapi.core.introspection import FieldMeta, ModelIntrospector, ModelMeta
from easy_fastapi.ext.orm.sqlmodel.introspector import SQLModelModelIntrospector
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "intro_sm_user"
    __table_args__ = {"extend_existing": True}
    id: int | None = Field(default=None, primary_key=True)
    username: str | None = Field(default=None, index=True)
    hashed_password: str
    is_active: bool = True


def test_introspector_satisfies_protocol():
    assert isinstance(SQLModelModelIntrospector(), ModelIntrospector)


def test_introspect_user_model():
    metas = SQLModelModelIntrospector().extract_models([User])
    names = [m.name for m in metas]
    assert "User" in names


def test_introspect_returns_list_of_modelmeta():
    metas = SQLModelModelIntrospector().extract_models([User])
    assert isinstance(metas, list)
    assert isinstance(metas[0], ModelMeta)


def test_introspect_fields_are_fieldmeta():
    metas = SQLModelModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    for f in um.fields:
        assert isinstance(f, FieldMeta)


def test_introspect_user_has_username_field():
    metas = SQLModelModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    fns = [f.name for f in um.fields]
    assert "username" in fns
    assert "hashed_password" in fns
    assert "is_active" in fns


def test_introspect_id_is_primary_key():
    metas = SQLModelModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    pk = next(f for f in um.fields if f.name == "id")
    assert pk.primary_key is True


def test_introspect_username_nullable():
    metas = SQLModelModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    username = next(f for f in um.fields if f.name == "username")
    assert username.nullable is True


def test_introspect_hashed_password_not_nullable():
    metas = SQLModelModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    hp = next(f for f in um.fields if f.name == "hashed_password")
    assert hp.nullable is False


def test_introspect_empty_models_returns_empty():
    metas = SQLModelModelIntrospector().extract_models([])
    assert metas == []


def test_introspect_ignore_skips_model():
    metas = SQLModelModelIntrospector().extract_models([User], ignore={"User"})
    assert "User" not in [m.name for m in metas]

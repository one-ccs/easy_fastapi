"""SQLAlchemyModelIntrospector 测试。"""

from easy_fastapi.core.introspection import FieldMeta, ModelIntrospector, ModelMeta
from easy_fastapi.ext.orm.sqlalchemy.introspector import SQLAlchemyModelIntrospector
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class _Base(DeclarativeBase):
    pass


class User(_Base):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=True)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)


def test_introspector_satisfies_protocol():
    assert isinstance(SQLAlchemyModelIntrospector(), ModelIntrospector)


def test_introspect_user_model():
    metas = SQLAlchemyModelIntrospector().extract_models([User])
    names = [m.name for m in metas]
    assert "User" in names
    um = next(m for m in metas if m.name == "User")
    fns = [f.name for f in um.fields]
    assert "username" in fns
    assert "id" in fns
    pk = next(f for f in um.fields if f.name == "id")
    assert pk.primary_key is True


def test_introspect_fields_are_fieldmeta():
    metas = SQLAlchemyModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    for f in um.fields:
        assert isinstance(f, FieldMeta)


def test_introspect_username_nullable():
    metas = SQLAlchemyModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    username = next(f for f in um.fields if f.name == "username")
    assert username.nullable is True


def test_introspect_hashed_password_not_nullable():
    metas = SQLAlchemyModelIntrospector().extract_models([User])
    um = next(m for m in metas if m.name == "User")
    hp = next(f for f in um.fields if f.name == "hashed_password")
    assert hp.nullable is False


def test_introspect_empty_models_returns_empty():
    metas = SQLAlchemyModelIntrospector().extract_models([])
    assert metas == []


def test_introspect_ignore_skips_model():
    metas = SQLAlchemyModelIntrospector().extract_models([User], ignore={"User"})
    assert "User" not in [m.name for m in metas]


def test_introspect_returns_list():
    metas = SQLAlchemyModelIntrospector().extract_models([User])
    assert isinstance(metas, list)
    assert isinstance(metas[0], ModelMeta)

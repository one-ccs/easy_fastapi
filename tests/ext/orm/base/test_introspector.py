"""共享 SQLAlchemy 风格 introspector 测试。"""

from easy_fastapi.ext.orm.base.introspector import SQLAlchemyStyleIntrospector
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class _Base(DeclarativeBase):
    pass


class User(_Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=True)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)


class Role(_Base):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True)
    role = Column(String(16), unique=True)


def test_introspector_extract_models_returns_list():
    """extract_models 返回 ModelMeta 列表。"""
    introspector = SQLAlchemyStyleIntrospector(models=[])
    result = introspector.extract_models()
    assert isinstance(result, list)


def test_introspector_accepts_models_param():
    import inspect

    sig = inspect.signature(SQLAlchemyStyleIntrospector.__init__)
    assert "models" in sig.parameters


def test_introspector_produces_model_meta():
    """给定 SQLAlchemy/SQLModel 风格的模型类，产出正确的 ModelMeta。"""
    from easy_fastapi.core.introspection import ModelMeta

    introspector = SQLAlchemyStyleIntrospector(models=[User])
    result = introspector.extract_models()
    assert len(result) == 1
    assert isinstance(result[0], ModelMeta)
    assert result[0].name == "User"
    # User 至少有 id 和 username 字段
    field_names = [f.name for f in result[0].fields]
    assert "id" in field_names
    assert "username" in field_names


def test_introspector_ignores_models():
    """ignore 参数排除指定模型。"""
    introspector = SQLAlchemyStyleIntrospector(models=[User, Role])
    result = introspector.extract_models(ignore={"Role"})
    assert len(result) == 1
    assert result[0].name == "User"

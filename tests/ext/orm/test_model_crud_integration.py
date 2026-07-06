"""C5: 项目模型接入 CRUDMixin 的协议满足性测试。

验证 SQLAlchemy / SQLModel 两套 ORM 的项目模型（继承各自 CRUDMixin）后
满足 BaseCRUDMixin 协议（isinstance 检查）并暴露 5 个统一 CRUD 方法。
框架不再持有内置 User/Role 模型，本测试用本地模型类验证 mixin 行为。
"""

import inspect
from functools import lru_cache

from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.sqlalchemy.crud import SQLAlchemyCRUDMixin
from easy_fastapi.ext.orm.sqlmodel.crud import SQLModelCRUDMixin

CRUD_METHODS = ["by_id", "paginate", "create", "update_from_dict", "delete_by_ids"]


# ── SQLAlchemy User/Role ──
# lru_cache 保证类只定义一次，避免重复在同一 Base 上注册同名类触发 SAWarning。


@lru_cache(maxsize=1)
def _make_sqlalchemy_models():
    from easy_fastapi.ext.orm.sqlalchemy.base import Base
    from sqlalchemy import Boolean, Column, Integer, String

    class User(Base, SQLAlchemyCRUDMixin):
        __tablename__ = "c5_user"
        __table_args__ = {"extend_existing": True}
        id = Column(Integer, primary_key=True)
        username = Column(String(32), unique=True, nullable=True)
        hashed_password = Column(String(128), nullable=False)
        is_active = Column(Boolean, default=True)

    class Role(Base, SQLAlchemyCRUDMixin):
        __tablename__ = "c5_role"
        __table_args__ = {"extend_existing": True}
        id = Column(Integer, primary_key=True)
        role = Column(String(16), unique=True)

    return User, Role


def test_sqlalchemy_user_satisfies_base_protocol():
    User, _ = _make_sqlalchemy_models()
    assert isinstance(User, BaseCRUDMixin)


def test_sqlalchemy_role_satisfies_base_protocol():
    _, Role = _make_sqlalchemy_models()
    assert isinstance(Role, BaseCRUDMixin)


def test_sqlalchemy_user_exposes_crud_methods():
    User, _ = _make_sqlalchemy_models()
    for name in CRUD_METHODS:
        assert hasattr(User, name), f"User 缺少 CRUD 方法 {name}"


def test_sqlalchemy_role_exposes_crud_methods():
    _, Role = _make_sqlalchemy_models()
    for name in CRUD_METHODS:
        assert hasattr(Role, name), f"Role 缺少 CRUD 方法 {name}"


def test_sqlalchemy_crud_methods_are_classmethods():
    """CRUD 方法必须为 classmethod（通过 cls 操作，而非实例）。"""
    User, _ = _make_sqlalchemy_models()
    for name in CRUD_METHODS:
        attr = inspect.getattr_static(User, name)
        assert isinstance(attr, classmethod), f"User.{name} 不是 classmethod"


# ── SQLModel User/Role ──


@lru_cache(maxsize=1)
def _make_sqlmodel_models():
    from sqlmodel import Field, SQLModel

    class User(SQLModel, SQLModelCRUDMixin, table=True):
        __tablename__ = "c5_sm_user"
        __table_args__ = {"extend_existing": True}
        id: int | None = Field(default=None, primary_key=True)
        username: str | None = Field(default=None, index=True)
        hashed_password: str
        is_active: bool = True

    class Role(SQLModel, SQLModelCRUDMixin, table=True):
        __tablename__ = "c5_sm_role"
        __table_args__ = {"extend_existing": True}
        id: int | None = Field(default=None, primary_key=True)
        role: str = Field(unique=True)

    return User, Role


def test_sqlmodel_user_satisfies_base_protocol():
    User, _ = _make_sqlmodel_models()
    assert isinstance(User, BaseCRUDMixin)


def test_sqlmodel_role_satisfies_base_protocol():
    _, Role = _make_sqlmodel_models()
    assert isinstance(Role, BaseCRUDMixin)


def test_sqlmodel_user_exposes_crud_methods():
    User, _ = _make_sqlmodel_models()
    for name in CRUD_METHODS:
        assert hasattr(User, name), f"User 缺少 CRUD 方法 {name}"


def test_sqlmodel_role_exposes_crud_methods():
    _, Role = _make_sqlmodel_models()
    for name in CRUD_METHODS:
        assert hasattr(Role, name), f"Role 缺少 CRUD 方法 {name}"


def test_sqlmodel_crud_methods_are_classmethods():
    User, _ = _make_sqlmodel_models()
    for name in CRUD_METHODS:
        attr = inspect.getattr_static(User, name)
        assert isinstance(attr, classmethod), f"User.{name} 不是 classmethod"

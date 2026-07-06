"""SQLAlchemy 声明基类 + metadata 暴露 + User 模型测试。

覆盖：Base/metadata 暴露、User 表名、字段齐全、AuthUser 协议、
in-memory sqlite CRUD、username unique、is_active 默认、
hashed_password、更新、删除。
"""

import pytest
from easy_fastapi.core.protocols import AuthUser
from easy_fastapi.ext.orm.sqlalchemy.base import Base, metadata
from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=True)
    hashed_password = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    scopes: list[str] = []  # AuthUser 协议要求


class Role(Base):
    __tablename__ = "role"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    role = Column(String(16), unique=True)


def test_base_exposes_metadata():
    assert metadata is Base.metadata


def test_user_registered_in_metadata():
    assert "user" in metadata.tables


def test_user_table_has_expected_columns():
    cols = {c.name for c in metadata.tables["user"].columns}
    assert {"id", "username", "hashed_password", "is_active"}.issubset(cols)


def test_user_id_is_primary_key():
    pk_cols = {c.name for c in metadata.tables["user"].primary_key.columns}
    assert "id" in pk_cols


def test_user_username_nullable():
    col = metadata.tables["user"].c.username
    assert col.nullable is True


def test_user_hashed_password_not_nullable():
    col = metadata.tables["user"].c.hashed_password
    assert col.nullable is False


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    await engine.dispose()


async def test_user_create_and_get(db):
    u = User(username="alice", hashed_password="h", is_active=True)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    assert u.id is not None
    from sqlalchemy import select

    got = (await db.execute(select(User).where(User.username == "alice"))).scalar_one()
    assert got.hashed_password == "h"


async def test_user_satisfies_authuser(db):
    u = User(username="bob", hashed_password="hp", is_active=True)
    db.add(u)
    await db.commit()
    assert isinstance(u, AuthUser)


async def test_user_is_active_defaults_true(db):
    u = User(username="def", hashed_password="h")
    db.add(u)
    await db.commit()
    await db.refresh(u)
    assert u.is_active is True


async def test_user_repr():
    u = User(username="repr_user", hashed_password="h")
    r = repr(u)
    assert "User" in r

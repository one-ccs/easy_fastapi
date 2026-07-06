"""SQLModel CRUDMixin 业务 classmethod 测试。"""

import pytest


@pytest.fixture
async def sqlmodel_user_setup():
    """初始化 SQLModel 内存数据库 + User 表。"""
    from easy_fastapi.ext.orm.sqlmodel.crud import SQLModelCRUDMixin
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlmodel import Field, SQLModel
    from sqlmodel.ext.asyncio.session import AsyncSession

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    class User(SQLModel, SQLModelCRUDMixin, table=True):
        __tablename__ = "bm_user"
        __table_args__ = {"extend_existing": True}
        id: int | None = Field(default=None, primary_key=True)
        username: str | None = Field(default=None, unique=True, max_length=32)
        email: str | None = Field(default=None, unique=True, max_length=64)
        hashed_password: str = Field(max_length=128)
        is_active: bool = Field(default=True)

        @property
        def identity(self):
            return self.username or self.email

        @property
        def h_pwd(self):
            return self.hashed_password

        @property
        def scopes(self):
            return []

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    User._sa_session_factory = factory

    async with factory() as s:
        s.add(User(username="u0", hashed_password="h0", is_active=True))
        s.add(User(username="u1", email="u1@test.com", hashed_password="h1", is_active=True))
        await s.commit()

    try:
        yield User, factory
    finally:
        await engine.dispose()


async def test_get_by_username_found(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    result = await User.get_by_username("u0")
    assert result is not None
    assert result.username == "u0"


async def test_get_by_username_not_found(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    result = await User.get_by_username("ghost")
    assert result is None


async def test_get_by_email_found(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    result = await User.get_by_email("u1@test.com")
    assert result is not None


async def test_get_by_id_found(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    result = await User.get_by_id(1)
    assert result is not None


async def test_get_by_username_or_email(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    result = await User.get_by_username_or_email("u0")
    assert result is not None
    result2 = await User.get_by_username_or_email("u1@test.com")
    assert result2 is not None


async def test_create_user(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    result = await User.create_user(username="new", hashed_password="hp")
    assert result.username == "new"
    assert result.id is not None


async def test_update_password(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    await User.update_password(1, "new_hash")
    result = await User.get_by_id(1)
    assert result.hashed_password == "new_hash"


async def test_session_auto_commit(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    async with User._session() as s:
        u = User(username="auto_commit", hashed_password="h")
        s.add(u)
        await s.flush()
    found = await User.get_by_username("auto_commit")
    assert found is not None


async def test_session_auto_rollback(sqlmodel_user_setup):
    User, _ = sqlmodel_user_setup
    with pytest.raises(ValueError):
        async with User._session() as s:
            u = User(username="rollback_user", hashed_password="h")
            s.add(u)
            await s.flush()
            raise ValueError("boom")
    found = await User.get_by_username("rollback_user")
    assert found is None


def test_user_satisfies_user_model_protocol(sqlmodel_user_setup):
    from easy_fastapi.core.protocols import UserModelProtocol

    User, _ = sqlmodel_user_setup
    assert isinstance(User, UserModelProtocol)

"""SQLAlchemy CRUDMixin 业务 classmethod 测试（get_by_username/create_user/update_password）。"""

import pytest


@pytest.fixture
async def sa_user_setup():
    """初始化 SQLAlchemy 内存数据库 + User 表，yield (User, session_factory)。"""
    from easy_fastapi.ext.orm.sqlalchemy.crud import SQLAlchemyCRUDMixin
    from sqlalchemy import Boolean, Column, Integer, String
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    class Base(DeclarativeBase):
        pass

    class User(Base, SQLAlchemyCRUDMixin):
        __tablename__ = "user"
        id = Column(Integer, primary_key=True, autoincrement=True)
        username = Column(String(32), unique=True, nullable=True)
        email = Column(String(64), unique=True, nullable=True)
        hashed_password = Column(String(128), nullable=False)
        is_active = Column(Boolean, default=True)

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
        await conn.run_sync(Base.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    User._sa_session_factory = factory

    # 种子数据
    async with factory() as s:
        s.add(User(username="u0", hashed_password="h0", is_active=True))
        s.add(User(username="u1", email="u1@test.com", hashed_password="h1", is_active=True))
        await s.commit()

    try:
        yield User, factory
    finally:
        await engine.dispose()


# ---- get_by_username ----


async def test_get_by_username_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_username("u0")
    assert result is not None
    assert result.username == "u0"


async def test_get_by_username_not_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_username("ghost")
    assert result is None


# ---- get_by_email ----


async def test_get_by_email_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_email("u1@test.com")
    assert result is not None
    assert result.email == "u1@test.com"


async def test_get_by_email_not_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_email("no@such.com")
    assert result is None


# ---- get_by_id ----


async def test_get_by_id_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_id(1)
    assert result is not None
    assert result.id == 1


async def test_get_by_id_not_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_id(99999)
    assert result is None


# ---- get_by_username_or_email ----


async def test_get_by_username_or_email_by_username(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_username_or_email("u0")
    assert result is not None
    assert result.username == "u0"


async def test_get_by_username_or_email_by_email(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_username_or_email("u1@test.com")
    assert result is not None
    assert result.email == "u1@test.com"


async def test_get_by_username_or_email_not_found(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.get_by_username_or_email("nobody")
    assert result is None


# ---- create_user ----


async def test_create_user_creates_and_returns(sa_user_setup):
    User, _ = sa_user_setup
    result = await User.create_user(username="new", hashed_password="hp")
    assert result is not None
    assert result.username == "new"
    assert result.id is not None


async def test_create_user_persists(sa_user_setup):
    User, _ = sa_user_setup
    created = await User.create_user(username="persist", hashed_password="hp")
    found = await User.get_by_username("persist")
    assert found is not None
    assert found.id == created.id


# ---- update_password ----


async def test_update_password_changes_hash(sa_user_setup):
    User, _ = sa_user_setup
    await User.update_password(1, "new_hash")
    result = await User.get_by_id(1)
    assert result.hashed_password == "new_hash"


async def test_update_password_nonexistent_no_error(sa_user_setup):
    User, _ = sa_user_setup
    # 不存在也不报错（与原 repository 行为一致）
    await User.update_password(99999, "x")


# ---- _session 自动 commit ----


async def test_session_auto_commits_on_success(sa_user_setup):
    User, _ = sa_user_setup
    async with User._session() as s:
        u = User(username="auto_commit", hashed_password="h")
        s.add(u)
        await s.flush()
    # session 退出后已 commit，新 session 可查到
    found = await User.get_by_username("auto_commit")
    assert found is not None


async def test_session_auto_rollback_on_error(sa_user_setup):
    User, _ = sa_user_setup
    with pytest.raises(ValueError):
        async with User._session() as s:
            u = User(username="rollback_user", hashed_password="h")
            s.add(u)
            await s.flush()
            raise ValueError("boom")
    # rollback 后不应存在
    found = await User.get_by_username("rollback_user")
    assert found is None


# ---- UserModelProtocol 满足性 ----


def test_user_satisfies_user_model_protocol(sa_user_setup):
    from easy_fastapi.core.protocols import UserModelProtocol

    User, _ = sa_user_setup
    assert isinstance(User, UserModelProtocol)


def test_role_satisfies_role_model_protocol():
    """SQLAlchemy Role 模型满足 RoleModelProtocol（含 get_by_role/create_role）。"""
    from easy_fastapi.core.protocols import RoleModelProtocol
    from easy_fastapi.ext.orm.sqlalchemy.crud import SQLAlchemyCRUDMixin
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    class Base(DeclarativeBase):
        pass

    class Role(Base, SQLAlchemyCRUDMixin):
        __tablename__ = "role"
        id = Column(Integer, primary_key=True, autoincrement=True)
        role = Column(String(16), unique=True, nullable=False)
        role_desc = Column(String(32), nullable=False)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    Role._sa_session_factory = factory

    assert isinstance(Role, RoleModelProtocol)
    assert hasattr(Role, "get_by_role")
    assert hasattr(Role, "create_role")

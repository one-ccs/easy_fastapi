"""SQLAlchemy CRUDMixin 测试。

使用真实 SQLite 内存数据库验证 CRUD 操作，与 Tortoise test_crud.py 约定一致。
覆盖：正常路径（by_id/paginate/create/update_from_dict/delete_by_ids）、
边界（空列表/空数据/不存在）、异常（id 不存在）。
"""

import pytest
from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.base.pagination import Pagination


@pytest.fixture
async def sa_setup():
    """初始化 SQLAlchemy 内存数据库 + 创建 User/Role 表，yield (User, Role, session_factory)。"""
    from easy_fastapi.ext.orm.sqlalchemy.crud import SQLAlchemyCRUDMixin
    from sqlalchemy import Boolean, Column, Integer, String
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    class Base(DeclarativeBase):
        pass

    class User(Base, SQLAlchemyCRUDMixin):
        __tablename__ = "user"
        id = Column(Integer, primary_key=True)
        username = Column(String(32), nullable=True)
        email = Column(String(64), nullable=True)
        hashed_password = Column(String(128), nullable=False)
        is_active = Column(Boolean, default=True)

    class Role(Base, SQLAlchemyCRUDMixin):
        __tablename__ = "role"
        id = Column(Integer, primary_key=True)
        role = Column(String(16), unique=True)
        role_desc = Column(String(32))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 注入 session factory 到 mixin
    User._sa_session_factory = factory
    Role._sa_session_factory = factory

    # 造 3 个 User + 2 个 Role
    async with factory() as s:
        for i in range(3):
            s.add(User(username=f"u{i}", hashed_password="h"))
        s.add(Role(role="admin", role_desc="管理员"))
        s.add(Role(role="user", role_desc="用户"))
        await s.commit()

    try:
        yield User, Role, factory
    finally:
        await engine.dispose()


# ── by_id ──


async def test_by_id_hits(sa_setup):
    User, Role, _ = sa_setup
    result = await User.by_id(1)
    assert result is not None
    assert result.username == "u0"


async def test_by_id_miss_returns_none(sa_setup):
    User, Role, _ = sa_setup
    result = await User.by_id(99999)
    assert result is None


# ── paginate ──


async def test_paginate_returns_pagination(sa_setup):
    User, Role, _ = sa_setup
    page = await User.paginate(page_index=1, page_size=2)
    assert isinstance(page, Pagination)
    assert page.total == 3
    assert len(page.items) == 2


async def test_paginate_finished_flag(sa_setup):
    User, Role, _ = sa_setup
    p1 = await User.paginate(page_index=1, page_size=2)
    assert p1.finished is False
    p2 = await User.paginate(page_index=2, page_size=2)
    assert p2.finished is True


async def test_paginate_empty_table(sa_setup):
    User, Role, _ = sa_setup
    # 删掉所有 User
    await User.delete_by_ids([1, 2, 3])
    page = await User.paginate(page_index=1, page_size=10)
    assert page.total == 0
    assert page.items == []
    assert page.finished is True


# ── create ──


async def test_create_returns_instance(sa_setup):
    User, Role, _ = sa_setup
    result = await User.create(username="new", hashed_password="h")
    assert result is not None
    assert result.username == "new"
    assert result.id is not None


async def test_create_persists_to_db(sa_setup):
    User, Role, _ = sa_setup
    await User.create(username="persist", hashed_password="h")
    found = await User.by_id(4)  # id 4 = 3 initial + 1 new
    assert found is not None
    assert found.username == "persist"


async def test_create_role(sa_setup):
    User, Role, _ = sa_setup
    result = await Role.create(role="editor", role_desc="编辑")
    assert result.role == "editor"


# ── update_from_dict ──


async def test_update_from_dict_updates_fields(sa_setup):
    User, Role, _ = sa_setup
    user = await User.by_id(1)
    result = await User.update_from_dict(user, {"username": "updated"})
    assert result.username == "updated"


async def test_update_from_dict_persists_to_db(sa_setup):
    User, Role, _ = sa_setup
    user = await User.by_id(1)
    await User.update_from_dict(user, {"username": "persisted"})
    refetched = await User.by_id(1)
    assert refetched.username == "persisted"


async def test_update_from_dict_empty_data_no_change(sa_setup):
    User, Role, _ = sa_setup
    user = await User.by_id(1)
    original_name = user.username
    result = await User.update_from_dict(user, {})
    assert result.username == original_name


async def test_update_from_dict_returns_same_instance(sa_setup):
    User, Role, _ = sa_setup
    user = await User.by_id(1)
    result = await User.update_from_dict(user, {"username": "x"})
    assert result.id == user.id


# ── delete_by_ids ──


async def test_delete_by_ids_removes_records(sa_setup):
    User, Role, _ = sa_setup
    count = await User.delete_by_ids([1, 2])
    assert count == 2
    assert await User.by_id(1) is None
    assert await User.by_id(2) is None


async def test_delete_by_ids_returns_count(sa_setup):
    User, Role, _ = sa_setup
    count = await User.delete_by_ids([1])
    assert count == 1


async def test_delete_by_ids_empty_list_returns_zero(sa_setup):
    User, Role, _ = sa_setup
    count = await User.delete_by_ids([])
    assert count == 0


async def test_delete_by_ids_nonexistent_id_returns_zero(sa_setup):
    User, Role, _ = sa_setup
    count = await User.delete_by_ids([99999])
    assert count == 0


async def test_delete_by_ids_partial_existing(sa_setup):
    User, Role, _ = sa_setup
    count = await User.delete_by_ids([1, 99999])
    assert count == 1


# ── 协议满足性 ──


def test_sqlalchemy_crud_mixin_satisfies_base_protocol():
    from easy_fastapi.ext.orm.sqlalchemy.crud import SQLAlchemyCRUDMixin

    assert isinstance(SQLAlchemyCRUDMixin, BaseCRUDMixin)


async def test_user_model_satisfies_base_protocol(sa_setup):
    User, Role, _ = sa_setup
    assert isinstance(User, BaseCRUDMixin)


async def test_role_model_satisfies_base_protocol(sa_setup):
    User, Role, _ = sa_setup
    assert isinstance(Role, BaseCRUDMixin)


# ── exists / exists_by_email / get_or_create ──


async def test_exists_returns_true_for_existing_username(sa_setup):
    User, Role, _ = sa_setup
    result = await User.exists(username="u0")
    assert result is True


async def test_exists_returns_false_for_missing_username(sa_setup):
    User, Role, _ = sa_setup
    result = await User.exists(username="nonexistent")
    assert result is False


async def test_exists_by_email_returns_true(sa_setup):
    User, Role, _ = sa_setup
    await User.create(username="email_user", email="test@test.com", hashed_password="h")
    result = await User.exists_by_email("test@test.com")
    assert result is True


async def test_exists_by_email_returns_false(sa_setup):
    User, Role, _ = sa_setup
    result = await User.exists_by_email("no@such.com")
    assert result is False


async def test_exists_with_multiple_filters(sa_setup):
    User, Role, _ = sa_setup
    result = await User.exists(username="u0", is_active=True)
    assert result is True


async def test_role_exists_returns_true(sa_setup):
    User, Role, _ = sa_setup
    result = await Role.exists(role="admin")
    assert result is True


async def test_role_exists_returns_false(sa_setup):
    User, Role, _ = sa_setup
    result = await Role.exists(role="nonexistent")
    assert result is False


async def test_get_or_create_returns_existing(sa_setup):
    User, Role, _ = sa_setup
    result, created = await Role.get_or_create(role="admin", role_desc="管理员")
    assert result.role == "admin"
    assert created is False


async def test_get_or_create_creates_new(sa_setup):
    User, Role, _ = sa_setup
    result, created = await Role.get_or_create(role="editor", role_desc="编辑")
    assert result.role == "editor"
    assert result.id is not None
    assert created is True

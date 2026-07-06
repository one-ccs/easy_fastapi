"""SQLModel CRUDMixin 测试。

使用真实 SQLite 内存数据库验证 CRUD 操作，与 Tortoise/SQLAlchemy test_crud 约定一致。
覆盖：正常路径、边界（空列表/空数据/不存在）、异常。

注：SQLModel 使用全局共享 metadata，table=True 模型必须在模块作用域定义一次，
否则跨 fixture 调用会触发 "Table already defined"。测试模型使用独立表名
（crud_user / crud_role）避免与包内真实 user/role 表冲突。
"""

import pytest
from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.base.pagination import Pagination
from easy_fastapi.ext.orm.sqlmodel.crud import SQLModelCRUDMixin
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


class User(SQLModel, SQLModelCRUDMixin, table=True):
    __tablename__ = "crud_user"
    id: int | None = Field(default=None, primary_key=True)
    username: str | None = Field(default=None, max_length=32)
    hashed_password: str = Field(max_length=128)
    is_active: bool = Field(default=True)


class Role(SQLModel, SQLModelCRUDMixin, table=True):
    __tablename__ = "crud_role"
    id: int | None = Field(default=None, primary_key=True)
    role: str = Field(max_length=16, unique=True)
    role_desc: str = Field(max_length=32)


@pytest.fixture
async def sm_setup():
    """初始化 SQLModel 内存数据库 + 建表 + 造数据，yield (User, Role, factory)。"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    User._sa_session_factory = factory
    Role._sa_session_factory = factory

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


async def test_by_id_hits(sm_setup):
    User, Role, _ = sm_setup
    result = await User.by_id(1)
    assert result is not None
    assert result.username == "u0"


async def test_by_id_miss_returns_none(sm_setup):
    User, Role, _ = sm_setup
    result = await User.by_id(99999)
    assert result is None


# ── paginate ──


async def test_paginate_returns_pagination(sm_setup):
    User, Role, _ = sm_setup
    page = await User.paginate(page_index=1, page_size=2)
    assert isinstance(page, Pagination)
    assert page.total == 3
    assert len(page.items) == 2


async def test_paginate_finished_flag(sm_setup):
    User, Role, _ = sm_setup
    p1 = await User.paginate(page_index=1, page_size=2)
    assert p1.finished is False
    p2 = await User.paginate(page_index=2, page_size=2)
    assert p2.finished is True


async def test_paginate_empty_table(sm_setup):
    User, Role, _ = sm_setup
    await User.delete_by_ids([1, 2, 3])
    page = await User.paginate(page_index=1, page_size=10)
    assert page.total == 0
    assert page.items == []
    assert page.finished is True


# ── create ──


async def test_create_returns_instance(sm_setup):
    User, Role, _ = sm_setup
    result = await User.create(username="new", hashed_password="h")
    assert result is not None
    assert result.username == "new"
    assert result.id is not None


async def test_create_persists_to_db(sm_setup):
    User, Role, _ = sm_setup
    await User.create(username="persist", hashed_password="h")
    found = await User.by_id(4)
    assert found is not None
    assert found.username == "persist"


async def test_create_role(sm_setup):
    User, Role, _ = sm_setup
    result = await Role.create(role="editor", role_desc="编辑")
    assert result.role == "editor"


# ── update_from_dict ──


async def test_update_from_dict_updates_fields(sm_setup):
    User, Role, _ = sm_setup
    user = await User.by_id(1)
    result = await User.update_from_dict(user, {"username": "updated"})
    assert result.username == "updated"


async def test_update_from_dict_persists_to_db(sm_setup):
    User, Role, _ = sm_setup
    user = await User.by_id(1)
    await User.update_from_dict(user, {"username": "persisted"})
    refetched = await User.by_id(1)
    assert refetched.username == "persisted"


async def test_update_from_dict_empty_data_no_change(sm_setup):
    User, Role, _ = sm_setup
    user = await User.by_id(1)
    original_name = user.username
    result = await User.update_from_dict(user, {})
    assert result.username == original_name


async def test_update_from_dict_returns_same_instance(sm_setup):
    User, Role, _ = sm_setup
    user = await User.by_id(1)
    result = await User.update_from_dict(user, {"username": "x"})
    assert result.id == user.id


# ── delete_by_ids ──


async def test_delete_by_ids_removes_records(sm_setup):
    User, Role, _ = sm_setup
    count = await User.delete_by_ids([1, 2])
    assert count == 2
    assert await User.by_id(1) is None


async def test_delete_by_ids_returns_count(sm_setup):
    User, Role, _ = sm_setup
    count = await User.delete_by_ids([1])
    assert count == 1


async def test_delete_by_ids_empty_list_returns_zero(sm_setup):
    User, Role, _ = sm_setup
    count = await User.delete_by_ids([])
    assert count == 0


async def test_delete_by_ids_nonexistent_id_returns_zero(sm_setup):
    User, Role, _ = sm_setup
    count = await User.delete_by_ids([99999])
    assert count == 0


async def test_delete_by_ids_partial_existing(sm_setup):
    User, Role, _ = sm_setup
    count = await User.delete_by_ids([1, 99999])
    assert count == 1


# ── 协议满足性 ──


def test_sqlmodel_crud_mixin_satisfies_base_protocol():
    assert isinstance(SQLModelCRUDMixin, BaseCRUDMixin)


async def test_user_model_satisfies_base_protocol(sm_setup):
    User, Role, _ = sm_setup
    assert isinstance(User, BaseCRUDMixin)


async def test_role_model_satisfies_base_protocol(sm_setup):
    User, Role, _ = sm_setup
    assert isinstance(Role, BaseCRUDMixin)


# ── exists / exists_by_email / get_or_create ──


async def test_exists_returns_true_for_existing_username(sm_setup):
    User, Role, _ = sm_setup
    result = await User.exists(username="u0")
    assert result is True


async def test_exists_returns_false_for_missing_username(sm_setup):
    User, Role, _ = sm_setup
    result = await User.exists(username="nonexistent")
    assert result is False


async def test_exists_with_multiple_filters(sm_setup):
    User, Role, _ = sm_setup
    result = await User.exists(username="u0", is_active=True)
    assert result is True


async def test_role_exists_returns_true(sm_setup):
    User, Role, _ = sm_setup
    result = await Role.exists(role="admin")
    assert result is True


async def test_role_exists_returns_false(sm_setup):
    User, Role, _ = sm_setup
    result = await Role.exists(role="nonexistent")
    assert result is False


async def test_get_or_create_returns_existing(sm_setup):
    User, Role, _ = sm_setup
    result, created = await Role.get_or_create(role="admin", role_desc="管理员")
    assert result.role == "admin"
    assert created is False


async def test_get_or_create_creates_new(sm_setup):
    User, Role, _ = sm_setup
    result, created = await Role.get_or_create(role="editor", role_desc="编辑")
    assert result.role == "editor"
    assert result.id is not None
    assert created is True

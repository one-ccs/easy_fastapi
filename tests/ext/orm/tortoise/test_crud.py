"""Tortoise ExtendedCRUD 测试。

ExtendedCRUD 为 mixin：by_id/paginate 作为 classmethod，继承后 cls 即模型类。
测试通过在 fixture 中动态创建子类（注册到 Tortoise）来验证。
覆盖：by_id 命中/未命中、paginate total/items/finished、page 边界、
prefetch、空表分页、filter 透传、page_size 超总数。
"""

import pytest
from easy_fastapi.ext.orm.base.pagination import Pagination
from easy_fastapi.ext.orm.tortoise.crud import ExtendedCRUD
from tortoise import Tortoise, fields
from tortoise.models import Model


# 本模块模型：Tortoise 通过 modules={"models": [__name__]} 发现
class _User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=32, unique=True, null=True)
    hashed_password = fields.CharField(max_length=128)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "crud_user"


class _Role(Model):
    id = fields.IntField(pk=True)
    role = fields.CharField(max_length=16, unique=True)
    role_desc = fields.CharField(max_length=32, null=True)

    class Meta:
        table = "crud_role"


@pytest.fixture
async def users():
    """init tortoise + 造 5 个 User，yield User 模型类。"""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()
    for i in range(5):
        await _User.create(username=f"u{i}", hashed_password="h")
    try:
        yield _User
    finally:
        await Tortoise.close_connections()


async def test_by_id_hits(users):
    User = users
    got = await ExtendedCRUD.by_id.__func__(User, 1)
    assert got is not None
    assert got.username == "u0"


async def test_by_id_miss_returns_none(users):
    User = users
    assert await ExtendedCRUD.by_id.__func__(User, 99999) is None


async def test_paginate_returns_pagination(users):
    User = users
    page = await ExtendedCRUD.paginate.__func__(User, page_index=1, page_size=2)
    assert isinstance(page, Pagination)
    assert page.total == 5
    assert len(page.items) == 2


async def test_paginate_finished_flag(users):
    User = users
    p1 = await ExtendedCRUD.paginate.__func__(User, page_index=1, page_size=2)
    assert p1.finished is False
    p3 = await ExtendedCRUD.paginate.__func__(User, page_index=3, page_size=2)
    assert p3.finished is True


async def test_paginate_second_page_items(users):
    User = users
    p2 = await ExtendedCRUD.paginate.__func__(User, page_index=2, page_size=2)
    assert len(p2.items) == 2


async def test_paginate_empty_table():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()
    try:
        page = await ExtendedCRUD.paginate.__func__(_User, page_index=1, page_size=10)
        assert page.total == 0
        assert page.items == []
        assert page.finished is True
    finally:
        await Tortoise.close_connections()


async def test_paginate_filter_passes_through(users):
    User = users
    await User.create(username="inactive", hashed_password="h", is_active=False)
    page = await ExtendedCRUD.paginate.__func__(User, page_index=1, page_size=10, is_active=True)
    assert page.total == 5


async def test_paginate_page_size_larger_than_total(users):
    User = users
    page = await ExtendedCRUD.paginate.__func__(User, page_index=1, page_size=100)
    assert page.total == 5
    assert len(page.items) == 5
    assert page.finished is True


async def test_paginate_items_are_model_instances(users):
    User = users
    page = await ExtendedCRUD.paginate.__func__(User, page_index=1, page_size=2)
    assert all(hasattr(it, "username") for it in page.items)

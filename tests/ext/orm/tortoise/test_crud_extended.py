"""Tortoise ExtendedCRUD 新增方法测试（create / update_from_dict / delete_by_ids）。

使用真实 SQLite 内存数据库，与现有 test_crud.py 约定一致。
覆盖：正常路径、边界（空列表/空数据）、异常（不存在记录）。
"""

import pytest
from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.tortoise.crud import ExtendedCRUD
from tortoise import Tortoise, fields
from tortoise.models import Model


# 本模块模型
class _User(Model, ExtendedCRUD):  # type: ignore[misc, valid-type]
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=32, unique=True, null=True)
    hashed_password = fields.CharField(max_length=128)
    is_active = fields.BooleanField(default=True)
    email = fields.CharField(max_length=64, unique=True, null=True)

    class Meta:
        table = "ext_user"


class _Role(Model, ExtendedCRUD):  # type: ignore[misc, valid-type]
    id = fields.IntField(pk=True)
    role = fields.CharField(max_length=16, unique=True)
    role_desc = fields.CharField(max_length=32, null=True)

    class Meta:
        table = "ext_role"


@pytest.fixture
async def users():
    """init tortoise + 造 3 个 User，yield User 模型类。"""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()
    for i in range(3):
        await _User.create(username=f"u{i}", hashed_password="h")
    try:
        yield _User
    finally:
        await Tortoise.close_connections()


@pytest.fixture
async def roles():
    """init tortoise + 造 2 个 Role，yield Role 模型类。"""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()
    await _Role.create(role="admin", role_desc="管理员")
    await _Role.create(role="user", role_desc="用户")
    try:
        yield _Role
    finally:
        await Tortoise.close_connections()


# ── create ──


async def test_create_returns_instance(users):
    User = users
    result = await ExtendedCRUD.create.__func__(User, username="new", hashed_password="h")
    assert result is not None
    assert result.username == "new"
    assert result.id is not None


async def test_create_with_extra_kwargs(users):
    User = users
    result = await ExtendedCRUD.create.__func__(User, username="extra", hashed_password="h", is_active=False)
    assert result.is_active is False


async def test_create_persists_to_db(users):
    User = users
    await ExtendedCRUD.create.__func__(User, username="persist", hashed_password="h")
    found = await User.get_or_none(username="persist")
    assert found is not None


async def test_create_role(roles):
    Role = roles
    result = await ExtendedCRUD.create.__func__(Role, role="editor", role_desc="编辑")
    assert result.role == "editor"


# ── update_from_dict ──


async def test_update_from_dict_updates_fields(users):
    User = users
    user = await User.get(username="u0")
    result = await ExtendedCRUD.update_from_dict.__func__(User, user, {"username": "updated"})
    assert result.username == "updated"


async def test_update_from_dict_persists_to_db(users):
    User = users
    user = await User.get(username="u0")
    await ExtendedCRUD.update_from_dict.__func__(User, user, {"username": "persisted"})
    refetched = await User.get(id=user.id)
    assert refetched.username == "persisted"


async def test_update_from_dict_empty_data_no_change(users):
    User = users
    user = await User.get(username="u0")
    original_name = user.username
    result = await ExtendedCRUD.update_from_dict.__func__(User, user, {})
    assert result.username == original_name


async def test_update_from_dict_returns_same_instance(users):
    User = users
    user = await User.get(username="u0")
    result = await ExtendedCRUD.update_from_dict.__func__(User, user, {"username": "x"})
    assert result.id == user.id


# ── delete_by_ids ──


async def test_delete_by_ids_removes_records(users):
    User = users
    count = await ExtendedCRUD.delete_by_ids.__func__(User, [1, 2])
    assert count == 2
    assert await User.filter(id__in=[1, 2]).count() == 0


async def test_delete_by_ids_returns_count(users):
    User = users
    count = await ExtendedCRUD.delete_by_ids.__func__(User, [1])
    assert count == 1


async def test_delete_by_ids_empty_list_returns_zero(users):
    User = users
    count = await ExtendedCRUD.delete_by_ids.__func__(User, [])
    assert count == 0
    # 确认没有误删
    assert await User.all().count() == 3


async def test_delete_by_ids_nonexistent_id_returns_zero(users):
    User = users
    count = await ExtendedCRUD.delete_by_ids.__func__(User, [99999])
    assert count == 0


async def test_delete_by_ids_partial_existing(users):
    """部分 id 存在、部分不存在，只删除存在的。"""
    User = users
    count = await ExtendedCRUD.delete_by_ids.__func__(User, [1, 99999])
    assert count == 1


# ── 协议满足性 ──


def test_extended_crud_satisfies_base_protocol():
    """ExtendedCRUD 满足 BaseCRUDMixin 协议。"""
    assert isinstance(ExtendedCRUD, BaseCRUDMixin)


async def test_user_model_satisfies_base_protocol(users):
    """运行时 User 模型满足 BaseCRUDMixin。"""
    assert isinstance(users, BaseCRUDMixin)


async def test_role_model_satisfies_base_protocol(roles):
    Role = roles
    assert isinstance(Role, BaseCRUDMixin)


# ── exists / exists_by_email / get_or_create ──


async def test_exists_returns_true_for_existing_username(users):
    User = users
    result = await User.exists(username="u0")
    assert result is True


async def test_exists_returns_false_for_missing_username(users):
    User = users
    result = await User.exists(username="nonexistent")
    assert result is False


async def test_exists_by_email_returns_true(users):
    User = users
    await User.create(username="email_user", email="test@test.com", hashed_password="h")
    result = await User.exists_by_email("test@test.com")
    assert result is True


async def test_exists_by_email_returns_false(users):
    User = users
    result = await User.exists_by_email("no@such.com")
    assert result is False


async def test_get_or_create_returns_existing(roles):
    Role = roles
    result, created = await Role.get_or_create(role="admin", role_desc="管理员")
    assert result.role == "admin"


async def test_get_or_create_creates_new(roles):
    Role = roles
    result, created = await Role.get_or_create(role="editor", role_desc="编辑")
    assert result.role == "editor"


async def test_role_exists_returns_true(roles):
    Role = roles
    result = await Role.exists(role="admin")
    assert result is True


async def test_role_exists_returns_false(roles):
    Role = roles
    result = await Role.exists(role="nonexistent")
    assert result is False

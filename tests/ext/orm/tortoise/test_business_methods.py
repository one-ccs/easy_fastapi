"""Tortoise ExtendedCRUD 业务 classmethod 测试。

模型定义在模块级别，Tortoise 通过 modules={"models": [__name__]} 加载。
"""

import pytest
from easy_fastapi.ext.orm.tortoise.crud import ExtendedCRUD

# 模块级别模型定义（Tortoise 需通过模块路径发现）
from tortoise import fields
from tortoise.models import Model


class User(Model, ExtendedCRUD):
    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=32, null=True, unique=True)
    email = fields.CharField(max_length=64, null=True, unique=True)
    hashed_password = fields.CharField(max_length=128)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "bm_user"

    @property
    def identity(self):
        return self.username or self.email

    @property
    def h_pwd(self):
        return self.hashed_password

    @property
    def scopes(self):
        return []


@pytest.fixture
async def tortoise_user_setup():
    """初始化 Tortoise 内存数据库 + 种子数据，yield User 模型类。"""
    from tortoise import Tortoise

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [__name__]},
    )
    await Tortoise.generate_schemas()

    await User.create(username="u0", hashed_password="h0", is_active=True)
    await User.create(username="u1", email="u1@test.com", hashed_password="h1", is_active=True)

    try:
        yield User
    finally:
        await Tortoise.close_connections()


async def test_get_by_username_found(tortoise_user_setup):
    result = await User.get_by_username("u0")
    assert result is not None
    assert result.username == "u0"


async def test_get_by_username_not_found(tortoise_user_setup):
    result = await User.get_by_username("ghost")
    assert result is None


async def test_get_by_email_found(tortoise_user_setup):
    result = await User.get_by_email("u1@test.com")
    assert result is not None


async def test_get_by_id_found(tortoise_user_setup):
    result = await User.get_by_id(1)
    assert result is not None


async def test_get_by_username_or_email(tortoise_user_setup):
    result = await User.get_by_username_or_email("u0")
    assert result is not None


async def test_create_user(tortoise_user_setup):
    result = await User.create_user(username="new", hashed_password="hp")
    assert result.username == "new"


async def test_update_password(tortoise_user_setup):
    await User.update_password(1, "new_hash")
    result = await User.get_by_id(1)
    assert result.hashed_password == "new_hash"


def test_user_satisfies_user_model_protocol(tortoise_user_setup):
    from easy_fastapi.core.protocols import UserModelProtocol

    assert isinstance(User, UserModelProtocol)

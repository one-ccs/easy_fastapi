"""C6: Tortoise User/Role 模型满足 BaseCRUDMixin 协议验证。

Tortoise 的 User/Role 通过 ExtendedCRUD mixin 补全了 5 个统一 CRUD 方法，
本测试确认运行时模型类满足 BaseCRUDMixin 协议（isinstance 检查 + 方法暴露）。
框架不再持有内置模型，用本地模型验证。
"""

from easy_fastapi.ext.orm.base.crud import BaseCRUDMixin
from easy_fastapi.ext.orm.tortoise.crud import ExtendedCRUD
from tortoise import fields
from tortoise.models import Model

CRUD_METHODS = ["by_id", "paginate", "create", "update_from_dict", "delete_by_ids"]


class User(Model, ExtendedCRUD):  # type: ignore[misc, valid-type]
    id = fields.IntField(primary_key=True)
    username = fields.CharField(max_length=32, unique=True, null=True)
    hashed_password = fields.CharField(max_length=128)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "proto_user"


class Role(Model, ExtendedCRUD):  # type: ignore[misc, valid-type]
    id = fields.IntField(primary_key=True)
    role = fields.CharField(max_length=16, unique=True)
    role_desc = fields.CharField(max_length=32, null=True)

    class Meta:
        table = "proto_role"


def test_tortoise_user_satisfies_base_protocol():
    assert isinstance(User, BaseCRUDMixin)


def test_tortoise_role_satisfies_base_protocol():
    assert isinstance(Role, BaseCRUDMixin)


def test_tortoise_user_exposes_crud_methods():
    for name in CRUD_METHODS:
        assert hasattr(User, name), f"User 缺少 CRUD 方法 {name}"


def test_tortoise_role_exposes_crud_methods():
    for name in CRUD_METHODS:
        assert hasattr(Role, name), f"Role 缺少 CRUD 方法 {name}"


def test_tortoise_extended_crud_mixin_satisfies_protocol():
    assert isinstance(ExtendedCRUD, BaseCRUDMixin)

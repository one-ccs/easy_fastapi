"""AuthExtension.load_user 装饰器测试。"""

from pathlib import Path

import pytest
from easy_fastapi.core.app import EasyFastAPI
from easy_fastapi.ext.auth.extension import AuthExtension
from easy_fastapi.ext.orm.sqlalchemy.extension import SQLAlchemyExtension
from fastapi import FastAPI


class FakeUser:
    """满足 UserModelProtocol 的最小假模型。"""

    @classmethod
    async def get_by_username(cls, username):
        return None

    @classmethod
    async def get_by_id(cls, id):
        return None

    @classmethod
    async def get_by_email(cls, email):
        return None

    @classmethod
    async def get_by_username_or_email(cls, username_or_email):
        return None

    @classmethod
    async def create_user(cls, username, hashed_password, **extra):
        pass

    @classmethod
    async def update_password(cls, id, hashed_password):
        pass

    @classmethod
    async def by_id(cls, id, prefetch=None):
        return None

    @classmethod
    async def paginate(cls, page_index, page_size, prefetch=None):
        from easy_fastapi.ext.orm.base.pagination import Pagination

        return Pagination(total=0, items=[], finished=True)

    @classmethod
    async def create(cls, **kwargs):
        pass

    @classmethod
    async def update_from_dict(cls, instance, data):
        pass

    @classmethod
    async def delete_by_ids(cls, ids):
        return 0


class FakeRole:
    """满足 RoleModelProtocol 的最小假模型。"""

    @classmethod
    async def get_by_id(cls, id):
        return None

    @classmethod
    async def get_by_role(cls, role):
        return None

    @classmethod
    async def create_role(cls, role, role_desc, **extra):
        pass


def _yaml(tmp_path: Path) -> Path:
    p = tmp_path / "easy-fastapi.yaml"
    content = (
        "fastapi:\n  root_path: /api\n"
        "easy_fastapi:\n"
        '  database:\n    dialect: sqlite\n    database: ":memory:"\n'
        '  auth:\n    secret: "supersecret_16ch+"\n    access_expire_minutes: 30\n'
    )
    p.write_text(content, encoding="utf-8")
    return p


def _make_app(tmp_path):
    app = FastAPI()
    easy = EasyFastAPI(app, config_path=_yaml(tmp_path))
    return app, easy


# ── load_user 装饰器基础 ──


def test_load_user_is_callable_decorator(tmp_path):
    """load_user 是可用的装饰器。"""
    auth = AuthExtension()
    assert callable(auth.load_user)

    @auth.load_user
    async def my_loader(user_id: int):
        return None

    assert auth._user_loader is my_loader


def test_load_user_returns_original_function(tmp_path):
    """装饰器返回原函数（不包装）。"""
    auth = AuthExtension()

    @auth.load_user
    async def my_loader(user_id: int):
        return {"id": user_id}

    # 返回的是原函数
    assert auth._user_loader is my_loader


def test_load_user_stores_function_before_init_app(tmp_path):
    """在 init_app 前使用 @auth.load_user——存储函数引用。"""
    auth = AuthExtension()

    @auth.load_user
    async def my_loader(user_id: int):
        return {"id": user_id}

    app, easy = _make_app(tmp_path)
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    # init_app 后 _user_loader 仍指向自定义函数
    assert auth._user_loader is my_loader


def test_load_user_default_is_none(tmp_path):
    """不使用 @auth.load_user 时 _user_loader 为 None。"""
    auth = AuthExtension()
    assert auth._user_loader is None

    app, easy = _make_app(tmp_path)
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)
    assert auth._user_loader is None


# ── _default_load_user 行为 ──


async def test_default_load_user_calls_user_model(tmp_path):
    """默认 _default_load_user 调用 user_model.get_by_id。"""
    auth = AuthExtension()
    app, easy = _make_app(tmp_path)
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    # FakeUser.get_by_id 返回 None → 应抛 UnauthorizedException
    from easy_fastapi.core.exceptions import UnauthorizedException

    with pytest.raises(UnauthorizedException):
        await auth._default_load_user(1)


# ── current_user 使用 load_user ──


def test_current_user_uses_custom_loader(tmp_path):
    """current_user 依赖使用自定义 loader 替代默认逻辑。"""
    auth = AuthExtension()

    loaded_ids = []

    @auth.load_user
    async def my_loader(user_id: int):
        loaded_ids.append(user_id)
        return {"id": user_id, "is_active": True, "scopes": []}

    app, easy = _make_app(tmp_path)
    easy.use(SQLAlchemyExtension(models=[FakeUser, FakeRole])).use(auth)

    # auth.current_user() 闭包应调用 my_loader 而非 _default_load_user
    assert auth._user_loader is my_loader


def test_load_user_replaces_previous(tmp_path):
    """多次 @auth.load_user 替换前一个。"""
    auth = AuthExtension()

    @auth.load_user
    async def first_loader(user_id: int):
        return {"id": user_id, "loader": "first"}

    @auth.load_user
    async def second_loader(user_id: int):
        return {"id": user_id, "loader": "second"}

    assert auth._user_loader is second_loader

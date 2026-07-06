"""Tortoise session/db_session_factory 测试。

覆盖：make_session_factory 满足 DbSessionFactory、factory __call__ 返回 async cm、
session commit/rollback/close 不报错、factory 独立调用、init_tortoise 集成。
注：init_tortoise/generate_schemas 的真实 DB 集成测试放在 test_extension.py
（那里有完整 lifespan 集成），本文件聚焦协议与结构。
"""

from easy_fastapi.core.protocols import DbSessionFactory
from easy_fastapi.ext.orm.tortoise.session import (
    make_session_factory,
)

# 用本测试模块作为 models 模块路径（Tortoise 通过模块路径发现模型）
DB_URL = "sqlite://:memory:"


def test_make_session_factory_satisfies_protocol():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    assert isinstance(factory, DbSessionFactory)


async def test_factory_call_returns_async_context_manager():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    cm = factory()
    assert hasattr(cm, "__aenter__")
    assert hasattr(cm, "__aexit__")


async def test_session_commit_rollback_close_no_error():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    async with factory() as session:
        await session.commit()
        await session.rollback()
        await session.close()


async def test_session_operations_idempotent():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    async with factory() as session:
        await session.commit()
        await session.commit()  # 幂等
        await session.rollback()
        await session.close()
        await session.close()  # 幂等


async def test_factory_independent_sessions():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    async with factory() as s1:
        pass
    async with factory() as s2:
        pass
    # tortoise 无 per-request session，但两个 cm 是独立对象
    assert s1 is not s2


async def test_session_entered_is_not_none():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    async with factory() as session:
        assert session is not None


def test_factory_is_callable():
    factory = make_session_factory(db_url=DB_URL, models=[__name__])
    assert callable(factory)


async def test_factory_multiple_factories():
    # 不同参数造不同 factory，均满足协议
    f1 = make_session_factory(db_url=DB_URL, models=[__name__])
    f2 = make_session_factory(db_url=DB_URL, models=[__name__])
    assert isinstance(f1, DbSessionFactory)
    assert isinstance(f2, DbSessionFactory)


async def test_init_tortoise_and_close():
    """验证 init_tortoise 可正常 init + close（真实集成）。"""
    from easy_fastapi.ext.orm.tortoise.session import generate_schemas, init_tortoise
    from tortoise import Tortoise

    await init_tortoise(db_url=DB_URL, models=[__name__])
    await generate_schemas()
    # Tortoise apps 中应含本模块定义的 User 模型
    app_models = Tortoise.apps.get("models", {})
    assert "User" in app_models
    assert app_models["User"]._meta.db_table == "session_user"
    await Tortoise.close_connections()


# 本模块定义 Tortoise 模型，供 modules={"models": [__name__]} 发现
from tortoise import fields  # noqa: E402
from tortoise.models import Model  # noqa: E402


class User(Model):  # noqa: D101
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=32, unique=True, null=True)
    hashed_password = fields.CharField(max_length=128)

    class Meta:  # noqa: D106
        table = "session_user"

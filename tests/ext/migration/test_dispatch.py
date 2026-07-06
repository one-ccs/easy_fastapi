"""migration 分派测试。"""

import pytest
from easy_fastapi.core.exceptions import ExtensionError
from easy_fastapi.ext.migration.base import dispatch_migration_op


async def test_dispatch_tortoise_calls_aerich(monkeypatch):
    calls = []

    async def fake(app, op, **kw):
        calls.append(("aerich", op, kw.get("db_url"), kw.get("models")))

    monkeypatch.setattr("easy_fastapi.ext.migration.aerich_impl.run", fake)
    await dispatch_migration_op(orm="tortoise", op="migrate", db_url="sqlite://db", models=["a"])
    assert calls == [("aerich", "migrate", "sqlite://db", ["a"])]


async def test_dispatch_sqlalchemy_calls_alembic(monkeypatch):
    calls = []

    async def fake(app, op, **kw):
        calls.append(("alembic", op, kw.get("orm")))

    monkeypatch.setattr("easy_fastapi.ext.migration.alembic_impl.run", fake)
    await dispatch_migration_op(orm="sqlalchemy", op="upgrade")
    assert calls == [("alembic", "upgrade", "sqlalchemy")]


async def test_dispatch_sqlmodel_calls_alembic(monkeypatch):
    calls = []

    async def fake(app, op, **kw):
        calls.append(("alembic", op, kw.get("orm")))

    monkeypatch.setattr("easy_fastapi.ext.migration.alembic_impl.run", fake)
    await dispatch_migration_op(orm="sqlmodel", op="sync")
    assert calls == [("alembic", "sync", "sqlmodel")]


async def test_dispatch_none_orm_raises():
    with pytest.raises(ExtensionError, match="未启用"):
        await dispatch_migration_op(orm=None, op="migrate")


async def test_dispatch_unknown_orm_raises():
    with pytest.raises(ExtensionError, match="不支持的 ORM"):
        await dispatch_migration_op(orm="mongo", op="migrate")


async def test_dispatch_empty_string_orm_raises():
    with pytest.raises(ExtensionError):
        await dispatch_migration_op(orm="", op="init")


async def test_dispatch_tortoise_init(monkeypatch):
    calls = []

    async def fake(app, op, **kw):
        calls.append(("aerich", op))

    monkeypatch.setattr("easy_fastapi.ext.migration.aerich_impl.run", fake)
    await dispatch_migration_op(orm="tortoise", op="init")
    assert calls == [("aerich", "init")]


async def test_dispatch_alembic_transparent_kwargs(monkeypatch):
    """验证 db_url/models 透传到 alembic_impl。"""
    calls = []

    async def fake(app, op, **kw):
        calls.append(kw)

    monkeypatch.setattr("easy_fastapi.ext.migration.alembic_impl.run", fake)
    await dispatch_migration_op(orm="sqlalchemy", op="upgrade", db_url="pg://x", models=["m1"])
    assert calls[0]["db_url"] == "pg://x"
    assert calls[0]["models"] == ["m1"]

"""Core commands/db 真实建表集成测试（从 tests/db_ops/test_ops.py 搬移并改写为新签名）。

Core 的 run_db_* 签名为 (project_dir)，从 marker+yaml 推导 orm/db_url/models。
本测试用 marker+yaml 驱动，验证 sqlmodel/sqlalchemy sync 真实建表、tortoise sync 走 init+schemas、
init/migrate/upgrade 经 dispatch 路由、不支持 ORM 报错。

yaml-driven：sqlite 落 dev.db（验证真实建表）；tortoise 用 :memory: 走 fake 路径。
"""

import json
import sqlite3

import pytest
from easy_fastapi.commands.db import run_db_init, run_db_migrate, run_db_sync, run_db_upgrade
from easy_fastapi.core.config.loader import _clear_config_cache
from easy_fastapi.core.exceptions import ConfigError

MARKER_FILENAME = ".easy-fastapi.json"


def _write_marker(tmp_path, *, orm, db_dialect="sqlite", database=True):
    data = {
        "marker_schema_version": 1,
        "project_layout": "backend-only",
        "options": {"orm": orm, "db_dialect": db_dialect, "database": database},
        "registered_extensions": [f"orm.{orm}"] if database and orm else [],
    }
    (tmp_path / MARKER_FILENAME).write_text(json.dumps(data), encoding="utf-8")


def _write_yaml(app_dir, *, dialect="sqlite", database=":memory:"):
    app_dir.mkdir(parents=True, exist_ok=True)
    lines = ["easy_fastapi:", "  database:", f'    dialect: "{dialect}"']
    if dialect == "sqlite":
        lines.append(f'    database: "{database}"')
    (app_dir / "easy-fastapi.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_cache():
    _clear_config_cache()
    yield
    _clear_config_cache()


async def test_run_db_init_tortoise(monkeypatch, tmp_path):
    _write_marker(tmp_path, orm="tortoise")
    _write_yaml(tmp_path, database=":memory:")
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    await run_db_init(tmp_path)
    assert calls == [("tortoise", "init")]


async def test_run_db_migrate_sqlalchemy(monkeypatch, tmp_path):
    _write_marker(tmp_path, orm="sqlalchemy")
    _write_yaml(tmp_path, database="dev.db")
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    await run_db_migrate(tmp_path)
    assert calls == [("sqlalchemy", "migrate")]


async def test_run_db_upgrade_sqlmodel(monkeypatch, tmp_path):
    _write_marker(tmp_path, orm="sqlmodel")
    _write_yaml(tmp_path, database="dev.db")
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    await run_db_upgrade(tmp_path)
    assert calls == [("sqlmodel", "upgrade")]


async def test_run_db_sync_sqlmodel_creates_table(tmp_path, monkeypatch):
    """sqlmodel sync 真实建表（dev.db 落在 tmp_path）。

    _sync 动态 import 项目模型模块，注册进 SQLModel.metadata 后 create_all。
    用唯一模块名避免与其他测试的 app.models 缓存冲突。
    """
    mod_name = "dbops_sm_proj"
    (tmp_path / f"{mod_name}.py").write_text(
        "from sqlmodel import SQLModel, Field\n"
        "class User(SQLModel, table=True):\n"
        "    __tablename__ = 'dbops_user'\n"
        "    __table_args__ = {'extend_existing': True}\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    username: str | None = Field(default=None, index=True)\n"
        "    hashed_password: str\n"
        "class Role(SQLModel, table=True):\n"
        "    __tablename__ = 'dbops_role'\n"
        "    __table_args__ = {'extend_existing': True}\n"
        "    id: int | None = Field(default=None, primary_key=True)\n"
        "    role: str = Field(unique=True)\n",
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))

    _write_marker(tmp_path, orm="sqlmodel")
    _write_yaml(tmp_path, database="dev.db")
    monkeypatch.chdir(tmp_path)

    from easy_fastapi.ext.migration.base import dispatch_migration_op

    await dispatch_migration_op(orm="sqlmodel", op="sync", db_url="sqlite+aiosqlite:///dev.db", models=[mod_name])

    db_path = tmp_path / "dev.db"
    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "dbops_user" in tables

    sys.path.remove(str(tmp_path))
    sys.modules.pop(mod_name, None)


async def test_run_db_sync_sqlalchemy_creates_table(tmp_path, monkeypatch):
    """sqlalchemy sync 真实建表。

    _sync 动态 import 项目模型模块，从 DeclarativeBase 子类提取 metadata 后 create_all。
    用唯一模块名避免与其他测试的模块缓存冲突。
    """
    mod_name = "dbops_sa_proj"
    (tmp_path / f"{mod_name}.py").write_text(
        "from sqlalchemy import Boolean, Column, Integer, String\n"
        "from sqlalchemy.orm import DeclarativeBase\n"
        "class Base(DeclarativeBase):\n"
        "    pass\n"
        "class User(Base):\n"
        "    __tablename__ = 'dbops_sa_user'\n"
        "    id = Column(Integer, primary_key=True)\n"
        "    username = Column(String(32), unique=True)\n"
        "    hashed_password = Column(String(128), nullable=False)\n"
        "    is_active = Column(Boolean, default=True)\n",
        encoding="utf-8",
    )
    import sys

    sys.path.insert(0, str(tmp_path))

    _write_marker(tmp_path, orm="sqlalchemy")
    _write_yaml(tmp_path, database="dev.db")
    monkeypatch.chdir(tmp_path)

    from easy_fastapi.ext.migration.base import dispatch_migration_op

    await dispatch_migration_op(orm="sqlalchemy", op="sync", db_url="sqlite+aiosqlite:///dev.db", models=[mod_name])

    db_path = tmp_path / "dev.db"
    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "dbops_sa_user" in tables

    sys.path.remove(str(tmp_path))
    sys.modules.pop(mod_name, None)


async def test_run_db_sync_tortoise_calls_init_and_schemas(monkeypatch, tmp_path):
    _write_marker(tmp_path, orm="tortoise")
    _write_yaml(tmp_path, database=":memory:")
    monkeypatch.chdir(tmp_path)
    calls = []

    async def fake_init(*, db_url, models=None, **kw):
        calls.append(("init_tortoise", db_url))

    async def fake_schemas():
        calls.append(("generate_schemas",))

    monkeypatch.setattr("easy_fastapi.ext.orm.tortoise.session.init_tortoise", fake_init)
    monkeypatch.setattr("easy_fastapi.ext.orm.tortoise.session.generate_schemas", fake_schemas)
    await run_db_sync(tmp_path)
    assert ("init_tortoise", "sqlite://:memory:") in calls
    assert ("generate_schemas",) in calls


async def test_run_db_migrate_unsupported_orm_raises(tmp_path):
    """marker.orm 为不支持的值时，resolve_db_config 报 ConfigError。"""
    _write_marker(tmp_path, orm="mongo")
    _write_yaml(tmp_path, database="dev.db")
    with pytest.raises(ConfigError, match="不支持的 ORM"):
        await run_db_migrate(tmp_path)


async def test_run_db_init_passes_models(monkeypatch, tmp_path):
    _write_marker(tmp_path, orm="tortoise")
    _write_yaml(tmp_path, database=":memory:")
    monkeypatch.chdir(tmp_path)
    captured = {}

    async def fake_dispatch(*, orm, op, **kw):
        captured.update(kw)

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    await run_db_init(tmp_path)
    assert captured["models"] == ["app.models"]

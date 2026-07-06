"""Core commands/db 执行逻辑单测。

覆盖：run_db_init/migrate/upgrade/sync 的 dispatch 调用、
tortoise sync 的 init_tortoise+generate_schemas 路径、无数据库配置报错。
通过 monkeypatch dispatch_migration_op / tortoise session 符号验证路由正确，
不真实建连。

yaml-driven：在 marker 旁写 easy-fastapi.yaml 的 database 段，
经 resolve_db_config 构建真实 db_url（sqlite → sqlite://:memory:）。
"""

import json

import pytest
from easy_fastapi.core.config.loader import _clear_config_cache
from easy_fastapi.core.exceptions import ConfigError

MARKER_FILENAME = ".easy-fastapi.json"


def _write_marker(tmp_path, *, orm="sqlmodel", db_dialect="sqlite", database=True):
    data = {
        "marker_schema_version": 1,
        "project_layout": "backend-only",
        "options": {"orm": orm, "db_dialect": db_dialect, "database": database},
        "registered_extensions": [f"orm.{orm}"] if database and orm else [],
    }
    (tmp_path / MARKER_FILENAME).write_text(json.dumps(data), encoding="utf-8")


def _write_yaml(
    app_dir,
    *,
    dialect="sqlite",
    database=":memory:",
    username="root",
    password="123",
    host="localhost",
    port=3306,
):
    app_dir.mkdir(parents=True, exist_ok=True)
    lines = ["easy_fastapi:", "  database:", f'    dialect: "{dialect}"']
    if dialect == "sqlite":
        lines.append(f'    database: "{database}"')
    else:
        lines.extend(
            [
                f'    username: "{username}"',
                f'    password: "{password}"',
                f'    database: "{database}"',
                f'    host: "{host}"',
                f"    port: {port}",
            ]
        )
    (app_dir / "easy-fastapi.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _setup(tmp_path, *, orm="sqlmodel", db_dialect="sqlite", database=True):
    """写 marker + 对应 yaml（backend-only 时 yaml 与 marker 同级）。"""
    _write_marker(tmp_path, orm=orm, db_dialect=db_dialect, database=database)
    if database and orm:
        db = ":memory:" if db_dialect == "sqlite" else "app"
        _write_yaml(tmp_path, dialect=db_dialect, database=db)


@pytest.fixture(autouse=True)
def _clear_cache():
    _clear_config_cache()
    yield
    _clear_config_cache()


async def test_run_db_init_dispatches(monkeypatch, tmp_path):
    _setup(tmp_path, orm="tortoise")
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op, kw.get("db_url"), kw.get("models")))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    from easy_fastapi.commands.db import run_db_init

    await run_db_init(tmp_path)
    assert calls == [("tortoise", "init", "sqlite://:memory:", ["app.models"])]


async def test_run_db_migrate_dispatches(monkeypatch, tmp_path):
    _setup(tmp_path, orm="sqlalchemy")
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    from easy_fastapi.commands.db import run_db_migrate

    await run_db_migrate(tmp_path)
    assert calls == [("sqlalchemy", "migrate")]


async def test_run_db_upgrade_dispatches(monkeypatch, tmp_path):
    _setup(tmp_path, orm="sqlmodel")
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    from easy_fastapi.commands.db import run_db_upgrade

    await run_db_upgrade(tmp_path)
    assert calls == [("sqlmodel", "upgrade")]


async def test_run_db_sync_sqlmodel_dispatches(monkeypatch, tmp_path):
    _setup(tmp_path, orm="sqlmodel")
    calls = []

    async def fake_dispatch(*, orm, op, **kw):
        calls.append((orm, op))

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    from easy_fastapi.commands.db import run_db_sync

    await run_db_sync(tmp_path)
    assert calls == [("sqlmodel", "sync")]


async def test_run_db_sync_tortoise_calls_init_and_schemas(monkeypatch, tmp_path):
    _setup(tmp_path, orm="tortoise")
    calls = []

    async def fake_init(*, db_url, models=None, **kw):
        calls.append(("init_tortoise", db_url, models))

    async def fake_schemas():
        calls.append(("generate_schemas",))

    monkeypatch.setattr("easy_fastapi.ext.orm.tortoise.session.init_tortoise", fake_init)
    monkeypatch.setattr("easy_fastapi.ext.orm.tortoise.session.generate_schemas", fake_schemas)
    from easy_fastapi.commands.db import run_db_sync

    await run_db_sync(tmp_path)
    assert ("init_tortoise", "sqlite://:memory:", ["app.models"]) in calls
    assert ("generate_schemas",) in calls


async def test_run_db_sync_tortoise_does_not_call_dispatch(monkeypatch, tmp_path):
    """tortoise sync 不走 dispatch（无 alembic sync）。"""
    _setup(tmp_path, orm="tortoise")

    async def fake_dispatch(*, orm, op, **kw):
        raise AssertionError(f"tortoise sync 不应走 dispatch，却被调用 op={op}")

    async def fake_init(*, db_url, models=None, **kw):
        return None

    async def fake_schemas():
        return None

    monkeypatch.setattr("easy_fastapi.commands.db.dispatch_migration_op", fake_dispatch)
    monkeypatch.setattr("easy_fastapi.ext.orm.tortoise.session.init_tortoise", fake_init)
    monkeypatch.setattr("easy_fastapi.ext.orm.tortoise.session.generate_schemas", fake_schemas)
    from easy_fastapi.commands.db import run_db_sync

    await run_db_sync(tmp_path)  # 不抛 AssertionError 即通过


async def test_run_db_no_database_raises(tmp_path):
    _setup(tmp_path, orm=None, database=False)
    from easy_fastapi.commands.db import run_db_init

    with pytest.raises(ConfigError):
        await run_db_init(tmp_path)


async def test_run_db_missing_marker_raises(tmp_path):
    from easy_fastapi.commands.db import run_db_sync

    with pytest.raises(ConfigError):
        await run_db_sync(tmp_path)

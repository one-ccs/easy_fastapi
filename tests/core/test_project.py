"""easy_fastapi.project 共享上下文层测试。

覆盖：find_project_root / resolve_config_path / read_marker / app_target / app_target_from_dir / resolve_db_config。
"""

import json

import pytest
from easy_fastapi.core.exceptions import ConfigError
from easy_fastapi.project import (
    MARKER_FILENAME,
    app_target,
    app_target_from_dir,
    find_project_root,
    read_marker,
    resolve_config_path,
    resolve_db_config,
)


def _write_marker(tmp_path, *, layout="backend-only", orm="sqlmodel", db_dialect="sqlite", database=True):
    data = {
        "marker_schema_version": 1,
        "project_layout": layout,
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


# ── read_marker ──


def test_read_marker_returns_dict(tmp_path):
    _write_marker(tmp_path)
    result = read_marker(tmp_path)
    assert result["marker_schema_version"] == 1
    assert result["project_layout"] == "backend-only"
    assert result["options"]["orm"] == "sqlmodel"


def test_read_marker_missing_raises(tmp_path):
    with pytest.raises(ConfigError):
        read_marker(tmp_path)


def test_read_marker_corrupt_raises(tmp_path):
    (tmp_path / MARKER_FILENAME).write_text("not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        read_marker(tmp_path)


# ── app_target ──


def test_app_target_backend_only():
    marker = {"project_layout": "backend-only", "options": {}}
    app_str, app_dir = app_target(marker)
    assert app_str == "app.main:app"
    assert app_dir is None


def test_app_target_fullstack():
    marker = {"project_layout": "fullstack", "options": {}}
    app_str, app_dir = app_target(marker)
    assert app_str == "app.main:app"
    assert app_dir == "backend"


def test_app_target_default_layout():
    marker = {"options": {}}
    app_str, app_dir = app_target(marker)
    assert app_str == "app.main:app"
    assert app_dir is None


# ── app_target_from_dir ──


def test_app_target_from_dir_backend_only(tmp_path):
    _write_marker(tmp_path, layout="backend-only")
    app_str, app_dir = app_target_from_dir(tmp_path)
    assert app_str == "app.main:app"
    assert app_dir is None


def test_app_target_from_dir_fullstack(tmp_path):
    _write_marker(tmp_path, layout="fullstack")
    app_str, app_dir = app_target_from_dir(tmp_path)
    assert app_str == "app.main:app"
    assert app_dir == "backend"


def test_app_target_from_dir_missing_marker(tmp_path):
    with pytest.raises(ConfigError):
        app_target_from_dir(tmp_path)


# ── resolve_db_config ──


def test_resolve_db_config_sqlite_sqlmodel(tmp_path):
    _write_marker(tmp_path, orm="sqlmodel", db_dialect="sqlite")
    _write_yaml(tmp_path, dialect="sqlite", database=":memory:")
    orm, db_url, models, app_dir = resolve_db_config(tmp_path)
    assert orm == "sqlmodel"
    assert db_url == "sqlite+aiosqlite:///:memory:"
    assert models == ["app.models"]
    assert app_dir == tmp_path


def test_resolve_db_config_sqlite_tortoise(tmp_path):
    _write_marker(tmp_path, orm="tortoise", db_dialect="sqlite")
    _write_yaml(tmp_path, dialect="sqlite", database="db.sqlite")
    orm, db_url, models, app_dir = resolve_db_config(tmp_path)
    assert orm == "tortoise"
    assert db_url == "sqlite://db.sqlite"
    assert app_dir == tmp_path


def test_resolve_db_config_mysql(tmp_path):
    _write_marker(tmp_path, orm="sqlalchemy", db_dialect="mysql")
    _write_yaml(tmp_path, dialect="mysql", username="root", password="123", database="app", host="localhost", port=3306)
    orm, db_url, models, app_dir = resolve_db_config(tmp_path)
    assert orm == "sqlalchemy"
    assert "mysql+asyncmy" in db_url
    assert "root:123" in db_url


def test_resolve_db_config_fullstack(tmp_path):
    _write_marker(tmp_path, layout="fullstack", orm="tortoise", db_dialect="sqlite")
    _write_yaml(tmp_path / "backend", dialect="sqlite", database=":memory:")
    orm, db_url, models, app_dir = resolve_db_config(tmp_path)
    assert app_dir == tmp_path / "backend"


def test_resolve_db_config_no_orm_raises(tmp_path):
    _write_marker(tmp_path, orm=None, database=True)
    with pytest.raises(ConfigError, match="ORM"):
        resolve_db_config(tmp_path)


def test_resolve_db_config_no_database_raises(tmp_path):
    _write_marker(tmp_path, orm=None, database=False)
    with pytest.raises(ConfigError, match="数据库"):
        resolve_db_config(tmp_path)


def test_resolve_db_config_invalid_orm_raises(tmp_path):
    _write_marker(tmp_path, orm="peewee", db_dialect="sqlite")
    _write_yaml(tmp_path, dialect="sqlite", database=":memory:")
    with pytest.raises(ConfigError, match="不支持的 ORM"):
        resolve_db_config(tmp_path)


def test_resolve_db_config_missing_marker_raises(tmp_path):
    with pytest.raises(ConfigError):
        resolve_db_config(tmp_path)


# ── find_project_root ──


def test_find_project_root_in_project_dir(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    root = find_project_root()
    assert root == tmp_path


def test_find_project_root_explicit_start(tmp_path):
    _write_marker(tmp_path)
    root = find_project_root(tmp_path)
    assert root == tmp_path


def test_find_project_root_not_in_project_dir_raises(tmp_path, monkeypatch):
    """CWD 不含 marker 时报错——禁止在非项目根目录启动。"""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError, match=".easy-fastapi.json"):
        find_project_root()


def test_find_project_root_subdir_not_accepted(tmp_path, monkeypatch):
    """CWD 在项目子目录时也报错——必须在项目根目录启动。"""
    _write_marker(tmp_path)
    sub = tmp_path / "app" / "routers"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    with pytest.raises(ConfigError, match=".easy-fastapi.json"):
        find_project_root()


# ── resolve_config_path ──


def test_resolve_config_path_backend_only(tmp_path, monkeypatch):
    _write_marker(tmp_path, layout="backend-only")
    _write_yaml(tmp_path)
    monkeypatch.chdir(tmp_path)
    yaml_path = resolve_config_path()
    assert yaml_path == tmp_path / "easy-fastapi.yaml"


def test_resolve_config_path_fullstack(tmp_path, monkeypatch):
    _write_marker(tmp_path, layout="fullstack")
    _write_yaml(tmp_path / "backend")
    monkeypatch.chdir(tmp_path)
    yaml_path = resolve_config_path()
    assert yaml_path == tmp_path / "backend" / "easy-fastapi.yaml"


def test_resolve_config_path_explicit_start(tmp_path):
    _write_marker(tmp_path)
    _write_yaml(tmp_path)
    yaml_path = resolve_config_path(tmp_path)
    assert yaml_path == tmp_path / "easy-fastapi.yaml"


def test_resolve_config_path_missing_yaml_raises(tmp_path):
    _write_marker(tmp_path)
    with pytest.raises(ConfigError, match="easy-fastapi.yaml"):
        resolve_config_path(tmp_path)


def test_resolve_config_path_missing_marker_raises(tmp_path):
    with pytest.raises(ConfigError, match=".easy-fastapi.json"):
        resolve_config_path(tmp_path)


def test_resolve_config_path_subdir_cwd_raises(tmp_path, monkeypatch):
    """CWD 在项目子目录时报错——必须在项目根目录启动。"""
    _write_marker(tmp_path)
    _write_yaml(tmp_path)
    sub = tmp_path / "app" / "services"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    with pytest.raises(ConfigError, match=".easy-fastapi.json"):
        resolve_config_path()

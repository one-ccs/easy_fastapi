"""CLI 守卫 require_project 测试（≥8 用例）。"""

import json

import pytest
from easy_fastapi.core.exceptions import ConfigError
from easy_fastapi_cli._guard import require_project


def _write_marker(tmp_path, *, layout="backend-only", orm=None, database=False):
    data = {
        "marker_schema_version": 1,
        "project_layout": layout,
        "options": {"orm": orm, "db_dialect": "sqlite", "database": database},
        "registered_extensions": [f"orm.{orm}"] if orm and database else [],
    }
    (tmp_path / ".easy-fastapi.json").write_text(json.dumps(data), encoding="utf-8")


# ── 1. 无 marker 时抛 ConfigError ──


def test_require_project_missing_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError):
        require_project()


# ── 2. 有 marker 时返回 marker dict ──


def test_require_project_present(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    data = require_project()
    assert data["marker_schema_version"] == 1


# ── 3. 损坏 marker 抛 ConfigError ──


def test_require_project_corrupt_raises(tmp_path, monkeypatch):
    (tmp_path / ".easy-fastapi.json").write_text("not json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError):
        require_project()


# ── 4. 空 marker 文件抛 ConfigError ──


def test_require_project_empty_raises(tmp_path, monkeypatch):
    (tmp_path / ".easy-fastapi.json").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigError):
        require_project()


# ── 5. marker 含 orm 信息 ──


def test_require_project_with_orm(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="tortoise", database=True)
    monkeypatch.chdir(tmp_path)
    data = require_project()
    assert data["options"]["orm"] == "tortoise"


# ── 6. marker 含 fullstack 布局 ──


def test_require_project_fullstack(tmp_path, monkeypatch):
    _write_marker(tmp_path, layout="fullstack")
    monkeypatch.chdir(tmp_path)
    data = require_project()
    assert data["project_layout"] == "fullstack"


# ── 7. db/gen/run 三命令均用 require_project（集成：无 marker 统一报错）──


def test_db_uses_guard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from easy_fastapi_cli.main import app
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["db", "init"])
    assert result.exit_code != 0


def test_gen_uses_guard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from easy_fastapi_cli.main import app
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["gen"])
    assert result.exit_code != 0


def test_run_uses_guard(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from easy_fastapi_cli.main import app
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["run"])
    assert result.exit_code != 0


# ── 10. require_project 连续调用无副作用 ──


def test_require_project_idempotent(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="sqlalchemy", database=True)
    monkeypatch.chdir(tmp_path)
    data1 = require_project()
    data2 = require_project()
    assert data1["marker_schema_version"] == data2["marker_schema_version"]

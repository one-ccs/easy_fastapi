"""efa db 命令测试（CLI 薄壳：转发到项目 venv，≥8 用例）。

改写后 CLI db 不再进程内调 db_ops，而是经 venv_bridge 转发：
  uv run --no-sync --directory <root> python -m easy_fastapi._runner db <action>
测试 patch venv_bridge.run_in_project_venv 捕获转发命令。
marker 校验（缺失/损坏/无 database/orm）仍在 CLI 侧做轻探测。
"""

import json

from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _write_marker(tmp_path, *, orm="sqlmodel", dialect="sqlite", database=True):
    (tmp_path / ".easy-fastapi.json").write_text(
        json.dumps(
            {
                "marker_schema_version": 1,
                "project_layout": "backend-only",
                "options": {"orm": orm, "db_dialect": dialect, "database": database},
                "registered_extensions": [f"orm.{orm}"] if database and orm else [],
            }
        ),
        encoding="utf-8",
    )


def _patch_bridge(monkeypatch):
    """patch venv_bridge.run_in_project_venv，返回 captured 字典。"""
    import easy_fastapi_cli.commands.db as dbmod

    captured = {}

    def fake_run(project_dir, cmd):
        captured.update(project_dir=str(project_dir), cmd=list(cmd))

    monkeypatch.setattr(dbmod, "run_in_project_venv", fake_run)
    return captured


# ── 1. 无 marker 时 db init 报错退出 ──


def test_db_init_no_marker_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code != 0


# ── 2. 无 marker 时 db sync 报错退出 ──


def test_db_sync_no_marker_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["db", "sync"])
    assert result.exit_code != 0


# ── 3. marker 无 database 时报错 ──


def test_db_no_database_raises(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm=None, database=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code != 0


# ── 4. marker 无 orm 时报错 ──


def test_db_no_orm_raises(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm=None, database=True)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["db", "migrate"])
    assert result.exit_code != 0


# ── 5. sync 转发 _runner db sync ──


def test_db_sync_forwards(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="sqlmodel", dialect="sqlite")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["db", "sync"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"] == ["python", "-m", "easy_fastapi._runner", "db", "sync"]


# ── 6. init 转发 _runner db init ──


def test_db_init_forwards(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="tortoise", dialect="sqlite")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"] == ["python", "-m", "easy_fastapi._runner", "db", "init"]


# ── 7. migrate 转发 _runner db migrate ──


def test_db_migrate_forwards(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="sqlalchemy", dialect="mysql")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["db", "migrate"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"] == ["python", "-m", "easy_fastapi._runner", "db", "migrate"]


# ── 8. upgrade 转发 _runner db upgrade ──


def test_db_upgrade_forwards(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="sqlmodel", dialect="postgres")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["db", "upgrade"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"] == ["python", "-m", "easy_fastapi._runner", "db", "upgrade"]


# ── 9. 转发命令含 --directory 指向项目根 ──


def test_db_forwards_with_directory(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm="sqlmodel", dialect="sqlite")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["db", "sync"])
    assert result.exit_code == 0, result.output
    assert captured["project_dir"] == str(tmp_path)


# ── 10. db --help 列出四子命令 ──


def test_db_help_lists_subcommands():
    result = runner.invoke(app, ["db", "--help"])
    assert result.exit_code == 0
    for sub in ("init", "migrate", "upgrade", "sync"):
        assert sub in result.output


# ── 11. 损坏 marker 报错退出 ──


def test_db_corrupt_marker_raises(tmp_path, monkeypatch):
    (tmp_path / ".easy-fastapi.json").write_text("not json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["db", "sync"])
    assert result.exit_code != 0

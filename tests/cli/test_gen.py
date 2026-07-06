"""efa gen 命令测试（CLI 薄壳：转发到项目 venv，≥8 用例）。

改写后 CLI gen 不再进程内调 introspector/codegen，而是经 venv_bridge 转发：
  uv run --no-sync --directory <root> python -m easy_fastapi._runner gen [--force]
测试 patch venv_bridge.run_in_project_venv 捕获转发命令。
marker 校验（缺失/损坏/无 orm）仍在 CLI 侧做轻探测。
"""

import json

from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _write_marker(tmp_path, *, orm="tortoise", database=True):
    (tmp_path / ".easy-fastapi.json").write_text(
        json.dumps(
            {
                "marker_schema_version": 1,
                "project_layout": "backend-only",
                "options": {"orm": orm, "db_dialect": "sqlite", "database": database},
                "registered_extensions": [f"orm.{orm}"] if database and orm else [],
            }
        ),
        encoding="utf-8",
    )


def _patch_bridge(monkeypatch):
    """patch venv_bridge.run_in_project_venv，返回 captured 字典。"""
    import easy_fastapi_cli.commands.gen as genmod

    captured = {}

    def fake_run(project_dir, cmd):
        captured.update(project_dir=str(project_dir), cmd=list(cmd))

    monkeypatch.setattr(genmod, "run_in_project_venv", fake_run)
    return captured


# ── 1. 无 marker 时 gen 报错退出 ──


def test_gen_no_marker_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gen"])
    assert result.exit_code != 0


# ── 2. marker 无 orm 时 gen 报错 ──


def test_gen_no_orm_raises(tmp_path, monkeypatch):
    _write_marker(tmp_path, orm=None, database=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gen"])
    assert result.exit_code != 0


# ── 3. gen 转发 _runner gen ──


def test_gen_forwards(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["gen"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"] == ["python", "-m", "easy_fastapi._runner", "gen"]


# ── 4. gen --force 转发含 --force ──


def test_gen_force_forwards(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["gen", "--force"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"] == ["python", "-m", "easy_fastapi._runner", "gen", "--force"]


# ── 5. 转发命令含 --directory 指向项目根 ──


def test_gen_forwards_with_directory(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["gen"])
    assert result.exit_code == 0, result.output
    assert captured["project_dir"] == str(tmp_path)


# ── 6. 默认不含 --force ──


def test_gen_default_no_force(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["gen"])
    assert result.exit_code == 0, result.output
    assert "--force" not in captured["cmd"]


# ── 7. 损坏 marker 报错退出 ──


def test_gen_corrupt_marker_raises(tmp_path, monkeypatch):
    (tmp_path / ".easy-fastapi.json").write_text("not json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gen"])
    assert result.exit_code != 0


# ── 8. gen --help 可运行 ──


def test_gen_help():
    result = runner.invoke(app, ["gen", "--help"])
    assert result.exit_code == 0
    assert "force" in result.output.lower()

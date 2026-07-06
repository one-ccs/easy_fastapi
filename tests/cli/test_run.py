"""efa run 命令测试（CLI 薄壳：转发到项目 venv，≥8 用例）。

改写后 CLI run 不再进程内调 uvicorn，而是经 venv_bridge 转发：
  uv run --no-sync --directory <root> uvicorn app.main:app [--app-dir backend] --host --port [--reload]
测试 patch venv_bridge.run_in_project_venv 捕获转发命令。
"""

import json

from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _write_marker(tmp_path, *, layout="backend-only"):
    (tmp_path / ".easy-fastapi.json").write_text(
        json.dumps(
            {
                "marker_schema_version": 1,
                "project_layout": layout,
                "options": {"orm": "sqlmodel", "db_dialect": "sqlite", "database": True},
                "registered_extensions": ["orm.sqlmodel"],
            }
        ),
        encoding="utf-8",
    )


def _patch_bridge(monkeypatch):
    """patch venv_bridge.run_in_project_venv，返回 captured 字典。"""
    import easy_fastapi_cli.commands.run as runmod

    captured = {}

    def fake_run(project_dir, cmd):
        captured.update(project_dir=str(project_dir), cmd=list(cmd))

    monkeypatch.setattr(runmod, "run_in_project_venv", fake_run)
    return captured


# ── 1. 非项目目录（无 marker）报错退出 ──


def test_run_outside_project_warns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0
    assert "项目" in result.output or "marker" in result.output.lower() or "Easy FastAPI" in result.output


# ── 2. 项目目录转发 uvicorn 命令 ──


def test_run_in_project_forwards_uvicorn(tmp_path, monkeypatch):
    _write_marker(tmp_path, layout="backend-only")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    assert captured["cmd"][0] == "uvicorn"
    assert "app.main:app" in captured["cmd"]


# ── 3. fullstack 项目转发含 --app-dir backend ──


def test_run_fullstack_forwards_app_dir(tmp_path, monkeypatch):
    _write_marker(tmp_path, layout="fullstack")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    assert "--app-dir" in captured["cmd"]
    assert "backend" in captured["cmd"]


# ── 4. backend-only 不含 --app-dir ──


def test_run_backend_only_no_app_dir(tmp_path, monkeypatch):
    _write_marker(tmp_path, layout="backend-only")
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    assert "--app-dir" not in captured["cmd"]


# ── 5. 自定义 host 转发 ──


def test_run_custom_host(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run", "--host", "0.0.0.0"])
    assert result.exit_code == 0, result.output
    assert "--host" in captured["cmd"]
    assert "0.0.0.0" in captured["cmd"]


# ── 6. 自定义 port 转发 ──


def test_run_custom_port(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run", "--port", "9999"])
    assert result.exit_code == 0, result.output
    assert "--port" in captured["cmd"]
    assert "9999" in captured["cmd"]


# ── 7. --reload 转发 ──


def test_run_reload_flag(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run", "--reload"])
    assert result.exit_code == 0, result.output
    assert "--reload" in captured["cmd"]


# ── 8. 默认 reload=False 不含 --reload ──


def test_run_default_no_reload(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    assert "--reload" not in captured["cmd"]


# ── 9. 默认 host/port ──


def test_run_default_host_port(tmp_path, monkeypatch):
    _write_marker(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured = _patch_bridge(monkeypatch)
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    assert "localhost" in captured["cmd"]
    assert "8000" in captured["cmd"]


# ── 10. 损坏 marker 报错退出 ──


def test_run_corrupt_marker_raises(tmp_path, monkeypatch):
    (tmp_path / ".easy-fastapi.json").write_text("not json", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0


# ── 11. run --help 可运行且含 host/port/reload ──


def test_run_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    out = result.output.lower()
    assert "host" in out
    assert "port" in out
    assert "reload" in out

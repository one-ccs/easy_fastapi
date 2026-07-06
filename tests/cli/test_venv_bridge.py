"""CLI venv_bridge 转发层单测。

覆盖：build_run_command（backend-only/fullstack/reload 控制）、
build_db_command（各 action）、build_gen_command（force/no-force）、
run_in_project_venv（subprocess 调用 + uv run 前缀 + 失败友好退出）。
"""

import json

import pytest
from easy_fastapi.project import MARKER_FILENAME


def _write_marker(tmp_path, *, layout="backend-only"):
    data = {
        "marker_schema_version": 1,
        "project_layout": layout,
        "options": {"orm": "sqlmodel", "db_dialect": "sqlite", "database": True},
        "registered_extensions": ["orm.sqlmodel"],
    }
    (tmp_path / MARKER_FILENAME).write_text(json.dumps(data), encoding="utf-8")


# ── build_run_command ──


def test_build_run_command_backend_only(tmp_path):
    _write_marker(tmp_path, layout="backend-only")
    from easy_fastapi_cli.venv_bridge import build_run_command

    cmd = build_run_command(tmp_path, host="localhost", port=8000, reload=False)
    assert cmd[0] == "uvicorn"
    assert "app.main:app" in cmd
    assert "--host" in cmd
    assert "localhost" in cmd
    assert "--port" in cmd
    assert "8000" in cmd
    # backend-only 不传 --app-dir
    assert "--app-dir" not in cmd


def test_build_run_command_fullstack(tmp_path):
    _write_marker(tmp_path, layout="fullstack")
    from easy_fastapi_cli.venv_bridge import build_run_command

    cmd = build_run_command(tmp_path, host="0.0.0.0", port=9999, reload=True)
    assert "--app-dir" in cmd
    assert "backend" in cmd
    assert "--reload" in cmd


def test_build_run_command_no_reload_no_flag(tmp_path):
    _write_marker(tmp_path, layout="backend-only")
    from easy_fastapi_cli.venv_bridge import build_run_command

    cmd = build_run_command(tmp_path, host="localhost", port=8000, reload=False)
    assert "--reload" not in cmd


def test_build_run_command_fullstack_app_dir_before_host(tmp_path):
    """fullstack 下 --app-dir 应在 --host 之前（uvicorn 参数顺序）。"""
    _write_marker(tmp_path, layout="fullstack")
    from easy_fastapi_cli.venv_bridge import build_run_command

    cmd = build_run_command(tmp_path, host="localhost", port=8000, reload=False)
    app_dir_idx = cmd.index("--app-dir")
    host_idx = cmd.index("--host")
    assert app_dir_idx < host_idx


# ── build_db_command ──


def test_build_db_command_sync(tmp_path):
    from easy_fastapi_cli.venv_bridge import build_db_command

    cmd = build_db_command(action="sync")
    assert cmd == ["python", "-m", "easy_fastapi._runner", "db", "sync"]


def test_build_db_command_init(tmp_path):
    from easy_fastapi_cli.venv_bridge import build_db_command

    cmd = build_db_command(action="init")
    assert cmd == ["python", "-m", "easy_fastapi._runner", "db", "init"]


def test_build_db_command_migrate(tmp_path):
    from easy_fastapi_cli.venv_bridge import build_db_command

    cmd = build_db_command(action="migrate")
    assert cmd == ["python", "-m", "easy_fastapi._runner", "db", "migrate"]


# ── build_gen_command ──


def test_build_gen_command_no_force(tmp_path):
    from easy_fastapi_cli.venv_bridge import build_gen_command

    cmd = build_gen_command(force=False)
    assert cmd == ["python", "-m", "easy_fastapi._runner", "gen"]


def test_build_gen_command_force(tmp_path):
    from easy_fastapi_cli.venv_bridge import build_gen_command

    cmd = build_gen_command(force=True)
    assert cmd == ["python", "-m", "easy_fastapi._runner", "gen", "--force"]


# ── run_in_project_venv（自动加 uv run 前缀）──


def test_run_in_project_venv_calls_subprocess(tmp_path, monkeypatch):
    from easy_fastapi_cli.venv_bridge import run_in_project_venv

    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        captured["check"] = kw.get("check", False)

    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.subprocess.run", fake_run)
    run_in_project_venv(tmp_path, ["echo", "hello"])
    assert captured["cmd"] == ["uv", "run", "--no-sync", "--directory", str(tmp_path), "echo", "hello"]
    assert captured["check"] is True


def test_run_in_project_venv_passes_check(tmp_path, monkeypatch):
    from easy_fastapi_cli.venv_bridge import run_in_project_venv

    captured = {}

    def fake_run(cmd, **kw):
        captured["check"] = kw.get("check", False)

    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.subprocess.run", fake_run)
    run_in_project_venv(tmp_path, ["echo"])
    assert captured["check"] is True


# ── run_in_project_venv 失败路径：友好错误 ──


def test_run_in_project_venv_failure_friendly_exit(tmp_path, monkeypatch):
    """子进程非零退出时：抛 typer.Exit(code=N)，stderr 含友好提示。"""
    import subprocess

    import typer
    from easy_fastapi_cli.venv_bridge import run_in_project_venv

    def fake_run(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.subprocess.run", fake_run)

    err_lines = []

    def fake_echo(msg, **kw):
        if kw.get("err"):
            err_lines.append(msg)

    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.typer.echo", fake_echo)

    with pytest.raises(typer.Exit) as exc_info:
        run_in_project_venv(tmp_path, ["failing-cmd"])
    assert exc_info.value.exit_code == 1
    assert any("退出码 1" in line for line in err_lines)


def test_run_in_project_venv_failure_preserves_exit_code(tmp_path, monkeypatch):
    """子进程退出码透传：退出码 42 → typer.Exit(code=42)。"""
    import subprocess

    import typer
    from easy_fastapi_cli.venv_bridge import run_in_project_venv

    def fake_run(cmd, **kw):
        raise subprocess.CalledProcessError(42, cmd)

    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.subprocess.run", fake_run)
    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.typer.echo", lambda *a, **kw: None)

    with pytest.raises(typer.Exit) as exc_info:
        run_in_project_venv(tmp_path, ["cmd"])
    assert exc_info.value.exit_code == 42


def test_run_in_project_venv_success_no_extra_output(tmp_path, monkeypatch):
    """子进程成功时：不调 typer.echo，不抛异常。"""
    from easy_fastapi_cli.venv_bridge import run_in_project_venv

    called_echo = False

    def fake_run(cmd, **kw):
        pass  # 成功

    def fake_echo(msg, **kw):
        nonlocal called_echo
        called_echo = True

    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.subprocess.run", fake_run)
    monkeypatch.setattr("easy_fastapi_cli.venv_bridge.typer.echo", fake_echo)

    run_in_project_venv(tmp_path, ["success-cmd"])
    assert not called_echo

"""Typer CLI 骨架 + 双别名入口测试（≥8 用例）。

只验证四命令占位存在且 --help 可用；db 子命令组（init/migrate/upgrade/sync）
与 gen --force 在后续任务实现，此处不测。
"""

from easy_fastapi_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


# ── 1. 顶层帮助列出四命令 ──


def test_app_help_lists_four_commands():
    """efa --help 列出 create/run/db/gen 四命令。"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.output
    for cmd in ("create", "run", "db", "gen"):
        assert cmd in out, f"命令 '{cmd}' 未出现在 --help 输出"


# ── 2. 无参数等同于 --help ──


def test_no_args_shows_help():
    """无参数时 no_args_is_help=True，Typer 返回 exit code 2 并显示帮助。"""
    result = runner.invoke(app, [])
    # Typer no_args_is_help 返回 exit_code 2，输出包含帮助文本
    assert result.exit_code == 0 or result.exit_code == 2
    assert "create" in result.output or "Usage" in result.output


# ── 3. 各子命令 --help 可运行 ──


def test_create_help():
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0


def test_run_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0


def test_db_help():
    result = runner.invoke(app, ["db", "--help"])
    assert result.exit_code == 0


def test_gen_help():
    result = runner.invoke(app, ["gen", "--help"])
    assert result.exit_code == 0


# ── 4. 未知命令报错 ──


def test_unknown_command_nonzero():
    """未知子命令应非零退出。"""
    result = runner.invoke(app, ["nonexistent"])
    assert result.exit_code != 0


# ── 5. app 属性 ──


def test_app_name_is_efa():
    """Typer app name 应为 'efa'。"""
    assert app.info.name == "efa"


# ── 6. 重复调用不报错 ──


def test_repeated_help_calls():
    """多次调用 --help 不会因为全局状态报错。"""
    for _ in range(3):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0


# ── 7. create 已为真实命令，db 已为子命令组，gen/run 仍为占位 ──


def test_create_requires_target():
    """create 已实现为真实命令，缺 target 参数应非零退出。"""
    result = runner.invoke(app, ["create"])
    assert result.exit_code != 0


def test_db_requires_subcommand():
    """db 已为子命令组，缺子命令应非零退出并显示帮助。"""
    result = runner.invoke(app, ["db"])
    assert result.exit_code != 0


def test_db_help_lists_subcommands():
    """db --help 应列出 init/migrate/upgrade/sync。"""
    result = runner.invoke(app, ["db", "--help"])
    assert result.exit_code == 0
    for sub in ("init", "migrate", "upgrade", "sync"):
        assert sub in result.output


def test_gen_no_marker_raises():
    """gen 已实现为真实命令，无 marker 应非零退出。"""
    result = runner.invoke(app, ["gen"])
    assert result.exit_code != 0


def test_run_no_marker_raises():
    """run 已实现为真实命令，无 marker 应非零退出。"""
    result = runner.invoke(app, ["run"])
    assert result.exit_code != 0

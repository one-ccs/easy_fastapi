"""i18n CLI 插件注册测试。"""

import pytest
import typer
from easy_fastapi.ext.i18n.cli import _project_dir, cli_plugin
from easy_fastapi_cli.plugin_protocol import CLIPlugin


def test_cli_plugin_satisfies_protocol():
    """I18nCLIPlugin 满足 CLIPlugin 协议。"""
    assert isinstance(cli_plugin, CLIPlugin)
    assert cli_plugin.name == "i18n"


def test_cli_plugin_registers_without_error():
    """register() 不抛异常。"""
    app = typer.Typer()
    cli_plugin.register(app, rich_help_panel="Extensions")


def test_project_dir_backend_only(tmp_path, monkeypatch):
    """backend-only 项目：_project_dir() 返回 cwd 本身。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "easy_fastapi.project.read_marker",
        lambda d: {"project_layout": "backend-only"},
    )
    result = _project_dir()
    assert result == tmp_path


def test_project_dir_fullstack(tmp_path, monkeypatch):
    """fullstack 项目：_project_dir() 返回 cwd/backend。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "easy_fastapi.project.read_marker",
        lambda d: {"project_layout": "fullstack"},
    )
    result = _project_dir()
    assert result == tmp_path / "backend"


def test_project_dir_missing_marker(tmp_path, monkeypatch):
    """_project_dir() 在非项目目录（marker 缺失）时抛 ConfigError。"""
    from easy_fastapi.core.exceptions import ConfigError

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "easy_fastapi.project.read_marker",
        lambda d: (_ for _ in ()).throw(ConfigError("missing")),
    )
    with pytest.raises(ConfigError):
        _project_dir()

# packages/easy_fastapi_cli/src/easy_fastapi_cli/plugin_loader.py
"""CLI 插件发现与注册。

两条发现路径：
1. 内置扩展：约定扫描 easy_fastapi.ext.{name}.cli 模块
2. 外部插件：entry_points group="easy_fastapi.cli_plugins"

统一注册到 Typer app，单个插件失败不阻塞其他插件。

venv 限制：
entry_points() 扫描的是 CLI 进程所在环境，扫不到项目 venv 里的插件。
本函数在 CLI 包导入时（main.py 模块级）执行，此时仍在 CLI venv，尚未经
venv_bridge re-exec 到项目 venv。外部插件须装在 CLI 环境：
  - pipx: pipx inject easy-fastapi-cli <plugin>
  - 或 uv add --dev easy-fastapi-cli 装进项目 venv（CLI 与插件同环境）
内置扩展不受影响（easy_fastapi 是 CLI 依赖，必在 CLI venv）。
不做跨 venv 扫描——详见 docs/DECISIONS.md ADR #36。
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typer

from .plugin_protocol import CLIPlugin

logger = logging.getLogger(__name__)


def load_plugins(app: typer.Typer) -> list[CLIPlugin]:
    """发现并注册所有 CLI 插件。

    返回成功注册的插件列表。
    """
    plugins: list[CLIPlugin] = []
    plugins.extend(_discover_builtin_plugins())
    plugins.extend(_discover_entrypoint_plugins())

    seen: dict[str, CLIPlugin] = {}
    for plugin in plugins:
        if plugin.name in seen:
            logger.warning("CLI 插件 '%s' 重复，跳过后者", plugin.name)
            continue
        try:
            plugin.register(app, rich_help_panel="Extensions")
            seen[plugin.name] = plugin
        except Exception:
            logger.warning("CLI 插件 '%s' 注册失败", plugin.name, exc_info=True)

    return list(seen.values())


def _discover_builtin_plugins() -> list[CLIPlugin]:
    """约定扫描：easy_fastapi.ext.{name}.cli 模块若存在且有 cli_plugin 对象则加载。"""
    try:
        from easy_fastapi.ext import __path__ as ext_paths  # type: ignore[import-untyped]
    except ImportError:
        return []

    plugins: list[CLIPlugin] = []
    for _importer, modname, ispkg in pkgutil.iter_modules(ext_paths):
        if not ispkg:
            continue
        try:
            cli_mod = importlib.import_module(f"easy_fastapi.ext.{modname}.cli")
        except ImportError:
            continue
        plugin = getattr(cli_mod, "cli_plugin", None)
        if plugin is not None and isinstance(plugin, CLIPlugin):
            plugins.append(plugin)
    return plugins


def _discover_entrypoint_plugins() -> list[CLIPlugin]:
    """外部插件通过 entry_points 注册。"""
    plugins: list[CLIPlugin] = []
    try:
        eps = entry_points(group="easy_fastapi.cli_plugins")
    except Exception:
        return []

    for ep in eps:
        try:
            plugin = ep.load()
            if isinstance(plugin, CLIPlugin):
                plugins.append(plugin)
        except Exception:
            logger.warning("外部 CLI 插件 '%s' 加载失败", ep.name, exc_info=True)
    return plugins

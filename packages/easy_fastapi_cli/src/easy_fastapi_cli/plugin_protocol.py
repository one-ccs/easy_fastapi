# packages/easy_fastapi_cli/src/easy_fastapi_cli/plugin_protocol.py
"""CLI 插件协议。

极简协议：只需要 name 属性和 register(app) 方法。
借鉴 Flask 的设计——不要求继承基类，鸭子类型即可。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import typer


@runtime_checkable
class CLIPlugin(Protocol):
    """CLI 插件协议。

    name: 唯一标识，用于冲突检测和错误提示。
    register: 将插件命令注册到 typer app。
    """

    name: str

    def register(self, app: typer.Typer, *, rich_help_panel: str | None = None) -> None:
        """将插件的命令注册到主 Typer 应用。"""
        ...

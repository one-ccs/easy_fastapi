"""i18n CLI 插件（typer 命令绑定）。

typer 仅在 register() 内延迟导入，Core 的 pyproject.toml 不声明 typer 依赖。
此模块只在被 CLI 包的 plugin_loader import 时才执行。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class I18nCLIPlugin:
    """i18n 扩展的 CLI 命令插件。"""

    name = "i18n"

    def register(self, app, *, rich_help_panel: str | None = None) -> None:
        """注册 i18n 子命令组到主 Typer 应用。"""
        import typer

        i18n_app = typer.Typer(help="国际化管理", no_args_is_help=True)

        @i18n_app.command()
        def init(
            lang: str = typer.Argument(..., help="语言代码，如 zh_CN"),
        ):
            """初始化翻译目录和 .po 文件。"""
            from .cli_commands import do_init

            do_init(lang, project_dir=_project_dir())

        @i18n_app.command("compile")
        def compile_cmd():
            """编译 .po → .mo（纯 Python，不依赖系统 msgfmt）。"""
            from .cli_commands import do_compile

            do_compile(project_dir=_project_dir())

        @i18n_app.command()
        def update():
            """扫描源码 _() 调用，更新 .po 文件。"""
            from .cli_commands import do_update

            do_update(project_dir=_project_dir())

        app.add_typer(i18n_app, name="i18n", rich_help_panel=rich_help_panel)


def _project_dir():
    """获取后端工作目录并验证 marker 文件存在。

    fullstack 项目：locales/ 等在 backend/ 子目录下，返回 cwd/backend。
    backend-only 项目：返回 cwd 本身。

    复用 project.resolve_app_dir 统一推导规则。
    """
    from pathlib import Path

    from easy_fastapi.project import read_marker, resolve_app_dir

    cwd = Path.cwd()
    marker = read_marker(cwd)  # 缺失/损坏会抛 ConfigError
    return resolve_app_dir(cwd, marker)


# 约定导出对象：plugin_loader 通过 getattr(cli_mod, "cli_plugin") 发现
cli_plugin = I18nCLIPlugin()

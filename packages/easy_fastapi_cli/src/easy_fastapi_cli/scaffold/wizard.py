"""交互向导（questionary+rich）。

按顺序收集选项，返回 CreateOptions。模块级 questionary 引用便于测试 monkeypatch。
"""

import re

import questionary
from rich.console import Console
from rich.table import Table

from .options import CreateOptions

_console = Console()


def _slug(name: str | None) -> str:
    """project_name → 合法 Python package_name（小写+下划线，首字符必须为字母）。"""
    if not name:
        return "app"
    s = re.sub(r"[^a-zA-Z0-9]", "_", name.strip()).lower()
    s = re.sub(r"_+", "_", s.strip("_"))  # 压缩连续下划线
    if not s or not s[0].isalpha():
        return "app"  # 数字开头或纯符号 → fallback
    return s


def run_wizard(*, default_project_name: str | None = None) -> CreateOptions:
    """交互式收集所有选项，返回 CreateOptions。"""
    project_name = questionary.text("项目名称：", default=default_project_name or "").ask()
    resolved_name = project_name or default_project_name or "app"
    package_name_default = _slug(resolved_name)
    package_name = questionary.text("包名：", default=package_name_default).ask() or package_name_default
    language = questionary.select("语言：", choices=["zh", "en"], default="zh").ask()

    frontend = questionary.confirm("启用前端骨架（api-sdk monorepo）？", default=False).ask()

    database = questionary.confirm("启用数据库？", default=False).ask()
    orm = None
    dialect = None
    migration = False
    auth = False
    if database:
        orm = questionary.select("ORM：", choices=["tortoise", "sqlalchemy", "sqlmodel"], default="tortoise").ask()
        dialect = questionary.select("数据库类型：", choices=["mysql", "postgres", "sqlite"], default="sqlite").ask()
        migration = questionary.confirm("启用迁移？", default=True).ask()
        auth = questionary.confirm("启用认证？", default=False).ask()

    redis = questionary.confirm("启用 Redis？", default=False).ask()
    static = questionary.confirm("启用静态文件托管？", default=False).ask()
    i18n = questionary.confirm("启用国际化（i18n）？", default=False).ask()

    return CreateOptions(
        project_name=resolved_name,
        package_name=package_name,
        language=language,
        frontend=frontend,
        database=database,
        orm=orm,
        db_dialect=dialect,
        migration=migration,
        auth=auth,
        redis=redis,
        static=static,
        i18n=i18n,
    )


def _render_summary(options: CreateOptions) -> None:
    """用 rich 打印选项摘要表。"""
    table = Table(title="项目选项确认", show_header=True)
    table.add_column("项")
    table.add_column("值")
    rows = [
        ("project_name", options.project_name),
        ("package_name", options.package_name),
        ("language", options.language),
        ("layout", "fullstack" if options.frontend else "backend-only"),
        ("frontend", options.frontend),
        ("database", options.database),
        ("orm", options.orm),
        ("db_dialect", options.db_dialect),
        ("migration", options.migration),
        ("auth", options.auth),
        ("redis", options.redis),
        ("static", options.static),
        ("i18n", options.i18n),
    ]
    for k, v in rows:
        table.add_row(str(k), str(v))
    _console.print(table)


def confirm_options(options: CreateOptions) -> bool:
    """rich 打印摘要 + 二次确认。返回是否确认。"""
    _render_summary(options)
    return bool(questionary.confirm("以上选项正确？", default=True).ask())


def options_from_args(*, project_name: str, package_name: str | None = None, **kwargs) -> CreateOptions:
    """非交互模式：从 CLI 参数直构 CreateOptions。"""
    return CreateOptions(
        project_name=project_name,
        package_name=package_name or _slug(project_name),
        **kwargs,
    )

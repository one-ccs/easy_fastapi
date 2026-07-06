"""efa db 命令（CLI 薄壳：转发到项目 venv 的 _runner）。

不进程内调 db_ops（工具 venv 无项目运行时依赖），改经 venv_bridge 转发：
  uv run --no-sync --directory <root> python -m easy_fastapi._runner db <action>
CLI 侧只做轻量 marker 校验（database/orm 存在），不预解析派生状态。
"""

import typer

from easy_fastapi_cli._guard import require_project
from easy_fastapi_cli.venv_bridge import build_db_command, run_in_project_venv


def _check_db_enabled(marker: dict) -> None:
    """轻量校验：marker 启用了 database + orm。否则报错退出。"""
    opts = marker.get("options", {})
    if not opts.get("database") or not opts.get("orm"):
        raise typer.BadParameter("当前项目未启用数据库/ORM（marker 中 database/orm 缺失）")


def do_db(action: str) -> None:
    """执行 db 子命令：读 marker → 轻量校验 → 转发 _runner。"""
    marker = require_project()
    _check_db_enabled(marker)
    from pathlib import Path

    cwd = Path.cwd()
    cmd = build_db_command(action=action)
    run_in_project_venv(cwd, cmd)

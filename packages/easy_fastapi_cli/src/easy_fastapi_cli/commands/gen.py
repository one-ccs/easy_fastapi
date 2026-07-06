"""efa gen 命令（CLI 薄壳：转发到项目 venv 的 _runner）。

不进程内调 introspector/codegen（工具 venv 无项目运行时依赖），改经 venv_bridge 转发：
  uv run --no-sync --directory <root> python -m easy_fastapi._runner gen [--force]
CLI 侧只做轻量 marker 校验（orm 存在），不预解析派生状态。
"""

from pathlib import Path

import typer

from easy_fastapi_cli._guard import require_project
from easy_fastapi_cli.venv_bridge import build_gen_command, run_in_project_venv


def do_gen(force: bool = False) -> None:
    """读 marker → 轻量校验 orm → 转发 _runner gen。"""
    marker = require_project()
    orm = marker.get("options", {}).get("orm")
    if not orm:
        raise typer.BadParameter("当前项目未启用 ORM，无法生成模型代码")
    cwd = Path.cwd()
    cmd = build_gen_command(force=force)
    run_in_project_venv(cwd, cmd)

"""efa run 命令（CLI 薄壳：转发到项目 venv 的 uvicorn）。

不进程内调 uvicorn（工具 venv 无项目运行时依赖），改经 venv_bridge 转发：
  uv run --no-sync --directory <root> uvicorn <app_target> [--app-dir <app_dir>] --host --port [--reload]
"""

import os
from pathlib import Path

import typer

from easy_fastapi_cli._guard import require_project
from easy_fastapi_cli.scaffold.marker import MARKER_FILENAME
from easy_fastapi_cli.venv_bridge import build_run_command, run_in_project_venv


def do_run(host: str, port: int, reload: bool) -> None:
    """校验项目目录 → 读 marker → 转发 uvicorn 到项目 venv。"""
    cwd = Path.cwd()
    if not (cwd / MARKER_FILENAME).exists():
        typer.echo(f"当前目录不是 Easy FastAPI 项目（缺少 {MARKER_FILENAME}）。请在项目根目录运行 efa run。")
        raise typer.Exit(code=1)
    require_project()  # 顺带校验 marker 完整性
    # 传递服务器地址给应用（供启动日志构造完整 URL）
    os.environ["EFA_SERVER_HOST"] = host
    os.environ["EFA_SERVER_PORT"] = str(port)
    cmd = build_run_command(cwd, host=host, port=port, reload=reload)
    run_in_project_venv(cwd, cmd)

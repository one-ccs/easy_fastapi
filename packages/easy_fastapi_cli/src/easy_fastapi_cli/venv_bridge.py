"""CLI venv-bridge 转发层：将项目命令 re-exec 到项目 venv。

所有项目命令（run/db/gen）一律经 uv run --no-sync --directory <root> 转发，
在项目 venv 内执行。CLI 侧不做 in-process 执行，无防递归环境变量。
efa create 不经此转发。

设计约定：build_* 返回项目 venv 内部命令（不含 uv run 前缀），
run_in_project_venv 负责加 uv run --no-sync --directory <root> 前缀。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from easy_fastapi.project import app_target_from_dir


def run_in_project_venv(project_dir: Path, cmd: list[str]) -> None:
    """在项目 venv 内执行命令：uv run --no-sync --directory <root> <cmd>。

    子进程非零退出时向 stderr 打印友好提示并以该退出码退出，
    不让 CalledProcessError traceback 泄漏到终端。
    """
    full_cmd = ["uv", "run", "--no-sync", "--directory", str(project_dir)] + cmd
    try:
        subprocess.run(full_cmd, check=True, cwd=project_dir)
    except FileNotFoundError:
        typer.echo(
            "未找到 'uv' 命令，请先安装 uv（https://docs.astral.sh/uv/）并确保其在 PATH 中。",
            err=True,
        )
        raise typer.Exit(code=127) from None
    except subprocess.CalledProcessError as e:
        typer.echo(f"项目命令执行失败（退出码 {e.returncode}）。详见上方输出。", err=True)
        raise typer.Exit(code=e.returncode) from None


def build_run_command(project_dir: Path, *, host: str, port: int, reload: bool) -> list[str]:
    """构建 uvicorn 命令（项目 venv 内部分）。

    uvicorn <app_target> [--app-dir <app_dir>] --host <host> --port <port> [--reload]
    """
    app_str, app_dir = app_target_from_dir(project_dir)
    cmd = ["uvicorn", app_str]
    if app_dir:
        cmd.extend(["--app-dir", app_dir])
    cmd.extend(["--host", host, "--port", str(port)])
    if reload:
        cmd.append("--reload")
    return cmd


def build_db_command(action: str) -> list[str]:
    """构建 db 命令（项目 venv 内部分）。

    python -m easy_fastapi._runner db <action>
    """
    return ["python", "-m", "easy_fastapi._runner", "db", action]


def build_gen_command(*, force: bool) -> list[str]:
    """构建 gen 命令（项目 venv 内部分）。

    python -m easy_fastapi._runner gen [--force]
    """
    cmd = ["python", "-m", "easy_fastapi._runner", "gen"]
    if force:
        cmd.append("--force")
    return cmd

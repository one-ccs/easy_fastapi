"""最小 argv 分发器（argparse）。

目标：python -m easy_fastapi._runner db sync / gen --force
只做 argv→函数映射，不承载业务逻辑。
永远在项目 venv 内运行（由 CLI re-exec 进入），in-process 分发到 Core 命令，不二次 re-exec。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="easy_fastapi._runner", description="Easy FastAPI 项目命令分发")
    sub = parser.add_subparsers(dest="command", required=True)

    # db 子命令
    db_parser = sub.add_parser("db", help="数据库操作")
    db_parser.add_argument("action", choices=["init", "migrate", "upgrade", "sync"], help="操作类型")

    # gen 子命令
    gen_parser = sub.add_parser("gen", help="代码生成")
    gen_parser.add_argument("--force", action="store_true", help="覆盖已存在文件")

    args = parser.parse_args(argv)
    project_dir = Path.cwd()

    # fullstack 项目：app 包在 backend/ 下，需加入 sys.path 以便 import app.*
    # 复用 project.app_target_from_dir，避免 fullstack 路径推导在多处重复。
    from easy_fastapi.project import app_target_from_dir

    try:
        _, app_dir = app_target_from_dir(project_dir)
    except Exception:
        app_dir = None

    if app_dir:
        backend_dir = str(project_dir / app_dir)
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

    if args.command == "db":
        from easy_fastapi.commands.db import run_db_init, run_db_migrate, run_db_sync, run_db_upgrade

        ops = {
            "init": run_db_init,
            "migrate": run_db_migrate,
            "upgrade": run_db_upgrade,
            "sync": run_db_sync,
        }
        asyncio.run(ops[args.action](project_dir))

    elif args.command == "gen":
        from easy_fastapi.commands.gen import run_gen

        run_gen(project_dir, force=args.force)


if __name__ == "__main__":
    main()

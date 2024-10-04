#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        title='可选命令',
        dest='cmd',
    )

    # fastapi
    run_parser = subparsers.add_parser('run', help='FastAPI 相关命令')
    run_parser.add_argument('app', nargs='?', default='app.main:app', help='应用, 默认为 "app.main:app"')
    run_parser.add_argument('-H', '--host', type=str, default='0.0.0.0', help='主机, 默认为 "0.0.0.0"')
    run_parser.add_argument('-p', '--port', type=int, default=8000, help='端口, 默认为 8000')
    run_parser.add_argument('-r', '--reload', action='store_true', help='是否自动重启服务器, 默认为 False')
    run_parser.add_argument('--log-config', type=str, default='uvicorn_log_config.json', help='日志配置, 默认为 "uvicorn_log_config.json"')
    run_parser.add_argument('--log-level', type=str, default='warning', help='日志级别, 默认为 "warning"')

    # database
    db_parser = subparsers.add_parser('db', help='数据库相关命令')
    db_subparsers = db_parser.add_subparsers(
        title='可选命令',
        dest='db_cmd',
    )
    db_init_parser = db_subparsers.add_parser('init', help='初始化 Aerich 配置')
    db_init_parser.add_argument('-t', default='core.TORTOISE_ORM', help='Tortoise 配置路径, 默认为 "core.TORTOISE_ORM"')

    db_subparsers.add_parser('init-db', help='初始化数据库')
    db_subparsers.add_parser('init-table', help='初始化表')

    args = parser.parse_args()

    if args.cmd == 'run':
        import uvicorn

        if args.reload:
            args.log_config = None
            args.log_level = 'info'

        uvicorn.run(
            args.app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_config=args.log_config,
            log_level=args.log_level,
        )
    elif args.cmd == 'db':
        import os

        if args.db_cmd == 'init':
            with os.popen(f'cd app && aerich init -t {args.t}') as f:
                print(f.read())
        elif args.db_cmd == 'init-db':
            with os.popen('cd app && aerich init-db') as f:
                print(f.read())
        elif args.db_cmd == 'init-table':
            from tortoise import run_async
            from app.core import generate_schemas

            run_async(generate_schemas())
    else:
        parser.print_help()

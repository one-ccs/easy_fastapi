#!/usr/bin/env python
# -*- coding: utf-8 -*-


def execute_from_command_line():
    import os, argparse, uvicorn

    from easy_fastapi import __version__
    from easy_fastapi import logger

    parser = argparse.ArgumentParser(prog='easy_fastapi', description='Easy FastAPI 脚手架管理工具', add_help=False)

    parser.add_argument('-h', '--help', action='help', help='显示帮助信息并退出')
    parser.add_argument('-v', '--version', help='显示版本信息并退出', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--path', help='工作路径', default='.')
    parser.add_argument('--lv', help='日志级别', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    subparsers = parser.add_subparsers(
        title='可选命令',
        dest='cmd',
    )

    # fastapi
    run_parser = subparsers.add_parser('run', help='FastAPI 相关命令')
    run_parser.add_argument('app', nargs='?', default='app.main:app', help='应用, 默认为 "app.main:app"')
    run_parser.add_argument('--host', type=str, default='127.0.0.1', help='主机, 默认为 "127.0.0.1"')
    run_parser.add_argument('--port', type=int, default=8000, help='端口, 默认为 8000')
    run_parser.add_argument('--reload', action='store_true', help='是否自动重启服务器, 默认为 False')
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

    # generator
    gen_parser = subparsers.add_parser('gen', help='代码生成器')
    gen_parser.add_argument('-pk', dest='_pk', default='id', help='主键字段名, 默认为 "id"')
    gen_parser.add_argument('-im', dest='_im', nargs='?', default='user,role', help='要忽略的模型列表, 用逗号分隔, 默认为 "user,role"')

    args = parser.parse_args()

    logger.setLevel(args.lv)
    logger.debug(f'工作路径: {os.path.abspath(args.path)}')

    os.chdir(args.path)

    match args.cmd:
        case 'run':
            if args.reload:
                from uvicorn.config import LOGGING_CONFIG
                args.log_config = LOGGING_CONFIG
                args.log_level = None

            uvicorn.run(
                args.app,
                host=args.host,
                port=args.port,
                reload=args.reload,
                log_config=args.log_config,
                log_level=args.log_level,
            )
        case 'db':
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
        case 'gen':
            from app import models
            from app.core import Generator

            Generator(
                models_path=models.__path__,
                pk_name=args._pk,
                models_ignore=set(args._im.replace(' ', '').split(',')) if args._im else {},
            ).build()
        case _:
            parser.print_help()

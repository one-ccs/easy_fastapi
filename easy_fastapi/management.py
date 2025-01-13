#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import shutil
import uvicorn
from uvicorn.config import LOGGING_CONFIG
from pathlib import Path
from os import popen

from easy_pyoc import AnsiColor, PathUtil, PackageUtil

from .logger import logger


TEMPLATES_DIR = Path(__file__).parent / 'templates'


def execute_from_command_line():
    parser = argparse.ArgumentParser(prog='easy_fastapi', description='Easy FastAPI 脚手架管理工具', add_help=False)

    parser.add_argument('-h', '--help', action='help', help='显示帮助信息并退出')
    parser.add_argument('-v', '--version', help='显示版本信息并退出', action='version', version=f'%(prog)s {PackageUtil.get_version("easy_fastapi")}')
    parser.add_argument('--path', help='工作目录, 默认 "."', default='.')
    parser.add_argument('--lv', help='日志级别', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])

    subparsers = parser.add_subparsers(
        title='可选命令',
        dest='cmd',
    )

    subparsers.add_parser('init', help='初始化项目')

    # fastapi
    run_parser = subparsers.add_parser('run', help='FastAPI 相关命令')
    run_parser.add_argument('app', nargs='?', default='app.main:app', help='应用, 默认为 "app.main:app"')
    run_parser.add_argument('--host', type=str, default='127.0.0.1', help='主机, 默认为 "127.0.0.1"')
    run_parser.add_argument('--port', type=int, default=8000, help='端口, 默认为 8000')
    run_parser.add_argument('--reload', action='store_true', help='是否自动重启服务器, 默认为 False')
    run_parser.add_argument('--log-config', type=str, default='log_config.json', help='日志配置, 默认为 "log_config.json"')
    run_parser.add_argument('--log-level', type=str, default='warning', help='日志级别, 默认为 "warning"')

    # database
    db_parser = subparsers.add_parser('db', help='数据库相关命令')
    db_subparsers = db_parser.add_subparsers(
        title='可选命令',
        dest='db_cmd',
    )
    db_init_parser = db_subparsers.add_parser('init', help='初始化 Aerich 配置')
    db_init_parser.add_argument('-t', default='easy_fastapi.TORTOISE_ORM', help='Tortoise 配置路径, 默认为 "easy_fastapi.TORTOISE_ORM"')

    db_subparsers.add_parser('init-db', help='初始化数据库')
    db_subparsers.add_parser('init-table', help='初始化表')

    # generator
    gen_parser = subparsers.add_parser('gen', help='代码生成器')
    gen_parser.add_argument('-pk', dest='_pk', default='id', help='主键字段名, 默认为 "id"')
    gen_parser.add_argument('-im', dest='_im', nargs='?', default='user,role', help='要忽略的模型列表, 用逗号分隔, 默认为 "user,role"')

    args = parser.parse_args()

    work_dir = Path(args.path)

    logger.setLevel(args.lv)
    logger.debug(f'工作目录: {work_dir.absolute()}')

    # 添加包导入路径并设置工作路径
    PathUtil.sys_path.insert(0, str(work_dir.absolute()))
    PathUtil.set_work_dir(work_dir.absolute())

    match args.cmd:
        case 'init':
            init(work_dir, args)
        case 'run':
            run(work_dir, args)
        case 'db':
            db(work_dir, args)
        case 'gen':
            gen(work_dir, args)
        case _:
            parser.print_help()


def init(work_dir: Path, args: argparse.Namespace) -> None:
    project_name = input('请输入项目名称: ')
    project_path = work_dir / project_name

    if PathUtil.is_exists_dir(project_path):
        logger.error(f'目录 {project_path} 已存在, 请先删除后再尝试初始化')
        return

    shutil.copytree(TEMPLATES_DIR, project_path)
    project_path.joinpath('backend', 'logs').mkdir(parents=True, exist_ok=True)

    logger.info(
        '项目初始化完成，启动项目:'
        f'{AnsiColor(AnsiColor.FORE_GREEN, bold=True)}'
        f'\n    cd {project_path}/backend'
        '\n    easy_fastapi run --reload'
        f'{AnsiColor(AnsiColor.FORE_RESET, AnsiColor.BACK_RESET)}'
    )


def run(work_dir: Path, args: argparse.Namespace) -> None:
    if args.reload:
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


def db(work_dir: Path, args: argparse.Namespace) -> None:
    if args.db_cmd == 'init':
        with popen(f'aerich init -t {args.t}') as f:
            print(f.read())
    elif args.db_cmd == 'init-db':
        with popen('aerich init-db') as f:
            print(f.read())
    elif args.db_cmd == 'init-table':
        from tortoise import run_async
        from easy_fastapi import generate_schemas

        run_async(generate_schemas())


def gen(work_dir: Path, args: argparse.Namespace) -> None:
    from app import models # type: ignore
    from app.core import Generator # type: ignore

    Generator(
        models_path=models.__path__,
        pk_name=args._pk,
        models_ignore=set(args._im.replace(' ', '').split(',')) if args._im else {},
    ).build()

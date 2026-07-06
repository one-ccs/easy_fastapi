"""efa CLI 入口（Typer）。

双别名：efa / easy-fastapi（pyproject [project.scripts]）。
四命令全部真实：create / db / gen / run。
"""

import typer
from rich.console import Console
from rich.panel import Panel

from easy_fastapi_cli.commands.create import do_create
from easy_fastapi_cli.commands.db import do_db
from easy_fastapi_cli.commands.gen import do_gen
from easy_fastapi_cli.commands.run import do_run

app = typer.Typer(
    name="efa",
    help="Easy FastAPI 脚手架命令行工具",
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

_console = Console()


def _version_callback(value: bool) -> None:
    """--version：打印版本号后退出。"""
    if value:
        from easy_fastapi_cli import __version__

        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="显示版本号并退出",
    ),
) -> None:
    """Easy FastAPI 脚手架命令行工具。"""


@app.command()
def create(
    target: str = typer.Argument(..., help="目标目录（. 表示当前目录）"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="交互向导"),
    project_name: str | None = typer.Option(None, "--project-name", help="项目名称"),
    package_name: str | None = typer.Option(None, "--package-name", help="包名"),
    language: str = typer.Option("zh", "--language", help="语言（zh/en）"),
    frontend: bool = typer.Option(False, "--frontend/--no-frontend", help="启用前端"),
    static: bool = typer.Option(False, "--static/--no-static", help="启用静态文件托管"),
    database: bool = typer.Option(False, "--database/--no-database", help="启用数据库"),
    orm: str | None = typer.Option(None, "--orm", help="ORM（tortoise/sqlalchemy/sqlmodel）"),
    db_dialect: str | None = typer.Option(None, "--db-dialect", help="数据库类型（mysql/postgres/sqlite）"),
    migration: bool = typer.Option(False, "--migration/--no-migration", help="启用迁移"),
    auth: bool = typer.Option(False, "--auth/--no-auth", help="启用认证"),
    redis: bool = typer.Option(False, "--redis/--no-redis", help="启用 Redis"),
    i18n: bool = typer.Option(False, "--i18n/--no-i18n", help="启用国际化"),
):
    """创建新项目（交互向导或全参数）。"""
    project_dir, manifest = do_create(
        target,
        interactive=interactive,
        project_name=project_name,
        package_name=package_name,
        language=language,
        frontend=frontend,
        static=static,
        database=database,
        orm=orm,
        db_dialect=db_dialect,
        migration=migration,
        auth=auth,
        redis=redis,
        i18n=i18n,
    )
    typer.echo(f"已创建项目：{project_dir}")
    if manifest.post_messages:
        try:
            _console.print(Panel("\n".join(manifest.post_messages), title="下一步", border_style="green"))
        except UnicodeEncodeError:
            # Windows GBK 等终端无法编码 Rich 格式化输出时，回退到纯文本
            typer.echo("\n".join(manifest.post_messages))


@app.command()
def run(
    host: str = typer.Option("localhost", "--host", help="监听地址"),
    port: int = typer.Option(8000, "--port", help="监听端口"),
    reload: bool = typer.Option(False, "--reload/--no-reload", help="自动重载"),
):
    """运行项目（uvicorn）。"""
    do_run(host=host, port=port, reload=reload)


db_app = typer.Typer(help="数据库迁移与同步（init/migrate/upgrade/sync）", no_args_is_help=True)
app.add_typer(db_app, name="db")


@db_app.command()
def init():
    """初始化数据库（建表/生成迁移脚本）。"""
    do_db("init")
    typer.echo("db init 完成")


@db_app.command()
def migrate():
    """生成迁移脚本。"""
    do_db("migrate")
    typer.echo("db migrate 完成")


@db_app.command()
def upgrade():
    """应用迁移到最新版本。"""
    do_db("upgrade")
    typer.echo("db upgrade 完成")


@db_app.command()
def sync():
    """同步 schema 到数据库（tortoise→generate_schemas；sa/sqlmodel→alembic sync）。"""
    do_db("sync")
    typer.echo("db sync 完成")


@app.command()
def gen(force: bool = typer.Option(False, "--force", help="覆盖已存在文件")):
    """根据模型生成 CRUD 路由/schema/service。"""
    do_gen(force=force)


# 加载插件命令（内置扩展约定扫描 + 外部 entry_points）
from .plugin_loader import load_plugins  # noqa: E402

load_plugins(app)


if __name__ == "__main__":
    app()

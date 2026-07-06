"""alembic 迁移实现（SQLAlchemy/SQLModel）。

init / migrate / upgrade：走 alembic 命令封装。
sync：直接 metadata.create_all（跳过迁移文件，用于 ORM 修正/快速建表）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from easy_fastapi.core.extras import require
from easy_fastapi.ext.orm.base.db_config import OrmName

if TYPE_CHECKING:
    from sqlalchemy import MetaData

from .base import MigrationOp

# 模块级引用：真实来自 alembic 子模块；测试可用 monkeypatch 替换。
Config = require("alembic", "alembic.config").Config
command = require("alembic", "alembic.command")


async def run(
    app: Any,
    op: MigrationOp,
    *,
    orm: OrmName,
    db_url: str | None = None,
    models: list[str] | None = None,
):
    if op not in ("init", "migrate", "upgrade", "sync"):
        raise ValueError(f"alembic 不支持的操作 '{op}'（仅 init/migrate/upgrade/sync）")

    if op == "sync":
        return await _sync(orm, db_url, models)

    cfg = Config()
    cfg.set_main_option("script_location", "./alembic")
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)

    if op == "init":
        command.init(cfg, "alembic")
    elif op == "migrate":
        command.revision(cfg, autogenerate=True, message="auto")
    elif op == "upgrade":
        command.upgrade(cfg, "head")


async def _sync(orm: OrmName, db_url: str | None, models: list[str] | None):
    import importlib

    from sqlalchemy.ext.asyncio import create_async_engine

    url = db_url or "sqlite+aiosqlite:///./db.sqlite"
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            # 动态 import 项目模型模块，确保 table=True 的模型注册进 metadata
            imported = [importlib.import_module(mod_path) for mod_path in (models or [])]

            if orm == "sqlmodel":
                from sqlmodel import SQLModel

                await conn.run_sync(SQLModel.metadata.create_all)
            else:  # sqlalchemy：从项目模型模块里找 DeclarativeBase.metadata
                metadata = _extract_sqlalchemy_metadata(imported)
                if metadata is not None:
                    await conn.run_sync(metadata.create_all)
    finally:
        await engine.dispose()


def _extract_sqlalchemy_metadata(modules: list) -> MetaData | None:
    """从 import 进来的项目模块中提取 SQLAlchemy DeclarativeBase 的 metadata。

    项目模型继承自己的 Base（非框架 Base），扫描模块属性找 DeclarativeBase 子类，
    取其 .metadata。找到第一个即返回（一个项目通常只有一个 Base）。
    """
    from sqlalchemy.orm import DeclarativeBase

    for mod in modules:
        for attr in vars(mod).values():
            try:
                if isinstance(attr, type) and issubclass(attr, DeclarativeBase) and attr is not DeclarativeBase:
                    return attr.metadata
            except TypeError:
                continue
    return None

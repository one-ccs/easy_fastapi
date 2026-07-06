"""efa db 执行逻辑（init/migrate/upgrade/sync）——Core 侧。

从 marker 读 orm + 从 yaml 读真实 db 配置后，经 migration dispatch 执行。
sync 对 tortoise 走 generate_schemas（先 init_tortoise），对 sqlalchemy/sqlmodel 走 alembic._sync。
"""

from __future__ import annotations

from pathlib import Path

from easy_fastapi.ext.migration.base import dispatch_migration_op
from easy_fastapi.project import resolve_db_config


async def run_db_init(project_dir: Path) -> None:
    orm, db_url, models, _ = resolve_db_config(project_dir)
    await dispatch_migration_op(orm=orm, op="init", db_url=db_url, models=models)


async def run_db_migrate(project_dir: Path) -> None:
    orm, db_url, models, _ = resolve_db_config(project_dir)
    await dispatch_migration_op(orm=orm, op="migrate", db_url=db_url, models=models)


async def run_db_upgrade(project_dir: Path) -> None:
    orm, db_url, models, _ = resolve_db_config(project_dir)
    await dispatch_migration_op(orm=orm, op="upgrade", db_url=db_url, models=models)


async def run_db_sync(project_dir: Path) -> None:
    orm, db_url, models, _ = resolve_db_config(project_dir)
    if orm == "tortoise":
        # tortoise 无 alembic sync；先 init 再 generate_schemas
        from easy_fastapi.ext.orm.tortoise.session import generate_schemas, init_tortoise

        await init_tortoise(db_url=db_url, models=models)
        await generate_schemas()
    else:
        await dispatch_migration_op(orm=orm, op="sync", db_url=db_url, models=models)

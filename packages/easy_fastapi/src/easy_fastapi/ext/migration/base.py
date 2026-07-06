"""迁移分派：按已注册 ORM 路由到 aerich/alembic。

init/migrate/upgrade/sync 等 op 透传 db_url/models 给对应 impl。
"""

from __future__ import annotations

from typing import Any, Literal

from easy_fastapi.core.exceptions import ExtensionError
from easy_fastapi.ext.orm.base.db_config import OrmName

MigrationOp = Literal["init", "migrate", "upgrade", "sync"]


async def dispatch_migration_op(
    *,
    orm: OrmName | None,
    op: MigrationOp,
    app: Any = None,
    db_url: str | None = None,
    models: list[str] | None = None,
):
    """op ∈ {init, migrate, upgrade, sync}。返回 impl.run 的协程结果。

    - tortoise → aerich_impl.run
    - sqlalchemy / sqlmodel → alembic_impl.run（透传 orm 区分）
    - None / 空串 → ExtensionError（项目未启用 ORM）
    - 其它 → ExtensionError（不支持的 ORM）
    """
    if orm == "tortoise":
        from . import aerich_impl

        return await aerich_impl.run(app, op, db_url=db_url, models=models)
    if orm in ("sqlalchemy", "sqlmodel"):
        from . import alembic_impl

        return await alembic_impl.run(app, op, orm=orm, db_url=db_url, models=models)
    if not orm:
        raise ExtensionError("当前项目未启用任何 ORM 扩展，无法执行迁移操作")
    raise ExtensionError(f"不支持的 ORM '{orm}'，无对应迁移实现")

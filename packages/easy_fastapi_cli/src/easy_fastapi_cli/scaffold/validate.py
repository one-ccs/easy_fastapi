"""选项联动校验（铁律 B/C）。

B: database=True & orm=None → 报错；orm!=None & database=False → 报错
C: migration=True & orm=None → 报错；auth=True & database=False → 报错
"""

from easy_fastapi.core.exceptions import ConfigError

from .options import CreateOptions


def apply_defaults(options: CreateOptions) -> CreateOptions:
    """返回 options 的副本（不可变语义），补全隐含默认值。

    - db_dialect：启用 database+orm 但未指定方言时，默认 sqlite（与交互向导一致）。
    """
    updates: dict = {}
    if options.orm is not None and options.db_dialect is None:
        updates["db_dialect"] = "sqlite"
    return options.model_copy(update=updates) if updates else options.model_copy()


def validate(options: CreateOptions) -> CreateOptions:
    """铁律 B/C 校验。违例抛 ConfigError。"""
    o = options

    # 铁律 B：database ↔ orm 双向绑定
    if o.database and o.orm is None:
        raise ConfigError("database=True 时必须指定 orm（tortoise/sqlalchemy/sqlmodel）")
    if o.orm is not None and not o.database:
        raise ConfigError("指定了 orm 但 database=False；二者必须同进退")

    # 铁律 C：migration 依赖 orm
    if o.migration and o.orm is None:
        raise ConfigError("migration=True 时必须启用 database 并指定 orm")
    # 铁律 C：auth 依赖 database
    if o.auth and not o.database:
        raise ConfigError("auth=True 时必须启用 database")
    return o

"""共享数据库连接配置 + dialect→driver 映射 + 公共 URL 构造器。

build_uri 直接接受 DatabaseConfig（删除 ConnectionConfig 重复层）。
build_db_url(orm, loader) 公共 helper，供 ORM 扩展 + resolve_db_config 共用。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

if TYPE_CHECKING:
    from easy_fastapi.core.config.loader import ConfigLoader
    from easy_fastapi.core.config.models import DatabaseConfig

OrmName = Literal["tortoise", "sqlalchemy", "sqlmodel"]

Dialect = Literal["mysql", "postgres", "sqlite"]

_DRIVER_MAP = {
    "mysql": "asyncmy",
    "postgres": "asyncpg",
    "sqlite": "aiosqlite",
}


def dialect_to_driver(dialect: str) -> str:
    """v1 async 默认驱动映射。"""
    if dialect not in _DRIVER_MAP:
        raise ValueError(f"不支持的数据库 dialect：'{dialect}'（v1 仅支持 mysql/postgres/sqlite）")
    return _DRIVER_MAP[dialect]


def build_uri(orm: OrmName, db_cfg: DatabaseConfig) -> str:
    """按 orm + DatabaseConfig 拼接数据库 URL。

    - tortoise：朴素 scheme（mysql:// / postgres:// / sqlite://）。
    - sqlalchemy/sqlmodel：scheme+driver（mysql+asyncmy:// / postgresql+asyncpg:// / sqlite+aiosqlite://）。
    - sqlite：host/port/凭证忽略；database 为空时用 :memory:。
    - 非 sqlite：username/password/database 三者不可空，否则 ValueError。
    """
    dialect = db_cfg.dialect

    if dialect == "sqlite":
        db = db_cfg.database or ":memory:"
        if db != ":memory:":
            # 统一为 POSIX 路径（Windows 反斜杠 → 正斜杠），避免 URL 含非法字符
            db = Path(db).as_posix()
        if orm == "tortoise":
            return f"sqlite://{db}"
        return f"sqlite+aiosqlite:///{db}"

    if not db_cfg.username or not db_cfg.password or not db_cfg.database:
        raise ValueError("非 sqlite 数据库的 username/password/database 不能为空")
    auth = f"{quote(db_cfg.username, safe='')}:{quote(db_cfg.password, safe='')}"
    host = db_cfg.host
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    # port=None → 不拼端口，让驱动用 dialect 默认值；否则显式拼入
    host_port = f"{host}:{db_cfg.port}" if db_cfg.port is not None else host
    driver = dialect_to_driver(dialect)
    db_name = quote(db_cfg.database, safe="")
    if orm == "tortoise":
        return f"{dialect}://{auth}@{host_port}/{db_name}"
    scheme = "postgresql" if dialect == "postgres" else dialect
    return f"{scheme}+{driver}://{auth}@{host_port}/{db_name}"


def build_db_url(orm: OrmName, loader: ConfigLoader) -> str:
    """公共 helper：从 ConfigLoader 读 database 段，调用 build_uri。

    供 ORM 扩展 init_app + resolve_db_config 共用。
    """
    from easy_fastapi.core.config.models import DatabaseConfig

    db_cfg = loader.section("easy_fastapi.database", DatabaseConfig)
    return build_uri(orm, db_cfg)

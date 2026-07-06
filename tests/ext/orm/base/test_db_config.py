"""db_config 测试：dialect→driver 映射 + build_uri(DatabaseConfig) + build_db_url。

覆盖：dialect_to_driver 三映射、未知 dialect 报错、build_uri 各 ORM×dialect URL 构造、
sqlite 内存/相对/绝对路径分支、非 sqlite 凭证缺失报错、IPv6/特殊字符安全增强、
build_db_url 从 ConfigLoader 读 database 段。
"""

import pytest
from easy_fastapi.core.config.models import DatabaseConfig
from easy_fastapi.ext.orm.base.db_config import dialect_to_driver

# ---- dialect_to_driver ----


def test_dialect_to_driver_mysql():
    assert dialect_to_driver("mysql") == "asyncmy"


def test_dialect_to_driver_postgres():
    assert dialect_to_driver("postgres") == "asyncpg"


def test_dialect_to_driver_sqlite():
    assert dialect_to_driver("sqlite") == "aiosqlite"


def test_dialect_to_driver_unknown_raises_value_error():
    with pytest.raises(ValueError):
        dialect_to_driver("oracle")


def test_dialect_to_driver_unknown_message_contains_dialect():
    with pytest.raises(ValueError, match="oracle"):
        dialect_to_driver("oracle")


def test_dialect_to_driver_case_sensitive():
    # 大小写敏感，MySQL 不等于 mysql
    with pytest.raises(ValueError):
        dialect_to_driver("MySQL")


# ---- build_uri（ORM×dialect URL 构造器，接受 DatabaseConfig） ----


def test_build_uri_tortoise_mysql():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="root", password="123", database="db", host="h", port=3306)
    assert build_uri("tortoise", cfg) == "mysql://root:123@h:3306/db"


def test_build_uri_tortoise_postgres():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="postgres", username="u", password="p", database="db", host="h", port=5432)
    assert build_uri("tortoise", cfg) == "postgres://u:p@h:5432/db"


def test_build_uri_tortoise_sqlite():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    # 绝对路径 → 三斜杠，tortoise file_path=/tmp/test.db
    cfg = DatabaseConfig(dialect="sqlite", database="/tmp/test.db")
    assert build_uri("tortoise", cfg) == "sqlite:///tmp/test.db"


def test_build_uri_tortoise_sqlite_relative_path():
    """Tortoise SQLite 相对文件路径必须两斜杠（sqlite://mydb.sqlite3），否则被解析成绝对路径。"""
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="sqlite", database="mydb.sqlite3")
    assert build_uri("tortoise", cfg) == "sqlite://mydb.sqlite3"


def test_build_uri_tortoise_sqlite_memory_explicit():
    """Tortoise SQLite 内存数据库显式 :memory: 必须两斜杠（sqlite://:memory:）。"""
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="sqlite", database=":memory:")
    assert build_uri("tortoise", cfg) == "sqlite://:memory:"


def test_build_uri_sqlalchemy_mysql():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="u", password="p", database="db", host="h", port=3306)
    assert build_uri("sqlalchemy", cfg) == "mysql+asyncmy://u:p@h:3306/db"


def test_build_uri_sqlalchemy_postgres():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="postgres", username="u", password="p", database="db", host="h", port=5432)
    assert build_uri("sqlalchemy", cfg) == "postgresql+asyncpg://u:p@h:5432/db"


def test_build_uri_sqlmodel_mysql():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="u", password="p", database="db", host="h", port=3306)
    assert build_uri("sqlmodel", cfg) == "mysql+asyncmy://u:p@h:3306/db"


def test_build_uri_sqlalchemy_sqlite():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="sqlite", database="/tmp/test.db")
    assert build_uri("sqlalchemy", cfg) == "sqlite+aiosqlite:////tmp/test.db"


def test_build_uri_tortoise_sqlite_memory_default():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    # database 为空 → tortoise 用 :memory:（两斜杠）
    cfg = DatabaseConfig(dialect="sqlite", database="")
    assert build_uri("tortoise", cfg) == "sqlite://:memory:"


def test_build_uri_missing_username_raises():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="", password="p", database="db")
    with pytest.raises(ValueError):
        build_uri("tortoise", cfg)


def test_build_uri_missing_password_raises():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="postgres", username="u", password="", database="db")
    with pytest.raises(ValueError):
        build_uri("sqlalchemy", cfg)


def test_build_uri_missing_database_raises():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="u", password="p", database="")
    with pytest.raises(ValueError):
        build_uri("sqlmodel", cfg)


# ---- build_uri 安全增强：IPv6 + URL 编码（C8，与 _build_db_url 对齐） ----


def test_build_uri_ipv6_host_bracketed():
    """IPv6 地址 host 必须用方括号包裹（[::1]）。"""
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="root", password="123", database="db", host="::1", port=3306)
    assert build_uri("tortoise", cfg) == "mysql://root:123@[::1]:3306/db"


def test_build_uri_ipv6_host_sqlalchemy_bracketed():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="u", password="p", database="db", host="::1", port=3306)
    assert build_uri("sqlalchemy", cfg) == "mysql+asyncmy://u:p@[::1]:3306/db"


def test_build_uri_special_chars_in_password_url_encoded():
    """密码含特殊字符（@, :）必须 URL 编码。"""
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="root", password="p@ss:word", database="db")
    uri = build_uri("tortoise", cfg)
    assert "p%40ss%3Aword" in uri
    assert "@" not in uri.split("://root:")[1].split("@")[0]  # 凭证段无裸 @


def test_build_uri_special_chars_in_username_url_encoded():
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="postgres", username="r@oot", password="123", database="db")
    uri = build_uri("sqlalchemy", cfg)
    assert "r%40oot" in uri


def test_build_uri_ipv4_host_not_bracketed():
    """IPv4 / 主机名不带方括号。"""
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="root", password="123", database="db", host="localhost", port=3306)
    assert build_uri("tortoise", cfg) == "mysql://root:123@localhost:3306/db"


def test_build_uri_password_no_special_chars_unchanged():
    """无特殊字符的密码保持原样。"""
    from easy_fastapi.ext.orm.base.db_config import build_uri

    cfg = DatabaseConfig(dialect="mysql", username="root", password="plain123", database="db")
    uri = build_uri("tortoise", cfg)
    assert "plain123" in uri


# ---- build_db_url 公共 helper ----


def test_build_db_url_sqlite_sqlmodel():
    from easy_fastapi.core.config.loader import ConfigLoader
    from easy_fastapi.ext.orm.base.db_config import build_db_url

    raw = {"easy_fastapi": {"database": {"dialect": "sqlite", "database": ":memory:"}}}
    loader = ConfigLoader(raw, path=None)
    assert build_db_url("sqlmodel", loader) == "sqlite+aiosqlite:///:memory:"


def test_build_db_url_mysql_tortoise():
    from easy_fastapi.core.config.loader import ConfigLoader
    from easy_fastapi.ext.orm.base.db_config import build_db_url

    raw = {"easy_fastapi": {"database": {"dialect": "mysql", "username": "root", "password": "123", "database": "db"}}}
    loader = ConfigLoader(raw, path=None)
    assert build_db_url("tortoise", loader) == "mysql://root:123@localhost:3306/db"

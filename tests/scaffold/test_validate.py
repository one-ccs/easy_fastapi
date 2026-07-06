"""铁律 B/C——database/orm/migration/auth 一致性测试。"""

import pytest
from easy_fastapi.core.exceptions import ConfigError
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.validate import apply_defaults, validate


def _mk(**kw):
    base = {"project_name": "p", "package_name": "p"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. apply_defaults 返回新实例（不可变语义）──


def test_apply_defaults_returns_new_instance():
    o = _mk(frontend=True)
    o2 = apply_defaults(o)
    assert o is not o2


# ── 2. apply_defaults 保持 frontend 字段不变 ──


def test_apply_defaults_preserves_frontend_flag():
    o = _mk(frontend=True)
    o = apply_defaults(o)
    assert o.frontend is True
    o = _mk(frontend=False)
    o = apply_defaults(o)
    assert o.frontend is False


# ════════════════════════════════════════════════════════════════════
# 铁律 B/C——database/orm/migration/auth 一致性（≥8 用例）
# ════════════════════════════════════════════════════════════════════


# ── B1: database=True 但 orm=None → 报错 ──


def test_validate_b_database_without_orm_raises():
    with pytest.raises(ConfigError):
        validate(_mk(database=True))  # orm=None


# ── B2: orm 设了但 database=False → 报错 ──


def test_validate_b_orm_without_database_raises():
    with pytest.raises(ConfigError):
        validate(_mk(database=False, orm="tortoise"))


# ── B3: database=True + orm + dialect → 通过 ──


def test_validate_b_database_with_orm_ok():
    o = validate(_mk(database=True, orm="tortoise", db_dialect="mysql"))
    assert o.orm == "tortoise"


# ── B4: 三种 ORM 各自合法 ──


def test_validate_b_all_orms_ok():
    for orm in ("tortoise", "sqlalchemy", "sqlmodel"):
        o = validate(_mk(database=True, orm=orm, db_dialect="mysql"))
        assert o.orm == orm


# ── C1: migration=True 但 orm=None → 报错 ──


def test_validate_c_migration_without_orm_raises():
    with pytest.raises(ConfigError):
        validate(_mk(migration=True))


# ── C2: migration=True + database + orm → 通过 ──


def test_validate_c_migration_with_orm_ok():
    o = validate(_mk(database=True, orm="tortoise", db_dialect="mysql", migration=True))
    assert o.migration is True


# ── C3: auth=True 但 database=False → 报错 ──


def test_validate_c_auth_without_database_raises():
    with pytest.raises(ConfigError):
        validate(_mk(auth=True))


# ── C4: auth=True + database + orm → 通过 ──


def test_validate_c_auth_with_database_ok():
    o = validate(_mk(database=True, orm="tortoise", db_dialect="mysql", auth=True))
    assert o.auth is True


# ── 纯后端最小集通过 ──


def test_validate_minimal_ok():
    o = validate(_mk())  # 全默认
    assert o.database is False
    assert o.orm is None


# ── 报错信息可读（含关键词）──


def test_validate_b_error_message_readable():
    with pytest.raises(ConfigError) as ei:
        validate(_mk(database=True))
    assert "orm" in str(ei.value)


def test_validate_c_auth_error_message_readable():
    with pytest.raises(ConfigError) as ei:
        validate(_mk(auth=True))
    assert "database" in str(ei.value)


# ── 组合违例：migration + auth 都缺 orm/database ──


def test_validate_multi_violation_raises():
    """migration=True & auth=True 但 database=False：至少触发一条铁律。"""
    with pytest.raises(ConfigError):
        validate(_mk(migration=True, auth=True))


# ── redis 不依赖 database（独立开关）──


def test_validate_redis_without_database_ok():
    o = validate(_mk(redis=True))
    assert o.redis is True

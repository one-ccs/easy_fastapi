"""CreateOptions 选项模型测试（≥8 用例）。"""

import pytest
from easy_fastapi_cli.scaffold.options import CreateOptions
from pydantic import ValidationError


def _mk(**kw):
    base = {"project_name": "p", "package_name": "p"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. 默认值 ──


def test_defaults():
    o = CreateOptions(project_name="myproj", package_name="myproj")
    assert o.in_place is False
    assert o.language == "zh"
    assert o.frontend is False
    assert o.static is False
    assert o.database is False
    assert o.orm is None
    assert o.db_dialect is None
    assert o.migration is False
    assert o.auth is False
    assert o.redis is False


# ── 2. 无 app_name 字段（已删除）──


def test_no_app_name_field():
    o = CreateOptions(project_name="p", package_name="p")
    assert not hasattr(o, "app_name")


# ── 3. language 受 Literal 约束 ──


def test_invalid_language_rejected():
    with pytest.raises(ValidationError):
        CreateOptions(project_name="p", package_name="p", language="jp")


def test_language_en_ok():
    assert _mk(language="en").language == "en"


# ── 6. orm / db_dialect 受 Literal 约束 ──


def test_invalid_orm_rejected():
    with pytest.raises(ValidationError):
        _mk(database=True, orm="peewee")


def test_invalid_dialect_rejected():
    with pytest.raises(ValidationError):
        _mk(database=True, orm="tortoise", db_dialect="oracle")


def test_all_three_orms_accepted():
    for orm in ("tortoise", "sqlalchemy", "sqlmodel"):
        assert _mk(database=True, orm=orm).orm == orm


def test_all_three_dialects_accepted():
    for d in ("mysql", "postgres", "sqlite"):
        assert _mk(database=True, orm="tortoise", db_dialect=d).db_dialect == d


# ── 7. extra='forbid' 拒绝未知字段 ──


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        CreateOptions(project_name="p", package_name="p", unknown_field="x")


def test_app_name_as_extra_rejected():
    """app_name 已删，传入应被 forbid 拒绝。"""
    with pytest.raises(ValidationError):
        CreateOptions(project_name="p", package_name="p", app_name="x")


# ── 8. 全字段合法构造 ──


def test_full_valid_options():
    o = CreateOptions(
        project_name="demo",
        package_name="demo",
        frontend=True,
        static=True,
        database=True,
        orm="tortoise",
        db_dialect="mysql",
        migration=True,
        auth=True,
        redis=True,
    )
    assert o.orm == "tortoise" and o.db_dialect == "mysql"


# ── 9. 必填字段缺失被拒 ──


def test_missing_project_name_rejected():
    with pytest.raises(ValidationError):
        CreateOptions(package_name="p")


def test_missing_package_name_rejected():
    with pytest.raises(ValidationError):
        CreateOptions(project_name="p")


# ── 10. in_place 字段 ──


def test_in_place_true():
    assert _mk(in_place=True).in_place is True

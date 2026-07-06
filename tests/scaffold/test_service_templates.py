"""scaffold service 模板使用 ExtendedCRUD 统一接口验证。

确认 user/role service 模板渲染后：
- 不含 Tortoise 原生 API（save/filter().delete/db.update_from_dict().save）
- 使用 ExtendedCRUD 统一接口（by_id/create/update_from_dict/delete_by_ids/paginate）
- 使用 exists/exists_by_email 业务方法做重复检查
"""

from pathlib import Path

from jinja2 import Environment, StrictUndefined

_TEMPLATES = Path("packages/easy_fastapi_cli/src/easy_fastapi_cli/templates")


def _render(template_rel: str, **ctx) -> str:
    env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)
    tmpl = env.from_string((_TEMPLATES / template_rel).read_text(encoding="utf-8"))
    return tmpl.render(**ctx)


# ── B8: user service ──


def test_user_service_no_tortoise_save():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "await db_user.save()" not in rendered
    assert "await role.save()" not in rendered


def test_user_service_no_instance_update_from_dict():
    """不使用实例方法 db_user.update_from_dict(...)（应改用类方法 models.User.update_from_dict）。"""
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "db_user.update_from_dict(" not in rendered


def test_user_service_no_filter_delete():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "models.User.filter(id__in=ids).delete()" not in rendered


def test_user_service_uses_by_id():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "models.User.by_id" in rendered


def test_user_service_uses_create():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "await models.User.create(" in rendered


def test_user_service_uses_update_from_dict():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "models.User.update_from_dict" in rendered


def test_user_service_uses_delete_by_ids():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "models.User.delete_by_ids" in rendered


def test_user_service_uses_paginate():
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "models.User.paginate" in rendered


def test_user_service_uses_exists_for_username():
    """register/add 通过 exists(username=...) 做用户名重复检查（而非 filter().exists()）。"""
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "await models.User.exists(username=" in rendered
    assert ".filter(username=" not in rendered


def test_user_service_uses_exists_by_email():
    """register/add 通过 exists_by_email 做邮箱重复检查。"""
    rendered = _render("backend/base/backend/app/services/user.py.j2")
    assert "await models.User.exists_by_email(" in rendered
    assert ".filter(email=" not in rendered


# ── B9: role service ──


def test_role_service_no_tortoise_save():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "await role.save()" not in rendered


def test_role_service_no_instance_update_from_dict():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "role.update_from_dict(" not in rendered


def test_role_service_no_filter_delete():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "models.Role.filter(id__in=ids).delete()" not in rendered


def test_role_service_uses_by_id():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "models.Role.by_id" in rendered


def test_role_service_uses_create():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "await models.Role.create(" in rendered


def test_role_service_uses_update_from_dict():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "models.Role.update_from_dict" in rendered


def test_role_service_uses_delete_by_ids():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "models.Role.delete_by_ids" in rendered


def test_role_service_uses_paginate():
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "models.Role.paginate" in rendered


def test_role_service_uses_exists_for_role():
    """add 通过 exists(role=...) 做 role 重复检查（而非 filter().exists()）。"""
    rendered = _render("backend/base/backend/app/services/role.py.j2")
    assert "await models.Role.exists(role=" in rendered
    assert ".filter(role=" not in rendered

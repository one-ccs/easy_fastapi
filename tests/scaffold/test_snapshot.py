"""快照测试：锁定当前模板生成输出，供模板重组后回归比对。

每个组合生成项目到 tmp_path，记录文件树（相对路径列表）。
重组后若生成结果不变，测试继续 PASS；若有意变更，更新快照。
"""

from importlib.resources import files
from pathlib import Path

import pytest
from easy_fastapi_cli.scaffold.conflict import check_target
from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.marker import write_marker
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.validate import apply_defaults, validate
from easy_fastapi_cli.scaffold.write import write_manifest


def _generate(tmp_path, name, **kwargs):
    """生成项目并返回 (project_dir, 文件树列表)。"""
    o = apply_defaults(CreateOptions(project_name=name, package_name=name, **kwargs))
    o = validate(o)
    project_dir = tmp_path / name
    check_target(project_dir, in_place=False)
    project_dir.mkdir(parents=True)
    templates_root = Path(str(files("easy_fastapi_cli") / "templates"))
    manifest = build_manifest(o, templates_root=templates_root)
    write_manifest(manifest, o, project_dir, templates_root)
    write_marker(project_dir, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    tree = sorted(p.relative_to(project_dir).as_posix() for p in project_dir.rglob("*") if p.is_file())
    return project_dir, tree


# 关键组合矩阵
COMBOS = [
    ("be_min", {}),
    ("be_orm_t", dict(database=True, orm="tortoise", db_dialect="sqlite")),
    ("be_orm_sa", dict(database=True, orm="sqlalchemy", db_dialect="sqlite")),
    ("be_orm_sm", dict(database=True, orm="sqlmodel", db_dialect="sqlite")),
    ("be_auth_t", dict(database=True, orm="tortoise", db_dialect="sqlite", auth=True)),
    ("be_auth_sa", dict(database=True, orm="sqlalchemy", db_dialect="sqlite", auth=True)),
    ("be_auth_sm", dict(database=True, orm="sqlmodel", db_dialect="sqlite", auth=True)),
    ("be_static", dict(static=True)),
    ("be_redis", dict(redis=True)),
    ("be_mig_t", dict(database=True, orm="tortoise", db_dialect="sqlite", migration=True)),
    ("be_mig_sa", dict(database=True, orm="sqlalchemy", db_dialect="sqlite", migration=True)),
    ("fs_min", dict(frontend=True)),
    ("fs_auth_t", dict(frontend=True, database=True, orm="tortoise", db_dialect="sqlite", auth=True)),
]


@pytest.mark.parametrize("combo_name,kwargs", COMBOS, ids=[c[0] for c in COMBOS])
def test_snapshot_file_tree(tmp_path, combo_name, kwargs):
    """每个组合生成非空文件树。"""
    _, tree = _generate(tmp_path, combo_name, **kwargs)
    assert len(tree) > 0, f"{combo_name} 生成空项目"


@pytest.mark.parametrize("combo_name,kwargs", COMBOS, ids=[c[0] for c in COMBOS])
def test_snapshot_has_app_main(tmp_path, combo_name, kwargs):
    """每个组合都有 app/main.py。"""
    project_dir, tree = _generate(tmp_path, combo_name, **kwargs)
    # backend-only: app/main.py; fullstack: backend/app/main.py
    if kwargs.get("frontend"):
        assert "backend/app/main.py" in tree
    else:
        assert "app/main.py" in tree


def test_snapshot_auth_has_routers_and_handlers(tmp_path):
    """auth 组合含 routers + handlers。"""
    _, tree = _generate(tmp_path, "snap_auth", database=True, orm="tortoise", db_dialect="sqlite", auth=True)
    assert "app/routers/auth.py" in tree
    assert "app/handlers/auth_handler.py" in tree
    assert "app/schemas/user.py" in tree
    assert "app/services/user.py" in tree


def test_snapshot_no_auth_without_auth(tmp_path):
    """非 auth 组合不含 auth 文件。"""
    _, tree = _generate(tmp_path, "snap_noauth", database=True, orm="tortoise", db_dialect="sqlite")
    assert "app/routers/auth.py" not in tree
    assert "app/handlers/auth_handler.py" not in tree


def test_snapshot_migration_aerich(tmp_path):
    """tortoise + migration 含 pyproject.toml.aerich。"""
    _, tree = _generate(tmp_path, "snap_mig_t", database=True, orm="tortoise", db_dialect="sqlite", migration=True)
    assert "pyproject.toml.aerich" in tree


def test_snapshot_migration_alembic(tmp_path):
    """sqlalchemy + migration 含 alembic/。"""
    _, tree = _generate(tmp_path, "snap_mig_sa", database=True, orm="sqlalchemy", db_dialect="sqlite", migration=True)
    assert "alembic/env.py" in tree
    assert "alembic/script.py.mako" in tree


def test_snapshot_static_no_mount_py(tmp_path):
    """static 组合不含 static_mount.py（变更②后走扩展）。"""
    _, tree = _generate(tmp_path, "snap_static", static=True)
    assert "app/core/static_mount.py" not in tree


def test_snapshot_fullstack_backend_under_backend(tmp_path):
    """fullstack 后端文件在 backend/ 下。"""
    _, tree = _generate(tmp_path, "snap_fs", frontend=True, database=True, orm="tortoise", db_dialect="sqlite")
    assert "backend/app/main.py" in tree
    assert "backend/pyproject.toml" in tree
    # 根级 pyproject 是 workspace 的
    assert "pyproject.toml" in tree

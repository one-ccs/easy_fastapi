"""选项组合矩阵（12 组合）。

每组合：apply_defaults→validate→check_target→build_manifest→write_manifest→marker 全程不抛；
marker.registered_extensions 与预期一致。
"""

import json
from importlib.resources import files
from pathlib import Path

import pytest
from easy_fastapi_cli.scaffold.conflict import check_target
from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.marker import write_marker
from easy_fastapi_cli.scaffold.options import CreateOptions
from easy_fastapi_cli.scaffold.validate import apply_defaults, validate
from easy_fastapi_cli.scaffold.write import write_manifest

# (id, kwargs, expected_extensions)
COMBINATIONS = [
    ("backend-only-minimal", dict(project_name="p", package_name="p"), []),
    (
        "backend-only-tortoise-mysql",
        dict(project_name="p", package_name="p", database=True, orm="tortoise", db_dialect="mysql"),
        ["orm.tortoise"],
    ),
    (
        "backend-only-tortoise-pg-migration-auth",
        dict(
            project_name="p",
            package_name="p",
            database=True,
            orm="tortoise",
            db_dialect="postgres",
            migration=True,
            auth=True,
        ),
        ["orm.tortoise", "auth"],
    ),
    (
        "backend-only-sqlalchemy-sqlite-auth-redis",
        dict(
            project_name="p",
            package_name="p",
            database=True,
            orm="sqlalchemy",
            db_dialect="sqlite",
            auth=True,
            redis=True,
        ),
        ["orm.sqlalchemy", "auth", "redis"],
    ),
    (
        "backend-only-sqlmodel-mysql-full",
        dict(
            project_name="p",
            package_name="p",
            database=True,
            orm="sqlmodel",
            db_dialect="mysql",
            migration=True,
            auth=True,
            redis=True,
        ),
        ["orm.sqlmodel", "auth", "redis"],
    ),
    (
        "backend-only-static",
        dict(
            project_name="p",
            package_name="p",
            static=True,
        ),
        [],
    ),
    (
        "fullstack-tortoise-admin-auth",
        dict(
            project_name="p",
            package_name="p",
            frontend=True,
            database=True,
            orm="tortoise",
            db_dialect="mysql",
            auth=True,
        ),
        ["orm.tortoise", "auth"],
    ),
    (
        "fullstack-tortoise-admin-client",
        dict(
            project_name="p",
            package_name="p",
            frontend=True,
            database=True,
            orm="tortoise",
            db_dialect="mysql",
        ),
        ["orm.tortoise"],
    ),
    (
        "fullstack-sqlalchemy-auth-redis-static",
        dict(
            project_name="p",
            package_name="p",
            frontend=True,
            database=True,
            orm="sqlalchemy",
            db_dialect="postgres",
            auth=True,
            redis=True,
            static=True,
        ),
        ["orm.sqlalchemy", "auth", "redis"],
    ),
    (
        "fullstack-sqlmodel-minimal",
        dict(
            project_name="p",
            package_name="p",
            frontend=True,
            database=True,
            orm="sqlmodel",
            db_dialect="sqlite",
        ),
        ["orm.sqlmodel"],
    ),
    (
        "backend-only-en-lang",
        dict(
            project_name="p",
            package_name="p",
            language="en",
            database=True,
            orm="tortoise",
            db_dialect="mysql",
        ),
        ["orm.tortoise"],
    ),
    (
        "fullstack-en-lang-auth",
        dict(
            project_name="p",
            package_name="p",
            language="en",
            frontend=True,
            database=True,
            orm="sqlalchemy",
            db_dialect="mysql",
            auth=True,
        ),
        ["orm.sqlalchemy", "auth"],
    ),
]


def _create_project(tmp_path: Path, name: str, kwargs: dict):
    o = apply_defaults(CreateOptions(**kwargs))
    o = validate(o)
    project_dir = tmp_path / name
    check_target(project_dir, in_place=False)
    project_dir.mkdir(parents=True)
    templates_root = Path(str(files("easy_fastapi_cli") / "templates"))
    manifest = build_manifest(o, templates_root=templates_root)
    write_manifest(manifest, o, project_dir, templates_root)
    write_marker(project_dir, o, easy_fastapi_version="1.0.0", template_version="1.0.0")
    return project_dir


@pytest.mark.parametrize("name,kwargs,expected", COMBINATIONS, ids=[c[0] for c in COMBINATIONS])
def test_combination_creates_project(tmp_path, name, kwargs, expected):
    project_dir = _create_project(tmp_path, name, kwargs)
    data = json.loads((project_dir / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert set(data["registered_extensions"]) == set(expected)
    # fullstack 模式 pyproject 在 backend/ 下；backend-only 在根
    layout = data["project_layout"]
    pyproject = project_dir / ("backend/pyproject.toml" if layout == "fullstack" else "pyproject.toml")
    assert pyproject.exists()


def test_matrix_has_twelve_combinations():
    assert len(COMBINATIONS) == 12


def test_fullstack_project_has_frontend_dir(tmp_path):
    name, kwargs, _ = COMBINATIONS[6]  # fullstack-tortoise-admin-auth
    project_dir = _create_project(tmp_path, name, kwargs)
    assert (project_dir / "frontend").is_dir()
    assert (project_dir / "package.json").exists()


def test_backend_only_has_no_frontend_dir(tmp_path):
    name, kwargs, _ = COMBINATIONS[0]  # backend-only-minimal
    project_dir = _create_project(tmp_path, name, kwargs)
    assert not (project_dir / "frontend").exists()


def test_fullstack_has_backend_prefix(tmp_path):
    name, kwargs, _ = COMBINATIONS[6]  # fullstack-tortoise-admin-auth
    project_dir = _create_project(tmp_path, name, kwargs)
    assert (project_dir / "backend" / "app" / "main.py").exists()


def test_backend_only_no_backend_prefix(tmp_path):
    name, kwargs, _ = COMBINATIONS[0]  # backend-only-minimal
    project_dir = _create_project(tmp_path, name, kwargs)
    assert (project_dir / "app" / "main.py").exists()
    assert not (project_dir / "backend").exists()


def test_marker_schema_version_is_one(tmp_path):
    name, kwargs, _ = COMBINATIONS[0]
    project_dir = _create_project(tmp_path, name, kwargs)
    data = json.loads((project_dir / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert data["marker_schema_version"] == 1


def test_marker_has_project_layout(tmp_path):
    name, kwargs, _ = COMBINATIONS[6]  # fullstack
    project_dir = _create_project(tmp_path, name, kwargs)
    data = json.loads((project_dir / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert data["project_layout"] == "fullstack"


def test_backend_only_marker_layout(tmp_path):
    name, kwargs, _ = COMBINATIONS[0]
    project_dir = _create_project(tmp_path, name, kwargs)
    data = json.loads((project_dir / ".easy-fastapi.json").read_text(encoding="utf-8"))
    assert data["project_layout"] == "backend-only"

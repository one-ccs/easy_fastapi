"""build_manifest ORM 片段测试（真实包名+驱动，≥8 用例）。"""

from easy_fastapi_cli.scaffold.manifest import build_manifest
from easy_fastapi_cli.scaffold.options import CreateOptions


def _mk(**kw):
    base = {"project_name": "demo", "package_name": "demo", "database": True, "db_dialect": "mysql"}
    base.update(kw)
    return CreateOptions(**base)


# ── 1. tortoise + mysql ──


def test_tortoise_mysql():
    m = build_manifest(_mk(orm="tortoise"))
    dests = " ".join(f.dest for f in m.fragments)
    assert "app/models/user.py" in dests
    assert "tortoise-orm" in m.dependencies
    assert "asyncmy" in m.dependencies


# ── 2. tortoise + postgres ──


def test_tortoise_postgres():
    m = build_manifest(_mk(orm="tortoise", db_dialect="postgres"))
    assert "tortoise-orm" in m.dependencies
    assert "asyncpg" in m.dependencies


# ── 3. tortoise + sqlite ──


def test_tortoise_sqlite():
    m = build_manifest(_mk(orm="tortoise", db_dialect="sqlite"))
    assert "tortoise-orm" in m.dependencies
    assert "aiosqlite" in m.dependencies


# ── 4. sqlalchemy + sqlite ──


def test_sqlalchemy_sqlite():
    m = build_manifest(_mk(orm="sqlalchemy", db_dialect="sqlite"))
    assert "sqlalchemy" in m.dependencies
    assert "aiosqlite" in m.dependencies


# ── 5. sqlalchemy + postgres ──


def test_sqlalchemy_postgres():
    m = build_manifest(_mk(orm="sqlalchemy", db_dialect="postgres"))
    assert "sqlalchemy" in m.dependencies
    assert "asyncpg" in m.dependencies


# ── 6. sqlmodel + mysql ──


def test_sqlmodel_mysql():
    m = build_manifest(_mk(orm="sqlmodel", db_dialect="mysql"))
    assert "sqlmodel" in m.dependencies
    assert "asyncmy" in m.dependencies


# ── 7. database=False 无 ORM 片段/依赖 ──


def test_no_orm_fragments_when_database_false():
    o = CreateOptions(project_name="d", package_name="d")
    m = build_manifest(o)
    assert not any("models" in f.dest for f in m.fragments)
    joined = " ".join(m.dependencies)
    assert "tortoise-orm" not in joined
    assert "sqlalchemy" not in joined
    assert "sqlmodel" not in joined


# ── 8. ORM 片段不再生成 db_config / repository ──


def test_orm_fragments_config_and_repo():
    m = build_manifest(_mk(orm="tortoise"))
    dests = " ".join(f.dest for f in m.fragments)
    assert "app/core/db_config.py" not in dests
    assert "app/repository/user_repository.py" not in dests


# ── 9. 三 ORM 的 src 路径分目录 ──


def test_orm_src_paths_separated():
    for orm in ("tortoise", "sqlalchemy", "sqlmodel"):
        m = build_manifest(_mk(orm=orm))
        srcs = " ".join(f.src for f in m.fragments)
        assert f"{orm}/backend" in srcs


# ── 10. ORM 依赖只加一次（不重复）──


def test_orm_dep_not_duplicated():
    m = build_manifest(_mk(orm="tortoise"))
    assert m.dependencies.count("tortoise-orm") == 1


# ── 11. common 片段仍在（叠加不覆盖）──


def test_common_still_present_with_orm():
    m = build_manifest(_mk(orm="tortoise"))
    dests = {f.dest for f in m.fragments}
    assert "pyproject.toml" in dests
    assert "app/main.py" in dests
